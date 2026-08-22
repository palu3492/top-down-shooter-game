"""Zombie Survival reactions to neutral attributed combat facts."""

from shooter import config
from shooter.domain_events import EntityKilled
from shooter.systems import loot


class SurvivalConsequences:
    def consume(self, events, player_id, entities, cash, spill):
        for event in events:
            if not isinstance(event, EntityKilled) or event.killer_id != player_id:
                continue
            target = entities.get(event.entity_id)
            cash.increase_cash(config.KILL_REWARD)
            for item, count in loot.spoils(target.kind):
                spill(item, count, target.get_position())

