from smart_meter import SmartMeter, MeterMode
from database import get_db, MeterUser, Transaction
from datetime import datetime

def demonstrate_remote_tariff():
    """Demonstrate remote tariff change functionality"""
    
    # Initialize meter
    meter_id = "REMOTE_METER"
    meter = SmartMeter(meter_id, MeterMode.PREPAID)
    db = next(get_db())
    
    # Get API key
    user = db.query(MeterUser).filter_by(meter_id=meter_id).first()
    api_key = user.api_key
    
    print("\n=== Remote Tariff Change Demonstration ===")
    
    # Show initial rate
    print(f"\nInitial tariff rate: ${meter.rate_per_kwh:.3f} per kWh")
    
    # 1. Valid tariff change
    print("\n1. Changing to $0.25 per kWh")
    success = meter.remote_tariff_change(0.25, api_key)
    if success:
        # Show sample bill calculation
        consumption = 100  # kWh
        bill = consumption * meter.rate_per_kwh
        print(f"\nSample bill calculation:")
        print(f"Consumption: {consumption} kWh")
        print(f"Bill amount: ${bill:.2f}")
    
    # 2. Another valid change
    print("\n2. Changing to $0.30 per kWh")
    success = meter.remote_tariff_change(0.30, api_key)
    if success:
        # Show sample bill calculation
        consumption = 100  # kWh
        bill = consumption * meter.rate_per_kwh
        print(f"\nSample bill calculation:")
        print(f"Consumption: {consumption} kWh")
        print(f"Bill amount: ${bill:.2f}")
    
    # 3. Invalid rate (negative)
    print("\n3. Attempting to set invalid negative rate")
    meter.remote_tariff_change(-0.1, api_key)
    
    # 4. Invalid rate (zero)
    print("\n4. Attempting to set invalid zero rate")
    meter.remote_tariff_change(0.0, api_key)
    
    # 5. Invalid API key
    print("\n5. Attempting change with invalid API key")
    meter.remote_tariff_change(0.35, "invalid_api_key")
    
    # Show transaction history
    print("\nTariff Change Transaction History:")
    transactions = db.query(Transaction)\
        .filter_by(meter_id=meter_id, transaction_type="tariff_change")\
        .order_by(Transaction.created_at.desc())\
        .all()
    
    for tx in transactions:
        print(f"Timestamp: {tx.created_at}, Status: {tx.status}")

if __name__ == "__main__":
    demonstrate_remote_tariff()
