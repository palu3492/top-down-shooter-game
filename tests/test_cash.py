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


# Known bugs are recorded only as strict xfails, never as plain asserts of the
# broken outcome -- one signal per bug, and it fires the moment AT5 fixes it.


@pytest.mark.xfail(strict=True, reason="rejects any purchase from a zero balance")
def test_zero_balance_should_still_allow_a_free_transaction(wallet):
    assert wallet.cash_add_remove(0) is True


@pytest.mark.xfail(strict=True, reason="rejects spending the balance exactly")
def test_spending_the_entire_balance_should_succeed(wallet):
    wallet.increase_cash(100)

    assert wallet.cash_add_remove(-100) is True
    assert wallet.cash_amount == 0


@pytest.mark.xfail(strict=True, reason="no sufficiency check; allows going negative")
def test_overspending_should_be_refused(wallet):
    wallet.increase_cash(100)

    assert wallet.cash_add_remove(-500) is False
    assert wallet.cash_amount == 100
