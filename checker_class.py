import requests
import json
from bs4 import BeautifulSoup
import re
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context, bot

_URL: str = "https://papermc.io/downloads/paper"
_PATH_CONFIG: str = "config.json"
_PATH_VERSION: str = "version.txt"


class VersionNotFoundException(Exception):
    def __init__(self, text) -> None:
        super().__init__(f"No version number found in text: {text}")


class DiscordBot(commands.Bot):
    config: dict

    def __init__(self, config: dict) -> None:
        super().__init__(command_prefix="!",
                         intents=discord.Intents.all())
        self.config = config
        self.register_commands()

    @tasks.loop(minutes=10)
    async def check_and_update_version(self) -> None:
        try:
            current_version: str = check_paper_version()
            previous_version: str = load_previous_version(_PATH_VERSION)
            channel = await self.fetch_channel(int(config['channel_id']))
            if current_version != previous_version:
                save_new_version(_PATH_VERSION, current_version)
                await channel.send(f"New Paper Version: {current_version}")
        except Exception as e:
            print(f"An error occurred {e}")

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user}")
        if not self.check_and_update_version.is_running():
            self.check_and_update_version.start()

    def register_commands(self) -> None:

        @commands.command(name="version")
        async def version(ctx: Context) -> None:
            paper_version: str = check_paper_version()
            save_new_version(_PATH_VERSION, paper_version)
            await ctx.send(f"Actual version: {paper_version}")

        self.add_command(version)


def load_config(config_file: str) -> dict:
    with open(config_file, 'r') as f:
        return json.loads(f.read())


def load_previous_version(version_file: str) -> str | None:
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def save_new_version(version_file: str, version: str) -> None:
    with open(version_file, 'w') as f:
        f.write(version)


def extract_version(text: str) -> str | None:
    version_pattern: str = r'\b\d+(\.\d+){1,3}\b'
    match = re.search(version_pattern, text)
    if match:
        return match.group(0)
    else:
        raise VersionNotFoundException(text)


def check_paper_version() -> str:
    response: requests = requests.get(_URL)
    soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')
    data: str = soup.find('h2').text
    return extract_version(data)


if __name__ == '__main__':
    try:
        config: dict = load_config(_PATH_CONFIG)
        bot = DiscordBot(config)
        bot.run(config['token'])
    except Exception as e:
        print(f"An error occurred: {e}")
