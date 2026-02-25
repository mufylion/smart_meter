from typing import Dict, Optional, Tuple
import hmac
import hashlib
import struct
import time
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

class STSTokenGenerator:
    def __init__(self, vending_key: bytes, supply_group_code: str):
        self.vending_key = vending_key
        self.supply_group_code = supply_group_code
        self.backend = default_backend()
    
    def generate_token(self, 
                      token_class: str,
                      token_subclass: str,
                      amount: float = 0.0,
                      meter_id: str = None,
                      key_revision: int = 1,
                      key_expiry: int = 255) -> Tuple[str, int]:
        """
        Generate a 66-bit STS compliant token
        Returns token number and TID (Token Identifier)
        """
        # Generate Token Identifier (TID)
        tid = self._generate_tid()
        
        # Create token base
        token_base = self._create_token_base(
            token_class,
            token_subclass,
            amount,
            tid,
            key_revision,
            key_expiry
        )
        
        # Encrypt token using DEA
        encrypted_token = self._encrypt_token(token_base)
        
        # Format as 20-digit decimal number
        token_number = self._format_token(encrypted_token)
        
        return token_number, tid

    def _generate_tid(self) -> int:
        """Generate Token Identifier based on current time"""
        base_time = datetime(2014, 1, 1).timestamp()
        current_time = datetime.now().timestamp()
        minutes_passed = int((current_time - base_time) / 60)
        return minutes_passed % 0xFFFFFF  # 24-bit number

    def _create_token_base(self,
                          token_class: str,
                          token_subclass: str,
                          amount: float,
                          tid: int,
                          key_revision: int,
                          key_expiry: int) -> bytes:
        """Create 64-bit token base"""
        # Convert amount to Transfer Amount Register (TAR)
        tar = self._calculate_tar(amount)
        
        # Pack token data
        token_data = struct.pack('>BBHIB',
            int(token_class),
            int(token_subclass),
            tar,
            tid,
            (key_revision << 4) | (key_expiry & 0x0F)
        )
        
        # Add CRC
        crc = self._calculate_crc(token_data)
        return token_data + struct.pack('>H', crc)

    def _calculate_tar(self, amount: float) -> int:
        """Convert monetary amount to Transfer Amount Register value"""
        # Implementation based on STS specification
        # Typically uses a scaling factor and currency conversion
        scaled_amount = int(amount * 100)  # Example: convert to cents
        return scaled_amount & 0xFFFF  # 16-bit number

    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC-16 for token data"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1
        return crc

    def _encrypt_token(self, token_base: bytes) -> bytes:
        """Encrypt token using DEA (Data Encryption Algorithm)"""
        cipher = Cipher(
            algorithms.TripleDES(self.vending_key),
            modes.ECB(),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        
        # Add padding if needed
        padder = padding.PKCS7(64).padder()
        padded_data = padder.update(token_base) + padder.finalize()
        
        return encryptor.update(padded_data) + encryptor.finalize()

    def _format_token(self, encrypted_token: bytes) -> str:
        """Format encrypted token as 20-digit decimal number"""
        # Convert to large integer
        token_int = int.from_bytes(encrypted_token, byteorder='big')
        
        # Format as 20-digit number
        return f"{token_int % 10**20:020d}"

class STSTokenValidator:
    def __init__(self, decoder_key: bytes, supply_group_code: str):
        self.decoder_key = decoder_key
        self.supply_group_code = supply_group_code
        self.backend = default_backend()
    
    def validate_token(self, 
                      token_number: str,
                      expected_class: str = None,
                      meter_id: str = None) -> Dict:
        """
        Validate an STS token
        Returns dictionary with validation results
        """
        try:
            # Convert token to bytes
            token_bytes = self._decode_token_number(token_number)
            
            # Decrypt token
            decrypted_token = self._decrypt_token(token_bytes)
            
            # Parse token data
            token_data = self._parse_token_data(decrypted_token)
            
            # Verify CRC
            if not self._verify_crc(decrypted_token):
                return {"valid": False, "error": "Invalid CRC"}
            
            # Check token class if specified
            if expected_class and token_data["class"] != expected_class:
                return {"valid": False, "error": "Invalid token class"}
            
            # Check token expiry
            if self._is_token_expired(token_data["tid"]):
                return {"valid": False, "error": "Token expired"}
            
            return {
                "valid": True,
                "data": token_data
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _decode_token_number(self, token_number: str) -> bytes:
        """Convert 20-digit token number to bytes"""
        token_int = int(token_number)
        return token_int.to_bytes(8, byteorder='big')

    def _decrypt_token(self, token_bytes: bytes) -> bytes:
        """Decrypt token using DEA"""
        cipher = Cipher(
            algorithms.TripleDES(self.decoder_key),
            modes.ECB(),
            backend=self.backend
        )
        decryptor = cipher.decryptor()
        
        # Remove padding after decryption
        unpadder = padding.PKCS7(64).unpadder()
        padded_data = decryptor.update(token_bytes) + decryptor.finalize()
        return unpadder.update(padded_data) + unpadder.finalize()

    def _parse_token_data(self, decrypted_token: bytes) -> Dict:
        """Parse decrypted token data"""
        token_class = decrypted_token[0]
        token_subclass = decrypted_token[1]
        tar = struct.unpack('>H', decrypted_token[2:4])[0]
        tid = struct.unpack('>I', decrypted_token[4:8])[0]
        key_data = decrypted_token[8]
        key_revision = key_data >> 4
        key_expiry = key_data & 0x0F
        
        return {
            "class": str(token_class),
            "subclass": str(token_subclass),
            "amount": self._calculate_amount(tar),
            "tid": tid,
            "key_revision": key_revision,
            "key_expiry": key_expiry
        }

    def _calculate_amount(self, tar: int) -> float:
        """Convert TAR value to monetary amount"""
        # Implementation based on STS specification
        return float(tar) / 100  # Example: convert from cents

    def _verify_crc(self, token_data: bytes) -> bool:
        """Verify token CRC"""
        data = token_data[:-2]
        expected_crc = struct.unpack('>H', token_data[-2:])[0]
        calculated_crc = self._calculate_crc(data)
        return calculated_crc == expected_crc

    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC-16 for token data"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1
        return crc

    def _is_token_expired(self, tid: int) -> bool:
        """Check if token has expired based on TID"""
        base_time = datetime(2014, 1, 1).timestamp()
        token_time = base_time + (tid * 60)  # Convert minutes to seconds
        current_time = datetime.now().timestamp()
        
        # Tokens typically valid for 24 hours
        return (current_time - token_time) > (24 * 60 * 60)
