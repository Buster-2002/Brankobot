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

import datetime
import json
import logging
import random
import time
from collections import defaultdict
from pathlib import Path
from textwrap import dedent

import aiohttp
import aiosqlite
import discord
from discord import __version__ as dcversion
from discord.ext import commands, tasks
from discord.message import MessageReference
from discord.utils import format_dt
from humanize import naturaldelta
from humanize.number import ordinal
from main import __version__ as botversion

from .utils.enums import (BigRLDChannelType, Emote, GuildType,
                          SmallRLDChannelType, try_enum)
from .utils.errors import *
from .utils.models import Achievement, Birthday, Reminder, Tank


# -- Cog -- #
class Events(commands.Cog):
    '''
    All events that can happen
    - respond to certain on message events
    - respond to being ready
    - respond to member joining
    '''

    def __init__(self, bot):
        self.bot = bot
        self.counter = 0
        self.custom_command_cooldown = commands.CooldownMapping.from_cooldown(
            rate=10, # Custom commands can be used 10 times every 60 seconds on a per guild basis
            per=60,
            type=commands.BucketType.guild
        )
        self._mention_responses = {
            '{}': 15,
            'stop @ing me idiot': 15,
            'PUINK\n!!!': 15,
            'No u': 15,
            'shut up {}': 15,
            f'{Emote.shush}': 15,
            'i did not ask tho': 15,

            'please be quiet in the back of the bus': 10,
            f'can you dont {Emote.rolling_eyes}': 10,

            f'behave yourself or we\'ll end the ride early {Emote.mad}': 5,
            'did you mean to mention <@!331395741585244162>?': 5,
            'https://cdn.discordapp.com/attachments/724542301543727134/737432024373133312/04264c87b5ff12243395b867730e11e940c6f6efv2_00.png': 5,
        }
        self._join_responses = {
            'who you {}': 16,
            '{} who you be': 16,
            'new guy {} who dis': 16,

            f'who dis one {{}} {Emote.eyes}': 12,
            '{} new phon who dis': 12,
            'hi {}': 12,
            'shalom {}': 12,

            'siema pl {}': 8,
            '{}; do you sexually abuse busses too': 8,
            'ah, {}, a new one to ride my bus': 8,
            f'{{}} {Emote.bus} WROOM WROOM!': 8,
            'my bus is open, please enter {}': 8,
            f'would you like to see my \'bus\' {{}} {Emote.eyes}': 8,

            f'{Emote.oncoming_bus} is the last thing they see {{}}': 4,

            'hi {}!\ntoo slow <@!331395741585244162>': 2
        }
        self._reminder_replies = (
            'you wanted me to remind you',
            'you wanted to be reminded',
            'you had something on your mind',
            'here you go',
            f'there, reminded you {Emote.rolling_eyes}'
        )
        self._last_messages = defaultdict(
            lambda: {
                'content': str(),
                'counter': int()
            }
        )


    @commands.Cog.listener()
    async def on_ready(self):
        '''
        Called when the client is done preparing the data received from Discord
        - create bot.AIOHTTP_SESSION
        - load tanks in bot.TANKS
        - load achievements in bot.ACHIEVEMENTS
        - create bot.CONN and check if reminders and custom_commands tables are in place
        - load reminders from database and start their timer
        '''
        if self.bot.BEEN_READY is False:
            # Load variables that require async func
            self.bot.AIOHTTP_SESSION = aiohttp.ClientSession(loop=self.bot.loop)
            logger = logging.getLogger('brankobot')
            logger.info('Bot is ready')

            # Load tanks in memory
            print('-' * 75)
            print(f'[*] Loading tanks in memory...')

            reward_vehicles = {'T95/FV4201', 'VK 75.01 K', 'Obj. 907', 'M60', '121B', 'T95E6', 'Carro 45 t', 'Obj. 279 (e)', 'Obj. 260', 'Chimera' 'T-22 med.', 'T 55A', 'StuG IV', 'Excalibur', 'Kpz 50 t', 'T28 HTC', 'Concept 1B', 'AE Phase I', '114 SP2', 'Obj. 777 II', 'K-91-PT', 'Kunze Panzer', 'Char Futur 4', 'WZ-111 QL', 'Foch 155', 'FV215b', 'FV215b 183', 'Super Hellcat', 'T-50-2', 'Super Chaffee'}
            collector_vehicles = {'Pz.Jäg. I', 'M7 Priest', 'D.W. 2', 'Pz. 38 (t)', 'T-46', 'T2 Medium', 'UE 57', 'AT-1', 'T1 HMC', 'Loyd GC', 'T40', 'St.Pz. II', 'Pz. III/IV', 'G1 R', 'Pvlvv fm/42', 'Chi-Ni', 'JPanther II', 'Ikv 72', 'Medium I', 'Pz. I C', 'L6/40', 'VK 20.01 D', 'Ke-Ni', 'FT BS', 'Pz.Sfl. IVb', 'Type 95', 'M37', 'Birch Gun', 'KV-85', 'UC 2-pdr', 'M7', 'M3G FT', 'SU-18', 'T56 GMC', 'SU-5', 'SU-85B', 'Pz. 38 nA', 'Pz. 35 (t)', 'Archer', 'T67', 'KV-13', 'Marder 38T', 'D1', 'M2', 'SU-14-1', 'M3 Lee', 'Pz. IV D', 'T82 HMC', 'Hetzer', 'Bison', '113', 'T-50', 'T-26G FT', 'Grant', 'FT AC', 'Alecto', 'T3 HMC', 'T-26', 'Wespe', 'Medium II', 'SU-26', 'T-62A', 'SARL 42', 'R35', 'D2', 'VK 30.01 D', 'Ke-Ho', 'H35', 'Firefly', 'G.Pz. Mk. VI', 'Pz.Sfl. IVc', 'Lorr. 39L AM', 'Pz. IV A', 'I-Go/Chi-Ro', 'T18 HMC', 'O-I Exp.', 'Stuart I-IV', 'T-80', 'M2 Medium', 'Churchill GC', 'T21', 'Marder II', 'Medium III', 'Sherman III', 'M4A3E2', 'T71 DA', 'AMX 105 AM', 'AMX 30', 'Pz. I', 'Sexton II', 'AMX 30 B', 'Type 91'}
            data = await self.bot.wot_api(
                '/wot/encyclopedia/vehicles/',
                params={
                    'fields': 'tank_id,type,tag,name,short_name,nation,tier,is_premium,images'
                }
            )

            self.bot.TANKS = {}
            for k, v in data['data'].items():
                self.bot.TANKS[int(k)] = Tank(
                    id=int(k),
                    type=v['type'],
                    name=v['name'],
                    short_name=v['short_name'],
                    internal_name=v['tag'],
                    nation=v['nation'],
                    tier=v['tier'],
                    big_icon=v['images']['big_icon'],
                    small_icon=v['images']['small_icon'],
                    contour_icon=v['images']['contour_icon'],
                    is_premium=v['is_premium'],
                    is_reward=v['short_name'] in reward_vehicles,
                    is_collector=v['short_name'] in collector_vehicles
                )

            # Load achievements in memory
            print('-' * 75)
            print(f'[*] Loading achievements in memory...')

            with open(Path('assets/data/achievements.json', encoding='utf-8')) as file:
                achievements = json.load(file)

            self.bot.ACHIEVEMENTS = {}
            for k, v in achievements.items():
                self.bot.ACHIEVEMENTS[int(k)] = Achievement(
                    id=int(k),
                    name=v['name'],
                    internal_name=v['internal_name'],
                    emote=try_enum(Emote, v['emote_name']),
                    description=v['description']
                )

            # Create database connection
            self.bot.CONN = conn = await aiosqlite.connect(Path('assets/data/database.db'))
            cursor = await conn.cursor()

            # Create tables
            try:
                print('-' * 75)
                print('[*] Creating DB connection...')

                # Create custom commands table if it doesn't yet exist
                create_cc_table_query = dedent('''
                    CREATE TABLE IF NOT EXISTS custom_commands (
                        id                 INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                        creator_id         INTEGER NOT NULL,
                        times_used         INTEGER DEFAULT 0 NOT NULL,
                        creation_timestamp REAL NOT NULL,
                        name               TEXT NOT NULL,
                        content            TEXT NOT NULL
                    );
                '''.strip())
                await cursor.execute(create_cc_table_query)
                await conn.commit()

                # Create reminder table if it doesn't yet exist
                create_reminder_table_query = dedent('''
                    CREATE TABLE IF NOT EXISTS reminders (
                        id                   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                        creator_id           INTEGER NOT NULL,
                        channel_id           INTEGER NOT NULL,
                        context_message_link TEXT NOT NULL,
                        creation_timestamp   REAL NOT NULL,
                        end_timestamp        REAL NOT NULL,
                        message              TEXT DEFAULT '' NOT NULL
                    );
                '''.strip())
                await cursor.execute(create_reminder_table_query)
                await conn.commit()

                # Create birthdays table it doesn't yet exist
                create_birthday_table_query = dedent('''
                    CREATE TABLE IF NOT EXISTS birthdays (
                        id            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                        user_id       INTEGER NOT NULL,
                        server_id     INTEGER NOT NULL,
                        birthday_date TEXT NOT NULL
                    );
                '''.strip())
                await cursor.execute(create_birthday_table_query)
                await conn.commit()

                print('-' * 75)
                print('[*] Loading reminders...')

                select_reminder_query = dedent(f'''
                    SELECT *
                    FROM reminders
                '''.strip())

                result = await cursor.execute(select_reminder_query)
                rows = await result.fetchall()

                if rows:
                    reminders = [Reminder(*r) for r in rows]
                    for reminder in reminders:
                        print(f'[*] Loaded reminder belonging to {reminder.creator.id}')
                        self.bot.loop.create_task(self.bot.start_timer(reminder))

                # Starting birthday task
                self.check_birthdays.start()

                self.bot.BEEN_READY = True
                print('-' * 75)
                print(f'[*] Bot {self.bot.user.name} is ready')
                print(f'[*] Running on version {botversion}')
                print(f'[*] Running with discord.py version {dcversion}')
                print('-' * 75)

            finally:
                await cursor.close()


    # Check for birthdays every day at 07:00 UTC which is 08:00 CET
    @tasks.loop(time=datetime.time(hour=7))
    async def check_birthdays(self):
        logger = logging.getLogger('brankobot')
        logger.info('Checking for birthdays...')
        cursor = await self.bot.CONN.cursor()
        try:
            select_birthdays_query = dedent('''
                SELECT *
                FROM birthdays;
            '''.strip())

            result = await cursor.execute(select_birthdays_query)
            rows = await result.fetchall()

            if rows:
                birthdays = [Birthday(*r) for r in rows]
                for birthday in birthdays:
                    today = datetime.date.today()

                    # Only proceed if today is actually the day...
                    if (today.month, today.day) == (birthday.date.month, birthday.date.day):
                        server_id = birthday.server_id
                        channel_id = None

                        if server_id is GuildType.big_rld.value:
                            channel_id = BigRLDChannelType.classified.value
                        elif server_id is GuildType.small_rld.value:
                            channel_id = SmallRLDChannelType.classified.value

                        if channel_id:
                            channel = self.bot.get_channel(channel_id)
                            user = self.bot.get_user(birthday.user_id)
                            await channel.send(f'{Emote.tada} it\'s {user.mention}\'s **{ordinal(today.year - birthday.date.year)}** birthday {Emote.cake}!')
                            await channel.send(str(Emote.feels_birthday_man))

        finally:
            await cursor.close()


    @commands.Cog.listener()
    async def on_reminder_due(self, reminder: Reminder):
        '''
        Called when a reminders timer finished
        - send a message in the channel where the reminder was created,
          replying to the message that created it
        - delete reminder from database
        '''
        cursor = await self.bot.CONN.cursor()
        try:
            channel = self.bot.get_channel(reminder.channel.id)
            # for some reason MessageReference has no classmethod for message links
            guild_id, channel_id, message_id = map(int, reminder.context_message_link.split('/')[-3:])

            if channel is not None:
                # Send message with a reply to message that created reminder
                msg = format_dt(reminder.created_at, 'R')
                if reminder.message:
                    msg += f': {reminder.message}'
                else:
                    msg += f', {random.choice(self._reminder_replies)}'

                await channel.send(
                    msg,
                    reference=MessageReference(
                        message_id=message_id,
                        channel_id=channel_id,
                        guild_id=guild_id,
                        fail_if_not_exists=False
                    )
                )

                await self.bot.delete_reminder(reminder)

        finally:
            await cursor.close()


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        '''
        Called for every message send that the bot can see.
        - react if mentioned
        - send custom command content if its found, and increment its usage by 1
        - send message content if it is the same 4x in a row
        '''
        channel = message.channel
        content = message.content

        # Ignore ourselves in messages
        if message.author == self.bot.user or self.bot.BEEN_READY is False:
            return

        # React to being mentioned
        if self.bot.user in message.mentions:
            response = (random.choices(*zip(*self._mention_responses.items()))[0]).format(message.author.mention)
            await channel.send(response)

        # See if it's a custom command by checking the database
        elif content.startswith('>'):
            cursor = await self.bot.CONN.cursor()
            try:
                command_name = content[1:]
                command = await self.bot.get_custom_command(command_name)

                if command:
                    # Get ratelimit bucket
                    bucket = self.custom_command_cooldown.get_bucket(message)
                    retry_after = bucket.update_rate_limit() # Returns 0 for no ratelimit or > 0 for time left to wait

                    if not retry_after:
                        await channel.send(command.content)

                        # Increment usage by 1
                        update_command_query = dedent('''
                            UPDATE custom_commands
                            SET times_used = times_used + 1
                            WHERE id = ?;
                        '''.strip())
                        await cursor.execute(
                            update_command_query,
                            (command.id,)
                        )
                        await self.bot.CONN.commit()

                    else:
                        # This will be caught by our on_error handler
                        raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.guild)

            finally:
                await cursor.close()

        # update last message for channel and increment counter if its the same as last
        # respond if it has been the same 4x in a row
        elif content.startswith(('>', '.')) is False:
            d_content = self._last_messages[channel.id]['content']
            d_counter = self._last_messages[channel.id]['counter']

            # Message content not the same as last recorded
            # or no recorded content at all. We just set it
            # to the current
            if not d_content or content != d_content:
                d_content, d_counter = content, 1

            else:
                d_counter += 1
                if d_counter == 4:
                    await channel.send(content)

            # Update dict with (new) values
            self._last_messages[channel.id].update({
                'content': d_content,
                'counter': d_counter
            })


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        '''
        Called when a member joins a guild.
        - Brankobot will send a welcoming message if
          that server is small or big RLD Discord.
        '''
        guild = member.guild
        channel_id = None

        if guild.id == GuildType.big_rld.value:
            channel_id = BigRLDChannelType.general.value
        elif guild.id == GuildType.small_rld.value:
            channel_id = SmallRLDChannelType.general.value

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            response = random.choices(*zip(*self._join_responses.items()))[0]
            await channel.send(response.format(member.mention))


    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        '''
        Called when a member leaves a guild.
        - Bot will remove any reminders/birthdays
          associated with this user in this guild.
        '''
        logger = logging.getLogger('brankobot')
        logger.info(f'{member} left {member.guild}; removing reminders/birthday')
        text_channels = {tc.id for tc in member.guild.text_channels}

        cursor = await self.bot.CONN.cursor()
        try:
            # Removing reminders
            select_reminders_query = dedent('''
                SELECT *
                FROM reminders
                WHERE creator_id = ?;
            '''.strip())

            result = await cursor.execute(
                select_reminders_query,
                (member.id,)
            )
            rows = await result.fetchall()

            if rows:
                reminders = [Reminder(*r) for r in rows]
                for reminder in reminders:
                    if reminder.channel_id in text_channels:
                        await self.bot.delete_reminder(reminder)

            # Removing birthday
            birthday: Birthday = await self.bot.get_birthday(member.id)
            if member.guild.id == birthday.server_id:
                await self.bot.delete_birthday(member.id)

        finally:
            await cursor.close()


    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        '''
        Called for every attempted command invoke
        - Adds an invoke time for a command to calculate
          time it took to respond
        '''
        ctx.command.invoke_time = time.perf_counter()


    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        '''Called when a command successfully finished
        - Bot will log command usage to logging file
        '''
        logger = logging.getLogger('brankobot')
        logger.info(f'"{ctx.author}" used "{ctx.command.qualified_name}" in #{ctx.channel}')


    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        '''
        Called for every error raised inside of a command
        - Handles error by sending message with information'''
        if ctx.command:
            ctx.command.reset_cooldown(ctx)

        if isinstance(error, commands.CommandNotFound):
            return

        # birthday errors
        elif isinstance(error, BirthdayDoesntExist):
            exc = f'{error.user} has no birthday registered'

        elif isinstance(error, NoBirthdays):
            exc = 'No people have registered their birthday in this server'

        elif isinstance(error, NotAModerator):
            exc = 'Only moderators can remove birthdays from the database to prevent spamming'

        elif isinstance(error, BirthdayAlreadyRegistered):
            exc = f'You have already registered your birthday ({format_dt(error.birthday.date)}) in {self.bot.get_guild(error.birthday.server_id)}'

        # music errors
        elif isinstance(error, VoiceChannelError):
            if error.destination:
                exc = f'Couldn\'t connect to {error.destination.mention}: {error.message}'
            else:
                exc = error.message

        elif isinstance(error, NotPlaying):
            exc = 'I am not currently playing any music'

        elif isinstance(error, EmptyQueue):
            exc = 'The music queue is empty'

        elif isinstance(error, InvalidVolume):
            exc = f'{error.volume}% is not valid, pick a number between 0 and 100'

        # Reminder errors
        elif isinstance(error, NoTimeFound):
            exc = 'I couldn\'t find a time in your reminder. Use e.g "in 4 hours watch quickybaby" or "at 22:30 GMT+1 play stronghold with RLD"'

        elif isinstance(error, commands.CheckFailure):
            exc = 'You can only use `help` in #bot'

        elif isinstance(error, TimeTravelNotPossible):
            exc = f'You can\'t travel back in time {naturaldelta(datetime.datetime.now() - error.date)} 🙄'

        elif isinstance(error, ReminderDoesntExist):
            exc = f'The reminder {error.id} doesn\'t exist'

        elif isinstance(error, NoReminders):
            exc = 'You have no current running reminders'

        elif isinstance(error, NotReminderOwner):
            owner = ctx.bot.get_user(error.reminder.creator_id)
            exc = f'You don\'t own this reminder. It belongs to {owner}'

        # Custom command errors
        elif isinstance(error, CommandExists):
            exc = f'The command {error.command_name} command already exist'

        elif isinstance(error, CommandDoesntExist):
            exc = f'The command {error.command_name} command doesn\'t exist'

        elif isinstance(error, NotCommandOwner):
            owner = ctx.bot.get_user(error.command.creator_id)
            exc = f'You don\'t own this command. It belongs to {owner}'

        elif isinstance(error, NoCustomCommands):
            if error.user:
                exc = f'{error.user} doesn\'t own any custom commands'
            else:
                exc = 'Couldn\'t find any custom commands by your query'

        elif isinstance(error, InvalidCommandName):
            exc = 'You can\'t name your command this. Make sure its at least 1 character and at most 50 characters long, and consists of just latin characters / spaces / numbers'

        elif isinstance(error, InvalidCommandContent):
            exc = 'You can\'t have your command send this. Make sure the content is at most 500 chars long'

        # Other errors
        elif isinstance(error, aiosqlite.Error):
            await self.bot.CONN.rollback()
            await ctx.reply(f'Database had an error: {error} (<@764584777642672160>)', mention_author=False)
            raise error

        elif isinstance(error, ReplayError):
            exc = f'Something went wrong: {error.message}'

        elif isinstance(error, ChannelNotAllowed):
            allowed = ', '.join(list(filter(None, set([getattr(ctx.guild.get_channel(i), 'mention', None) for i in error.allowed_ids]))))
            exc = f'You can only use this command in: {allowed}'

        elif isinstance(error, MissingRoles):
            allowed = ', '.join(list(filter(None, set([getattr(ctx.guild.get_role(i), 'mention', None) for i in error.allowed_ids]))))
            exc = f'You are missing any of the following roles to use this command: {allowed}'

        elif isinstance(error, NotARegion):
            exc = f'The argument {error.region_argument} isn\'t a valid region. Choose eu/europe, na/america or ru/russia'

        elif isinstance(error, NoMoe):
            exc = f'The player {error.nickname} on region {error.region} hasn\'t achieved any marks of excellence'

        elif isinstance(error, InvalidNickname):
            exc = 'The input nickname must be between or equal to 3 to 24 characters, and should only contain letters and numbers'

        elif isinstance(error, InvalidFlags):
            exc = 'No data could be found with your flags'

        elif isinstance(error, PlayerNotFound):
            exc = f'The player {error.nickname} couldn\'t be found on region {error.region}'

        elif isinstance(error, InvalidClan):
            exc = 'The input clan tag/name must be between 2 to 20 characters, and should only contain letters, numbers and underscores'

        elif isinstance(error, ClanNotFound):
            exc = f'The clan {error.clan} couldn\'t be found on region {error.region}'

        elif isinstance(error, TankNotFound):
            exc = f'The tank {error.tank} couldn\'t be found'

        elif isinstance(error, ApiError):
            exc = f'WoT API failed: {error.http_code}: {error.error_message.replace("_", " ").capitalize()}'

        elif isinstance(error, commands.MissingAnyRole):
            exc = f'You are missing one of the required roles ({", ".join(error.missing_roles)}) to use this command :joy:'

        elif isinstance(error, commands.BadArgument):
            exc = f'Bad input argument(s): {error}'

        elif isinstance(error, commands.NotOwner):
            exc = 'You can\'t use this command'

        elif isinstance(error, commands.CommandOnCooldown):
            exc = f'The command is on cooldown ({error.type.name} scope). try again in {error.retry_after:.0f}s :joy:'

        elif isinstance(error, commands.MissingRequiredArgument):
            exc = f'You are missing a required argument: {error.param}'

        else:
            await ctx.reply(f'Something unexpected happened (mention buster if issue persists): {str(error)}', mention_author=False)
            raise error

        await ctx.reply(exc, delete_after=60, mention_author=False)

def setup(bot):
    bot.add_cog(Events(bot))
