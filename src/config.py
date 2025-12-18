import os
from cryptography.fernet import Fernet

#--------------------------------------------------------------------------------------------------#
# Global Configurations                                                                            #
#--------------------------------------------------------------------------------------------------#

# Config Variables
CURRENT_DIR = os.getcwd() + os.sep

# SQLite DB path
DB_PATH = CURRENT_DIR + '..'+os.sep+'database' + os.sep + 'sqlite.db'

# Download Path
DOWNLOAD_DIR = CURRENT_DIR + '..'+os.sep+'downloads' + os.sep  # Path of folder where files will be stored

#IS REMOVE FILES
IS_REMOVE_FILES = 1

# Remove Posted Files Interval
REMOVE_FILE_AFTER_MINS = 120 #every two hours

# Encryption key for passwords (generate once and store securely)
ENCRYPTION_KEY = b'your-32-byte-key-here-replace-with-actual'  # TODO: Generate and secure this

cipher = Fernet(ENCRYPTION_KEY)

def encrypt_password(password):
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    return cipher.decrypt(encrypted_password.encode()).decode()

#--------------------------------------------------------------------------------------------------#
# Instagram Configurations                                                                         #
#--------------------------------------------------------------------------------------------------#

# IS RUN REELS SCRAPER (disable for our tool)
IS_ENABLED_REELS_SCRAPER = 0

# IS RUN AUTO POSTER
IS_ENABLED_AUTO_POSTER = 1

# IS POST STORY
IS_POST_TO_STORY = 0  # Disable for reels

# Fetch LIMIT for scraper script (not used)
FETCH_LIMIT = 10

# Posting interval in Minutes (not used, use scheduler)
POSTING_INTERVAL_IN_MIN = 15  # Every 15 Minutes

# Scraper interval in Minutes (not used)
SCRAPER_INTERVAL_IN_MIN = 720  # Every 12 hours

# Instagram Accounts (list of dicts with username and encrypted password)
INSTAGRAM_ACCOUNTS = [
    {"username": "account1", "password": encrypt_password("password1")},
    {"username": "account2", "password": encrypt_password("password2")},
    # Add more as needed
]

# like_and_view_counts_disabled
LIKE_AND_VIEW_COUNTS_DISABLED = 0

# disable_comments
DISABLE_COMMENTS = 0

# HASHTAGS to add while Posting (will be customized per post)
HASHTAGS = "#reels #shorts #likes #follow"

#--------------------------------------------------------------------------------------------------#
# Youtube Configurations (not used)                                                                 #
#--------------------------------------------------------------------------------------------------#

# IS RUN YOUTUBE SCRAPER
IS_ENABLED_YOUTUBE_SCRAPING = 0


# IS RUN YOUTUBE SCRAPER
YOUTUBE_SCRAPING_INTERVAL_IN_MINS = 120


# YOUTUBE API KEY
YOUTUBE_API_KEY = "YOUR_API_KEY"



# YouTube Channel List short for scraping
CHANNEL_LINKS = [
    "https://www.youtube.com/@exampleChannleName."
]


