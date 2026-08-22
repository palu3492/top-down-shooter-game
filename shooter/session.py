"""One playthrough: the world, and how it advances and draws.

`game_loop` used to hold all of this as fifty locals, which meant there was
nothing to construct and nothing to discard -- and so no way to start a game,
end one, or have none running while a menu is up.

The rules arrive as a collaborator. `WaveSystem` is the freeplay rules today;
a campaign replaces it without this file changing.

World state -- positions, health, cash, the wave count -- lives in plain
attributes that never hold a `Surface`, so writing a session to disk later is
additive rather than a rewrite.
"""

import math

import pygame

from shooter import commands, config, items
from shooter.background import TiledBackground
from shooter.camera import FollowCamera
from shooter.collision import load_obstacles
from shooter.entities import powerups as powerup_kinds
from shooter.entities.player import Human
from shooter.entities.zombie import keep_apart
from shooter.entities.powerups import PowerUps
from shooter.entities.props import Harvestable
from shooter.entities.projectiles import LETHAL, Grenade, StunGrenade
from shooter.render import blit_group
from shooter.spatial import Bounds, Box, SpatialStore, Transform
from shooter.systems import loot, shop, world
from shooter.systems.waves import WaveSystem
from shooter.ui.hud import HUD, Cash, GrenadeData, HealthBar, WeaponPanel, prompt
from shooter.ui.radar import RadarScreen
from shooter.ui.shopfront import ShopFront
from shooter.weapons import RELOAD, SLOTS, equip, everything
from shooter.viewport import visible_world
from shooter.domain_events import EventQueue
from shooter.map_definition import current_map_definition
from shooter.world_collision import Aabb, actor_box, overlaps
from shooter.world_registry import WorldRegistry

INSTAKILL_SECONDS = config.INSTAKILL_SECONDS
INSTAKILL_TOP = 40
RELOADING_TOP = 100
COLLISION_DEBUG = (255, 0, 255)

# Legacy public key constants retained only while direct Session-input tests are
# migrated. Production input translation lives in `PygameInputAdapter`.
SLOT_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)
INTERACT = pygame.K_e
GRANT_ALL = pygame.K_0

# What the player bumps into. Smaller than the sprite, and fixed rather than
# read from `human.rect`, which grows and shrinks as the player turns -- a
# hitbox that depends on where you are aiming is not a hitbox.
PLAYER_SOLID = (70, 70)

# Chopping the same tree twice tops up the pile already lying there rather than
# starting a second one. Ten wood is one thing to look at, not ten.
MERGE_WITHIN = 110

# How long "+4 WOOD" or "NO ROOM" stays on the screen, and how far above the
# player it sits -- fixed heights near the top are where the between-wave
# banner already is, and the two printed over each other.
NOTICE_SECONDS = 1.6
NOTICE_ABOVE = 120

# How a game can finish. `None` means it is still being played.
LOST, WON = "LOST", "WON"


def collect_powerup(kind, human, zombie_group, carried):
    """Apply a collected power-up. Returns instakill seconds to add, if any.

    Ammunition is restored to everything carried rather than to whatever
    happens to be in hand -- a pickup walked over with the knife out used to
    refill the knife, which is to say nothing at all.
    """
    if kind == powerup_kinds.NUKE:
        zombie_group.empty()
    elif kind == powerup_kinds.MAX_HEALTH:
        human.restore_health()
    elif kind == powerup_kinds.MAX_AMMO:
        for held in carried:
            held.refill()
    elif kind == powerup_kinds.INSTAKILL:
        return INSTAKILL_SECONDS
    return 0.0


def is_zombie_attacking(human, zombie, dt=config.SIM_DT):
    attacking = pygame.sprite.collide_rect(human, zombie)
    zombie.update_anim("ATTACK" if attacking else "MOVE", dt)
    if attacking and human.remove_health(config.ZOMBIE_DAMAGE * dt):
        human.kill()
    return attacking


def explosion_touching_zombie(zombie, explosion):
    if pygame.sprite.collide_rect(zombie, explosion) and zombie.remove_health(
        config.EXPLOSION_DAMAGE
    ):
        zombie.kill()


def stun_explosion_touching_zombie(zombie, explosion):
    if pygame.sprite.collide_rect(zombie, explosion):
        zombie.remove_speed(config.STUN_SPEED)


def centred_text(screen, window, message, top, size, colour=config.WHITE):
    """Measured and centred rather than nudged by a hand-tuned offset.

    `window[0] / 2 - 70` was only ever centred for one particular string at one
    particular font size.
    """
    text = pygame.font.Font(None, size).render(message, True, colour)
    screen.blit(text, (window[0] / 2.0 - text.get_width() / 2.0, top))


class Session:
    """A game in progress."""

    def __init__(self, window, rules=WaveSystem, map_definition=None):
        self.map_definition = map_definition or current_map_definition()
        self.window = window
        self._camera_x, self._camera_y = 0, 0
        self.previous_camera = (0, 0)
        self.instakill_seconds = 0.0
        # Sampled now rather than left at the origin: input is handled before
        # the loop first calls `aim_at`, so a click on the opening frame would
        # otherwise fire at atan2(0, 0) -- straight right, wherever the pointer.
        self.aim = (0, 0)
        self.aim_at(pygame.mouse.get_pos())

        self.change_x = self.change_y = 0
        self.shooting = False

        self.background = TiledBackground(self.map_definition.presentation_source)
        self.world_size = self.map_definition.size
        self.camera_x = self.window[0] / 2 - self.world_size[0] / 2
        self.camera_y = self.window[1] / 2 - self.world_size[1] / 2
        self.previous_camera = self.camera
        self.obstacles = load_obstacles(self.map_definition.presentation_source)
        # Compatibility container for tests and legacy runtime additions.
        # Authored collision arrives through the neutral map definition.
        self.collision_rects = []
        self.human = Human(window)
        self.human_group = pygame.sprite.Group(self.human)
        self.zombies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.grenades = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.stun_grenades = pygame.sprite.Group()
        self.stun_explosions = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group(PowerUps())

        self.cash = Cash()
        self.carried = [equip(which) for which in SLOTS]
        self.equipped = self.carried[0]
        self.shopping = False
        self.shop_says = None
        self.backpack = items.Backpack()
        self.dropped = pygame.sprite.Group()
        self.notice = None
        self.notice_seconds = 0.0
        self.grenade_data = GrenadeData()
        self.heads_up_display = HUD(window)
        self.health_display = HealthBar(window)
        self.weapon_display = WeaponPanel(window, self.grenade_data)
        self.shop_display = ShopFront(window)
        self.radar = RadarScreen()

        self.rules = rules(window, self.zombies, self.cash, self.visible)
        self.props = pygame.sprite.Group()
        self.events = EventQueue()
        self.entities = WorldRegistry(self.events)
        self.player_id = self.entities.register(self.human, ("actor", "player"))
        self.spatial = SpatialStore()
        self.spatial.attach(
            self.player_id,
            Transform(*self._muzzle()),
            Box(*PLAYER_SOLID),
        )
        self.player_bounds = Bounds(
            self.window[0] / 2,
            self.window[1] / 2,
            self.world_size[0] - self.window[0] / 2,
            self.world_size[1] - self.window[1] / 2,
        )
        self.presentation_camera = FollowCamera(
            self.window, self.world_size, self.spatial, self.player_id
        )
        self._camera_x, self._camera_y = self.presentation_camera.offset
        self._enemy_ids = {}
        self._sync_enemy_registry()

    @property
    def outcome(self):
        """`None` while the game is still being played.

        Losing belongs to the session: a player at zero health is lost whatever
        mode is being played. Winning belongs to the rules, because what counts
        as finished is exactly what a mode decides -- endless freeplay never
        declares one.
        """
        if not self.human.alive():
            return LOST
        return self.rules.outcome

    @property
    def visible(self):
        return visible_world((self.camera_x, self.camera_y), self.window)

    @property
    def camera(self):
        return (self.camera_x, self.camera_y)

    @property
    def camera_x(self):
        if hasattr(self, "presentation_camera"):
            return self.presentation_camera.offset[0]
        return self._camera_x

    @camera_x.setter
    def camera_x(self, value):
        self._camera_x = value
        if hasattr(self, "spatial"):
            current = self.spatial.get(self.player_id).transform
            self.spatial.move_to(
                self.player_id, self.window[0] / 2 - value, current.y
            )
            self.presentation_camera.sync()

    @property
    def camera_y(self):
        if hasattr(self, "presentation_camera"):
            return self.presentation_camera.offset[1]
        return self._camera_y

    @camera_y.setter
    def camera_y(self, value):
        self._camera_y = value
        if hasattr(self, "spatial"):
            current = self.spatial.get(self.player_id).transform
            self.spatial.move_to(
                self.player_id, current.x, self.window[1] / 2 - value
            )
            self.presentation_camera.sync()

    def resize(self):
        """Take no window: there is only ever one.

        AT25 replaced twenty copies of the render size with a single shared
        `Viewport`, so the readouts, the health bar and every zombie already read the
        new size the moment it changes. Accepting a window here would imply
        there are copies to update and quietly leave most of them stale -- the
        player is the only thing holding a position derived from it.
        """
        self.human.recentre(self.window)
        self.presentation_camera.resize(self.window)

    def aim_at(self, pointer):
        """Sampled once per frame; the pointer does not move between steps."""
        self.aim = (
            int(pointer[0] - self.window[0] / 2),
            -int(pointer[1] - self.window[1] / 2),
        )

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle(self, event):
        """Temporary compatibility for callers still sending pygame events."""
        from shooter.input_adapter import PygameInputAdapter

        command = PygameInputAdapter().action_for(event)
        if command is not None:
            self.apply_action(command)

    def apply_action(self, command):
        """Apply discrete player intent without exposing pygame to the caller."""
        if self.shopping:
            if command.action == commands.INTERACT:
                self.shopping = False
            elif command.action == commands.SELECT_SLOT and command.value is not None:
                line = command.value
                if line < len(shop.STOCK):
                    self.shop_says = shop.buy(
                        shop.STOCK[line], self.cash, self.carried
                    )
            return
        if command.action == commands.FIRE:
            self._shoot()
        elif command.action == commands.INTERACT:
            self._interact()
        elif command.action == commands.SKIP_PHASE:
            request_skip = getattr(self.rules, "request_skip", None)
            if request_skip is not None:
                request_skip()
        elif command.action == commands.USE_GRENADE:
            self._use_grenade(stun=False)
        elif command.action == commands.USE_STUN_GRENADE:
            self._use_grenade(stun=True)
        elif command.action == commands.RELOAD:
            self.equipped.manual_reload()
        elif command.action == commands.SELECT_SLOT and command.value is not None:
            self._equip(command.value)
        elif command.action == commands.GRANT_ALL and config.DEV_TOOLS:
            self._grant_everything()

    @property
    def ammo_count(self):
        """Why the weapon in hand cannot be fired, or `None`.

        Read from the weapon rather than remembered here. Holding it on the
        session meant it described whichever weapon was equipped a moment ago,
        and changing weapon wiped it.
        """
        return self.equipped.status

    def _shoot(self):
        if self.shopping or not self.equipped.ready:
            return
        self.shooting = True
        self.bullets.add(self.equipped.attack(self._muzzle(), self.aim, self._damage()))
        self.equipped.fire()

    def _damage(self):
        return LETHAL if self.instakill_seconds > 0 else self.equipped.damage

    @property
    def nearby(self):
        """What the player is standing close enough to use, if anything."""
        here = self._muzzle()
        return next((prop for prop in self.props if prop.within(here)), None)

    def _use_grenade(self, stun):
        if stun and self.grenade_data.stun_grenade_amount > 0:
            self.stun_grenades.add(StunGrenade(*self._muzzle(), *self.aim))
            self.grenade_data.stun_grenade_amount -= 1
        elif not stun and self.grenade_data.grenade_amount > 0:
            self.grenades.add(Grenade(*self._muzzle(), *self.aim))
            self.grenade_data.grenade_amount -= 1

    def _grant_everything(self):
        """Every weapon there is, loaded, on the number keys.

        For trying the armoury without playing to it. What does not fit in the
        slots is left out rather than made unreachable -- five keys is five
        weapons, and which five is a choice AT41 gives the player properly.
        """
        self.carried = everything()[: commands.SLOT_COUNT]
        self.equipped = self.carried[0]

    def _equip(self, slot):
        """Hold something else.

        Nothing is reset. A gun put away mid-reload goes on reloading and is
        still locked when it comes back -- clearing that here let the player
        cancel every reload, and fire an empty gun, with two keystrokes.
        """
        if slot >= len(self.carried):
            return
        self.equipped = self.carried[slot]

    def _interact(self):
        """Use what is at hand: a stand sells, a tree is chopped."""
        thing = self.nearby
        if thing is None:
            return
        if isinstance(thing, Harvestable):
            self._chop(thing)
            return
        self.shopping = True
        self.shop_says = None

    def _chop(self, thing):
        won = thing.harvest(self.equipped.damage, self.equipped)
        if won:
            self._spill(thing.yields.item, won, thing.middle)

    def _spill(self, item, count, at):
        """Drop this here, or add it to what is already lying here."""
        for pile in self.dropped:
            if pile.item is item and math.dist(pile.middle, at) <= MERGE_WITHIN:
                pile.count += count
                return
        self.dropped.add(world.spilled(item, count, at))

    def _drop_loot(self, standing):
        """Leave behind what the fallen were carrying.

        Only what was actually killed. A nuke empties the group without
        anything being cut down, and the field should not be carpeted for it.
        """
        for zombie in standing - set(self.zombies):
            if not zombie.killed:
                continue
            for item, count in loot.spoils(zombie.kind):
                self._spill(item, count, zombie.get_position())

    def _gather(self):
        """Take what is underfoot, as far as there is room for it.

        A pile the pack cannot take is left exactly as it was and said out
        loud: walking over wood and seeing nothing happen reads as a bug rather
        than as a full backpack.
        """
        here = self._muzzle()
        for pile in list(self.dropped):
            if not pile.within(here):
                continue
            item = pile.item
            taken = pile.take(self.backpack)
            self.say(f"+{taken} {item.name.upper()}" if taken else "NO ROOM")

    def say(self, message):
        self.notice = message
        self.notice_seconds = NOTICE_SECONDS

    def _muzzle(self):
        if hasattr(self, "spatial") and self.player_id in self.spatial:
            position = self.spatial.get(self.player_id).transform
            return (position.x, position.y)
        return (
            (self.window[0] / 2.0) - self.camera_x,
            (self.window[1] / 2.0) - self.camera_y,
        )

    # ------------------------------------------------------------------
    # Simulation: one fixed step.
    # ------------------------------------------------------------------

    def step(self, pressed, dt=config.SIM_DT, trigger=False):
        """Temporary compatibility for pygame-key-state tests and callers."""
        from shooter.input_adapter import PygameInputAdapter

        controls = PygameInputAdapter().legacy_controls(pressed, self.aim, trigger)
        self.step_controls(controls, dt)

    def step_controls(self, controls, dt=config.SIM_DT):
        """Advance from neutral continuous intent during the migration seam."""
        self.aim = controls.aim
        if self.human.alive():
            self.change_x = controls.move[0] * config.PLAYER_SPEED * dt
            self.change_y = controls.move[1] * config.PLAYER_SPEED * dt
        self._step_after_movement(dt, controls.trigger_held)

    def _step_after_movement(self, dt, trigger):
        self._sync_enemy_registry()
        self.previous_camera = self.camera
        self._advance_player()

        for held in self.carried:
            held.tick(dt)

        self._gather()
        if self.notice_seconds > 0:
            self.notice_seconds = max(0.0, self.notice_seconds - dt)
            if not self.notice_seconds:
                self.notice = None

        # Walking away closes the stand. Nothing else would, and a shop that
        # follows the player across the map is not a place.
        if self.shopping and self.nearby is None:
            self.shopping = False

        # Holding the button keeps an automatic weapon firing. Everything else
        # is one pull per shot, and its rate is what stops the clicking.
        if trigger and self.equipped.automatic:
            self._shoot()

        self._animate_player(dt)
        # Who was standing before anything could cut them down. Loot is worked
        # out from who is missing afterwards rather than at the moment of
        # death, which happens inside a bullet, a swing and an explosion --
        # three places with no business knowing what a pickup is.
        standing = set(self.zombies)
        self._advance_zombies(dt)
        self._collect_powerups(dt)

        self.bullets.update(self.camera_x, self.camera_y, self.zombies, dt)
        self.grenades.update(self.camera_x, self.camera_y, self.explosions, dt)
        self.explosions.update(self.camera_x, self.camera_y, dt)
        self.stun_grenades.update(
            self.camera_x, self.camera_y, self.stun_explosions, dt
        )
        self.stun_explosions.update(self.camera_x, self.camera_y, dt)

        self._drop_loot(standing)

        if not self.zombies:
            self.rules.advance(self.window, self.zombies, self.cash, dt, self.visible)
        self._sync_enemy_registry()

        self.instakill_seconds = max(0.0, self.instakill_seconds - dt)
        self.change_x = self.change_y = 0
        self.shooting = False

    def _sync_enemy_registry(self):
        """Temporary bridge while legacy rules still mutate a sprite group."""
        present = set(self.zombies)
        for zombie in present - self._enemy_ids.keys():
            entity_id = self.entities.register(
                zombie, ("actor", "enemy")
            )
            self._enemy_ids[zombie] = entity_id
            self.spatial.attach(
                entity_id,
                Transform(
                    zombie.world_x + config.ZOMBIE_SIZE[0] / 2,
                    zombie.world_y + config.ZOMBIE_SIZE[1] / 2,
                ),
                Box(*config.ZOMBIE_SIZE),
            )
        for zombie in present:
            entity_id = self._enemy_ids[zombie]
            self.spatial.move_to(
                entity_id,
                zombie.world_x + config.ZOMBIE_SIZE[0] / 2,
                zombie.world_y + config.ZOMBIE_SIZE[1] / 2,
            )
        for zombie in self._enemy_ids.keys() - present:
            entity_id = self._enemy_ids.pop(zombie)
            self.spatial.remove(entity_id)
            self.entities.remove(entity_id, reason="legacy_group_removal")

    def _advance_player(self):
        """Move authoritative world state, unless something is in the way.

        One axis at a time, so walking into a tree at an angle slides along it
        rather than stopping dead. Anything already overlapping is let through
        in either direction -- a player who somehow ends up inside a footprint
        should be able to walk out of it rather than be held there.
        """
        current = self.spatial.get(self.player_id).transform
        stuck = self._blocked_world(current)

        wanted = self.player_bounds.clamp(
            Transform(current.x + self.change_x, current.y)
        )
        if stuck or not self._blocked_world(wanted):
            current = wanted

        wanted = self.player_bounds.clamp(
            Transform(current.x, current.y + self.change_y)
        )
        if stuck or not self._blocked_world(wanted):
            current = wanted

        self.spatial.move_to(self.player_id, current.x, current.y)
        self._camera_x, self._camera_y = self.presentation_camera.sync()

    def _standing_at(self, camera_x, camera_y):
        box = pygame.Rect(0, 0, *PLAYER_SOLID)
        box.center = (
            self.window[0] / 2 - camera_x,
            self.window[1] / 2 - camera_y,
        )
        return box

    def _blocked(self, camera_x, camera_y):
        """Compatibility query for callers still positioning through a camera."""
        return self._blocked_world(
            Transform(
                self.window[0] / 2 - camera_x,
                self.window[1] / 2 - camera_y,
            )
        )

    def _blocked_world(self, transform):
        state = self.spatial.get(self.player_id)
        here = actor_box(transform, state.collision)
        return any(overlaps(here, obstacle) for obstacle in self._world_obstacles())

    def _world_obstacles(self):
        yield from self.map_definition.collision
        for rect in self.collision_rects:
            yield Aabb(rect.x, rect.y, rect.width, rect.height)
        for prop in self.props:
            footprint = prop.footprint
            if footprint is not None:
                yield Aabb(
                    footprint.x, footprint.y, footprint.width, footprint.height
                )

    def _animate_player(self, dt):
        # Preserves the original rule, quirks included: MOVE only when both
        # axes are positive, otherwise IDLE, and SHOOT overrides either.
        animation = "MOVE"
        if self.change_x <= 0 or self.change_y <= 0:
            animation = "IDLE"
        if self.shooting:
            animation = "SHOOT"
        self.human.update_anim(animation, dt, self.equipped.weapon.id)
        # Rotation resizes human.rect, which collision reads, so it has to
        # happen exactly once per step -- in the render pass it compounded with
        # frame rate and inflated the hitbox.
        self.human.rot_center(math.degrees(math.atan2(self.aim[1], self.aim[0])))

    def _advance_zombies(self, dt):
        for zombie in self.zombies:
            # The player moves through the world by moving the camera. Keep the
            # zombie's screen-space collision box in step with that camera
            # before deciding whether it is still touching the player. An
            # attacking zombie does not call move_toward_center(), so without
            # this sync its old box can remain on the player indefinitely.
            zombie.move_position(self.camera_x, self.camera_y)
            attacking = is_zombie_attacking(self.human, zombie, dt)
            if attacking:
                zombie.face_player()
            else:
                zombie.move_toward_center(self.camera_x, self.camera_y, dt)
            for explosion in self.explosions:
                explosion_touching_zombie(zombie, explosion)
            for stun_explosion in self.stun_explosions:
                stun_explosion_touching_zombie(zombie, stun_explosion)
            zombie.zombie_speed_timer(dt)

        keep_apart(self.zombies, self.camera, dt)

    def _collect_powerups(self, dt):
        for powerup in self.powerups:
            collected = powerup.update(self.human, self.camera_x, self.camera_y, dt)
            if collected is None:
                continue
            if collected != powerup_kinds.EXPIRED:
                self.instakill_seconds += collect_powerup(
                    collected, self.human, self.zombies, self.carried
                )
            powerup.kill()

    # ------------------------------------------------------------------
    # Render: once per frame, between steps.
    # ------------------------------------------------------------------

    def draw(self, screen, alpha):
        draw_x, draw_y = self._interpolated_camera(alpha)

        self.background.draw(screen, draw_x, draw_y)
        for obstacle in self.obstacles:
            obstacle.draw(screen, COLLISION_DEBUG, (draw_x, draw_y))
        for rect in self.collision_rects:
            pygame.draw.rect(screen, COLLISION_DEBUG, rect.move(draw_x, draw_y), 2)

        blit_group(screen, self.dropped, draw_x, draw_y, alpha)
        blit_group(screen, self.powerups, draw_x, draw_y, alpha)
        for zombie in self.zombies:
            zombie.health_bar(screen, zombie.draw_position(draw_x, draw_y, alpha))
        blit_group(screen, self.zombies, draw_x, draw_y, alpha)
        self.human_group.draw(screen)
        player_solid = pygame.Rect(0, 0, *PLAYER_SOLID)
        player_solid.center = (self.window[0] / 2, self.window[1] / 2)
        pygame.draw.rect(screen, COLLISION_DEBUG, player_solid, 2)
        blit_group(screen, self.bullets, draw_x, draw_y, alpha)

        if not self.zombies:
            self.rules.draw(screen, self.window)

        for group in (
            self.grenades,
            self.explosions,
            self.stun_grenades,
            self.stun_explosions,
        ):
            blit_group(screen, group, draw_x, draw_y, alpha)

        self._draw_overlays(screen)

    def _interpolated_camera(self, alpha):
        return (
            self.previous_camera[0] + (self.camera_x - self.previous_camera[0]) * alpha,
            self.previous_camera[1] + (self.camera_y - self.previous_camera[1]) * alpha,
        )

    def _draw_overlays(self, screen):
        self.radar.draw(
            screen,
            -self.camera_x + self.window[0] / 2,
            -self.camera_y + self.window[1] / 2,
        )
        for zombie in self.zombies:
            self.radar.update_zom(screen, zombie)

        if self.instakill_seconds > 0:
            centred_text(
                screen,
                self.window,
                f"INSTAKILL {int(self.instakill_seconds) + 1}s",
                INSTAKILL_TOP,
                size=34,
                colour=config.INSTAKILL_TEXT,
            )

        self.heads_up_display.update(screen, self.window)
        self.health_display.draw(screen, self.human.get_health())
        self.weapon_display.draw(screen, self.equipped)
        self.cash.update(screen, self.window)

        if self.ammo_count == RELOAD:
            centred_text(screen, self.window, "Reloading", RELOADING_TOP, size=30)

        if self.notice:
            centred_text(
                screen,
                self.window,
                self.notice,
                self.window[1] / 2 - NOTICE_ABOVE,
                size=30,
            )

        if self.shopping:
            self.shop_display.draw(screen, self.cash, self.carried, self.shop_says)
        elif self.nearby is not None:
            prompt(screen, self.window, self.nearby.label)
