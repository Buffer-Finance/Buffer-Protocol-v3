pragma solidity 0.8.16;

// SPDX-License-Identifier: BUSL-1.1

import "@openzeppelin/contracts/access/Ownable.sol";
import "../interfaces/Interfaces.sol";

/**
 * @author Heisenberg
 * @title Buffer MarketSetter
 * @notice Set Market times for trading on Forex and Commodities
 */
contract MarketSetter is Ownable, IMarketSetter {
    mapping(uint8 => Window) public marketTimes;

    function getMarketTimes(uint8 period)
        public
        view
        returns (
            uint8,
            uint8,
            uint8,
            uint8
        )
    {
        Window memory marketTime = marketTimes[period];
        return (
            marketTime.startHour,
            marketTime.startMinute,
            marketTime.endHour,
            marketTime.endMinute
        );
    }

    function setMarketTime(Window[] memory windows) external onlyOwner {
        for (uint8 index = 0; index < windows.length; index++) {
            marketTimes[index] = windows[index];
        }
        emit UpdateMarketTime();
    }

    /**
     * @notice Checks if the market is open at the time of option creation and execution.
     * Used only for forex options
     */
    function isInCreationWindow(uint256 period)
        public
        view
        override
        returns (bool)
    {
        uint256 currentTime = block.timestamp;
        uint256 currentDay = ((currentTime / 86400) + 4) % 7;
        uint256 expirationDay = (((currentTime + period) / 86400) + 4) % 7;

        uint256 currentHour = (currentTime / 3600) % 24;
        uint256 currentMinute = (currentTime % 3600) / 60;
        uint256 expirationHour = ((currentTime + period) / 3600) % 24;
        uint256 expirationMinute = ((currentTime + period) % 3600) / 60;
        (
            uint8 startHour,
            uint8 startMinute,
            uint8 endHour,
            uint8 endMinute
        ) = getMarketTimes(uint8(currentDay));
        if (
            currentHour == startHour && startHour == endHour && startHour == 0
        ) {
            if (
                isInLeftWindow(
                    currentHour,
                    currentMinute,
                    expirationHour,
                    expirationMinute
                )
            ) {
                return true;
            } else {
                (startHour, startMinute, endHour, endMinute) = getMarketTimes(
                    uint8(expirationDay)
                );
                if (endHour == endMinute && endMinute == 0) {
                    return true;
                } else if (
                    isInLeftWindow(
                        expirationHour,
                        expirationMinute,
                        startHour,
                        startMinute
                    )
                ) {
                    return true;
                }
            }
            return false;
        }
        if (
            isInLeftWindow(
                currentHour,
                currentMinute,
                startHour,
                startMinute
            ) &&
            isInLeftWindow(
                expirationHour,
                expirationMinute,
                startHour,
                startMinute
            ) &&
            isInLeftWindow(
                currentHour,
                currentMinute,
                expirationHour,
                expirationMinute
            )
        ) {
            return true;
        } else if (
            isInRightWindow(currentHour, currentMinute, endHour, endMinute)
        ) {
            if (
                isInLeftWindow(
                    currentHour,
                    currentMinute,
                    expirationHour,
                    expirationMinute
                )
            ) {
                return true;
            } else {
                (endHour, endMinute, , ) = getMarketTimes(uint8(expirationDay));
                if (
                    isInLeftWindow(
                        expirationHour,
                        expirationMinute,
                        endHour,
                        endMinute
                    )
                ) {
                    return true;
                }
            }
        }

        return false;
    }

    function isInLeftWindow(
        uint256 h1,
        uint256 m1,
        uint256 h2,
        uint256 m2
    ) public view returns (bool) {
        return (h1 < h2 || (h1 == h2 && m1 < m2));
    }

    function isInRightWindow(
        uint256 h1,
        uint256 m1,
        uint256 h2,
        uint256 m2
    ) public view returns (bool) {
        return (h1 > h2 || (h1 == h2 && m1 > m2));
    }
}
