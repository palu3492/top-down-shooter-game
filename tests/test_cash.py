import pytest

from shooter.ui.hud import Cash


@pytest.fixture
def wallet():
    return Cash()


def test_starts_empty(wallet):
    assert wallet.cash_amount == 0


def test_kills_pay_out(wallet):
    wallet.increase_cash(50)
    wallet.increase_cash(50)

    assert wallet.cash_amount == 100


def test_two_wallets_are_independent(wallet):
    wallet.increase_cash(50)

    assert Cash().cash_amount == 0


def test_affordable_purchase_succeeds(wallet):
    wallet.increase_cash(100)

    assert wallet.cash_add_remove(-40) is True
    assert wallet.cash_amount == 60


def test_zero_balance_allows_a_free_transaction(wallet):
    assert wallet.cash_add_remove(0) is True


def test_spending_the_entire_balance_succeeds(wallet):
    wallet.increase_cash(100)

    assert wallet.cash_add_remove(-100) is True
    assert wallet.cash_amount == 0


def test_overspending_is_refused(wallet):
    wallet.increase_cash(100)

    assert wallet.cash_add_remove(-500) is False
    assert wallet.cash_amount == 100
