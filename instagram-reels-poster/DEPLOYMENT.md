# Production Deployment Guide

## Security Configuration

### 1. Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save this key in your `.env` file as `ENCRYPTION_KEY`.

### 2. Update Environment Variables

Create a production `.env` file with:

```env
SECRET_KEY=your-secure-random-key-32-characters-minimum
ENCRYPTION_KEY=your-generated-fernet-key
FLASK_ENV=production
```

### 3. Secure Requirements

- Never commit `.env` file to version control
- Use strong, unique encryption keys per deployment
- Change `SECRET_KEY` for production
- Set `debug=False` in production (already configured)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize database:
```bash
python app.py
```

3. Run with production server (not Flask development server):
```bash
gunicorn --workers 4 --worker-class sync --bind 0.0.0.0:5000 app:app
```

## Features

### Rate Limiting
- Accounts: 30 requests/minute
- Posts: 30 requests/minute  
- Config: 20 requests/minute
- Default: 200 requests/day, 50 requests/hour

### Error Handling
- All endpoints have try-catch error handling
- Database sessions rollback on errors
- Comprehensive logging to `instagram_poster.log`
- Proper HTTP status codes

### Data Validation
- Username length: 3-100 characters
- Password minimum: 6 characters
- Video path validation and file existence check
- Scheduled time must be in the future
- Caption limit: 1000 characters
- Hashtags limit: 500 characters

### Database Models
- **Account**: Stores Instagram credentials (encrypted)
- **Post**: Stores scheduled posts with status tracking
- **ScheduleConfig**: Stores scheduling configuration

## Logging

All events are logged to `instagram_poster.log`:
- Account operations (add, delete)
- Post scheduling and uploads
- Login attempts and session management
- Errors and exceptions with stack traces

## Monitoring

Check logs regularly:
```bash
tail -f instagram_poster.log
```

Monitor pending posts:
- Dashboard shows real-time post status
- Automatic rescheduling of missed posts on app restart
- 5-minute grace period for overdue posts
