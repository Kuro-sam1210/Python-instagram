#!/usr/bin/env python3
"""
Session Generator for Instagram Accounts
Run this script to authenticate Instagram accounts and generate session files
"""
import os
import sys
import json
from datetime import datetime, timezone
from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    LoginRequired,
    ChallengeRequired,
    TwoFactorRequired,
    PleaseWaitFewMinutes
)
import hashlib
import uuid
from dotenv import load_dotenv
load_dotenv()

def generate_device_config(username):
    """Generate deterministic device config for account"""
    # Use DEVICE_SALT (not ENCRYPTION_KEY) for device consistency
    device_salt = os.environ.get('DEVICE_SALT', 'default-salt')
    seed = hashlib.sha256(f"device_{username}_{device_salt}".encode()).hexdigest()
   
    def seeded_uuid(prefix):
        return str(uuid.UUID(hashlib.md5(f"{seed}_{prefix}".encode()).hexdigest()))
   
    devices = [
        ("Samsung", "SM-G991B", "o1s", "exynos2100"),
        ("Google", "Pixel 6", "oriole", "tensor"),
        ("OnePlus", "9 Pro", "lemonadep", "snapdragon888"),
        ("Xiaomi", "Mi 11", "venus", "snapdragon888"),
    ]
   
    # Select device based on username hash
    device_index = int(hashlib.md5(username.encode()).hexdigest(), 16) % len(devices)
    device_info = devices[device_index]
   
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

def handle_2fa(api):
    """Handle two-factor authentication"""
    print("\n🔐 Two-factor authentication required")
    code = input("Enter the 2FA code from your authentication app: ").strip()
   
    try:
        api.two_factor_login(code)
        return True
    except Exception as e:
        print(f"❌ 2FA failed: {e}")
        return False

def handle_challenge(api):
    """Handle challenge (email/SMS verification)"""
    print("\n⚠️ Challenge required by Instagram")
    print("Instagram needs to verify your identity.")
   
    try:
        # Try to get challenge choice
        challenge_info = api.challenge_code_handler(api.last_json)
        print(f"Challenge info: {challenge_info}")
       
        choice = input("Choose verification method (0=email, 1=SMS): ").strip()
        api.challenge_choice(choice)
       
        code = input("Enter the verification code you received: ").strip()
        api.challenge_submit(code)
       
        return True
    except Exception as e:
        print(f"❌ Challenge failed: {e}")
        print("\nTips:")
        print("- Check your email/SMS for the verification code")
        print("- Try logging in from the Instagram app first")
        print("- Wait a few hours and try again")
        return False

def create_session(username, password):
    """Create and save Instagram session"""
    session_file = f"session_{username}.json"
   
    # Check if session already exists
    if os.path.exists(session_file):
        overwrite = input(f"\n⚠️ Session file already exists for {username}. Overwrite? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("❌ Cancelled")
            return False
   
    print(f"\n🔄 Creating session for: {username}")
   
    # Initialize client with realistic settings
    api = Client()
    api.delay_range = [2, 5]
   
    # Set device configuration
    device_config = generate_device_config(username)
    api.set_device(device_config)
    api.set_uuids(device_config['uuids'])
   
    try:
        print("📱 Logging in...")
        api.login(username=username, password=password)
       
        # Verify login
        user_info = api.account_info()
        print(f"✅ Login successful! Logged in as: {user_info.username}")
       
        # Save session
        api.dump_settings(session_file)
        print(f"💾 Session saved to: {session_file}")
       
        # Display account info
        print(f"\n📊 Account Info:")
        print(f" Username: {user_info.username}")
        print(f" Full Name: {user_info.full_name}")
        print(f" Followers: {user_info.follower_count}")
        print(f" Following: {user_info.following_count}")
        print(f" Posts: {user_info.media_count}")
       
        return True
       
    except TwoFactorRequired:
        if handle_2fa(api):
            api.dump_settings(session_file)
            print(f"✅ Session saved with 2FA: {session_file}")
            return True
        return False
       
    except ChallengeRequired:
        if handle_challenge(api):
            api.dump_settings(session_file)
            print(f"✅ Session saved after challenge: {session_file}")
            return True
        return False
       
    except BadPassword:
        print("❌ Invalid password")
        return False
       
    except PleaseWaitFewMinutes:
        print("⏳ Instagram rate limit hit. Please wait 5-10 minutes and try again.")
        return False
       
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("\nPossible reasons:")
        print("- Incorrect username or password")
        print("- Account has security restrictions")
        print("- Too many login attempts (wait and try again)")
        print("- Instagram detected automation (try from official app first)")
        return False

def verify_session(username):
    """Verify existing session is still valid"""
    session_file = f"session_{username}.json"
   
    if not os.path.exists(session_file):
        print(f"❌ Session file not found: {session_file}")
        return False
   
    print(f"🔍 Verifying session for: {username}")
   
    api = Client()
    api.delay_range = [2, 5]
   
    # Set device configuration
    device_config = generate_device_config(username)
    api.set_device(device_config)
    api.set_uuids(device_config['uuids'])
   
    try:
        api.load_settings(session_file)
       
        # Test session
        user_info = api.account_info()
        timeline = api.get_timeline_feed()
       
        print(f"✅ Session is valid!")
        print(f" Logged in as: {user_info.username}")
        print(f" Full Name: {user_info.full_name}")
        return True
       
    except LoginRequired:
        print("❌ Session expired. Please create a new session.")
        return False
       
    except Exception as e:
        print(f"❌ Session verification failed: {e}")
        return False

def list_sessions():
    """List all existing session files"""
    session_files = [f for f in os.listdir('.') if f.startswith('session_') and f.endswith('.json')]
   
    if not session_files:
        print("No session files found.")
        return
   
    print(f"\n📁 Found {len(session_files)} session file(s):")
    for i, session_file in enumerate(session_files, 1):
        username = session_file.replace('session_', '').replace('.json', '')
       
        # Try to get session info
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
                created = datetime.fromtimestamp(os.path.getctime(session_file))
                print(f" {i}. {username} (created: {created.strftime('%Y-%m-%d %H:%M')})")
        except:
            print(f" {i}. {username} (invalid file)")

def main():
    print("=" * 60)
    print("Instagram Session Generator")
    print("=" * 60)
   
    # Check for required environment variables
    if not os.environ.get('DEVICE_SALT'):
        print("\n⚠️ WARNING: DEVICE_SALT not set in environment")
        print("Set this in your .env file to ensure consistent device fingerprinting")
        print("This should NEVER be changed once set in production!")
        print()
   
    while True:
        print("\nOptions:")
        print("1. Create new session")
        print("2. Verify existing session")
        print("3. List all sessions")
        print("4. Exit")
       
        choice = input("\nEnter your choice (1-4): ").strip()
       
        if choice == '1':
            print("\n" + "=" * 60)
            username = input("Instagram username: ").strip()
            password = input("Instagram password: ").strip()
           
            if not username or not password:
                print("❌ Username and password are required")
                continue
           
            create_session(username, password)
           
        elif choice == '2':
            print("\n" + "=" * 60)
            username = input("Instagram username to verify: ").strip()
           
            if not username:
                print("❌ Username is required")
                continue
           
            verify_session(username)
           
        elif choice == '3':
            list_sessions()
           
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
           
        else:
            print("❌ Invalid choice")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)