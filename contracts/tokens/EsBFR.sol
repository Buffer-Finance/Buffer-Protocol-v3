// SPDX-License-Identifier: BUSL-1.1

pragma solidity 0.8.16;

import "../tokens/MintableBaseToken.sol";

contract EsBFR is MintableBaseToken {
    constructor() MintableBaseToken("Escrowed BFR", "esBFR", 0) {}

    function id() external pure returns (string memory _name) {
        return "esBFR";
    }
}
