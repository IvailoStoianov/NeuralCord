#!/bin/bash

# Character.AI Discord Bot Installer
# This script installs and configures the Character.AI Discord Bot

set -e

echo "====================================="
echo "Character.AI Discord Bot Installer"
echo "====================================="

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (use sudo)"
  exit 1
fi

# Default installation directory
INSTALL_DIR="/opt/characterai-discord-bot"
CONFIG_DIR="$INSTALL_DIR/discord-bot"
SERVICE_NAME="characterai-bot"

echo "This script will install the Character.AI Discord Bot to $INSTALL_DIR"
echo

# Create installation directory
echo "Creating installation directory..."
mkdir -p $INSTALL_DIR
mkdir -p $CONFIG_DIR/data

# Clone repository
echo "Cloning repository..."
if [ -d "$INSTALL_DIR/.git" ]; then
  cd $INSTALL_DIR
  git pull
else
  git clone https://github.com/yourusername/characterai-discord-bot.git $INSTALL_DIR
fi

# Install dependencies
echo "Installing dependencies..."
apt-get update
apt-get install -y python3 python3-pip

# Install Python requirements
echo "Installing Python packages..."
pip3 install -r $CONFIG_DIR/requirements.txt

# Set up environment file
if [ ! -f "$CONFIG_DIR/.env" ]; then
  echo "Setting up environment file..."
  cp $CONFIG_DIR/.env.example $CONFIG_DIR/.env
  echo
  echo "Please edit $CONFIG_DIR/.env with your Discord token and other settings"
fi

# Install systemd service
echo "Installing systemd service..."
cp $CONFIG_DIR/deploy/characterai-bot.service /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Edit $CONFIG_DIR/.env with your Discord token and settings"
echo "2. Start the bot with: sudo systemctl start $SERVICE_NAME"
echo "3. Enable the bot to start on boot: sudo systemctl enable $SERVICE_NAME"
echo
echo "Commands:"
echo "- Check status: sudo systemctl status $SERVICE_NAME"
echo "- View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "- Restart: sudo systemctl restart $SERVICE_NAME"
echo
echo "Thank you for installing the Character.AI Discord Bot!" 