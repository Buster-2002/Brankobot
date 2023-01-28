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

import os
import sys
import time
from collections import Counter
from datetime import datetime
from io import StringIO
from textwrap import dedent

import discord
import psutil
from discord import __version__ as dcversion
from discord.ext import commands
from humanize import intcomma, naturalsize, precisedelta

from main import __version__ as botversion, Bot, Context
from .utils.checks import channel_check, role_check
from .utils.enums import BigRLDRoleType, SmallRLDRoleType, Emote, TikTokVoice, try_enum


class Misc(commands.Cog):
    '''Some misc commands'''

    def __init__(self, bot):
        self.bot: Bot = bot


    @commands.is_owner()
    @commands.command(aliases=['setsessionid', 'tiktokid'], hidden=True)
    async def tiktoksessionid(self, ctx: Context, sessionid: str):
        '''Sets the TikTok session id'''
        self.bot.TIKTOK_SESSIONID = sessionid
        await ctx.send(f'{Emote.socialcredit}')


    @role_check(BigRLDRoleType.xo, SmallRLDRoleType.xo, BigRLDRoleType.po, SmallRLDRoleType.po, BigRLDRoleType.ro, SmallRLDRoleType.ro)
    @commands.command()
    async def cleanup(self, ctx: Context, limit: int = 100):
        '''Deletes bot messages in current channel'''
        prefixes = tuple(await self.bot.get_prefix(ctx.message))
        def check(message: discord.Message):
            return message.author == self.bot.user or message.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=limit, check=check, before=ctx.message)
        counter = Counter([m.author.mention for m in deleted])
        amount_deleted = sum(counter.values())

        messages = [f'{amount_deleted} message{"s"[:amount_deleted^1]} removed.\n']
        if amount_deleted:
            messages.extend([
                f'**{author}:** {count}'
                for author, count in sorted(
                    counter.items(),
                    key=lambda t: t[1],
                    reverse=True
                )
            ])

        await ctx.send_response('\n'.join(messages), delete_after=15)


    @channel_check()
    @role_check()
    @commands.cooldown(5, 60, commands.BucketType.guild)
    @commands.command()
    async def ping(self, ctx: Context):
        '''Resolves the websocket (API) latency and total message latency'''
        start = time.perf_counter()
        message = await ctx.send('`Resolving...`')
        end = time.perf_counter()
        msg = f'**Web socket latency:** {round(self.bot.latency * 1000)}ms\n**Total latency:** {(end - start) * 1000:.0f}ms'
        await message.edit(content=msg)


    @commands.is_owner()
    @commands.command(hidden=True)
    async def restart(self, ctx: Context):
        '''Restarts brankobot'''
        await self.bot.CONN.commit()
        await self.bot.CONN.close()
        await ctx.send('Grabbing new spoon... (Restarting)')
        e = sys.executable
        os.execl(e, e, *sys.argv)


    @commands.is_owner()
    @commands.command(hidden=True)
    async def botlog(self, ctx: Context):
        '''Sends bot log'''
        with open('brankobot.log', encoding='utf-8') as logfile:
            content = logfile.read()
            s = StringIO()
            s.write(content)
            s.seek(0)
            await ctx.send(file=discord.File(s, 'log.log'))


    @commands.is_owner()
    @commands.command(hidden=True)
    async def reload(self, ctx: Context, module: str = None):
        if module:
            await self.bot.reload_extension(module)
        else:
            for cog in list(self.bot.cogs.values()):
                await self.bot.reload_extension(cog.__module__)

        await ctx.send(f'Reloaded {module or "all modules"}')


    @commands.is_owner()
    @commands.command(aliases=['memory', 'pinfo'])
    async def processinfo(self, ctx: Context):
        '''Shows bot process info'''
        cursor = await self.bot.CONN.cursor()
        try:
            select_commands_query = dedent('''
                SELECT COUNT(*)
                FROM custom_commands
            '''.strip())

            result = await cursor.execute(select_commands_query)
            cc_amount, = await result.fetchone()
            
            start = time.perf_counter()
            resolve_message = await ctx.send('`Resolving...`')
            end = time.perf_counter()
            process = psutil.Process(os.getpid())
            mem = process.memory_info()
            c_amount = len(self.bot.commands)
            sc_amount = sum([(len(c.commands)) for c in self.bot.commands if isinstance(c, commands.Group)])

            msg = f'Processinfo | pid {process.pid}'
            fields = [
                ('Loaded', f'Commands: {c_amount}\nSubcommands: {sc_amount}\nCustomcommands: {cc_amount}\nTotal: {cc_amount + c_amount + sc_amount}\nCogs: {len(self.bot.cogs)}'),
                ('Versions', f'Selfbot: {botversion}\nPython: {".".join(map(str, sys.version_info[0:3]))}\ndiscord.py: {dcversion}'),
                ('Latencies', f'WS: {self.bot.latency * 1000:.2f}ms\nREST: {(end - start) * 1000:.2f}ms'),
                ('Usages', f'Phys. mem: {naturalsize(mem.rss)}\nVirt. mem: {naturalsize(mem.vms)}\nCPU: {process.cpu_percent():.2f}%\nThreads: {process.num_threads()}'),
                ('Events', f"Raw send: {intcomma(self.bot.SOCKET_STATS['RAW_SEND'])}\nRaw received: {intcomma(self.bot.SOCKET_STATS['RAW_RECEIVED'])}"),
                ('Uptime', precisedelta(datetime.now() - self.bot.START_TIME, format='%0.0f'))
            ]
            await resolve_message.delete()
            await ctx.send_response(msg, fields=fields)

        finally:
            await cursor.close()


    @commands.is_owner()
    @commands.group('voice', aliases=['tiktokvoice'], invoke_without_command=True)
    async def voice(self, _: Context):
        '''Commands for the bot's voice'''

    @commands.is_owner()
    @voice.command('set', aliases=['change', 'update'])
    async def voice_set(self, ctx: Context, voice: commands.clean_content):
        '''Set the voice of the bot'''
        self.bot.TIKTOK_VOICE = voice
        await ctx.send(f'Ofcourse, my liege {Emote.socialcredit.value} tiktok voice is set to {try_enum(TikTokVoice, voice)}')

    @commands.is_owner()
    @voice.command('reset', aliases=['default', 'clear'])
    async def voice_reset(self, ctx: Context):
        '''Reset the voice of the bot to the default'''
        self.bot.TIKTOK_VOICE = self.bot.TIKTOK_VOICE
        await ctx.send(f'Ofcourse, my liege {Emote.socialcredit.value}')

    @voice.command('current', aliases=['show', 'get'])
    async def voice_current(self, ctx: Context):
        '''Get the current voice of the bot'''
        await ctx.send(f'Current (tiktok) voice: {try_enum(TikTokVoice, self.bot.TIKTOK_VOICE)} ({self.bot.TIKTOK_VOICE})')


    @commands.is_owner()
    @commands.group('personality', invoke_without_command=True)
    async def personality(self, _: Context):
        '''Commands for the bot personality'''

    @commands.is_owner()
    @personality.command('set', aliases=['change', 'update'])
    async def personality_set(self, ctx: Context, *, personality: commands.clean_content):
        '''Set the personality of the bot'''
        self.bot.PERSONALITY = personality
        await ctx.send(f'Ofcourse, my liege {Emote.socialcredit.value}')

    @commands.is_owner()
    @personality.command('reset', aliases=['default', 'clear'])
    async def personality_reset(self, ctx: Context):
        '''Reset the personality of the bot to the default'''
        self.bot.PERSONALITY = self.bot.DEFAULT_PERSONALITY
        await ctx.send(f'Ofcourse, my liege {Emote.socialcredit.value}')

    @personality.command('current', aliases=['show', 'get'])
    async def personality_current(self, ctx: Context):
        '''Get the current personality of the bot'''
        await ctx.send(f'Current personality: {self.bot.PERSONALITY}')

async def setup(bot):
    await bot.add_cog(Misc(bot))
