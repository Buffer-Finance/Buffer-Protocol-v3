// SPDX-License-Identifier: BUSL-1.1

pragma solidity 0.8.4;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./interfaces/Interfaces.sol";

/**
 * @author Heisenberg
 * @title Buffer Whitelist Storage contract
 */

contract Whitelist {
    mapping(address => bool) public whitelistedUsers;

    function isWhitelist(address user) external view returns (bool) {
        return !whitelistedUsers[user];
    }
}
