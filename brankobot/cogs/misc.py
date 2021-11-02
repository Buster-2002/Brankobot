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

from main import __version__ as botversion
from .utils.checks import channel_check, role_check


class Misc(commands.Cog):
    '''Some misc commands'''

    def __init__(self, bot):
        self.bot = bot


    @commands.has_permissions(manage_messages=True)
    @commands.command()
    async def cleanup(self, ctx: commands.Context, search: int = 100):
        '''Deletes bot messages in current channel'''
        prefixes = tuple(await self.bot.get_prefix(ctx.message))
        def check(message: discord.Message):
            return message.author == self.bot.user or message.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
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
    async def ping(self, ctx: commands.Context):
        '''Resolves the websocket (API) latency and total message latency'''
        start = time.perf_counter()
        message = await ctx.send('`Resolving...`')
        end = time.perf_counter()
        msg = f'**Web socket latency:** {round(self.bot.latency * 1000)}ms\n**Total latency:** {(end - start) * 1000:.0f}ms'
        await message.edit(content=msg)


    @commands.is_owner()
    @commands.command(hidden=True)
    async def restart(self, ctx: commands.Context):
        '''Restarts brankobot'''
        await self.bot.CONN.commit()
        await self.bot.CONN.close()
        await ctx.send('Grabbing new spoon... (Restarting)')
        e = sys.executable
        os.execl(e, e, *sys.argv)


    @commands.is_owner()
    @commands.command(hidden=True)
    async def botlog(self, ctx: commands.Context):
        '''Sends bot log'''
        with open('brankobot.log', encoding='utf-8') as logfile:
            content = logfile.read()
            s = StringIO()
            s.write(content)
            s.seek(0)
            await ctx.send(file=discord.File(s, 'log.log'))


    @commands.is_owner()
    @commands.command(hidden=True)
    async def reload(self, ctx: commands.Context, module: str = None):
        if module:
            self.bot.reload_extension(module)
        else:
            for cog in list(self.bot.cogs.values()):
                self.bot.reload_extension(cog.__module__)

        await ctx.send(f'Reloaded {module or "all modules"}')


    @commands.is_owner()
    @commands.command(aliases=['memory', 'pinfo'])
    async def processinfo(self, ctx: commands.Context):
        '''Shows bot process info'''
        cursor = await self.bot.CONN.cursor()
        try:
            select_commands_query = dedent('''
                SELECT COUNT(*)
                FROM custom_commands
            '''.strip())

            rows = await cursor.execute(select_commands_query)
            cc_amount, = await rows.fetchone()
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

def setup(bot):
    bot.add_cog(Misc(bot))
