from typing import Any, Dict
from dotenv import load_dotenv
import os
from datetime import timedelta
from django.utils import timezone
from siwe import SiweMessage,generate_nonce,ISO8601Datetime
from eth_utils import to_checksum_address, is_checksum_address

class SignWithEthereum:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SignWithEthereum, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        
        if not hasattr(self, '_initialized'):
            load_dotenv()
            self.nonces: Dict[str, SiweMessage] = {}  # address : [nonce,message] 
            self._initialized = True

            self.domain = os.getenv("DOMAIN")
            self.uri = os.getenv("URI")
            

    @classmethod
    def address_is_checksum_address(cls,address):
      try:
          checksum_address = to_checksum_address(address)
          if checksum_address != address:
              return False
          if not is_checksum_address(address):
             return False
      except ValueError as e:
          return False
      return True
        
    
    
    def create_message(self,address:str) :
        if  not self.address_is_checksum_address(address):
            raise ValueError("invalid address ")
        nonce = generate_nonce()
        issued_at = ISO8601Datetime.from_datetime(timezone.now())
        expiration_time = ISO8601Datetime.from_datetime(timezone.now() + timedelta(minutes=10))
        message = SiweMessage(domain=self.domain, address=address,uri=self.uri,version="1", chain_id=1, issued_at=issued_at,expiration_time=expiration_time, nonce=nonce, statement="you are going to sing in with this wallet address in this app")
        self.nonces[address] = [nonce,message]
        return message.prepare_message()
    
    def verify_message(self,address:str,nonce:str,signature:str):
        if self.nonces.get(address) is None:
            return False
        nonceAddress,message = self.nonces[address]
        del self.nonces[address]
        try:
            message.verify(signature)
            return nonceAddress == nonce
        except:
            return False
    
