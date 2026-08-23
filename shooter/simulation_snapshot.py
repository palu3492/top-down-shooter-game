"""Immutable, pygame-free views copied from authoritative Match state."""

from dataclasses import dataclass, fields, is_dataclass

from shooter.spatial import Box, Circle


class MutableSnapshotValueError(TypeError):
    pass


@dataclass(frozen=True, slots=True)
class CollisionSnapshot:
    kind: str
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class VitalSnapshot:
    health: float
    max_health: float
    armor: float
    max_armor: float
    alive: bool


@dataclass(frozen=True, slots=True)
class WeaponSnapshot:
    weapon_id: str
    attack_kind: str
    loaded: int | None
    reserve: int | None
    cooldown_remaining: float
    reload_remaining: float
    ready: bool
    status: str | None
    selected: bool


@dataclass(frozen=True, slots=True)
class EntitySnapshot:
    entity_id: int
    tags: frozenset[str]
    faction: str | None
    position: tuple[float, float] | None
    collision: CollisionSnapshot | None
    vitality: VitalSnapshot | None
    weapons: tuple[WeaponSnapshot, ...] = ()
    tool: WeaponSnapshot | None = None


@dataclass(frozen=True, slots=True)
class MatchSnapshot:
    mode_id: str
    map_id: str
    seed: int
    state: str
    tick: int
    entities: tuple[EntitySnapshot, ...]
    mode_status: object | None = None
    result: object | None = None

    def entity(self, entity_id):
        return next(item for item in self.entities if item.entity_id == entity_id)


def build_match_snapshot(
    match, *, loadouts=None, tools=None, mode_status=None, result=None
):
    """Copy one coherent presentation view without exposing mutable stores."""
    _require_immutable(mode_status, "mode_status")
    _require_immutable(result, "result")
    loadouts = {} if loadouts is None else loadouts
    tools = {} if tools is None else tools
    entities = tuple(
        _entity_snapshot(
            match, entity_id, loadouts.get(entity_id), tools.get(entity_id)
        )
        for entity_id in match.entities.ids()
    )
    return MatchSnapshot(
        mode_id=match.configuration.mode_id,
        map_id=match.configuration.map_id,
        seed=match.configuration.seed,
        state=match.state,
        tick=match.tick,
        entities=entities,
        mode_status=mode_status,
        result=result,
    )


def _entity_snapshot(match, entity_id, loadout, tool_slot):
    spatial = match.spatial.get(entity_id) if entity_id in match.spatial else None
    vital = match.combat.get(entity_id) if entity_id in match.combat else None
    return EntitySnapshot(
        entity_id=int(entity_id),
        tags=match.entities.tags_for(entity_id),
        faction=match.factions.faction_of(entity_id),
        position=(
            None
            if spatial is None
            else (spatial.transform.x, spatial.transform.y)
        ),
        collision=None if spatial is None else _collision_snapshot(spatial.collision),
        vitality=(
            None
            if vital is None
            else VitalSnapshot(
                vital.health,
                vital.max_health,
                vital.armor,
                vital.max_armor,
                vital.alive,
            )
        ),
        weapons=() if loadout is None else _weapon_snapshots(loadout),
        tool=None if tool_slot is None else _tool_snapshot(tool_slot),
    )


def _collision_snapshot(collision):
    if collision is None:
        return None
    if isinstance(collision, Box):
        return CollisionSnapshot(
            "box",
            (
                collision.width,
                collision.height,
                collision.offset_x,
                collision.offset_y,
            ),
        )
    if isinstance(collision, Circle):
        return CollisionSnapshot(
            "circle", (collision.radius, collision.offset_x, collision.offset_y)
        )
    raise TypeError(f"unsupported collision snapshot: {type(collision).__name__}")


def _weapon_snapshots(loadout):
    selected = loadout.selected_index
    return tuple(
        WeaponSnapshot(
            weapon_id=held.definition.definition_id,
            attack_kind=held.definition.attack_kind,
            loaded=held.runtime.loaded,
            reserve=held.runtime.reserve,
            cooldown_remaining=held.runtime.cooldown_remaining,
            reload_remaining=held.runtime.reload_remaining,
            ready=held.ready,
            status=held.status,
            selected=index == selected,
        )
        for index, held in enumerate(loadout)
    )


def _tool_snapshot(tool_slot):
    held = tool_slot.equipped
    if held is None:
        return None
    return WeaponSnapshot(
        weapon_id=held.definition.definition_id,
        attack_kind=held.definition.attack_kind,
        loaded=held.runtime.loaded,
        reserve=held.runtime.reserve,
        cooldown_remaining=held.runtime.cooldown_remaining,
        reload_remaining=held.runtime.reload_remaining,
        ready=held.ready,
        status=held.status,
        selected=True,
    )


def _require_immutable(value, field_name):
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, (tuple, frozenset)):
        for item in value:
            _require_immutable(item, field_name)
        return
    parameters = getattr(type(value), "__dataclass_params__", None)
    if is_dataclass(value) and parameters is not None and parameters.frozen:
        for item in fields(value):
            _require_immutable(getattr(value, item.name), field_name)
        return
    raise MutableSnapshotValueError(
        f"{field_name} must be an immutable value, got {type(value).__name__}"
    )
