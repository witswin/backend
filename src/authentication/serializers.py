import json
from rest_framework import serializers
from eth_utils import to_checksum_address, is_checksum_address

from authentication.models import UserProfile
from core.crypto import Crypto



class UserProfileSerializer(serializers.ModelSerializer):
  class Meta:
    model = UserProfile
    fields = ['pk', 'wallet_address', 'username']
    read_only_fields = ['wallet_address']



class AuthenticateSerializer(serializers.Serializer):
  address = serializers.CharField( max_length=256)
  signature = serializers.CharField()
  message = serializers.CharField()

  def is_valid(self, *, raise_exception=False):
    is_data_valid = super().is_valid(raise_exception=raise_exception)

    if is_data_valid is False:
      return is_data_valid
    
    crypto = Crypto()

    assert type(self.validated_data) == dict, "validated data must not be empty"


    is_verified = crypto.verify_signature(self.validated_data.get("address"), self.validated_data.get("message"), self.validated_data.get("signature"))

    if is_verified is False:
      return is_verified
    
    message = json.loads(self.validated_data['message'])

    
    return message["message"]["message"] == "Wits Sign In" and message["message"]["URI"] == "https://wits.win"

class EIP55AddressField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        self.validate_eip55_address(value)
        return value
    @classmethod
    def validate_eip55_address(cls,address):
      try:
          checksum_address = to_checksum_address(address)
          if checksum_address != address:
              raise ValueError("Address is not EIP-55 compliant")
          if not is_checksum_address(address):
              raise ValueError("Invalid EIP-55 address")
      except ValueError as e:
          raise ValueError(f"Invalid Ethereum address: {str(e)}")
        
      
class AddressSerializer(serializers.Serializer):
    address = EIP55AddressField(max_length=42)

class VerifyWalletSerializer(serializers.Serializer):
    nonce = serializers.CharField(max_length=255)
    signature = serializers.CharField(max_length=255)
    address = EIP55AddressField(max_length=42)