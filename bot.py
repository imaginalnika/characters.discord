import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
import redis
from dotenv import load_dotenv
from anthropic import Anthropic
from openai import OpenAI
import db
from db import hget, hset

load_dotenv(os.path.expanduser('~/.env'))

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
db.setup(r)

NAME = 'pirate'

if not r.exists(NAME):
    hset(NAME, mapping={
        'prompt': llm(f"Generate a short character prompt for a self-aware Discord bot named '{NAME}'. Keep it 1-2 sentences, friendly and conversational."),
        'home_msg': llm(f"Generate a short, in-character message (1 sentence) for a '{NAME}' character bot saying this channel is now their home.")
    })

def chat_response(chat_messages, system=None):
    response = client.messages.create(model="claude-sonnet-4-5", max_tokens=8192, system=system, messages=chat_messages)
    return response.content[0].text

def llm(prompt, system=None):
    return chat_response([{"role": "user", "content": prompt}], system=system)

def structured_llm(prompt, schema):
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_schema", "json_schema": {"name": "response", "strict": True, "schema": schema}}
    )
    return json.loads(response.choices[0].message.content)

async def respond_in(channel):
    async with channel.typing():
        messages = [msg async for msg in channel.history(limit=20)]
        chat_messages = []
        for msg in reversed(messages):
            chat_messages.append({"role": "assistant" if msg.author == bot.user else "user", "content": msg.content})

        response_text = chat_response(chat_messages, system=hget(NAME, 'prompt'))
        last_message = messages[0]

        result = structured_llm(
            f"Is this a question? Message: {last_message.content}",
            {"type": "object", "properties": {"reasoning": {"type": "string"}, "is_question": {"type": "boolean"}}, "required": ["reasoning", "is_question"], "additionalProperties": False}
        )

        print(f"reasoning: {result['reasoning']}", flush=True)
        print(f"is_question: {result['is_question']}", flush=True)

        if result["is_question"]:
            await last_message.reply(response_text)
        else:
            await channel.send(response_text)

@bot.event
async def on_ready():
    await bot.tree.sync()

@bot.tree.command(name="hello", description="Test command")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("hello")

@bot.tree.command(name="sethome", description="Set this channel as home")
async def sethome(interaction: discord.Interaction):
    hset(NAME, 'home_id', interaction.channel.id)
    message = hget(NAME, 'home_msg') or 'Home set!'
    await interaction.response.send_message(message)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    home_id = hget(NAME, 'home_id')
    if home_id and message.channel.id == home_id and not message.content.startswith('!'):
        await respond_in(message.channel)

bot.run(hget(NAME, 'discord_bot_token'))
