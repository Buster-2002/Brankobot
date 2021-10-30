#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
The MIT License (MIT)

Copyright (c) 2021-present Buster

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
'''

__title__ = 'Brankobot'
__author__ = 'Buster#5741'
__license__ = 'MIT'
__copyright__ = 'Copyright 2021-present Buster'
__version__ = '6.0.0'

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from difflib import get_close_matches
from functools import lru_cache
from textwrap import dedent
from typing import List, Optional, Tuple, Union

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.utils.enums import Region, WotApiType
from cogs.utils.errors import ApiError, TankNotFound
from cogs.utils.models import Achievement, CustomCommand, Reminder, Tank

load_dotenv()

# Set up logging
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.INFO)
discord_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
discord_handler.setFormatter(formatter)
discord_logger.addHandler(discord_handler)

bot_logger = logging.getLogger('brankobot')
bot_logger.setLevel(logging.DEBUG)
bot_handler = logging.FileHandler(filename='brankobot.log', encoding='utf-8', mode='w')
bot_handler.setFormatter(formatter)
bot_logger.addHandler(bot_handler)

# Extensions to load
EXTENSIONS = {
    'cogs.events',
    'cogs.fun',
    'cogs.help',
    'cogs.utilities',
    'cogs.wot',
    'cogs.music',
    'cogs.misc'
}


def get_prefix(_bot: commands.Bot, _message: discord.Message) -> commands.when_mentioned_or:
    '''Returns a prefix used for the bot

    Args:
        bot (commands.Bot): The bot instance
        message (discord.Message): The message instance that was send, and the bot is now checking for prefix

    Returns:
        commands.when_mentioned_or: Allows for the bot to be mentioned, as well as the prefixes to be used as prefix
    '''
    prefixes = (
        '?',
        '.',
        'branko '
    )

    return commands.when_mentioned_or(*prefixes)(_bot, _message)


class Context(commands.Context):
    async def send_response(
        self,
        message: str = '',
        **kwargs
    ) -> Union[discord.Message, discord.Embed]:
        '''Sends an embed to ctx with the given title and description

        Args:
            message (str, optional): The primary message to send. Defaults to ''.
            url (str, optional): The url for title
            title (str, optional): The embed title. Defaults to command name.
            image (str, optional): The image to send. Defaults to Embed.Empty.
            thumbnail (str, optional): The thumbnail to send. Defaults to Embed.Empty.
            fields (List[Tuple[str, str, Optional[bool]]], optional): The embed fields to include. Defaults to None.
            files (Union[List[File], File], optional): The files to upload along with the message. Defaults to None.
            send (bool, optional): Whether to send the embed or return the embed.

        Returns:
            Union[discord.Message, discord.Embed]: The embedded message or the to be send embed
        '''
        title: str = kwargs.get('title', self.command.qualified_name.title())
        url: str = kwargs.get('url', discord.Embed.Empty)
        colour: int = kwargs.get('colour', 14389052)
        thumbnail: str = kwargs.get('thumbnail', discord.Embed.Empty)
        image: str = kwargs.get('image', discord.Embed.Empty)
        files: Union[List[discord.File], discord.File] = kwargs.get('files', [])
        files = [files] if not isinstance(files, list) else files
        fields: List[Tuple[str, str, Optional[bool]]] = kwargs.get('fields', [])
        delete_after: int = kwargs.get('delete_after')
        send: bool = kwargs.get('send', True)
        show_invoke_speed: bool = kwargs.get('show_invoke_speed', True)
        add_reference: bool = kwargs.get('add_reference', True)
        invoke_time = None
        if show_invoke_speed:
            if invoke_time := getattr(self.command, 'invoke_time', None):
                invoke_time = int((time.perf_counter() - invoke_time) * 1000)

        embed = discord.Embed(
            title=title,
            url=url,
            colour=colour,
            timestamp=datetime.utcnow(),
            description=message
        ).set_footer(
            text=f'.{self.command.qualified_name}'
            + (f' | took {invoke_time}ms' if invoke_time else ''),
            icon_url=self.bot.user.display_avatar
        ).set_thumbnail(
            url=thumbnail
        ).set_image(
            url=image
        )

        if fields:
            # Needed to properly align 2 fields next
            # to each other, doesn't do it when last
            # field isn't inline though
            if not fields[-1][-1] is False:
                while len(fields) % 3:
                    fields.append(('\u200b', '\u200b'))

            for field in fields:
                try:
                    inline = field[2]
                except IndexError:
                    inline = True

                embed.add_field(
                    name=str(field[0]),
                    value=str(field[1]),
                    inline=inline
                )

        if send is False:
            return embed

        options = {
            'embed': embed,
            'delete_after': delete_after,
            'files': files
        }
        if add_reference is True:
            options['mention_author'] = False
            options['reference'] = self.message.to_reference()

        return await self.send(**options)


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=get_prefix,
            case_insensitive=True,
            description='A bot for the RLD WoT clan Discord server',
            intents=discord.Intents(
                guilds=True, # get_channel
                members=True, # on_member_join, get_user, get_member, roles, nick
                presences=True, # Only used for offline command (Getting jocs status)
                guild_messages=True, # on_message
                guild_reactions=True, # For menus
                voice_states=True, # music
            ),
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                users=True,
                roles=False
            ),
            activity=discord.Activity(
                type=discord.ActivityType.competing,
                name='a spoon licking contest'
            ),
            owner_ids={
                159746057524346880, # marnik
                764584777642672160 # me
            }
        )
        self.BEEN_READY = False
        self.DISCORD_API_TOKEN = os.getenv('DISCORD_TOKEN')
        self.WOT_API_TOKEN = os.getenv('WOT_TOKEN')
        self.REMINDER_TASKS = {}
        self.MUSIC_PLAYERS = {}
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()


    async def on_error(self, event: str, *args, **kwargs) -> Optional[discord.Message]:
        '''Handles errors for events

        Args:
            event (str): The event in which the error occurred

        Returns:
            Optional[discord.Message]: The error message replying to the message that caused the error
        '''
        exception_type, error, traceback = sys.exc_info()
        if event == 'on_message':
            message = args[0]
            if isinstance(error, commands.CommandOnCooldown):
                return await message.reply(
                    f'The command is on cooldown ({error.type.name} scope), try again in {error.retry_after:.0f}s :joy:',
                    delete_after=60,
                    mention_author=False
                )

        logger = logging.getLogger('brankobot')
        logger.exception('Unexpected error')


    async def delete_reminder(self, reminder: Reminder):
        '''Deletes a reminder from the database and local dict

        Args:
            reminder (Reminder): The reminder to delete
        '''
        cursor = await self.CONN.cursor()
        try:
            delete_reminder_query = dedent('''
                DELETE
                FROM reminders
                WHERE id = ?;
            '''.strip())
            await cursor.execute(
                delete_reminder_query,
                (reminder.id,)
            )
            await self.CONN.commit()
            self.REMINDER_TASKS.pop(reminder.id)

        finally:
            await cursor.close()


    async def start_timer(self, reminder: Reminder):
        '''Starts a timer for the reminder command

        It calculates the time needed to sleep based on current time,
        not the time the command was created. If the end time has
        already passed, the reminder will be deleted.

        Dispatches an event, on_reminder_due, when the
        reminder sleep finished

        Args:
            reminder (Reminder): The reminder to start a timer for
        '''
        cursor = await self.CONN.cursor()
        try:
            seconds = (reminder.ends_at - datetime.now()).total_seconds()
            if seconds > 0:
                task = self.loop.create_task(asyncio.sleep(seconds))
                self.REMINDER_TASKS[reminder.id] = {
                    'task': task,
                    'reminder': reminder
                }

                # Await the task and dispatch event when it finished without being cancelled
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                else:
                    self.dispatch('reminder_due', reminder)

            else:
                await self.delete_reminder(reminder)

        finally:
            await cursor.close()


    async def get_custom_command(self, command_name: str) -> Optional[CustomCommand]:
        '''Gets a custom command by name

        Args:
            command_name (str): the custom commands name

        Returns:
            Optional[CustomCommand]: The custom command if found
        '''
        cursor = await self.CONN.cursor()
        try:
            select_command_query = dedent('''
                SELECT *
                FROM custom_commands
                WHERE name = ?;
            '''.strip())
            rows = await cursor.execute(
                select_command_query,
                (command_name,)
            )

            row = await rows.fetchone()
            if row:
                return CustomCommand(*row)

            return None

        finally:
            await cursor.close()


    @lru_cache(maxsize=64)
    def search_achievement(self, achievement_search: str, key: str = 'internal_name') -> Achievement:
        """Searches for an achievement by key in internal list

        Args:
            achievement_search (str): The string to search by
            key (str, optional): The achievement key to search by. Defaults to 'internal_name'.

        Returns:
            Achievement: The achievement, if found
        """
        possibilities = {getattr(v, key): k for k, v in self.ACHIEVEMENTS.items()}
        matches = get_close_matches(
            achievement_search,
            list(possibilities.keys()),
            n=1,
            cutoff=0.5
        )

        return self.TANKS[possibilities[matches[0]]]


    @lru_cache(maxsize=256)
    def search_tank(self, tank_search: str, key: str = 'internal_name') -> Tank:
        '''Searches a tank by key in internal list

        Args:
            tank_search (str): The string to search by
            key (str, optional): The tank key to search by. Defaults to 'internal_name'.

        Raises:
            TankNotFound: The tank wasn't found

        Returns:
            Tank: The tank, if found
        '''
        possibilities = {getattr(v, key): k for k, v in self.TANKS.items()}
        matches = get_close_matches(
            tank_search,
            list(possibilities.keys()),
            n=1,
            cutoff=0.5
        )

        if not matches:
            raise TankNotFound(tank_search)

        return self.TANKS[possibilities[matches[0]]]


    async def get_context(self, message: discord.Message, *, cls=None):
        return await super().get_context(message, cls=cls or Context)


    async def wot_api(
        self,
        endpoint: str,
        *,
        method: str = 'GET',
        params: dict = {},
        headers: dict = {},
        payload: dict = None,
        region: Region = Region.eu,
        api_type: WotApiType = WotApiType.official
    ) -> dict:
        '''Sends a request to one of the three WoT api's

        Args:
            endpoint (str): The endpoint to use
            method (str, optional): The HTTP method to use. Defaults to 'GET'.
            params (dict, optional): The params to pass. Defaults to {}.
            headers (dict, optional): The headers to pass. Defaults to {}.
            payload (dict, optional): The payload to pass. Defaults to None.
            region (Region, optional): The API region to use. Defaults to Region.eu.
            api_type (WotApiType, optional): The API type to use. Defaults to WotApiType.official.

        Raises:
            ApiError: Getting the data failed

        Returns:
            dict: The API response
        '''
        region = str(region).lower()

        # official and unofficial API use .com instead of .na
        # api.worldoftanks.com, worldoftanks.com
        # wargaming uses na: na.wargaming.net
        if region == 'na':
            if api_type in {WotApiType.official, WotApiType.unofficial}:
                region = 'com'

        base = api_type.value.format(region)
        url = f'https://{base}{endpoint}'

        if api_type is WotApiType.official:
            params['application_id'] = self.WOT_API_TOKEN
        elif api_type is WotApiType.unofficial:
            # needed to imitate browser
            headers['x-requested-with'] = 'XMLHttpRequest'

        async with self.AIOHTTP_SESSION.request(
            method,
            url,
            json=payload,
            params=params,
            headers=headers
        ) as r:
            json_data = await r.json(content_type=None)
            if error := json_data.get('error'):
                raise ApiError(
                    error['code'],
                    error['message']
                )

            return json_data


bot = Bot()

if __name__ == '__main__':
    for ext in EXTENSIONS:
        bot.load_extension(ext)
        print(f'[*] Loaded cog {ext}')

    bot.run(bot.DISCORD_API_TOKEN)
