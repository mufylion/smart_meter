from smart_meter import SmartMeter, MeterMode
from database import get_db, MeterUser
from datetime import datetime

def demonstrate_tariff_impact():
    """Demonstrate how tariff changes affect existing credit"""
    
    # Initialize meter in prepaid mode
    meter_id = "TARIFF_TEST_METER"
    meter = SmartMeter(meter_id, MeterMode.PREPAID)
    db = next(get_db())
    
    # Get API key
    user = db.query(MeterUser).filter_by(meter_id=meter_id).first()
    api_key = user.api_key
    
    print("\n=== Tariff Change Impact Demonstration ===")
    
    # 1. Add initial credit at original rate
    initial_credit = 100.0  # $100
    print(f"\n1. Adding initial credit: ${initial_credit:.2f}")
    meter.add_credit(initial_credit)
    
    # Calculate initial purchasable power
    initial_kwh = initial_credit / meter.rate_per_kwh
    print(f"Initial purchasable power: {initial_kwh:.2f} kWh")
    
    # 2. Consume some power at original rate
    consumption = 200  # kWh
    print(f"\n2. Consuming {consumption} kWh at rate ${meter.rate_per_kwh:.3f}/kWh")
    meter.consume_power(consumption)
    print(f"Remaining balance: ${meter.balance:.2f}")
    
    # 3. Change tariff rate
    new_rate = 0.25  # $0.25 per kWh
    print(f"\n3. Changing tariff rate to ${new_rate:.3f}/kWh")
    meter.remote_tariff_change(new_rate, api_key)
    
    # 4. Consume same amount at new rate
    print(f"\n4. Consuming {consumption} kWh at new rate ${meter.rate_per_kwh:.3f}/kWh")
    meter.consume_power(consumption)
    print(f"Remaining balance: ${meter.balance:.2f}")
    
    # 5. Show usage history with rates
    print("\n5. Usage History:")
    for usage in meter.usage_history:
        print(f"Timestamp: {usage['timestamp']}")
        print(f"Consumption: {usage['consumption']} kWh")
        print(f"Rate: ${usage['rate']:.3f}/kWh")
        print(f"Cost: ${usage['cost']:.2f}")
        print()

if __name__ == "__main__":
    demonstrate_tariff_impact()
