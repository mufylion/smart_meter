from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()

class EventType(str, enum.Enum):
    POWER_QUALITY = "power_quality"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    COMMUNICATION = "communication"
    TAMPER = "tamper"
    DEMAND_RESPONSE = "demand_response"

class PowerQualityEventType(str, enum.Enum):
    VOLTAGE_SAG = "voltage_sag"
    VOLTAGE_SWELL = "voltage_swell"
    FREQUENCY_DEVIATION = "frequency_deviation"
    POWER_OUTAGE = "power_outage"
    POWER_RESTORE = "power_restore"

class DemandResponseEventType(str, enum.Enum):
    LOAD_REDUCTION = "load_reduction"
    LOAD_SHIFT = "load_shift"
    PRICE_RESPONSE = "price_response"
    EMERGENCY_DR = "emergency_dr"

class CommunicationProtocol(str, enum.Enum):
    ANSI_C12_19 = "ansi_c12_19"
    DLMS_COSEM = "dlms_cosem"
    IEC_61850 = "iec_61850"

class STSTokenClass(str, enum.Enum):
    MANAGEMENT = "0"
    CREDIT = "1"
    RAW = "2"
    CONFIGURATION = "3"
    DISPLAY = "4"

class STSTokenSubclass(str, enum.Enum):
    # Class 0 (Management)
    SET_MAXIMUM_POWER_LIMIT = "0"
    CLEAR_TAMPER = "1"
    SET_TARIFF_RATE = "2"
    SET_1ST_SECTION_DECODER_KEY = "3"
    SET_2ND_SECTION_DECODER_KEY = "4"
    CLEAR_CREDIT = "5"
    SET_METER_MODE = "6"
    
    # Class 1 (Credit)
    CREDIT_TRANSFER = "0"
    EMERGENCY_CREDIT = "1"
    
    # Class 2 (Raw)
    RESERVED = "0"
    
    # Class 3 (Configuration)
    SET_TARIFF_STRUCTURE = "0"
    SET_MAXIMUM_PHASE_POWER = "1"
    
    # Class 4 (Display)
    DISPLAY_REGISTER = "0"

class MeterMode(str, enum.Enum):
    PREPAID = "prepaid"
    POSTPAID = "postpaid"

class TokenStatus(str, enum.Enum):
    VALID = "valid"
    INVALID = "invalid"
    USED = "used"
    EXPIRED = "expired"
    KEY_EXPIRED = "key_expired"
    KEY_REVISION_MISMATCH = "key_revision_mismatch"

class STSToken(Base):
    __tablename__ = 'sts_tokens'
    
    id = Column(Integer, primary_key=True)
    token_number = Column(String, unique=True, nullable=False)
    token_identifier = Column(Integer, nullable=False)  # TID
    token_class = Column(String, nullable=False)
    token_subclass = Column(String, nullable=False)
    amount = Column(Float, nullable=True)  # For credit tokens
    key_revision_number = Column(Integer, nullable=False)
    key_expiry_number = Column(Integer, nullable=False)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("MeterUser", back_populates="tokens")

class MeterUser(Base):
    __tablename__ = 'meter_users'
    
    meter_id = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    decoder_key = Column(String, nullable=False)  # Encrypted
    key_revision_number = Column(Integer, default=1)
    key_expiry_number = Column(Integer, nullable=False)
    vending_key = Column(String, nullable=False)  # Encrypted
    supply_group_code = Column(String, nullable=False)
    tariff_index = Column(Integer, default=1)
    key_change_register = Column(Integer, default=0)
    power_limit = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    
    tokens = relationship("STSToken", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    load_profiles = relationship("LoadProfile", back_populates="user")
    power_quality_events = relationship("PowerQualityEvent", back_populates="user")
    event_logs = relationship("EventLog", back_populates="user")
    demand_response_events = relationship("DemandResponseEvent", back_populates="user")
    communication_logs = relationship("CommunicationLog", back_populates="user")
    firmware_updates = relationship("FirmwareUpdate", back_populates="user")
    security_audit_logs = relationship("SecurityAuditLog", back_populates="user")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("MeterUser", back_populates="transactions")

class LoadProfile(Base):
    __tablename__ = 'load_profiles'
    
    id = Column(Integer, primary_key=True)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    voltage = Column(Float, nullable=False)
    current = Column(Float, nullable=False)
    power_factor = Column(Float, nullable=False)
    active_power = Column(Float, nullable=False)
    reactive_power = Column(Float, nullable=False)
    frequency = Column(Float, nullable=False)
    interval_minutes = Column(Integer, nullable=False)
    
    user = relationship("MeterUser", back_populates="load_profiles")

class PowerQualityEvent(Base):
    __tablename__ = 'power_quality_events'
    
    id = Column(Integer, primary_key=True)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    duration = Column(Float, nullable=True)  # in seconds
    magnitude = Column(Float, nullable=True)  # depends on event type
    nominal_value = Column(Float, nullable=True)
    measured_value = Column(Float, nullable=True)
    
    user = relationship("MeterUser", back_populates="power_quality_events")

class EventLog(Base):
    __tablename__ = 'event_logs'
    
    id = Column(Integer, primary_key=True)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    additional_data = Column(String, nullable=True)
    
    user = relationship("MeterUser", back_populates="event_logs")

class DemandResponseEvent(Base):
    __tablename__ = 'demand_response_events'
    
    id = Column(Integer, primary_key=True)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    event_type = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    target_reduction = Column(Float, nullable=False)  # in kW
    actual_reduction = Column(Float, nullable=True)   # in kW
    status = Column(String, nullable=False)  # scheduled, active, completed, cancelled
    priority = Column(Integer, nullable=False)
    
    user = relationship("MeterUser", back_populates="demand_response_events")

class CommunicationLog(Base):
    __tablename__ = 'communication_logs'
    
    id = Column(Integer, primary_key=True)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    protocol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    message_type = Column(String, nullable=False)
    message_data = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    retry_count = Column(Integer, default=0)
    
    user = relationship("MeterUser", back_populates="communication_logs")

class FirmwareUpdate(Base):
    __tablename__ = 'firmware_updates'
    
    id = Column(Integer, primary_key=True)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    version = Column(String, nullable=False)
    update_time = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)
    signature = Column(String, nullable=False)
    checksum = Column(String, nullable=False)
    
    user = relationship("MeterUser", back_populates="firmware_updates")

class SecurityAuditLog(Base):
    __tablename__ = 'security_audit_logs'
    
    id = Column(Integer, primary_key=True)
    meter_id = Column(String, ForeignKey('meter_users.meter_id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    event_type = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    
    user = relationship("MeterUser", back_populates="security_audit_logs")

# Create database engine
engine = create_engine('sqlite:///smart_meter.db')

# Create all tables
Base.metadata.create_all(engine)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
