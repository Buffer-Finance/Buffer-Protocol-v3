// SPDX-License-Identifier: BUSL-1.1

pragma solidity 0.8.16;

import "@openzeppelin/contracts/utils/Address.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract FakeUSDC is ERC20("USDC", "USDC"), AccessControl {
    mapping(address => bool) public approvedAddresses;

    constructor() {
        uint256 INITIAL_SUPPLY = 1000 * 10**6 * 10**decimals();
        _mint(msg.sender, INITIAL_SUPPLY);
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    function decimals() public view virtual override returns (uint8) {
        return 6;
    }

    function approveAddress(address addressToApprove)
        public
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        approvedAddresses[addressToApprove] = true;
    }

    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal virtual override {
        if (
            from != address(0) &&
            to != address(0) &&
            approvedAddresses[to] == false &&
            approvedAddresses[from] == false
        ) {
            revert("Token transfer not allowed");
        }
    }
}
