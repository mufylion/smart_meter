import unittest
from smart_meter import SmartMeter, MeterMode, TokenStatus
from database import get_db, MeterUser, Token, Transaction
from security import SecurityUtils

class TestSmartMeter(unittest.TestCase):
    def setUp(self):
        """Set up test cases"""
        self.meter_id = "TEST_METER_001"
        self.prepaid_meter = SmartMeter(self.meter_id, MeterMode.PREPAID)
        self.db = next(get_db())
        
        # Store the API key for testing
        self.user = self.db.query(MeterUser).filter_by(meter_id=self.meter_id).first()
        self.api_key = self.user.api_key

    def test_meter_initialization(self):
        """Test meter initialization"""
        self.assertEqual(self.prepaid_meter.meter_id, self.meter_id)
        self.assertEqual(self.prepaid_meter.mode, MeterMode.PREPAID)
        self.assertEqual(self.prepaid_meter.balance, 0.0)
        self.assertTrue(self.prepaid_meter.is_active)

    def test_consumption_tracking(self):
        """Test power consumption tracking"""
        # Add initial credit
        self.prepaid_meter.add_credit(100.0)
        initial_balance = self.prepaid_meter.balance
        
        # Consume power
        kwh_consumed = 10.0
        self.prepaid_meter.consume_power(kwh_consumed)
        
        # Check consumption and balance
        expected_cost = kwh_consumed * self.prepaid_meter.rate_per_kwh
        self.assertEqual(self.prepaid_meter.consumption, kwh_consumed)
        self.assertEqual(self.prepaid_meter.balance, initial_balance - expected_cost)

    def test_token_generation_and_loading(self):
        """Test token generation and credit loading"""
        # Generate token
        amount = 50.0
        token = SmartMeter.generate_token(amount, self.meter_id, self.api_key, self.db)
        self.assertIsNotNone(token)
        
        # Load token
        initial_balance = self.prepaid_meter.balance
        success = self.prepaid_meter.load_token_credit(token)
        
        # Verify token loading
        self.assertTrue(success)
        self.assertEqual(self.prepaid_meter.balance, initial_balance + amount)
        
        # Try to use same token again
        success = self.prepaid_meter.load_token_credit(token)
        self.assertFalse(success)  # Should fail as token is already used

    def test_remote_credit_loading(self):
        """Test remote credit loading"""
        amount = 30.0
        initial_balance = self.prepaid_meter.balance
        
        # Load credit with valid API key
        success = self.prepaid_meter.remote_credit_load(amount, self.api_key)
        self.assertTrue(success)
        self.assertEqual(self.prepaid_meter.balance, initial_balance + amount)
        
        # Try with invalid API key
        success = self.prepaid_meter.remote_credit_load(amount, "invalid_api_key")
        self.assertFalse(success)

    def test_mode_switching(self):
        """Test switching between prepaid and postpaid modes"""
        # Switch to postpaid
        self.prepaid_meter.switch_mode(MeterMode.POSTPAID)
        self.assertEqual(self.prepaid_meter.mode, MeterMode.POSTPAID)
        
        # Try to load token in postpaid mode
        token = SmartMeter.generate_token(20.0, self.meter_id, self.api_key, self.db)
        success = self.prepaid_meter.load_token_credit(token)
        self.assertFalse(success)  # Should fail in postpaid mode

    def test_insufficient_credit(self):
        """Test behavior when credit is insufficient"""
        self.prepaid_meter.balance = 1.0  # Set very low balance
        
        # Try to consume more power than credit allows
        success = self.prepaid_meter.consume_power(100.0)  # This should cost more than available balance
        self.assertFalse(success)
        self.assertFalse(self.prepaid_meter.is_active)

    def test_transaction_logging(self):
        """Test transaction logging"""
        # Add credit and check transaction record
        amount = 25.0
        self.prepaid_meter.remote_credit_load(amount, self.api_key)
        
        # Verify transaction in database
        transaction = self.db.query(Transaction)\
            .filter_by(meter_id=self.meter_id, amount=amount)\
            .order_by(Transaction.id.desc())\
            .first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.status, "completed")

    def test_security_features(self):
        """Test security utilities"""
        # Test password hashing
        password = "test_password"
        hashed = SecurityUtils.hash_password(password)
        self.assertTrue(SecurityUtils.verify_password(password, hashed))
        self.assertFalse(SecurityUtils.verify_password("wrong_password", hashed))
        
        # Test API key generation
        api_key = SecurityUtils.generate_api_key()
        self.assertIsNotNone(api_key)
        
        # Test token encryption/decryption
        data = "test_data"
        encrypted, hash_value = SecurityUtils.encrypt_data(data)
        decrypted = SecurityUtils.decrypt_data(encrypted)
        self.assertEqual(data, decrypted)

if __name__ == '__main__':
    unittest.main()
