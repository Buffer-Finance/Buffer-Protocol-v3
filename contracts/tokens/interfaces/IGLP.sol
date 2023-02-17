// SPDX-License-Identifier: BUSL-1.1

pragma solidity 0.8.16;

interface IBLP {
    function mint(address _account, uint256 _amount) external;

    function burn(address _account, uint256 _amount) external;
}
