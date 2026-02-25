from smart_meter import SmartMeter, MeterMode

def demonstrate_mode_switching():
    # Create a meter (default is postpaid mode)
    meter = SmartMeter("METER001", MeterMode.POSTPAID)
    print(f"\nInitial mode: {meter.mode.value}")
    
    # Consume some power in postpaid mode
    meter.consume_power(10)  # Consume 10 kWh
    print(f"Bill in postpaid mode: {meter.get_bill():.2f}")
    
    # Switch to prepaid mode
    print("\nSwitching to prepaid mode...")
    meter.switch_mode(MeterMode.PREPAID)
    print(f"Current mode: {meter.mode.value}")
    
    # Add credit since we're in prepaid mode
    meter.add_credit(50.0)
    print(f"Added credit: 50.0")
    print(f"Current balance: {meter.balance:.2f}")
    
    # Consume power in prepaid mode
    meter.consume_power(10)  # Consume 10 kWh
    print(f"Balance after consumption: {meter.balance:.2f}")
    
    # Switch back to postpaid
    print("\nSwitching back to postpaid mode...")
    meter.switch_mode(MeterMode.POSTPAID)
    print(f"Current mode: {meter.mode.value}")
    
    # Show final stats
    print("\nFinal meter stats:")
    print(meter.get_consumption_stats())

if __name__ == "__main__":
    demonstrate_mode_switching()
