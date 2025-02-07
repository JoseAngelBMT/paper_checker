import requests
import json
from bs4 import BeautifulSoup
import re
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
import pandas as pd
import pytz
from datetime import datetime

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

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if self.user in message.mentions and "daily" in message.content.lower():
            await message.channel.send("DALE!")

        if "miércoles eh" in message.content.lower() or "miercoles eh" in message.content.lower():
            await message.channel.send("", embed=discord.Embed().set_image(url="https://pbs.twimg.com/media/GWpRGcWWgAA7yr3.jpg"))

        await self.process_commands(message)

    def register_commands(self) -> None:

        @commands.command(name="version")
        async def version(ctx: Context) -> None:
            paper_version: str = check_paper_version()
            save_new_version(_PATH_VERSION, paper_version)
            await ctx.send(f"Actual version: {paper_version}")

        @commands.command(name="last_version")
        async def last_version(ctx: Context, arg: str = commands.parameter(default=check_paper_version())) -> None:
            url: str = f"https://api.papermc.io/v2/projects/paper/versions/{arg}/builds"
            response: requests = requests.get(url)
            if response.status_code != 200:
                await ctx.send("Wrong version input")
            else:
                data: dict = response.json()
                if 'builds' in data:
                    builds_data = data['builds']
                    df: pd.DataFrame = pd.DataFrame(builds_data)
                    # df['time'] = pd.to_datetime(df['time'])
                    df.sort_values(by='time', inplace=True, ascending=False)
                    df.reset_index(drop=True, inplace=True)
                    version_type: str = "experimental"
                    if df['channel'].loc[0] == "default":
                        version_type = "stable"
                    date_time = convert_utc_madrid(df['time'].loc[0])
                    await ctx.send(f"Version: {arg} #{df['build'].loc[0]}\n **{version_type.title()}** on **{date_time}**")
                else:
                    await ctx.send("Some problem with request")

        self.add_command(version)
        self.add_command(last_version)


def convert_utc_madrid(date_time: str) -> str:
    utc_date_time: datetime = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
    madrid_zone: pytz = pytz.timezone('Europe/Madrid')
    madrid_date_time: datetime = utc_date_time.astimezone(madrid_zone)
    return madrid_date_time.strftime("%d/%m/%Y %H:%M:%S")


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
        raise
