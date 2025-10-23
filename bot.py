import discord
from discord.ext import commands
from discord import app_commands
import redis
import asyncio
import db
from db import hget, hset
from llm import llm, chat_response

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
db.setup(r)

async def run_bot(name):
    assert hget(name, 'discord_bot_token'), f"Character '{name}' missing discord_bot_token"
    assert hget(name, 'prompt'), f"Character '{name}' missing prompt"

    print(f"[{name}] Starting bot with token: {hget(name, 'discord_bot_token')[:20]}...", flush=True)
    bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

    async def respond_in(channel):
        messages = [msg async for msg in channel.history(limit=20)]

        # Skip simple reactions
        last_message = messages[0]
        stripped = last_message.content.replace(" ", "").replace("\n", "")
        if stripped and (set(stripped) <= {'아', 'ㅋ', '헉', 'ㄷ', '.', '!', '?', '엥'} or stripped == "레게노"):
            return

        async with channel.typing():
            chat_messages = [{"role": "assistant" if msg.author == bot.user else "user", "content": f"[{msg.author.display_name}] {msg.content}"} for msg in reversed(messages)]

            response_text = chat_response(chat_messages, system=hget(name, 'prompt'))
            response_text = response_text.removeprefix(f"[{name}] ")
            await channel.send(response_text)

    @bot.event
    async def on_ready():
        print(f"[{name}] Bot is ready!", flush=True)
        await bot.tree.sync()

    @bot.tree.command(name=f"hello-{name}", description="Test command")
    async def hello(interaction: discord.Interaction):
        await interaction.response.send_message("hello")

    @bot.tree.command(name=f"sethome-{name}", description=f"Set this channel as home for {name}")
    async def sethome(interaction: discord.Interaction):
        hset(name, 'home_id', interaction.channel.id)
        message = hget(name, 'home_msg') or 'Home set!'
        await interaction.response.send_message(message)

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return

        await bot.process_commands(message)

        home_id = hget(name, 'home_id')
        if home_id and message.channel.id == home_id and not message.content.startswith('!'):
            if message.mentions and bot.user not in message.mentions:
                return
            await respond_in(message.channel)

    await bot.start(hget(name, 'discord_bot_token'))

async def main():
    character_names = []
    for key in r.keys():
        if hget(key, 'discord_bot_token'):
            character_names.append(key)

    print(f"Found {len(character_names)} characters with discord_bot_token: {character_names}", flush=True)

    for name in character_names:
        if not hget(name, 'prompt'):
            hset(name, mapping={
                'prompt': llm(f"Generate a short character prompt for a self-aware Discord bot named '{name}'. Keep it 1-2 sentences, friendly and conversational."),
                'home_msg': llm(f"Generate a short, in-character message (1 sentence) for a '{name}' character bot saying this channel is now their home.")
            })

    await asyncio.gather(*[run_bot(name) for name in character_names])

if __name__ == '__main__':
    asyncio.run(main())
