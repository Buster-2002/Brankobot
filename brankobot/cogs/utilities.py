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
from datetime import datetime
from difflib import get_close_matches
from textwrap import dedent
from typing import List, Optional, Union

import discord
from discord.ext import commands
from discord.ext.menus.views import ViewMenuPages
from discord.utils import escape_markdown, format_dt

from .utils.checks import channel_check, role_check
from .utils.converters import CommandNameCheck, DateConverter
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


    @staticmethod
    def _is_moderator(roles: List[discord.Role]) -> bool:
        '''Checks whether roles contain any mod roles

        Args:
            roles (List[discord.Role]): The list of roles to check for mod roles

        Returns:
            bool: True if the roles contain mod roles, False if they don't
        '''
        moderator_roles = {
            BigRLDRoleType.xo,
            SmallRLDRoleType.xo,
            BigRLDRoleType.po,
            SmallRLDRoleType.po,
            BigRLDRoleType.co,
            SmallRLDRoleType.co
        }
        allowed_ids = {mr.value for mr in moderator_roles}
        return any([r.id in allowed_ids for r in roles])


    @channel_check()
    @commands.cooldown(5, 60, commands.BucketType.guild)
    @commands.command(aliases=['info'])
    async def userinfo(self, ctx, user: Union[discord.Member, discord.User] = None):
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
    async def _reminder(self, ctx, *, reminder: DateConverter):
        '''Creates a reminder from message'''
        extracted, ends_at = reminder
        cursor = await self.bot.CONN.cursor()
        try:
            args = (
                ctx.message.author.id,
                ctx.channel.id,
                ctx.message.jump_url,
                datetime.timestamp(ctx.message.created_at),
                datetime.timestamp(ends_at),
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

            rows = await cursor.execute(
                insert_reminder_query,
                args
            )
            id = await rows.fetchone()
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
    async def _reminder_list(self, ctx):
        '''Lists your reminders'''
        cursor = await self.bot.CONN.cursor()
        try:
            select_reminders_query = dedent('''
                SELECT *
                FROM reminders
                WHERE creator_id = ?;
            '''.strip())

            rows = await cursor.execute(
                select_reminders_query,
                (ctx.author.id,)
            )
            if rows := await rows.fetchall():
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
    async def _reminder_remove(self, ctx, id: int):
        '''Removes your reminder by its ID (see reminder list)'''
        cursor = await self.bot.CONN.cursor()
        try:
            reminder_task = self.bot.REMINDER_TASKS.get(id)
            if reminder_task is None:
                raise ReminderDoesntExist(id)

            reminder = reminder_task['reminder']
            if not self._is_moderator(ctx.author.roles):
                if reminder.creator.id != ctx.author.id:
                    raise NotReminderOwner(reminder)

            with suppress(Exception):
                task = reminder_task['task']
                task.cancel()

            await self.bot.delete_reminder(reminder)
            await ctx.send_response(
                f'Removed reminder `{id}`.',
                title='Reminder removed'
            )

        finally:
            await cursor.close()

    @_reminder.command('clear')
    async def _reminder_clear(self, ctx):
        '''Removes all your reminders'''
        cursor = await self.bot.CONN.cursor()
        try:
            delete_reminders_query = dedent('''
                DELETE
                FROM reminders
                WHERE creator_id = ?
                RETURNING id;
            '''.strip())

            rows = await cursor.execute(
                delete_reminders_query,
                (ctx.author.id,)
            )
            if rows := await rows.fetchall():
                for reminder_id in rows:
                    with suppress(Exception):
                        reminder_task = self.bot.REMINDER_TASKS[reminder_id]['task']
                        reminder_task.cancel()
                        self.bot.REMINDER_TASKS.pop(reminder_id)

                await ctx.send_response(
                    f'Cleared {len(rows)} reminders',
                    title='Cleared Reminders'
                )
            else:
                raise NoReminders()

        finally:
            await cursor.close()

    @commands.cooldown(5, 15, commands.BucketType.user)
    @commands.group(invoke_without_command=True, aliases=['customcommand', 'tag'])
    async def cc(self, _):
        '''Base command for the custom commands'''

    @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    @cc.command('add', aliases=['make', 'create'])
    async def cc_add(self, ctx, command_name: CommandNameCheck, *, content: str):
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
                ) VALUES (?, ?, ?, ?);
            '''.strip())

            await cursor.execute(
                insert_command_query,
                (
                    ctx.message.author.id,
                    datetime.timestamp(ctx.message.created_at),
                    command_name,
                    content
                )
            )
            await self.bot.CONN.commit()
            await ctx.send_response(
                f'Created command `{command_name}`.',
                title='Command Created'
            )

        finally:
            await cursor.close()

    @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    @cc.command('remove', aliases=['delete', 'del'])
    async def cc_remove(self, ctx, *, command_name: CommandNameCheck):
        '''Removes a custom command belonging to you'''
        cursor = await self.bot.CONN.cursor()
        try:
            command = await self.bot.get_custom_command(command_name)
            if command is None:
                raise CommandDoesntExist(command_name)

            # Exclude moderators from this check
            if not self._is_moderator(ctx.author.roles):
                if command.creator.id != ctx.author.id:
                    raise NotCommandOwner(command)

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
                f'Removed command `{command_name}`.',
                title='Command Removed'
            )

        finally:
            await cursor.close()

    @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    @cc.command('rename', aliases=['update'])
    async def cc_rename(self, ctx, command_name: CommandNameCheck, new_command_name: CommandNameCheck):
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
                f'Renamed command `{command_name}` to `{new_command_name}`.',
                title='Command Renamed'
            )

        finally:
            await cursor.close()

    @cc.command('info')
    async def cc_info(self, ctx, *, command_name: CommandNameCheck):
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
    async def cc_search(self, ctx, cutoff: Optional[float] = 0.5, *, query: commands.clean_content):
        '''Searches for a custom command by query'''
        cursor = await self.bot.CONN.cursor()
        try:
            if not 0 <= cutoff <= 1:
                raise commands.BadArgument('Cutoff must be a number between 0 and 1')

            select_commands_query = dedent('''
                SELECT *
                FROM custom_commands
            '''.strip())
            rows = await cursor.execute(select_commands_query)
            rows = await rows.fetchall()
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
    async def cc_list(self, ctx, user: discord.User = None):
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

            rows = await cursor.execute(select_commands_query)
            if rows := await rows.fetchall():
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
