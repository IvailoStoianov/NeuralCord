# Character.AI Discord Bot

A Discord bot for Character.AI that brings AI characters to your Discord server.

## Features

- Chat with Character.AI characters using commands
- Enable "Social Mode" where the bot can naturally join conversations
- Support for multiple characters
- Admin controls for managing characters and settings

## Requirements

- Python 3.8 or higher
- A Character.AI account
- A Discord bot token
- Ollama server (for Social Mode)

## Setup

1. Clone this repository
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Set up environment variables in a `.env` file:
```
DISCORD_TOKEN=your_discord_bot_token
GUILD_ID=optional_guild_id_for_testing
ADMIN_ROLE_ID=optional_role_id_for_admins
OLLAMA_API_URL=http://localhost:11434/api
OLLAMA_MODEL=mistral
```
4. Run the bot:
```
python src/bot.py
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
4. A cooldown period prevents the character from responding too frequently

To use Social Mode:
1. Make sure you have a default character set with `/setcharacter`
2. Enable Social Mode with `/socialmode true`
3. Add channels to monitor with `/addchannel`
4. Optionally, adjust the cooldown with `/setcooldown`

## Ollama Setup

Social Mode requires an Ollama server running locally or remotely. To set up:

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull the desired model: `ollama pull mistral`
3. Run Ollama server
4. Set the `OLLAMA_API_URL` in your `.env` file

## Credits

Built by NeuralCord 