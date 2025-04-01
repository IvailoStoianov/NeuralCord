# Character.AI Discord Bot

A Discord bot for Character.AI that brings AI characters to your Discord server.

![Version](https://img.shields.io/badge/version-0.9.0-blue)
![Status](https://img.shields.io/badge/status-beta-orange)

## Features

- Chat with Character.AI characters using commands
- Enable "Social Mode" where the bot can naturally join conversations
- Intelligent filter AI to determine when to engage in conversations
- Support for multiple characters
- Inappropriate content detection and filtering
- Admin controls for managing characters and settings
- API rate limiting to prevent abuse

## Requirements

- Python 3.8 or higher
- A Character.AI account
- A Discord bot token
- Ollama server (for Social Mode)

## Quick Start

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/characterai-discord-bot.git
   cd characterai-discord-bot
   ```

2. Install dependencies:
   ```
   pip install -r discord-bot/requirements.txt
   ```

3. Copy the example environment file:
   ```
   cp discord-bot/.env.example discord-bot/.env
   ```

4. Edit the `.env` file with your Discord token and other settings

5. Run the bot:
   ```
   cd discord-bot
   python src/bot.py
   ```

## Detailed Setup Guide

### Creating a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the "Privileged Gateway Intents" section, enable "Message Content Intent"
5. Copy your bot token and add it to your `.env` file
6. Go to OAuth2 > URL Generator, select `bot` and `applications.commands` scopes
7. Select the following bot permissions:
   - Send Messages
   - Send Messages in Threads
   - Embed Links
   - Attach Files
   - Read Message History
   - Use Slash Commands
8. Copy the generated URL and open it in your browser to add the bot to your server

### Environment Configuration

Create a `.env` file with the following variables:

```
DISCORD_TOKEN=your_discord_bot_token
GUILD_ID=optional_guild_id_for_testing
ADMIN_ROLE_ID=optional_role_id_for_admins
OLLAMA_API_URL=http://localhost:11434/api
OLLAMA_MODEL=mistral
```

### Ollama Setup

Social Mode requires an Ollama server running locally or remotely:

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull the desired model: `ollama pull mistral`
3. Run the Ollama server (it will run on port 11434 by default)
4. Set the `OLLAMA_API_URL` in your `.env` file

## Deployment Options

### Docker Deployment

A Dockerfile is provided for easy deployment:

```bash
# Build the Docker image
docker build -t characterai-discord-bot .

# Run the container
docker run -d --name characterai-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  characterai-discord-bot
```

### Systemd Service (Linux)

Create a systemd service file at `/etc/systemd/system/characterai-bot.service`:

```ini
[Unit]
Description=Character.AI Discord Bot
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/characterai-discord-bot/discord-bot
ExecStart=/usr/bin/python3 src/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:

```bash
sudo systemctl enable characterai-bot.service
sudo systemctl start characterai-bot.service
```

## Commands

### Everyone Commands
- `/chat [message]` - Talk to the default character
- `/talk [character_id] [message]` - Talk to a specific character by ID
- `/listcharacters` - List all available characters
- `/info` - Show bot information

### Admin Commands
- `/login [email]` - Start the Character.AI login process
- `/verify [link]` - Verify with the link from your email
- `/setcharacter [character_id]` - Set the default character
- `/resetchat [character_id]` - Reset the chat with a character
- `/deletechat [character_id]` - Delete a character from the bot
- `/socialmode [enabled]` - Toggle Social Mode on/off
- `/addchannel` - Add the current channel to Social Mode
- `/removechannel` - Remove the current channel from Social Mode
- `/setcooldown [seconds]` - Set Social Mode cooldown
- `/setmodel [model_name]` - Change the filter AI model

## Social Mode

Social Mode allows the character to join conversations naturally without requiring explicit commands. When enabled:

1. The bot monitors messages in channels that have been added with `/addchannel`
2. A filter AI analyzes conversations to determine when the character should respond
3. When appropriate, the character will respond naturally as part of the conversation

To use Social Mode:
1. Make sure you have a default character set with `/setcharacter`
2. Enable Social Mode with `/socialmode true`
3. Add channels to monitor with `/addchannel`
4. Optionally, adjust the cooldown with `/setcooldown`

## Finding Character IDs

To find a character's ID:
1. Go to [Character.AI](https://beta.character.ai)
2. Navigate to the character's page
3. The ID is in the URL: `https://beta.character.ai/chat?char=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`
4. Copy the ID (the part after `char=`)

## Beta Testing Guidelines

This is a beta release. Please report any issues and feedback through:
- GitHub Issues
- Discord server: [Join Here](https://discord.gg/yourdiscordserver)

### Known Limitations
- Character.AI rate limits may apply
- Some characters may not respond as expected
- Social Mode requires fine-tuning for optimal performance

## Troubleshooting

### Common Issues

**Bot doesn't respond to commands**:
- Check that the bot has proper permissions
- Ensure message content intent is enabled
- Check logs for errors

**Character.AI authentication issues**:
- Verify your Character.AI account credentials
- Check your email for verification link

**Social Mode not responding**:
- Ensure Ollama server is running
- Check if the channel is added to Social Mode
- Verify the filter AI model is available

## Credits

Built by NeuralCord 