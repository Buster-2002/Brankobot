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
from io import StringIO

import discord
from discord.ext import commands

from .utils.checks import channel_check, role_check


class Misc(commands.Cog):
    '''Some misc commands'''

    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(manage_messages=True)
    @commands.command()
    async def cleanup(self, ctx, search: int = 100):
        '''Deletes bot messages in current channel'''
        prefixes = tuple(await self.bot.get_prefix(ctx.message))
        def check(message: discord.Message):
            return message.author == self.bot.user or message.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        counter = Counter([m.author.display_name for m in deleted])
        amount_deleted = sum(counter.values())

        messages = [f'{amount_deleted} message{"s"[:amount_deleted^1]} removed.']
        if amount_deleted:
            messages.append('')
            spammers = sorted(counter.items(), key=lambda t: t[1], reverse=True)
            messages.extend([f'**{author}:** {count}' for author, count in spammers])

        await ctx.send_response('\n'.join(messages), delete_after=15)


    @channel_check()
    @role_check()
    @commands.cooldown(5, 60, commands.BucketType.guild)
    @commands.command()
    async def ping(self, ctx):
        '''Resolves the websocket (API) latency and total message latency'''
        start = time.perf_counter()
        message = await ctx.send('`Resolving...`')
        end = time.perf_counter()
        msg = f'**Web socket latency:** {round(self.bot.latency * 1000)}ms\n**Total latency:** {(end - start) * 1000:.0f}ms'
        await message.edit(content=msg)


    @commands.is_owner()
    @commands.command(hidden=True)
    async def restart(self, ctx):
        '''Restarts brankobot'''
        await self.bot.CONN.close()
        await ctx.send('Grabbing new spoon... (Restarting)')
        e = sys.executable
        os.execl(e, e, *sys.argv)


    @commands.is_owner()
    @commands.command(hidden=True)
    async def botlog(self, ctx):
        '''Sends bot log'''
        with open('brankobot.log', encoding='utf-8') as logfile:
            content = logfile.read()
            s = StringIO()
            s.write(content)
            s.seek(0)
            await ctx.send(file=discord.File(s, 'log.log'))


    @commands.is_owner()
    @commands.command(hidden=True)
    async def reload(self, ctx, module: str = None):
        if module:
            self.bot.reload_extension(module)
        else:
            for cog in list(self.bot.cogs.values()):
                self.bot.reload_extension(cog.__module__)

        await ctx.send(f'Reloaded {module or "all modules"}')


def setup(bot):
    bot.add_cog(Misc(bot))
