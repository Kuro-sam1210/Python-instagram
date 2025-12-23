from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from cryptography.fernet import Fernet
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy import event
import os
from datetime import datetime, timezone, timedelta
import json
import logging
import uuid
from werkzeug.utils import secure_filename
from functools import wraps
from dotenv import load_dotenv
import hashlib

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///reels_poster.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable must be set")

UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi'}
MAX_VIDEO_DURATION = 90  # seconds

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

# Use Redis for rate limiting if available, otherwise memory
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=REDIS_URL
    )
else:
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

# Enable scheduler debug logging
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

# API Key authentication
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-API-Key') != API_KEY:
            return jsonify({'message': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Encryption setup - MUST be set in environment
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    logger.error("ENCRYPTION_KEY not set in environment variables!")
    raise ValueError(
        "ENCRYPTION_KEY must be set in environment variables. "
        "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

# Device salt - SEPARATE from encryption key to prevent device changes on key rotation
DEVICE_SALT = os.environ.get('DEVICE_SALT')
if not DEVICE_SALT:
    logger.error("DEVICE_SALT not set in environment variables!")
    raise ValueError(
        "DEVICE_SALT must be set in environment variables. "
        "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
        "\nWARNING: Never change this value in production - it will invalidate all sessions!"
    )

try:
    cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
except Exception as e:
    logger.error(f"Invalid encryption key: {e}")
    raise ValueError("ENCRYPTION_KEY is invalid. Must be a valid Fernet key.")

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
        raise ValueError("Failed to decrypt password - encryption key may have changed")

def generate_device_config(account_id):
    """Generate deterministic device config per account"""
    # Use DEVICE_SALT (not ENCRYPTION_KEY) to ensure device consistency
    # even if encryption key is rotated
    seed = hashlib.sha256(f"device_{account_id}_{DEVICE_SALT}".encode()).hexdigest()

    # Generate deterministic UUIDs from seed
    def seeded_uuid(prefix):
        return str(uuid.UUID(hashlib.md5(f"{seed}_{prefix}".encode()).hexdigest()))

    devices = [
        ("Samsung", "SM-G991B", "o1s", "exynos2100"),
        ("Google", "Pixel 6", "oriole", "tensor"),
        ("OnePlus", "9 Pro", "lemonadep", "snapdragon888"),
        ("Xiaomi", "Mi 11", "venus", "snapdragon888"),
    ]

    # Select device based on account_id
    device_info = devices[account_id % len(devices)]

    return {
        "app_version": "269.0.0.18.75",
        "android_version": 12,
        "android_release": "12",
        "dpi": "420dpi",
        "resolution": "1080x2340",
        "manufacturer": device_info[0],
        "device": device_info[2],
        "model": device_info[1],
        "cpu": device_info[3],
        "uuids": {
            "phone_id": seeded_uuid("phone"),
            "uuid": seeded_uuid("uuid"),
            "client_session_id": seeded_uuid("client"),
            "advertising_id": seeded_uuid("advertising"),
            "device_id": f"android-{seeded_uuid('device').replace('-', '')[:16]}"
        }
    }

# Database Models
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.Text, nullable=False)  # encrypted
    # Session stored in session_<username>.json files only (no DB duplication)
    is_active = db.Column(db.Boolean, default=True)
    last_post_time = db.Column(db.DateTime)  # Track posting frequency
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    posts = db.relationship(
        'Post',
        backref='account',
        cascade='all, delete-orphan',
        passive_deletes=True
    )

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer,
        db.ForeignKey('account.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    video_filename = db.Column(db.String(500), nullable=False)  # Store relative filename only
    caption = db.Column(db.Text)
    hashtags = db.Column(db.Text)
    scheduled_time = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, posted, failed
    posted_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)  # Store failure reason
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def video_path(self):
        """Get full video path"""
        return os.path.join(app.config['UPLOAD_FOLDER'], self.video_filename)

    def cleanup_video(self):
        """Remove video file from disk"""
        try:
            path = self.video_path
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Cleaned up video file: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup video file: {e}")

class ScheduleConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interval_hours = db.Column(db.Integer, default=1)
    active = db.Column(db.Boolean, default=True)

# Initialize scheduler AFTER models are defined
scheduler = BackgroundScheduler(
    jobstores={
        'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
    },
    job_defaults={
        'coalesce': True,  # Combine multiple missed executions into one
        'max_instances': 1  # Prevent duplicate executions
    }
)

def validate_video_file(file_path):
    """Validate video duration and format"""
    try:
        import subprocess

        # Check file exists
        if not os.path.exists(file_path):
            return False, "Video file not found"

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:  # 100MB
            return False, "Video file too large (max 100MB)"

        # Use ffprobe to check duration (if available)
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                if duration > MAX_VIDEO_DURATION:
                    return False, f"Video too long (max {MAX_VIDEO_DURATION}s)"
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            # ffprobe not available or failed, skip duration check
            logger.warning("ffprobe not available, skipping duration validation")
            pass

        return True, None
    except Exception as e:
        logger.error(f"Video validation error: {e}")
        return False, str(e)

# Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Check database
        db.session.execute('SELECT 1').scalar()
        db_status = 'healthy'
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = 'unhealthy'

    # Check scheduler
    scheduler_status = 'running' if scheduler.running else 'stopped'

    # Get job counts
    try:
        pending_jobs = len(scheduler.get_jobs())
    except:
        pending_jobs = 0

    status_code = 200 if db_status == 'healthy' and scheduler_status == 'running' else 503

    return jsonify({
        'status': 'healthy' if status_code == 200 else 'degraded',
        'database': db_status,
        'scheduler': scheduler_status,
        'pending_jobs': pending_jobs,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), status_code

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
@require_api_key
def manage_accounts():
    if request.method == 'POST':
        try:
            data = request.json

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

            encrypted_password = encrypt_password(password)
            account = Account(
                username=username,
                password=encrypted_password,
                is_active=data.get('is_active', True)
            )

            db.session.add(account)
            db.session.commit()

            logger.info(f"Account added: {username} (ID: {account.id})")
            return jsonify({
                'message': 'Account added successfully',
                'id': account.id
            }), 201

        except ValueError as e:
            db.session.rollback()
            return jsonify({'message': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding account: {e}")
            return jsonify({'message': 'Failed to add account'}), 500

    # GET request
    try:
        accounts = Account.query.all()
        return jsonify([{
            'id': acc.id,
            'username': acc.username,
            'is_active': acc.is_active,
            'last_post_time': acc.last_post_time.isoformat() if acc.last_post_time else None,
            'created_at': acc.created_at.isoformat(),
            'post_count': len(acc.posts)
        } for acc in accounts])
    except Exception as e:
        logger.error(f"Error retrieving accounts: {e}")
        return jsonify({'message': 'Failed to retrieve accounts'}), 500

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
@require_api_key
def delete_account(account_id):
    try:
        account = db.session.get(Account, account_id)
        if not account:
            return jsonify({'message': 'Account not found'}), 404

        # Check for pending posts
        pending_posts = Post.query.filter_by(account_id=account_id, status='pending').all()
        if pending_posts:
            return jsonify({
                'message': f'Cannot delete account with {len(pending_posts)} pending posts'
            }), 400

        # Remove session file
        session_file = f"session_{account.username}.json"
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
                logger.info(f"Removed session file: {session_file}")
        except Exception as e:
            logger.warning(f"Failed to remove session file: {e}")

        # Cleanup video files for failed posts
        failed_posts = Post.query.filter_by(account_id=account_id, status='failed').all()
        for post in failed_posts:
            post.cleanup_video()

        username = account.username
        db.session.delete(account)
        db.session.commit()

        logger.info(f"Account deleted: {username}")
        return jsonify({'message': 'Account deleted successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting account {account_id}: {e}")
        return jsonify({'message': 'Failed to delete account'}), 500

@app.route('/api/posts', methods=['GET', 'POST'])
@limiter.limit("30 per minute")
@require_api_key
def manage_posts():
    if request.method == 'POST':
        try:
            account_id = request.form.get('accountId')
            caption = request.form.get('caption', '')
            hashtags = request.form.get('hashtags', '')
            scheduled_time_str = request.form.get('scheduledTime')

            if not account_id:
                return jsonify({'message': 'Account ID is required'}), 400

            if 'videoFile' not in request.files:
                return jsonify({'message': 'No video file uploaded'}), 400

            video_file = request.files['videoFile']
            if video_file.filename == '':
                return jsonify({'message': 'No selected file'}), 400

            if not allowed_file(video_file.filename):
                return jsonify({'message': 'Invalid file type. Only MP4, MOV, AVI allowed'}), 400

            # Verify account exists
            account = db.session.get(Account, account_id)
            if not account:
                return jsonify({'message': 'Account not found'}), 404

            if not account.is_active:
                return jsonify({'message': 'Account is not active'}), 400

            # Parse and validate scheduled time
            try:
                scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
                if scheduled_time.tzinfo is None:
                    scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError):
                return jsonify({'message': 'Invalid scheduled time format'}), 400

            now = datetime.now(timezone.utc)
            if scheduled_time < now:
                return jsonify({'message': 'Scheduled time must be in the future'}), 400

            # Check for duplicate scheduling (same account within 5 minutes)
            duplicate = Post.query.filter(
                Post.account_id == account_id,
                Post.status == 'pending',
                Post.scheduled_time.between(
                    scheduled_time - timedelta(minutes=5),
                    scheduled_time + timedelta(minutes=5)
                )
            ).first()

            if duplicate:
                return jsonify({
                    'message': 'Another post is already scheduled within 5 minutes of this time'
                }), 400

            # Save video file with unique name
            filename = f"{uuid.uuid4()}_{secure_filename(video_file.filename)}"
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video_file.save(video_path)

            # Validate video
            is_valid, error_msg = validate_video_file(video_path)
            if not is_valid:
                os.remove(video_path)
                return jsonify({'message': f'Video validation failed: {error_msg}'}), 400

            # Create post and schedule job in transaction
            try:
                post = Post(
                    account_id=account_id,
                    video_filename=filename,
                    caption=caption.strip()[:2200],  # Instagram limit
                    hashtags=hashtags.strip()[:500],
                    scheduled_time=scheduled_time
                )

                db.session.add(post)
                db.session.flush()  # Get post.id without committing

                # Schedule the job
                scheduler.add_job(
                    func=post_to_instagram,
                    trigger="date",
                    run_date=scheduled_time.astimezone(timezone.utc),
                    args=[post.id],
                    id=f'post_{post.id}',
                    misfire_grace_time=300,
                    replace_existing=True,
                    timezone="UTC"
                )

                db.session.commit()  # Commit only if job scheduled successfully

                logger.info(f"Post scheduled: {post.id} for {account.username} at {scheduled_time}")
                return jsonify({
                    'message': 'Post scheduled successfully',
                    'id': post.id,
                    'scheduled_time': scheduled_time.isoformat()
                }), 201

            except Exception as e:
                db.session.rollback()
                # Cleanup video file
                try:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                except:
                    pass
                raise e

        except Exception as e:
            logger.error(f"Error scheduling post: {e}")
            return jsonify({'message': f'Failed to schedule post: {str(e)}'}), 500

    # GET request
    try:
        # Support filtering
        status_filter = request.args.get('status')
        account_id_filter = request.args.get('account_id')

        query = Post.query

        if status_filter:
            query = query.filter_by(status=status_filter)
        if account_id_filter:
            query = query.filter_by(account_id=account_id_filter)

        posts = query.order_by(Post.scheduled_time.desc()).all()

        return jsonify([{
            'id': p.id,
            'account_id': p.account_id,
            'account_username': p.account.username if p.account else 'deleted_account',
            'video_filename': p.video_filename,
            'caption': p.caption,
            'hashtags': p.hashtags,
            'scheduled_time': p.scheduled_time.isoformat(),
            'status': p.status,
            'posted_at': p.posted_at.isoformat() if p.posted_at else None,
            'error_message': p.error_message,
            'created_at': p.created_at.isoformat()
        } for p in posts])

    except Exception as e:
        logger.error(f"Error retrieving posts: {e}")
        return jsonify({'message': 'Failed to retrieve posts'}), 500


def post_to_instagram(post_id):
    """Post to Instagram - runs in background scheduler"""
    with app.app_context():
        from instagrapi import Client
        from instagrapi.exceptions import LoginRequired

        logger.info(f"Starting post_to_instagram for post_id: {post_id}")

        try:
            post = db.session.get(Post, post_id)
            if not post:
                logger.warning(f"Post {post_id} no longer exists")
                return

            if post.status != 'pending':
                logger.info(f"Post {post_id} status is {post.status}, skipping")
                return

            account = post.account
            if not account:
                post.status = 'failed'
                post.error_message = 'Account no longer exists'
                db.session.commit()
                return

            if not account.is_active:
                post.status = 'failed'
                post.error_message = 'Account is not active'
                db.session.commit()
                return

            # Initialize API client with account-specific device config
            api = Client()
            api.delay_range = [2, 5]

            device_config = generate_device_config(account.id)
            api.set_device(device_config)
            api.set_uuids(device_config['uuids'])

            # Load session
            session_file = f"session_{account.username}.json"
            if not os.path.exists(session_file):
                post.status = 'failed'
                post.error_message = f'Session file missing – run create_session.py for {account.username}'
                db.session.commit()
                logger.error(post.error_message)
                return

            try:
                api.load_settings(session_file)

                # Light, low-risk validation only
                # account_info() is smaller/safer than get_timeline_feed()
                api.account_info()

                logger.info(f"Session valid for {account.username}")

            except Exception as session_error:
                # NEVER attempt to login here
                post.status = 'failed'
                post.error_message = (
                    f"Session expired or invalid – manual regeneration required. "
                    f"Run create_session.py for {account.username}. "
                    f"Error: {str(session_error)[:200]}"
                )
                db.session.commit()
                logger.warning(f"Session failed for {account.username} – post {post.id} marked failed. "
                               f"Manual intervention needed.")
                return

            # Re-check post still exists after login
            db.session.refresh(post)
            if post.status != 'pending':
                logger.info(f"Post {post_id} status changed to {post.status}, aborting")
                return

            # Verify video file exists
            if not os.path.exists(post.video_path):
                post.status = 'failed'
                post.error_message = 'Video file not found'
                db.session.commit()
                logger.error(f"Video file not found: {post.video_path}")
                return

            # Post the reel
            full_caption = f"{post.caption}\n\n{post.hashtags}".strip()
            logger.info(f"Uploading video for post {post_id}")

            media = api.clip_upload(path=post.video_path, caption=full_caption)

            if media:
                post.status = 'posted'
                post.posted_at = datetime.now(timezone.utc)
                account.last_post_time = post.posted_at

                db.session.commit()

                logger.info(f"Post {post_id} uploaded successfully")

                # Cleanup video file
                post.cleanup_video()
            else:
                post.status = 'failed'
                post.error_message = 'Upload returned no media object'
                db.session.commit()
                logger.error(f"Post {post_id} failed: no media returned")

        except Exception as e:
            logger.error(f"Posting failed for post {post_id}: {str(e)}", exc_info=True)
            try:
                post = db.session.get(Post, post_id)
                if post and post.status == 'pending':
                    post.status = 'failed'
                    post.error_message = str(e)[:500]  # Limit error message length
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"Failed to update post status: {db_error}")

        finally:
            # Cleanup scheduler job
            try:
                scheduler.remove_job(f"post_{post_id}", jobstore="default")
            except Exception as e:
                logger.debug(f"Could not remove job post_{post_id}: {e}")

@app.route('/api/schedule-config', methods=['GET', 'PUT'])
@limiter.limit("20 per minute")
@require_api_key
def schedule_config():
    try:
        config = ScheduleConfig.query.first()
        if not config:
            config = ScheduleConfig()
            db.session.add(config)
            db.session.commit()

        if request.method == 'PUT':
            data = request.json

            interval = data.get('interval_hours', config.interval_hours)
            if not isinstance(interval, int) or interval < 1 or interval > 168:
                return jsonify({'message': 'interval_hours must be between 1 and 168'}), 400

            config.interval_hours = interval
            config.active = data.get('active', config.active)

            db.session.commit()
            logger.info(f"Configuration updated: interval={interval}, active={config.active}")

            return jsonify({'message': 'Configuration updated'})

        return jsonify({
            'interval_hours': config.interval_hours,
            'active': config.active
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in schedule_config: {e}")
        return jsonify({'message': 'Failed to manage configuration'}), 500

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
@require_api_key
def delete_post(post_id):
    try:
        post = db.session.get(Post, post_id)
        if not post:
            return jsonify({'message': 'Post not found'}), 404

        if post.status == 'posted':
            return jsonify({'message': 'Cannot delete posted content'}), 400

        # Remove from scheduler
        try:
            scheduler.remove_job(f'post_{post_id}')
            logger.info(f"Removed scheduled job for post {post_id}")
        except Exception as e:
            logger.debug(f"Job post_{post_id} not in scheduler: {e}")

        # Cleanup video file
        post.cleanup_video()

        db.session.delete(post)
        db.session.commit()

        logger.info(f"Post deleted: {post_id}")
        return jsonify({'message': 'Post deleted successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({'message': 'Failed to delete post'}), 500

@app.route('/api/posts/failed', methods=['DELETE'])
@limiter.limit("10 per minute")
@require_api_key
def clear_failed_posts():
    try:
        failed_posts = Post.query.filter_by(status='failed').all()
        deleted_count = 0

        for post in failed_posts:
            # Remove from scheduler if exists
            try:
                scheduler.remove_job(f'post_{post.id}')
            except Exception:
                pass

            # Cleanup video
            post.cleanup_video()

            db.session.delete(post)
            deleted_count += 1

        db.session.commit()
        logger.info(f"Cleared {deleted_count} failed posts")

        return jsonify({'message': f'Successfully cleared {deleted_count} failed posts'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing failed posts: {e}")
        return jsonify({'message': 'Failed to clear failed posts'}), 500

@app.route('/api/stats', methods=['GET'])
@limiter.limit("60 per minute")
@require_api_key
def get_stats():
    """Get system statistics"""
    try:
        stats = {
            'accounts': {
                'total': Account.query.count(),
                'active': Account.query.filter_by(is_active=True).count()
            },
            'posts': {
                'total': Post.query.count(),
                'pending': Post.query.filter_by(status='pending').count(),
                'posted': Post.query.filter_by(status='posted').count(),
                'failed': Post.query.filter_by(status='failed').count()
            },
            'scheduler': {
                'running': scheduler.running,
                'jobs': len(scheduler.get_jobs())
            }
        }

        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'message': 'Failed to retrieve stats'}), 500

# Error handlers
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

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'message': 'File too large. Maximum size is 100MB'}), 413

def reschedule_pending_posts():
    """Reschedule all pending posts on startup"""
    try:
        pending_posts = Post.query.filter_by(status='pending').all()
        now = datetime.now(timezone.utc)
        rescheduled = 0
        posted_immediately = 0

        for post in pending_posts:
            scheduled_time = post.scheduled_time
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)

            if scheduled_time > now:
                try:
                    scheduler.add_job(
                        func=post_to_instagram,
                        trigger="date",
                        run_date=scheduled_time.astimezone(timezone.utc),
                        args=[post.id],
                        id=f'post_{post.id}',
                        misfire_grace_time=300,
                        replace_existing=True,
                        timezone="UTC"
                    )
                    rescheduled += 1
                    logger.info(f"Rescheduled post {post.id}")
                except Exception as e:
                    logger.error(f"Failed to reschedule post {post.id}: {e}")
            else:
                # Missed post - post immediately
                logger.info(f"Posting missed post {post.id} immediately")
                scheduler.add_job(
                    func=post_to_instagram,
                    trigger="date",
                    run_date=now,
                    args=[post.id],
                    id=f'post_{post.id}',
                    replace_existing=True
                )
                posted_immediately += 1

        logger.info(f"Rescheduled {rescheduled} posts, posting {posted_immediately} missed posts")

    except Exception as e:
        logger.error(f"Error rescheduling posts on startup: {e}")

if __name__ == '__main__':
    # Ensure required environment variables are set
    required_env_vars = ['API_KEY', 'ENCRYPTION_KEY', 'SECRET_KEY', 'DEVICE_SALT']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("\nERROR: Missing required environment variables!")
        print("Please set the following in your .env file:")
        for var in missing_vars:
            if var == 'ENCRYPTION_KEY':
                print(f"\n{var}=<generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'>\n")
            elif var == 'DEVICE_SALT':
                print(f"{var}=<generate with: python -c 'import secrets; print(secrets.token_hex(32))'>")
                print("WARNING: Never change DEVICE_SALT in production - it will invalidate all sessions!\n")
            else:
                print(f"{var}=<your-secret-value>")
        exit(1)

    with app.app_context():
        try:
            db.drop_all()
            db.create_all()
            logger.info("Database initialized")
            # Debug: check tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Tables in database: {tables}")
            if 'post' in tables:
                columns = inspector.get_columns('post')
                logger.info(f"Post table columns: {[col['name'] for col in columns]}")
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise

        # Start scheduler
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started")

        # Reschedule pending posts
        reschedule_pending_posts()

    logger.info("Starting Instagram Reels Poster application")

    # For production, use gunicorn:
    # gunicorn -w 4 -b 0.0.0.0:5000 app:app
    app.run(debug=False, host='0.0.0.0', port=5000)