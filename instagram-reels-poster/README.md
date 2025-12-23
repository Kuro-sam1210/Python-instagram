# Instagram Reels Poster

A web-based automation tool for scheduling and posting Instagram reels to multiple accounts with recurring intervals.

## Features

- **Multi-Account Support**: Manage up to 6 Instagram accounts
- **Scheduled Posting**: Schedule posts with precise timing
- **Recurring Intervals**: Automatic posting every 1-2 hours
- **Custom Captions & Hashtags**: Per-post customization
- **Google Drive Integration**: Fetch videos from Google Drive (planned)
- **Web Dashboard**: Easy-to-use interface for management
- **Secure Storage**: Encrypted credentials and session management

## Quick Setup

**Automated Setup (Recommended)**:

```bash
# Make setup script executable (Linux/macOS)
chmod +x setup.sh
./setup.sh

# Or on Windows with bash:
bash setup.sh
```

The setup script will:
- Check Python version compatibility
- Create virtual environment
- Install dependencies
- Generate secure keys (API_KEY, ENCRYPTION_KEY, SECRET_KEY, DEVICE_SALT)
- Initialize database
- Create uploads directory

**Manual Setup**:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   - Copy `.env.example` to `.env`
   - Generate required keys:
     ```bash
     # API key for authentication
     python -c "import secrets; print(secrets.token_urlsafe(32))"

     # Encryption key for passwords
     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

     # Secret key for Flask sessions
     python -c "import secrets; print(secrets.token_hex(32))"

     # Device salt for consistent fingerprints (IMPORTANT: Never change in production!)
     python -c "import secrets; print(secrets.token_hex(32))"
     ```

3. **Run the Application**:
   ```bash
   python app.py
   ```

4. **Access Dashboard**:
   - Open http://localhost:5000 in your browser

## Usage

1. **Add Instagram Accounts**:
   - Click "Add Account" in the dashboard
   - Enter username and password (stored encrypted)

2. **Schedule Posts**:
   - Click "Schedule New Post"
   - Select account, provide video path, caption, hashtags
   - Set schedule time

3. **Monitor**:
   - View scheduled and posted content in the dashboard
   - Check status of each post

## Google Drive Integration (Future)

To enable Google Drive integration:

1. Set up Google Cloud Console project
2. Enable Google Drive API
3. Download credentials.json
4. Update .env with credentials path and folder ID

## Security Notes

- **Encrypted Storage**: Credentials are encrypted using Fernet encryption
- **Device Consistency**: Device fingerprints use a separate salt (DEVICE_SALT) to remain consistent even if encryption keys are rotated
- **Session Management**: Instagram sessions are stored in JSON files and automatically refreshed when needed
- **WARNING**: Never change DEVICE_SALT in production - it will invalidate all existing sessions
- **Risk**: Use at your own risk - Instagram may ban accounts for automation

## API Endpoints

- `GET/POST /api/accounts` - Manage Instagram accounts
- `GET/POST /api/posts` - Manage scheduled posts
- `GET/PUT /api/schedule-config` - Configure posting intervals

## Requirements

- Python 3.9+
- Instagram accounts (preferably Business/Creator accounts)
- ffmpeg (optional, for video validation)
- Google Drive API credentials (optional)

## Disclaimer

This tool uses unofficial Instagram APIs. Usage may violate Instagram's terms of service. Use responsibly and at your own risk.