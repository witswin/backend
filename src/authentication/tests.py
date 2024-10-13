import os
import uuid
from django.test import RequestFactory, TestCase

# Create your tests here.
from django.test import TestCase
from unittest.mock import patch
from siwe import SiweMessage
from web3 import Web3
from eth_account.messages import encode_defunct
from dotenv import load_dotenv
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from authentication.models import UserProfile
from authentication.views import VerifyWalletView

from .SignWithEthereum import SignWithEthereum
from django.contrib.auth.models import User


class SignWitEthereumTests(TestCase):
    
    @classmethod
    def to_eip55(cls,address):
        return Web3.to_checksum_address(address)
    
    @classmethod
    def sign_message(self,message:str,private_key:str)->str:
        hash_message = encode_defunct(text=message)
        return Web3().eth.account.sign_message(hash_message , private_key=private_key).signature
    def test_create_message(self):
        
        addresses  = [
            '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
            '0x85A363699C6864248a6FfCA66e4a1A5cCf9f5567',
            '0x1a642f0E3c3aF545E7AcBD38b07251B3990914F1',
            '0x7cB57B5A97eAbe94205C07890BE4c1aD31E486A8',
            '0x2c8645BFe28BEEb6E19843eE9573e7173C56A12c',
            '0x9e84D9DB70fb5EcE08B3258beb57b2f6557756f7',
            '0x4675C7e5BaAFBFFbca748158bEcBA61ef3b0a263',
            '0xD8f24D8A1A8f8515fA3E536C0d6Dd1Ca73aD3E89',
            '0x76e68a8696537e4141F79E10cA3B20B376546f84',
            '0x3E5e9111Ae8eB78Fe1CC3bb8915d5D461F3Ef9A9'
            ]

        # Ensure the address is in EIP-55 format

        # Set environment variables for testing
        with patch.dict('os.environ', {'DOMAIN': 'example.com', 'URI': 'https://example.com'}):
            for address in addresses:
                address = self.to_eip55(address)
                signer = SignWithEthereum()
                message = signer.create_message(address)
                nonce,s_message = signer.nonces.get(address, (None, None))
                
                
                self.assertIsNotNone(nonce)
                self.assertEqual(s_message.prepare_message(),message)
                
        self.assertGreaterEqual(len(SignWithEthereum().nonces),len(addresses)) 
        
    def test_verify_message(self):
        load_dotenv()
        address = os.getenv("TEST_WALLET_ADDRESS")
        private_key = os.getenv("TEST_WALLET_PRIVATE_KEY")
        message = SignWithEthereum().create_message(address)
        nonce,_= SignWithEthereum().nonces.get(address)

        signature = self.sign_message(message, private_key)
        self.assertTrue(SignWithEthereum().verify_message(address, nonce, signature))


class CreateMessageViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('create-message')

    def test_create_message_success(self):
        load_dotenv()
        address = os.getenv("TEST_WALLET_ADDRESS")
        data = {'address': SignWitEthereumTests.to_eip55(address)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_message_invalid_address(self):
        data = {'address': 'invalid_address'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        
class VerifyWalletViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = VerifyWalletView.as_view()
        self.url = '/verify-wallet/'  # Adjust this to match your actual URL
        self.valid_data = {
            'address': '0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed',
            'nonce': 'test_nonce',
            'signature': 'test_signature'
        }

    @patch('authentication.views.SignWithEthereum')
    @patch('authentication.views.Web3.to_checksum_address')
    def test_successful_verification_existing_user(self, mock_to_checksum, mock_sign):
        # Setup
        mock_sign.return_value.verify_message.return_value = True
        mock_to_checksum.return_value = self.valid_data['address']
        
        user = User.objects.create_user(username='testuser')
        UserProfile.objects.create(user=user, wallet_address=self.valid_data['address'])

        # Execute
        request = self.factory.post(self.url, self.valid_data)
        response = self.view(request)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertTrue('userToken' in response.cookies)
        self.assertTrue(User.objects.filter(username='testuser').exists())

        
        
    @patch('authentication.views.SignWithEthereum')
    @patch('authentication.views.Web3.to_checksum_address')
    @patch('authentication.views.uuid.uuid4')
    def test_successful_verification_new_user(self, mock_uuid, mock_to_checksum, mock_sign):
        # Setup
        mock_sign.return_value.verify_message.return_value = True
        mock_to_checksum.return_value = self.valid_data['address']
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')

        # Execute
        request = self.factory.post(self.url, self.valid_data)
        response = self.view(request)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertTrue('userToken' in response.cookies)

    def test_invalid_data(self):
        # Setup
        invalid_data = {
            'address': 'invalid_address',
            'nonce': 'test_nonce',
            'signature': 'test_signature'
        }

        # Execute
        request = self.factory.post(self.url, invalid_data)
        response = self.view(request)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"message": "invalid data"})

    @patch('authentication.views.SignWithEthereum')
    def test_invalid_signature(self, mock_sign):
        # Setup
        mock_sign.return_value.verify_message.return_value = False

        # Execute
        request = self.factory.post(self.url, self.valid_data)
        response = self.view(request)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"message": "Invalid signature"})

    @patch('authentication.views.SignWithEthereum')
    @patch('authentication.views.Web3.to_checksum_address')
    @patch('authentication.views.UserProfileSerializer')
    def test_response_data(self, mock_serializer, mock_to_checksum, mock_sign):
        # Setup
        mock_sign.return_value.verify_message.return_value = True
        mock_to_checksum.return_value = self.valid_data['address']
        mock_serializer.return_value.data = {'username': 'testuser', 'wallet_address': self.valid_data['address']}

        user = User.objects.create_user(username='testuser')
        UserProfile.objects.create(user=user, wallet_address=self.valid_data['address'])

        # Execute
        request = self.factory.post(self.url, self.valid_data)
        response = self.view(request)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['wallet_address'], self.valid_data['address'])

    @patch('authentication.views.SignWithEthereum')
    @patch('authentication.views.Web3.to_checksum_address')
    def test_cookie_settings(self, mock_to_checksum, mock_sign):
        # Setup
        mock_sign.return_value.verify_message.return_value = True
        mock_to_checksum.return_value = self.valid_data['address']

        user = User.objects.create_user(username='testuser')
        UserProfile.objects.create(user=user, wallet_address=self.valid_data['address'])

        # Execute
        request = self.factory.post(self.url, self.valid_data)
        response = self.view(request)

        # Assert
        self.assertTrue('userToken' in response.cookies)
        self.assertTrue(response.cookies['userToken']['httponly'])
        self.assertTrue(response.cookies['userToken']['secure'])
        self.assertEqual(response.cookies['userToken']['domain'], '.wits.win')
        self.assertEqual(response.cookies['userToken']['samesite'], 'None')