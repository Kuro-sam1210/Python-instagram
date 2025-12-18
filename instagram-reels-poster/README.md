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

## Setup

1. **Clone and Install Dependencies**:
   ```bash
   cd instagram-reels-poster
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   - Copy `.env` and update the values
   - Generate encryption key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

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

- Credentials are encrypted using Fernet encryption
- Instagram sessions are cached for efficiency
- Use at your own risk - Instagram may ban accounts for automation

## API Endpoints

- `GET/POST /api/accounts` - Manage Instagram accounts
- `GET/POST /api/posts` - Manage scheduled posts
- `GET/PUT /api/schedule-config` - Configure posting intervals

## Requirements

- Python 3.8+
- Instagram accounts (preferably Business/Creator accounts)
- Google Drive API credentials (optional)

## Disclaimer

This tool uses unofficial Instagram APIs. Usage may violate Instagram's terms of service. Use responsibly and at your own risk.