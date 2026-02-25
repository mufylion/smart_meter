from smart_meter import SmartMeter, MeterMode
from database import get_db, MeterUser

def demonstrate_kwh_credit():
    """Demonstrate how kWh-based credit system works"""
    
    # Initialize meter
    meter_id = "KWH_TEST_METER"
    meter = SmartMeter(meter_id, MeterMode.PREPAID)
    db = next(get_db())
    
    # Get API key
    user = db.query(MeterUser).filter_by(meter_id=meter_id).first()
    api_key = user.api_key
    
    print("\n=== KWh-Based Credit System Demonstration ===")
    
    # 1. Add initial credit at original rate ($0.15/kWh)
    print("\n1. Adding $100 credit at rate $0.15/kWh")
    meter.add_credit(100.0)
    
    # 2. Consume some power
    print("\n2. Consuming 200 kWh")
    meter.consume_power(200)
    
    # 3. Change tariff rate to $0.25/kWh
    print("\n3. Changing tariff rate to $0.25/kWh")
    meter.remote_tariff_change(0.25, api_key)
    
    # 4. Add more credit at new rate
    print("\n4. Adding another $100 credit at new rate $0.25/kWh")
    meter.add_credit(100.0)
    
    # 5. Consume more power at new rate
    print("\n5. Consuming 200 kWh at new rate")
    meter.consume_power(200)
    
    # 6. Show usage history
    print("\n6. Usage History:")
    for usage in meter.usage_history:
        print(f"\nTimestamp: {usage['timestamp']}")
        print(f"Consumption: {usage['consumption']} kWh")
        print(f"Rate: ${usage['rate']:.3f}/kWh")
        print(f"Cost: ${usage['cost']:.2f}")
        print(f"Remaining credit: {usage['remaining_kwh']:.2f} kWh")

if __name__ == "__main__":
    demonstrate_kwh_credit()
