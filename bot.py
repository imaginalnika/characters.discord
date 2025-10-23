import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

@bot.command()
async def say(ctx, *, message):
    await ctx.send(message)

bot.run('YOUR_BOT_TOKEN_HERE')
