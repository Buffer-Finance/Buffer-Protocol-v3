import brownie


def test_binary_pool(contracts, accounts, chain):

    tokenX = contracts["tokenX"]
    binary_pool_atm = contracts["binary_pool_atm"]
    owner = accounts[0]
    user_1 = accounts[1]
    user_2 = accounts[2]
    user_3 = accounts[3]
    user_5 = accounts[5]
    handler = accounts[9]
    tokenX_amount_1 = int(3 * 1e6) // 100
    tokenX_amount_2 = int(2 * 1e6) // 100
    tokenX_amount_3 = int(1 * 1e6) // 100
    MAX_INTEGER = 2**256 - 1
    ONE_DAY = 86400
    ADDRESS_0 = "0x0000000000000000000000000000000000000000"

    ############ Should verify the roles assigned by constructor ############
    OPTION_ISSUER_ROLE = binary_pool_atm.OPTION_ISSUER_ROLE()
    binary_pool_atm.grantRole(OPTION_ISSUER_ROLE, user_2, {"from": owner})
    assert (
        binary_pool_atm.hasRole(OPTION_ISSUER_ROLE, user_2) == True
    ), "Option Issuer Role verified"
    DEFAULT_ADMIN_ROLE = binary_pool_atm.DEFAULT_ADMIN_ROLE()
    assert (
        binary_pool_atm.hasRole(DEFAULT_ADMIN_ROLE, owner) == True
    ), "Default Admin Role verified"

    ############ Should verify setting maxLiquidity ############
    with brownie.reverts():  # Wrong role
        binary_pool_atm.setMaxLiquidity(5000000e6, {"from": user_1})
    maxLiquidity = 5000000 * 10 ** tokenX.decimals()
    binary_pool_atm.setMaxLiquidity(maxLiquidity, {"from": owner})
    assert binary_pool_atm.maxLiquidity() == maxLiquidity, "Wrong maxLiquidity"

    ############ Should verify functioning of the revoke call ############
    chain.snapshot()
    binary_pool_atm.revokeRole(DEFAULT_ADMIN_ROLE, owner, {"from": owner})
    assert (
        binary_pool_atm.hasRole(DEFAULT_ADMIN_ROLE, owner) == False
    ), "Default Admin Role should be revoked"
    chain.revert()

    ############ Should verify shareof with 0 supply############
    assert binary_pool_atm.shareOf(user_1) == 0, "Wrong share"

    ############ Should verify adding and removing liquidity ############
    # If amount of tokenx provided to the contract are X
    # If provider hasn't approved that much amount then it should revert

    with brownie.reverts(""):
        binary_pool_atm.provide(tokenX_amount_1, 0, {"from": user_1})

    with brownie.reverts("Pool has already reached it's max limit"):
        binary_pool_atm.provide(maxLiquidity * 2, 0, {"from": user_1})

    tokenX.transfer(user_1, tokenX_amount_1, {"from": owner})
    tokenX.approve(binary_pool_atm.address, tokenX_amount_1, {"from": user_1})

    initial_tokenX_balance_user1 = tokenX.balanceOf(user_1)
    initial_tokenX_balance_lp = tokenX.balanceOf(binary_pool_atm.address)

    with brownie.reverts("Pool: Amount is too small"):
        binary_pool_atm.provide(0, 0, {"from": user_1})

    with brownie.reverts("Pool: Mint limit is too large"):
        binary_pool_atm.provide(tokenX_amount_1, 1e18, {"from": user_1})

    provide = binary_pool_atm.provide(tokenX_amount_1 / 3, 0, {"from": user_1})

    liquidity_per_user = binary_pool_atm.liquidityPerUser(user_1)

    assert liquidity_per_user[0] == 0, "Unlocked amount should be 0"
    assert liquidity_per_user[1] == 0, "Latest index should be 0"

    expected_mint = binary_pool_atm.INITIAL_RATE() * tokenX_amount_1 / 3

    final_tokenX_balance_user1 = tokenX.balanceOf(user_1)
    final_tokenX_balance_lp = tokenX.balanceOf(binary_pool_atm.address)

    assert provide.events["Provide"], "No event triggered"
    assert binary_pool_atm.balanceOf(user_1) == expected_mint, "Wrong mint"

    assert (
        initial_tokenX_balance_user1 - final_tokenX_balance_user1 == tokenX_amount_1 / 3
    ), "Wrong user balance"
    assert (
        final_tokenX_balance_lp - initial_tokenX_balance_lp == tokenX_amount_1 / 3
    ), "Wrong lp balance"

    lockup_period = binary_pool_atm.lockupPeriod()
    assert lockup_period == 10 * 60, "Lock up period is 10 mins"

    chain.snapshot()

    with brownie.reverts(
        "Pool: Withdrawal amount is greater than current unlocked amount"
    ):
        binary_pool_atm.withdraw(tokenX_amount_1 / 3, {"from": user_1})

    chain.sleep(lockup_period + ONE_DAY)

    binary_pool_atm.provide(tokenX_amount_1 / 3, 0, {"from": user_1})

    assert expected_mint == binary_pool_atm.getUnlockedLiquidity(
        user_1
    ), "Unlocked amount shouldn't be 0"

    initial_tokenX_balance_user1 = tokenX.balanceOf(user_1)
    initial_tokenX_balance_lp = tokenX.balanceOf(binary_pool_atm.address)
    initial_blp_balance = binary_pool_atm.balanceOf(user_1)

    amount_to_withdraw = tokenX_amount_1 / 6

    with brownie.reverts(
        "Pool: Not enough funds on the pool contract. Please lower the amount."
    ):
        binary_pool_atm.withdraw(tokenX_amount_1 * 100, {"from": user_1})
    with brownie.reverts("Pool: Amount is too small"):
        binary_pool_atm.withdraw(0, {"from": user_1})

    with brownie.reverts("Pool: Amount is too small"):
        binary_pool_atm.withdraw(amount_to_withdraw, {"from": user_5})

    binary_pool_atm.withdraw(amount_to_withdraw, {"from": user_1})

    final_tokenX_balance_user1 = tokenX.balanceOf(user_1)
    final_tokenX_balance_lp = tokenX.balanceOf(binary_pool_atm.address)
    final_blp_balance = binary_pool_atm.balanceOf(user_1)

    assert (
        final_tokenX_balance_user1 - initial_tokenX_balance_user1 == amount_to_withdraw
    ), "Wrong user balance"
    assert (
        initial_tokenX_balance_lp - final_tokenX_balance_lp == amount_to_withdraw
    ), "Wrong lp balance"

    assert initial_blp_balance - final_blp_balance == (
        binary_pool_atm.INITIAL_RATE() * amount_to_withdraw
    ), "Wrong burn"

    liquidity_per_user = binary_pool_atm.liquidityPerUser(user_1)

    with brownie.reverts(
        "Pool: Withdrawal amount is greater than current unlocked amount"
    ):
        binary_pool_atm.withdraw(binary_pool_atm.availableBalance(), {"from": user_1})

    binary_pool_atm.withdraw(
        liquidity_per_user[0] / binary_pool_atm.INITIAL_RATE(),
        {"from": user_1},
    )
    liquidity_per_user = binary_pool_atm.liquidityPerUser(user_1)

    assert (
        liquidity_per_user[0] == 0 == binary_pool_atm.getUnlockedLiquidity(user_1)
    ), "Unlocked amount should be 0"
    assert liquidity_per_user[1] == 1, "Latest index should be 1"

    ############ Should verify buying using handler ############

    with brownie.reverts("Pool: forbidden"):
        binary_pool_atm.provideForAccount(tokenX_amount_1, 0, user_1, {"from": user_1})

    with brownie.reverts("Pool: forbidden"):
        binary_pool_atm.provideForAccount(tokenX_amount_1, 0, user_1, {"from": owner})

    with brownie.reverts():  # Wrong role
        binary_pool_atm.setHandler(handler, True, {"from": user_1})

    binary_pool_atm.setHandler(handler, True, {"from": owner})
    tokenX.transfer(user_2, tokenX_amount_1 / 3, {"from": owner})
    tokenX.approve(binary_pool_atm.address, tokenX_amount_1 / 3, {"from": user_2})
    binary_pool_atm.provideForAccount(tokenX_amount_1 / 3, 0, user_2, {"from": handler})

    assert binary_pool_atm.balanceOf(user_2) == expected_mint, "Wrong mint"

    ############ Should verify transferFrom and allowance ############

    chain.snapshot()
    chain.sleep(lockup_period + ONE_DAY)

    _balance = binary_pool_atm.balanceOf(user_1) // 2

    with brownie.reverts("Pool: transfer amount exceeds allowance"):
        binary_pool_atm.transferFrom(user_1, user_3, _balance, {"from": user_2})

    binary_pool_atm.approve(user_2, _balance, {"from": user_1})
    binary_pool_atm.transferFrom(user_1, user_3, _balance, {"from": user_2})

    assert binary_pool_atm.allowance(user_1, user_2) == 0, "Wrong allowance"
    assert binary_pool_atm.balanceOf(user_1) == _balance, "Wrong balance"
    assert binary_pool_atm.balanceOf(user_3) == _balance, "Wrong balance"

    chain.revert()

    ############ Should verify shareof with supply############
    assert binary_pool_atm.shareOf(user_1) > 0, "Wrong share"

    ############ Should verify transfering to handler even in lockup ############

    amount_to_transfer = binary_pool_atm.balanceOf(user_2)
    with brownie.reverts("Pool: transfer amount exceeds allowance"):
        binary_pool_atm.transferFrom(user_2, user_1, expected_mint, {"from": user_1})

    binary_pool_atm.approve(user_1, expected_mint, {"from": user_2})

    with brownie.reverts("Pool: Transfer of funds in lock in period is blocked"):
        binary_pool_atm.transferFrom(user_2, user_1, expected_mint, {"from": handler})

    binary_pool_atm.transferFrom(user_2, handler, amount_to_transfer, {"from": user_1})

    assert binary_pool_atm.balanceOf(user_2) == 0, "Wrong balance"
    assert binary_pool_atm.balanceOf(handler) == amount_to_transfer, "Wrong balance"

    chain.snapshot()

    handler_amount_to_transfer = binary_pool_atm.balanceOf(handler)
    binary_pool_atm.transfer(user_2, handler_amount_to_transfer, {"from": handler})

    assert (
        binary_pool_atm.balanceOf(user_2) == handler_amount_to_transfer
    ), "Wrong balance"
    assert binary_pool_atm.balanceOf(handler) == 0, "Wrong balance"

    chain.revert()

    ############ Should verify locking ############

    lock_ids = [0, 1]
    lock_amount = tokenX_amount_3

    for id in lock_ids:
        with brownie.reverts():  # Wrong role
            binary_pool_atm.lock(id, tokenX_amount_3, tokenX_amount_2, {"from": user_1})

        _supply = binary_pool_atm.totalSupply()
        _totalTokenXBalance = binary_pool_atm.totalTokenXBalance()
        initial_locked_liquidity = binary_pool_atm.lockedAmount()
        initial_locked_premimum = binary_pool_atm.lockedPremium()

        tokenX.transfer(user_2, tokenX_amount_2, {"from": owner})

        with brownie.reverts("Pool: Amount is too large."):
            binary_pool_atm.lock(
                id,
                _totalTokenXBalance + tokenX_amount_3,
                tokenX_amount_2,
                {"from": user_2},
            )

        with brownie.reverts(""):
            binary_pool_atm.lock(id, tokenX_amount_3, tokenX_amount_2, {"from": user_2})

        initial_tokenX_balance_options = tokenX.balanceOf(user_2)
        initial_tokenX_balance_lp = tokenX.balanceOf(binary_pool_atm.address)

        tokenX.approve(binary_pool_atm.address, tokenX_amount_1, {"from": user_2})
        with brownie.reverts("Pool: Wrong id"):
            binary_pool_atm.lock(
                id + 1, tokenX_amount_3, tokenX_amount_2, {"from": user_2}
            )
        binary_pool_atm.lock(id, lock_amount, tokenX_amount_2, {"from": user_2})

        final_tokenX_balance_options = tokenX.balanceOf(user_2)
        final_tokenX_balance_lp = tokenX.balanceOf(binary_pool_atm.address)
        final_locked_liquidity = binary_pool_atm.lockedAmount()
        final_locked_premimum = binary_pool_atm.lockedPremium()

        assert (
            initial_tokenX_balance_options - final_tokenX_balance_options
        ) == tokenX_amount_2, "Wrong options balance"
        assert (
            final_tokenX_balance_lp - initial_tokenX_balance_lp
        ) == tokenX_amount_2, "Wrong lp balance"
        assert (
            final_locked_premimum - initial_locked_premimum
        ) == tokenX_amount_2, "Wrong lockedPremium"
        assert (
            final_locked_liquidity - initial_locked_liquidity
        ) == tokenX_amount_3, "Wrong lockedAmount"

    ############ Should verify sending profit ############

    def test_send(payout, id):
        chain.snapshot()

        initial_locked_liquidity = binary_pool_atm.lockedAmount()
        initial_locked_premimum = binary_pool_atm.lockedPremium()
        initial_tokenX_balance_user = tokenX.balanceOf(user_1)
        ll = binary_pool_atm.lockedLiquidity(user_2, id)
        expected_payout = min(payout, ll["amount"])

        with brownie.reverts():  # 0 address
            binary_pool_atm.send(id, ADDRESS_0, payout, {"from": user_2})

        send = binary_pool_atm.send(id, user_1, payout, {"from": user_2})
        final_ll = binary_pool_atm.lockedLiquidity(user_2, id)
        final_locked_liquidity = binary_pool_atm.lockedAmount()
        final_tokenX_balance_user = tokenX.balanceOf(user_1)
        final_locked_premimum = binary_pool_atm.lockedPremium()

        if expected_payout > ll["premium"]:
            assert (
                send.events["Loss"]["amount"] == expected_payout - ll["premium"]
            ), "Wrong loss amount"
        else:
            assert (
                send.events["Profit"]["amount"] == ll["premium"] - expected_payout
            ), "Wrong profit amount"

        assert final_ll["locked"] == False, "Wrong state"
        assert (
            initial_locked_premimum - final_locked_premimum == ll["premium"]
        ), "Wrong lockedPremium"
        assert initial_locked_liquidity - final_locked_liquidity == min(
            payout, ll["amount"]
        ), "Wrong lockedAmount"
        assert (
            final_tokenX_balance_user - initial_tokenX_balance_user
        ) == expected_payout, "Wrong user balance"

        with brownie.reverts("Pool: lockedAmount is already unlocked"):
            binary_pool_atm.send(id, user_1, payout, {"from": user_2})
        chain.revert()

    payouts = [int(lock_amount * 0.95), int(lock_amount * 1.05)]
    with brownie.reverts():  # Wrong role
        binary_pool_atm.send(lock_ids[0], user_1, tokenX_amount_3, {"from": user_1})
    for index, id in enumerate(lock_ids):
        test_send(payouts[index], id)

    ############ Should verify unlocking ############

    for id in lock_ids:
        user = user_2
        ll = binary_pool_atm.lockedLiquidity(user, id)
        lockedPremium = binary_pool_atm.lockedPremium()
        lockedAmount = binary_pool_atm.lockedAmount()

        unlock = binary_pool_atm.unlock(id, {"from": user})

        final_ll = binary_pool_atm.lockedLiquidity(user, id)
        final_lockedPremium = binary_pool_atm.lockedPremium()
        final_lockedAmount = binary_pool_atm.lockedAmount()

        assert (
            lockedPremium - final_lockedPremium == ll["premium"]
        ), "Wrong lockedPremium"
        assert lockedAmount - final_lockedAmount == ll["amount"], "Wrong lockedAmount"
        assert unlock.events["Profit"]["amount"] == ll["premium"], "Wrong premium"
        assert final_ll["locked"] == False, "Wrong state"

    with brownie.reverts("Pool: lockedAmount is already unlocked"):
        unlock = binary_pool_atm.unlock(1, {"from": user})

    assert binary_pool_atm.lockedAmount() == 0, "Wrong value"
    assert binary_pool_atm.lockedPremium() == 0, "Wrong value"

    with brownie.reverts("Invalid new maxLiquidity"):  # Wrong role
        binary_pool_atm.setMaxLiquidity(
            binary_pool_atm.totalTokenXBalance(), {"from": owner}
        )
    binary_pool_atm.setMaxLiquidity(
        binary_pool_atm.totalTokenXBalance() + 1e6, {"from": owner}
    )
