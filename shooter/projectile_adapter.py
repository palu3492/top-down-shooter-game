"""The single pygame adapter from neutral attacks to current attack sprites."""

from shooter.entities.projectiles import GUN_SHOT, Shot, Swing, play


def adapt_attacks(descriptions):
    descriptions = tuple(descriptions)
    if descriptions and descriptions[0].attack_kind == "ballistic":
        play(GUN_SHOT)
    return tuple(_adapt(description) for description in descriptions)


def _adapt(description):
    if description.attack_kind == "ballistic":
        attack = Shot(
            *description.origin,
            *description.direction,
            damage=description.damage,
        )
    elif description.attack_kind == "melee":
        attack = Swing(
            *description.origin,
            *description.direction,
            damage=description.damage,
            reach=description.reach,
            arc=description.arc,
        )
    else:
        raise ValueError(f"unknown attack kind: {description.attack_kind}")
    attack.instigator_id = description.instigator_id
    attack.weapon_id = description.weapon_id
    return attack
