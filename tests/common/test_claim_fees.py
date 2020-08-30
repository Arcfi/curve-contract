import brownie
import pytest

MAX_FEE = 5 * 10**9


def get_admin_balances(swap, wrapped_coins):
    admin_balances = []
    for i, coin in enumerate(wrapped_coins):
        if hasattr(swap, "admin_balances"):
            admin_balances.append(swap.admin_balances(i))
        else:
            admin_balances.append(coin.balanceOf(swap) - swap.balances(i))

    return admin_balances


@pytest.fixture(scope="module", autouse=True)
def setup(chain, alice, bob, wrapped_coins, swap, initial_amounts):
    for coin, amount in zip(wrapped_coins, initial_amounts):
        coin._mint_for_testing(alice, amount, {'from': alice})
        coin._mint_for_testing(bob, amount, {'from': bob})
        coin.approve(swap, 2**256-1, {'from': alice})
        coin.approve(swap, 2**256-1, {'from': bob})

    swap.add_liquidity(initial_amounts, 0, {'from': alice})

    if hasattr(swap, "commit_new_fee"):
        swap.commit_new_fee(MAX_FEE, MAX_FEE, {'from': alice})
        chain.sleep(86400*3)
        swap.apply_new_fee({'from': alice})
    else:
        swap.commit_new_parameters(360 * 2, MAX_FEE, MAX_FEE, {'from': alice})
        chain.sleep(86400*3)
        swap.apply_new_parameters({'from': alice})


def test_admin_balances(alice, bob, swap, wrapped_coins, initial_amounts):
    for send, recv in [(0, 1), (1, 0)]:
        swap.exchange(send, recv, initial_amounts[send], 0, {'from': bob})

    for i in range(2):
        admin_fee = wrapped_coins[i].balanceOf(swap) - swap.balances(i)
        assert admin_fee > 0
        assert admin_fee + swap.balances(i) == wrapped_coins[i].balanceOf(swap)


@pytest.mark.itercoins("sending", "receiving")
def test_withdraw_one_coin(alice, bob, swap, wrapped_coins, sending, receiving, initial_amounts):

    swap.exchange(sending, receiving, initial_amounts[sending], 0, {'from': bob})

    admin_balances = get_admin_balances(swap, wrapped_coins)

    assert admin_balances[receiving] > 0
    assert sum(admin_balances) == admin_balances[receiving]

    swap.withdraw_admin_fees({'from': alice})
    assert wrapped_coins[receiving].balanceOf(alice) == admin_balances[receiving]

    assert swap.balances(receiving) == wrapped_coins[receiving].balanceOf(swap)


def test_withdraw_all_coins(alice, bob, swap, wrapped_coins, initial_amounts):
    for send, recv in [(0, 1), (1, 0)]:
        swap.exchange(send, recv, initial_amounts[send], 0, {'from': bob})

    admin_balances = get_admin_balances(swap, wrapped_coins[:2])

    swap.withdraw_admin_fees({'from': alice})
    balances = [i.balanceOf(alice) for i in wrapped_coins[:2]]

    assert admin_balances == balances


def test_withdraw_only_owner(bob, swap):
    with brownie.reverts():
        swap.withdraw_admin_fees({'from': bob})


# def test_donate(alice, bob, swap, wrapped_coins, initial_amounts):
#     for send, recv in [(0, 1), (1, 0)]:
#         swap.exchange(send, recv, initial_amounts[send], 0, {'from': bob})

#     swap.donate_admin_fees({'from': alice})

#     assert sum(get_admin_balances(swap, wrapped_coins)) == 0
#     assert sum(i.balanceOf(alice) for i in wrapped_coins) == 0


def test_donate_only_owner(bob, swap):
    with brownie.reverts():
        swap.withdraw_admin_fees({'from': bob})
