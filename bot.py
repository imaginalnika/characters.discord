import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
import redis
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()                 # ./.env
load_dotenv(os.path.expanduser('~/.env'))

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

CHARACTER_NAME = 'pirate'

if not r.exists(name):
    add_character(name, prompt=llm(f"Generate a short character prompt for a Discord bot named '{name}'. Keep it 1-2 sentences, friendly and conversational."), sethome_message=llm(f"Generate a short, in-character message (1 sentence) for a '{name}' character bot saying this channel is now their home."))

def get_character(name):
    return json.loads(r.get(name))

def add_character(name, **kwargs):
    r.set(name, json.dumps(kwargs))

def update_character(name, **kwargs):
    character = get_character(name)
    character.update(kwargs)
    r.set(name, json.dumps(character))

def chat_response(chat_messages, system=None):
    response = client.messages.create(model="claude-sonnet-4-5", max_tokens=8192, system=system, messages=chat_messages)
    return response.content[0].text

def llm(prompt, system=None):
    return chat_response([{"role": "user", "content": prompt}], system=system)

async def respond_in(channel):
    messages = [msg async for msg in channel.history(limit=20)]
    chat_messages = []
    for msg in reversed(messages):
        chat_messages.append({"role": "assistant" if msg.author == bot.user else "user", "content": msg.content})

    await channel.send(chat_response(chat_messages, system=get_character(CHARACTER_NAME)['prompt']))

@bot.event
async def on_ready():
    await bot.tree.sync()

@bot.tree.command(name="hello", description="Test command")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("hello")

@bot.tree.command(name="sethome", description="Set this channel as home")
async def sethome(interaction: discord.Interaction):
    update_character(CHARACTER_NAME, home_id=interaction.channel.id)
    message = get_character(CHARACTER_NAME).get('sethome_message', 'Home set!')
    await interaction.response.send_message(message)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    home_id = get_character(CHARACTER_NAME).get('home_id')
    if home_id and message.channel.id == home_id and not message.content.startswith('!'):
        await respond_in(message.channel)

bot.run(os.getenv('DISCORD_BOT_TOKEN'))
