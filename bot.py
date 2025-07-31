import os
import discord
import boto3
from discord.ext import commands
from dotenv import load_dotenv
import paramiko
import asyncio

# Load environment variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
EC2_INSTANCE_ID = os.getenv("EC2_INSTANCE_ID")

EC2_HOST = os.getenv("EC2_HOST")
EC2_USERNAME = os.getenv("EC2_USERNAME")
PEM_FILE_NAME = os.getenv("PEM_FILE_NAME")
MINECRAFT_SERVER_DIR = os.getenv("MINECRAFT_SERVER_DIR")

# Set up Discord bot with prefix commands and intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Set up AWS EC2 client
ec2 = boto3.client(
    "ec2",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# SSH helper function to run commands
def run_ssh_command(host, user, key_path, commands):
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, key_filename=key_path)

    output = ""
    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        print(out)
        if exit_status != 0:
            ssh.close()
            raise Exception(f"SSH command failed: {cmd}\nError: {err}")
        output += f"$ {cmd}\n{out}\n"
    ssh.close()

    return output

# Start Minecraft server command
@bot.command(name="start_server")
async def start_server_prefix(ctx):
    try:
        commands = [
            f"cd {MINECRAFT_SERVER_DIR}",
            "screen -S minecraft -X quit || true",
            "screen -dmS minecraft ./start.sh",
        ]

        output = run_ssh_command(EC2_HOST, EC2_USERNAME, PEM_FILE_NAME, commands)
        await ctx.send(f"🟢 Minecraft server started! Here is the directory listing:\n```\n{output}\n```")
    except Exception as e:
        try: 
            commands.pop(1)
            print(commands)
            output = run_ssh_command(EC2_HOST, EC2_USERNAME, PEM_FILE_NAME, commands)
            await ctx.send(f"🟢 Minecraft server started! Here is the directory listing:\n```\n{output}\n```")
        except Exception as e:

            await ctx.send(f"{e}")
# Stop Minecraft server command
@bot.command(name="stop_server")
async def stop_server_prefix(ctx):
    try:
        commands = [
            "screen -S minecraft -X stuff 'stop\n'"
        ]
        run_ssh_command(EC2_HOST, EC2_USERNAME, PEM_FILE_NAME, commands)

        await ctx.send("🛑 Minecraft server stopping...")

        # Wait 10 seconds to let the server shutdown gracefully
        await asyncio.sleep(4)

        # Then stop the EC2 instance
        ec2.stop_instances(InstanceIds=[EC2_INSTANCE_ID])
        await ctx.send("🔴 EC2 instance stopping...")
    except Exception as e:
        await ctx.send(f"⚠️ Error stopping server: {str(e)}")

# Ping command for testing
@bot.command(name="ping")
async def ping_bot(ctx):
    await ctx.send("✅ Bot is alive!")

# On bot ready event
@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")

# Run the bot
bot.run(DISCORD_TOKEN)
