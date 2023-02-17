#!/usr/bin/python3

import time
from enum import IntEnum

import pytest

ONE_DAY = 86400


class OptionType(IntEnum):
    ALL = 0
    PUT = 1
    CALL = 2
    NONE = 3


@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test, to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass


@pytest.fixture(scope="module")
def contracts(
    accounts,
    USDC,
    BFR,
    BufferBinaryPool,
    BufferBinaryOptions,
    OptionsConfig,
    BufferRouter,
    FakeTraderNFT,
    ReferralStorage,
    OptionMath,
    ABDKMath64x64,
    Whitelist,
    MarketSetter,
):

    publisher = accounts.add()
    ibfr_contract = BFR.deploy({"from": accounts[0]})
    sfd = accounts.add()
    tokenX = USDC.deploy({"from": accounts[0]})
    whitelist = Whitelist.deploy({"from": accounts[0]})
    marketSetter = MarketSetter.deploy({"from": accounts[0]})
    binary_pool_atm = BufferBinaryPool.deploy(
        tokenX.address, 600, {"from": accounts[0]}
    )
    OPTION_ISSUER_ROLE = binary_pool_atm.OPTION_ISSUER_ROLE()
    router = BufferRouter.deploy(publisher, {"from": accounts[0]})
    trader_nft = FakeTraderNFT.deploy(accounts[9], {"from": accounts[0]})
    ABDKMath64x64.deploy({"from": accounts[0]})
    OptionMath.deploy({"from": accounts[0]})

    print("############### Binary ATM Options 1 #################")
    binary_options_config_atm = OptionsConfig.deploy(
        binary_pool_atm.address,
        {"from": accounts[0]},
    )
    # binary_options_config_atm.setWhitelistStorage(whitelist, {"from": accounts[0]})
    referral_contract = ReferralStorage.deploy({"from": accounts[0]})

    binary_european_options_atm = BufferBinaryOptions.deploy(
        tokenX.address,
        binary_pool_atm.address,
        binary_options_config_atm.address,
        referral_contract.address,
        1,
        "ETH_BTC",
        {"from": accounts[0]},
    )

    binary_options_config_atm.setSettlementFeeDisbursalContract(
        sfd,
        {"from": accounts[0]},
    )

    binary_european_options_atm.approvePoolToTransferTokenX(
        {"from": accounts[0]},
    )
    binary_pool_atm.grantRole(
        OPTION_ISSUER_ROLE,
        binary_european_options_atm.address,
        {"from": accounts[0]},
    )
    ROUTER_ROLE = binary_european_options_atm.ROUTER_ROLE()
    binary_european_options_atm.grantRole(
        ROUTER_ROLE,
        router.address,
        {"from": accounts[0]},
    )

    # binary_options_config_atm.settraderNFTContract(trader_nft.address)
    binary_european_options_atm.configure(
        15e2, 15e2, [5, 10, 16, 24], {"from": accounts[0]}
    )

    print("############### Binary ATM Options 2 #################")
    binary_options_config_atm_2 = OptionsConfig.deploy(
        binary_pool_atm.address,
        {"from": accounts[0]},
    )
    # binary_options_config_atm_2.setWhitelistStorage(whitelist, {"from": accounts[0]})

    binary_european_options_atm_2 = BufferBinaryOptions.deploy(
        tokenX.address,
        binary_pool_atm.address,
        binary_options_config_atm_2.address,
        referral_contract.address,
        1,
        "ETH_BTC",
        {"from": accounts[0]},
    )

    binary_options_config_atm_2.setSettlementFeeDisbursalContract(
        sfd,
        {"from": accounts[0]},
    )

    binary_european_options_atm_2.approvePoolToTransferTokenX(
        {"from": accounts[0]},
    )
    binary_european_options_atm_2.grantRole(
        ROUTER_ROLE,
        router.address,
        {"from": accounts[0]},
    )

    binary_pool_atm.grantRole(
        OPTION_ISSUER_ROLE,
        binary_european_options_atm_2.address,
        {"from": accounts[0]},
    )
    # binary_options_config_atm_2.settraderNFTContract(trader_nft.address)
    binary_european_options_atm_2.configure(
        15e2, 15e2, [5, 10, 16, 24], {"from": accounts[0]}
    )

    print("############### Binary ATM Options 3 #################")
    binary_options_config_atm_3 = OptionsConfig.deploy(
        binary_pool_atm.address,
        {"from": accounts[0]},
    )
    # binary_options_config_atm_3.setWhitelistStorage(whitelist, {"from": accounts[0]})

    binary_european_options_atm_3 = BufferBinaryOptions.deploy(
        tokenX.address,
        binary_pool_atm.address,
        binary_options_config_atm_3.address,
        referral_contract.address,
        0,
        "ETH_BTC",
        {"from": accounts[0]},
    )

    binary_options_config_atm_3.setSettlementFeeDisbursalContract(
        sfd,
        {"from": accounts[0]},
    )

    binary_european_options_atm_3.approvePoolToTransferTokenX(
        {"from": accounts[0]},
    )
    binary_pool_atm.grantRole(
        OPTION_ISSUER_ROLE,
        binary_european_options_atm_3.address,
        {"from": accounts[0]},
    )
    binary_european_options_atm_3.grantRole(
        ROUTER_ROLE,
        router.address,
        {"from": accounts[0]},
    )

    # binary_options_config_atm_3.settraderNFTContract(trader_nft.address)
    binary_european_options_atm_3.configure(
        15e2, 15e2, [5, 10, 16, 24], {"from": accounts[0]}
    )

    print("############### Deploying BFR pool contracts #################")

    bfr_pool_atm = BufferBinaryPool.deploy(
        ibfr_contract.address, 600, {"from": accounts[0]}
    )

    bfr_binary_options_config_atm = OptionsConfig.deploy(
        bfr_pool_atm.address,
        {"from": accounts[0]},
    )
    # bfr_binary_options_config_atm.setWhitelistStorage(whitelist, {"from": accounts[0]})

    bfr_binary_european_options_atm = BufferBinaryOptions.deploy(
        ibfr_contract.address,
        bfr_pool_atm.address,
        bfr_binary_options_config_atm.address,
        referral_contract.address,
        1,
        "ETH_BTC",
        {"from": accounts[0]},
    )

    bfr_binary_options_config_atm.setSettlementFeeDisbursalContract(
        sfd,
        {"from": accounts[0]},
    )

    bfr_binary_european_options_atm.approvePoolToTransferTokenX(
        {"from": accounts[0]},
    )
    OPTION_ISSUER_ROLE = bfr_pool_atm.OPTION_ISSUER_ROLE()
    bfr_pool_atm.grantRole(
        OPTION_ISSUER_ROLE,
        bfr_binary_european_options_atm.address,
        {"from": accounts[0]},
    )

    bfr_binary_european_options_atm.grantRole(
        ROUTER_ROLE,
        router.address,
        {"from": accounts[0]},
    )

    # bfr_binary_options_config_atm.settraderNFTContract(trader_nft.address)
    bfr_binary_european_options_atm.configure(
        15e2, 15e2, [5, 10, 16, 24], {"from": accounts[0]}
    )
    referral_contract.configure([4, 10, 16], [25e3, 50e3, 75e3], {"from": accounts[0]})

    router.setContractRegistry(bfr_binary_european_options_atm.address, True)
    router.setContractRegistry(binary_european_options_atm_2.address, True)
    router.setContractRegistry(binary_european_options_atm_3.address, True)

    return {
        "tokenX": tokenX,
        "referral_contract": referral_contract,
        "binary_pool_atm": binary_pool_atm,
        "binary_options_config_atm": binary_options_config_atm,
        "binary_european_options_atm": binary_european_options_atm,
        "binary_options_config_atm_2": binary_options_config_atm_2,
        "binary_european_options_atm_2": binary_european_options_atm_2,
        "binary_options_config_atm_3": binary_options_config_atm_3,
        "binary_european_options_atm_3": binary_european_options_atm_3,
        "router": router,
        "trader_nft_contract": trader_nft,
        "ibfr_contract": ibfr_contract,
        "bfr_pool_atm": bfr_pool_atm,
        "bfr_binary_options_config_atm": bfr_binary_options_config_atm,
        "bfr_binary_european_options_atm": bfr_binary_european_options_atm,
        "publisher": publisher,
        "settlement_fee_disbursal": sfd,
        "market_setter": marketSetter,
    }
