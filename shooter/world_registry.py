"""Match-scoped entity identity and controlled world registration."""

from dataclasses import dataclass
from typing import NewType

from shooter.domain_events import EntityRegistered, EntityRemoved

EntityId = NewType("EntityId", int)


@dataclass(frozen=True, slots=True)
class EntityRecord:
    entity_id: EntityId
    entity: object
    tags: frozenset[str]


class WorldRegistry:
    """Assign stable IDs without depending on an entity's implementation type."""

    def __init__(self, events=None):
        self._next_id = 1
        self._records = {}
        self._ids_by_object = {}
        self._events = events

    def register(self, entity, tags=()):
        object_key = id(entity)
        existing = self._ids_by_object.get(object_key)
        if existing is not None:
            return existing

        entity_id = EntityId(self._next_id)
        self._next_id += 1
        self._records[entity_id] = EntityRecord(
            entity_id, entity, frozenset(tags)
        )
        self._ids_by_object[object_key] = entity_id
        if self._events is not None:
            self._events.publish(
                EntityRegistered(
                    entity_id, tuple(sorted(self._records[entity_id].tags))
                )
            )
        return entity_id

    def remove(self, entity_id, reason="removed"):
        record = self._records.pop(entity_id)
        self._ids_by_object.pop(id(record.entity), None)
        if self._events is not None:
            self._events.publish(EntityRemoved(entity_id, reason))
        return record.entity

    def get(self, entity_id):
        return self._records[entity_id].entity

    def id_for(self, entity):
        return self._ids_by_object.get(id(entity))

    def ids(self, tag=None):
        return tuple(
            entity_id
            for entity_id, record in self._records.items()
            if tag is None or tag in record.tags
        )

    def entities(self, tag=None):
        return tuple(self.get(entity_id) for entity_id in self.ids(tag))

    def __contains__(self, entity_id):
        return entity_id in self._records

    def __len__(self):
        return len(self._records)

    def clear(self):
        self._records.clear()
        self._ids_by_object.clear()
