"""Neutral first vertical slice of Zombie Survival rules."""

from dataclasses import dataclass
import math

from shooter import config
from shooter.actor_creation import ActorDefinition
from shooter.construction import ConstructionService
from shooter.consumables import ConsumableInventory, ConsumablePurchaseService
from shooter.damage import DamageRequest
from shooter.equipment_roles import ToolSlot
from shooter.harvesting import HarvestingService
from shooter.interactions import InteractionService
from shooter.loadout import Loadout
from shooter.map_definition import MapInteraction
from shooter.match_actors import (
    move_match_actor,
    remove_match_actor,
    spawn_match_actors,
)
from shooter.modes.zombie_survival.state import LOST, SurvivalStatus, SurvivalWallet
from shooter.resources import ResourceInventory
from shooter.station_purchases import StationPurchaseService
from shooter.survival_balance import load_survival_balance
from shooter.modes.zombie_survival.wave_config import (
    EnemyWaveRule,
    SurvivalWavePlan,
)
from shooter.spawn_selection import PlacementConstraints, SpawnQuery
from shooter.spawn_director import (
    SpawnBudget,
    SpawnDirector,
    SpawnDirectorPolicy,
)
from shooter.spawn_service import SpawnActorRequest
from shooter.steering import pursue_match_actor, separate_overlapping_actors
from shooter.targeting import first_box_target_on_ray
from shooter.weapon_attacks import AttackDescriptionService, damage_at_distance
from shooter.weapon_purchases import WeaponCatalog, WeaponPurchaseService
from shooter.weapon_state import AUTOMATIC, NO_AMMO, EquippedWeapon, WeaponDefinition
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
    "walker", "walker", "horde", config.ZOMBIE_HEALTH, (56, 56), 240
)
RUNNER = ActorDefinition("runner", "runner", "horde", 70, (42, 42), 380)
BREAKER = ActorDefinition("breaker", "breaker", "horde", 260, (64, 64), 220)
ENEMY_BARRICADE_DAMAGE = {"walker": 1.0, "runner": 1.0, "breaker": 4.0}
RIFLE = WeaponDefinition(
    "survivor_rifle",
    "ballistic",
    config.BULLET_DAMAGE,
    6.0,
    30,
    30,
    config.RELOAD_SECONDS,
    "556",
    max_range=1300,
    effective_range=800,
    minimum_damage_fraction=0.7,
)
PISTOL = WeaponDefinition(
    "survivor_pistol", "ballistic", 18, 4.0, 12, 48, 1.0, "9mm",
    max_range=800, effective_range=500, minimum_damage_fraction=0.65,
)
SMG = WeaponDefinition(
    "survivor_smg",
    "ballistic",
    12,
    12.0,
    40,
    200,
    1.2,
    "9mm",
    spread=5.0,
    firing_mode=AUTOMATIC,
    max_range=650,
    effective_range=350,
    minimum_damage_fraction=0.55,
)
PICKAXE = WeaponDefinition(
    "survivor_pickaxe",
    "melee",
    75,
    3.0,
    reach=85,
    arc=70,
    capabilities=frozenset(("melee_attack", "harvest")),
)
SURVIVAL_WEAPONS = WeaponCatalog((PISTOL, RIFLE, SMG))
DEFAULT_WAVE_PLAN = SurvivalWavePlan(
    (
        EnemyWaveRule(WALKER, 5, growth=2),
        EnemyWaveRule(RUNNER, 2, growth=1, starts_at=3),
        EnemyWaveRule(BREAKER, 1, starts_at=5),
    ),
    25,
)


@dataclass(frozen=True, slots=True)
class MoveSurvivor:
    direction: tuple[float, float]


@dataclass(frozen=True, slots=True)
class FireSurvivorWeapon:
    aim: tuple[float, float]


@dataclass(frozen=True, slots=True)
class HoldSurvivorWeapon:
    aim: tuple[float, float]


@dataclass(frozen=True, slots=True)
class ReloadSurvivorWeapon:
    pass


@dataclass(frozen=True, slots=True)
class SelectSurvivorWeapon:
    """Select a zero-based firearm slot without exposing input details to rules."""

    slot: int


@dataclass(frozen=True, slots=True)
class UseSurvivorTool:
    """Equip the configured tool; left-click then uses it as the active weapon."""

    pass


@dataclass(frozen=True, slots=True)
class UseHealthPack:
    pass


@dataclass(frozen=True, slots=True)
class InteractSurvivor:
    pass


class SurvivalMode:
    """Shared-runtime Survival state with repeatable escalating waves."""

    def __init__(
        self,
        spawn_sources=(),
        enemy_count=None,
        preparation_seconds=None,
        initial_preparation_seconds=0,
        wave_plan=None,
        firearm_slots=2,
        tool_definition=PICKAXE,
        balance=None,
        starting_firearm=RIFLE,
        spawn_director_policy=None,
    ):
        self.balance = load_survival_balance() if balance is None else balance
        self.walker = ActorDefinition(
            "walker",
            "walker",
            "horde",
            config.ZOMBIE_HEALTH,
            (56, 56),
            self.balance.walker_speed,
        )
        self.runner = ActorDefinition(
            "runner", "runner", "horde", 70, (42, 42), self.balance.runner_speed
        )
        self.breaker = ActorDefinition(
            "breaker",
            "breaker",
            "horde",
            260,
            (64, 64),
            self.balance.breaker_speed,
        )
        self.rifle = WeaponDefinition(
            "survivor_rifle", "ballistic", config.BULLET_DAMAGE, 6.0,
            self.balance.starting_magazine, self.balance.starting_reserve,
            config.RELOAD_SECONDS, "556",
            max_range=1300,
            effective_range=800,
            minimum_damage_fraction=0.7,
        )
        self.spawn_sources = tuple(spawn_sources)
        selected_plan = (
            SurvivalWavePlan(
                (
                    EnemyWaveRule(self.walker, 5, growth=2),
                    EnemyWaveRule(self.runner, 2, growth=1, starts_at=3),
                    EnemyWaveRule(self.breaker, 1, starts_at=5),
                ),
                self.balance.preparation_seconds,
            )
            if wave_plan is None
            else wave_plan
        )
        entries = selected_plan.entries
        if enemy_count is not None:
            entries = (EnemyWaveRule(self.walker, enemy_count, growth=1, exponent=2),)
        self.wave_plan = SurvivalWavePlan(
            entries,
            selected_plan.preparation_seconds
            if preparation_seconds is None
            else preparation_seconds,
        )
        if initial_preparation_seconds < 0:
            raise ValueError("initial_preparation_seconds cannot be negative")
        self.initial_preparation_seconds = initial_preparation_seconds
        if firearm_slots < 1:
            raise ValueError("firearm_slots must be at least one")
        self.firearm_slots = firearm_slots
        self.player_id = None
        self.enemy_ids = ()
        self.spawn_director = SpawnDirector(
            SpawnDirectorPolicy(
                self.balance.spawn_burst_size,
                self.balance.spawn_burst_interval_seconds,
                self.balance.spawn_activation_delay_seconds,
            )
            if spawn_director_policy is None
            else spawn_director_policy
        )
        self.entry_remaining = {}
        self.retired_enemy_ids = ()
        self.spawn_results = ()
        self.loadouts = {}
        self.tool_slots = {}
        self.tool_definition = tool_definition
        self.starting_firearm = starting_firearm
        self.tool_equipped = False
        self.attacks = AttackDescriptionService()
        self.cash = SurvivalWallet()
        self.interactions = InteractionService()
        self.interaction_context = None
        self.interaction_result = None
        self.purchase_result = None
        self.weapon_purchases = WeaponPurchaseService()
        self.station_purchases = StationPurchaseService()
        self.station_result = None
        self.consumable_purchases = ConsumablePurchaseService()
        self.consumable_purchase_result = None
        self.harvesting = HarvestingService()
        self.harvestables = {}
        self.harvest_result = None
        self.harvest_context = None
        self.resources = ResourceInventory()
        self.consumables = ConsumableInventory()
        self.health_pack_result = None
        self.construction = ConstructionService()
        self.barricades = {}
        self.construction_result = None
        self.wave = 1
        self.phase = "combat"
        self.preparation_remaining = 0.0
        self.first_wave_pending = False
        self.disposed = False

    def start(self, match):
        width, height = match.map_definition.size
        common = {
            "bounds": Aabb(0, 0, width, height),
            "collision": match.map_definition.collision,
            "playable_areas": match.map_definition.playable_areas,
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
        self.player_id = player.actor_ids[0] if player.actor_ids else None
        if self.player_id is not None:
            entries = (
                ()
                if self.starting_firearm is None
                else (EquippedWeapon(self.starting_firearm),)
            )
            self.loadouts[self.player_id] = Loadout(
                entries, capacity=self.firearm_slots
            )
            self.tool_slots[self.player_id] = ToolSlot(
                None
                if self.tool_definition is None
                else EquippedWeapon(self.tool_definition)
            )
            self.tool_equipped = (
                self.tool_slots[self.player_id].equipped is not None
                and self.starting_firearm is None
            )
        self.first_wave_pending = self.initial_preparation_seconds > 0
        self.phase = "preparation" if self.first_wave_pending else "combat"
        self.preparation_remaining = self.initial_preparation_seconds
        enemy_batches = () if self.first_wave_pending else self._spawn_wave(match)
        self.harvestables = self.harvesting.create_states(
            match.map_definition.harvestables
        )
        self.barricades = self.construction.create_states(
            match.map_definition.construction_anchors
        )
        self._refresh_interaction(match)
        self._refresh_harvest_context(match)
        self.spawn_results = (
            player.spawn_result,
            *(batch.spawn_result for batch in enemy_batches),
        )

    def _spawn_wave(self, match):
        self.spawn_director.queue(
            SpawnBudget(entry.actor, entry.count_for(self.wave))
            for entry in self.wave_plan.entries
        )
        self.phase = "combat"
        self.preparation_remaining = 0.0
        return self._release_spawns(match, self.spawn_director.advance(0.0))

    @property
    def pending_spawns(self):
        return self.spawn_director.pending

    def _release_spawns(self, match, releases):
        return tuple(
            batch
            for release in releases
            for batch in (self._spawn_release(match, release),)
        )

    def _spawn_release(self, match, release):
        width, height = match.map_definition.size
        definition = release.definition
        batch = spawn_match_actors(
            match,
            SpawnActorRequest(
                definition,
                SpawnQuery(
                    role="enemy",
                    faction=definition.faction,
                    actor_kind=definition.actor_kind,
                ),
                PlacementConstraints(
                    footprint=definition.collision_size,
                    minimum_occupant_distance=max(definition.collision_size),
                    bounds=Aabb(0, 0, width, height),
                    reference=(
                        match.spatial.get(self.player_id).transform.x,
                        match.spatial.get(self.player_id).transform.y,
                    ),
                    minimum_distance=300,
                    visible_area=(
                        None
                        if width <= config.WINDOW[0] * 2
                        or height <= config.WINDOW[1] * 2
                        else Aabb(
                            match.spatial.get(self.player_id).transform.x
                            - config.WINDOW[0] / 2,
                            match.spatial.get(self.player_id).transform.y
                            - config.WINDOW[1] / 2,
                            *config.WINDOW,
                        )
                    ),
                    exclude_visible=(
                        width > config.WINDOW[0] * 2
                        and height > config.WINDOW[1] * 2
                    ),
                    collision=match.map_definition.collision,
                    playable_areas=match.map_definition.playable_areas,
                ),
                release.count,
            ),
            self.spawn_sources,
            f"survival-wave-{self.wave}-{definition.definition_id}-{release.sequence}",
            tags=("enemy",),
        )
        self.enemy_ids += batch.actor_ids
        self.entry_remaining.update(
            dict.fromkeys(batch.actor_ids, release.activation_delay_seconds)
        )
        self.spawn_results += (batch.spawn_result,)
        return batch

    def advance(self, match, commands, dt):
        if dt < 0:
            raise ValueError("dt cannot be negative")
        if self.result(match) is not None:
            return
        self._advance_weapons(dt)
        for actor_id in tuple(self.entry_remaining):
            remaining = max(0.0, self.entry_remaining[actor_id] - dt)
            if remaining == 0:
                del self.entry_remaining[actor_id]
            else:
                self.entry_remaining[actor_id] = remaining
        self._release_spawns(match, self.spawn_director.advance(dt))
        interaction_requested = False
        for command in commands:
            if isinstance(command, MoveSurvivor) and self.player_id is not None:
                move_match_actor(match, self.player_id, command.direction, dt)
            elif isinstance(command, FireSurvivorWeapon):
                self._fire_weapon(match, command.aim, pressed=True)
            elif isinstance(command, HoldSurvivorWeapon):
                selected = self._selected_weapon()
                if not self.tool_equipped and selected is not None:
                    self._fire_weapon(match, command.aim)
            elif isinstance(command, ReloadSurvivorWeapon):
                selected = self._selected_weapon()
                if not self.tool_equipped and selected is not None:
                    selected.reload()
            elif isinstance(command, SelectSurvivorWeapon):
                self._select_weapon(command.slot)
            elif isinstance(command, UseSurvivorTool):
                self.tool_equipped = (
                    self.tool_slots[self.player_id].equipped is not None
                )
            elif isinstance(command, UseHealthPack):
                if self.player_id is not None:
                    self.health_pack_result = self.consumables.use_health_pack(
                        "health_pack", 50, match.combat, self.player_id
                    )
            elif isinstance(command, InteractSurvivor):
                interaction_requested = True
        self._refresh_interaction(match)
        self._refresh_harvest_context(match)
        if interaction_requested:
            self.interaction_result = self.interactions.route_intent(
                self.player_id, self.interaction_context
            )
            self._execute_interaction(match)
        if self.phase == "combat":
            self._advance_enemies(match, dt)
            taking_contact_damage = self._apply_contact_damage(match, dt)
        else:
            taking_contact_damage = False
        if not taking_contact_damage:
            self._regenerate_health(match, dt)
        self._advance_waves(match, dt)

    def status(self, match):
        return SurvivalStatus(
            phase=self.phase,
            wave=self.wave,
            preparation_remaining=self.preparation_remaining,
            cash=self.cash.balance,
            enemies_remaining=self.enemies_remaining(match),
            active_equipment=self._active_equipment(),
            consumables=self.consumables.snapshot(),
            pending_enemies=self.spawn_director.remaining,
            outcome=self.result(match),
            enemy_composition=self._living_composition(match),
            interaction_context=self.interaction_context,
            interaction_result=self.interaction_result,
            purchase_result=self.purchase_result,
            station_result=self.station_result,
            consumable_purchase_result=self.consumable_purchase_result,
            health_pack_result=self.health_pack_result,
            harvest_result=self.harvest_result,
            harvest_context=self.harvest_context,
            resources=self.resources.snapshot(),
            construction_result=self.construction_result,
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

    def _regenerate_health(self, match, dt):
        if self.player_id is None or self.player_id not in match.combat:
            return
        match.combat.restore(
            self.player_id,
            health=self.balance.health_regeneration_per_second * dt,
        )

    def _advance_enemies(self, match, dt):
        if self.player_id is None or self.player_id not in match.spatial:
            return
        living = tuple(
            enemy_id
            for enemy_id in self.enemy_ids
            if enemy_id in match.combat and match.combat.get(enemy_id).alive
        )
        separate_overlapping_actors(
            match,
            living,
            self.construction.collision_obstacles(self.barricades),
        )
        for enemy_id in self.enemy_ids:
            if enemy_id not in match.spatial or not match.combat.get(enemy_id).alive:
                continue
            if enemy_id in self.entry_remaining:
                continue
            pursue_match_actor(
                match,
                enemy_id,
                self.player_id,
                dt,
                avoid_ids=(other for other in living if other != enemy_id),
                obstacles=self.construction.collision_obstacles(self.barricades),
            )
        self._apply_barricade_damage(match, dt)

    def _selected_weapon(self):
        return self.loadouts[self.player_id].selected

    def _active_equipment(self):
        if self.player_id is None:
            return None
        if self.tool_equipped:
            tool = self.tool_slots[self.player_id].equipped
            return None if tool is None else tool.definition.definition_id
        weapon = self._selected_weapon()
        return None if weapon is None else weapon.definition.definition_id

    def _select_weapon(self, slot):
        if self.player_id is None:
            return False
        selected = self.loadouts[self.player_id].select(slot)
        if selected:
            self.tool_equipped = False
        return selected

    def _select_fallback_equipment(self):
        if self.player_id is None:
            return
        alternate = self.loadouts[self.player_id].find(
            lambda weapon: weapon is not self._selected_weapon()
            and (weapon.runtime.loaded or 0) + (weapon.runtime.reserve or 0) > 0
        )
        if alternate is not None:
            self.loadouts[self.player_id].select_entry(alternate)
            self.tool_equipped = False
            return
        self.tool_equipped = self.tool_slots[self.player_id].equipped is not None

    def _advance_weapons(self, dt):
        if self.player_id is None:
            return
        for weapon in self.loadouts[self.player_id]:
            weapon.advance(dt)
        tool = self.tool_slots[self.player_id].equipped
        if tool is not None:
            tool.advance(dt)

    def _fire_weapon(self, match, aim, pressed=False):
        if self.player_id is None or math.hypot(*aim) == 0:
            return
        if self.tool_equipped:
            self._use_tool(match, aim)
            return
        weapon = self._selected_weapon()
        if weapon is None:
            return
        fired = weapon.trigger_pressed() if pressed else weapon.trigger_held()
        if not fired.accepted:
            if fired.status == NO_AMMO:
                self._select_fallback_equipment()
            return
        weapon.record_shot()
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
                    if enemy_id in match.combat
                    and match.combat.get(enemy_id).alive
                ),
                weapon.definition.max_range or config.BULLET_RANGE,
            )
            if target_id is None:
                continue
            result = match.damage.apply(
                DamageRequest(
                    attack.instigator_id,
                    self.player_id,
                    target_id,
                    damage_at_distance(
                        weapon.definition,
                        math.dist(
                            attack.origin,
                            (
                                match.spatial.get(target_id).transform.x,
                                match.spatial.get(target_id).transform.y,
                            ),
                        ),
                    ),
                    attack.attack_kind,
                    match.tick,
                    attack.weapon_id,
                )
            )
            self._award_kill(result)
        if fired.status == NO_AMMO:
            self._select_fallback_equipment()

    def _use_tool(self, match, aim):
        if self.player_id is None or math.hypot(*aim) == 0:
            return
        tool = self.tool_slots[self.player_id].equipped
        if tool is None:
            return
        used = tool.fire()
        if not used.accepted:
            return
        origin = match.spatial.get(self.player_id).transform
        harvestable = self.harvesting.nearest(
            self.harvestables, (origin.x, origin.y), tool.definition.reach or 0
        )
        if harvestable is not None:
            self.harvest_result = self.harvesting.harvest(tool, harvestable)
            if (
                self.harvest_result.success
                and self.harvest_result.resource_id is not None
                and self.harvest_result.resource_amount
            ):
                self.resources.add(
                    self.harvest_result.resource_id,
                    self.harvest_result.resource_amount,
                )
            return
        for attack in self.attacks.create(
            tool.definition,
            self.player_id,
            (origin.x, origin.y),
            aim,
            match.random_stream("survival-tool-attacks"),
        ):
            target_id = first_box_target_on_ray(
                match,
                attack.origin,
                attack.direction,
                (
                    enemy_id
                    for enemy_id in self.enemy_ids
                    if enemy_id in match.combat
                    and match.combat.get(enemy_id).alive
                ),
                attack.reach or 0,
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
            self.cash.increase_cash(self.balance.kill_reward)

    def _apply_contact_damage(self, match, dt):
        if dt == 0 or self.player_id is None or self.player_id not in match.spatial:
            return False
        player_state = match.spatial.get(self.player_id)
        if player_state.collision is None:
            return False
        player_box = actor_box(player_state.transform, player_state.collision)
        applied = False
        for enemy_id in self.enemy_ids:
            if enemy_id not in match.spatial or not match.combat.get(enemy_id).alive:
                continue
            enemy_state = match.spatial.get(enemy_id)
            if enemy_state.collision is None:
                continue
            enemy_box = actor_box(enemy_state.transform, enemy_state.collision)
            if overlaps(enemy_box, player_box):
                applied = True
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
        return applied

    def _apply_barricade_damage(self, match, dt):
        if dt == 0:
            return
        for state in self.barricades.values():
            if not state.built or state.anchor.area is None:
                continue
            for enemy_id in self.enemy_ids:
                if (
                    enemy_id not in match.spatial
                    or not match.combat.get(enemy_id).alive
                ):
                    continue
                enemy = match.spatial.get(enemy_id)
                if enemy.collision is None:
                    continue
                enemy_box = actor_box(enemy.transform, enemy.collision)
                obstacle = state.anchor.area
                in_contact = overlaps(enemy_box, obstacle)
                if isinstance(obstacle, Aabb):
                    in_contact = in_contact or overlaps(
                        enemy_box,
                        Aabb(
                            obstacle.x - 1,
                            obstacle.y - 1,
                            obstacle.width + 2,
                            obstacle.height + 2,
                        ),
                    )
                if not in_contact:
                    continue
                role = match.entities.get(enemy_id).definition_id
                multiplier = ENEMY_BARRICADE_DAMAGE.get(role, 1.0)
                self.construction.damage(
                    state, config.ZOMBIE_DAMAGE * multiplier * dt
                )

    def _advance_waves(self, match, dt):
        if self.result(match) is not None:
            return
        if self.phase == "combat":
            if not self.spawn_director.active and self.enemies_remaining(match) == 0:
                self.phase = "preparation"
                self.preparation_remaining = self.wave_plan.preparation_seconds
            return
        self._cleanup_defeated_enemies(match)
        self.preparation_remaining = max(0.0, self.preparation_remaining - dt)
        if self.preparation_remaining == 0:
            if self.first_wave_pending:
                self.first_wave_pending = False
                self._spawn_wave(match)
                return
            self.wave += 1
            self._spawn_wave(match)

    def _cleanup_defeated_enemies(self, match):
        defeated = tuple(
            enemy_id
            for enemy_id in self.enemy_ids
            if enemy_id in match.combat and not match.combat.get(enemy_id).alive
        )
        for enemy_id in defeated:
            remove_match_actor(match, enemy_id, reason="defeated")
        if defeated:
            retired = set(defeated)
            self.enemy_ids = tuple(
                enemy_id for enemy_id in self.enemy_ids if enemy_id not in retired
            )
            self.retired_enemy_ids += defeated

    def _living_composition(self, match):
        counts = {}
        for enemy_id in self.enemy_ids:
            if enemy_id not in match.combat or not match.combat.get(enemy_id).alive:
                continue
            definition_id = match.entities.get(enemy_id).definition_id
            counts[definition_id] = counts.get(definition_id, 0) + 1
        return tuple(sorted(counts.items()))

    def _refresh_interaction(self, match):
        if self.player_id is None or self.player_id not in match.spatial:
            self.interaction_context = None
            return
        position = match.spatial.get(self.player_id).transform
        self.interaction_context = self.interactions.discover(
            self.player_id,
            (position.x, position.y),
            (*match.map_definition.interactions, *self._anchor_interactions(match)),
            120,
        )

    def _refresh_harvest_context(self, match):
        if self.player_id is None or self.player_id not in match.spatial:
            self.harvest_context = None
            return
        tool = self.tool_slots[self.player_id].equipped
        position = match.spatial.get(self.player_id).transform
        self.harvest_context = self.harvesting.discover(
            self.harvestables,
            (position.x, position.y),
            0 if tool is None else tool.definition.reach or 0,
            tool,
        )

    def _anchor_interactions(self, match):
        return tuple(
            MapInteraction(
                anchor.anchor_id,
                "construction_anchor",
                anchor.position,
                anchor.area,
                anchor.tags,
                anchor.properties,
            )
            for anchor in match.map_definition.construction_anchors
        )

    def _execute_interaction(self, match):
        if self.interaction_result is None or not self.interaction_result.available:
            return
        if self.interaction_context.kind == "weapon_station":
            self.purchase_result = self.weapon_purchases.purchase(
                self.interaction_context.properties,
                SURVIVAL_WEAPONS,
                self.loadouts[self.player_id],
                self.cash,
            )
        elif self.interaction_context.kind in {
            "ammo_station",
            "health_station",
            "armor_station",
        }:
            self.station_result = self.station_purchases.purchase(
                self.interaction_context.kind,
                self.interaction_context.properties,
                self.loadouts[self.player_id],
                match.combat,
                self.player_id,
                self.cash,
            )
        elif self.interaction_context.kind == "health_pack_station":
            self.consumable_purchase_result = self.consumable_purchases.purchase(
                self.interaction_context.properties, self.consumables, self.cash
            )
        elif self.interaction_context.kind == "construction_anchor":
            state = self.barricades[self.interaction_context.interaction_id]
            self.construction_result = self.construction.build_or_repair(
                state, self.resources
            )
