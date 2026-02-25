import unittest
from smart_meter import SmartMeter, MeterMode, KCTType
from database import get_db, MeterUser, Token, Transaction
from datetime import datetime

class TestKCTFunctionality(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.meter = SmartMeter("TEST_METER_KCT", MeterMode.PREPAID)
        self.db = next(get_db())
        self.user = self.db.query(MeterUser).filter_by(meter_id="TEST_METER_KCT").first()
        self.api_key = self.user.api_key

    def test_1_mode_switch_kct(self):
        """Test mode switching KCT"""
        print("\nTesting Mode Switch KCT...")
        
        # Test switching to postpaid
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.MODE_SWITCH,
            self.api_key,
            self.db,
            {"mode": "postpaid"}
        )
        self.assertIsNotNone(kct)
        success = self.meter.process_kct(kct)
        self.assertTrue(success)
        self.assertEqual(self.meter.mode, MeterMode.POSTPAID)
        
        # Test switching back to prepaid
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.MODE_SWITCH,
            self.api_key,
            self.db,
            {"mode": "prepaid"}
        )
        success = self.meter.process_kct(kct)
        self.assertTrue(success)
        self.assertEqual(self.meter.mode, MeterMode.PREPAID)

    def test_2_tariff_change_kct(self):
        """Test tariff change KCT"""
        print("\nTesting Tariff Change KCT...")
        
        initial_rate = self.meter.rate_per_kwh
        new_rate = 0.25
        
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.CHANGE_TARIFF,
            self.api_key,
            self.db,
            {"rate": new_rate}
        )
        success = self.meter.process_kct(kct)
        self.assertTrue(success)
        self.assertEqual(self.meter.rate_per_kwh, new_rate)
        
        # Test invalid rate
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.CHANGE_TARIFF,
            self.api_key,
            self.db,
            {"rate": -1.0}  # Invalid negative rate
        )
        success = self.meter.process_kct(kct)
        self.assertFalse(success)

    def test_3_emergency_credit_kct(self):
        """Test emergency credit KCT"""
        print("\nTesting Emergency Credit KCT...")
        
        # Test in prepaid mode
        self.meter.mode = MeterMode.PREPAID
        initial_balance = self.meter.balance
        emergency_amount = 15.0
        
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.EMERGENCY_CREDIT,
            self.api_key,
            self.db,
            {"amount": emergency_amount}
        )
        success = self.meter.process_kct(kct)
        self.assertTrue(success)
        self.assertTrue(self.meter.emergency_credit_active)
        self.assertEqual(self.meter.balance, initial_balance + emergency_amount)
        
        # Test in postpaid mode (should fail)
        self.meter.mode = MeterMode.POSTPAID
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.EMERGENCY_CREDIT,
            self.api_key,
            self.db,
            {"amount": emergency_amount}
        )
        success = self.meter.process_kct(kct)
        self.assertFalse(success)

    def test_4_software_update_kct(self):
        """Test software update KCT"""
        print("\nTesting Software Update KCT...")
        
        initial_version = self.meter.software_version
        new_version = "2.0.0"
        
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.SOFTWARE_UPDATE,
            self.api_key,
            self.db,
            {"version": new_version}
        )
        success = self.meter.process_kct(kct)
        self.assertTrue(success)
        self.assertEqual(self.meter.software_version, new_version)
        
        # Test invalid version format
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.SOFTWARE_UPDATE,
            self.api_key,
            self.db,
            {"version": "invalid"}
        )
        success = self.meter.process_kct(kct)
        self.assertFalse(success)

    def test_5_clear_memory_kct(self):
        """Test clear memory KCT"""
        print("\nTesting Clear Memory KCT...")
        
        # Add some test data
        self.meter.usage_history.append({"timestamp": datetime.now(), "consumption": 10.0})
        self.meter.payment_history.append({"timestamp": datetime.now(), "amount": 50.0})
        
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.CLEAR_MEMORY,
            self.api_key,
            self.db,
            {}
        )
        success = self.meter.process_kct(kct)
        self.assertTrue(success)
        self.assertEqual(len(self.meter.usage_history), 0)
        self.assertEqual(len(self.meter.payment_history), 0)

    def test_6_reset_password_kct(self):
        """Test password reset KCT"""
        print("\nTesting Password Reset KCT...")
        
        initial_password_hash = self.user.password_hash
        
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.RESET_PASSWORD,
            self.api_key,
            self.db,
            {}
        )
        success = self.meter.process_kct(kct)
        self.assertTrue(success)
        
        # Refresh user from database
        self.db.refresh(self.user)
        self.assertNotEqual(self.user.password_hash, initial_password_hash)

    def test_7_reset_tamper_kct(self):
        """Test tamper reset KCT"""
        print("\nTesting Tamper Reset KCT...")
        
        # Simulate tamper detection
        self.meter.tamper_count = 3
        
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.RESET_TAMPER,
            self.api_key,
            self.db,
            {}
        )
        success = self.meter.process_kct(kct)
        self.assertTrue(success)
        self.assertEqual(self.meter.tamper_count, 0)

    def test_8_token_reuse(self):
        """Test token reuse prevention"""
        print("\nTesting Token Reuse Prevention...")
        
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.MODE_SWITCH,
            self.api_key,
            self.db,
            {"mode": "postpaid"}
        )
        
        # First use should succeed
        success1 = self.meter.process_kct(kct)
        self.assertTrue(success1)
        
        # Second use should fail
        success2 = self.meter.process_kct(kct)
        self.assertFalse(success2)

    def test_9_invalid_api_key(self):
        """Test KCT generation with invalid API key"""
        print("\nTesting Invalid API Key...")
        
        invalid_api_key = "invalid_key"
        kct = SmartMeter.generate_kct(
            self.meter.meter_id,
            KCTType.MODE_SWITCH,
            invalid_api_key,
            self.db,
            {"mode": "postpaid"}
        )
        self.assertIsNone(kct)

    def test_10_wrong_meter_id(self):
        """Test KCT with wrong meter ID"""
        print("\nTesting Wrong Meter ID...")
        
        kct = SmartMeter.generate_kct(
            "WRONG_METER_ID",
            KCTType.MODE_SWITCH,
            self.api_key,
            self.db,
            {"mode": "postpaid"}
        )
        self.assertIsNone(kct)

if __name__ == '__main__':
    # Remove the database file before running tests
    import os
    if os.path.exists("smart_meter.db"):
        os.remove("smart_meter.db")
    
    # Run the tests
    unittest.main(verbosity=2)
