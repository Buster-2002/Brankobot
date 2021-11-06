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

from contextlib import suppress
from difflib import get_close_matches
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import List, Optional, Union

import discord
from discord.ext import commands
from discord.ext.menus.views import ViewMenuPages
from discord.utils import escape_markdown, format_dt
from youtube_dl.YoutubeDL import DownloadError, YoutubeDL

from .utils.checks import channel_check, is_moderator, role_check
from .utils.converters import CommandNameCheck, ReminderConverter
from .utils.enums import BigRLDRoleType, SmallRLDRoleType
from .utils.errors import (CommandDoesntExist, CommandExists,
                           InvalidCommandContent, NoCustomCommands,
                           NoReminders, NotCommandOwner, NotReminderOwner,
                           ReminderDoesntExist)
from .utils.models import CustomCommand, Reminder
from .utils.paginators import CustomCommandsPaginator, ReminderPaginator


# -- Cog -- #
class Utilities(commands.Cog):
    '''All the utility commands'''

    def __init__(self, bot):
        self.bot = bot


    @commands.cooldown(2, 60, commands.BucketType.user)
    @commands.command(aliases=['download', 'downloadmedia', 'uploadmedia'], usage='<link (works with [these](https://ytdl-org.github.io/youtube-dl/supportedsites.html) platform links)>')
    async def upload(self, ctx: commands.Context, link: str):
        '''Upload media like mp4/mp3 from link'''
        async with ctx.loading(initial_message='Downloading') as loader:
            temp_dir = TemporaryDirectory()
            ytdl_options = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'restrictfilenames': True,
                'format': f'best[filesize<{ctx.guild.filesize_limit}]',
                'outtmpl': f'{temp_dir.name}//%(id)s.%(ext)s'
            }
            try:
                meta = await self.bot.loop.run_in_executor(
                    None,
                    lambda: YoutubeDL(ytdl_options).extract_info(
                        link,
                        download=True
                    )
                )
            except DownloadError as e:
                await ctx.reply(f'Couldn\'t download: {e} (file too big?)', delete_after=60, mention_author=False)
            else:
                await loader.update('Uploading')
                ext = meta["ext"]
                await ctx.send(file=discord.File(
                    f'{temp_dir.name}/{meta["id"]}.{ext}',
                    f'{meta["title"]}.{ext}'
                ))


    @channel_check()
    @commands.cooldown(5, 60, commands.BucketType.guild)
    @commands.command(aliases=['info'])
    async def userinfo(self, ctx: commands.Context, user: Union[discord.Member, discord.User] = None):
        '''Shows some user information about a member or user'''
        user = user or ctx.author
        status_emotes = {
            str(discord.Status.offline): '⚫',
            str(discord.Status.dnd): '🔴',
            str(discord.Status.idle): '🟡'
        }
        desktop_status = status_emotes.get(str(user.desktop_status), '🟢')
        web_status = status_emotes.get(str(user.web_status), '🟢')
        mobile_status = status_emotes.get(str(user.mobile_status), '🟢')
        join_pos = sorted(ctx.guild.members, key=lambda m: m.joined_at).index(user) + 1
        join_outof = len(ctx.guild.members)
        flags = ', '.join([n.replace('_', ' ').title() for n, v in list(user.public_flags) if v])
        nick = user.display_name if user.display_name != user.name else None
        activity = user.activity if not getattr(user.activity, 'application_id', False) else None
        data = {
            'Name#tag': str(user),
            'ID': user.id,
            'Nickname': nick,
            'Joined': format_dt(user.joined_at, 'R'),
            'Created': format_dt(user.created_at, 'R'),
            'Join pos': f'{join_pos}th out of {join_outof} members' if join_pos else None,
            'Top role': user.top_role.name,
            'Status/activity': activity,
            'Desktop': desktop_status,
            'Web': web_status,
            'Mobile': mobile_status,
            'Flags': flags,
            'thumbnail': user.display_avatar
        }
        des = '\n'.join([(f'**{k}:** {v}') for k, v in data.items() if v and k != 'thumbnail'])
        await ctx.send_response(des, title='User Info', thumbnail=data.get('thumbnail'))


    @commands.group(
        'reminder',
        invoke_without_command=True,
        aliases=['remind', 'reminders'],
        usage='<reminder (should contain a loose interpretation of time, e.g "in 4 hours watch quickybaby" or "at 22:30, play stronghold with RLD")>'
    )
    async def _reminder(self, ctx: commands.Context, *, reminder: ReminderConverter):
        '''Creates a reminder from message'''
        extracted, ends_at = reminder
        cursor = await self.bot.CONN.cursor()
        try:
            args = (
                ctx.message.author.id,
                ctx.channel.id,
                ctx.message.jump_url,
                ctx.message.created_at.timestamp(),
                ends_at.timestamp(),
                extracted.replace('"', '""')
            )
            insert_reminder_query = dedent('''
                INSERT INTO reminders (
                    creator_id,
                    channel_id,
                    context_message_link,
                    creation_timestamp,
                    end_timestamp,
                    message
                ) VALUES (
                    ?, ?, ?, ?, ?, ?
                ) RETURNING id;
            '''.strip())

            result = await cursor.execute(
                insert_reminder_query,
                args
            )
            id = await result.fetchone()

            args = id + args
            reminder = Reminder(*args)
            msg = f'okay, {format_dt(reminder.ends_at, "R")}, I will remind you'
            if extracted:
                msg += f': {extracted}'

            await ctx.send_response(msg, title='Reminder added')
            await self.bot.CONN.commit()
            await self.bot.loop.create_task(self.bot.start_timer(reminder))

        finally:
            await cursor.close()

    @_reminder.command('list')
    async def _reminder_list(self, ctx: commands.Context):
        '''Lists your reminders'''
        cursor = await self.bot.CONN.cursor()
        try:
            select_reminders_query = dedent('''
                SELECT *
                FROM reminders
                WHERE creator_id = ?;
            '''.strip())

            result = await cursor.execute(
                select_reminders_query,
                (ctx.author.id,)
            )
            rows = await result.fetchall()

            if rows:
                reminders = [Reminder(*r) for r in rows]
                pages = ViewMenuPages(
                    source=ReminderPaginator(
                        reminders,
                        ctx
                    ), clear_reactions_after=True
                )
                await pages.start(ctx)

            else:
                raise NoReminders()

        finally:
            await cursor.close()

    @_reminder.command('remove', aliases=['delete', 'del'])
    async def _reminder_remove(self, ctx: commands.Context, id: int):
        '''Removes your reminder by its ID (see reminder list)'''
        reminder_task = self.bot.REMINDER_TASKS.get(id)
        if reminder_task is None:
            raise ReminderDoesntExist(id)

        msg = 'are you sure you want to remove this reminder?'
        reminder: Reminder = reminder_task['reminder']
        # Moderators can delete any reminder
        if is_moderator(ctx):
            msg = msg.rstrip('?')
            msg += f' belonging to {self.bot.get_user(reminder.creator_id)}?'
        else:
            if reminder.creator.id != ctx.author.id:
                raise NotReminderOwner(reminder)

        if not await ctx.confirm(msg):
            return

        await self.bot.delete_reminder(reminder)
        await ctx.send_response(
            f'Removed reminder with ID `{id}`',
            title='Reminder removed'
        )

    @_reminder.command('clear')
    async def _reminder_clear(self, ctx: commands.Context):
        '''Removes all your reminders'''
        cursor = await self.bot.CONN.cursor()
        try:
            select_reminders_query = dedent('''
                SELECT id
                FROM reminders
                WHERE creator_id = ?;
            '''.strip())
            
            result = await cursor.execute(
                select_reminders_query,
                (ctx.author.id,)
            )
            rows = await result.fetchall()

            if rows:
                reminders = [Reminder(*r) for r in rows]
                for reminder in reminders:
                    await self.bot.delete_reminder(reminder)

            else:
                raise NoReminders()

        finally:
            await cursor.close()


    @commands.cooldown(5, 15, commands.BucketType.user)
    @commands.group(invoke_without_command=True, aliases=['customcommand', 'tag'])
    async def cc(self, _):
        '''Base command for creating/renaming/deleting/showing custom commands'''

    @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    @cc.command('add', aliases=['make', 'create'])
    async def cc_add(self, ctx: commands.Context, command_name: CommandNameCheck, *, content: str):
        '''Creates a custom command'''
        if len(content) > 500:
            raise InvalidCommandContent()

        cursor = await self.bot.CONN.cursor()
        try:
            command = await self.bot.get_custom_command(command_name)
            if command is not None:
                raise CommandExists(command_name)

            insert_command_query = dedent('''
                INSERT INTO custom_commands (
                    creator_id,
                    creation_timestamp,
                    name,
                    content
                ) VALUES (
                    ?, ?, ?, ?
                );
            '''.strip())

            await cursor.execute(
                insert_command_query,
                (
                    ctx.message.author.id,
                    ctx.message.created_at.timestamp(),
                    command_name,
                    content
                )
            )
            await self.bot.CONN.commit()

            await ctx.send_response(
                f'okay, you can now use >{command_name}',
                title='Command Created'
            )

        finally:
            await cursor.close()

    @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    @cc.command('remove', aliases=['delete', 'del'])
    async def cc_remove(self, ctx: commands.Context, *, command_name: CommandNameCheck):
        '''Removes a custom command belonging to you'''
        cursor = await self.bot.CONN.cursor()
        try:
            command: CustomCommand = await self.bot.get_custom_command(command_name)
            if command is None:
                raise CommandDoesntExist(command_name)

            msg = 'are you sure you want to remove this command?'
            # Moderators can delete any custom command
            if is_moderator(ctx):
                msg = msg.rstrip('?')
                msg += f' belonging to {self.bot.get_user(command.creator_id)}?'
            else:
                if command.creator.id != ctx.author.id:
                    raise NotCommandOwner(command)

            if not await ctx.confirm(msg):
                return

            delete_command_query = dedent('''
                DELETE
                FROM custom_commands
                WHERE id = ?;
            '''.strip())

            await cursor.execute(
                delete_command_query,
                (command.id,)
            )
            await self.bot.CONN.commit()

            await ctx.send_response(
                f'removed command with name `{command_name}`',
                title='Command Removed'
            )

        finally:
            await cursor.close()

    @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    @cc.command('rename', aliases=['update'])
    async def cc_rename(self, ctx: commands.Context, command_name: CommandNameCheck, new_command_name: CommandNameCheck):
        '''Renames a custom command belonging to you'''
        cursor = await self.bot.CONN.cursor()
        try:
            command = await self.bot.get_custom_command(command_name)
            if command is None:
                raise CommandDoesntExist(command_name)

            command = await self.bot.get_custom_command(new_command_name)
            if command is not None:
                raise CommandExists(new_command_name)

            update_command_query = dedent('''
                UPDATE custom_commands
                SET name = ?
                WHERE name = ?;
            '''.strip())

            await cursor.execute(
                update_command_query,
                (
                    new_command_name,
                    command_name
                )
            )
            await self.bot.CONN.commit()

            await ctx.send_response(
                f'np, renamed `{command_name}` to `{new_command_name}`',
                title='Command Renamed'
            )

        finally:
            await cursor.close()

    @cc.command('info')
    async def cc_info(self, ctx: commands.Context, *, command_name: CommandNameCheck):
        '''Shows info about a custom command'''
        command = await self.bot.get_custom_command(command_name)
        if command is None:
            raise CommandDoesntExist(command_name)

        owner = self.bot.get_user(command.creator.id) or 'Unknown'
        await ctx.send_response(
            dedent(f'''
                **ID:** {command.id}
                **Name:** {escape_markdown(command_name)}
                **Created by:** {owner} ({getattr(owner, 'mention', 'N/A')})
                **Content length:** {len(command.content)} chars
                **Created:** {format_dt(command.created_at, 'R')}
                **Times used:** {command.times_used}
            '''.strip()),
            title='Command Info'
        )

    @cc.command('search', aliases=['find'])
    async def cc_search(self, ctx: commands.Context, cutoff: Optional[float] = 0.5, *, query: commands.clean_content):
        '''Searches for a custom command by query'''
        cursor = await self.bot.CONN.cursor()
        try:
            if not 0 <= cutoff <= 1:
                raise commands.BadArgument('Cutoff must be a number between 0 and 1')

            select_commands_query = dedent('''
                SELECT *
                FROM custom_commands
            '''.strip())

            result = await cursor.execute(select_commands_query)
            rows = await result.fetchall()

            custom_commands = [CustomCommand(*r) for r in rows]
            close_matches = get_close_matches(
                query,
                [c.name for c in custom_commands],
                n=100,
                cutoff=cutoff
            )

            if close_matches:
                custom_commands = [c for c in custom_commands if c.name in set(close_matches)]
                pages = ViewMenuPages(
                    source=CustomCommandsPaginator(
                        custom_commands,
                        ctx
                    ), clear_reactions_after=True
                )
                await pages.start(ctx)
            else:
                raise NoCustomCommands()

        finally:
            await cursor.close()

    @cc.command('list', aliases=['all'])
    async def cc_list(self, ctx: commands.Context, user: discord.User = None):
        '''Shows custom commands, optionally filtering by a user'''
        cursor = await self.bot.CONN.cursor()
        try:
            select_commands_query = dedent('''
                SELECT *
                FROM custom_commands
            '''.strip())
            if user:
                select_commands_query += '\nWHERE creator_id = {};'.format(user.id)
            else:
                select_commands_query += ';'

            result = await cursor.execute(select_commands_query)
            rows = await result.fetchall()

            if rows:
                custom_commands = [CustomCommand(*r) for r in rows]
                pages = ViewMenuPages(
                    source=CustomCommandsPaginator(
                        custom_commands,
                        ctx,
                        user
                    ), clear_reactions_after=True
                )
                await pages.start(ctx)
            else:
                raise NoCustomCommands(user)

        finally:
            await cursor.close()

def setup(bot):
    bot.add_cog(Utilities(bot))
