# This example requires the 'message_content' intent.
from characterai import aiocai, sendCode, authUser
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')  # Optional: for guild-specific commands

# User data storage
USER_DATA_FILE = "user_data.json"

# Load existing user data or create empty dict
def load_user_data():
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save user data to file
def save_user_data(user_data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f)

# Initialize user data
user_data = load_user_data()

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot with both prefix and slash command support
class CharacterAIBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.synced = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            # Sync commands with Discord
            if guild_id:
                # Sync to specific guild (faster for testing)
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            else:
                # Sync globally (takes up to an hour to propagate)
                await self.tree.sync()
            self.synced = True
            
        print(f'Logged in as {self.user}!')
        print('------')

bot = CharacterAIBot()

# Login command
@bot.tree.command(name="login", description="Start the login process")
@app_commands.describe(email="Your Character.AI account email")
async def login_slash(interaction: discord.Interaction, email: str):
    """Sends the verification code to the user's email"""
    user_id = str(interaction.user.id)
    
    # Store the email for this specific user
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['email'] = email
    save_user_data(user_data)
    
    await interaction.response.send_message(f"Sending verification code to {email}", ephemeral=True)
    sendCode(email)
    await interaction.followup.send(f"Please check your email for the verification link.", ephemeral=True)

# Verify command
@bot.tree.command(name="verify", description="Verify with the link from your email")
@app_commands.describe(link="The verification link from your email")
async def verify_slash(interaction: discord.Interaction, link: str):
    """Verifies the user's email"""
    user_id = str(interaction.user.id)
    
    # Check if user has logged in
    if user_id not in user_data or 'email' not in user_data[user_id]:
        await interaction.response.send_message("Please login first with /login", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        email = user_data[user_id]['email']
        token = authUser(link, email)
        
        # Store the token for this user
        user_data[user_id]['token'] = token
        save_user_data(user_data)
        
        client = aiocai.Client(token)
        me = await client.get_me()
        await interaction.followup.send(f"Successfully verified and logged in as {me.name}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error during verification: {str(e)}", ephemeral=True)

# Set character command
@bot.tree.command(name="setcharacter", description="Set your default character")
@app_commands.describe(character_id="The character ID from Character.AI")
async def set_character_slash(interaction: discord.Interaction, character_id: str):
    """Sets the default character to chat with"""
    user_id = str(interaction.user.id)
    
    # Make sure user is authenticated
    if user_id not in user_data or 'token' not in user_data[user_id]:
        await interaction.response.send_message("You need to login and verify first. Use /login and then /verify", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # Verify character ID is valid and get character name
    try:
        token = user_data[user_id]['token']
        client = aiocai.Client(token)
        
        async with await client.connect() as chat:
            # Try to start a chat with this character to verify it exists
            me = await client.get_me()
            try:
                new, answer = await chat.new_chat(character_id, me.id)
                character_name = answer.name
                
                # Store the default character ID
                if user_id not in user_data:
                    user_data[user_id] = {}
                
                user_data[user_id]['default_character'] = character_id
                user_data[user_id]['default_character_name'] = character_name
                
                # If we have chats but not for this character, initialize it
                if 'chats' not in user_data[user_id]:
                    user_data[user_id]['chats'] = {}
                
                # Store the chat ID for future use
                chat_data = user_data[user_id]['chats']
                chat_key = character_id
                chat_data[chat_key] = {
                    'chat_id': new.chat_id,
                    'name': character_name  # Store the character name
                }
                
                save_user_data(user_data)
                
                await interaction.followup.send(f"Default character set to: **{character_name}** (ID: {character_id})")
                await interaction.followup.send("You can now use /chat to talk to this character without specifying the ID each time.")
                await interaction.followup.send(f"**{answer.name}**: {answer.text}")
            except Exception as e:
                await interaction.followup.send(f"Error: Invalid character ID or couldn't connect to character. Please check the ID and try again.")
                await interaction.followup.send(f"Details: {str(e)}")
    except Exception as e:
        await interaction.followup.send(f"Error validating character: {str(e)}")

# Chat command
@bot.tree.command(name="chat", description="Chat with your default character")
@app_commands.describe(message="Your message to the character")
async def chat_slash(interaction: discord.Interaction, message: str):
    """Chat with your default character"""
    user_id = str(interaction.user.id)
    
    # Check if user is authenticated
    if user_id not in user_data or 'token' not in user_data[user_id]:
        await interaction.response.send_message("You need to login and verify first. Use /login and then /verify", ephemeral=True)
        return
    
    # Check if user has set a default character
    if 'default_character' not in user_data[user_id]:
        await interaction.response.send_message("You need to set a default character first. Use /setcharacter", ephemeral=True)
        return
    
    character_id = user_data[user_id]['default_character']
    character_name = user_data[user_id].get('default_character_name', 'Character')
    
    await interaction.response.defer()
    
    try:
        token = user_data[user_id]['token']
        client = aiocai.Client(token)
        
        # Get or create chat
        if 'chats' not in user_data[user_id]:
            user_data[user_id]['chats'] = {}
        
        # Create or get existing chat
        chat_data = user_data[user_id]['chats']
        chat_key = character_id
        
        await interaction.followup.send(f"Sending message to **{character_name}**... please wait")
        
        async with await client.connect() as chat:
            if chat_key not in chat_data:
                # Create a new chat
                me = await client.get_me()
                new, answer = await chat.new_chat(character_id, me.id)
                chat_data[chat_key] = {
                    'chat_id': new.chat_id,
                    'name': answer.name  # Store the character name
                }
                save_user_data(user_data)
                await interaction.followup.send(f"**{answer.name}**: {answer.text}")
            else:
                # Use existing chat
                chat_id = chat_data[chat_key]['chat_id']
                message_response = await chat.send_message(character_id, chat_id, message)
                
                # Update name if it doesn't exist or has changed
                if 'name' not in chat_data[chat_key] or chat_data[chat_key]['name'] != message_response.name:
                    chat_data[chat_key]['name'] = message_response.name
                    save_user_data(user_data)
                
                await interaction.followup.send(f"**{message_response.name}**: {message_response.text}")
    except Exception as e:
        await interaction.followup.send(f"Error talking to character: {str(e)}")

# Talk command
@bot.tree.command(name="talk", description="Talk to a specific character by ID")
@app_commands.describe(
    character_id="The character ID from Character.AI",
    message="Your message to the character"
)
async def talk_slash(interaction: discord.Interaction, character_id: str, message: str):
    """Talk to a Character.AI character"""
    user_id = str(interaction.user.id)
    
    # Check if user is authenticated
    if user_id not in user_data or 'token' not in user_data[user_id]:
        await interaction.response.send_message("You need to login and verify first. Use /login and then /verify", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        token = user_data[user_id]['token']
        client = aiocai.Client(token)
        
        # Get or create chat
        if 'chats' not in user_data[user_id]:
            user_data[user_id]['chats'] = {}
        
        # Create or get existing chat
        chat_data = user_data[user_id]['chats']
        chat_key = character_id
        
        await interaction.followup.send("Sending message to character... please wait")
        
        async with await client.connect() as chat:
            if chat_key not in chat_data:
                # Create a new chat
                me = await client.get_me()
                new, answer = await chat.new_chat(character_id, me.id)
                chat_data[chat_key] = {
                    'chat_id': new.chat_id,
                    'name': answer.name  # Store the character name
                }
                save_user_data(user_data)
                await interaction.followup.send(f"**{answer.name}**: {answer.text}")
            else:
                # Use existing chat
                chat_id = chat_data[chat_key]['chat_id']
                message_response = await chat.send_message(character_id, chat_id, message)
                
                # Update name if it doesn't exist or has changed
                if 'name' not in chat_data[chat_key] or chat_data[chat_key]['name'] != message_response.name:
                    chat_data[chat_key]['name'] = message_response.name
                    save_user_data(user_data)
                
                await interaction.followup.send(f"**{message_response.name}**: {message_response.text}")
    except Exception as e:
        await interaction.followup.send(f"Error talking to character: {str(e)}")

# List characters command
@bot.tree.command(name="listcharacters", description="List all characters you've interacted with")
async def list_characters_slash(interaction: discord.Interaction):
    """Lists all characters you've interacted with"""
    user_id = str(interaction.user.id)
    
    # Check if user is authenticated
    if user_id not in user_data or 'token' not in user_data[user_id]:
        await interaction.response.send_message("You need to login and verify first. Use /login and then /verify", ephemeral=True)
        return
    
    # Check if user has any chats
    if 'chats' not in user_data[user_id] or not user_data[user_id]['chats']:
        await interaction.response.send_message("You haven't interacted with any characters yet. Use /talk to start a conversation.", ephemeral=True)
        return
    
    # Create embed with character list
    embed = discord.Embed(
        title="Your Characters",
        description="Characters you've interacted with",
        color=discord.Color.green()
    )
    
    # Get default character if set
    default_char_id = user_data[user_id].get('default_character', None)
    default_char_name = user_data[user_id].get('default_character_name', 'Unknown')
    
    if default_char_id:
        embed.add_field(
            name="Default Character",
            value=f"**{default_char_name}** (ID: `{default_char_id}`)",
            inline=False
        )
    
    # Add all characters from chat history
    chats = user_data[user_id]['chats']
    
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
                value=other_chars,
                inline=False
            )
        else:
            embed.add_field(
                name="Other Characters",
                value="You haven't chatted with any other characters yet.",
                inline=False
            )
    
    embed.set_footer(text="Use /setcharacter to set your default character")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Delete chat command
@bot.tree.command(name="deletechat", description="Delete chat history with a character by ID")
@app_commands.describe(character_id="The character ID to delete")
async def delete_chat_slash(interaction: discord.Interaction, character_id: str):
    """Delete your chat history with a specific character"""
    user_id = str(interaction.user.id)
    
    # Check if user is authenticated
    if user_id not in user_data or 'token' not in user_data[user_id]:
        await interaction.response.send_message("You need to login and verify first. Use /login and then /verify", ephemeral=True)
        return
    
    # Check if user has any chats
    if 'chats' not in user_data[user_id] or not user_data[user_id]['chats']:
        await interaction.response.send_message("You don't have any chat history to delete.", ephemeral=True)
        return
    
    # Check if character exists in chats
    chat_data = user_data[user_id]['chats']
    if character_id not in chat_data:
        await interaction.response.send_message(f"No chat found with character ID: `{character_id}`\nUse /listcharacters to see your available characters.", ephemeral=True)
        return
    
    # Get character name before deletion
    character_name = chat_data[character_id].get('name', 'Unknown Character')
    
    # Check if this is the default character
    is_default = user_data[user_id].get('default_character') == character_id
    
    # Delete the chat
    del chat_data[character_id]
    
    # If it was the default character, remove the default character setting
    if is_default:
        user_data[user_id].pop('default_character', None)
        user_data[user_id].pop('default_character_name', None)
        await interaction.response.send_message(f"Deleted chat with **{character_name}** (ID: `{character_id}`)\nNote: This was your default character. You'll need to set a new default with /setcharacter.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Deleted chat with **{character_name}** (ID: `{character_id}`)", ephemeral=True)
    
    # Save the updated user data
    save_user_data(user_data)

# Delete character command
@bot.tree.command(name="deletecharacter", description="Delete chat history with a character by name")
@app_commands.describe(character_name="The character name to delete")
async def delete_character_slash(interaction: discord.Interaction, character_name: str):
    """Delete your chat history with a character by name"""
    user_id = str(interaction.user.id)
    
    # Check if user is authenticated
    if user_id not in user_data or 'token' not in user_data[user_id]:
        await interaction.response.send_message("You need to login and verify first. Use /login and then /verify", ephemeral=True)
        return
    
    # Check if user has any chats
    if 'chats' not in user_data[user_id] or not user_data[user_id]['chats']:
        await interaction.response.send_message("You don't have any chat history to delete.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # Find character ID by name
    character_id = None
    chats = user_data[user_id]['chats']
    
    # First check if this matches the default character name
    default_char_id = user_data[user_id].get('default_character', None)
    default_char_name = user_data[user_id].get('default_character_name', '')
    
    if default_char_name.lower() == character_name.lower():
        character_id = default_char_id
    else:
        # Look through all chats for a name match
        for char_id, chat_data in chats.items():
            if 'name' in chat_data and chat_data['name'].lower() == character_name.lower():
                character_id = char_id
                break
    
    if not character_id:
        # If no exact match, check for partial matches
        possible_matches = []
        
        # Check default character for partial match
        if default_char_name and character_name.lower() in default_char_name.lower():
            possible_matches.append((default_char_id, default_char_name))
        
        # Check all chats for partial matches
        for char_id, chat_data in chats.items():
            if 'name' in chat_data and character_name.lower() in chat_data['name'].lower():
                # Don't duplicate the default character
                if char_id != default_char_id:
                    possible_matches.append((char_id, chat_data['name']))
        
        if possible_matches:
            # Found some partial matches
            match_list = "\n".join([f"• **{name}** (ID: `{id}`)" for id, name in possible_matches])
            await interaction.followup.send(f"I couldn't find an exact match for '{character_name}'. Did you mean one of these?\n{match_list}\nTry again with the exact name or use /deletechat with the ID")
            return
        else:
            # No matches at all
            await interaction.followup.send(f"I couldn't find any character named '{character_name}' in your chat history.\nUse /listcharacters to see all available characters.")
            return
    
    # Get character name before deletion
    character_name = chats[character_id].get('name', 'Unknown Character')
    
    # Check if this is the default character
    is_default = user_data[user_id].get('default_character') == character_id
    
    # Delete the chat
    del chats[character_id]
    
    # If it was the default character, remove the default character setting
    if is_default:
        user_data[user_id].pop('default_character', None)
        user_data[user_id].pop('default_character_name', None)
        await interaction.followup.send(f"Deleted chat with **{character_name}** (ID: `{character_id}`)\nNote: This was your default character. You'll need to set a new default with /setcharacter.")
    else:
        await interaction.followup.send(f"Deleted chat with **{character_name}** (ID: `{character_id}`)")
    
    # Save the updated user data
    save_user_data(user_data)

# Info command
@bot.tree.command(name="info", description="Show information about the bot")
async def info_slash(interaction: discord.Interaction):
    """Shows info about the bot"""
    embed = discord.Embed(
        title="Bot Info",
        description="A Discord bot for Character.AI",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Commands", 
        value="/login - Start the login process\n"
              "/verify - Verify with email link\n"
              "/setcharacter - Set your default character\n"
              "/listcharacters - Show all characters you've interacted with\n"
              "/chat - Talk to your default character\n"
              "/talk - Talk to a specific character by ID\n"
              "/deletechat - Delete chat history with a character by ID\n"
              "/deletecharacter - Delete chat history with a character by name\n"
              "/info - Show this help message", 
        inline=False
    )
    embed.set_footer(text="Created by NeuralCord")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Keep old prefix commands for backward compatibility
@bot.command()
async def info(ctx):
    await ctx.send("This bot now uses slash (/) commands instead of prefix (!) commands.\nType / to see available commands.")

# Run the bot
bot.run(token)
