## Documentation

Refer to this [link](https://docs.google.com/document/d/1mgnjQ1n5nbKeSUjqY5av2akqBq_hmQrVAZeD4Gh5Cao/edit)

## Solidity Metrics

![Metrics](https://github.com/bufferfinance/Buffer-Protocol-v2/blob/master/metrics.png?raw=true)

## Installation

[Install Brownie](https://eth-brownie.readthedocs.io/en/stable/install.html), if you haven't already.

## Compiling

To build and compile:

```bash
brownie compile
```

## Testing

To run the tests:

```bash
brownie test
```

## Coverage

To get the coverage:

```bash
brownie test -n auto --coverage
```

```bash
  contract: BufferBinaryOptions - 95.2%
    BufferBinaryOptions._getMaxUtilization - 100.0%
    BufferBinaryOptions._getbaseSettlementFeePercentage - 100.0%
    BufferBinaryOptions.checkParams - 100.0%
    BufferBinaryOptions.configure - 100.0%
    BufferBinaryOptions.min - 100.0%
    BufferBinaryOptions.runInitialChecks - 100.0%
    BufferBinaryOptions.unlock - 96.4%
    BufferBinaryOptions.isInCreationWindow - 92.5%
    BufferBinaryOptions._getSettlementFeeDiscount - 90.0%
    BufferBinaryOptions._processReferralRebate - 83.3%

  contract: BufferBinaryPool - 92.0%
    BufferBinaryPool._beforeTokenTransfer - 100.0%
    BufferBinaryPool._getUnlockedLiquidity - 100.0%
    BufferBinaryPool._unlock - 100.0%
    BufferBinaryPool._validateHandler - 100.0%
    BufferBinaryPool.shareOf - 100.0%
    BufferBinaryPool.send - 95.0%
    BufferBinaryPool._provide - 91.7%
    BufferBinaryPool._withdraw - 91.7%
    BufferBinaryPool.lock - 91.7%
    BufferBinaryPool.transferFrom - 91.7%
    BufferBinaryPool.divCeil - 50.0%

  contract: BufferRouter - 100.0%
    BufferRouter._openQueuedTrade - 100.0%
    BufferRouter._validateKeeper - 100.0%
    BufferRouter.cancelQueuedTrade - 100.0%
    BufferRouter.initiateTrade - 100.0%
    BufferRouter.resolveQueuedTrades - 100.0%
    BufferRouter.unlockOptions - 100.0%

  contract: OptionsConfig - 90.0%
    OptionsConfig.setAssetUtilizationLimit - 100.0%
    OptionsConfig.setMaxPeriod - 100.0%
    OptionsConfig.setMinPeriod - 100.0%
    OptionsConfig.setOverallPoolUtilizationLimit - 100.0%

  contract: ReferralStorage - 87.5%
    ReferralStorage.getTraderReferralInfo - 100.0%
    ReferralStorage.registerCode - 100.0%
    ReferralStorage.setCodeOwner - 100.0%

```
