from smart_meter import SmartMeter, MeterMode, KCTType
from database import get_db, MeterUser

def change_meter_tariff(meter_id: str, new_rate: float):
    """
    Change the tariff rate for a specific meter
    
    Args:
        meter_id: The ID of the meter
        new_rate: New tariff rate per kWh (must be positive)
    """
    # Initialize the meter and database
    meter = SmartMeter(meter_id)
    db = next(get_db())
    
    # Get the meter's API key
    user = db.query(MeterUser).filter_by(meter_id=meter_id).first()
    if not user:
        print(f"Error: Meter {meter_id} not found")
        return
    
    # Print current tariff
    print(f"\nCurrent tariff rate: {meter.rate_per_kwh} per kWh")
    
    # Validate new rate
    if new_rate <= 0:
        print(f"Error: Invalid rate {new_rate}. Rate must be positive")
        return
    
    # Generate tariff change KCT
    print(f"\nGenerating KCT for new rate: {new_rate} per kWh")
    kct = SmartMeter.generate_kct(
        meter_id,
        KCTType.CHANGE_TARIFF,
        user.api_key,
        db,
        {"rate": new_rate}
    )
    
    if not kct:
        print("Error: Failed to generate KCT")
        return
    
    # Apply the KCT to change tariff
    print("\nApplying tariff change...")
    success = meter.process_kct(kct)
    
    if success:
        print(f"\nTariff change successful!")
        print(f"New tariff rate: {meter.rate_per_kwh} per kWh")
        
        # Calculate sample bill to demonstrate new rate
        sample_consumption = 100  # kWh
        sample_bill = sample_consumption * meter.rate_per_kwh
        print(f"\nSample bill calculation:")
        print(f"Consumption: {sample_consumption} kWh")
        print(f"Bill amount: ${sample_bill:.2f}")
    else:
        print("Error: Failed to change tariff")

def demonstrate_tariff_changes():
    """Demonstrate various tariff change scenarios"""
    meter_id = "DEMO_METER_TARIFF"
    
    print("=== Tariff Change Demonstration ===")
    
    # 1. Normal tariff change
    print("\n1. Normal tariff change")
    change_meter_tariff(meter_id, 0.25)  # Change to $0.25 per kWh
    
    # 2. Another valid change
    print("\n2. Another tariff change")
    change_meter_tariff(meter_id, 0.30)  # Change to $0.30 per kWh
    
    # 3. Invalid rate (negative)
    print("\n3. Attempting invalid negative rate")
    change_meter_tariff(meter_id, -0.1)
    
    # 4. Invalid rate (zero)
    print("\n4. Attempting invalid zero rate")
    change_meter_tariff(meter_id, 0.0)

if __name__ == "__main__":
    demonstrate_tariff_changes()
