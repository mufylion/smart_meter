from datetime import datetime, timedelta
from smart_meter import SmartMeter, MeterMode
from database import DemandResponseEventType, DemandResponseEvent

def demonstrate_demand_response():
    """Demonstrate demand response functionality"""
    
    # Create a test meter
    meter = SmartMeter("DR_TEST_METER", MeterMode.PREPAID)
    print("\nInitial meter credentials generated:")
    print(f"Meter ID: {meter.meter_id}")
    
    print("\n=== Demand Response Demonstration ===\n")
    
    # 1. Start a load reduction event
    print("1. Starting Load Reduction Event")
    print(f"Initial power limit: {meter.max_power_limit:.2f} kW")
    
    success = meter.handle_demand_response_event(
        event_type=DemandResponseEventType.LOAD_REDUCTION,
        target_reduction=2.0,  # Reduce by 2kW
        duration_minutes=30,
        priority=1
    )
    
    print(f"New power limit: {meter.max_power_limit:.2f} kW\n")
    
    if success:
        print("Event Details:")
        # Get the most recent DR event
        event = meter._db.query(DemandResponseEvent).filter_by(
            meter_id=meter.meter_id
        ).order_by(DemandResponseEvent.start_time.desc()).first()
        
        if event:
            print(f"\nType: {event.event_type}")
            print(f"Start Time: {event.start_time}")
            print(f"End Time: {event.end_time}")
            print(f"Target Reduction: {event.target_reduction:.2f} kW")
            print(f"Status: {event.status}")
            print(f"Priority: {event.priority}")
    else:
        print("Failed to start demand response event")
    
    # 2. End the event early
    print("\n2. Ending Event Early")
    success = meter.end_demand_response_event()
    
    if success:
        print("Event ended successfully")
        event = meter._db.query(DemandResponseEvent).filter_by(
            meter_id=meter.meter_id
        ).order_by(DemandResponseEvent.start_time.desc()).first()
        
        if event:
            print(f"Final Status: {event.status}")
    else:
        print("Failed to end event")
    
    # 3. Start an emergency DR event
    print("\n3. Starting Emergency DR Event")
    success = meter.handle_demand_response_event(
        event_type=DemandResponseEventType.EMERGENCY_DR,
        target_reduction=5.0,  # Reduce by 5kW
        duration_minutes=60,
        priority=0  # Highest priority
    )
    
    if success:
        print("Emergency DR event started successfully")
        event = meter._db.query(DemandResponseEvent).filter_by(
            meter_id=meter.meter_id
        ).order_by(DemandResponseEvent.start_time.desc()).first()
        
        if event:
            print(f"Type: {event.event_type}")
            print(f"Target Reduction: {event.target_reduction:.2f} kW")
            print(f"Priority: {event.priority}")
    else:
        print("Failed to start emergency DR event")

if __name__ == "__main__":
    demonstrate_demand_response()
