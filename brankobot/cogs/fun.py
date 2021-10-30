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

import random
from io import BytesIO
from pathlib import Path
from textwrap import dedent, wrap

import discord
from discord.ext import commands
from discord.utils import escape_markdown, remove_markdown
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence

from .utils.checks import channel_check, role_check
from .utils.enums import (BigRLDChannelType, BigRLDRoleType, Emote, GuildType,
                          SmallRLDChannelType, SmallRLDRoleType)
from .utils.gif import save_transparent_gif


# -- Cog -- #
class Fun(commands.Cog):
    '''All the commands without a real purpose'''

    def __init__(self, bot):
        self.bot = bot
        self._8ball_responses = [
            'it is very certain',
            'it is decidedly so',
            'without a doubt',
            'yes, definitely',
            'you may rely on it',
            'as i see it, yes',
            'most likely',
            'outlook good',
            'yes',
            'signs point to yes',
            'reply hazy, try again maybe?',
            'ask again later',
            'uhh.. better not tell you now',
            'ant predict now\nc*',
            'concentrate and ask again',
            'dont count on it',
            'my reply is no',
            'my sources say no',
            'outlook not so good',
            'its very doubtful'
        ]
        self._rand_responses_1 = [
            'on a scale of {n1} to {n2} i think {num}',
            'from {n1} to {n2} maybe {num}?',
            'i choose {num} (from {n1} to {n2})'
        ]
        self._rand_responses_2 = [
            'maybe {num}%?',
            'probably {num}%',
            '{num}%'
        ]
        self._rand_responses_3 = [
            'definitely {num}.',
            'i guess {num}',
            'maybe {num}?',
            'uhhh.. {num}?',
            'possibly {num}'
        ]
        self._echo_responses = [
            'nah',
            'nope',
            'no',
            'and if i dont?',
            'lol yeah, no',
            'shut up please'
        ]


    @staticmethod
    def _get_joke(api_response: dict) -> str:
        '''Returns a message based on whether the joke is twopart of a singular setup

        Args:
            api_response (dict): The response of the API

        Returns:
            str: A message containing either a twopart or singular joke
        '''
        if api_response['type'] == 'twopart':
            return f'{api_response["setup"]}\n\n{api_response["delivery"]}'
        return api_response['joke']


    def _input_check(self, text: str) -> bool:
        '''Checks if text is good to repeat back

        Args:
            text (str): The input text to check

        Returns:
            bool: True if there is no blacklisted_words, and the length is below 100
        '''
        # This is kinda useless but still funny if
        # someone tries to say something with it and fails
        blacklisted_words  = {
            'nigger',
            'cunt',
            'faggot',
            'retard',
            'chink',
            'motherfucker',
            'gay',
            'jew'
        }
        text = remove_markdown(text.casefold())
        if any([bw in text for bw in blacklisted_words]) or len(text) > 100:
            return False
        return True


    async def _get_bytes(self, item) -> bytes:
        '''Returns bytes for given item

        Args:
            item: the item to convert into bytes
            can be a discord.Attachment, discord.User/discord.Member/discord.ClientUser or a direct image url

        Returns:
            bytes: the item (image) as bytes
        '''
        if isinstance(item, discord.Attachment):
            return await item.read()

        if isinstance(item, (discord.User, discord.Member, discord.ClientUser)):
            item = str(item.display_avatar)

        async with self.bot.AIOHTTP_SESSION.get(item) as response:
            return await response.read()


    def _caption(self, im_bytes: bytes, text: str):
        im = Image.open(BytesIO(im_bytes))
        frames = []
        BEBASNEUE = str(Path('assets/fonts/BebasNeue.ttf'))
        font = ImageFont.truetype(BEBASNEUE, 1)
        ft = im.format.lower()
        W = im.size[0]

        fontsize = 1
        if len(text) < 23:
            while font.getsize(text)[0] < (0.9 * W):
                fontsize += 1
                font = ImageFont.truetype(BEBASNEUE, fontsize)
        else:
            font = ImageFont.truetype(BEBASNEUE, 50)

        width = 1
        lines = wrap(text, width)
        while font.getsize(max(lines, key=len))[0] < (0.9 * W):
            width += 1
            lines = wrap(text, width)
            if width > 50:
                break

        bar_height = int((len(lines) * font.getsize(lines[0])[1])) + 8

        for frame in ImageSequence.Iterator(im):
            frame = frame.convert('RGBA')
            frame = ImageOps.expand(frame, (0, bar_height, 0, 0), 'white')
            draw = ImageDraw.Draw(frame)
            for i, line in enumerate(lines):
                w, h = draw.multiline_textsize(line, font=font)
                draw.text(((W - w) / 2, i * h), line, 'black', font)
            frames.append(frame)

        fp = BytesIO()
        save_transparent_gif(frames, im.info.get('duration', 64), fp)
        fp.seek(0)
        return discord.File(fp, f'caption.{ft}'), ft


    @channel_check()
    @role_check()
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.command(aliases=['makememe', 'gifcaption', 'captiongif'])
    async def caption(self, ctx, link: str, *, text: str):
        '''Will caption your <link> with <text>'''
        async with ctx.typing():
            b = await self._get_bytes(link)
            _file, ft = await self.bot.loop.run_in_executor(None, lambda: self._caption(b, text))
            await ctx.send_response(image=f'attachment://caption.{ft}', files=_file)


    @role_check()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.command()
    async def offline(self, ctx):
        '''Sends an MP3 if Joc666 is offline'''
        guild = self.bot.get_guild(GuildType.big_rld)
        if guild:
            user = guild.get_member(234023954522701824)
        if not user.status is discord.Status.offline:
            await ctx.send('c\'mon joc666 where are you, aargh this guy is online')
            self.offline.reset_cooldown(ctx)
        else:
            await ctx.send(file=discord.File(str(Path('assets/audio/joc666_offline.mp3'))))


    @commands.cooldown(5, 60, commands.BucketType.guild)
    @commands.command()
    async def rand(self, ctx, num1: int, num2: int, type: str = None):
        '''Chooses random number between <num1> and <num2>
        Possible third argument: scale and percentage
        '''
        r_int = random.randrange(num1, (num2 + 1))
        if type == 'scale':
            rep = self._rand_responses_1
        elif type == 'percentage':
            rep = self._rand_responses_2
        else:
            rep = self._rand_responses_3
        await ctx.send(random.choice(rep).format(n1=num1, n2=num2, num=r_int))


    @commands.command()
    @commands.cooldown(5, 60, commands.BucketType.guild)
    async def love(self, ctx, *, thing: str):
        '''Chooses random number between 0 and 100'''
        r_int = random.randrange(101)
        if r_int < 33:
            emote = Emote.cry
        elif 33 < r_int < 67:
            emote = Emote.flushed_pumpkin
        else:
            emote = Emote.heart
        await ctx.send(f'{ctx.author.mention} loves {thing} for {r_int}% {emote}')


    @commands.command('8ball', aliases=['magic8ball'])
    @commands.cooldown(5, 60, commands.BucketType.guild)
    async def _8ball(self, ctx):
        '''Picks random response from list'''
        await ctx.send(f'{ctx.author.mention}, {random.choice(self._8ball_responses)}')


    @channel_check(BigRLDChannelType.general)
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(aliases=['urbandict', 'define'])
    async def urban(self, ctx, *, query: commands.clean_content):
        '''Will search your <query> on urban dictionary and send definition'''
        r = await self.bot.AIOHTTP_SESSION.get(f'http://api.urbandictionary.com/v0/define?term={query}')
        data = await r.json()
        nl = '\n'
        try:
            msg = dedent(f'''
                **Word:** [{data["word"]}]({data.get("permalink")})
                **Date:** {data.get("written_on", "1900-01-01")[0:10]}
                **Upvotes:** {data.get("thumbs_up", "No Upvotes")}
                **Downvotes:** {data.get("thumbs_down", "No Downvotes")}
                **Definition:** {escape_markdown(data.get("definition").replace(nl, ""))}

                *{escape_markdown(data.get("example").replace(nl, ""))}*
            '''.strip())
        except KeyError:
            msg = f'Word {query} not found'
        await ctx.send_response(msg, title='Urban Dictionary')


    @channel_check(BigRLDChannelType.memes, SmallRLDChannelType.memes)
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(aliases=['randommeme', 'meme'])
    async def reddit(self, ctx, subreddit: str = 'memes'):
        '''Returns a random post from [subreddit=memes]'''
        r = await self.bot.AIOHTTP_SESSION.get(f'https://meme-api.herokuapp.com/gimme/{subreddit}')
        data = await r.json()
        try:
            if data['nsfw'] is False:
                fields = [
                    ('Subreddit', f"[{data['subreddit']}](https://www.reddit.com/r/{data['subreddit']})"),
                    ('Author', f"[{data['author']}](https://www.reddit.com/r/{data['author']})"),
                    ('Upvotes', f"{data['ups']} 👍🏻")
                ]
                await ctx.send_response(
                    fields=fields,
                    title=data['title'],
                    image=data['url'],
                    url=data['postLink']
                )
            else:
                await ctx.send('Can\'t send NSFW stuff')
        except KeyError:
            await ctx.send(f'Couldn\'t find subreddit {subreddit}')


    @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.command(aliases=['echo'])
    async def say(self, ctx, *, message: str):
        '''Brankobot will repeat your message input'''
        if not self._input_check(message):
            await ctx.send(random.choice(self._echo_responses))
        else:
            await ctx.message.delete()
            msg = await ctx.send(message)
            await msg.add_reaction('🤡')


    @role_check()
    @commands.command(aliases=['chief', 'chieftain'], hidden=True)
    @commands.cooldown(1, 300, commands.BucketType.guild)
    async def outside(self, ctx):
        '''30% chance of responding with h7's outside mp3'''
        if random.ranrange(0, 101) > 70:
            await ctx.send(file=discord.File(str(Path('assets/audio/h7_outside.mp3'))))


    @role_check()
    @commands.command(aliases=['uselessfact'])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fact(self, ctx):
        '''Will send a random useless fact'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://uselessfacts.jsph.pl/random.json?language=en')).json()
        msg = r['text'].replace('`', "'")
        await ctx.send_response(msg, title='Useless Fact')


    @role_check()
    @commands.command(aliases=['createpoll'])
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def poll(self, ctx, title: str, *answers: str):
        '''Will create a strawpoll with possible [answers...] and [options...]'''
        payload = {
            'poll': {
                'title': title,
                'answers': list(answers)
            }
        }
        r = await (await self.bot.AIOHTTP_SESSION.post('https://strawpoll.com/api/poll', headers={'Content-Type': 'application/json'}, json=payload)).json()
        await ctx.send(f'https://strawpoll.com/{r["content_id"]}')


    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def joke(self, _):
        '''Base command for sending jokes'''

    @joke.command('dad')
    async def joke_dad(self, ctx):
        '''Will send a random dad joke from [this website](https://icanhazdadjoke.com)'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://icanhazdadjoke.com', headers={'Accept': 'application/json'})).json()
        msg = r['joke']
        await ctx.send_response(msg)

    @joke.command('dark')
    async def joke_dark(self, ctx):
        '''Will send a random dark joke from [this website](https://sv443.net/jokeapi)'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://sv443.net/jokeapi/v2/joke/Dark')).json()
        await ctx.send_response(self._get_joke(r))

    @joke.command('pun')
    async def joke_pun(self, ctx):
        '''Will send a random pun joke from [this website](https://sv443.net/jokeapi)'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://sv443.net/jokeapi/v2/joke/Pun')).json()
        await ctx.send_response(self._get_joke(r))

    @joke.command('misc')
    async def joke_misc(self, ctx):
        '''Will send a random miscellaneous joke from [this website](https://sv443.net/jokeapi)'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://sv443.net/jokeapi/v2/joke/Miscellaneous')).json()
        await ctx.send_response(self._get_joke(r))


def setup(bot):
    bot.add_cog(Fun(bot))
