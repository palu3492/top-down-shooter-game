"""Buying a gun from a stand you have to walk to.

Two halves: what a purchase does to the money and the loadout, and what
standing next to the thing on the map means. The second half is the interaction
layer AT42 builds harvesting on, so it is tested as its own thing rather than as
a detail of shopping.
"""

import math

import pygame
import pytest

from shooter import config, weapons
from shooter.entities.props import Prop
from shooter.session import SLOT_KEYS, Session
from shooter.systems import shop, world
from shooter.ui.hud import Cash
from shooter.viewport import Viewport

WINDOW = (1080, 720)
M16 = shop.STOCK[0]
SNIPER = shop.STOCK[3]


@pytest.fixture
def wallet():
    return Cash()


@pytest.fixture
def carried():
    return [weapons.equip(weapons.KNIFE)]


@pytest.fixture
def game(display):
    return Session(Viewport(WINDOW))


def the_stand(session):
    return next(prop for prop in session.props if prop.label == "GUN STAND")


def at_the_stand(session):
    stand = the_stand(session)
    session.camera_x = session.window[0] / 2 - stand.middle[0]
    session.camera_y = session.window[1] / 2 - stand.middle[1]
    return session


def press(session, key):
    session.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def step(session, seconds=config.SIM_DT):
    idle = dict.fromkeys(range(512), False)
    for _ in range(max(1, int(seconds * config.SIM_HZ))):
        session.step(idle, config.SIM_DT)


# ----------------------------------------------------------------------
# The money
# ----------------------------------------------------------------------


def test_buying_a_gun_costs_its_price_and_hands_it_over(wallet, carried):
    wallet.increase_cash(M16.price)

    assert shop.buy(M16, wallet, carried) == shop.BOUGHT
    assert wallet.cash_amount == 0
    assert [held.weapon.id for held in carried] == [weapons.KNIFE.id, M16.weapon]


def test_a_bought_gun_arrives_loaded(wallet, carried):
    wallet.increase_cash(M16.price)
    shop.buy(M16, wallet, carried)

    bought = carried[-1]
    assert bought.loaded == bought.weapon.clip
    assert bought.reserve == bought.weapon.reserve


def test_a_gun_you_cannot_afford_is_not_sold(wallet, carried):
    wallet.increase_cash(M16.price - 1)

    assert shop.buy(M16, wallet, carried) == shop.TOO_POOR
    assert wallet.cash_amount == M16.price - 1, "a refusal must not cost anything"
    assert len(carried) == 1


def test_buying_one_you_already_carry_buys_its_ammunition(wallet, carried):
    wallet.increase_cash(M16.price + M16.ammo)
    shop.buy(M16, wallet, carried)
    rifle = carried[-1]
    rifle.reserve = 0

    assert shop.buy(M16, wallet, carried) == shop.REFILLED
    assert rifle.reserve == rifle.weapon.reserve
    assert wallet.cash_amount == 0
    assert len(carried) == 2, "the second sale is ammunition, not a second gun"


def test_ammunition_is_cheaper_than_the_gun(wallet, carried):
    assert all(offer.ammo < offer.price for offer in shop.STOCK)
    assert shop.price_of(M16, carried) == M16.price

    wallet.increase_cash(M16.price)
    shop.buy(M16, wallet, carried)

    assert shop.price_of(M16, carried) == M16.ammo


def test_a_full_gun_is_not_sold_ammunition_it_cannot_hold(wallet, carried):
    wallet.increase_cash(M16.price + M16.ammo)
    shop.buy(M16, wallet, carried)
    spent = wallet.cash_amount

    assert shop.buy(M16, wallet, carried) == shop.STOCKED
    assert wallet.cash_amount == spent


def test_a_weapon_that_will_not_fit_is_not_charged_for(wallet, carried):
    """Five slots, and today five weapons -- so a full loadout already holds
    everything and this cannot happen in play. It can the moment AT40.1 adds a
    sixth, which is what the guard is for. Filled with knives so the sniper is
    genuinely a new gun rather than an ammunition sale."""
    while len(carried) < weapons.MAX_SLOTS:
        carried.append(weapons.equip(weapons.KNIFE))
    wallet.increase_cash(10_000)
    rich = wallet.cash_amount

    assert shop.carrying(carried, SNIPER) is None
    assert shop.buy(SNIPER, wallet, carried) == shop.NO_ROOM
    assert wallet.cash_amount == rich
    assert len(carried) == weapons.MAX_SLOTS


def test_the_sign_and_the_price_agree():
    """`gun_on_wall.png` has $500 painted on it, so that is what the rifle
    costs. Changing one without the other makes the art a lie."""
    assert M16.price == 500
    assert M16.weapon == weapons.M16.id


def test_every_weapon_but_the_knife_is_for_sale():
    for_sale = {offer.weapon for offer in shop.STOCK}
    assert for_sale == set(weapons.weapon_ids()) - {weapons.KNIFE.id}


def test_there_is_a_line_on_the_panel_for_every_offer():
    """The panel is worked by the number keys, so an offer past the fifth would
    be unreachable rather than merely unlisted."""
    assert len(shop.STOCK) <= len(SLOT_KEYS)


# ----------------------------------------------------------------------
# Standing next to it
# ----------------------------------------------------------------------


def test_a_prop_offers_itself_only_from_close_enough(display):
    stand = Prop(world.STAND_SPRITE, 1000, 1000, label="GUN STAND")
    middle = stand.middle

    assert stand.within(middle)
    assert stand.within((middle[0] + stand.reach - 1, middle[1]))
    assert not stand.within((middle[0] + stand.reach + 1, middle[1]))


def test_reach_is_measured_from_the_middle_not_the_corner(display):
    """A wide prop must not be easier to reach along its length than across
    it."""
    stand = Prop(world.STAND_SPRITE, 1000, 1000)
    middle = stand.middle
    step_out = stand.reach - 1

    for angle in range(0, 360, 30):
        at = (
            middle[0] + step_out * math.cos(math.radians(angle)),
            middle[1] + step_out * math.sin(math.radians(angle)),
        )
        assert stand.within(at), angle


def test_the_stand_is_standing_in_the_world(game):
    placed = next(one for one in world.STARTER if one.kind == world.STAND)
    stand = the_stand(game)

    assert (stand.prop_x, stand.prop_y) == placed.at
    assert game.nearby is None, "not at the opening corner"


def test_walking_up_to_it_offers_it(game):
    at_the_stand(game)
    assert game.nearby is not None
    assert game.nearby.label == "GUN STAND"


def test_e_opens_it_and_e_closes_it(game):
    at_the_stand(game)

    press(game, pygame.K_e)
    assert game.shopping is True

    press(game, pygame.K_e)
    assert game.shopping is False


def test_e_does_nothing_when_there_is_nothing_to_use(game):
    press(game, pygame.K_e)
    assert game.shopping is False


def test_walking_away_closes_it(game):
    at_the_stand(game)
    press(game, pygame.K_e)
    assert game.shopping is True

    game.camera_x = 0
    game.camera_y = 0
    step(game)

    assert game.shopping is False


# ----------------------------------------------------------------------
# Shopping while the wave is still coming
# ----------------------------------------------------------------------


def test_the_game_does_not_stop_while_the_stand_is_open(game):
    """The whole reason this is an overlay and not a scene: a scene on top of
    gameplay is what pausing is, and standing still to shop is meant to cost
    something."""
    at_the_stand(game)
    press(game, pygame.K_e)
    before = [zombie.get_position() for zombie in game.zombies]

    step(game, 0.5)

    assert game.shopping is True
    assert [zombie.get_position() for zombie in game.zombies] != before


def test_the_number_keys_buy_rather_than_equip_while_it_is_open(game):
    at_the_stand(game)
    game.cash.increase_cash(M16.price)
    press(game, pygame.K_e)

    press(game, pygame.K_1)

    assert game.shop_says == shop.BOUGHT
    assert game.equipped.weapon.id == weapons.KNIFE.id, "buying is not equipping"
    assert [held.weapon.id for held in game.carried] == [
        weapons.KNIFE.id,
        weapons.M16.id,
    ]


def test_the_number_keys_go_back_to_equipping_once_it_is_closed(game):
    at_the_stand(game)
    game.cash.increase_cash(M16.price)
    press(game, pygame.K_e)
    press(game, pygame.K_1)
    press(game, pygame.K_e)

    press(game, pygame.K_2)

    assert game.equipped.weapon.id == weapons.M16.id


def test_both_hands_are_busy_while_the_stand_is_open(game):
    at_the_stand(game)
    game.aim_at((900, 300))
    press(game, pygame.K_e)

    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert len(game.bullets) == 0


def test_a_line_with_nothing_behind_it_does_nothing(game):
    at_the_stand(game)
    press(game, pygame.K_e)

    press(game, SLOT_KEYS[len(shop.STOCK)])

    assert game.shop_says is None
    assert len(game.carried) == 1


# ----------------------------------------------------------------------
# The stand and the dev cheat, which landed separately
# ----------------------------------------------------------------------


def test_the_cheat_is_a_way_past_the_stand_as_well(game):
    """`0` was written when the loadout started full. Now that a game starts
    with a knife it is also how you skip shopping, which is what a dev cheat is
    for."""
    assert [held.weapon.id for held in game.carried] == [weapons.KNIFE.id]

    press(game, pygame.K_0)

    assert len(game.carried) == weapons.MAX_SLOTS


def test_the_cheat_is_off_while_the_stand_is_open(game):
    """Every key goes to the panel while it is up; the number keys buy and
    nothing else fires. `0` is no exception."""
    at_the_stand(game)
    press(game, pygame.K_e)

    press(game, pygame.K_0)

    assert len(game.carried) == 1
    assert game.shop_says is None


def test_buying_what_the_cheat_gave_you_buys_ammunition(game):
    at_the_stand(game)
    press(game, pygame.K_0)
    rifle = game.carried[1]
    rifle.reserve = 0
    game.cash.increase_cash(M16.price)
    press(game, pygame.K_e)

    press(game, pygame.K_1)

    assert game.shop_says == shop.REFILLED
    assert rifle.reserve == rifle.weapon.reserve
    assert game.cash.cash_amount == M16.price - M16.ammo
