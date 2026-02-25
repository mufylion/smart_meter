from smart_meter import SmartMeter, MeterMode, KCTType
from database import get_db, MeterUser

def demonstrate_kcts():
    # Create a meter
    meter = SmartMeter("METER002", MeterMode.PREPAID)
    db = next(get_db())
    
    # Get the API key
    user = db.query(MeterUser).filter_by(meter_id="METER002").first()
    api_key = user.api_key
    
    print("\n1. Mode Switch KCT")
    # Generate and process mode switch KCT
    mode_switch_kct = SmartMeter.generate_kct(
        meter.meter_id,
        KCTType.MODE_SWITCH,
        api_key,
        db,
        {"mode": "postpaid"}
    )
    meter.process_kct(mode_switch_kct)
    
    print("\n2. Change Tariff KCT")
    # Generate and process tariff change KCT
    tariff_kct = SmartMeter.generate_kct(
        meter.meter_id,
        KCTType.CHANGE_TARIFF,
        api_key,
        db,
        {"rate": 0.20}  # New rate per kWh
    )
    meter.process_kct(tariff_kct)
    
    print("\n3. Emergency Credit KCT")
    # Generate and process emergency credit KCT
    emergency_kct = SmartMeter.generate_kct(
        meter.meter_id,
        KCTType.EMERGENCY_CREDIT,
        api_key,
        db,
        {"amount": 15.0}
    )
    meter.process_kct(emergency_kct)
    
    print("\n4. Software Update KCT")
    # Generate and process software update KCT
    update_kct = SmartMeter.generate_kct(
        meter.meter_id,
        KCTType.SOFTWARE_UPDATE,
        api_key,
        db,
        {"version": "1.1.0"}
    )
    meter.process_kct(update_kct)
    
    print("\n5. Clear Memory KCT")
    # Generate and process clear memory KCT
    clear_kct = SmartMeter.generate_kct(
        meter.meter_id,
        KCTType.CLEAR_MEMORY,
        api_key,
        db,
        {}
    )
    meter.process_kct(clear_kct)
    
    print("\n6. Reset Password KCT")
    # Generate and process password reset KCT
    password_kct = SmartMeter.generate_kct(
        meter.meter_id,
        KCTType.RESET_PASSWORD,
        api_key,
        db,
        {}
    )
    meter.process_kct(password_kct)
    
    print("\n7. Reset Tamper KCT")
    # Generate and process tamper reset KCT
    tamper_kct = SmartMeter.generate_kct(
        meter.meter_id,
        KCTType.RESET_TAMPER,
        api_key,
        db,
        {}
    )
    meter.process_kct(tamper_kct)
    
    # Show final meter state
    print("\nFinal Meter State:")
    print(f"Mode: {meter.mode.value}")
    print(f"Software Version: {meter.software_version}")
    print(f"Tariff Rate: {meter.rate_per_kwh}")
    print(f"Emergency Credit Active: {meter.emergency_credit_active}")
    print(f"Balance: {meter.balance}")

if __name__ == "__main__":
    demonstrate_kcts()
