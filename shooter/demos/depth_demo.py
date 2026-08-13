"""Fixed-screen 2.5D vertical slice.

Run directly with ``python -m shooter.demos.depth_demo``.  Art in
``Assets/Demo2_5D`` is optional; the scene intentionally has procedural
fallbacks so its mechanics remain easy to test while art is iterated.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pygame

from shooter.assets import load_asset
from shooter.demos.actor_runtime import (
    ActorGeometry,
    AnimationState,
    Direction,
    DirectionalSpriteSet,
)
from shooter.demos.demo_navigation import FlowField
from shooter.demos.environment_map import EnvironmentMap, EnvironmentProp

LOGICAL_SIZE = (1080, 720)
ARENA = pygame.Rect(24, 24, 1032, 672)
ASSET_ROOT = Path(__file__).resolve().parents[2] / "Assets" / "Demo2_5D"
ASSET_IDS = {
    "ground": "demo.2p5d.ground",
    "player": "demo.2p5d.player",
    "zombie": "demo.2p5d.zombie",
    "bush": "demo.2p5d.prop.bush",
    "tree": "demo.2p5d.prop.tree",
    "car": "demo.2p5d.prop.car",
    "fence": "demo.2p5d.prop.fence",
}


def _unit(vector: pygame.Vector2) -> pygame.Vector2:
    return vector.normalize() if vector.length_squared() else pygame.Vector2()


def _load(name: str, size: tuple[int, int]) -> pygame.Surface | None:
    try:
        catalogued = load_asset(ASSET_IDS[Path(name).stem])
        if catalogued.get_size() == size:
            return catalogued
        return pygame.transform.smoothscale(catalogued, size)
    except (KeyError, ValueError, FileNotFoundError, pygame.error):
        pass

    path = ASSET_ROOT / name
    if not path.is_file():
        return None
    try:
        return pygame.transform.smoothscale(
            pygame.image.load(path).convert_alpha(), size
        )
    except pygame.error:
        return None


def _actor_surface(kind: str, size: tuple[int, int]) -> pygame.Surface:
    loaded = _load(f"{kind}.png", size)
    if loaded:
        return loaded
    surface = pygame.Surface(size, pygame.SRCALPHA)
    cx, feet = size[0] // 2, size[1] - 8
    color = (48, 63, 45) if kind == "player" else (100, 78, 65)
    pygame.draw.ellipse(surface, (0, 0, 0, 75), (cx - 25, feet - 10, 50, 16))
    pygame.draw.polygon(
        surface,
        color,
        [(cx, feet - 78), (cx - 28, feet - 22), (cx, feet - 6), (cx + 28, feet - 22)],
    )
    pygame.draw.circle(surface, (154, 145, 114), (cx, feet - 70), 14)
    if kind == "player":
        pygame.draw.line(
            surface, (35, 35, 30), (cx, feet - 50), (cx + 42, feet - 62), 7
        )
    return surface


@dataclass
class Obstacle:
    name: str
    footprint: pygame.Rect
    image: pygame.Surface
    anchor_y: float

    def draw(self, target: pygame.Surface) -> None:
        target.blit(
            self.image,
            self.image.get_rect(midbottom=(self.footprint.centerx, self.anchor_y)),
        )


@dataclass
class Zombie:
    position: pygame.Vector2
    speed: float = 82.0
    health: int = 1
    radius: int = 14
    animation: AnimationState = field(
        default_factory=lambda: AnimationState("run", Direction.S)
    )
    action_clock: float = 0.0
    corpse_clock: float = 0.0
    hit_flash: float = 0.0
    knockback: pygame.Vector2 = field(default_factory=pygame.Vector2)

    @property
    def dead(self) -> bool:
        return self.health <= 0

    def hit(self) -> bool:
        """Apply a hit and return whether it was lethal."""
        self.health -= 1
        action = "death" if self.dead else "hit"
        self.animation.set(action, self.animation.direction)
        self.action_clock = 0.45 if self.dead else 0.12
        self.corpse_clock = 2.2 if self.dead else 0.0
        self.hit_flash = 0.1
        return self.dead

    @property
    def ground_y(self) -> float:
        return self.position.y


@dataclass
class Bullet:
    position: pygame.Vector2
    velocity: pygame.Vector2
    ttl: float = 1.15
    start: pygame.Vector2 = field(default_factory=pygame.Vector2)


class DemoState(str, Enum):
    READY = "ready"
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass
class Pickup:
    kind: str
    position: pygame.Vector2
    amount: int
    radius: int = 18


@dataclass
class MuzzleFlash:
    position: pygame.Vector2
    direction: pygame.Vector2
    ttl: float = 0.07


class DemoScene:
    """Testable scene containing all state for the fixed-screen demo."""

    def __init__(
        self,
        *,
        seed: int = 12,
        spawn_interval: float = 1.0,
        encounter_duration: float = 180.0,
        start_ready: bool = False,
        max_zombies: int = 30,
    ):
        self.seed = seed
        self.rng = random.Random(seed)
        self.state = DemoState.READY if start_ready else DemoState.PLAYING
        self.encounter_duration = encounter_duration
        self.max_zombies = max_zombies
        self.player = pygame.Vector2(LOGICAL_SIZE[0] / 2, LOGICAL_SIZE[1] / 2 + 80)
        self.player_radius = 16
        self.player_health = 100.0
        self.player_speed = 205.0
        self.aim = pygame.Vector2(1, 0)
        self.player_movement = pygame.Vector2()
        self.player_fire_clock = 0.0
        self.zombies: list[Zombie] = []
        self.corpses: list[Zombie] = []
        self.bullets: list[Bullet] = []
        self.pickups: list[Pickup] = []
        self.muzzle_flashes: list[MuzzleFlash] = []
        self.kills = 0
        self.elapsed = 0.0
        self.spawn_interval = spawn_interval
        self.spawn_clock = 0.0
        self.pickup_clock = 12.0
        self.flow_clock = 0.0
        self.shot_cooldown = 0.0
        self.ammo = 24
        self.reserve_ammo = 120
        self.magazine_size = 24
        self.reload_clock = 0.0
        self.debug = False
        self.player_image = _actor_surface("player", (104, 116))
        self.zombie_image = _actor_surface("zombie", (92, 108))
        self.player_animation = AnimationState("idle", Direction.E)
        self.player_sprites = DirectionalSpriteSet(
            ASSET_ROOT,
            "player",
            self.player_image.get_size(),
            self.player_image,
            fps={"idle": 5.0, "move": 9.0, "fire": 12.0},
            geometry=ActorGeometry(
                ground_anchor=(0.5, 0.96), weapon_socket=(0.82, 0.48)
            ),
        )
        self.zombie_sprites = DirectionalSpriteSet(
            ASSET_ROOT,
            "zombie",
            self.zombie_image.get_size(),
            self.zombie_image,
            fps={"run": 9.0, "attack": 7.0, "hit": 10.0, "death": 8.0},
            geometry=ActorGeometry(ground_anchor=(0.5, 0.96)),
        )
        self.player_sprites.preload(("idle", "move", "fire"))
        self.zombie_sprites.preload(("run", "attack", "hit", "death"))
        self.ground = self._make_ground()
        self.environment = EnvironmentMap()
        self.environment.draw_decals(self.ground)
        self.obstacles = self.environment.props
        self.flow = FlowField(ARENA)
        self.flow.rebuild([o.footprint for o in self.obstacles], self.player)

    @property
    def time_remaining(self) -> float:
        return max(0.0, self.encounter_duration - self.elapsed)

    def start(self) -> None:
        if self.state == DemoState.READY:
            self.state = DemoState.PLAYING

    def restart(self, *, ready: bool = False) -> None:
        self.__init__(
            seed=self.seed,
            spawn_interval=self.spawn_interval,
            encounter_duration=self.encounter_duration,
            start_ready=ready,
            max_zombies=self.max_zombies,
        )

    def reload(self) -> bool:
        if (
            self.reload_clock
            or self.ammo >= self.magazine_size
            or not self.reserve_ammo
        ):
            return False
        self.reload_clock = 0.85
        return True

    def _finish_reload(self) -> None:
        needed = self.magazine_size - self.ammo
        loaded = min(needed, self.reserve_ammo)
        self.ammo += loaded
        self.reserve_ammo -= loaded

    def _safe_pickup_position(self) -> pygame.Vector2:
        for _ in range(60):
            candidate = pygame.Vector2(
                self.rng.randrange(90, 990), self.rng.randrange(95, 650)
            )
            if (
                not self._blocked(candidate, 22)
                and candidate.distance_to(self.player) > 180
            ):
                return candidate
        return pygame.Vector2(ARENA.center)

    def spawn_pickup(self, kind: str | None = None) -> Pickup:
        kind = kind or ("ammo" if self.ammo + self.reserve_ammo < 80 else "health")
        pickup = Pickup(
            kind, self._safe_pickup_position(), 48 if kind == "ammo" else 35
        )
        self.pickups.append(pickup)
        return pickup

    @staticmethod
    def _make_ground() -> pygame.Surface:
        loaded = _load("ground.png", LOGICAL_SIZE)
        if loaded:
            return loaded
        surface = pygame.Surface(LOGICAL_SIZE)
        surface.fill((64, 76, 35))
        rng = random.Random(4)
        for _ in range(950):
            x, y = rng.randrange(1080), rng.randrange(720)
            color = rng.choice(
                ((76, 91, 39), (46, 62, 29), (104, 91, 49), (135, 119, 64))
            )
            pygame.draw.circle(surface, color, (x, y), rng.choice((1, 1, 2)))
        pygame.draw.ellipse(surface, (104, 89, 58), (180, 175, 720, 420))
        pygame.draw.ellipse(surface, (88, 76, 51), (205, 195, 675, 380), 4)
        return surface

    @staticmethod
    def _prop(
        name: str, size: tuple[int, int], color: tuple[int, int, int]
    ) -> pygame.Surface:
        loaded = _load(f"{name}.png", size)
        if loaded:
            return loaded
        surface = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.ellipse(surface, (0, 0, 0, 70), (8, size[1] - 25, size[0] - 16, 22))
        pygame.draw.ellipse(surface, color, (4, 5, size[0] - 8, size[1] - 22))
        pygame.draw.ellipse(
            surface,
            tuple(min(255, c + 28) for c in color),
            (15, 10, size[0] - 35, size[1] // 2),
        )
        return surface

    def _make_obstacles(self) -> list[Obstacle]:
        specs = (
            ("bush", pygame.Rect(198, 190, 86, 44), (155, 145), (43, 75, 31)),
            ("tree", pygame.Rect(775, 165, 52, 42), (190, 225), (41, 64, 27)),
            ("car", pygame.Rect(760, 500, 155, 58), (200, 120), (57, 60, 52)),
            ("fence", pygame.Rect(315, 530, 205, 28), (245, 100), (93, 73, 46)),
        )
        return [
            Obstacle(name, rect, self._prop(name, size, color), rect.bottom)
            for name, rect, size, color in specs
        ]

    def _blocked(self, position: pygame.Vector2, radius: int) -> bool:
        return self.environment.blocked(position, radius)

    def move_player(self, direction: pygame.Vector2, dt: float) -> None:
        self.player_movement = _unit(direction)
        delta = self.player_movement * self.player_speed * dt
        for axis in (0, 1):
            candidate = self.player.copy()
            candidate[axis] += delta[axis]
            candidate.x = min(ARENA.right - 18, max(ARENA.left + 18, candidate.x))
            candidate.y = min(ARENA.bottom - 18, max(ARENA.top + 18, candidate.y))
            if not self._blocked(candidate, self.player_radius):
                self.player = candidate

    def spawn_zombie(self) -> Zombie:
        position = pygame.Vector2(12, 360)
        for _ in range(40):
            side = self.rng.randrange(4)
            if side < 2:
                position = pygame.Vector2(
                    self.rng.randrange(40, 1040), 12 if side == 0 else 708
                )
            else:
                position = pygame.Vector2(
                    12 if side == 2 else 1068, self.rng.randrange(40, 680)
                )
            if not self._blocked(position, 14):
                break
        zombie = Zombie(position, self.rng.uniform(70, 105))
        self.zombies.append(zombie)
        return zombie

    def shoot(self, target: pygame.Vector2) -> bool:
        if (
            self.state != DemoState.PLAYING
            or self.shot_cooldown > 0
            or self.reload_clock
        ):
            return False
        if self.ammo <= 0:
            self.reload()
            return False
        direction = _unit(target - self.player)
        if not direction:
            return False
        self.aim = direction
        self.player_fire_clock = 0.13
        self.player_animation.set("fire", Direction.from_vector(self.aim))
        # Collision projectiles originate at the actor's ground-space centre.
        # The optional artwork socket is available to rendering for muzzle FX.
        origin = self.player + direction * 28
        self.bullets.append(Bullet(origin, direction * 700, 0.42, origin.copy()))
        self.muzzle_flashes.append(MuzzleFlash(origin, direction))
        self.ammo -= 1
        self.shot_cooldown = 0.16
        return True

    def _move_zombie(self, zombie: Zombie, dt: float) -> None:
        if zombie.dead or zombie.action_clock > 0:
            return
        toward = self.flow.direction(zombie.position, self.player)
        separation = pygame.Vector2()
        for other in self.zombies:
            if other is zombie or other.dead:
                continue
            offset = zombie.position - other.position
            if 0 < offset.length_squared() < 34 * 34:
                separation += offset.normalize() * (34 - offset.length()) / 34
        toward = _unit(toward + separation * 0.65)
        candidates = (toward, toward.rotate(55), toward.rotate(-55), toward.rotate(90))
        for direction in candidates:
            candidate = zombie.position + direction * zombie.speed * dt
            if not self._blocked(candidate, zombie.radius):
                zombie.position = candidate
                zombie.animation.set("run", Direction.from_vector(direction))
                break

    def update(
        self,
        dt: float,
        movement: pygame.Vector2 | None = None,
        aim_at: pygame.Vector2 | None = None,
        firing: bool = False,
    ) -> None:
        dt = min(dt, 0.05)
        if self.state != DemoState.PLAYING:
            return
        self.elapsed += dt
        if self.elapsed >= self.encounter_duration:
            self.state = DemoState.WON
            return
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        self.player_fire_clock = max(0.0, self.player_fire_clock - dt)
        prior_reload = self.reload_clock
        self.reload_clock = max(0.0, self.reload_clock - dt)
        if prior_reload > 0 and self.reload_clock == 0:
            self._finish_reload()
        self.move_player(movement or pygame.Vector2(), dt)
        if aim_at is not None:
            new_aim = _unit(aim_at - self.player)
            if new_aim:
                self.aim = new_aim
            if firing:
                self.shoot(aim_at)
        if self.player_fire_clock <= 0:
            if self.player_movement.length_squared():
                self.player_animation.set(
                    "move", Direction.from_vector(self.player_movement)
                )
            else:
                self.player_animation.set("idle", Direction.from_vector(self.aim))
        self.player_sprites.update(self.player_animation, dt)
        # Two seconds of breathing room around the midpoint.
        midpoint = self.encounter_duration / 2
        breathing = abs(self.elapsed - midpoint) < min(
            5.0, self.encounter_duration * 0.08
        )
        progress = min(1.0, self.elapsed / max(0.01, self.encounter_duration))
        current_interval = max(0.28, self.spawn_interval * (1.25 - progress * 0.75))
        self.spawn_clock += dt
        while self.spawn_clock >= current_interval:
            self.spawn_clock -= current_interval
            if (
                not breathing
                and sum(not z.dead for z in self.zombies) < self.max_zombies
            ):
                self.spawn_zombie()
        self.pickup_clock -= dt
        if self.pickup_clock <= 0 and len(self.pickups) < 2:
            self.spawn_pickup()
            self.pickup_clock = self.rng.uniform(14, 22)
        self.flow_clock -= dt
        if self.flow_clock <= 0:
            self.flow.rebuild([o.footprint for o in self.obstacles], self.player)
            self.flow_clock = 0.35
        for zombie in self.zombies:
            zombie.action_clock = max(0.0, zombie.action_clock - dt)
            zombie.hit_flash = max(0.0, zombie.hit_flash - dt)
            if zombie.knockback.length_squared():
                candidate = zombie.position + zombie.knockback * dt
                if not self._blocked(candidate, zombie.radius):
                    zombie.position = candidate
                zombie.knockback *= max(0.0, 1 - 10 * dt)
            self._move_zombie(zombie, dt)
            if not zombie.dead and zombie.position.distance_to(self.player) < 30:
                zombie.animation.set(
                    "attack", Direction.from_vector(self.player - zombie.position)
                )
                self.player_health = max(0.0, self.player_health - 22 * dt)
            self.zombie_sprites.update(zombie.animation, dt)
        for bullet in self.bullets:
            bullet.position += bullet.velocity * dt
            bullet.ttl -= dt
        for bullet in self.bullets:
            if bullet.ttl <= 0:
                continue
            for zombie in self.zombies:
                if (
                    not zombie.dead
                    and bullet.position.distance_to(zombie.position) < zombie.radius + 5
                ):
                    zombie.knockback = _unit(bullet.velocity) * 145
                    zombie.hit()
                    bullet.ttl = 0
                    if zombie.dead:
                        self.kills += 1
                        self.corpses.append(zombie)
                    break
        self.zombies = [z for z in self.zombies if not z.dead]
        for corpse in self.corpses:
            corpse.corpse_clock = max(0.0, corpse.corpse_clock - dt)
            self.zombie_sprites.update(corpse.animation, dt, loop=False)
        self.corpses = [corpse for corpse in self.corpses if corpse.corpse_clock > 0]
        self.bullets = [
            b
            for b in self.bullets
            if b.ttl > 0 and ARENA.inflate(80, 80).collidepoint(b.position)
        ]
        for flash in self.muzzle_flashes:
            flash.ttl -= dt
        self.muzzle_flashes = [flash for flash in self.muzzle_flashes if flash.ttl > 0]
        for pickup in self.pickups[:]:
            if (
                pickup.position.distance_to(self.player)
                <= pickup.radius + self.player_radius
            ):
                if pickup.kind == "health":
                    self.player_health = min(100.0, self.player_health + pickup.amount)
                else:
                    self.reserve_ammo += pickup.amount
                self.pickups.remove(pickup)
        if self.player_health <= 0:
            self.state = DemoState.LOST

    def depth_order(self) -> list[object]:
        return sorted(
            [*self.obstacles, *self.zombies, *self.corpses, "player"],
            key=self._ground_y,
        )

    def _ground_y(self, item: object) -> float:
        if item == "player":
            return self.player.y
        if isinstance(item, (Zombie, EnvironmentProp)):
            return float(item.ground_y)
        return float(item.anchor_y)

    def draw(self, target: pygame.Surface) -> None:
        target.blit(self.ground, (0, 0))
        for item in self.depth_order():
            if item == "player":
                self.player_sprites.draw(target, self.player_animation, self.player)
            elif isinstance(item, Zombie):
                rect = self.zombie_sprites.draw(target, item.animation, item.position)
                if item.hit_flash:
                    flash = pygame.Surface(rect.size, pygame.SRCALPHA)
                    flash.fill((255, 235, 210, int(150 * item.hit_flash / 0.1)))
                    target.blit(flash, rect, special_flags=pygame.BLEND_RGBA_ADD)
            elif isinstance(item, EnvironmentProp):
                item.draw(target, self.player)
            else:
                item.draw(target)
        for pickup in self.pickups:
            color = (91, 244, 91) if pickup.kind == "health" else (244, 194, 64)
            pygame.draw.circle(target, (8, 20, 8), pickup.position, pickup.radius + 5)
            pygame.draw.circle(target, color, pickup.position, pickup.radius, 3)
            label = "+" if pickup.kind == "health" else "A"
            glyph = pygame.font.Font(None, 30).render(label, True, color)
            target.blit(glyph, glyph.get_rect(center=pickup.position))
        for bullet in self.bullets:
            tail = bullet.position - _unit(bullet.velocity) * 26
            pygame.draw.line(target, (255, 229, 151), tail, bullet.position, 3)
        for flash in self.muzzle_flashes:
            tip = flash.position + flash.direction * 18
            side = flash.direction.rotate(90) * 6
            pygame.draw.polygon(
                target,
                (255, 215, 92),
                (flash.position - side, tip, flash.position + side),
            )
        if self.debug:
            for obstacle in self.obstacles:
                pygame.draw.rect(target, (255, 80, 80), obstacle.footprint, 2)
                pygame.draw.circle(
                    target,
                    (80, 220, 255),
                    (obstacle.footprint.centerx, round(obstacle.ground_y)),
                    3,
                )
            pygame.draw.circle(
                target, (80, 220, 255), self.player, self.player_radius, 2
            )
        self._draw_hud(target)
        if self.state != DemoState.PLAYING:
            self._draw_overlay(target)

    def _draw_hud(self, target: pygame.Surface) -> None:
        font = pygame.font.Font(None, 30)
        small = pygame.font.Font(None, 21)
        panel = pygame.Surface((280, 66), pygame.SRCALPHA)
        panel.fill((5, 13, 9, 215))
        pygame.draw.rect(panel, (78, 205, 71), panel.get_rect(), 2, border_radius=12)
        panel.blit(
            font.render(
                f"SURVIVE {int(self.time_remaining):03d}s   KILLS {self.kills}",
                True,
                "white",
            ),
            (16, 10),
        )
        pygame.draw.rect(panel, (35, 49, 35), (16, 43, 246, 10), border_radius=5)
        pygame.draw.rect(
            panel,
            (88, 219, 76),
            (16, 43, 246 * self.player_health / 100, 10),
            border_radius=5,
        )
        target.blit(panel, (LOGICAL_SIZE[0] // 2 - 140, 18))
        radar = pygame.Surface((150, 150), pygame.SRCALPHA)
        radar.fill((5, 13, 9, 205))
        pygame.draw.rect(radar, (78, 205, 71), radar.get_rect(), 2, border_radius=12)
        for zombie in self.zombies:
            pygame.draw.circle(
                radar,
                (217, 67, 45),
                (zombie.position.x * 150 / 1080, zombie.position.y * 150 / 720),
                2,
            )
        pygame.draw.circle(
            radar,
            (104, 240, 88),
            (self.player.x * 150 / 1080, self.player.y * 150 / 720),
            4,
        )
        radar.blit(small.render("RADAR", True, "white"), (8, 6))
        target.blit(radar, (18, 18))
        ammo = font.render(
            f"AMMO {self.ammo:02d} / {self.reserve_ammo:03d}", True, "white"
        )
        target.blit(ammo, (LOGICAL_SIZE[0] - ammo.get_width() - 28, 24))
        if self.reload_clock:
            target.blit(
                small.render("RELOADING", True, (105, 240, 88)),
                (LOGICAL_SIZE[0] - 128, 58),
            )

    def _draw_overlay(self, target: pygame.Surface) -> None:
        veil = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        veil.fill((2, 7, 4, 155))
        target.blit(veil, (0, 0))
        title_font = pygame.font.Font(None, 68)
        text_font = pygame.font.Font(None, 30)
        title = {
            DemoState.READY: "2.5D SURVIVAL PROTOTYPE",
            DemoState.WON: "EXTRACTION SURVIVED",
            DemoState.LOST: "OVERRUN",
        }[self.state]
        subtitle = (
            "SPACE TO BEGIN"
            if self.state == DemoState.READY
            else f"{self.kills} KILLS  •  R TO RESTART"
        )
        rendered = title_font.render(title, True, (112, 238, 88))
        target.blit(rendered, rendered.get_rect(center=(540, 310)))
        rendered = text_font.render(subtitle, True, "white")
        target.blit(rendered, rendered.get_rect(center=(540, 370)))
        if self.state == DemoState.READY:
            controls = text_font.render(
                "WASD MOVE  •  MOUSE AIM/FIRE  •  R RELOAD  •  F3 DEBUG",
                True,
                (210, 218, 207),
            )
            target.blit(controls, controls.get_rect(center=(540, 410)))


def run_demo() -> None:
    """Open and run the demo until Escape or the window close button."""
    pygame.init()
    window = pygame.display.set_mode(LOGICAL_SIZE)
    pygame.display.set_caption("2.5D Depth Demo")
    clock = pygame.time.Clock()
    scene = DemoScene(start_ready=True)
    running = True
    while running:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    scene.start()
                elif event.key == pygame.K_r:
                    if scene.state in (DemoState.WON, DemoState.LOST):
                        scene.restart()
                    else:
                        scene.reload()
                elif event.key == pygame.K_F3:
                    scene.debug = not scene.debug
        keys = pygame.key.get_pressed()
        movement = pygame.Vector2(
            keys[pygame.K_d]
            + keys[pygame.K_RIGHT]
            - keys[pygame.K_a]
            - keys[pygame.K_LEFT],
            keys[pygame.K_s]
            + keys[pygame.K_DOWN]
            - keys[pygame.K_w]
            - keys[pygame.K_UP],
        )
        scene.update(
            dt,
            movement,
            pygame.Vector2(pygame.mouse.get_pos()),
            pygame.mouse.get_pressed()[0],
        )
        scene.draw(window)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    run_demo()
