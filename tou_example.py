from smart_meter import SmartMeter, MeterMode
from database import get_db, TariffSchedule
from datetime import datetime, timedelta

def demonstrate_tou_tariffs():
    """Demonstrate Time-of-Use tariff functionality"""
    
    # Initialize meter
    meter_id = "TOU_TEST_METER"
    meter = SmartMeter(meter_id, MeterMode.PREPAID)
    db = next(get_db())
    
    print("\n=== Time-of-Use Tariff Demonstration ===")
    
    # Define TOU schedules
    weekday_schedules = [
        # Off-peak (00:00 - 06:00)
        {"start_time": 0, "end_time": 360, "rate": 0.10, "type": "weekday", "is_peak": False},
        # Peak (06:00 - 12:00)
        {"start_time": 360, "end_time": 720, "rate": 0.25, "type": "weekday", "is_peak": True},
        # Shoulder (12:00 - 18:00)
        {"start_time": 720, "end_time": 1080, "rate": 0.15, "type": "weekday", "is_peak": False},
        # Peak (18:00 - 22:00)
        {"start_time": 1080, "end_time": 1320, "rate": 0.25, "type": "weekday", "is_peak": True},
        # Off-peak (22:00 - 24:00)
        {"start_time": 1320, "end_time": 1440, "rate": 0.10, "type": "weekday", "is_peak": False}
    ]
    
    weekend_schedules = [
        # Single off-peak rate for weekends
        {"start_time": 0, "end_time": 1440, "rate": 0.12, "type": "weekend", "is_peak": False}
    ]
    
    # Set TOU schedules
    print("\n1. Setting TOU schedules...")
    all_schedules = weekday_schedules + weekend_schedules
    success = meter.set_tou_schedule(all_schedules)
    if success:
        print("Successfully set TOU schedules")
    
    # Display current schedules
    print("\n2. Current TOU Schedules:")
    schedules = db.query(TariffSchedule).filter_by(meter_id=meter_id).all()
    for schedule in schedules:
        start_time = f"{schedule.start_time // 60:02d}:{schedule.start_time % 60:02d}"
        end_time = f"{schedule.end_time // 60:02d}:{schedule.end_time % 60:02d}"
        print(f"\nSchedule Type: {schedule.schedule_type}")
        print(f"Time: {start_time} - {end_time}")
        print(f"Rate: ${schedule.rate:.3f}/kWh")
        print(f"Peak Period: {'Yes' if schedule.is_peak else 'No'}")
    
    # Show current rate
    print(f"\n3. Current Rate: ${meter.get_current_rate():.3f}/kWh")
    
    # Simulate consumption at different times
    print("\n4. Simulated Consumption at Different Times:")
    test_times = [
        (5, 0),   # 05:00 (off-peak)
        (8, 0),   # 08:00 (peak)
        (14, 0),  # 14:00 (shoulder)
        (20, 0),  # 20:00 (peak)
        (23, 0)   # 23:00 (off-peak)
    ]
    
    for hour, minute in test_times:
        # Simulate different times
        test_time = datetime.now().replace(hour=hour, minute=minute)
        print(f"\nTime: {test_time.strftime('%H:%M')}")
        
        # Get applicable rate
        applicable_rate = meter.get_current_rate()
        print(f"Applicable Rate: ${applicable_rate:.3f}/kWh")
        
        # Calculate cost for 1 kWh
        cost = applicable_rate * 1
        print(f"Cost for 1 kWh: ${cost:.2f}")

if __name__ == "__main__":
    demonstrate_tou_tariffs()
