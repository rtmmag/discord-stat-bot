import os
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE = "stats.db"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def setup_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            elo INTEGER DEFAULT 500
        )
    """)

    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    conn.close()
    return user


def create_user(user_id: int, username: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username)
        VALUES (?, ?)
    """, (user_id, username))

    conn.commit()
    conn.close()


@bot.event
async def on_ready():
    setup_database()
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


@bot.tree.command(name="ping", description="Checks response of bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")


@bot.tree.command(name="register", description="Registers use for stat tracking")
async def register(interaction: discord.Interaction):
    user_id = interaction.user.id
    username = interaction.user.name

    create_user(user_id, username)

    await interaction.response.send_message(
        f"{interaction.user.mention}, registered!"
    )


@bot.tree.command(name="stats", description="Views stats")
async def stats(interaction: discord.Interaction):
    user = get_user(interaction.user.id)

    if user is None:
        await interaction.response.send_message("Not registered. Use /register first.")
        return

    user_id, username, wins, losses, elo = user

    embed = discord.Embed(
        title=f"{username}'s Stats",
        description="Player stat profile",
    )
    embed.add_field(name="Wins", value=wins)
    embed.add_field(name="Losses", value=losses)
    embed.add_field(name="ELO", value=elo)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="addwin", description="Adds a win to stats")
async def addwin(interaction: discord.Interaction):
    user = get_user(interaction.user.id)

    if user is None:
        await interaction.response.send_message("Not registered. Use /register first.")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET wins = wins + 1,
            elo = elo + 25
        WHERE user_id = ?
    """, (interaction.user.id,))

    conn.commit()
    conn.close()

    await interaction.response.send_message("Win has been added. +25 ELO.")


@bot.tree.command(name="addloss", description="Adds a loss to stats")
async def addloss(interaction: discord.Interaction):
    user = get_user(interaction.user.id)

    if user is None:
        await interaction.response.send_message("Not registered. Use /register first.")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET losses = losses + 1,
            elo = MAX(0, elo - 25)
        WHERE user_id = ?
    """, (interaction.user.id,))

    conn.commit()
    conn.close()

    await interaction.response.send_message("Loss added. -25 ELO.")


@bot.tree.command(name="leaderboard", description="Show the top players by ELO")
async def leaderboard(interaction: discord.Interaction):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, wins, losses, elo
        FROM users
        ORDER BY elo DESC
        LIMIT 10
    """)

    players = cursor.fetchall()
    conn.close()

    if not players:
        await interaction.response.send_message("No players registered yet.")
        return

    description = ""

    for index, player in enumerate(players, start=1):
        username, wins, losses, elo = player
        description += f"**{index}. {username}** — {elo} ELO | {wins}W / {losses}L\n"

    embed = discord.Embed(
        title="Leaderboard",
        description=description
    )

    await interaction.response.send_message(embed=embed)


bot.run(TOKEN)