import time
from enum import IntEnum

import brownie
from brownie import BufferBinaryOptions
from eth_account import Account
from eth_account.messages import encode_defunct


class OptionType(IntEnum):
    ALL = 0
    PUT = 1
    CALL = 2
    NONE = 3


ONE_DAY = 86400
ADDRESS_0 = "0x0000000000000000000000000000000000000000"


class BinaryOptionTesting(object):
    def __init__(
        self,
        accounts,
        options,
        generic_pool,
        total_fee,
        chain,
        tokenX,
        liquidity,
        options_config,
        period,
        is_yes,
        is_above,
        router,
        tokenX_option_2,
        options_config_2,
        forex_option,
        forex_option_config,
        trader_nft_contract,
        referral_contract,
        publisher,
        ibfr_contract,
        settlement_fee_disbursal,
    ):
        self.bfr = ibfr_contract
        self.settlement_fee_disbursal = settlement_fee_disbursal
        self.publisher = publisher
        self.trader_nft_contract = trader_nft_contract
        self.forex_option = forex_option
        self.forex_option_config = forex_option_config
        self.tokenX_option_2 = tokenX_option_2
        self.options_config_2 = options_config_2
        self.tokenX_options = options
        self.options_config = options_config
        self.generic_pool = generic_pool
        self.total_fee = total_fee
        self.option_holder = accounts[1]
        self.accounts = accounts
        self.owner = accounts[0]
        self.user_1 = accounts[1]
        self.user_2 = accounts[2]
        self.referrer = accounts[3]
        self.referral_code = "code123"
        self.bot = accounts[4]
        self.user_5 = accounts[5]
        self.user_6 = accounts[6]
        self.user_7 = accounts[7]
        self.option_id = 0
        self.liquidity = liquidity
        self.tokenX = tokenX
        self.chain = chain
        self.period = period
        self.is_yes = is_yes
        self.is_above = is_above
        self.router = router
        self.expected_strike = int(400e8)
        self.slippage = 100
        self.allow_partial_fill = True
        # self.is_trader_nft = False
        self.trader_id = 0
        self.strike = int(400e8)
        self.referral_contract = referral_contract

    def init(self):
        with brownie.reverts("O27"):
            self.tokenX_options.configure(9e2, 20e2, [0, 1, 2, 3])
        with brownie.reverts("O28"):
            self.tokenX_options.configure(51e2, 20e2, [0, 1, 2, 3])

        with brownie.reverts("O27"):
            self.tokenX_options.configure(20e2, 9e2, [0, 1, 2, 3])
        with brownie.reverts("O28"):
            self.tokenX_options.configure(20e2, 51e2, [0, 1, 2, 3])

        self.tokenX.approve(
            self.generic_pool.address, self.liquidity, {"from": self.owner}
        )
        self.generic_pool.provide(self.liquidity, 0, {"from": self.owner})
        self.router.setContractRegistry(self.tokenX_options.address, True)
        self.router.setInPrivateKeeperMode()

        assert self.tokenX_options.assetPair() == "ETH_BTC", "Wrong pair"

    def verify_referrals(self):
        self.chain.snapshot()

        (code, referrer) = self.referral_contract.getTraderReferralInfo(self.user_1)
        assert code == "" and referrer == ADDRESS_0, "Wrong ref data"

        self.referral_contract.setTraderReferralCodeByUser("123", {"from": self.user_1})

        (code, referrer) = self.referral_contract.getTraderReferralInfo(self.user_1)
        assert code == "123" and referrer == ADDRESS_0, "Wrong ref data"

        self.referral_contract.registerCode("123", {"from": self.user_1})

        self.chain.revert()

    def verify_option_config(self):
        self.chain.snapshot()

        # assetUtilizationLimit
        with brownie.reverts("Wrong utilization value"):
            self.options_config.setAssetUtilizationLimit(112e2)
        with brownie.reverts():  # Wrong role
            self.options_config.setAssetUtilizationLimit(10e2, {"from": self.user_1})
        with brownie.reverts("Wrong utilization value"):
            self.options_config.setAssetUtilizationLimit(0)

        self.options_config.setAssetUtilizationLimit(52e2)
        assert self.options_config.assetUtilizationLimit() == 52e2

        # overallPoolUtilizationLimit
        with brownie.reverts("Wrong utilization value"):
            self.options_config.setOverallPoolUtilizationLimit(112e2)
        with brownie.reverts():  # Wrong role
            self.options_config.setOverallPoolUtilizationLimit(
                10e2, {"from": self.user_1}
            )
        with brownie.reverts("Wrong utilization value"):
            self.options_config.setOverallPoolUtilizationLimit(0)

        self.options_config.setOverallPoolUtilizationLimit(52e2)
        assert self.options_config.overallPoolUtilizationLimit() == 52e2

        # maxPeriod
        with brownie.reverts(
            "MaxPeriod needs to be greater than or equal the min period"
        ):
            self.options_config.setMaxPeriod(50)
        with brownie.reverts():  # Wrong role
            self.options_config.setMaxPeriod(86400, {"from": self.user_1})
        with brownie.reverts(
            "MaxPeriod needs to be greater than or equal the min period"
        ):
            self.options_config.setMaxPeriod(120)
        with brownie.reverts("MaxPeriod should be less than or equal to 1 day"):
            self.options_config.setMaxPeriod(86400 + 1)
        self.options_config.setMaxPeriod(86400)
        assert self.options_config.maxPeriod() == 86400

        # minPeriod
        with brownie.reverts("MinPeriod needs to be greater than 1 minute"):
            self.options_config.setMinPeriod(50)
        with brownie.reverts():  # Wrong role
            self.options_config.setMinPeriod(300, {"from": self.user_1})
        self.options_config.setMinPeriod(300)
        assert self.options_config.minPeriod() == 300

        with brownie.reverts():  # Wrong role
            self.options_config.transferOwnership(self.user_2, {"from": self.user_1})
        with brownie.reverts():  # Wrong address
            self.options_config.transferOwnership(ADDRESS_0)
        self.options_config.transferOwnership(self.user_2)
        assert self.options_config.owner() == self.user_2, "Wrong owner"

        self.chain.revert()

    def verify_owner(self):
        assert self.tokenX_options.hasRole(
            self.tokenX_options.DEFAULT_ADMIN_ROLE(), self.accounts[0]
        ), "The admin of the contract should be the account the contract was deployed by"

    def verify_option_states(
        self,
        option_id,
        user,
        expected_strike,
        expected_amount,
        expected_premium,
        expected_option_type,
        expected_total_fee,
        expected_settlement_fee,
        pool_balance_diff,
        sfd_diff,
        txn,
    ):
        (
            _,
            strike,
            amount,
            locked_amount,
            premium,
            _,
            _is_above,
            fee,
            _,
        ) = self.tokenX_options.options(option_id)
        print(self.tokenX_options.options(option_id))
        assert strike == expected_strike, "Wrong strike"
        assert (
            amount == locked_amount == expected_amount
        ), "Wrong amount or locked amount"
        assert premium == expected_premium, "Wrong premium"
        assert _is_above == expected_option_type, "Wrong option_type"
        assert fee == expected_total_fee, "Wrong fee"
        assert (
            self.tokenX.balanceOf(self.tokenX_options.address)
            == self.tokenX.balanceOf(self.router.address)
            == 0
        ), "Wrong option balance"
        assert pool_balance_diff == expected_premium, "Wrong premium transferred"
        assert (
            self.generic_pool.lockedLiquidity(self.tokenX_options.address, option_id)[0]
            == locked_amount
        ), "Wrong liquidity locked"
        assert self.tokenX_options.ownerOf(option_id) == user, "Wrong owner"

        assert (
            txn.events["Create"]["settlementFee"] == expected_settlement_fee
            and sfd_diff == expected_settlement_fee
        ), "Wrong settlementFee"

    def get_signature(self, token, timestamp, price, publisher=None):
        # timestamp = 1667208839
        # token = "0x32A49a15F8eE598C1EeDc21138DEb23b391f425b"
        # price = int(83e8)
        web3 = brownie.network.web3
        key = self.publisher.private_key if not publisher else publisher.private_key
        msg_hash = web3.solidityKeccak(
            ["string", "uint256", "uint256"],
            [BufferBinaryOptions.at(token).assetPair(), timestamp, int(price)],
        )
        signed_message = Account.sign_message(encode_defunct(msg_hash), key)

        def to_32byte_hex(val):
            return web3.toHex(web3.toBytes(val).rjust(32, b"\0"))

        return to_32byte_hex(signed_message.signature)

    def verify_forex_option_trading_window(self):
        market_times = [
            (17, 0, 23, 59),
            (0, 0, 23, 59),
            (0, 0, 23, 59),
            (0, 0, 23, 59),
            (0, 0, 23, 59),
            (0, 0, 15, 59),
            (0, 0, 0, 0),
        ]

        # Set the current time at 5,0 of the day
        currentTime = self.chain.time()
        self.chain.sleep(86400 - (currentTime % 86400) + (5 * 3600))
        currentTime = self.chain.time()

        currentDay = ((currentTime // 86400) + 4) % 7
        self.tokenX.transfer(self.user_1, self.total_fee * 10, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 10, {"from": self.user_1}
        )
        next_id = self.router.nextQueueId()
        _params = (
            self.total_fee,
            self.period,  # slightly less then a day
            self.is_above,
            self.forex_option.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        # Shouldn't allow forex trades when market times haven't been set
        self.chain.snapshot()
        self.router.initiateTrade(
            *_params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.forex_option.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"] and txn.events["CancelTrade"]["reason"] == "O30"
        )
        self.chain.revert()

        # Only the options config owner can set the market time
        with brownie.reverts("Ownable: caller is not the owner"):
            self.options_config.setMarketTime(
                market_times,
                {"from": self.user_1},
            )

        ########### MARKET IS OPEN FOR THE WHOLE DAY ###########
        market_times[currentDay] = (0, 0, 23, 59)
        self.forex_option_config.setMarketTime(
            market_times,
            {"from": self.owner},
        )

        # Should cancel inter-day trades
        self.chain.snapshot()
        self.router.initiateTrade(
            *_params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.forex_option.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"] and txn.events["CancelTrade"]["reason"] == "O30"
        )
        self.chain.revert()

        # Should open intra-day trades

        params = (
            self.total_fee,
            300,  # 5mins
            self.is_above,
            self.forex_option.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.chain.snapshot()
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.forex_option.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert txn.events["OpenTrade"], "Trade didn't open"
        self.chain.revert()

        currentHour = (currentTime // 3600) % 24
        currentMinute = (currentTime % 3600) / 60

        ########### MARKET HASN'T OPENED YET ###########
        market_times[currentDay] = (currentHour + 1, currentMinute, 23, 59)
        self.forex_option_config.setMarketTime(
            market_times,
            {"from": self.owner},
        )

        # Should cancel the trade
        self.chain.snapshot()
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.forex_option.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"] and txn.events["CancelTrade"]["reason"] == "O30"
        )
        self.chain.revert()

        # Time travel to market open time
        self.chain.sleep(3600)

        # Should open the trade
        self.chain.snapshot()
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.forex_option.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert txn.events["OpenTrade"], "Trade didn't open"
        self.chain.revert()

        ########### MARKET IS GONNA CLOSE in 10 min ###########
        currentTime = self.chain.time()
        currentHour = (currentTime // 3600) % 24
        currentMinute = (currentTime % 3600) // 60
        expirationHour = ((currentTime + 300) // 3600) % 24
        expirationMinute = ((currentTime + 300) % 3600) // 60

        market_times[currentDay] = (
            0,
            0,
            currentHour if currentMinute + 10 < 60 else currentHour + 1,
            (currentMinute + 10) % 60,
        )
        self.forex_option_config.setMarketTime(
            market_times,
            {"from": self.owner},
        )
        print(
            currentHour,
            currentMinute,
            expirationHour,
            expirationMinute,
            self.forex_option_config.marketTimes(currentDay),
        )
        # Should open the trade
        self.chain.snapshot()
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.forex_option.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert txn.events["OpenTrade"], "Trade didn't open"
        self.chain.revert()

        # Should cancel the trade beyond 10 min
        self.chain.snapshot()
        self.router.initiateTrade(
            self.total_fee,
            601,
            self.is_above,
            self.forex_option.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.forex_option.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"] and txn.events["CancelTrade"]["reason"] == "O30"
        )
        self.chain.revert()

        # Time travel to market close time
        self.chain.sleep(600)

        # Should cancel trade
        self.chain.snapshot()
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.forex_option.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"] and txn.events["CancelTrade"]["reason"] == "O30"
        )
        self.chain.revert()

    def verify_fake_referral_protection(self):
        self.chain.snapshot()
        self.tokenX.transfer(self.user_5, self.total_fee * 3, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 3, {"from": self.user_5}
        )
        self.referral_code = "code1234"

        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.referral_contract.registerCode(
            self.referral_code,
            {"from": self.user_7},
        )
        self.referral_contract.setCodeOwner(
            self.referral_code,
            self.referral_contract.address,
            {"from": self.referrer},
        )
        txn = self.router.initiateTrade(
            *params,
            {"from": self.user_5},
        )
        queue_id = txn.events["InitiateTrade"]["queueId"]

        initial_referrer_tokenX_balance = self.tokenX.balanceOf(
            self.referral_contract.address
        )
        queued_trade = self.router.queuedTrades(queue_id)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]

        txn = self.router.resolveQueuedTrades(
            [
                (
                    queue_id,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )

        final_referrer_tokenX_balance = self.tokenX.balanceOf(
            self.referral_contract.address
        )

        assert txn.events["OpenTrade"], "Trade not opened"
        assert txn.events["Create"], "Not created"
        assert (
            final_referrer_tokenX_balance - initial_referrer_tokenX_balance == 0
        ), "Wrong user balance"

        self.chain.revert()

    def verify_creation_with_referral_and_no_nft(self):
        # tier 0
        self.chain.snapshot()
        self.tokenX.transfer(self.user_5, self.total_fee * 3, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 3, {"from": self.user_5}
        )
        self.referral_code = "code1234"

        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.referral_contract.registerCode(
            self.referral_code,
            {"from": self.referrer},
        )
        with brownie.reverts("ReferralStorage: code already exists"):
            self.referral_contract.registerCode(
                self.referral_code,
                {"from": self.user_2},
            )

        txn = self.router.initiateTrade(
            *params,
            {"from": self.user_5},
        )
        queue_id = txn.events["InitiateTrade"]["queueId"]

        expected_amount = 1720001.0

        initial_referrer_tokenX_balance = self.tokenX.balanceOf(self.referrer)
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_5)
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)

        queued_trade = self.router.queuedTrades(queue_id)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]

        txn = self.router.resolveQueuedTrades(
            [
                (
                    queue_id,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )

        final_referrer_tokenX_balance = self.tokenX.balanceOf(self.referrer)
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_5)
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)

        option_id = txn.events["Create"]["id"]

        assert txn.events["OpenTrade"], "Trade not opened"
        assert txn.events["Create"], "Not created"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 0
        ), "Wrong user balance"
        assert (
            final_referrer_tokenX_balance - initial_referrer_tokenX_balance == 2500
        ), "Wrong user balance"
        self.verify_option_states(
            option_id,
            self.user_5,
            396e8,
            expected_amount,
            expected_amount // 2,
            self.is_above,
            self.total_fee,
            137500,  # 14% - 2500
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )
        self.chain.revert()

    def verify_creation_with_no_referral_and_no_nft(self):
        self.tokenX.transfer(self.user_1, self.total_fee * 3, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 3, {"from": self.user_1}
        )

        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )

        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_locked_amount = self.tokenX_options.totalLockedAmount()
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        queued_trade = self.router.queuedTrades(0)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    0,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)
        final_locked_amount = self.tokenX_options.totalLockedAmount()
        assert txn.events["OpenTrade"], "Trade not opened"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 0
        ), "Wrong user balance"
        assert final_locked_amount - initial_locked_amount == 1700000
        self.verify_option_states(
            0,
            self.user_1,
            396e8,
            1700000,
            1700000 // 2,
            self.is_above,
            self.total_fee,
            150000,
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )

        # No referral discount is case referrer is the owner
        # This requirement is mute now but we are keeping the remaining test case as it affects rest of the state of the system
        self.referral_code = "code12345"

        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        queued_trade = self.router.queuedTrades(1)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)
        assert txn.events["OpenTrade"], "Trade not opened"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 0
        ), "Wrong user balance"
        self.verify_option_states(
            1,
            self.user_1,
            396e8,
            1700000,
            1700000 // 2,
            self.is_above,
            self.total_fee,
            150000,
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(2)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    2,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )

    def verify_creation_with_no_referral_and_nft(self):
        self.chain.snapshot()
        self.options_config.settraderNFTContract(self.trader_nft_contract.address)

        self.tokenX.transfer(self.user_1, self.total_fee * 3, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 3, {"from": self.user_1}
        )
        metadata_hash = "QmRu61jShPgiQp33UA5RNcULAvLU5JEPbnXGqEtBmVcdMg"
        self.trader_nft_contract.claim({"from": self.user_1, "value": "2 ether"})
        self.trader_nft_contract.safeMint(
            self.user_1,
            metadata_hash,
            1,
            0,
            {"from": self.owner},
        )
        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        expected_amount = 1750001
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_locked_amount = self.tokenX_options.totalLockedAmount()
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        queued_trade = self.router.queuedTrades(3)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    3,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_locked_amount = self.tokenX_options.totalLockedAmount()
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)
        assert txn.events["OpenTrade"], "Trade not opened"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 0
        ), "Wrong user balance"
        assert final_locked_amount - initial_locked_amount == expected_amount
        self.verify_option_states(
            3,
            self.user_1,
            396e8,
            expected_amount,
            expected_amount // 2,
            self.is_above,
            self.total_fee,
            125000.0,
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )

        self.chain.revert()

    def verify_creation_with_referral_and_nft(self):
        self.chain.snapshot()
        # Case 1 : referrer tier > nft tier - tier 1
        self.options_config.settraderNFTContract(self.trader_nft_contract.address)

        self.referral_contract.setReferrerTier(self.referrer, 1, {"from": self.owner})
        self.referral_contract.registerCode(
            self.referral_code,
            {"from": self.referrer},
        )

        self.referral_contract.setTraderReferralCodeByUser(
            self.referral_code,
            {"from": self.user_1},
        )
        self.tokenX.transfer(self.user_1, self.total_fee * 3, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 3, {"from": self.user_1}
        )
        metadata_hash = "QmRu61jShPgiQp33UA5RNcULAvLU5JEPbnXGqEtBmVcdMg"
        self.trader_nft_contract.claim({"from": self.user_1, "value": "2 ether"})
        self.trader_nft_contract.safeMint(
            self.user_1,
            metadata_hash,
            0,
            0,
            {"from": self.owner},
        )
        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        expected_amount = 1750001
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_locked_amount = self.tokenX_options.totalLockedAmount()
        initial_referrer_tokenX_balance = self.tokenX.balanceOf(self.referrer)
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        queued_trade = self.router.queuedTrades(0)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    0,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_referrer_tokenX_balance = self.tokenX.balanceOf(self.referrer)
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_locked_amount = self.tokenX_options.totalLockedAmount()
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)

        assert (
            final_referrer_tokenX_balance - initial_referrer_tokenX_balance == 5000
        ), "Wrong ref balance"
        assert txn.events["OpenTrade"], "Trade not opened"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 0
        ), "Wrong user balance"
        assert final_locked_amount - initial_locked_amount == expected_amount
        self.verify_option_states(
            0,
            self.user_1,
            396e8,
            expected_amount,
            expected_amount // 2,
            self.is_above,
            self.total_fee,
            120000.0,  # 5%
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )

        self.chain.revert()

        # Case 2 : referrer tier < nft tier - tier 2
        self.chain.snapshot()
        self.options_config.settraderNFTContract(self.trader_nft_contract.address)

        self.referral_contract.setReferrerTier(self.referrer, 0, {"from": self.owner})
        self.referral_contract.registerCode(
            self.referral_code,
            {"from": self.referrer},
        )

        self.referral_contract.setTraderReferralCodeByUser(
            self.referral_code,
            {"from": self.user_1},
        )
        self.tokenX.transfer(self.user_1, self.total_fee * 3, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 3, {"from": self.user_1}
        )
        metadata_hash = "QmRu61jShPgiQp33UA5RNcULAvLU5JEPbnXGqEtBmVcdMg"
        self.trader_nft_contract.claim({"from": self.user_1, "value": "2 ether"})
        self.trader_nft_contract.safeMint(
            self.user_1,
            metadata_hash,
            2,
            0,
            {"from": self.owner},
        )

        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )

        expected_amount = 1780002.0
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_locked_amount = self.tokenX_options.totalLockedAmount()
        initial_referrer_tokenX_balance = self.tokenX.balanceOf(self.referrer)
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        queued_trade = self.router.queuedTrades(0)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    0,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_referrer_tokenX_balance = self.tokenX.balanceOf(self.referrer)
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_locked_amount = self.tokenX_options.totalLockedAmount()
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)

        assert (
            final_referrer_tokenX_balance - initial_referrer_tokenX_balance == 2500
        ), "Wrong ref balance"
        assert txn.events["OpenTrade"], "Trade not opened"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 0
        ), "Wrong user balance"
        assert final_locked_amount - initial_locked_amount == expected_amount
        self.verify_option_states(
            0,
            self.user_1,
            396e8,
            expected_amount,
            expected_amount // 2,
            self.is_above,
            self.total_fee,
            107499.0,
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )
        self.chain.revert()

    def verify_put_creation_with_less_liquidity(self):
        self.tokenX.transfer(self.user_1, self.total_fee * 2, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 2, {"from": self.user_1}
        )

        params = (
            self.total_fee * 2,
            self.period,
            False,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )
        next_id = self.router.nextQueueId()

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        totalPoolBalance = self.generic_pool.totalTokenXBalance()
        availableBalance = totalPoolBalance - self.tokenX_options.totalLockedAmount()

        max_utilization = self.tokenX_options.getMaxUtilization()
        print(
            "available",
            availableBalance,
            availableBalance - (totalPoolBalance * 90 // 100),
            max_utilization,
        )
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            396e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)
        assert txn.events["OpenTrade"], "Wrong action"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 882353.0
        ), "Wrong user balance"

        self.verify_option_states(
            next_id,
            self.user_1,
            396e8,
            max_utilization,  # self.generic_pool.availableBalance() * 5 // 100
            max_utilization // 2,
            False,
            1117647.0,
            167647.0,
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )

    def verify_call_creation_with_less_liquidity(self):

        self.tokenX.approve(self.generic_pool.address, 100e6, {"from": self.owner})
        self.generic_pool.provide(10e6, 0, {"from": self.owner})
        self.tokenX.transfer(self.user_1, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_1})
        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        totalPoolBalance = self.generic_pool.totalTokenXBalance()
        availableBalance = totalPoolBalance - self.tokenX_options.totalLockedAmount()
        max_utilization = self.tokenX_options.getMaxUtilization()
        print(
            "available",
            availableBalance,
            availableBalance - (totalPoolBalance * 90 // 100),
            max_utilization,
        )
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        queued_trade = self.router.queuedTrades(4)
        open_params_1 = [
            queued_trade[10],
            400e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    4,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)
        assert txn.events["OpenTrade"], "Wrong action"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 411765.0
        ), "Wrong user balance"
        self.verify_option_states(
            4,
            self.user_1,
            400e8,
            max_utilization,
            max_utilization // 2,
            self.is_above,
            588235.0,
            88235.0,
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )

    def verify_creation_with_high_trade_amount(self):
        self.chain.snapshot()
        self.options_config.setAssetUtilizationLimit(50e2, {"from": self.owner})

        self.tokenX.approve(self.generic_pool.address, 100e6, {"from": self.owner})
        self.generic_pool.provide(100e6, 0, {"from": self.owner})
        self.tokenX.transfer(self.user_1, self.total_fee * 7, {"from": self.owner})
        self.tokenX.approve(
            self.router.address, self.total_fee * 7, {"from": self.user_1}
        )
        params = (
            self.total_fee * 7,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        availableBalance = self.generic_pool.availableBalance()
        maxTxnLimit = availableBalance * 5 // 100
        print(
            "available....",
            self.options_config.optionFeePerTxnLimitPercent(),
            maxTxnLimit / 1e6,
            self.tokenX_options.getMaxUtilization() / 1e6,
        )
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_sfd_tokenX_balance = self.tokenX.balanceOf(
            self.settlement_fee_disbursal
        )
        queued_trade = self.router.queuedTrades(6)
        open_params_1 = [
            queued_trade[10],
            400e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    6,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_sfd_tokenX_balance = self.tokenX.balanceOf(self.settlement_fee_disbursal)
        assert txn.events["OpenTrade"], "Wrong action"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 1819998
        ), "Wrong user balance"
        self.verify_option_states(
            5,
            self.user_1,
            400e8,
            8806004.0,
            8806004.0 // 2,
            self.is_above,
            5180002,
            777000.0,
            final_pool_tokenX_balance - initial_pool_tokenX_balance,
            final_sfd_tokenX_balance - initial_sfd_tokenX_balance,
            txn,
        )
        self.chain.revert()

    def verify_creation_with_high_utilization(self):
        self.tokenX.transfer(self.user_1, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_1})
        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(5)
        open_params_1 = [
            queued_trade[10],
            400e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    5,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )

        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"]["queueId"] == 5
            and txn.events["CancelTrade"]["reason"] == "O31"
        )

    def verify_creation_with_paused_creation(self):
        self.chain.snapshot()
        self.tokenX.transfer(self.user_1, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_1})
        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(5)
        open_params_1 = [
            queued_trade[10],
            400e8,
        ]
        self.tokenX_options.toggleCreation()
        txn = self.router.resolveQueuedTrades(
            [
                (
                    5,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )

        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"]["queueId"] == 5
            and txn.events["CancelTrade"]["reason"] == "O33"
        )
        self.chain.revert()

    def unlock_options(self, options):
        params = []
        for option in options:
            option_data = self.tokenX_options.options(option[0])
            close_params = (self.tokenX_options.address, option_data[5], option[1])
            params.append(
                (
                    option[0],
                    *close_params,
                    self.get_signature(
                        *close_params,
                    ),
                )
            )
        txn = self.router.unlockOptions(
            params,
            {"from": self.bot},
        )
        return txn

    def verify_unlocking_ITM(self):
        self.chain.snapshot()

        # ITM for call
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        initial_locked_amount = self.tokenX_options.totalLockedAmount()

        txn = self.unlock_options([(0, 500e8)])
        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        final_locked_amount = self.tokenX_options.totalLockedAmount()

        assert txn.events["Loss"] and txn.events["Exercise"], "Option didnot exercise"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 1700000
        ), "Wrong user balance"
        assert (
            initial_pool_tokenX_balance - final_pool_tokenX_balance == 1700000
        ), "Wrong pool balance"
        assert self.tokenX_options.options(0)[0] == 2, "Wrong state"
        assert initial_locked_amount - final_locked_amount == 1700000

        # ITM for put
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        txn = self.unlock_options([(3, 300e8)])

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)

        assert txn.events["Loss"] and txn.events["Exercise"], "Option didnot exercise"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == 1900000
        ), "Wrong user balance"
        assert (
            initial_pool_tokenX_balance - final_pool_tokenX_balance == 1900000
        ), "Wrong pool balance"
        assert self.tokenX_options.options(3)[0] == 2, "Wrong state"

        txn = self.unlock_options([(0, 500e8)])
        assert txn.events["FailUnlock"]["reason"] == "O10", "Wrong action"

        self.chain.revert()

    def verify_unlocking_OTM_and_ATM(self):
        self.chain.snapshot()
        # ATM for Call
        txn = self.unlock_options([(0, 396e8)])

        assert txn.events["Profit"] and txn.events["Expire"], "Option didnot expire"
        assert self.tokenX_options.options(0)[0] == 3, "Wrong state"

        # OTM for Call
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        txn = self.unlock_options([(1, 390e8)])

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)

        assert txn.events["Profit"] and txn.events["Expire"], "Option didnot expire"

        assert (
            initial_user_tokenX_balance - final_user_tokenX_balance
            == final_pool_tokenX_balance - initial_pool_tokenX_balance
            == 0
        ), "Wrong transfer of funds"
        with brownie.reverts("ERC721: invalid token ID"):  # Option burnt

            self.tokenX_options.ownerOf(1)

        txn = self.unlock_options([(0, 390e8)])
        assert txn.events["FailUnlock"]["reason"] == "O10", "Wrong action"

        txn = self.unlock_options([(1, 390e8)])
        assert txn.events["FailUnlock"]["reason"] == "O10", "Wrong action"

        # OTM for Put
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)
        txn = self.unlock_options([(3, 490e8)])

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_pool_tokenX_balance = self.tokenX.balanceOf(self.generic_pool.address)

        assert txn.events["Profit"] and txn.events["Expire"], "Option didnot expire"

        assert (
            initial_user_tokenX_balance - final_user_tokenX_balance
            == final_pool_tokenX_balance - initial_pool_tokenX_balance
            == 0
        ), "Wrong transfer of funds"
        with brownie.reverts("ERC721: invalid token ID"):  # Option burnt
            self.tokenX_options.ownerOf(1)

        txn = self.unlock_options([(0, 390e8)])
        assert txn.events["FailUnlock"]["reason"] == "O10", "Wrong action"

        txn = self.unlock_options([(1, 390e8)])
        assert txn.events["FailUnlock"]["reason"] == "O10", "Wrong action"

        self.chain.revert()

    def verify_unlocking_multiple_options_at_once(self):

        txn = self.unlock_options(
            [(0, 500e8), (1, 300e8), (2, 200e8), (3, 200e8), (4, 550e8)],
        )

        profit_events = txn.events["Profit"]
        loss_events = txn.events["Loss"]
        exercise_events = txn.events["Exercise"]
        expire_events = txn.events["Expire"]
        # print(txn.events)
        assert profit_events[0]["id"] == 1 and profit_events[1]["id"] == 2
        assert (
            loss_events[0]["id"] == 0
            and loss_events[1]["id"] == 3
            and loss_events[2]["id"] == 4
        )
        assert expire_events[0]["id"] == 1 and expire_events[1]["id"] == 2
        assert (
            exercise_events[0]["id"] == 0
            and exercise_events[1]["id"] == 3
            and exercise_events[2]["id"] == 4
        )

    def verify_asset_utilization_limit(self):
        self.chain.snapshot()
        self.tokenX.approve(self.generic_pool.address, 100e6, {"from": self.owner})
        self.generic_pool.provide(60e6, 0, {"from": self.owner})

        # Set utilization limit for the asset A and asset B as 10%
        self.options_config.setAssetUtilizationLimit(10e2, {"from": self.owner})
        self.options_config_2.setAssetUtilizationLimit(10e2, {"from": self.owner})
        print(
            "pool",
            self.tokenX_options.totalLockedAmount() / 1e6,
            self.generic_pool.totalTokenXBalance() / 1e6,
            self.generic_pool.availableBalance() / 1e6,
        )
        print(self.tokenX_options.getMaxUtilization())
        fee = 1e6
        self.tokenX.transfer(self.user_1, fee * 20, {"from": self.owner})
        self.tokenX.approve(self.router.address, fee * 20, {"from": self.user_1})
        next_id = self.router.nextQueueId()
        next_option_id = self.tokenX_options.nextTokenId()
        params = (
            fee * 2,
            300,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        # Buy multiple trades for asset A
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )

        # Trade 1,2,3 use the max utilization(10%) of asset A so trade 4 should cancel
        queued_trade = self.router.queuedTrades(next_id)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        queued_trade = self.router.queuedTrades(next_id + 1)
        open_params_2 = [
            queued_trade[10],
            self.expected_strike,
        ]
        queued_trade = self.router.queuedTrades(next_id + 2)
        open_params_3 = [
            queued_trade[10],
            self.expected_strike,
        ]
        queued_trade = self.router.queuedTrades(next_id + 3)
        open_params_4 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
                (
                    next_id + 1,
                    *open_params_2,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_2,
                    ),
                ),
                (
                    next_id + 2,
                    *open_params_3,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_3,
                    ),
                ),
                (
                    next_id + 3,
                    *open_params_4,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_4,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        print(self.tokenX_options.options(next_option_id))
        print(self.tokenX_options.options(next_option_id + 1))
        print(self.tokenX_options.options(next_option_id + 2))
        print(self.tokenX_options.options(next_option_id + 3))

        assert len(txn.events["OpenTrade"]) == 3, "Wrong count"
        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"]["queueId"] == next_id + 3
            and txn.events["CancelTrade"]["reason"] == "O31"
        )
        print(self.tokenX_options.ownerOf(next_option_id))
        option_to_unlock = next_option_id

        # Trades for asset B should still open since its utilization hasn't reached max
        print(self.tokenX_option_2.getMaxUtilization() / 1e6)

        print(
            "pool",
            self.tokenX_option_2.totalLockedAmount() / 1e6,
            self.generic_pool.totalTokenXBalance() / 1e6,
            self.generic_pool.availableBalance() / 1e6,
        )
        params = (
            fee * 2,
            self.period,
            self.is_above,
            self.tokenX_option_2.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )
        next_id = self.router.nextQueueId()
        next_option_id = self.tokenX_option_2.nextTokenId()

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )

        queued_trade = self.router.queuedTrades(next_id)
        open_params_2 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_2,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_2,
                    ),
                )
            ],
            {"from": self.bot},
        )
        print(self.router.queuedTrades(next_id))
        print(self.tokenX_option_2.options(next_option_id))
        assert txn.events["OpenTrade"]["queueId"] == next_id, "Wrong id"
        print(self.tokenX_option_2.getMaxUtilization() / 1e6)

        # Unlocking trade 1 should release the locked amount and allow opening other trades
        self.chain.sleep(301)

        txn = self.unlock_options(
            [(option_to_unlock, self.expected_strike)],
        )
        print(self.tokenX_options.getMaxUtilization() / 1e6)

        next_id = self.router.nextQueueId()
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        queued_trade = self.router.queuedTrades(next_id)
        open_params_2 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_2,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_2,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert txn.events["OpenTrade"]["queueId"] == next_id, "Trade should open"
        self.chain.revert()

    def verify_pausing(self):
        self.tokenX.transfer(self.user_1, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_1})
        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )

        with brownie.reverts():  # Wrong role
            self.tokenX_options.toggleCreation({"from": self.user_1})
        self.tokenX_options.toggleCreation({"from": self.owner})
        assert self.tokenX_options.isPaused(), "SHould have paused"

        with brownie.reverts("O33"):
            self.router.initiateTrade(
                *params,
                {"from": self.user_1},
            )
        self.tokenX_options.toggleCreation({"from": self.owner})
        assert not self.tokenX_options.isPaused(), "SHould have unpaused"

    def verify_overall_utilization_limit(self):
        self.chain.snapshot()
        self.tokenX.approve(self.generic_pool.address, 100e6, {"from": self.owner})
        self.generic_pool.provide(60e6, 0, {"from": self.owner})
        self.tokenX.transfer(self.user_1, 100e6, {"from": self.owner})
        self.tokenX.approve(self.router.address, 100e6, {"from": self.user_1})

        self.options_config.setOverallPoolUtilizationLimit(5e2)
        max_utilization = self.tokenX_options.getMaxUtilization()
        params = (
            4e6,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )
        next_id = self.router.nextQueueId()
        next_option_id = self.tokenX_options.nextTokenId()

        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )

        queued_trade = self.router.queuedTrades(next_id)
        open_params_2 = [
            queued_trade[10],
            self.expected_strike,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    next_id,
                    *open_params_2,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_2,
                    ),
                )
            ],
            {"from": self.bot},
        )

        assert txn.events["OpenTrade"]["queueId"] == next_id, "Wrong id"
        assert (
            self.tokenX_options.options(next_option_id)[2] == max_utilization
        ), "Wrong size"

        with brownie.reverts("O31"):
            self.tokenX_options.getMaxUtilization() / 1e6

        self.chain.revert()

    def complete_flow_test(self):
        self.init()
        self.verify_option_config()
        self.verify_owner()
        self.verify_pausing()

        with brownie.reverts():  # Wrong role
            self.tokenX_options.createFromRouter(
                (
                    self.strike,
                    0,
                    self.period,
                    True,
                    True,
                    self.total_fee,
                    self.user_1,
                    "1e6",
                    0,
                ),
                False,
                int(time.time()),
                {"from": self.accounts[0]},
            )

        self.verify_forex_option_trading_window()
        # self.verify_fake_referral_protection()
        self.verify_creation_with_referral_and_nft()
        self.verify_creation_with_referral_and_no_nft()
        self.verify_creation_with_no_referral_and_no_nft()
        self.verify_creation_with_no_referral_and_nft()
        self.verify_referrals()

        self.chain.sleep(10 * 60 + 1)
        self.generic_pool.withdraw(10e6, {"from": self.owner})

        self.verify_put_creation_with_less_liquidity()
        self.verify_call_creation_with_less_liquidity()
        self.verify_creation_with_paused_creation()

        self.chain.sleep(10 * 60 + 1)
        self.generic_pool.withdraw(
            self.generic_pool.availableBalance() * 95 // 100, {"from": self.owner}
        )

        self.verify_creation_with_high_utilization()
        self.verify_creation_with_high_trade_amount()

        with brownie.reverts():  # Wrong role
            self.tokenX_options.unlock(0, 500e8, {"from": self.user_1})
        with brownie.reverts():  # Wrong role
            self.tokenX_options.unlock(0, 500e8, {"from": self.owner})
        txn = self.unlock_options(
            [(0, 500e8)],
        )
        assert txn.events["FailUnlock"]["reason"] == "O4", "Wrong action"

        self.chain.sleep(self.period + 1)
        self.verify_unlocking_ITM()
        self.verify_unlocking_OTM_and_ATM()
        self.verify_unlocking_multiple_options_at_once()
        self.verify_asset_utilization_limit()
        self.verify_overall_utilization_limit()


def test_BinaryOptions(contracts, accounts, chain):

    trader_nft_contract = contracts["trader_nft_contract"]
    tokenX = contracts["tokenX"]
    ibfr_contract = contracts["ibfr_contract"]
    binary_pool_atm = contracts["binary_pool_atm"]
    binary_options_config_atm = contracts["binary_options_config_atm"]
    router = contracts["router"]
    binary_european_options_atm = contracts["binary_european_options_atm"]
    binary_options_config_atm_2 = contracts["binary_options_config_atm_2"]
    binary_european_options_atm_2 = contracts["binary_european_options_atm_2"]

    binary_options_config_atm_3 = contracts["binary_options_config_atm_3"]
    binary_european_options_atm_3 = contracts["binary_european_options_atm_3"]
    referral_contract = contracts["referral_contract"]
    publisher = contracts["publisher"]

    settlement_fee_disbursal = contracts["settlement_fee_disbursal"]

    total_fee = int(1e6)
    liquidity = int(80 * 1e6)
    period = 86300
    isYes = True
    isAbove = True
    option = BinaryOptionTesting(
        accounts,
        binary_european_options_atm,
        binary_pool_atm,
        total_fee,
        chain,
        tokenX,
        liquidity,
        binary_options_config_atm,
        period,
        isYes,
        isAbove,
        router,
        binary_european_options_atm_2,
        binary_options_config_atm_2,
        binary_european_options_atm_3,
        binary_options_config_atm_3,
        trader_nft_contract,
        referral_contract,
        publisher,
        ibfr_contract,
        settlement_fee_disbursal,
    )
    option.complete_flow_test()
