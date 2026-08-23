"""Neutral first vertical slice of Zombie Survival rules."""

from dataclasses import dataclass
import math

from shooter import config
from shooter.actor_creation import ActorDefinition
from shooter.damage import DamageRequest
from shooter.loadout import Loadout
from shooter.match_actors import move_match_actor, spawn_match_actors
from shooter.modes.zombie_survival.state import LOST, SurvivalStatus, SurvivalWallet
from shooter.spawn_selection import PlacementConstraints, SpawnQuery
from shooter.spawn_service import SpawnActorRequest
from shooter.targeting import first_box_target_on_ray
from shooter.weapon_attacks import AttackDescriptionService
from shooter.weapon_state import EquippedWeapon, WeaponDefinition
from shooter.world_collision import Aabb, actor_box, overlaps

SURVIVOR = ActorDefinition(
    "survivor",
    "soldier",
    "survivors",
    config.PLAYER_HEALTH,
    (48, 48),
    config.PLAYER_SPEED,
)
WALKER = ActorDefinition(
    "walker", "walker", "horde", config.ZOMBIE_HEALTH, (56, 56), config.ZOMBIE_SPEED
)
RIFLE = WeaponDefinition(
    "survivor_rifle",
    "ballistic",
    config.BULLET_DAMAGE,
    6.0,
    config.CLIP_SIZE,
    config.RESERVE_SIZE,
    config.RELOAD_SECONDS,
    "556",
)


@dataclass(frozen=True, slots=True)
class MoveSurvivor:
    direction: tuple[float, float]


@dataclass(frozen=True, slots=True)
class FireSurvivorWeapon:
    aim: tuple[float, float]


@dataclass(frozen=True, slots=True)
class ReloadSurvivorWeapon:
    pass


class SurvivalMode:
    """Shared-runtime Survival state with repeatable escalating waves."""

    def __init__(self, spawn_sources=(), enemy_count=None, preparation_seconds=None):
        self.spawn_sources = tuple(spawn_sources)
        self.initial_enemy_count = (
            config.WAVE_BASE if enemy_count is None else enemy_count
        )
        self.preparation_seconds = (
            config.WAVE_INTERVAL_SECONDS
            if preparation_seconds is None
            else preparation_seconds
        )
        self.player_id = None
        self.enemy_ids = ()
        self.spawn_results = ()
        self.loadouts = {}
        self.attacks = AttackDescriptionService()
        self.cash = SurvivalWallet()
        self.wave = 1
        self.phase = "combat"
        self.preparation_remaining = 0.0
        self.disposed = False

    def start(self, match):
        width, height = match.map_definition.size
        common = {
            "bounds": Aabb(0, 0, width, height),
            "collision": match.map_definition.collision,
        }
        player = spawn_match_actors(
            match,
            SpawnActorRequest(
                SURVIVOR,
                SpawnQuery(
                    role="player", faction="survivors", actor_kind="soldier"
                ),
                PlacementConstraints(
                    footprint=SURVIVOR.collision_size,
                    **common,
                ),
                1,
            ),
            self.spawn_sources,
            "survival-player-spawns",
            tags=("player",),
        )
        enemies = self._spawn_wave(match)
        self.player_id = player.actor_ids[0] if player.actor_ids else None
        if self.player_id is not None:
            self.loadouts[self.player_id] = Loadout(
                (EquippedWeapon(RIFLE),), capacity=1
            )
        self.spawn_results = (player.spawn_result, enemies.spawn_result)

    def _spawn_wave(self, match):
        width, height = match.map_definition.size
        enemies = spawn_match_actors(
            match,
            SpawnActorRequest(
                WALKER,
                SpawnQuery(role="enemy", faction="horde", actor_kind="walker"),
                PlacementConstraints(
                    footprint=WALKER.collision_size,
                    minimum_occupant_distance=max(WALKER.collision_size),
                    bounds=Aabb(0, 0, width, height),
                    collision=match.map_definition.collision,
                ),
                self.initial_enemy_count + (self.wave - 1) ** 2,
            ),
            self.spawn_sources,
            f"survival-enemy-spawns-wave-{self.wave}",
            tags=("enemy",),
        )
        self.enemy_ids += enemies.actor_ids
        self.spawn_results += (enemies.spawn_result,)
        self.phase = "combat"
        self.preparation_remaining = 0.0
        return enemies

    def advance(self, match, commands, dt):
        if dt < 0:
            raise ValueError("dt cannot be negative")
        if self.result(match) is not None:
            return
        self._advance_weapons(dt)
        for command in commands:
            if isinstance(command, MoveSurvivor) and self.player_id is not None:
                move_match_actor(match, self.player_id, command.direction, dt)
            elif isinstance(command, FireSurvivorWeapon):
                self._fire_weapon(match, command.aim)
            elif isinstance(command, ReloadSurvivorWeapon):
                self._selected_weapon().reload()
        if self.phase == "combat":
            self._advance_enemies(match, dt)
            self._apply_contact_damage(match, dt)
        self._advance_waves(match, dt)

    def status(self, match):
        return SurvivalStatus(
            phase=self.phase,
            wave=self.wave,
            preparation_remaining=self.preparation_remaining,
            cash=self.cash.balance,
            enemies_remaining=self.enemies_remaining(match),
            outcome=self.result(match),
        )

    def result(self, match):
        if self.player_id is None or self.player_id not in match.combat:
            return None
        return None if match.combat.get(self.player_id).alive else LOST

    def dispose(self, match):
        self.disposed = True

    def enemies_remaining(self, match):
        return sum(
            match.combat.get(enemy_id).alive
            for enemy_id in self.enemy_ids
            if enemy_id in match.combat
        )

    def _advance_enemies(self, match, dt):
        if self.player_id is None or self.player_id not in match.spatial:
            return
        target = match.spatial.get(self.player_id).transform
        for enemy_id in self.enemy_ids:
            if enemy_id not in match.spatial or not match.combat.get(enemy_id).alive:
                continue
            current = match.spatial.get(enemy_id).transform
            dx, dy = target.x - current.x, target.y - current.y
            distance = math.hypot(dx, dy)
            direction = (0, 0) if distance == 0 else (dx / distance, dy / distance)
            move_match_actor(match, enemy_id, direction, dt)

    def _selected_weapon(self):
        return self.loadouts[self.player_id].selected

    def _advance_weapons(self, dt):
        if self.player_id is None:
            return
        for weapon in self.loadouts[self.player_id]:
            weapon.advance(dt)

    def _fire_weapon(self, match, aim):
        if self.player_id is None or math.hypot(*aim) == 0:
            return
        weapon = self._selected_weapon()
        fired = weapon.fire()
        if not fired.accepted:
            return
        origin = match.spatial.get(self.player_id).transform
        attacks = self.attacks.create(
            weapon.definition,
            self.player_id,
            (origin.x, origin.y),
            aim,
            match.random_stream("survival-weapon-attacks"),
        )
        for attack in attacks:
            target_id = first_box_target_on_ray(
                match,
                attack.origin,
                attack.direction,
                (
                    enemy_id
                    for enemy_id in self.enemy_ids
                    if match.combat.get(enemy_id).alive
                ),
                config.BULLET_RANGE,
            )
            if target_id is None:
                continue
            result = match.damage.apply(
                DamageRequest(
                    attack.instigator_id,
                    self.player_id,
                    target_id,
                    attack.damage,
                    attack.attack_kind,
                    match.tick,
                    attack.weapon_id,
                )
            )
            self._award_kill(result)

    def _award_kill(self, damage_result):
        request = damage_result.request
        if (
            damage_result.lethal
            and request.instigator_id == self.player_id
            and request.target_id in self.enemy_ids
        ):
            self.cash.increase_cash(config.KILL_REWARD)

    def _apply_contact_damage(self, match, dt):
        if dt == 0 or self.player_id is None or self.player_id not in match.spatial:
            return
        player_state = match.spatial.get(self.player_id)
        if player_state.collision is None:
            return
        player_box = actor_box(player_state.transform, player_state.collision)
        for enemy_id in self.enemy_ids:
            if enemy_id not in match.spatial or not match.combat.get(enemy_id).alive:
                continue
            enemy_state = match.spatial.get(enemy_id)
            if enemy_state.collision is None:
                continue
            enemy_box = actor_box(enemy_state.transform, enemy_state.collision)
            if overlaps(enemy_box, player_box):
                match.damage.apply(
                    DamageRequest(
                        enemy_id,
                        enemy_id,
                        self.player_id,
                        config.ZOMBIE_DAMAGE * dt,
                        "contact",
                        match.tick,
                    )
                )

    def _advance_waves(self, match, dt):
        if self.result(match) is not None:
            return
        if self.phase == "combat":
            if self.enemies_remaining(match) == 0:
                self.phase = "preparation"
                self.preparation_remaining = self.preparation_seconds
            return
        self.preparation_remaining = max(0.0, self.preparation_remaining - dt)
        if self.preparation_remaining == 0:
            self.wave += 1
            self._spawn_wave(match)
