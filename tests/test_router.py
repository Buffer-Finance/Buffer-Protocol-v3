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


class Router(object):
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
        ibfr_contract,
        bfr_pool_atm,
        bfr_binary_options_config_atm,
        bfr_binary_european_options_atm,
        publisher,
    ):
        self.tokenX_options = options
        self.publisher = publisher
        self.options_config = options_config
        self.generic_pool = generic_pool
        self.bfr_options = bfr_binary_european_options_atm
        self.bfr_options_config = bfr_binary_options_config_atm
        self.bfr_pool = bfr_pool_atm
        self.total_fee = total_fee
        self.option_holder = accounts[1]
        self.accounts = accounts
        self.owner = accounts[0]
        self.user_1 = accounts[1]
        self.user_2 = accounts[2]
        self.referrer = accounts[3]
        self.bot = accounts[4]
        self.option_id = 0
        self.liquidity = liquidity
        self.tokenX = tokenX
        self.bfr = ibfr_contract
        self.chain = chain
        self.period = period
        self.is_yes = is_yes
        self.is_above = is_above
        self.router = router
        self.expected_strike = int(400e8)
        self.slippage = 100
        self.allow_partial_fill = False
        self.index = 11
        # self.is_trader_nft = False
        self.referral_code = "code123"
        self.trader_id = 0
        self.strike = int(400e8)
        self.option_params = [
            self.total_fee,
            120,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        ]

    def init(self):
        self.tokenX.approve(
            self.generic_pool.address, self.liquidity, {"from": self.owner}
        )
        self.generic_pool.provide(self.liquidity, 0, {"from": self.owner})
        self.bfr.approve(self.bfr_pool.address, 100e18, {"from": self.owner})
        self.bfr_pool.provide(100e18, 0, {"from": self.owner})

    def verify_owner(self):
        assert self.tokenX_options.hasRole(
            self.tokenX_options.DEFAULT_ADMIN_ROLE(), self.accounts[0]
        ), "The admin of the contract should be the account the contract was deployed by"

    def verify_target_contract_registration(self):
        with brownie.reverts("Router: Unauthorized contract"):
            self.router.initiateTrade(
                *self.option_params,
                {"from": self.owner},
            )

        with brownie.reverts():  # Wrong role
            self.router.setContractRegistry(
                self.tokenX_options.address, True, {"from": self.user_2}
            )

        self.router.setContractRegistry(self.tokenX_options.address, True)
        assert self.router.contractRegistry(
            self.tokenX_options.address
        ), "Contract not registered"

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

    def verify_multitoken_router(self):
        self.chain.snapshot()
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.owner})
        self.tokenX.transfer(self.user_1, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_1})

        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_user_bfr_balance = self.bfr.balanceOf(self.user_1)

        params = (
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            self.slippage,
            True,
            self.referral_code,
            0,
        )
        txn = self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_user_bfr_balance = self.bfr.balanceOf(self.user_1)

        assert (
            initial_user_tokenX_balance - final_user_tokenX_balance == self.total_fee
            and initial_user_bfr_balance - final_user_bfr_balance == 0
        )

        fee = 1e18
        self.bfr.approve(self.router.address, fee, {"from": self.owner})
        self.bfr.transfer(self.user_1, fee, {"from": self.owner})
        self.bfr.approve(self.router.address, fee, {"from": self.user_1})

        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_user_bfr_balance = self.bfr.balanceOf(self.user_1)

        params = (
            fee,
            self.period,
            self.is_above,
            self.bfr_options.address,
            self.expected_strike,
            self.slippage,
            self.allow_partial_fill,
            self.referral_code,
            0,
        )
        txn = self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_user_bfr_balance = self.bfr.balanceOf(self.user_1)

        assert (
            initial_user_bfr_balance - final_user_bfr_balance == fee
            and initial_user_tokenX_balance - final_user_tokenX_balance == 0
        )
        queued_trade = self.router.queuedTrades(8)
        open_params_1 = [
            queued_trade[10],
            self.expected_strike,
        ]
        queued_trade = self.router.queuedTrades(9)
        open_params_2 = [
            queued_trade[10],
            self.expected_strike,
        ]

        txn = self.router.resolveQueuedTrades(
            [
                (
                    8,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                ),
                (
                    9,
                    *open_params_2,
                    self.get_signature(
                        self.bfr_options.address,
                        *open_params_2,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert txn.events["OpenTrade"][0]["queueId"] == 8, "Wrong trade opened"
        assert txn.events["OpenTrade"][1]["queueId"] == 9, "Wrong trade opened"
        assert (
            self.tokenX_options.nextTokenId() == 3
            and self.bfr_options.nextTokenId() == 1
        ), "Wrong options"
        self.chain.revert()

    def verify_trade_initiation(self):
        # Reverts if period less than 5 mins
        with brownie.reverts():
            self.router.initiateTrade(
                self.total_fee,
                120,
                self.is_above,
                self.tokenX_options.address,
                self.expected_strike,
                self.slippage,
                self.allow_partial_fill,
                self.referral_code,
                0,
                {"from": self.owner},
            )

        # Reverts if period greater than 24 hours
        with brownie.reverts():
            self.router.initiateTrade(
                self.total_fee,
                87400,
                self.is_above,
                self.tokenX_options.address,
                self.expected_strike,
                self.slippage,
                self.allow_partial_fill,
                self.referral_code,
                0,
                {"from": self.owner},
            )

        # Reverts if slippage is greater than 5e2
        with brownie.reverts("O34"):
            self.router.initiateTrade(
                self.total_fee,
                self.period,
                self.is_above,
                self.tokenX_options.address,
                self.expected_strike,
                int(6e2),  # Slippage higher than max value
                self.allow_partial_fill,
                self.referral_code,
                0,
                {"from": self.owner},
            )

        with brownie.reverts("O35"):
            self.router.initiateTrade(
                1e5,
                self.period,
                self.is_above,
                self.tokenX_options.address,
                self.expected_strike,
                int(1e2),  # Slippage higher than max value
                self.allow_partial_fill,
                self.referral_code,
                0,
                {"from": self.owner},
            )

        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.owner})
        self.tokenX.transfer(self.user_1, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_1})

        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_router_tokenX_balance = self.tokenX.balanceOf(self.router.address)

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
        txn = self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_router_tokenX_balance = self.tokenX.balanceOf(self.router.address)

        trade = list(self.router.queuedTrades(0))

        trade.pop(10)
        trade.pop(10)
        assert trade == [0, 0, self.user_1, *params], "Wrong data"
        assert (
            initial_user_tokenX_balance - final_user_tokenX_balance == self.total_fee
        ) and (
            final_router_tokenX_balance - initial_router_tokenX_balance
            == self.total_fee
        ), "Wrong token transferred"
        assert self.router.nextQueueId() == 1, "Wrong QueueId"
        assert (
            txn.events["InitiateTrade"] and txn.events["InitiateTrade"]["queueId"] == 0
        ), "Wrong event"

        txn = self.router.initiateTrade(
            *params,
            {"from": self.owner},
        )
        trade = list(self.router.queuedTrades(1))
        trade.pop(10)
        trade.pop(10)
        assert trade == [1, 0, self.owner, *params], "Wrong data"
        assert self.router.nextQueueId() == 2, "Wrong QueueId"
        assert self.router.userQueueCount(self.owner) == 1, "Wrong data"
        assert self.router.userQueueCount(self.user_1) == 1, "Wrong data"
        assert self.router.userQueuedIds(self.owner, 0) == 1, "Wrong data"

    def verify_trade_cancellation(self):
        with brownie.reverts("Router: Forbidden"):
            self.router.cancelQueuedTrade(0, {"from": self.user_2})
        with brownie.reverts("Router: Forbidden"):
            self.router.cancelQueuedTrade(0, {"from": self.owner})
        with brownie.reverts("Router: Forbidden"):
            self.router.cancelQueuedTrade(0, {"from": self.bot})

        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        initial_router_tokenX_balance = self.tokenX.balanceOf(self.router.address)

        txn = self.router.cancelQueuedTrade(0, {"from": self.user_1})

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_router_tokenX_balance = self.tokenX.balanceOf(self.router.address)

        with brownie.reverts("Router: Trade has already been opened"):
            self.router.cancelQueuedTrade(0, {"from": self.user_1})

        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"]["reason"] == "User Cancelled"
        ), "Trade should have been cancelled"

        assert not self.router.queuedTrades(0)[self.index], "Wrong value"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance == self.total_fee
        ) and (
            initial_router_tokenX_balance - final_router_tokenX_balance
            == self.total_fee
        ), "Wrong token transferred"

    def verify_trade_execution(self):
        open_params = [
            self.chain.time(),
            self.expected_strike * 2,
        ]

        txn = self.router.resolveQueuedTrades(
            [
                (
                    0,
                    *open_params,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )
        try:
            assert (
                txn.events["CancelTrade"]
                and txn.events["CancelTrade"]["reason"] == "Slippage limit exceeds"
            ), "Trade should have been cancelled"
            assert txn.events["OpenTrade"], "Trade should have been cancelled"
            should_fail = True
        except:
            should_fail = False

        assert not should_fail
        # Permissible strike bound is [396, 404]

        # Executing at the price just above the highest permissible  should cancel
        self.chain.snapshot()
        assert self.router.queuedTrades(1)[self.index], "Wrong value"
        queued_trade = self.router.queuedTrades(1)
        open_params = [
            queued_trade[10],
            404e8 + 1,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    *open_params,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"]["reason"] == "Slippage limit exceeds"
        ), "Trade should have been cancelled"

        assert not self.router.queuedTrades(1)[self.index], "Wrong value"
        self.chain.revert()

        # Executing at the price just below the lowest permissible  should cancel
        self.chain.snapshot()
        assert self.router.queuedTrades(1)[self.index], "Wrong value"
        queued_trade = self.router.queuedTrades(1)
        open_params = [
            queued_trade[10],
            396e8 - 1,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    *open_params,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )
        final_router_tokenX_balance = self.tokenX.balanceOf(self.router.address)
        assert final_router_tokenX_balance == 0, "Wrong router balance"
        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"]["reason"] == "Slippage limit exceeds"
        ), "Trade should have been cancelled"
        assert not self.router.queuedTrades(1)[self.index], "Wrong value"
        self.chain.revert()

        # Executing at the lowest permissible price should create option
        self.chain.snapshot()
        queued_trade = self.router.queuedTrades(1)
        open_params = [
            queued_trade[10],
            396e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    *open_params,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert txn.events["OpenTrade"], "Trade should have been cancelled"

        self.chain.revert()

        # Executing at the highest permissible price should create option
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        queued_trade = self.router.queuedTrades(1)
        open_params = [
            queued_trade[10],
            404e8,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    *open_params,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_1)
        final_router_tokenX_balance = self.tokenX.balanceOf(self.router.address)

        assert final_router_tokenX_balance == 0, "Wrong router balance"
        assert (
            final_user_tokenX_balance == initial_user_tokenX_balance
        ), "Wrong user balance"
        assert txn.events["OpenTrade"], "Trade should have been cancelled"
        assert not self.router.queuedTrades(1)[self.index], "Wrong value"

        # Initiating a trade with amount greater than 5% of available liquidity
        self.tokenX.transfer(self.user_2, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_2})
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
        txn = self.router.initiateTrade(
            *params,
            {"from": self.user_2},
        )

        # Executing the above trade should refund the user
        self.chain.snapshot()
        queued_trade = self.router.queuedTrades(2)
        open_params = [
            queued_trade[10],
            404e8,
        ]
        initial_user_tokenX_balance = self.tokenX.balanceOf(self.user_2)
        txn = self.router.resolveQueuedTrades(
            [
                (
                    2,
                    *open_params,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )

        final_user_tokenX_balance = self.tokenX.balanceOf(self.user_2)
        final_router_tokenX_balance = self.tokenX.balanceOf(self.router.address)

        assert final_router_tokenX_balance == 0, "Wrong router balance"
        assert (
            final_user_tokenX_balance - initial_user_tokenX_balance
        ) == self.total_fee - self.tokenX_options.options(1)[7], "Wrong user balance"
        assert txn.events["OpenTrade"], "Trade should have been cancelled"

        self.chain.revert()

        # Executing after the max wait time should cancel
        self.chain.sleep(61)

        txn = self.router.resolveQueuedTrades(
            [
                (
                    2,
                    *open_params,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"]["reason"] == "Wait time too high"
        ), "Trade should have been cancelled"

        # Executing multiple trades at once
        self.tokenX.transfer(self.user_2, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_2})
        self.tokenX.transfer(self.user_1, self.total_fee, {"from": self.owner})
        self.tokenX.approve(self.router.address, self.total_fee, {"from": self.user_1})

        self.router.initiateTrade(
            *params,
            {"from": self.user_2},
        )
        self.router.initiateTrade(
            *params,
            {"from": self.user_1},
        )
        open_params = [
            self.router.queuedTrades(3)[10],
            404e8,
        ]
        open_params_1 = [
            self.router.queuedTrades(4)[10],
            404e8 + 1,
        ]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    3,
                    *open_params,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params,
                    ),
                ),
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
        assert txn.events["OpenTrade"]["queueId"] == 3, "Wrong trade opened"
        assert txn.events["CancelTrade"]["queueId"] == 4, "Wrong trade cancelled"
        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"]["reason"] == "Slippage limit exceeds"
        ), "Trade should have been cancelled"

    def verify_trade_execution_with_cancellable_trades(self):
        self.tokenX.approve(
            self.router.address, self.total_fee * 500, {"from": self.owner}
        )

        # Cancel when amount is too high and partial fill is disabled
        self.chain.snapshot()

        txn = self.router.initiateTrade(
            self.total_fee * 200,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            int(5e2),  # Slippage higher than max value
            self.allow_partial_fill,
            self.referral_code,
            0,
            {"from": self.owner},
        )
        queued_trade = self.router.queuedTrades(5)
        open_params_1 = [queued_trade[10], 404e8]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    5,
                    *open_params_1,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_1,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"] and txn.events["CancelTrade"]["reason"] == "O29"
        ), "Trade should have been cancelled"

        # Cancel when amount is too high and partial fill is disabled
        self.chain.sleep(10 * 60 + 1)
        self.generic_pool.withdraw(
            self.generic_pool.availableBalance() * 100 // 100, {"from": self.owner}
        )
        self.router.initiateTrade(
            self.total_fee * 200,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            int(5e2),  # Slippage higher than max value
            self.allow_partial_fill,
            self.referral_code,
            0,
            {"from": self.owner},
        )
        queued_trade = self.router.queuedTrades(6)
        open_params_2 = [queued_trade[10], 404e8]
        txn = self.router.resolveQueuedTrades(
            [
                (
                    6,
                    *open_params_2,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_2,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"] and txn.events["CancelTrade"]["reason"] == "O31"
        ), "Trade should have been cancelled"
        self.chain.revert()

        self.router.initiateTrade(
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            int(5e2),  # Slippage higher than max value
            True,
            self.referral_code,
            0,
            {"from": self.owner},
        )
        self.chain.sleep(10 * 60 + 1)
        self.router.initiateTrade(
            self.total_fee,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            int(5e2),  # Slippage higher than max value
            True,
            self.referral_code,
            0,
            {"from": self.owner},
        )
        self.generic_pool.withdraw(
            self.generic_pool.availableBalance() * 90 // 100, {"from": self.owner}
        )

        self.router.initiateTrade(
            self.total_fee * 100,
            self.period,
            self.is_above,
            self.tokenX_options.address,
            self.expected_strike,
            int(5e2),  # Slippage higher than max value
            self.allow_partial_fill,
            self.referral_code,
            0,
            {"from": self.owner},
        )

        self.chain.snapshot()
        queued_trade = self.router.queuedTrades(5)
        open_params_1 = [queued_trade[10], 404e8]
        queued_trade = self.router.queuedTrades(6)
        open_params_2 = [queued_trade[10], 404e8]
        queued_trade = self.router.queuedTrades(7)
        open_params_3 = [queued_trade[10], 404e8]
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
                (
                    6,
                    *open_params_2,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_2,
                    ),
                ),
                (
                    7,
                    *open_params_3,
                    self.get_signature(
                        self.tokenX_options.address,
                        *open_params_3,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"][0]["queueId"] == 5
            and txn.events["CancelTrade"][0]["reason"] == "Wait time too high"
        ), "Trade should have been cancelled"
        assert (
            txn.events["CancelTrade"]
            and txn.events["CancelTrade"][1]["queueId"] == 7
            and txn.events["CancelTrade"][1]["reason"] == "O29"
        ), "Trade should have been cancelled"
        assert (
            txn.events["OpenTrade"] and txn.events["OpenTrade"]["queueId"] == 6
        ), "Trade should have been cancelled"

        self.chain.revert()

    def verify_keeper(self):

        queued_trade = self.router.queuedTrades(1)
        open_params = [
            self.tokenX_options.address,
            queued_trade[10],
            self.expected_strike,
        ]
        open_params_1 = [
            self.tokenX_options.address,
            queued_trade[10] + 1,
            self.expected_strike,
        ]
        open_params_2 = [
            self.bfr_options,
            queued_trade[10] + 1,
            self.expected_strike,
        ]

        with brownie.reverts():  # Keeper not verified
            self.router.resolveQueuedTrades(
                [
                    (
                        1,
                        *open_params[1:],
                        self.get_signature(
                            *open_params,
                        ),
                    )
                ],
                {"from": self.user_2},
            )

        # Should allow anyone when not in private mode
        self.chain.snapshot()

        # Shouldn't allow random user to change keeper mode
        with brownie.reverts():  # Keeper not verified
            self.router.setInPrivateKeeperMode(
                {"from": self.user_2},
            )
        self.router.setInPrivateKeeperMode()
        self.router.resolveQueuedTrades(
            [
                (
                    1,
                    *open_params[1:],
                    self.get_signature(
                        *open_params,
                    ),
                )
            ],
            {"from": self.user_2},
        )

        self.chain.revert()

        self.router.setKeeper(self.bot, True)

        self.chain.snapshot()

        # Signature match failed due to wrong token
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    queued_trade[10],
                    self.expected_strike,
                    self.get_signature(
                        *open_params_2,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert txn.events["FailResolve"], "Wrong event"
        assert self.router.queuedTrades(1)[self.index], "Wrong state"

        # Signature match failed due to price mismatch
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    queued_trade[10],
                    self.expected_strike + 1,
                    self.get_signature(
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert txn.events["FailResolve"], "Wrong event"
        assert self.router.queuedTrades(1)[self.index], "Wrong state"

        # Signature match failed due to time mismatch
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    self.chain.time(),
                    self.expected_strike,
                    self.get_signature(
                        *open_params,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert txn.events["FailResolve"], "Wrong event"
        assert self.router.queuedTrades(1)[self.index], "Wrong state"

        # Signature match failed due to wrong publisher
        spam_publisher = self.accounts.add()
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    *open_params[1:],
                    self.get_signature(*open_params, spam_publisher),
                )
            ],
            {"from": self.bot},
        )
        assert txn.events["FailResolve"], "Wrong event"
        assert self.router.queuedTrades(1)[self.index], "Wrong state"

        # Nothing should happen if the time is wrong
        txn = self.router.resolveQueuedTrades(
            [
                (
                    1,
                    *open_params_1[1:],
                    self.get_signature(
                        *open_params_1,
                    ),
                )
            ],
            {"from": self.bot},
        )
        assert not txn.events, "SHouldn't change anything"
        assert self.router.queuedTrades(1)[12], "SHouldn't change anything"
        self.chain.revert()

    def verify_option_unlocking(self):
        option_1 = self.tokenX_options.options(0)
        option_2 = self.tokenX_options.options(1)

        close_params_1 = (self.tokenX_options.address, option_1[5], option_1[1] * 2)
        close_params_2 = (self.tokenX_options.address, option_2[5], option_2[1] // 2)
        with brownie.reverts():  # Keeper not verified
            self.router.unlockOptions(
                [
                    (
                        0,
                        *close_params_1,
                        self.get_signature(
                            *close_params_1,
                        ),
                    ),
                ],
                {"from": self.user_2},
            )
        txn = self.router.unlockOptions(
            [
                (
                    1,
                    *close_params_1,
                    self.get_signature(
                        *close_params_1,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["FailUnlock"]["reason"] == "Router: Wrong price"
        ), "Wrong event"

        txn = self.router.unlockOptions(
            [
                (
                    0,
                    *close_params_1,
                    self.get_signature(
                        *close_params_2,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        assert (
            txn.events["FailUnlock"]["reason"] == "Router: Signature didn't match"
        ), "Wrong event"

        # Should unlock with the right params
        self.chain.snapshot()
        user = self.tokenX_options.ownerOf(0)
        initial_user_balance = self.tokenX.balanceOf(user)
        txn = self.router.unlockOptions(
            [
                (
                    0,
                    *close_params_1,
                    self.get_signature(
                        *close_params_1,
                    ),
                ),
                (
                    1,
                    *close_params_2,
                    self.get_signature(
                        *close_params_2,
                    ),
                ),
            ],
            {"from": self.bot},
        )
        final_user_balance = self.tokenX.balanceOf(user)

        assert txn.events["Expire"]["id"] == 1 and txn.events["Exercise"]["id"] == 0
        assert (
            final_user_balance - initial_user_balance
            == txn.events["Exercise"]["profit"]
        ), "Wrong incentive"
        self.chain.revert()

    def complete_flow_test(self):
        self.init()
        self.verify_owner()
        self.verify_target_contract_registration()
        self.verify_trade_initiation()
        self.verify_trade_cancellation()
        self.verify_keeper()
        self.verify_trade_execution()
        self.verify_trade_execution_with_cancellable_trades()
        self.verify_multitoken_router()
        self.verify_option_unlocking()


def test_router(contracts, accounts, chain):

    tokenX = contracts["tokenX"]
    binary_pool_atm = contracts["binary_pool_atm"]
    binary_options_config_atm = contracts["binary_options_config_atm"]
    router = contracts["router"]
    binary_european_options_atm = contracts["binary_european_options_atm"]

    ibfr_contract = contracts["ibfr_contract"]
    bfr_pool_atm = contracts["bfr_pool_atm"]
    bfr_binary_options_config_atm = contracts["bfr_binary_options_config_atm"]
    bfr_binary_european_options_atm = contracts["bfr_binary_european_options_atm"]
    publisher = contracts["publisher"]

    total_fee = int(1e6)
    liquidity = int(1500e6)
    period = 600
    isYes = True
    isAbove = True
    option = Router(
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
        ibfr_contract,
        bfr_pool_atm,
        bfr_binary_options_config_atm,
        bfr_binary_european_options_atm,
        publisher,
    )
    option.complete_flow_test()
