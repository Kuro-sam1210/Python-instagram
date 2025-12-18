# Quick Reference Guide

## Installation & Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate encryption key (for production)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. Update .env with the generated key

# 4. Run the application
python app.py
```

## API Endpoints

### Accounts
- `GET /api/accounts` - List all accounts
- `POST /api/accounts` - Add new account
  ```json
  {"username": "instagram_user", "password": "secure_password"}
  ```
- `DELETE /api/accounts/<id>` - Delete account (no pending posts)

### Posts
- `GET /api/posts` - List all posts
- `POST /api/posts` - Schedule new post
  ```json
  {
    "accountId": 1,
    "videoPath": "/path/to/video.mp4",
    "caption": "Post caption",
    "hashtags": "#hashtag1 #hashtag2",
    "scheduledTime": "2024-12-25T15:30:00"
  }
  ```
- `DELETE /api/posts/<id>` - Delete pending post only

### Configuration
- `GET /api/schedule-config` - Get config
- `PUT /api/schedule-config` - Update config
  ```json
  {"interval_hours": 2, "active": true}
  ```

## Input Limits

| Field | Min | Max | Notes |
|-------|-----|-----|-------|
| Username | 3 | 100 | Must be unique |
| Password | 6 | N/A | Encrypted in DB |
| Video Path | 1 | 500 | Must exist |
| Caption | 0 | 1000 | Optional |
| Hashtags | 0 | 500 | Optional |
| Interval Hours | 1 | 168 | 1 week max |

## Rate Limits

- Accounts: **30 requests/minute**
- Posts: **30 requests/minute**
- Config: **20 requests/minute**
- Global: **200/day, 50/hour**

## Database

Location: `instagram-reels-poster/instance/reels_poster.db`

Tables:
- `account` - Instagram accounts (credentials encrypted)
- `post` - Scheduled posts with status tracking
- `schedule_config` - Scheduling settings

## Logging

- File: `instagram_poster.log`
- Format: `TIMESTAMP - NAME - LEVEL - MESSAGE`
- Includes: operations, errors, login attempts, post uploads

## Dashboard Features

- **Add Account**: Register Instagram account
- **Schedule Post**: Set video, caption, hashtags, time
- **Monitor**: View pending, posted, and failed posts
- **Delete**: Remove accounts (if no pending posts) or pending posts

## Environment Variables

```env
SECRET_KEY=your-secret-key          # Flask session encryption
ENCRYPTION_KEY=your-fernet-key      # Password encryption
FLASK_ENV=production                # Set to 'production' for live
```

## Error Response Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request (validation failed) |
| 401 | Unauthorized (not implemented) |
| 404 | Not found |
| 429 | Too many requests (rate limited) |
| 500 | Server error |

## Troubleshooting

**"Import flask_limiter not found"**
→ Run `pip install -r requirements.txt`

**"Invalid encryption key"**
→ Generate new key and update `.env`

**"Rate limit exceeded"**
→ Wait before making more requests

**Posts not uploading**
→ Check `instagram_poster.log` for error details

## Production Checklist

- [ ] Generate secure `ENCRYPTION_KEY`
- [ ] Set strong `SECRET_KEY`
- [ ] Install production dependencies
- [ ] Use `gunicorn` instead of Flask dev server
- [ ] Enable HTTPS/SSL
- [ ] Set `FLASK_ENV=production`
- [ ] Monitor `instagram_poster.log`
- [ ] Back up database regularly
- [ ] Never commit `.env` to git
