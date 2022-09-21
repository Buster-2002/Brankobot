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

from collections import Counter
from difflib import get_close_matches
from functools import partial
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Optional, Union

import discord
from discord.ext import commands
from discord.ext.menus.views import ViewMenuPages
from discord.utils import escape_markdown, format_dt
from humanize import ordinal
from humanize.filesize import naturalsize
from youtube_dl.YoutubeDL import DownloadError, YoutubeDL

from main import Bot, Context
from .utils.checks import channel_check, is_moderator, role_check
from .utils.converters import CommandNameCheck, ReminderConverter
from .utils.enums import BigRLDRoleType, Emote, SmallRLDRoleType, try_enum
from .utils.errors import (CommandDoesntExist, CommandExists,
                           InvalidCommandContent, NoCustomCommands,
                           NoReminders, NotCommandOwner, NotReminderOwner,
                           ReminderDoesntExist, AlreadyBlacklisted, NotBlacklisted, NoBlacklistedUsers)
from .utils.models import BlacklistedUser, CustomCommand, Reminder
from .utils.paginators import CustomCommandsPaginator, ReminderPaginator, BlacklistPaginator


class Utilities(commands.Cog):
    '''All the utility commands'''

    def __init__(self, bot):
        self.bot: Bot = bot


    @commands.cooldown(2, 60, commands.BucketType.user)
    @commands.command(aliases=['download', 'downloadmedia', 'uploadmedia'], usage='<link (works with [these](https://ytdl-org.github.io/youtube-dl/supportedsites.html) platform links)>')
    async def upload(self, ctx: Context, link: str):
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
                to_run = partial(YoutubeDL(ytdl_options).extract_info, url=link, download=True)
                meta = await self.bot.loop.run_in_executor(None, to_run)
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
    @commands.command(aliases=['server', 'guild', 'guildinfo'])
    async def serverinfo(self, ctx: Context, server: discord.Guild = None):
        '''Shows information about a server'''
        guild = server or ctx.guild
        owner = guild.owner.mention if guild.owner else 'No owner'
        special_channels = [
            (f'{Emote.voice_channel} AFK', guild.afk_channel),
            (f'{Emote.text_channel} System', guild.system_channel),
            (f'{Emote.rules} Rules', guild.rules_channel),
            (f'{Emote.announcement} Updates', guild.public_updates_channel)
        ]
        if data := list(filter(lambda item: item[1] is not None, special_channels)):
            special_channels = '\n'.join([f'{c[0]}: {c[1].mention}' for c in data])

        members = dedent(f'''
            {Emote.silhouette} Humans: {len([m for m in guild.members if m.bot is False])}
            {Emote.robot} Bots: {len([m for m in guild.members if m.bot is True])}
            {Emote.total} Total: {len(guild.members)}
            {Emote.admin} Admins: {len([m for m in guild.members if m.public_flags.staff])}
        ''')

        status_counter = Counter([m.status for m in guild.members])
        member_statuses = dedent(f'''
            {Emote.online} Online: {status_counter.get(discord.Status.online, 0)}
            {Emote.idle} Idle: {status_counter.get(discord.Status.idle, 0)}
            {Emote.dnd} DND: {status_counter.get(discord.Status.dnd, 0)}
            {Emote.offline} Offline: {status_counter.get(discord.Status.offline, 0)}
        ''')

        channel_counter = Counter([type(c).__name__ for c in guild.channels])
        channels = dedent(f'''
            {Emote.category_channel} Category: {channel_counter.get('CategoryChannel', 0)}
            {Emote.text_channel} Text: {channel_counter.get('TextChannel', 0)}
            {Emote.voice_channel} Voice: {channel_counter.get('VoiceChannel', 0)}
            {Emote.stage_channel} Stage: {channel_counter.get('StageChannel', 0)}
        ''')

        subscribers = sorted(guild.premium_subscribers, key=lambda m: m.premium_since)
        latest_sub = 'N/A'
        if subscribers:
            latest_sub = 'by ' + subscribers[-1].mention
        boosts = dedent(f'''
            {Emote.boost} Boosts: {guild.premium_subscription_count}
            {try_enum(Emote, f'boost_{guild.premium_tier}')} Tier: {guild.premium_tier}
            {Emote.role} Role: {guild.premium_subscriber_role or 'N/A'}
            {Emote.silhouette} Latest: {latest_sub}
        ''')

        emotes = dedent(f'''
            {Emote.blank_emoji} Static: {len([e for e in guild.emojis if e.animated is False])}
            {Emote.blank_emoji_rotate} Animated: {len([e for e in guild.emojis if e.animated is True])}
            {Emote.sticker} Stickers: {len(guild.stickers)}
            {Emote.warning} Limit: {guild.emoji_limit}/{guild.sticker_limit}
        ''')

        fields = [
            ('Name', guild.name),
            ('Owner', f'{Emote.silhouette} {owner}'),
            ('ID', f'{Emote.ID} {str(guild.id)[:10]}\n{str(guild.id)[10:]}'),

            ('Created', f'{Emote.created} {format_dt(guild.created_at, "R")}'),
            ('Roles', f'{Emote.role} {len(guild.roles)}'),
            ('Locale', f'{Emote.location} {str(guild.preferred_locale)}'),

            ('Filesize limit', f'{Emote.upload} {naturalsize(guild.filesize_limit)}'),
            ('Content filter', f'{Emote.locked_channel} {str(guild.explicit_content_filter).replace("_", " ").title()}'),
            ('Verification level', f'{Emote.verified} {str(guild.verification_level).title()}'),

            ('Members', members),
            ('Statuses', member_statuses),
            ('Boosts', boosts),

            ('Channels', channels),
            ('Special channels', special_channels),
            ('Emotes', emotes)
        ]

        await ctx.send_response(
            guild.description,
            title='Server Info',
            thumbnail=guild.icon,
            image=guild.banner,
            fields=fields
        )


    @channel_check()
    @commands.cooldown(5, 60, commands.BucketType.guild)
    @commands.command(aliases=['user', 'member', 'memberinfo'])
    async def userinfo(self, ctx: Context, user: Union[discord.Member, discord.User] = None):
        '''Shows information about a server member or discord user'''
        user = user or ctx.author
        join_pos = sorted(ctx.guild.members, key=lambda m: m.joined_at).index(user) + 1
        flags = ', '.join([n.replace('_', ' ').title() for n, v in list(user.public_flags) if v])
        nick = user.display_name if user.display_name != user.name else 'No nickname'
        boosting_since = format_dt(user.premium_since, 'R') if user.premium_since else 'Not boosting'
        mutual_guilds = ', '.join([g.name for g in user.mutual_guilds])
        is_bot = 'no' if user.bot is False else 'yes'
        is_afk, vc = 'no', None
        if user.voice:
            if vc := user.voice.channel:
                if vc == ctx.guild.afk_channel:
                    is_afk = 'yes'

        # Don't show RPC activity by checking if an application ID is present
        activity = user.activity if not getattr(user.activity, 'application_id', False) else 'No activity'
        if user.guild_permissions == discord.Permissions.all():
            permissions = 'All permissions (administrator)'
        else:
            permissions = ', '.join([p.replace('_', ' ').title() for p, v in list(user.guild_permissions) if v]) if user.guild_permissions != discord.Permissions.none() else 'No permissions'
        roles = ', '.join([r.name for r in user.roles[1:]]) if user.roles[1:] else 'No roles'
        status_emotes = {
            discord.Status.offline: (Emote.offline, 'Offline'),
            discord.Status.dnd: (Emote.dnd, 'DND'),
            discord.Status.idle: (Emote.idle, 'Idle'),
            discord.Status.online: (Emote.online, 'Online')
        }
        desktop_status = status_emotes.get(user.desktop_status)
        web_status = status_emotes.get(user.web_status)
        mobile_status = status_emotes.get(user.mobile_status)

        fields = [
            ('User', f'{Emote.silhouette} {user.mention}'),
            ('Nickname', nick),
            ('ID', f'{Emote.ID} {str(user.id)[:10]}\n{str(user.id)[10:]}'),

            ('Created', f'{Emote.created} {format_dt(user.created_at, "R")}'),
            ('Joined', f'{Emote.joined} {format_dt(user.joined_at, "R")} ({ordinal(join_pos)} out of {ctx.guild.member_count})'),
            ('Bot / AFK', f'{Emote.robot} {is_bot} / {Emote.zzz} {is_afk}'),

            ('Boosting', f'{Emote.boost} {boosting_since}'),
            ('Mutual servers', f'{Emote.server_discovery} {mutual_guilds}'),
            ('Voice', f'{Emote.voice_channel} {vc.mention if vc else "Not connected"}'),

            ('Status', f'{desktop_status[0]} Desktop: {desktop_status[1]}\n{web_status[0]} Web: {web_status[1]}\n{mobile_status[0]} Mobile: {mobile_status[1]}'),
            ('Activity', f'{Emote.activity} {activity}'),
            ('Flags', f'{Emote.flags} {flags}'),
            ('Permissions', f'{Emote.permission} {permissions}'),
            ('Roles', f'{Emote.role} {roles}')
        ]

        await ctx.send_response(
            title='User Info',
            fields=fields,
            thumbnail=str(user.display_avatar),
            image=user.banner
        )

    
    @role_check(BigRLDRoleType.xo)
    @commands.group(
        'blacklist',
        invoke_without_command=True,
        aliases=['jewlist'],
    )
    async def blacklist(self, _):
        '''Base command for blacklisting/unblacklisting/listing users'''

    @role_check(BigRLDRoleType.xo)
    @blacklist.command('add', aliases=['append'])
    async def blacklist_add(self, ctx: Context, user: Union[discord.User, discord.Object]):
        '''Adds a user to the blacklist which blocks them from using the bot'''
        cursor = await self.bot.CONN.cursor()
        try:
            blacklisted_user = await self.bot.get_blacklisted_user(user.id)
            if blacklisted_user is not None:
                raise AlreadyBlacklisted(user.id)

            insert_blacklisted_user_query = dedent('''
                INSERT INTO blacklisted_users (
                    user_id,
                    blacklisted_at_timestamp,
                    blacklisted_by_id
                ) VALUES (
                    ?, ?, ?
                );
            '''.strip())

            await cursor.execute(
                insert_blacklisted_user_query,
                (
                    user.id,
                    ctx.message.created_at.timestamp(),
                    ctx.author.id
                )
            )
            await self.bot.CONN.commit()

            await ctx.send_response(
                f'okay, the user {user.mention} (with ID {user.id}) is now ignored completely by brankobot',
                title='User Blacklisted'
            )

        finally:
            await cursor.close()

    @role_check(BigRLDRoleType.xo)
    @blacklist.command('remove', aliases=['delete'])
    async def blacklist_remove(self, ctx: Context, user: Union[discord.User, discord.Object]):
        '''Removes a user from the blacklist which allows them to use the bot again'''
        cursor= await self.bot.CONN.cursor()
        try: 
            blacklisted_user = await self.bot.get_blacklisted_user(user.id)
            if blacklisted_user is None:
                raise NotBlacklisted(user.id)

            if not await ctx.confirm(f'are you sure you want to remove {user} from the blacklist?'):
                return

            delete_blacklisted_user_query = dedent('''
                DELETE
                FROM blacklisted_users
                WHERE id = ?;
            '''.strip())

            await cursor.execute(
                delete_blacklisted_user_query,
                (blacklisted_user.id,)
            )
            await self.bot.CONN.commit()

            await ctx.send_response(
                f'removed {user} from brankobots blacklist',
                title='User Unblacklisted'
            )

        finally:
            await cursor.close()

    @blacklist.command('list', aliases=['all', 'show'])
    async def blacklist_list(self, ctx: Context):
        '''Lists all users that are on the brankobot blacklist'''
        cursor = await self.bot.CONN.cursor()
        try:
            select_blacklisted_users_query = dedent('''
                SELECT *
                FROM blacklisted_users
            '''.strip())

            result = await cursor.execute(select_blacklisted_users_query)
            rows = await result.fetchall()

            if rows:
                blacklisted_users = [BlacklistedUser(*r) for r in rows]
                sorted_data = sorted(
                    blacklisted_users,
                    key=lambda item: item.blacklisted_at,
                    reverse=True
                )
                pages = ViewMenuPages(
                    source=BlacklistPaginator(
                        sorted_data,
                        ctx
                    ), clear_reactions_after=True
                )
                await pages.start(ctx)

            else:
                raise NoBlacklistedUsers()

        finally:
            await cursor.close()
        

    @commands.group(
        'reminder',
        invoke_without_command=True,
        aliases=['remind', 'reminders'],
        usage='<reminder (should contain a loose interpretation of time, e.g "in 4 hours watch quickybaby" or "at 22:30, play stronghold with TAF-G")>'
    )
    async def _reminder(self, ctx: Context, *, reminder: ReminderConverter):
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

    @_reminder.command('list', aliases=['all', 'show'])
    async def _reminder_list(self, ctx: Context):
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
    async def _reminder_remove(self, ctx: Context, id: int):
        '''Removes your reminder by its ID (see reminder list)'''
        reminder_task = self.bot.REMINDER_TASKS.get(id)
        if reminder_task is None:
            raise ReminderDoesntExist(id)

        msg = 'are you sure you want to remove this reminder?'
        reminder: Reminder = reminder_task['reminder']
        # Moderators can delete any reminder
        if await is_moderator(ctx):
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
            title='Reminder Removed'
        )

    @_reminder.command('clear')
    async def _reminder_clear(self, ctx: Context):
        '''Removes all your reminders'''
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
                for reminder in reminders:
                    await self.bot.delete_reminder(reminder)

                await ctx.send_response(
                    f'Removed {len(reminders)} reminders',
                    title='Cleared Reminders'
                )

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
    async def cc_add(self, ctx: Context, command_name: CommandNameCheck, *, content: str):
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
    async def cc_remove(self, ctx: Context, *, command_name: CommandNameCheck):
        '''Removes a custom command belonging to you'''
        cursor = await self.bot.CONN.cursor()
        try:
            command = await self.bot.get_custom_command(command_name)
            if command is None:
                raise CommandDoesntExist(command_name)

            msg = 'are you sure you want to remove this command?'
            # Moderators can delete any custom command
            if await is_moderator(ctx):
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
    async def cc_rename(self, ctx: Context, command_name: CommandNameCheck, new_command_name: CommandNameCheck):
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
    async def cc_info(self, ctx: Context, *, command_name: CommandNameCheck):
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
    async def cc_search(self, ctx: Context, cutoff: Optional[float] = 0.5, *, query: commands.clean_content):
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

    @cc.command('list', aliases=['all', 'show'])
    async def cc_list(self, ctx: Context, user: discord.User = None):
        '''Shows custom commands sorted by usage, optionally filtering by a user'''
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
                sorted_data = sorted(
                    custom_commands,
                    key=lambda item: item.times_used,
                    reverse=True
                )
                pages = ViewMenuPages(
                    source=CustomCommandsPaginator(
                        sorted_data,
                        ctx,
                        user
                    ), clear_reactions_after=True
                )
                await pages.start(ctx)

            else:
                raise NoCustomCommands(user)

        finally:
            await cursor.close()

async def setup(bot):
    await bot.add_cog(Utilities(bot))
