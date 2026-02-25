from datetime import datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import random
import string
from sqlalchemy.orm import Session
from database import (
    get_db, STSToken, MeterUser, Transaction, LoadProfile, PowerQualityEvent, EventLog, TariffSchedule,
    DemandResponseEvent, CommunicationLog, FirmwareUpdate, SecurityAuditLog, STSTokenClass, STSTokenSubclass, TokenStatus, MeterMode
)
from sts_utils import STSTokenGenerator, STSTokenValidator
from cryptography.fernet import Fernet
import json
import re
import math
import hmac
import os

class MeterMode(Enum):
    PREPAID = "prepaid"
    POSTPAID = "postpaid"

class TokenStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    USED = "used"
    KEY_REVISION_MISMATCH = "key_revision_mismatch"
    KEY_EXPIRED = "key_expired"

class KCTType(Enum):
    MODE_SWITCH = "mode_switch"
    CLEAR_MEMORY = "clear_memory"
    SOFTWARE_UPDATE = "software_update"
    RESET_TAMPER = "reset_tamper"
    CHANGE_TARIFF = "change_tariff"
    RESET_PASSWORD = "reset_password"
    EMERGENCY_CREDIT = "emergency_credit"

class DemandResponseEventType(Enum):
    LOAD_REDUCTION = "load_reduction"
    EMERGENCY_DR = "emergency_dr"
    PRICE_RESPONSE = "price_response"

class CommunicationProtocol(Enum):
    ANSI_C12_19 = "ansi_c12_19"

class SmartMeter:
    def __init__(self, meter_id: str, mode: MeterMode = MeterMode.POSTPAID):
        """Initialize smart meter with STS6 compliance"""
        self.meter_id = meter_id
        self.mode = mode
        self.balance = 0.0
        self.consumption = 0.0
        self.rate_per_kwh = 0.15
        self.is_active = True
        
        # Power quality monitoring parameters
        self.nominal_voltage = 230.0  # V
        self.nominal_frequency = 50.0  # Hz
        self.voltage_tolerance = 0.1   # ±10%
        self.frequency_tolerance = 0.01 # ±1%
        self.power_factor_threshold = 0.85
        
        # Load profile parameters
        self.measurement_interval = 15  # minutes
        self.last_measurement_time = None
        
        # Demand Response parameters
        self.max_power_limit = 10.0  # kW
        self.current_power_limit = self.max_power_limit
        self.participating_in_dr = False
        
        self._db = next(get_db())
        
        # Initialize or get meter user with STS parameters
        self._init_meter_user()
        
        # Initialize STS token validator
        self._token_validator = STSTokenValidator(
            self._get_decoder_key(),
            self.user.supply_group_code
        )

    def _init_meter_user(self):
        """Initialize meter user with STS parameters"""
        user = self._db.query(MeterUser).filter_by(meter_id=self.meter_id).first()
        
        if not user:
            # Generate initial credentials
            initial_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            password_hash = hashlib.sha256(initial_password.encode()).hexdigest()
            
            # Generate STS keys
            vending_key = os.urandom(24)  # 192-bit key for Triple DES
            decoder_key = os.urandom(24)
            
            # Create new user with STS parameters
            user = MeterUser(
                meter_id=self.meter_id,
                password_hash=password_hash,
                decoder_key=self._encrypt_key(decoder_key),
                vending_key=self._encrypt_key(vending_key),
                supply_group_code="0001",  # Example supply group code
                key_revision_number=1,
                key_expiry_number=255,  # No expiry
                is_active=True
            )
            
            self._db.add(user)
            self._db.commit()
            
            print(f"Initial meter credentials generated:")
            print(f"Meter ID: {self.meter_id}")
            print(f"Initial Password: {initial_password}")
            
        self.user = user

    def _encrypt_key(self, key: bytes) -> str:
        """Encrypt a key for storage"""
        fernet = Fernet(Fernet.generate_key())
        return fernet.encrypt(key).decode()

    def _decrypt_key(self, encrypted_key: str) -> bytes:
        """Decrypt a stored key"""
        fernet = Fernet(Fernet.generate_key())
        return fernet.decrypt(encrypted_key.encode())

    def _get_decoder_key(self) -> bytes:
        """Get the current decoder key"""
        return self._decrypt_key(self.user.decoder_key)

    @staticmethod
    def generate_token(amount: float, meter_id: str, supply_group_code: str,
                      vending_key: bytes) -> Optional[str]:
        """Generate an STS6 compliant token"""
        try:
            generator = STSTokenGenerator(vending_key, supply_group_code)
            
            token_number, tid = generator.generate_token(
                token_class=STSTokenClass.CREDIT.value,
                token_subclass=STSTokenSubclass.CREDIT_TRANSFER.value,
                amount=amount,
                meter_id=meter_id
            )
            
            return token_number
            
        except Exception as e:
            print(f"Token generation failed: {str(e)}")
            return None

    def validate_token(self, token_number: str) -> Dict:
        """Validate an STS6 token"""
        if self.mode != MeterMode.PREPAID:
            return {"status": TokenStatus.INVALID, "error": "Token only valid in prepaid mode"}
        
        # Check if token already used
        existing_token = self._db.query(STSToken).filter_by(
            token_number=token_number
        ).first()
        
        if existing_token and existing_token.is_used:
            return {"status": TokenStatus.USED, "error": "Token already used"}
        
        # Validate token
        validation_result = self._token_validator.validate_token(
            token_number,
            expected_class=STSTokenClass.CREDIT.value
        )
        
        if not validation_result["valid"]:
            return {"status": TokenStatus.INVALID, "error": validation_result["error"]}
        
        token_data = validation_result["data"]
        
        # Verify key revision
        if token_data["key_revision"] != self.user.key_revision_number:
            return {"status": TokenStatus.KEY_REVISION_MISMATCH, "error": "Key revision mismatch"}
        
        # Check key expiry
        if token_data["key_expiry"] < self.user.key_expiry_number:
            return {"status": TokenStatus.KEY_EXPIRED, "error": "Key expired"}
        
        return {
            "status": TokenStatus.VALID,
            "amount": token_data["amount"],
            "tid": token_data["tid"]
        }

    def load_token_credit(self, token_number: str) -> bool:
        """Load credit using an STS6 token"""
        validation_result = self.validate_token(token_number)
        
        if validation_result["status"] != TokenStatus.VALID:
            print(f"Token validation failed: {validation_result.get('error', 'Unknown error')}")
            return False
        
        try:
            # Create token record
            token = STSToken(
                token_number=token_number,
                token_identifier=validation_result["tid"],
                token_class=STSTokenClass.CREDIT.value,
                token_subclass=STSTokenSubclass.CREDIT_TRANSFER.value,
                amount=validation_result["amount"],
                key_revision_number=self.user.key_revision_number,
                key_expiry_number=self.user.key_expiry_number,
                meter_id=self.meter_id
            )
            
            self._db.add(token)
            
            # Create transaction record
            transaction = Transaction(
                meter_id=self.meter_id,
                amount=validation_result["amount"],
                type="token_credit",
                status="completed"
            )
            
            self._db.add(transaction)
            
            # Update balance
            self.balance += validation_result["amount"]
            
            # Mark token as used
            token.is_used = True
            token.used_at = datetime.utcnow()
            
            self._db.commit()
            return True
            
        except Exception as e:
            self._db.rollback()
            print(f"Credit loading failed: {str(e)}")
            return False

    def remote_credit_load(self, amount: float, api_key: str) -> bool:
        """Load credit remotely using API key authentication"""
        if self.mode != MeterMode.PREPAID:
            print("Remote credit loading is only available in prepaid mode")
            return False

        # Verify API key
        user = self._db.query(MeterUser).filter_by(meter_id=self.meter_id, api_key=api_key).first()
        if not user or not user.is_active:
            print("Invalid API key or inactive meter")
            return False

        # Generate transaction ID and create record
        transaction_id = self._security.generate_transaction_id()
        transaction = Transaction(
            transaction_id=transaction_id,
            meter_id=self.meter_id,
            amount=amount,
            type="remote",
            status="pending"
        )
        self._db.add(transaction)

        # Add credit
        self.add_credit(amount)
        
        # Update transaction status
        transaction.status = "completed"
        self._db.commit()

        print(f"Successfully loaded {amount:.2f} credits remotely")
        return True

    def change_password(self, old_password: str, new_password: str) -> bool:
        """Change meter user password"""
        user = self._db.query(MeterUser).filter_by(meter_id=self.meter_id).first()
        if not user:
            return False
        
        if not self._security.verify_password(old_password, user.password_hash):
            return False
        
        user.password_hash = self._security.hash_password(new_password)
        self._db.commit()
        return True

    def regenerate_api_key(self, password: str) -> Optional[str]:
        """Regenerate API key with password authentication"""
        user = self._db.query(MeterUser).filter_by(meter_id=self.meter_id).first()
        if not user or not self._security.verify_password(password, user.password_hash):
            return None
        
        new_api_key = self._security.generate_api_key()
        user.api_key = new_api_key
        self._db.commit()
        return new_api_key

    def switch_mode(self, new_mode: MeterMode) -> None:
        """Switch between prepaid and postpaid modes"""
        if self.mode != new_mode:
            self.mode = new_mode
            print(f"Meter {self.meter_id} switched to {new_mode.value} mode")

    def add_credit(self, amount: float) -> None:
        """Add credit for prepaid mode"""
        self.balance += amount
        self.payment_history.append({
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "type": "credit"
        })
        print(f"Added ${amount:.2f} credit. New balance: ${self.balance:.2f}")
        print(f"Available power at current rate: {(self.balance / self.rate_per_kwh):.2f} kWh")

    def get_balance(self) -> float:
        """Get current balance in dollars"""
        return self.balance

    def consume_power(self, kwh: float) -> bool:
        """
        Consume power from available credit
        
        Args:
            kwh: Amount of power to consume in kWh
            
        Returns:
            bool: True if consumption was successful, False if insufficient credit
        """
        if self.mode == MeterMode.PREPAID:
            if not self.is_active or self.balance < kwh * self.rate_per_kwh:
                print("Insufficient credit or meter inactive. Please recharge.")
                print(f"Available credit: ${self.balance:.2f}")
                print(f"Requested consumption: {kwh:.2f} kWh (${kwh * self.rate_per_kwh:.2f})")
                self.is_active = False
                return False
                
            self.balance -= kwh * self.rate_per_kwh
            
        cost = kwh * self.rate_per_kwh
        self.consumption += kwh
        
        # Record usage
        self.usage_history.append({
            "timestamp": datetime.utcnow(),
            "consumption": kwh,
            "rate": self.rate_per_kwh,
            "cost": cost,
            "remaining_balance": self.balance
        })
        
        if self.mode == MeterMode.PREPAID:
            print(f"Consumed: {kwh:.2f} kWh (${cost:.2f})")
            print(f"Remaining credit: ${self.balance:.2f}")
        
        return True

    def get_bill(self) -> float:
        """Calculate bill for postpaid mode"""
        if self.mode == MeterMode.POSTPAID:
            return self.consumption * self.rate_per_kwh
        return 0.0

    def get_consumption_stats(self) -> Dict:
        """Get consumption statistics"""
        return {
            "total_consumption": self.consumption,
            "current_balance": self.get_balance(),
            "mode": self.mode.value,
            "is_active": self.is_active,
            "meter_id": self.meter_id
        }

    def reset_consumption(self) -> None:
        """Reset consumption counter (typically done monthly for billing)"""
        self.consumption = 0.0

    @staticmethod
    def generate_kct(
        meter_id: str, 
        kct_type: KCTType, 
        api_key: str, 
        db: Session, 
        params: Dict = None
    ) -> Optional[str]:
        """Generate a Key Change Token (KCT) for administrative functions"""
        # Verify API key
        user = db.query(MeterUser).filter_by(meter_id=meter_id, api_key=api_key).first()
        if not user or not user.is_active:
            return None

        # Generate token data
        token_data = {
            "meter_id": meter_id,
            "type": kct_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "params": params or {}
        }

        # Generate transaction ID and create token
        transaction_id = SecurityUtils.generate_transaction_id()
        token_string = json.dumps(token_data)
        encrypted_token, token_hash = SecurityUtils.encrypt_data(token_string)
        
        # Store token in database
        token = Token(
            token_hash=token_hash,
            amount=0.0,  # KCTs don't carry monetary value
            meter_id=meter_id,
            transaction_id=transaction_id,
            token_type=kct_type.value,
            params=json.dumps(params) if params else None
        )
        db.add(token)
        db.commit()
        
        return encrypted_token

    def process_kct(self, encrypted_token: str) -> bool:
        """Process a Key Change Token"""
        # Decrypt and validate token
        token_string = self._security.decrypt_data(encrypted_token)
        if not token_string:
            print("Invalid KCT")
            return False

        try:
            # Parse token data
            token_data = json.loads(token_string)
            token_hash = hashlib.sha256(token_string.encode()).hexdigest()
            
            # Verify token in database
            token = self._db.query(Token).filter_by(token_hash=token_hash).first()
            if not token or token.is_used or token.meter_id != self.meter_id:
                print("Invalid or used KCT")
                return False

            # Process based on token type
            kct_type = KCTType(token_data["type"])
            params = token_data.get("params", {})
            
            success = self._execute_kct_operation(kct_type, params)
            if success:
                # Mark token as used
                token.is_used = True
                token.used_at = datetime.utcnow()
                self._db.commit()
                return True
                
            return False

        except Exception as e:
            print(f"Error processing KCT: {str(e)}")
            return False

    def _execute_kct_operation(self, kct_type: KCTType, params: Dict) -> bool:
        """Execute the operation specified by the KCT"""
        try:
            if kct_type == KCTType.MODE_SWITCH:
                new_mode = MeterMode(params.get("mode"))
                return self._switch_mode_with_kct(new_mode)
                
            elif kct_type == KCTType.CLEAR_MEMORY:
                return self._clear_memory_with_kct()
                
            elif kct_type == KCTType.SOFTWARE_UPDATE:
                new_version = params.get("version")
                return self._update_software_with_kct(new_version)
                
            elif kct_type == KCTType.RESET_TAMPER:
                return self._reset_tamper_with_kct()
                
            elif kct_type == KCTType.CHANGE_TARIFF:
                new_rate = float(params.get("rate"))
                return self._change_tariff_with_kct(new_rate)
                
            elif kct_type == KCTType.RESET_PASSWORD:
                return self._reset_password_with_kct()
                
            elif kct_type == KCTType.EMERGENCY_CREDIT:
                amount = float(params.get("amount", self.emergency_credit_limit))
                return self._activate_emergency_credit_with_kct(amount)
                
            else:
                print(f"Unsupported KCT type: {kct_type}")
                return False
                
        except Exception as e:
            print(f"Error executing KCT operation: {str(e)}")
            return False

    def _switch_mode_with_kct(self, new_mode: MeterMode) -> bool:
        """Switch meter mode using KCT"""
        if self.mode != new_mode:
            self.mode = new_mode
            print(f"Meter {self.meter_id} switched to {new_mode.value} mode")
            return True
        return False

    def _clear_memory_with_kct(self) -> bool:
        """Clear meter memory using KCT"""
        self.usage_history = []
        self.payment_history = []
        print(f"Memory cleared for meter {self.meter_id}")
        return True

    def _update_software_with_kct(self, new_version: str) -> bool:
        """Update meter software version using KCT"""
        import re
        # Validate version format (x.y.z)
        if not re.match(r'^\d+\.\d+\.\d+$', new_version):
            print(f"Invalid version format: {new_version}. Must be in format x.y.z")
            return False
        if new_version != self.software_version:
            self.software_version = new_version
            print(f"Software updated to version {new_version}")
            return True
        return False

    def _reset_tamper_with_kct(self) -> bool:
        """Reset tamper count using KCT"""
        if self.tamper_count > 0:
            self.tamper_count = 0
            print("Tamper count reset to 0")
            return True
        return False

    def _change_tariff_with_kct(self, new_rate: float) -> bool:
        """Change tariff rate using KCT"""
        if new_rate <= 0:
            print(f"Invalid tariff rate: {new_rate}. Rate must be positive.")
            return False
        if new_rate != self.rate_per_kwh:
            self.rate_per_kwh = new_rate
            print(f"Tariff rate updated to {new_rate}")
            return True
        return False

    def _reset_password_with_kct(self) -> bool:
        """Reset meter password using KCT"""
        user = self._db.query(MeterUser).filter_by(meter_id=self.meter_id).first()
        if user:
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            user.password_hash = self._security.hash_password(new_password)
            self._db.commit()
            print(f"Password reset. New password: {new_password}")
            return True
        return False

    def _activate_emergency_credit_with_kct(self, amount: float) -> bool:
        """Activate emergency credit using KCT"""
        if not self.emergency_credit_active and self.mode == MeterMode.PREPAID:
            self.emergency_credit_active = True
            self.balance += amount
            print(f"Emergency credit of ${amount:.2f} activated")
            return True
        return False

    def remote_tariff_change(self, new_rate: float, api_key: str) -> bool:
        """
        Change the tariff rate remotely using API key authentication
        
        Args:
            new_rate: New tariff rate per kWh (must be positive)
            api_key: API key for authentication
            
        Returns:
            bool: True if tariff change was successful, False otherwise
        """
        # Verify API key
        user = self._db.query(MeterUser).filter_by(meter_id=self.meter_id, api_key=api_key).first()
        if not user or not user.is_active:
            print("Invalid API key or inactive meter")
            return False
            
        # Validate new rate
        if new_rate <= 0:
            print(f"Invalid tariff rate: {new_rate}. Rate must be positive")
            return False
            
        # Create transaction record
        transaction = Transaction(
            meter_id=self.meter_id,
            amount=0.0,
            transaction_type="tariff_change",
            status="pending"
        )
        self._db.add(transaction)
        
        try:
            old_rate = self.rate_per_kwh
            old_balance_dollars = self.get_balance()
            
            # Update tariff rate (credit_kwh remains unchanged)
            self.rate_per_kwh = new_rate
            new_balance_dollars = self.get_balance()
            
            print(f"\nTariff Rate Change Impact:")
            print(f"Old rate: ${old_rate:.3f} per kWh")
            print(f"New rate: ${new_rate:.3f} per kWh")
            print(f"Available power units: {(self.balance / self.rate_per_kwh):.2f} kWh")
            print(f"Old balance: ${old_balance_dollars:.2f}")
            print(f"New balance: ${new_balance_dollars:.2f}")
            
            # Calculate purchasing power comparison
            example_amount = 100.0  # $100 example
            old_kwh = example_amount / old_rate
            new_kwh = example_amount / new_rate
            
            print(f"\nPurchasing Power Comparison (for ${example_amount:.2f}):")
            print(f"At old rate: {old_kwh:.2f} kWh")
            print(f"At new rate: {new_kwh:.2f} kWh")
            
            # Update transaction status
            transaction.status = "completed"
            self._db.commit()
            
            return True
            
        except Exception as e:
            print(f"Error changing tariff: {str(e)}")
            transaction.status = "failed"
            self._db.commit()
            return False

    def handle_demand_response_event(self, event_type: DemandResponseEventType, target_reduction: float,
                                   duration_minutes: int, priority: int = 1) -> bool:
        """Handle a demand response event by reducing load."""
        try:
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Create demand response event
            dr_event = DemandResponseEvent(
                meter_id=self.meter_id,
                event_type=event_type.value,  # Use the string value
                start_time=start_time,
                end_time=end_time,
                target_reduction=target_reduction,
                status='scheduled',
                priority=priority
            )
            
            self._db.add(dr_event)
            self._db.commit()
            
            # Log the event
            self._log_event(
                EventType.DEMAND_RESPONSE.value,  # Use the string value
                f"Demand response event scheduled: {event_type.value}, target reduction: {target_reduction}kW",
                "info"
            )
            
            return True
            
        except Exception as e:
            self._log_event(
                EventType.DEMAND_RESPONSE.value,  # Use the string value
                f"Failed to handle demand response event: {str(e)}",
                "error"
            )
            return False

    def end_demand_response_event(self, event_id=None) -> bool:
        """End a demand response event."""
        try:
            # Get the active DR event
            if event_id is None:
                event = self._db.query(DemandResponseEvent)\
                    .filter_by(meter_id=self.meter_id, status='scheduled')\
                    .order_by(DemandResponseEvent.start_time.desc())\
                    .first()
                if event:
                    event_id = event.id
            
            if event_id is None:
                self._log_event(
                    EventType.DEMAND_RESPONSE.value,
                    "No active demand response event found",
                    "warning"
                )
                return False
            
            event = self._db.query(DemandResponseEvent).get(event_id)
            if event and event.meter_id == self.meter_id:
                event.end_time = datetime.now()
                event.status = "completed"
                self._db.commit()
                
                self._log_event(
                    EventType.DEMAND_RESPONSE.value,
                    f"Demand response event {event_id} ended",
                    "info"
                )
                return True
            return False
            
        except Exception as e:
            self._log_event(
                EventType.DEMAND_RESPONSE.value,
                f"Failed to end DR event: {str(e)}",
                "error"
            )
            return False

    def send_ansi_message(self, message_type: str, message_data: dict) -> bool:
        """Send a message using ANSI C12.19 protocol."""
        try:
            # Create communication log entry
            comm_log = CommunicationLog(
                meter_id=self.meter_id,
                protocol=CommunicationProtocol.ANSI_C12_19.value,  # Use the string value
                timestamp=datetime.now(),
                message_type=message_type,
                message_data=message_data,
                status='pending'
            )
            
            self._db.add(comm_log)
            self._db.commit()
            
            # Encrypt sensitive data
            if message_data.get('sensitive', False):
                message_data['payload'] = self._encrypt_data(str(message_data['payload']))
            
            # Log the communication event
            self._log_event(
                EventType.COMMUNICATION.value,  # Use the string value
                f"ANSI C12.19 message sent: {message_type}",
                "info"
            )
            
            return True
            
        except Exception as e:
            self._log_event(
                EventType.COMMUNICATION.value,  # Use the string value
                f"Failed to send ANSI message: {str(e)}",
                "error"
            )
            return False

    def update_firmware(self, version: str, firmware_data: bytes, signature: str) -> bool:
        """Handle firmware update"""
        try:
            # Verify firmware signature
            if not self._verify_firmware(firmware_data, signature):
                raise ValueError("Invalid firmware signature")
            
            # Calculate checksum
            checksum = hashlib.sha256(firmware_data).hexdigest()
            
            # Create firmware update record
            update = FirmwareUpdate(
                meter_id=self.meter_id,
                version=version,
                update_time=datetime.utcnow(),
                status="pending",
                signature=signature,
                checksum=checksum
            )
            self._db.add(update)
            
            # Simulate update process
            success = self._simulate_firmware_update()
            
            if success:
                update.status = "completed"
                self.software_version = version
                self._log_event(
                    EventType.CONFIGURATION.value,  # Use the string value
                    f"Firmware updated to version {version}",
                    "info"
                )
            else:
                update.status = "failed"
                self._log_event(
                    EventType.CONFIGURATION.value,  # Use the string value
                    "Firmware update failed",
                    "error"
                )
            
            self._db.commit()
            return success
            
        except Exception as e:
            self._log_event(
                EventType.CONFIGURATION.value,  # Use the string value
                f"Firmware update error: {str(e)}",
                "error"
            )
            return False

    def _verify_firmware(self, firmware_data: bytes, signature: str) -> bool:
        """Verify firmware signature (simplified for demonstration)"""
        # In real implementation, this would use proper cryptographic verification
        return len(signature) == 64  # Simulate SHA-256 signature check

    def _simulate_firmware_update(self) -> bool:
        """Simulate firmware update with 95% success rate"""
        return random.random() < 0.95

    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()

    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def log_security_event(self, event_type: str, action: str, 
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          details: Optional[Dict] = None) -> None:
        """Log security-related events"""
        try:
            audit_log = SecurityAuditLog(
                meter_id=self.meter_id,
                timestamp=datetime.utcnow(),
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address,
                action=action,
                status="recorded",
                details=details
            )
            self._db.add(audit_log)
            self._db.commit()
            
        except Exception as e:
            self._log_event(
                EventType.SECURITY.value,  # Use the string value
                f"Failed to log security event: {str(e)}",
                "error"
            )

    def record_load_profile(self) -> None:
        """Record load profile measurements"""
        now = datetime.utcnow()
        
        # Simulate measurements (in a real meter, these would come from sensors)
        voltage = self.nominal_voltage * (1 + random.uniform(-0.05, 0.05))
        current = random.uniform(0.5, 10.0)
        power_factor = random.uniform(0.85, 1.0)
        active_power = voltage * current * power_factor
        reactive_power = active_power * math.tan(math.acos(power_factor))
        frequency = self.nominal_frequency * (1 + random.uniform(-0.005, 0.005))
        
        # Create load profile record
        profile = LoadProfile(
            meter_id=self.meter_id,
            timestamp=now,
            voltage=voltage,
            current=current,
            power_factor=power_factor,
            active_power=active_power,
            reactive_power=reactive_power,
            frequency=frequency,
            interval_minutes=self.measurement_interval
        )
        
        self._db.add(profile)
        self._db.commit()
        
        # Check for power quality issues
        self._check_power_quality(voltage, frequency, power_factor)

    def _check_power_quality(self, voltage: float, frequency: float, power_factor: float) -> None:
        """Monitor power quality parameters and log events"""
        now = datetime.utcnow()
        
        # Check voltage sag/swell
        voltage_deviation = abs(voltage - self.nominal_voltage) / self.nominal_voltage
        if voltage_deviation > self.voltage_tolerance:
            event_type = PowerQualityEventType.VOLTAGE_SWELL if voltage > self.nominal_voltage else PowerQualityEventType.VOLTAGE_SAG
            self._log_power_quality_event(event_type, voltage, self.nominal_voltage)
        
        # Check frequency deviation
        freq_deviation = abs(frequency - self.nominal_frequency) / self.nominal_frequency
        if freq_deviation > self.frequency_tolerance:
            self._log_power_quality_event(
                PowerQualityEventType.FREQUENCY_DEVIATION,
                frequency,
                self.nominal_frequency
            )
        
        # Check power factor
        if power_factor < self.power_factor_threshold:
            self._log_event(
                EventType.POWER_QUALITY.value,  # Use the string value
                f"Low power factor detected: {power_factor:.2f}",
                "warning"
            )

    def _log_power_quality_event(self, event_type: PowerQualityEventType, measured: float, nominal: float) -> None:
        """Log a power quality event"""
        event = PowerQualityEvent(
            meter_id=self.meter_id,
            event_type=event_type.value,  # Use the string value
            timestamp=datetime.utcnow(),
            magnitude=abs(measured - nominal) / nominal * 100,  # as percentage
            nominal_value=nominal,
            measured_value=measured
        )
        self._db.add(event)
        self._db.commit()
        
        # Also log to general event log
        self._log_event(
            EventType.POWER_QUALITY.value,  # Use the string value
            f"{event_type.value}: Measured={measured:.2f}, Nominal={nominal:.2f}",
            "warning"
        )

    def _log_event(self, event_type: str, description: str, severity: str, additional_data: str = None) -> None:
        """Log a general event"""
        event = EventLog(
            meter_id=self.meter_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            description=description,
            severity=severity,
            additional_data=additional_data
        )
        self._db.add(event)
        self._db.commit()

    def set_tou_schedule(self, schedules: List[Dict]) -> bool:
        """Set Time-of-Use tariff schedule"""
        try:
            # Clear existing schedules
            self._db.query(TariffSchedule).filter_by(meter_id=self.meter_id).delete()
            
            # Add new schedules
            for schedule in schedules:
                tariff_schedule = TariffSchedule(
                    meter_id=self.meter_id,
                    start_time=schedule['start_time'],
                    end_time=schedule['end_time'],
                    rate=schedule['rate'],
                    schedule_type=schedule['type'],
                    is_peak=schedule.get('is_peak', False)
                )
                self._db.add(tariff_schedule)
            
            self._db.commit()
            self._log_event(
                EventType.CONFIGURATION.value,  # Use the string value
                "Updated TOU schedule",
                "info",
                json.dumps(schedules)
            )
            return True
        except Exception as e:
            self._log_event(
                EventType.CONFIGURATION.value,  # Use the string value
                f"Failed to update TOU schedule: {str(e)}",
                "error"
            )
            return False

    def get_current_rate(self) -> float:
        """Get the current applicable rate based on TOU schedule"""
        now = datetime.now()
        current_time = now.hour * 60 + now.minute  # Convert to minutes from midnight
        
        # Determine day type
        day_type = 'weekend' if now.weekday() >= 5 else 'weekday'
        
        # Query for applicable tariff
        schedule = self._db.query(TariffSchedule).filter(
            TariffSchedule.meter_id == self.meter_id,
            TariffSchedule.schedule_type == day_type,
            TariffSchedule.start_time <= current_time,
            TariffSchedule.end_time > current_time,
            TariffSchedule.is_active == True
        ).first()
        
        return schedule.rate if schedule else self.rate_per_kwh

# Example usage
if __name__ == "__main__":
    # Create a prepaid meter
    prepaid_meter = SmartMeter("PM001", MeterMode.PREPAID)
    
    # Store the API key that was generated during initialization
    api_key = prepaid_meter._db.query(MeterUser).filter_by(meter_id="PM001").first().api_key
    
    # Add initial credit
    prepaid_meter.add_credit(50.0)
    prepaid_meter.consume_power(10)  # Consume 10 kWh
    print(prepaid_meter.get_consumption_stats())

    # Create a postpaid meter
    postpaid_meter = SmartMeter("PM002", MeterMode.POSTPAID)
    postpaid_meter.consume_power(15)  # Consume 15 kWh
    print(f"Postpaid bill: {postpaid_meter.get_bill():.2f}")
    print(postpaid_meter.get_consumption_stats())

    # Generate a token for credit loading (typically done by utility company)
    db = next(get_db())
    token = SmartMeter.generate_token(20.0, "PM001", "0001", os.urandom(24))
    print(f"\nGenerated token: {token}")

    # Load credit using the token
    if token:
        prepaid_meter.load_token_credit(token)

    # Load credit remotely using the API key
    prepaid_meter.remote_credit_load(30.0, api_key)

    # Generate a KCT for mode switch
    kct = SmartMeter.generate_kct("PM001", KCTType.MODE_SWITCH, api_key, db, {"mode": "postpaid"})
    print(f"\nGenerated KCT: {kct}")

    # Process the KCT
    if kct:
        prepaid_meter.process_kct(kct)

    # Record load profile
    prepaid_meter.record_load_profile()

    # Set TOU schedule
    schedules = [
        {"start_time": 0, "end_time": 360, "rate": 0.10, "type": "weekday", "is_peak": False},
        {"start_time": 360, "end_time": 720, "rate": 0.20, "type": "weekday", "is_peak": True},
        {"start_time": 720, "end_time": 1440, "rate": 0.10, "type": "weekday", "is_peak": False},
        {"start_time": 0, "end_time": 1440, "rate": 0.15, "type": "weekend", "is_peak": False}
    ]
    prepaid_meter.set_tou_schedule(schedules)

    # Get current rate
    print(f"Current rate: {prepaid_meter.get_current_rate():.2f}")

    # Handle demand response event
    prepaid_meter.handle_demand_response_event(DemandResponseEventType.LOAD_REDUCTION, 2.0, 60)

    # Send ANSI message
    prepaid_meter.send_ansi_message("read_meter", {"meter_id": "PM001"})

    # Update firmware
    firmware_data = b"firmware_data"
    signature = "signature"
    prepaid_meter.update_firmware("2.0.0", firmware_data, signature)

    # Log security event
    prepaid_meter.log_security_event("login", "successful", "user123", "192.168.1.100")
