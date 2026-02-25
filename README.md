# Smart Electric Meter System

A Python-based smart electric meter system that supports both prepaid and postpaid billing modes.

## Features

- Dual mode support: Prepaid and Postpaid
- Balance tracking for prepaid meters
- Usage monitoring and history
- Flexible rate configuration
- Automatic disconnection for prepaid meters with insufficient credit
- Bill generation for postpaid meters
- Transaction and usage history logging

## Usage

### Creating a Meter

```python
from smart_meter import SmartMeter, MeterMode

# Create a prepaid meter
prepaid_meter = SmartMeter("METER001", MeterMode.PREPAID)

# Create a postpaid meter
postpaid_meter = SmartMeter("METER002", MeterMode.POSTPAID)
```

### Prepaid Mode Operations

```python
# Add credit
prepaid_meter.add_credit(50.0)

# Consume power
prepaid_meter.consume_power(10)  # Consume 10 kWh

# Check stats
print(prepaid_meter.get_consumption_stats())
```

### Postpaid Mode Operations

```python
# Consume power
postpaid_meter.consume_power(15)  # Consume 15 kWh

# Get bill
bill = postpaid_meter.get_bill()
print(f"Current bill: {bill}")
```

### Switching Modes

```python
meter.switch_mode(MeterMode.PREPAID)  # Switch to prepaid
meter.switch_mode(MeterMode.POSTPAID)  # Switch to postpaid
```

## Credit Loading Methods (Prepaid Mode)

### Token-based Credit Loading
```python
# Generate a token (typically done by the utility company)
token = SmartMeter.generate_token(amount=20.0, meter_id="METER001", secret_key="YOUR_SECRET_KEY")

# Load credit using the token
meter.load_token_credit(token)
```

### Remote Credit Loading
```python
# Load credit remotely (e.g., through a mobile app or utility company's system)
meter.remote_credit_load(amount=30.0, transaction_id="TRANSACTION_123")
```

## Security Features

### Authentication & Authorization
- Secure password hashing using bcrypt
- API key authentication for remote operations
- JWT token-based authentication
- Automatic credential generation for new meters

### Token Security
- AES encryption for token generation and validation
- One-time use tokens with database tracking
- Transaction ID tracking
- Meter-specific token validation

### Database Security
- SQLite database for persistent storage
- Secure transaction logging
- Token usage tracking
- User credential management

### Environment Variables
Create a `.env` file with the following variables:
```
JWT_SECRET_KEY=your_secure_jwt_secret_key_here
ENCRYPTION_KEY=your_secure_encryption_key_here
```

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Set up the environment variables in `.env`

3. Initialize the database (automatic on first run)

## Security Best Practices

1. **API Key Management**:
   - Store API keys securely
   - Regenerate API keys periodically
   - Never share API keys in code or version control

2. **Password Security**:
   - Change default passwords immediately
   - Use strong passwords
   - Regular password rotation

3. **Token Handling**:
   - Tokens are single-use only
   - Tokens are meter-specific
   - Tokens expire after use
   - All token operations are logged

## Features

- **Balance Tracking**: Automatically tracks remaining credit for prepaid meters
- **Usage Monitoring**: Records all power consumption with timestamps
- **Flexible Billing**: Supports both prepaid and postpaid billing modes
- **Safety Features**: Automatic disconnection when prepaid credit is exhausted
- **Usage Statistics**: Provides detailed consumption and payment history
# smart_meter
