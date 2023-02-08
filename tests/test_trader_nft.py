import brownie


def test_nft_creation(contracts, accounts, chain):

    trader_nft_contract = contracts["trader_nft_contract"]

    admin = accounts[9]
    metadata_hash = "QmRu61jShPgiQp33UA5RNcULAvLU5JEPbnXGqEtBmVcdMg"

    assert trader_nft_contract.baseURI() == "https://gateway.pinata.cloud/ipfs/"

    chain.snapshot()
    assert (
        trader_nft_contract.nftBasePrice() == 2e18
    ), "Pre defined NFTBasePrice is 2 BNB"

    trader_nft_contract.setNftBasePrice(5e18, {"from": accounts[0]})

    assert trader_nft_contract.nftBasePrice() == 5e18, "setNftBasePrice verified"
    chain.revert()

    chain.snapshot()
    with brownie.reverts(""):  # Wrong role
        trader_nft_contract.setMaxNFTMintLimit(
            1, {"from": accounts[1], "value": "1 ether"}
        )

    trader_nft_contract.setMaxNFTMintLimit(0, {"from": accounts[0]})
    assert (
        trader_nft_contract.maxNFTMintLimit() == 0
    ), "setMaxNFTMintLimit function should go through"

    with brownie.reverts("Maximum Limit for minting NFTs reached"):
        trader_nft_contract.claim({"from": accounts[1], "value": "2 ether"})

    chain.revert()

    with brownie.reverts("Wrong value"):
        trader_nft_contract.claim({"from": accounts[1], "value": "0 ether"})

    account_initial_balance = accounts[1].balance()
    admin_initial_balance = admin.balance()

    nft = trader_nft_contract.claim({"from": accounts[1], "value": "2 ether"})

    account_final_balance = accounts[1].balance()
    admin_final_balance = admin.balance()

    claimTokenId = nft.events["Claim"][0]["claimTokenId"]
    account = nft.events["Claim"][0]["account"]

    assert nft, "Claim should go through"
    assert trader_nft_contract.claimTokenIdCounter() == 1, "setNftBasePrice verified"
    assert nft.return_value == claimTokenId == 0, "Since this is the first NFT minted"
    assert account == accounts[1], "The account should be the same as of the msg.sender"
    assert (
        account_initial_balance - account_final_balance == 2e18
    ), "Balance difference should be the amount paid"

    assert (
        admin_final_balance - admin_initial_balance == 2e18
    ), "Balance difference should be the amount paid"

    tier = 5
    with brownie.reverts():  # Wrong role
        trader_nft_contract.safeMint(
            account,
            metadata_hash,
            tier,
            claimTokenId,
            {"from": accounts[1]},
        )

    mint = trader_nft_contract.safeMint(
        account,
        metadata_hash,
        tier,
        claimTokenId,
        {"from": accounts[0]},
    )

    tokenId = mint.events["Mint"][0]["tokenId"]
    _account = mint.events["Mint"][0]["account"]
    _tier = mint.events["Mint"][0]["tier"]

    assert mint.return_value == tokenId == 0, "Since this is the first NFT minted"
    assert (
        _account == account == accounts[1]
    ), "The account should be the same as of the msg.sender"
    assert _tier == tier, "Tier should be the same as sent to the mint function"

    with brownie.reverts("Token already minted"):
        trader_nft_contract.safeMint(
            account,
            metadata_hash,
            tier,
            claimTokenId,
            {"from": accounts[0]},
        )
    assert (
        trader_nft_contract.tokenURI(tokenId)
        == f"https://gateway.pinata.cloud/ipfs/{metadata_hash}"
    )
    assert trader_nft_contract.tokenTierMappings(tokenId) == tier, "Tiers should tally"

    assert trader_nft_contract.tokenIdCounter() == 1, "setNftBasePrice verified"

    assert trader_nft_contract.tokenMintMappings(claimTokenId), "Mint verified"

    # the user shouldn't get charged more than the base fee
    account_initial_balance = accounts[1].balance()
    admin_initial_balance = admin.balance()

    nft = trader_nft_contract.claim({"from": accounts[1], "value": "10 ether"})

    account_final_balance = accounts[1].balance()
    admin_final_balance = admin.balance()

    assert trader_nft_contract.claimTokenIdCounter() == 2, "setNftBasePrice verified"
    assert (
        account_initial_balance - account_final_balance == 2e18
    ), "Balance difference should be the amount paid"

    # Should always be max
    chain.snapshot()
    mint = trader_nft_contract.safeMint(
        account,
        metadata_hash,
        6,
        claimTokenId + 1,
        {"from": accounts[0]},
    )
    assert trader_nft_contract.tokenTierMappings(tokenId + 1) == 6, "Tiers should tally"
    chain.revert()

    chain.snapshot()
    mint = trader_nft_contract.safeMint(
        account,
        metadata_hash,
        4,
        claimTokenId + 1,
        {"from": accounts[0]},
    )
    assert trader_nft_contract.tokenTierMappings(tokenId + 1) == 4, "Tiers should tally"
    chain.revert()
