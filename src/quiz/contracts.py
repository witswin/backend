from statistics import median
import web3
import logging

from django.conf import settings
from web3 import Web3
from eth_account import Account


logger = logging.getLogger(__name__)

wits_contract_abi = [
    {"inputs": [], "name": "AccessControlBadConfirmation", "type": "error"},
    {
        "inputs": [
            {"internalType": "address", "name": "account", "type": "address"},
            {"internalType": "bytes32", "name": "neededRole", "type": "bytes32"},
        ],
        "name": "AccessControlUnauthorizedAccount",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "address", "name": "target", "type": "address"}],
        "name": "AddressEmptyCode",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "AddressInsufficientBalance",
        "type": "error",
    },
    {"inputs": [], "name": "EnforcedPause", "type": "error"},
    {"inputs": [], "name": "ExpectedPause", "type": "error"},
    {"inputs": [], "name": "FailedInnerCall", "type": "error"},
    {"inputs": [], "name": "InvalidInitialization", "type": "error"},
    {"inputs": [], "name": "NotInitializing", "type": "error"},
    {
        "inputs": [{"internalType": "address", "name": "token", "type": "address"}],
        "name": "SafeERC20FailedOperation",
        "type": "error",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address[]",
                "name": "users",
                "type": "address[]",
            },
            {
                "indexed": False,
                "internalType": "uint256[]",
                "name": "amounts",
                "type": "uint256[]",
            },
        ],
        "name": "Distribute",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "uint64",
                "name": "version",
                "type": "uint64",
            }
        ],
        "name": "Initialized",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "account",
                "type": "address",
            }
        ],
        "name": "Paused",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "role",
                "type": "bytes32",
            },
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "previousAdminRole",
                "type": "bytes32",
            },
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "newAdminRole",
                "type": "bytes32",
            },
        ],
        "name": "RoleAdminChanged",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "role",
                "type": "bytes32",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "account",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "sender",
                "type": "address",
            },
        ],
        "name": "RoleGranted",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "role",
                "type": "bytes32",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "account",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "sender",
                "type": "address",
            },
        ],
        "name": "RoleRevoked",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "account",
                "type": "address",
            }
        ],
        "name": "Unpaused",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "DEFAULT_ADMIN_ROLE",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "DISTRIBUTOR_ROLE",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "PAUSER_ROLE",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "UNPAUSER_ROLE",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "USDC",
        "outputs": [{"internalType": "contract IERC20", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address[]", "name": "users", "type": "address[]"},
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"},
        ],
        "name": "distribute",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "role", "type": "bytes32"}],
        "name": "getRoleAdmin",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "role", "type": "bytes32"},
            {"internalType": "uint256", "name": "index", "type": "uint256"},
        ],
        "name": "getRoleMember",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "role", "type": "bytes32"}],
        "name": "getRoleMemberCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "role", "type": "bytes32"},
            {"internalType": "address", "name": "account", "type": "address"},
        ],
        "name": "grantRole",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "role", "type": "bytes32"},
            {"internalType": "address", "name": "account", "type": "address"},
        ],
        "name": "hasRole",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "_usdc", "type": "address"},
            {"internalType": "address", "name": "_admin", "type": "address"},
        ],
        "name": "initialize",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "paused",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "role", "type": "bytes32"},
            {
                "internalType": "address",
                "name": "callerConfirmation",
                "type": "address",
            },
        ],
        "name": "renounceRole",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "role", "type": "bytes32"},
            {"internalType": "address", "name": "account", "type": "address"},
        ],
        "name": "revokeRole",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes4", "name": "interfaceId", "type": "bytes4"}],
        "name": "supportsInterface",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


wits_contract_address = "0x1042a37E7E0Fc24adCFbbF82919Da8631003b9D1"


class SafeContractException(Exception):
    pass


class ContractManager:
    def __init__(self, address=None, private_key=None, abi=None) -> None:
        self.instance = Web3(Web3.HTTPProvider(settings.OP_MAINNET_RPC_URL))
        self.contract = self.instance.eth.contract(
            address=address or wits_contract_address, abi=abi or wits_contract_abi
        )
        self.private_key = private_key or settings.OPTIMISM_DISTRIBUTOR_PRIVATE_KEY

        if self.instance.is_connected() is False:
            raise SafeContractException("instance must be connected")

        if not settings.OPTIMISM_DISTRIBUTOR_PRIVATE_KEY:
            raise SafeContractException("Optimism private key must be present")

        self.account = Account.from_key(
            private_key or settings.OPTIMISM_DISTRIBUTOR_PRIVATE_KEY
        )

    def estimate_gas(self):
        block = self.instance.eth.get_block("latest", full_transactions=True)

        return int(median(t.gas for t in block.transactions))

    def distribute(self, addresses, amounts):
        distribute = self.contract.functions.distribute(addresses, amounts)

        transaction = distribute.build_transaction(
            {
                "gas": self.estimate_gas(),
                "gasPrice": self.instance.eth.gas_price,
                "nonce": self.instance.eth.get_transaction_count(self.account.address),
            }
        )

        signed_tx = self.instance.eth.account.sign_transaction(
            transaction, private_key=self.private_key
        )

        txn_hash = self.instance.eth.send_raw_transaction(signed_tx.raw_transaction)

        txn_receipt = self.instance.eth.wait_for_transaction_receipt(txn_hash)

        return txn_hash
