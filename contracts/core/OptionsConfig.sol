pragma solidity 0.8.4;

// SPDX-License-Identifier: BUSL-1.1

import "./BufferBinaryPool.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @author Heisenberg
 * @title Buffer Options Config
 * @notice Maintains all the configurations for the options contracts
 */
contract OptionsConfig is Ownable, IOptionsConfig {
    BufferBinaryPool public pool;

    address public override settlementFeeDisbursalContract;
    address public override whitelistStorage;
    address public override traderNFTContract;
    uint16 public override assetUtilizationLimit = 10e2;
    uint16 public override overallPoolUtilizationLimit = 64e2;
    uint256 public override impliedProbability;
    mapping(uint32 => bool) public override periodWhitelist;

    uint16 public override optionFeePerTxnLimitPercent = 5e2;
    uint256 public override minFee = 1e6;

    mapping(uint8 => Window) public override marketTimes;

    constructor(BufferBinaryPool _pool) {
        pool = _pool;
    }

    function settraderNFTContract(address value) external onlyOwner {
        traderNFTContract = value;
        emit UpdatetraderNFTContract(value);
    }

    function setMinFee(uint256 value) external onlyOwner {
        minFee = value;
        emit UpdateMinFee(value);
    }

    function setImpliedProbability(uint256 value) external onlyOwner {
        impliedProbability = value;
        emit UpdateImpliedProbability(value);
    }

    function setWhitelistStorage(address value) external onlyOwner {
        whitelistStorage = value;
        emit UpdateWhitelistStorage(value);
    }

    function setSettlementFeeDisbursalContract(address value)
        external
        onlyOwner
    {
        settlementFeeDisbursalContract = value;
        emit UpdateSettlementFeeDisbursalContract(value);
    }

    function setOptionFeePerTxnLimitPercent(uint16 value) external onlyOwner {
        optionFeePerTxnLimitPercent = value;
        emit UpdateOptionFeePerTxnLimitPercent(value);
    }

    function setOverallPoolUtilizationLimit(uint16 value) external onlyOwner {
        require(value <= 100e2 && value > 0, "Wrong utilization value");
        overallPoolUtilizationLimit = value;
        emit UpdateOverallPoolUtilizationLimit(value);
    }

    function setAssetUtilizationLimit(uint16 value) external onlyOwner {
        require(value <= 100e2 && value > 0, "Wrong utilization value");
        assetUtilizationLimit = value;
        emit UpdateAssetUtilizationLimit(value);
    }

    function setMarketTime(Window[] memory windows) external onlyOwner {
        for (uint8 index = 0; index < windows.length; index++) {
            marketTimes[index] = windows[index];
        }
        emit UpdateMarketTime();
    }

    function setAllowedPeriods(uint32[] memory periods, bool[] memory isAllowed) external onlyOwner {
        require(periods.length == isAllowed.length, "Invalid input");
        for (uint256 index = 0; index < periods.length; index++) {
            periodWhitelist[periods[index]] = isAllowed[index];
            emit UpdateAllowedPeriods(periods[index], isAllowed[index]);
        }
    }

}
