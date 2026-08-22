"""What the dead leave behind.

The pickup, the bulk rule and the taking all came with AT43. This is the drop
table, and the question of *which* departures count as a death.
"""

import pytest

from shooter import config, items
from shooter.entities.projectiles import Swing
from shooter.session import Session
from shooter.systems import loot, world
from shooter.viewport import Viewport

WINDOW = (1080, 720)
IDLE = dict.fromkeys(range(512), False)


class Rigged:
    """Dice that land where the test says."""

    def __init__(self, throw=0.0, count=1):
        self.throw = throw
        self.count = count

    def random(self):
        return self.throw

    def randint(self, least, most):
        assert least <= self.count <= most, (least, self.count, most)
        return self.count


@pytest.fixture
def game(display):
    return Session(Viewport(WINDOW))


def cut_down(session, how_many=None):
    """Kill zombies the way the game does -- inside a step, by a weapon.

    Set in *world* coordinates: `_advance_zombies` runs before the swing does
    and recomputes every rect from those, so anything put straight into a rect
    is gone before the blow lands.
    """
    here = (
        WINDOW[0] / 2 - session.camera_x,
        WINDOW[1] / 2 - session.camera_y,
    )
    standing = list(session.zombies)[: how_many or len(session.zombies)]
    for index, zombie in enumerate(standing):
        zombie.set_position(here[0] + 20 + index * 12, here[1] + 20)
        zombie.zombie_health = 5
    session.bullets.add(
        Swing(
            WINDOW[0] / 2 - session.camera_x,
            WINDOW[1] / 2 - session.camera_y,
            1,
            0,
            damage=999,
            reach=600,
            arc=360,
        )
    )
    session.step(IDLE, config.SIM_DT)
    return standing


# ----------------------------------------------------------------------
# The table
# ----------------------------------------------------------------------


def test_a_line_that_wins_its_roll_drops_its_count():
    line = loot.Drop(world.CLOTH, 2, 4, 0.5)

    assert line.roll(Rigged(throw=0.1, count=3)) == 3


def test_a_line_that_loses_its_roll_drops_nothing():
    line = loot.Drop(world.CLOTH, 2, 4, 0.5)

    assert line.roll(Rigged(throw=0.9)) == 0


def test_a_roll_exactly_on_the_chance_is_a_miss():
    """`chance` is the share of corpses that drop it, so 0.5 must not be both
    the last hit and the first miss."""
    line = loot.Drop(world.CLOTH, 1, 1, 0.5)

    assert line.roll(Rigged(throw=0.5)) == 0
    assert line.roll(Rigged(throw=0.49999)) == 1


def test_spoils_returns_what_won_its_roll():
    won = loot.spoils("walker", Rigged(throw=0.0, count=1))

    assert [item for item, _ in won] == [world.CLOTH, world.METAL]
    assert all(count == 1 for _, count in won)


def test_nothing_at_all_is_a_perfectly_good_answer():
    """Loot that drops every time is not loot, it is a wage."""
    assert loot.spoils("walker", Rigged(throw=1.0)) == ()


def test_a_kind_with_no_table_drops_nothing():
    assert loot.spoils("brute", Rigged(throw=0.0)) == ()


def test_every_line_names_an_item_the_game_knows():
    for kind, table in loot.TABLE.items():
        for line in table:
            assert items.item(line.item.id) is line.item, kind
            assert line.item.id in world.LOOKS, "nothing to draw it with"
            assert 1 <= line.least <= line.most
            assert 0 < line.chance <= 1


def test_the_kind_a_zombie_says_it_is_has_a_table(display, cash):
    from shooter.entities.zombie import Zombie

    assert Zombie(WINDOW, cash).kind in loot.TABLE


# ----------------------------------------------------------------------
# Off the corpse
# ----------------------------------------------------------------------


def test_cutting_one_down_leaves_what_it_carried(game, monkeypatch):
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 3),))

    cut_down(game, 1)

    assert len(game.dropped) == 1
    pile = next(iter(game.dropped))
    assert (pile.item, pile.count) == (world.CLOTH, 3)


def test_loot_lands_where_the_zombie_fell(game, monkeypatch):
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 1),))

    (fallen,) = cut_down(game, 1)

    pile = next(iter(game.dropped))
    assert pile.middle == pytest.approx(fallen.get_position(), abs=1)


def test_a_crowd_leaves_piles_rather_than_litter(game, monkeypatch):
    """Five corpses close together is not five sprites per item. The bulk rule
    from AT43 does the work."""
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 2),))

    felled = cut_down(game)

    assert len(felled) > 2
    assert len(game.dropped) == 1
    assert next(iter(game.dropped)).count == 2 * len(felled)


def test_a_zombie_still_standing_has_dropped_nothing(game, monkeypatch):
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 3),))

    game.step(IDLE, config.SIM_DT)

    assert len(game.dropped) == 0


def test_a_nuke_going_off_mid_step_carpets_nothing(game, monkeypatch):
    """The real path: the group is emptied *during* a step, after the snapshot
    has been taken, which is the only moment the guard can matter."""
    from shooter.entities import powerups

    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 3),))
    for pickup in game.powerups:
        pickup.powerup_selected = powerups.NUKE
        monkeypatch.setattr(
            pickup, "update", lambda *args, **kwargs: powerups.NUKE, raising=False
        )
    assert game.zombies

    game.step(IDLE, config.SIM_DT)

    assert len(game.zombies) == 0, "the nuke did not go off"
    assert len(game.dropped) == 0


def test_loot_is_still_paid_for_in_coins(game, monkeypatch):
    """Killing already paid cash. Loot is as well as, not instead of."""
    monkeypatch.setattr(loot, "spoils", lambda kind: ())

    felled = cut_down(game)

    assert game.cash.cash_amount == config.KILL_REWARD * len(felled)


def test_what_a_corpse_leaves_can_be_picked_up(game, monkeypatch):
    """End to end: cut one down, walk over what it left, carry it."""
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.METAL, 4),))
    cut_down(game, 1)
    pile = next(iter(game.dropped))

    game.camera_x = WINDOW[0] / 2 - pile.middle[0]
    game.camera_y = WINDOW[1] / 2 - pile.middle[1]
    game.step(IDLE, config.SIM_DT)

    assert game.backpack.count(world.METAL) == 4
    assert game.notice == "+4 METAL"


def test_a_real_wave_drops_something_worth_having(game):
    """Unrigged, so the declared chances have to actually fire."""
    piles = 0
    for _ in range(30):
        made = Session(Viewport(WINDOW))
        cut_down(made)
        piles += len(made.dropped)

    assert piles > 0, "thirty waves and nothing dropped at all"
