from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from apscheduler.schedulers.background import BackgroundScheduler
from cryptography.fernet import Fernet
import os
from datetime import datetime, timezone
import json
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reels_poster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching

db = SQLAlchemy(app)
scheduler = BackgroundScheduler()
scheduler.start()

# Rate limiting setup
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_poster.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Encryption setup
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key().decode())
if not ENCRYPTION_KEY or ENCRYPTION_KEY == Fernet.generate_key().decode():
    logger.warning("Using default encryption key. Generate a secure key in production!")
try:
    cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
except Exception as e:
    logger.error(f"Encryption key is invalid: {e}")
    raise

def encrypt_password(password):
    if not password:
        raise ValueError("Password cannot be empty")
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    if not encrypted_password:
        raise ValueError("Encrypted password cannot be empty")
    try:
        return cipher.decrypt(encrypted_password.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt password: {e}")
        raise ValueError("Failed to decrypt password")

# Database Models
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)  # encrypted
    session_data = db.Column(db.Text)  # JSON string for instagrapi session
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    video_path = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.Text)
    hashtags = db.Column(db.Text)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, posted, failed
    posted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    account = db.relationship('Account', backref=db.backref('posts', lazy=True))

class ScheduleConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interval_hours = db.Column(db.Integer, default=1)
    active = db.Column(db.Boolean, default=True)

# Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.after_request
def add_cache_control(response):
    response.cache_control.no_cache = True
    response.cache_control.no_store = True
    response.cache_control.must_revalidate = True
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/accounts', methods=['GET', 'POST'])
@limiter.limit("30 per minute")
def manage_accounts():
    if request.method == 'POST':
        try:
            data = request.json
            
            # Input validation
            if not data or 'username' not in data or 'password' not in data:
                return jsonify({'message': 'Username and password are required'}), 400
            
            username = data['username'].strip()
            password = data['password'].strip()
            
            if not username or not password:
                return jsonify({'message': 'Username and password cannot be empty'}), 400
            
            if len(username) < 3 or len(username) > 100:
                return jsonify({'message': 'Username must be between 3 and 100 characters'}), 400
            
            if len(password) < 6:
                return jsonify({'message': 'Password must be at least 6 characters'}), 400
            
            existing = Account.query.filter_by(username=username).first()
            if existing:
                return jsonify({'message': 'Account with this username already exists'}), 400
            
            try:
                encrypted_password = encrypt_password(password)
                account = Account(
                    username=username,
                    password=encrypted_password,
                    is_active=data.get('is_active', True)
                )
                db.session.add(account)
                db.session.commit()
                logger.info(f"Account added: {username}")
                return jsonify({'message': 'Account added successfully', 'id': account.id}), 201
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding account: {e}")
                return jsonify({'message': 'Failed to add account'}), 500
        except Exception as e:
            logger.error(f"Unexpected error in manage_accounts POST: {e}")
            return jsonify({'message': 'An unexpected error occurred'}), 500

    try:
        accounts = Account.query.all()
        return jsonify([{
            'id': acc.id,
            'username': acc.username,
            'is_active': acc.is_active,
            'created_at': acc.created_at.isoformat()
        } for acc in accounts])
    except Exception as e:
        logger.error(f"Error retrieving accounts: {e}")
        return jsonify({'message': 'Failed to retrieve accounts'}), 500

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
def delete_account(account_id):
    try:
        account = Account.query.get(account_id)
        if not account:
            return jsonify({'message': 'Account not found'}), 404
        
        # Check if account has pending posts
        pending_posts = Post.query.filter_by(account_id=account_id, status='pending').count()
        if pending_posts > 0:
            return jsonify({'message': 'Cannot delete account with pending posts'}), 400
        
        db.session.delete(account)
        db.session.commit()
        logger.info(f"Account deleted: {account.username}")
        return jsonify({'message': 'Account deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting account {account_id}: {e}")
        return jsonify({'message': 'Failed to delete account'}), 500

@app.route('/api/posts', methods=['GET', 'POST'])
@limiter.limit("30 per minute")
def manage_posts():
    if request.method == 'POST':
        try:
            data = request.json
            
            # Input validation
            if not data or 'accountId' not in data or 'videoPath' not in data or 'scheduledTime' not in data:
                return jsonify({'message': 'accountId, videoPath, and scheduledTime are required'}), 400
            
            video_path = data['videoPath'].strip()
            
            if not video_path or len(video_path) > 500:
                return jsonify({'message': 'Video path is invalid'}), 400
            
            # Validate file exists
            if not os.path.exists(video_path):
                return jsonify({'message': 'Video file does not exist'}), 400
            
            # Validate scheduled time
            try:
                scheduled_time = datetime.fromisoformat(data['scheduledTime'])
                if scheduled_time <= datetime.now(timezone.utc):
                    return jsonify({'message': 'Scheduled time must be in the future'}), 400
            except ValueError:
                return jsonify({'message': 'Invalid scheduled time format'}), 400
            
            # Verify account exists
            account = Account.query.get(data['accountId'])
            if not account:
                return jsonify({'message': 'Account not found'}), 404
            
            try:
                post = Post(
                    account_id=data['accountId'],
                    video_path=video_path,
                    caption=data.get('caption', '').strip()[:1000],  # Limit to 1000 chars
                    hashtags=data.get('hashtags', '').strip()[:500],  # Limit to 500 chars
                    scheduled_time=scheduled_time
                )
                db.session.add(post)
                db.session.commit()

                # Schedule the post
                scheduler.add_job(
                    func=post_to_instagram,
                    trigger="date",
                    run_date=post.scheduled_time,
                    args=[post.id],
                    id=f'post_{post.id}',
                    misfire_grace_time=300
                )
                logger.info(f"Post scheduled: {post.id} for {account.username}")
                return jsonify({'message': 'Post scheduled successfully', 'id': post.id}), 201
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error scheduling post: {e}")
                return jsonify({'message': 'Failed to schedule post'}), 500
        except Exception as e:
            logger.error(f"Unexpected error in manage_posts POST: {e}")
            return jsonify({'message': 'An unexpected error occurred'}), 500

    try:
        posts = Post.query.order_by(Post.scheduled_time).all()
        return jsonify([{
            'id': p.id,
            'account_username': p.account.username,
            'video_path': p.video_path,
            'caption': p.caption,
            'hashtags': p.hashtags,
            'scheduled_time': p.scheduled_time.isoformat(),
            'status': p.status,
            'posted_at': p.posted_at.isoformat() if p.posted_at else None
        } for p in posts])
    except Exception as e:
        logger.error(f"Error retrieving posts: {e}")
        return jsonify({'message': 'Failed to retrieve posts'}), 500

def post_to_instagram(post_id):
    from instagrapi import Client

    post = Post.query.get(post_id)
    if not post:
        logger.error(f"Post {post_id} not found")
        return

    logger.info(f"Starting post upload for {post_id}")
    account = post.account
    try:
        api = Client()
        api.delay_range = [1, 3]

        # Load session if exists
        if account.session_data:
            try:
                session_dict = json.loads(account.session_data)
                api.set_settings(session_dict)
                api.login(account.username, decrypt_password(account.password))
                logger.info(f"Logged in with session for {account.username}")
            except Exception as e:
                logger.warning(f"Session login failed, attempting fresh login: {e}")
                api.login(account.username, decrypt_password(account.password))
        else:
            api.login(account.username, decrypt_password(account.password))
            # Save session
            try:
                account.session_data = json.dumps(api.get_settings())
                db.session.commit()
                logger.info(f"Logged in and saved session for {account.username}")
            except Exception as e:
                logger.warning(f"Failed to save session: {e}")

        # Post the reel
        full_caption = f"{post.caption}\n\n{post.hashtags}".strip()
        logger.info(f"Uploading video {post.video_path} with caption: {full_caption[:50]}...")
        
        media = api.clip_upload(post.video_path, full_caption)

        if media:
            post.status = 'posted'
            post.posted_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.info(f"Post {post_id} uploaded successfully")
        else:
            post.status = 'failed'
            db.session.commit()
            logger.error(f"Post {post_id} failed: no media returned")

    except Exception as e:
        post.status = 'failed'
        db.session.commit()
        logger.error(f"Posting failed for post {post_id}: {str(e)}", exc_info=True)

@app.route('/api/schedule-config', methods=['GET', 'PUT'])
@limiter.limit("20 per minute")
def schedule_config():
    try:
        config = ScheduleConfig.query.first()
        if not config:
            config = ScheduleConfig()
            db.session.add(config)
            db.session.commit()

        if request.method == 'PUT':
            try:
                data = request.json
                
                # Input validation
                interval = data.get('interval_hours', config.interval_hours)
                if not isinstance(interval, int) or interval < 1 or interval > 168:
                    return jsonify({'message': 'interval_hours must be between 1 and 168'}), 400
                
                config.interval_hours = interval
                config.active = data.get('active', config.active)
                db.session.commit()
                logger.info(f"Configuration updated: interval={interval}, active={config.active}")
                return jsonify({'message': 'Configuration updated'})
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating schedule config: {e}")
                return jsonify({'message': 'Failed to update configuration'}), 500

        return jsonify({
            'interval_hours': config.interval_hours,
            'active': config.active
        })
    except Exception as e:
        logger.error(f"Error in schedule_config: {e}")
        return jsonify({'message': 'Failed to retrieve configuration'}), 500

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
def delete_post(post_id):
    try:
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'message': 'Post not found'}), 404
        
        if post.status != 'pending':
            return jsonify({'message': 'Only pending posts can be deleted'}), 400
        
        # Remove from scheduler
        try:
            scheduler.remove_job(f'post_{post_id}')
        except Exception as e:
            logger.warning(f"Job post_{post_id} not found in scheduler: {e}")
        
        db.session.delete(post)
        db.session.commit()
        logger.info(f"Post deleted: {post_id}")
        return jsonify({'message': 'Post deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({'message': 'Failed to delete post'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded: {e.description}")
    return jsonify({'message': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(404)
def not_found(e):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({'message': 'Internal server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("Database initialized")
        
        # Reschedule pending posts
        try:
            pending_posts = Post.query.filter_by(status='pending').all()
            now = datetime.now(timezone.utc)
            for post in pending_posts:
                # Handle both naive and aware datetimes
                scheduled_time = post.scheduled_time
                if scheduled_time.tzinfo is None:
                    scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
                
                if scheduled_time > now:
                    scheduler.add_job(
                        func=post_to_instagram,
                        trigger="date",
                        run_date=scheduled_time,
                        args=[post.id],
                        id=f'post_{post.id}',
                        misfire_grace_time=300
                    )
                    logger.info(f"Rescheduled post {post.id}")
                else:
                    # If scheduled time has passed, post immediately
                    logger.info(f"Posting missed post {post.id} immediately")
                    post_to_instagram(post.id)
        except Exception as e:
            logger.error(f"Error rescheduling posts on startup: {e}")
    
    logger.info("Starting Instagram Reels Poster application")
    app.run(debug=False, host='0.0.0.0', port=5000)