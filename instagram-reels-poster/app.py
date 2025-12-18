from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from cryptography.fernet import Fernet
import os
from datetime import datetime
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reels_poster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)
scheduler = BackgroundScheduler()
scheduler.start()

# Encryption setup
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key().decode())
cipher = Fernet(ENCRYPTION_KEY.encode())

def encrypt_password(password):
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    return cipher.decrypt(encrypted_password.encode()).decode()

# Database Models
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)  # encrypted
    session_data = db.Column(db.Text)  # JSON string for instagrapi session
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    video_path = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.Text)
    hashtags = db.Column(db.Text)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, posted, failed
    posted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship('Account', backref=db.backref('posts', lazy=True))

class ScheduleConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interval_hours = db.Column(db.Integer, default=1)
    active = db.Column(db.Boolean, default=True)

# Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/accounts', methods=['GET', 'POST'])
def manage_accounts():
    if request.method == 'POST':
        data = request.json
        existing = Account.query.filter_by(username=data['username']).first()
        if existing:
            return jsonify({'message': 'Account with this username already exists'}), 400
        encrypted_password = encrypt_password(data['password'])
        account = Account(
            username=data['username'],
            password=encrypted_password,
            is_active=data.get('is_active', True)
        )
        db.session.add(account)
        db.session.commit()
        return jsonify({'message': 'Account added successfully', 'id': account.id}), 201

    accounts = Account.query.all()
    return jsonify([{
        'id': acc.id,
        'username': acc.username,
        'is_active': acc.is_active,
        'created_at': acc.created_at.isoformat()
    } for acc in accounts])

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    account = Account.query.get(account_id)
    if not account:
        return jsonify({'message': 'Account not found'}), 404
    # Check if account has pending posts
    pending_posts = Post.query.filter_by(account_id=account_id, status='pending').count()
    if pending_posts > 0:
        return jsonify({'message': 'Cannot delete account with pending posts'}), 400
    db.session.delete(account)
    db.session.commit()
    return jsonify({'message': 'Account deleted successfully'})

@app.route('/api/posts', methods=['GET', 'POST'])
def manage_posts():
    if request.method == 'POST':
        data = request.json
        post = Post(
            account_id=data['accountId'],
            video_path=data['videoPath'],
            caption=data.get('caption', ''),
            hashtags=data.get('hashtags', ''),
            scheduled_time=datetime.fromisoformat(data['scheduledTime'])
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
            misfire_grace_time=300  # Allow 5 minutes grace for missed jobs
        )

        return jsonify({'message': 'Post scheduled successfully', 'id': post.id}), 201

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

def post_to_instagram(post_id):
    from instagrapi import Client

    post = Post.query.get(post_id)
    if not post:
        print(f"Post {post_id} not found")
        return

    print(f"Starting post for {post_id} at {datetime.utcnow()}")
    account = post.account
    try:
        api = Client()
        api.delay_range = [1, 3]

        # Load session if exists
        if account.session_data:
            session_dict = json.loads(account.session_data)
            api.set_settings(session_dict)
            api.login(account.username, decrypt_password(account.password))
            print(f"Logged in with session for {account.username}")
        else:
            api.login(account.username, decrypt_password(account.password))
            # Save session
            account.session_data = json.dumps(api.get_settings())
            db.session.commit()
            print(f"Logged in and saved session for {account.username}")

        # Post the reel
        full_caption = f"{post.caption}\n\n{post.hashtags}".strip()
        print(f"Uploading video {post.video_path} with caption: {full_caption}")
        media = api.clip_upload(post.video_path, full_caption)

        if media:
            post.status = 'posted'
            post.posted_at = datetime.utcnow()
            print(f"Post {post_id} successful")
        else:
            post.status = 'failed'
            print(f"Post {post_id} failed: no media returned")

    except Exception as e:
        post.status = 'failed'
        print(f"Posting failed for post {post_id}: {str(e)}")

    db.session.commit()

@app.route('/api/schedule-config', methods=['GET', 'PUT'])
def schedule_config():
    config = ScheduleConfig.query.first()
    if not config:
        config = ScheduleConfig()
        db.session.add(config)
        db.session.commit()

    if request.method == 'PUT':
        data = request.json
        config.interval_hours = data.get('interval_hours', config.interval_hours)
        config.active = data.get('active', config.active)
        db.session.commit()
        return jsonify({'message': 'Configuration updated'})

    return jsonify({
        'interval_hours': config.interval_hours,
        'active': config.active
    })

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'message': 'Post not found'}), 404
    if post.status != 'pending':
        return jsonify({'message': 'Only pending posts can be deleted'}), 400
    # Remove from scheduler
    try:
        scheduler.remove_job(f'post_{post_id}')
    except:
        pass  # Job might not exist
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Post deleted successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Reschedule pending posts
        pending_posts = Post.query.filter_by(status='pending').all()
        for post in pending_posts:
            if post.scheduled_time > datetime.utcnow():
                scheduler.add_job(
                    func=post_to_instagram,
                    trigger="date",
                    run_date=post.scheduled_time,
                    args=[post.id],
                    id=f'post_{post.id}',
                    misfire_grace_time=300
                )
            else:
                # If scheduled time has passed, post immediately
                print(f"Posting missed post {post.id} immediately")
                post_to_instagram(post.id)
    app.run(debug=True)