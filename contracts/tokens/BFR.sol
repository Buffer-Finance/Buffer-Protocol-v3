// SPDX-License-Identifier: BUSL-1.1

pragma solidity 0.8.4;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @author Heisenberg
 * @title Buffer iBFR Token
 * @notice The central token to the Buffer ecosystem
 */
contract BFR is ERC20("Buffer Token", "BFR") {
    constructor() {
        uint256 INITIAL_SUPPLY = 100 * 10**6 * 10**decimals();
        _mint(msg.sender, INITIAL_SUPPLY);
    }
}
