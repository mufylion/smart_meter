from smart_meter import SmartMeter, MeterMode
from database import get_db, PowerQualityEvent, EventLog, LoadProfile
from datetime import datetime, timedelta
import time

def demonstrate_power_quality_monitoring():
    """Demonstrate power quality monitoring and load profile recording"""
    
    # Initialize meter
    meter_id = "PQ_TEST_METER"
    meter = SmartMeter(meter_id, MeterMode.PREPAID)
    db = next(get_db())
    
    print("\n=== Power Quality Monitoring Demonstration ===")
    
    # Record load profiles for a few intervals
    print("\n1. Recording load profiles...")
    for _ in range(5):
        meter.record_load_profile()
        time.sleep(1)  # Simulate time passing
    
    # Retrieve and display load profiles
    print("\n2. Recent Load Profiles:")
    profiles = db.query(LoadProfile).filter_by(meter_id=meter_id).order_by(LoadProfile.timestamp.desc()).limit(5).all()
    for profile in profiles:
        print(f"\nTimestamp: {profile.timestamp}")
        print(f"Voltage: {profile.voltage:.2f}V")
        print(f"Current: {profile.current:.2f}A")
        print(f"Power Factor: {profile.power_factor:.3f}")
        print(f"Active Power: {profile.active_power:.2f}W")
        print(f"Frequency: {profile.frequency:.2f}Hz")
    
    # Display power quality events
    print("\n3. Power Quality Events:")
    events = db.query(PowerQualityEvent).filter_by(meter_id=meter_id).order_by(PowerQualityEvent.timestamp.desc()).all()
    for event in events:
        print(f"\nEvent Type: {event.event_type.value}")
        print(f"Timestamp: {event.timestamp}")
        print(f"Magnitude: {event.magnitude:.2f}%")
        print(f"Measured: {event.measured_value:.2f}")
        print(f"Nominal: {event.nominal_value:.2f}")
    
    # Display general event log
    print("\n4. Event Log:")
    logs = db.query(EventLog).filter_by(meter_id=meter_id).order_by(EventLog.timestamp.desc()).all()
    for log in logs:
        print(f"\nEvent Type: {log.event_type.value}")
        print(f"Timestamp: {log.timestamp}")
        print(f"Description: {log.description}")
        print(f"Severity: {log.severity}")

if __name__ == "__main__":
    demonstrate_power_quality_monitoring()
