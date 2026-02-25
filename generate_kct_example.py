from smart_meter import SmartMeter, MeterMode, KCTType
from database import get_db, MeterUser
from typing import Optional

class KCTGenerator:
    def __init__(self, meter_id: str):
        self.meter_id = meter_id
        self.db = next(get_db())
        self.meter = SmartMeter(meter_id)
        self.user = self.db.query(MeterUser).filter_by(meter_id=meter_id).first()
        if not self.user:
            raise ValueError(f"No meter found with ID: {meter_id}")
        self.api_key = self.user.api_key

    def generate_mode_switch_kct(self, new_mode: str) -> Optional[str]:
        """Generate KCT for switching meter mode"""
        if new_mode not in ["prepaid", "postpaid"]:
            print(f"Invalid mode: {new_mode}. Must be 'prepaid' or 'postpaid'")
            return None
        
        kct = SmartMeter.generate_kct(
            self.meter_id,
            KCTType.MODE_SWITCH,
            self.api_key,
            self.db,
            {"mode": new_mode}
        )
        print(f"Generated Mode Switch KCT (to {new_mode} mode)")
        return kct

    def generate_tariff_change_kct(self, new_rate: float) -> Optional[str]:
        """Generate KCT for changing tariff rate"""
        if new_rate <= 0:
            print(f"Invalid rate: {new_rate}. Must be positive")
            return None
        
        kct = SmartMeter.generate_kct(
            self.meter_id,
            KCTType.CHANGE_TARIFF,
            self.api_key,
            self.db,
            {"rate": new_rate}
        )
        print(f"Generated Tariff Change KCT (new rate: {new_rate})")
        return kct

    def generate_emergency_credit_kct(self, amount: float = 10.0) -> Optional[str]:
        """Generate KCT for emergency credit activation"""
        if amount <= 0:
            print(f"Invalid amount: {amount}. Must be positive")
            return None
        
        kct = SmartMeter.generate_kct(
            self.meter_id,
            KCTType.EMERGENCY_CREDIT,
            self.api_key,
            self.db,
            {"amount": amount}
        )
        print(f"Generated Emergency Credit KCT (amount: {amount})")
        return kct

    def generate_software_update_kct(self, new_version: str) -> Optional[str]:
        """Generate KCT for software update"""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', new_version):
            print(f"Invalid version format: {new_version}. Must be in format x.y.z")
            return None
        
        kct = SmartMeter.generate_kct(
            self.meter_id,
            KCTType.SOFTWARE_UPDATE,
            self.api_key,
            self.db,
            {"version": new_version}
        )
        print(f"Generated Software Update KCT (version: {new_version})")
        return kct

    def generate_clear_memory_kct(self) -> str:
        """Generate KCT for clearing meter memory"""
        kct = SmartMeter.generate_kct(
            self.meter_id,
            KCTType.CLEAR_MEMORY,
            self.api_key,
            self.db,
            {}
        )
        print("Generated Clear Memory KCT")
        return kct

    def generate_reset_password_kct(self) -> str:
        """Generate KCT for resetting meter password"""
        kct = SmartMeter.generate_kct(
            self.meter_id,
            KCTType.RESET_PASSWORD,
            self.api_key,
            self.db,
            {}
        )
        print("Generated Password Reset KCT")
        return kct

    def generate_reset_tamper_kct(self) -> str:
        """Generate KCT for resetting tamper count"""
        kct = SmartMeter.generate_kct(
            self.meter_id,
            KCTType.RESET_TAMPER,
            self.api_key,
            self.db,
            {}
        )
        print("Generated Tamper Reset KCT")
        return kct

def demonstrate_kct_generation():
    # Create a KCT generator for a meter
    meter_id = "DEMO_METER"
    print(f"\nInitializing meter {meter_id}...")
    generator = KCTGenerator(meter_id)
    
    print("\nGenerating various types of KCTs:")
    
    # 1. Generate Mode Switch KCT
    print("\n1. Mode Switch KCT:")
    mode_kct = generator.generate_mode_switch_kct("postpaid")
    print(f"KCT: {mode_kct}")
    
    # 2. Generate Tariff Change KCT
    print("\n2. Tariff Change KCT:")
    tariff_kct = generator.generate_tariff_change_kct(0.20)
    print(f"KCT: {tariff_kct}")
    
    # 3. Generate Emergency Credit KCT
    print("\n3. Emergency Credit KCT:")
    emergency_kct = generator.generate_emergency_credit_kct(15.0)
    print(f"KCT: {emergency_kct}")
    
    # 4. Generate Software Update KCT
    print("\n4. Software Update KCT:")
    update_kct = generator.generate_software_update_kct("2.0.0")
    print(f"KCT: {update_kct}")
    
    # 5. Generate Clear Memory KCT
    print("\n5. Clear Memory KCT:")
    clear_kct = generator.generate_clear_memory_kct()
    print(f"KCT: {clear_kct}")
    
    # 6. Generate Password Reset KCT
    print("\n6. Password Reset KCT:")
    password_kct = generator.generate_reset_password_kct()
    print(f"KCT: {password_kct}")
    
    # 7. Generate Tamper Reset KCT
    print("\n7. Tamper Reset KCT:")
    tamper_kct = generator.generate_reset_tamper_kct()
    print(f"KCT: {tamper_kct}")
    
    # Demonstrate error handling
    print("\nError Handling Examples:")
    
    print("\n8. Invalid Mode:")
    invalid_mode_kct = generator.generate_mode_switch_kct("invalid_mode")
    print(f"KCT: {invalid_mode_kct}")
    
    print("\n9. Invalid Tariff Rate:")
    invalid_rate_kct = generator.generate_tariff_change_kct(-1.0)
    print(f"KCT: {invalid_rate_kct}")
    
    print("\n10. Invalid Software Version:")
    invalid_version_kct = generator.generate_software_update_kct("invalid")
    print(f"KCT: {invalid_version_kct}")

if __name__ == "__main__":
    demonstrate_kct_generation()
