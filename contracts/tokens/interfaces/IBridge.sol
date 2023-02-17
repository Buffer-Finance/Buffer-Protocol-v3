// SPDX-License-Identifier: BUSL-1.1

pragma solidity 0.8.16;

interface IBridge {
    function wrap(uint256 _amount, address _receiver) external;

    function unwrap(uint256 _amount, address _receiver) external;
}
