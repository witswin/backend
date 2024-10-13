from typing import Any, Dict
import os
from datetime import timedelta
from django.utils import timezone
from siwe import SiweMessage, generate_nonce, ISO8601Datetime
from eth_utils import to_checksum_address, is_checksum_address


class SignWithEthereum:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SignWithEthereum, cls).__new__(cls)
        return cls._instance

    def __init__(self):

        if not hasattr(self, "_initialized"):
            self.nonces: Dict[str, SiweMessage] = {}  # address : [nonce,message]
            self._initialized = True

            self.domain = os.getenv("DOMAIN")
            self.uri = os.getenv("URI")

    @staticmethod
    def address_is_checksum_address(address: str) -> bool:
        """
        Verifies if the Ethereum address is in the correct checksummed format.

        Args:
            address (str): Ethereum address to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        try:
            return to_checksum_address(address) == address and is_checksum_address(
                address
            )
        except ValueError:
            return False

    def create_message(self, address: str) -> str:
        """
        Creates a SIWE message for a given Ethereum address if it is valid.

        Args:
            address (str): Ethereum address to create the message for.

        Raises:
            ValueError: If the address is invalid.

        Returns:
            str: The prepared message for signing.
        """
        if not self.address_is_checksum_address(address):
            raise ValueError("Invalid Ethereum address")

        nonce = generate_nonce()
        issued_at = ISO8601Datetime.from_datetime(timezone.now())
        expiration_time = ISO8601Datetime.from_datetime(
            timezone.now() + timedelta(minutes=10)
        )

        print(
            {
                "domain": self.domain,
                "address": address,
                "uri": self.uri,
                "version": "1",
                "chain_id": 1,
                "issued_at": issued_at,
                "expiration_time": expiration_time,
                "nonce": nonce,
                "statement": "Sign in with this wallet address to authenticate.",
            }
        )

        message = SiweMessage(
            domain=self.domain,
            address=address,
            uri=self.uri,
            version="1",
            chain_id=1,
            issued_at=issued_at,
            expiration_time=expiration_time,
            nonce=nonce,
            statement="Sign in with this wallet address to authenticate.",
        )

        self.nonces[address] = (nonce, message)
        return message.prepare_message()

    def verify_message(self, address: str, nonce: str, signature: str) -> bool:
        """
        Verifies the SIWE message and nonce for a given Ethereum address.

        Args:
            address (str): Ethereum address to verify.
            nonce (str): The nonce sent by the client.
            signature (str): The signature provided by the client.

        Returns:
            bool: True if the message is verified and nonce matches, False otherwise.
        """
        if address not in self.nonces:
            return False

        stored_nonce, message = self.nonces.pop(address)

        try:
            message.verify(signature)
            return stored_nonce == nonce
        except Exception:
            return False
