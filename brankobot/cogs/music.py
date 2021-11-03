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

import asyncio
import time
from contextlib import suppress
from datetime import datetime
from functools import partial
from textwrap import dedent

import discord
from async_timeout import timeout
from discord.ext import commands
from discord.ext.menus.views import ViewMenuPages
from humanize import intcomma
from youtube_dl import YoutubeDL

from .utils.enums import Emote
from .utils.checks import channel_check, is_connected, role_check
from .utils.errors import (EmptyQueue, InvalidVolume, NotPlaying,
                           VoiceChannelError)
from .utils.paginators import MusicQueuePaginator

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
YTDL = YoutubeDL(YTDL_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source: discord.AudioSource, *, data: dict, requester: discord.Member):
        super().__init__(source)
        self.requester = requester
        self.title = data.get('title')
        self.webpage_url = data.get('webpage_url')
        self.duration = data.get('duration')
        self.view_count = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        self.thumbnail = data.get('thumbnails', [{'url': None}])[0]['url']
        self.upload_date = datetime.strptime(data.get('upload_date'), '%Y%m%d')


    @classmethod
    async def create_source(
        cls,
        ctx: commands.Context,
        search: str,
        *,
        loop: asyncio.BaseEventLoop,
        download: bool = False
    ) -> 'YTDLSource':
        loop = loop or asyncio.get_event_loop()
        to_run = partial(YTDL.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            data = data['entries'][0]

        msg = dedent(f'''
            **Added:** [{data["title"]}]({data["webpage_url"]}) to music queue

            *Use {ctx.prefix}queue for more info*
        ''')

        await ctx.send_response(
            msg,
            delete_after=15,
            thumbnail=data['thumbnails'][0]['url'],
            show_invoke_speed=False,
            title='Added To Queue'
        )

        if download:
            source = YTDL.prepare_filename(data)
        else:
            return {
                'title': data.get('title'),
                'webpage_url': data.get('webpage_url'),
                'duration': data.get('duration'),
                'view_count': data.get('view_count'),
                'likes': data.get('like_count'),
                'dislikes': data.get('dislike_count'),
                'uploader': data.get('uploader'),
                'uploader_url': data.get('uploader_url'),
                'upload_date': datetime.strptime(data.get('upload_date'), '%Y%m%d'),
                'thumbnail': data['thumbnails'][0]['url'],
                'requester': ctx.author,
            }

        return cls(
            discord.FFmpegPCMAudio(source),
            data=data,
            requester=ctx.author
        )


    @classmethod
    async def regather_stream(cls, data: dict, *, loop: asyncio.BaseEventLoop) -> 'YTDLSource':
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']
        to_run = partial(YTDL.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)
        return cls(
            discord.FFmpegPCMAudio(data['url']),
            data=data,
            requester=requester
        )


class MusicPlayer:
    __slots__ = ('bot', 'ctx', 'started_playing_at', 'queue', 'next', 'current', 'now_playing', 'volume')

    def __init__(self, ctx: commands.Context):
        self.bot = ctx.bot
        self.ctx = ctx
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.volume = 0.5
        self.current: YTDLSource = None
        self.started_playing_at: float = None
        self.now_playing: discord.Message = None
        ctx.bot.loop.create_task(self.player_loop())


    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            # Wait for a max for 5 minutes for next song
            try:
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                if self in self.ctx.bot.MUSIC_PLAYERS.values():
                    return self.destroy(self.ctx.guild)
                return

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    raise e

            def after(_):
                return self.bot.loop.call_soon_threadsafe(self.next.set)

            source.volume = self.volume
            self.current = source
            self.ctx.guild.voice_client.play(source, after=after)
            self.started_playing_at = time.perf_counter()
            msg = dedent(f'''
                **Song:** [{source.title}]({source.webpage_url})
                **Requested by:** {source.requester.mention}

                *Use {self.ctx.prefix}current for more info*
            ''')
            self.now_playing = await self.ctx.send_response(
                msg,
                thumbnail=source.thumbnail,
                show_invoke_speed=False,
                add_reference=False,
                title='Now Playing'
            )
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            with suppress(discord.HTTPException):
                await self.now_playing.delete()


    def destroy(self, guild: discord.Guild):
        return self.bot.loop.create_task(self.ctx.cog.cleanup(guild))


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def cleanup(self, guild: discord.Guild):
        with suppress(AttributeError, KeyError):
            await guild.voice_client.disconnect()
	
            for entry in self.bot.MUSIC_PLAYERS[guild.id].queue._queue:
                if isinstance(entry, YTDLSource): 
                    entry.cleanup()

            self.bot.MUSIC_PLAYERS[guild.id].queue._queue.clear()
            del self.bot.MUSIC_PLAYERS[guild.id]


    def get_player(self, ctx: commands.Context) -> MusicPlayer:
        try:
            player = self.bot.MUSIC_PLAYERS[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.bot.MUSIC_PLAYERS[ctx.guild.id] = player

        return player


    @is_connected()
    @channel_check()
    @role_check()
    @commands.command('connect', aliases=['join'])
    async def connect_(self, ctx: commands.Context):
        '''Connects to your voice channel'''
        destination = ctx.author.voice.channel
        try:
            # Check to see if there's already an active voice session
            if ctx.voice_client is not None:
                voice_client = ctx.voice_client
                voice_channel = voice_client.channel

                # Check if we're already connected to the channel
                if voice_channel == destination:
                    raise VoiceChannelError('I am already connected to this channel', destination)

                # Check if we're already connected to a different channel
                if voice_client.is_connected():
                    # We allow to move when the bot is connected, but there are no other members
                    # in the voice channel that aren't deafened.
                    voice_channel_members = list(filter(
                        lambda member: (
                            member != self.bot.user and
                            member.voice.self_deaf is False
                        ),
                        voice_channel.members
                    ))
                    if voice_channel_members:
                        amount = len(voice_channel_members)
                        raise VoiceChannelError(f'I am already connected to {voice_channel.mention} with {amount} active participant{"s"[:amount^1]}', destination)

                await voice_client.move_to(destination)

            else:
                await destination.connect()

        # Handle not being able to connect to VC due to network issues
        except asyncio.TimeoutError:
            raise VoiceChannelError('Timed out', destination)


    @is_connected()
    @channel_check()
    @role_check()
    @commands.command('play', aliases=['add'])
    async def play_(self, ctx: commands.Context, *, query: str):
        '''Plays a song by search or URL'''
        async with ctx.typing():
            voice_client = ctx.voice_client
            if voice_client is None:
                await ctx.invoke(self.connect_)

            # Start playing music and add to queue
            player = self.get_player(ctx)
            source = await YTDLSource.create_source(ctx, query, loop=self.bot.loop)
            await player.queue.put(source)


    @is_connected()
    @channel_check()
    @role_check()
    @commands.command('pause')
    async def pause_(self, ctx: commands.Context):
        '''Pauses the currently playing song'''
        voice_client = ctx.voice_client
        if voice_client is None or voice_client.is_playing() is False:
            raise NotPlaying()

        elif voice_client.is_paused() is True:
            await ctx.message.add_reaction('❌')

        voice_client.pause()
        await ctx.send_response(f'Music **paused** by {ctx.author.mention}', show_invoke_speed=False)


    @is_connected()
    @channel_check()
    @role_check()
    @commands.command('resume', aliases=['unpause'])
    async def resume_(self, ctx: commands.Context):
        '''Resumes the currently paused song'''
        voice_client = ctx.voice_client
        if voice_client is None or voice_client.is_connected() is False:
            raise NotPlaying()

        elif voice_client.is_paused() is False:
            await ctx.message.add_reaction('❌')

        voice_client.resume()
        await ctx.send_response(f'Music **resumed** by {ctx.author.mention}', show_invoke_speed=False)


    @is_connected()
    @channel_check()
    @role_check()
    @commands.command()
    async def skip(self, ctx: commands.Context):
        '''Skips currently playing song'''
        voice_client = ctx.voice_client
        if voice_client is None or voice_client.is_playing() is False:
            raise NotPlaying()

        voice_client.stop()
        await ctx.send_response(f'Song **skipped** by {ctx.author.mention}', show_invoke_speed=False)


    @is_connected()
    @channel_check()
    @commands.command('queue', aliases=['q', 'playlist', 'queue_info'])
    async def queue_(self, ctx: commands.Context):
        '''Shows current queue'''
        voice_client = ctx.voice_client
        if voice_client is None or voice_client.is_playing() is False:
            raise NotPlaying()

        # Get played for current server
        player = self.get_player(ctx)
        if player.queue.empty():
            raise EmptyQueue()

        # Start paginated view of queue
        pages = ViewMenuPages(
            source=MusicQueuePaginator(
                list(player.queue._queue),
                ctx
            ),
            clear_reactions_after=True
        )
        await pages.start(ctx)


    @is_connected()
    @channel_check()
    @commands.command(aliases=['np', 'nowplaying', 'currentsong', 'playing'])
    async def current(self, ctx: commands.Context):
        '''Shows current playing song'''
        voice_client = ctx.voice_client
        if voice_client is None or voice_client.is_connected() is False:
            raise NotPlaying()

        player = self.get_player(ctx)
        if player.current is None:
            raise NotPlaying()

        # Delete previous now playing message (with less information)
        with suppress(discord.HTTPException):
            await player.now_playing.delete()

        # Calculate progress into song
        source = voice_client.source
        duration = source.duration
        passed = time.perf_counter() - player.started_playing_at
        progress = round((passed / duration) * 10) # This way we get an int between 0 and 10 which we can directly use to create emotes
        leftover = 10 - progress

        # Create YT-like progress bar
        bar = str(Emote.start) + (progress * str(Emote.center_full)) + str(Emote.middle) + (leftover * str(Emote.center_empty)) + str(Emote.end)

        # Format time like in YouTube
        tf = lambda s: time.strftime(
            '%H:%M:%S' if s >= 60 * 60 else '%M:%S',
            time.gmtime(s)
        ).lstrip('0').replace(' 0', '') # %-H and %-M only works on linux for non-zero padded hours/minutes so we do this instead

        # Send response
        fields = [
            ('Song', f"[{source.title}]({source.webpage_url})"),
            ('Channel', f"[{source.uploader}]({source.uploader_url})"),
            ('Requested by', source.requester.mention),
            ('Views', intcomma(source.view_count)),
            ('Likes/Dislikes', f"{intcomma(source.likes)}/{intcomma(source.dislikes)}"),
            ('Uploaded', discord.utils.format_dt(source.upload_date, 'R'))
        ]
        player.now_playing = await ctx.send_response(
            f"{bar} ({tf(passed)}/{tf(duration)})",
            title='Now Playing',
            thumbnail=source.thumbnail,
            show_invoke_speed=False,
            fields=fields
        )


    @is_connected()
    @channel_check()
    @role_check()
    @commands.command(aliases=['changevolume', 'vol'])
    async def volume(self, ctx: commands.Context, volume: float):
        '''Changes music volume (must be between 0 and 100)'''
        voice_client = ctx.voice_client
        if voice_client is None or voice_client.is_connected() is False:
            raise NotPlaying()

        if not 0 < volume <= 100:
            raise InvalidVolume(volume)

        player = self.get_player(ctx)

        if voice_client.source:
            voice_client.source.volume = volume / 100

        player.volume = volume / 100
        await ctx.send_response(f'Volume changed to **{volume}%** by {ctx.author.mention}', show_invoke_speed=False)


    @is_connected()
    @channel_check()
    @role_check()
    @commands.command(aliases=['quit', 'disconnect'])
    async def stop(self, ctx: commands.Context):
        '''Stops music and clears queue'''
        voice_client = ctx.voice_client
        if voice_client is None or voice_client.is_connected() is False:
            raise NotPlaying()

        await self.cleanup(ctx.guild)
        await ctx.send_response(f'**Stopped** playing and disconnected by {ctx.author.mention}', show_invoke_speed=False)


def setup(bot):
    bot.add_cog(Music(bot))
