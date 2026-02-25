from smart_meter import SmartMeter, MeterMode, CommunicationProtocol
from database import get_db, SecurityAuditLog, CommunicationLog, FirmwareUpdate
from datetime import datetime, timedelta

def demonstrate_security_features():
    """Demonstrate security and communication features"""
    
    # Initialize meter
    meter_id = "SECURITY_TEST_METER"
    meter = SmartMeter(meter_id, MeterMode.PREPAID)
    db = next(get_db())
    
    print("\n=== Security and Communication Features Demonstration ===")
    
    # 1. Send ANSI C12.19 messages
    print("\n1. Testing ANSI C12.19 Communication")
    
    # Send meter reading request
    message_data = {
        "command": "read_register",
        "register": "current_demand",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    success = meter.send_ansi_message("meter_read", message_data)
    print(f"Meter read message sent: {'Success' if success else 'Failed'}")
    
    # Check communication logs
    comm_logs = db.query(CommunicationLog)\
        .filter_by(meter_id=meter_id)\
        .order_by(CommunicationLog.timestamp.desc())\
        .limit(1)\
        .all()
    
    print("\nCommunication Logs:")
    for log in comm_logs:
        print(f"Protocol: {log.protocol.value}")
        print(f"Message Type: {log.message_type}")
        print(f"Status: {log.status}")
        print(f"Retry Count: {log.retry_count}")
    
    # 2. Firmware Update
    print("\n2. Testing Firmware Update")
    
    # Simulate firmware update
    firmware_data = b"new_firmware_v2.0.0"
    signature = "a" * 64  # Simulated SHA-256 signature
    
    success = meter.update_firmware("2.0.0", firmware_data, signature)
    print(f"Firmware update: {'Success' if success else 'Failed'}")
    
    # Check firmware update logs
    updates = db.query(FirmwareUpdate)\
        .filter_by(meter_id=meter_id)\
        .order_by(FirmwareUpdate.update_time.desc())\
        .limit(1)\
        .all()
    
    print("\nFirmware Update Logs:")
    for update in updates:
        print(f"Version: {update.version}")
        print(f"Status: {update.status}")
        print(f"Update Time: {update.update_time}")
        print(f"Checksum: {update.checksum}")
    
    # 3. Security Audit Logging
    print("\n3. Testing Security Audit Logging")
    
    # Log various security events
    events = [
        ("login", "successful", "user123", "192.168.1.100"),
        ("configuration_change", "modified_settings", "admin", "192.168.1.200"),
        ("firmware_update", "verification", None, None),
        ("tamper_detect", "case_open", None, None)
    ]
    
    for event_type, action, user_id, ip in events:
        meter.log_security_event(event_type, action, user_id, ip)
    
    # Check security audit logs
    audit_logs = db.query(SecurityAuditLog)\
        .filter_by(meter_id=meter_id)\
        .order_by(SecurityAuditLog.timestamp.desc())\
        .all()
    
    print("\nSecurity Audit Logs:")
    for log in audit_logs:
        print(f"\nEvent Type: {log.event_type}")
        print(f"Action: {log.action}")
        print(f"User ID: {log.user_id}")
        print(f"IP Address: {log.ip_address}")
        print(f"Timestamp: {log.timestamp}")
        print(f"Status: {log.status}")

if __name__ == "__main__":
    demonstrate_security_features()
