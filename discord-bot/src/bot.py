# This example requires the 'message_content' intent.
from characterai import aiocai, sendCode, authUser
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import logging
from dotenv import load_dotenv
from filter_ai import FilterAI
from config import BOT_CONFIG, FILTER_AI_CONFIG, LOGGING_CONFIG

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["LEVEL"]),
    format=LOGGING_CONFIG["FORMAT"],
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGGING_CONFIG["BOT_LOG_FILE"])
    ]
)
logger = logging.getLogger("discord_bot")

# Load environment variables from .env file
load_dotenv()

token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')  # Optional: for guild-specific commands
admin_role_id = os.getenv('ADMIN_ROLE_ID')  # Role ID for admin commands
ollama_model = os.getenv('OLLAMA_MODEL', FILTER_AI_CONFIG["DEFAULT_MODEL"])  # Default Ollama model
ollama_api_url = os.getenv('OLLAMA_API_URL', 'http://localhost:11434/api')  # Default Ollama API URL

# Bot data storage
BOT_DATA_FILE = BOT_CONFIG["DATA_FILE"]

# Load existing bot data or create empty dict
def load_bot_data():
    try:
        with open(BOT_DATA_FILE, 'r') as f:
            data = json.load(f)
            logger.info(f"Loaded bot data from {BOT_DATA_FILE}")
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load bot data: {str(e)}. Creating new data file.")
        return {
            "is_authenticated": False,
            "email": "",
            "cai_token": "",
            "default_character": "",
            "default_character_name": "",
            "chats": {},
            "social_mode": {
                "enabled": False,
                "channels": [],
                "cooldown": BOT_CONFIG["DEFAULT_COOLDOWN"]  # Default cooldown in seconds
            }
        }

# Save bot data to file
def save_bot_data(bot_data):
    with open(BOT_DATA_FILE, 'w') as f:
        json.dump(bot_data, f)
        logger.debug("Saved bot data to file")

# Initialize bot data
bot_data = load_bot_data()

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot with both prefix and slash command support
class CharacterAIBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.synced = False
        self.filter_ai = FilterAI(model_name=ollama_model, api_url=ollama_api_url)
        self.last_response_time = {}  # Store last response time per channel
        logger.info(f"Bot initialized with Ollama model: {ollama_model}")

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            # Sync commands with Discord
            if guild_id:
                # Sync to specific guild (faster for testing)
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Command tree synced to guild ID: {guild_id}")
            else:
                # Sync globally (takes up to an hour to propagate)
                await self.tree.sync()
                logger.info("Command tree synced globally")
            self.synced = True
            
        logger.info(f'Logged in as {self.user}!')
        logger.info('------')
    
    async def on_message(self, message):
        # Ignore own messages
        if message.author == self.user:
            return
        
        # Process commands first
        await self.process_commands(message)
        
        # Check if social mode is enabled
        if not bot_data.get('social_mode', {}).get('enabled', False):
            return
        
        # Check if channel is in the allowed list
        channel_id = str(message.channel.id)
        if channel_id not in bot_data.get('social_mode', {}).get('channels', []):
            return
        
        # Check if we're authenticated and have a default character
        if not bot_data.get('is_authenticated', False) or not bot_data.get('default_character', ''):
            return
        
        # Remove cooldown check - allow the bot to respond to every message
        logger.info(f"Processing message from {message.author.display_name} in channel {channel_id}")
        
        # Get recent messages from this channel, including the bot's own messages
        context = []
        async for msg in message.channel.history(limit=15):
            # Include bot messages instead of skipping them
            author_name = msg.author.display_name
            
            # If this is a bot message, format it as the character name
            if msg.author == self.user:
                character_name = bot_data.get('default_character_name', 'AI Assistant')
                # Extract just the message content without the name prefix
                content = msg.content
                # If the message starts with "**CharacterName**:", extract just the message part
                if content.startswith(f"**{character_name}**:"):
                    content = content.split(":", 1)[1].strip()
                # Add the message with the character name
                context.append({
                    'author': character_name,
                    'content': content,
                    'id': msg.id,
                    'timestamp': msg.created_at.timestamp()
                })
                logger.debug(f"Added bot message to context: {character_name}: {content[:50]}...")
            else:
                # Regular user message
                context.append({
                    'author': author_name,
                    'content': msg.content,
                    'id': msg.id,
                    'timestamp': msg.created_at.timestamp()
                })
                logger.debug(f"Added user message to context: {author_name}: {msg.content[:50]}...")
        
        # Reverse to get correct chronological order
        context.reverse()
        
        # Get character name
        character_name = bot_data.get('default_character_name', 'AI Assistant')
        
        # Check if we should respond using the filter AI
        logger.info(f"Analyzing conversation with {len(context)} messages for character: {character_name}")
        should_respond, conversation_input = await self.filter_ai.should_respond(context, character_name)
        
        if should_respond and conversation_input:
            # We should respond - get the character AI client
            logger.info(f"Filter AI decided to respond with input: {conversation_input[:100]}...")
            try:
                token = bot_data['cai_token']
                client = aiocai.Client(token)
                character_id = bot_data['default_character']
                
                logger.info(f"Sending message to Character.AI (character ID: {character_id})")
                
                # Get existing chat or create a new one
                chat_data = bot_data.get('chats', {})
                chat_key = character_id
                
                # Send typing indicator
                async with message.channel.typing():
                    async with await client.connect() as chat:
                        if chat_key not in chat_data:
                            # Create a new chat
                            logger.info("Creating new chat with character")
                            me = await client.get_me()
                            new, answer = await chat.new_chat(character_id, me.id)
                            chat_data[chat_key] = {
                                'chat_id': new.chat_id,
                                'name': answer.name
                            }
                            save_bot_data(bot_data)
                            
                            logger.info(f"Initial response from character: {answer.text[:100]}...")
                            
                            # First, send the welcome message
                            await message.channel.send(f"**{answer.name}**: {answer.text}")
                            
                            # Then send our response to the conversation
                            logger.info(f"Sending conversation input to character: {conversation_input}")
                            message_response = await chat.send_message(character_id, new.chat_id, conversation_input)
                            logger.info(f"Character response: {message_response.text[:100]}...")
                            
                            # Post only the character's response, without any meta text
                            await message.channel.send(f"**{message_response.name}**: {message_response.text}")
                        else:
                            # Use existing chat
                            chat_id = chat_data[chat_key]['chat_id']
                            logger.info(f"Using existing chat (ID: {chat_id})")
                            logger.info(f"Sending conversation input to character: {conversation_input}")
                            message_response = await chat.send_message(character_id, chat_id, conversation_input)
                            logger.info(f"Character response: {message_response.text[:100]}...")
                            
                            # Post only the character's response, without any meta text
                            await message.channel.send(f"**{message_response.name}**: {message_response.text}")
                
                # Update the last response time (keep this for tracking purposes)
                current_time = message.created_at.timestamp()
                self.last_response_time[channel_id] = current_time
                logger.info(f"Updated last response time for channel {channel_id}")
                
            except Exception as e:
                logger.error(f"Error in social mode response: {str(e)}", exc_info=True)
                print(f"Error in social mode response: {str(e)}")

bot = CharacterAIBot()

# Check if user has admin role
def has_admin_role(interaction: discord.Interaction):
    if not admin_role_id:
        # If no admin role is configured, default to server admins
        return interaction.user.guild_permissions.administrator
    
    # Check if user has the specified admin role
    return any(role.id == int(admin_role_id) for role in interaction.user.roles)

# Admin-only login command
@bot.tree.command(name="login", description="[Admin] Start the login process")
@app_commands.describe(email="Your Character.AI account email")
async def login_slash(interaction: discord.Interaction, email: str):
    """Sends the verification code to the admin's email"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Store the email
    bot_data['email'] = email
    bot_data['is_authenticated'] = False
    save_bot_data(bot_data)
    
    logger.info(f"Admin {interaction.user.display_name} initiated login with email: {email}")
    
    await interaction.response.send_message(f"Sending verification code to {email}", ephemeral=True)
    sendCode(email)
    await interaction.followup.send(f"Please check your email for the verification link and use /verify with the link.", ephemeral=True)

# Admin-only verify command
@bot.tree.command(name="verify", description="[Admin] Verify with the link from your email")
@app_commands.describe(link="The verification link from your email")
async def verify_slash(interaction: discord.Interaction, link: str):
    """Verifies the admin's email"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Check if email is already set
    if 'email' not in bot_data or not bot_data['email']:
        await interaction.response.send_message("Please login first with /login", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        email = bot_data['email']
        logger.info(f"Admin {interaction.user.display_name} attempting to verify with email: {email}")
        
        token = authUser(link, email)
        
        # Store the token
        bot_data['cai_token'] = token
        bot_data['is_authenticated'] = True
        save_bot_data(bot_data)
        
        client = aiocai.Client(token)
        me = await client.get_me()
        logger.info(f"Successfully authenticated as Character.AI user: {me.name}")
        
        await interaction.followup.send(f"Successfully verified and logged in as {me.name}", ephemeral=True)
        await interaction.followup.send("Now anyone can chat with characters using /chat or /talk commands!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}", exc_info=True)
        await interaction.followup.send(f"Error during verification: {str(e)}", ephemeral=True)

# Admin-only set character command
@bot.tree.command(name="setcharacter", description="[Admin] Set the default character")
@app_commands.describe(character_id="The character ID from Character.AI")
async def set_character_slash(interaction: discord.Interaction, character_id: str):
    """Sets the default character to chat with"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Make sure bot is authenticated
    if not bot_data['is_authenticated']:
        await interaction.response.send_message("Bot is not authenticated. An admin needs to use /login and /verify first.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # Verify character ID is valid and get character name
    try:
        token = bot_data['cai_token']
        client = aiocai.Client(token)
        
        async with await client.connect() as chat:
            # Try to start a chat with this character to verify it exists
            me = await client.get_me()
            try:
                new, answer = await chat.new_chat(character_id, me.id)
                character_name = answer.name
                
                # Store the default character ID
                bot_data['default_character'] = character_id
                bot_data['default_character_name'] = character_name
                
                # Initialize chats if needed
                if 'chats' not in bot_data:
                    bot_data['chats'] = {}
                
                # Store the chat ID for future use
                chat_data = bot_data['chats']
                chat_key = character_id
                chat_data[chat_key] = {
                    'chat_id': new.chat_id,
                    'name': character_name  # Store the character name
                }
                
                save_bot_data(bot_data)
                
                await interaction.followup.send(f"Default character set to: **{character_name}** (ID: {character_id})")
                await interaction.followup.send("Anyone can now use /chat to talk to this character without specifying the ID.")
                await interaction.followup.send(f"**{answer.name}**: {answer.text}")
            except Exception as e:
                await interaction.followup.send(f"Error: Invalid character ID or couldn't connect to character. Please check the ID and try again.")
                await interaction.followup.send(f"Details: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f"Error validating character: {str(e)}")

# Chat command (available to everyone)
@bot.tree.command(name="chat", description="Chat with the default character")
@app_commands.describe(message="Your message to the character")
async def chat_slash(interaction: discord.Interaction, message: str):
    """Chat with the default character"""
    # Make sure bot is authenticated
    if not bot_data['is_authenticated']:
        await interaction.response.send_message("Bot is not authenticated. An admin needs to use /login and /verify first.", ephemeral=True)
        return
    
    # Check if default character is set
    if 'default_character' not in bot_data or not bot_data['default_character']:
        await interaction.response.send_message("No default character set. An admin needs to use /setcharacter first.", ephemeral=True)
        return
    
    character_id = bot_data['default_character']
    character_name = bot_data.get('default_character_name', 'Character')
    
    await interaction.response.defer()
    
    try:
        token = bot_data['cai_token']
        client = aiocai.Client(token)
        
        # Make sure chats dict exists
        if 'chats' not in bot_data:
            bot_data['chats'] = {}
        
        # Create or get existing chat
        chat_data = bot_data['chats']
        chat_key = character_id
        
        # Format the message as a natural conversation
        formatted_message = f"{interaction.user.display_name}: {message}"
        logger.info(f"Chat command: {formatted_message}")
        
        await interaction.followup.send(f"**{interaction.user.display_name}**: {message}")
        await interaction.followup.send(f"*{character_name} is typing...*")
        
        async with await client.connect() as chat:
            if chat_key not in chat_data:
                # Create a new chat
                me = await client.get_me()
                new, answer = await chat.new_chat(character_id, me.id)
                chat_data[chat_key] = {
                    'chat_id': new.chat_id,
                    'name': answer.name  # Store the character name
                }
                save_bot_data(bot_data)
                await interaction.followup.send(f"**{answer.name}**: {answer.text}")
            else:
                # Use existing chat
                chat_id = chat_data[chat_key]['chat_id']
                message_response = await chat.send_message(character_id, chat_id, formatted_message)
                
                # Update name if it doesn't exist or has changed
                if 'name' not in chat_data[chat_key] or chat_data[chat_key]['name'] != message_response.name:
                    chat_data[chat_key]['name'] = message_response.name
                    save_bot_data(bot_data)
                
                await interaction.followup.send(f"**{message_response.name}**: {message_response.text}")
    except Exception as e:
        logger.error(f"Error in chat command: {str(e)}", exc_info=True)
        await interaction.followup.send(f"Error talking to character: {str(e)}")

# Talk command (available to everyone)
@bot.tree.command(name="talk", description="Talk to a specific character by ID")
@app_commands.describe(
    character_id="The character ID from Character.AI",
    message="Your message to the character"
)
async def talk_slash(interaction: discord.Interaction, character_id: str, message: str):
    """Talk to a Character.AI character"""
    # Make sure bot is authenticated
    if not bot_data['is_authenticated']:
        await interaction.response.send_message("Bot is not authenticated. An admin needs to use /login and /verify first.", ephemeral=True)
        return
    
    await interaction.response.defer()
    try:
        token = bot_data['cai_token']
        client = aiocai.Client(token)
        
        # Make sure chats dict exists
        if 'chats' not in bot_data:
            bot_data['chats'] = {}
        
        # Create or get existing chat
        chat_data = bot_data['chats']
        chat_key = character_id
        
        # Format the message as a natural conversation
        formatted_message = f"{interaction.user.display_name}: {message}"
        logger.info(f"Talk command: {formatted_message}")
        
        await interaction.followup.send(f"**{interaction.user.display_name}**: {message}")
        await interaction.followup.send("*Character is typing...*")
        
        async with await client.connect() as chat:
            if chat_key not in chat_data:
                # Create a new chat
                me = await client.get_me()
                new, answer = await chat.new_chat(character_id, me.id)
                chat_data[chat_key] = {
                    'chat_id': new.chat_id,
                    'name': answer.name  # Store the character name
                }
                save_bot_data(bot_data)
                await interaction.followup.send(f"**{answer.name}**: {answer.text}")
            else:
                # Use existing chat
                chat_id = chat_data[chat_key]['chat_id']
                message_response = await chat.send_message(character_id, chat_id, formatted_message)
                
                # Update name if it doesn't exist or has changed
                if 'name' not in chat_data[chat_key] or chat_data[chat_key]['name'] != message_response.name:
                    chat_data[chat_key]['name'] = message_response.name
                    save_bot_data(bot_data)
                
                await interaction.followup.send(f"**{message_response.name}**: {message_response.text}")
    except Exception as e:
        logger.error(f"Error in talk command: {str(e)}", exc_info=True)
        await interaction.followup.send(f"Error talking to character: {str(e)}")

# List characters command (available to everyone)
@bot.tree.command(name="listcharacters", description="List all available characters")
async def list_characters_slash(interaction: discord.Interaction):
    """Lists all characters the bot has interacted with"""
    # Make sure bot is authenticated
    if not bot_data['is_authenticated']:
        await interaction.response.send_message("Bot is not authenticated. An admin needs to use /login and /verify first.", ephemeral=True)
        return
    
    # Check if any chats exist
    if 'chats' not in bot_data or not bot_data['chats']:
        await interaction.response.send_message("No characters available yet. Use /talk to start a conversation with a character.", ephemeral=True)
        return
    
    # Create embed with character list
    embed = discord.Embed(
        title="Available Characters",
        description="Characters that anyone can talk to",
        color=discord.Color.green()
    )
    
    # Get default character if set
    default_char_id = bot_data.get('default_character', None)
    default_char_name = bot_data.get('default_character_name', 'Unknown')
    
    if default_char_id:
        embed.add_field(
            name="Default Character",
            value=f"**{default_char_name}** (ID: `{default_char_id}`)\nUse /chat to talk to this character",
            inline=False
        )
    
    # Add all characters from chat history
    chats = bot_data['chats']
    
    # Sort characters by character ID
    character_list = []
    for char_id in chats:
        # Try to get name from chat data if available
        char_name = "Unknown"
        if 'name' in chats[char_id]:
            char_name = chats[char_id]['name']
        elif char_id == default_char_id:
            # Use default character name if this is the default character
            char_name = default_char_name
        
        # Mark default character
        is_default = char_id == default_char_id
        character_list.append((char_id, char_name, is_default))
    
    # Add characters to embed
    if character_list:
        other_chars = "\n".join([
            f"• **{name}** (ID: `{id}`)" for id, name, is_default in character_list if not is_default
        ])
        
        if other_chars:
            embed.add_field(
                name="Other Characters",
                value=f"{other_chars}\nUse /talk with the character ID to talk to these characters",
                inline=False
            )
        else:
            embed.add_field(
                name="Other Characters",
                value="No other characters available yet.",
                inline=False
            )
    
    embed.set_footer(text="Admins can use /setcharacter to change the default character")
    await interaction.response.send_message(embed=embed)

# Admin-only reset chat command
@bot.tree.command(name="resetchat", description="[Admin] Reset the chat with a character")
@app_commands.describe(character_id="The character ID to reset chat for")
async def reset_chat_slash(interaction: discord.Interaction, character_id: str):
    """Reset the chat with a specific character"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Make sure bot is authenticated
    if not bot_data['is_authenticated']:
        await interaction.response.send_message("Bot is not authenticated. An admin needs to use /login and /verify first.", ephemeral=True)
        return
    
    # Check if any chats exist
    if 'chats' not in bot_data or not bot_data['chats']:
        await interaction.response.send_message("No chats to reset.", ephemeral=True)
        return
    
    # Check if character exists in chats
    chat_data = bot_data['chats']
    if character_id not in chat_data:
        await interaction.response.send_message(f"No chat found with character ID: `{character_id}`\nUse /listcharacters to see available characters.", ephemeral=True)
        return
    
    # Get character name before deletion
    character_name = chat_data[character_id].get('name', 'Unknown Character')
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        token = bot_data['cai_token']
        client = aiocai.Client(token)
        
        # Create a new chat with the character
        me = await client.get_me()
        
        async with await client.connect() as chat:
            new, answer = await chat.new_chat(character_id, me.id)
            chat_data[character_id] = {
                'chat_id': new.chat_id,
                'name': answer.name
            }
            save_bot_data(bot_data)
            
            await interaction.followup.send(f"Reset chat with **{character_name}** (ID: `{character_id}`)")
            await interaction.followup.send(f"First message from character: **{answer.name}**: {answer.text}")
    except Exception as e:
        await interaction.followup.send(f"Error resetting chat: {str(e)}")

# Admin-only delete chat command
@bot.tree.command(name="deletechat", description="[Admin] Delete a character from the bot")
@app_commands.describe(character_id="The character ID to delete")
async def delete_chat_slash(interaction: discord.Interaction, character_id: str):
    """Delete a character chat completely"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Make sure bot is authenticated
    if not bot_data['is_authenticated']:
        await interaction.response.send_message("Bot is not authenticated. An admin needs to use /login and /verify first.", ephemeral=True)
        return
    
    # Check if any chats exist
    if 'chats' not in bot_data or not bot_data['chats']:
        await interaction.response.send_message("No chats to delete.", ephemeral=True)
        return
    
    # Check if character exists in chats
    chat_data = bot_data['chats']
    if character_id not in chat_data:
        await interaction.response.send_message(f"No chat found with character ID: `{character_id}`\nUse /listcharacters to see available characters.", ephemeral=True)
        return
    
    # Get character name before deletion
    character_name = chat_data[character_id].get('name', 'Unknown Character')
    
    # Check if this is the default character
    is_default = bot_data.get('default_character') == character_id
    
    # Delete the chat
    del chat_data[character_id]
    
    # If it was the default character, remove the default character setting
    if is_default:
        bot_data.pop('default_character', None)
        bot_data.pop('default_character_name', None)
        await interaction.response.send_message(f"Deleted chat with **{character_name}** (ID: `{character_id}`)\nNote: This was the default character. You'll need to set a new default with /setcharacter.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Deleted chat with **{character_name}** (ID: `{character_id}`)", ephemeral=True)
    
    # Save the updated bot data
    save_bot_data(bot_data)

# Info command (available to everyone)
@bot.tree.command(name="info", description="Show information about the bot")
async def info_slash(interaction: discord.Interaction):
    """Shows info about the bot"""
    embed = discord.Embed(
        title="Bot Info",
        description="A Discord bot for Character.AI",
        color=discord.Color.blue()
    )
    
    # Status section
    status = "✅ Ready" if bot_data.get('is_authenticated', False) else "❌ Not authenticated"
    default_char = f"**{bot_data.get('default_character_name', 'None')}**" if bot_data.get('default_character', '') else "None"
    social_mode = "✅ Enabled" if bot_data.get('social_mode', {}).get('enabled', False) else "❌ Disabled"
    
    embed.add_field(
        name="Status", 
        value=f"Authentication: {status}\nDefault Character: {default_char}\nSocial Mode: {social_mode}", 
        inline=False
    )
    
    # User commands
    embed.add_field(
        name="Everyone Commands", 
        value="/chat - Talk to the default character\n"
              "/talk - Talk to a specific character by ID\n"
              "/listcharacters - Show all available characters\n"
              "/info - Show this help message", 
        inline=False
    )
    
    # Admin commands
    embed.add_field(
        name="Admin Commands", 
        value="/login - Start the login process\n"
              "/verify - Verify with email link\n"
              "/setcharacter - Set the default character\n"
              "/resetchat - Reset chat history with a character\n"
              "/deletechat - Delete a character completely\n"
              "/socialmode - Toggle Social Mode\n"
              "/addchannel - Add a channel to Social Mode\n"
              "/removechannel - Remove a channel from Social Mode\n"
              "/setcooldown - Set Social Mode cooldown\n"
              "/setmodel - Change the filter AI model", 
        inline=False
    )
    
    embed.set_footer(text="Created by NeuralCord")
    await interaction.response.send_message(embed=embed)

# Admin-only social mode toggle command
@bot.tree.command(name="socialmode", description="[Admin] Toggle Social Mode")
@app_commands.describe(enabled="Enable or disable Social Mode")
async def social_mode_slash(interaction: discord.Interaction, enabled: bool):
    """Enable or disable Social Mode"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Make sure bot is authenticated
    if not bot_data['is_authenticated']:
        await interaction.response.send_message("Bot is not authenticated. An admin needs to use /login and /verify first.", ephemeral=True)
        return
    
    # Check if default character is set
    if 'default_character' not in bot_data or not bot_data['default_character']:
        await interaction.response.send_message("No default character set. An admin needs to use /setcharacter first.", ephemeral=True)
        return
    
    # Initialize social mode if it doesn't exist
    if 'social_mode' not in bot_data:
        bot_data['social_mode'] = {
            'enabled': False,
            'channels': [],
            'cooldown': BOT_CONFIG["DEFAULT_COOLDOWN"]
        }
    
    # Update social mode
    bot_data['social_mode']['enabled'] = enabled
    save_bot_data(bot_data)
    
    status = "enabled" if enabled else "disabled"
    logger.info(f"Admin {interaction.user.display_name} {status} Social Mode")
    
    await interaction.response.send_message(f"Social Mode has been {status}.", ephemeral=True)
    
    if enabled:
        if not bot_data['social_mode']['channels']:
            await interaction.followup.send("No channels are currently being monitored. Use /addchannel to add channels for Social Mode.", ephemeral=True)
        else:
            num_channels = len(bot_data['social_mode']['channels'])
            await interaction.followup.send(f"Social Mode is now active in {num_channels} channel(s).", ephemeral=True)
            logger.info(f"Social Mode activated in {num_channels} channels")

# Admin-only add channel command
@bot.tree.command(name="addchannel", description="[Admin] Add a channel to Social Mode")
async def add_channel_slash(interaction: discord.Interaction):
    """Add the current channel to Social Mode"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Initialize social mode if it doesn't exist
    if 'social_mode' not in bot_data:
        bot_data['social_mode'] = {
            'enabled': False,
            'channels': [],
            'cooldown': BOT_CONFIG["DEFAULT_COOLDOWN"]
        }
    
    # Get the current channel ID
    channel_id = str(interaction.channel_id)
    
    # Check if channel is already in the list
    if channel_id in bot_data['social_mode']['channels']:
        await interaction.response.send_message("This channel is already in Social Mode.", ephemeral=True)
        return
    
    # Add the channel to the list
    bot_data['social_mode']['channels'].append(channel_id)
    save_bot_data(bot_data)
    
    await interaction.response.send_message(f"Added <#{channel_id}> to Social Mode.", ephemeral=True)
    
    # If social mode is enabled, mention that the bot will be active here
    if bot_data['social_mode']['enabled']:
        await interaction.followup.send("Social Mode is currently active. The character will now join conversations in this channel.", ephemeral=True)
    else:
        await interaction.followup.send("Note: Social Mode is currently disabled. Use /socialmode to enable it.", ephemeral=True)

# Admin-only remove channel command
@bot.tree.command(name="removechannel", description="[Admin] Remove a channel from Social Mode")
async def remove_channel_slash(interaction: discord.Interaction):
    """Remove the current channel from Social Mode"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Initialize social mode if it doesn't exist
    if 'social_mode' not in bot_data:
        bot_data['social_mode'] = {
            'enabled': False,
            'channels': [],
            'cooldown': BOT_CONFIG["DEFAULT_COOLDOWN"]
        }
    
    # Get the current channel ID
    channel_id = str(interaction.channel_id)
    
    # Check if channel is in the list
    if channel_id not in bot_data['social_mode']['channels']:
        await interaction.response.send_message("This channel is not in Social Mode.", ephemeral=True)
        return
    
    # Remove the channel from the list
    bot_data['social_mode']['channels'].remove(channel_id)
    save_bot_data(bot_data)
    
    await interaction.response.send_message(f"Removed <#{channel_id}> from Social Mode.", ephemeral=True)

# Admin-only set cooldown command
@bot.tree.command(name="setcooldown", description="[Admin] Set Social Mode cooldown in seconds")
@app_commands.describe(seconds="Cooldown time in seconds (minimum 10)")
async def set_cooldown_slash(interaction: discord.Interaction, seconds: int):
    """Set the cooldown period for Social Mode responses"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Validate cooldown value
    if seconds < BOT_CONFIG["MIN_COOLDOWN"]:
        await interaction.response.send_message(f"Cooldown must be at least {BOT_CONFIG['MIN_COOLDOWN']} seconds.", ephemeral=True)
        return
    
    # Initialize social mode if it doesn't exist
    if 'social_mode' not in bot_data:
        bot_data['social_mode'] = {
            'enabled': False,
            'channels': [],
            'cooldown': BOT_CONFIG["DEFAULT_COOLDOWN"]
        }
    
    # Update cooldown
    bot_data['social_mode']['cooldown'] = seconds
    save_bot_data(bot_data)
    
    await interaction.response.send_message(f"Social Mode cooldown set to {seconds} seconds.", ephemeral=True)

# Admin-only set model command
@bot.tree.command(name="setmodel", description="[Admin] Change the filter AI model")
@app_commands.describe(model_name="The name of the Ollama model to use")
async def set_model_slash(interaction: discord.Interaction, model_name: str):
    """Change the filter AI model"""
    # Check if user has admin permissions
    if not has_admin_role(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    logger.info(f"Admin {interaction.user.display_name} attempting to change model to: {model_name}")
    
    # Attempt to change the model
    success = await bot.filter_ai.change_model(model_name)
    
    if success:
        logger.info(f"Successfully changed filter AI model to: {model_name}")
        await interaction.followup.send(f"Filter AI model changed to: {model_name}", ephemeral=True)
    else:
        logger.warning(f"Failed to change filter AI model to: {model_name}")
        await interaction.followup.send(f"Failed to change filter AI model. Please check if '{model_name}' is available on your Ollama server.", ephemeral=True)

# Keep old prefix commands for backward compatibility
@bot.command()
async def info(ctx):
    await ctx.send("This bot now uses slash (/) commands instead of prefix (!) commands.\nType / to see available commands.")

# Run the bot
bot.run(token)
