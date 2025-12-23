import sqlite3

conn = sqlite3.connect('reels_poster.db')
c = conn.cursor()

# Create the post table with correct columns
c.execute('''CREATE TABLE IF NOT EXISTS post (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    video_filename VARCHAR(500) NOT NULL,
    caption TEXT,
    hashtags TEXT,
    scheduled_time DATETIME NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    posted_at DATETIME,
    error_message TEXT,
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES account (id) ON DELETE CASCADE
)''')

# Create account table
c.execute('''CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    last_post_time DATETIME,
    created_at DATETIME
)''')

# Create schedule_config table
c.execute('''CREATE TABLE IF NOT EXISTS schedule_config (
    id INTEGER PRIMARY KEY,
    interval_hours INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT 1
)''')

conn.commit()
conn.close()
print("Tables created")