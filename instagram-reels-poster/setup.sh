#!/bin/bash

# Instagram Reels Poster - Setup Script
# This script automates the initial setup process

set -e

echo "======================================"
echo "Instagram Reels Poster Setup"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.9+ is required (found $python_version)"
    exit 1
fi
echo "✅ Python $python_version found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ Pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists"
    read -p "Do you want to regenerate it? (y/N): " regenerate
    if [ "$regenerate" != "y" ] && [ "$regenerate" != "Y" ]; then
        echo "Keeping existing .env file"
    else
        cp .env.example .env
        echo "✅ .env file regenerated from template"
    fi
else
    cp .env.example .env
    echo "✅ .env file created from template"
fi
echo ""

# Generate keys
echo "Generating security keys..."
echo ""

# Generate API key
api_key=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
echo "Generated API_KEY: $api_key"

# Generate encryption key
encryption_key=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
echo "Generated ENCRYPTION_KEY: $encryption_key"

# Generate secret key
secret_key=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
echo "Generated SECRET_KEY: $secret_key"

# Generate device salt
device_salt=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
echo "Generated DEVICE_SALT: $device_salt"

echo ""
read -p "Do you want to automatically update .env with these keys? (Y/n): " update_env

if [ "$update_env" != "n" ] && [ "$update_env" != "N" ]; then
    # Update .env file
    sed -i.bak "s/API_KEY=.*/API_KEY=$api_key/" .env
    sed -i.bak "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$encryption_key/" .env
    sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$secret_key/" .env
    sed -i.bak "s/DEVICE_SALT=.*/DEVICE_SALT=$device_salt/" .env
    rm .env.bak 2>/dev/null || true
    echo "✅ .env file updated with generated keys"
else
    echo ""
    echo "⚠️  Please manually update your .env file with these keys:"
    echo "   API_KEY=$api_key"
    echo "   ENCRYPTION_KEY=$encryption_key"
    echo "   SECRET_KEY=$secret_key"
    echo "   DEVICE_SALT=$device_salt"
fi
echo ""

# Create uploads directory
echo "Creating uploads directory..."
mkdir -p uploads
chmod 750 uploads
echo "✅ Uploads directory created"
echo ""

# Check for ffmpeg (optional)
if command -v ffmpeg &> /dev/null; then
    echo "✅ ffmpeg found (video validation will work)"
else
    echo "⚠️  ffmpeg not found (video validation will be limited)"
    echo "   Install with: sudo apt-get install ffmpeg (Ubuntu/Debian)"
    echo "   or: brew install ffmpeg (macOS)"
fi
echo ""

# Initialize database
echo "Initializing database..."
python3 << EOF
from app import app, db
with app.app_context():
    db.create_all()
    print("✅ Database initialized")
EOF
echo ""

# Create session files info
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Review and update .env file if needed:"
echo "   nano .env"
echo ""
echo "2. Create Instagram sessions:"
echo "   python create_session.py"
echo ""
echo "3. Start the application:"
echo "   python app.py"
echo ""
echo "   OR for production:"
echo "   gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app"
echo ""
echo "4. Test the health endpoint:"
echo "   curl http://localhost:5000/health"
echo ""
echo "5. Access the dashboard:"
echo "   http://localhost:5000"
echo ""
echo "For production deployment, see DEPLOYMENT.md"
echo ""

# Offer to create a session now
read -p "Would you like to create an Instagram session now? (y/N): " create_session

if [ "$create_session" = "y" ] || [ "$create_session" = "Y" ]; then
    echo ""
    python3 create_session.py
fi

echo ""
echo "🎉 Setup complete! Happy posting!"