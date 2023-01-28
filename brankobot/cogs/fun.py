# -*- coding: utf-8 -*-

'''
The MIT License (MIT)

Copyright (c) 2021-present Buster

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the 'Software'),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
'''
import asyncio
import base64
import random
from functools import partial
from io import BytesIO
from pathlib import Path
from textwrap import dedent, fill
from typing import Optional, Union

import discord
import openai
from discord.ext import commands
from discord.utils import escape_markdown, remove_markdown
from gtts import gTTS
from main import Bot, Context
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence

from .utils.checks import channel_check, role_check, is_connected
from .utils.enums import (BigRLDChannelType, BigRLDRoleType, Emote, GuildType,
                          SmallRLDChannelType, SmallRLDRoleType, TikTokVoice)
# from .utils.helpers import average, get_next_birthday
# from .utils.models import Birthday
from .utils.flags import OpenAIFlags
# from .utils.errors import (BirthdayAlreadyRegistered, BirthdayDoesntExist,
#                            NoBirthdays, NotAModerator)
from .utils.gif import save_transparent_gif
from .utils.errors import VoiceChannelError
from .utils.ttts import tTTS


class Fun(commands.Cog):
    '''All the commands without a real purpose'''

    def __init__(self, bot):
        self.bot: Bot = bot
        openai.api_key = self.bot.OPENAI_API_TOKEN
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
    def _generate_caption(im_bytes: bytes, text: str) -> discord.File:
        '''Adds a caption to an image

        Parameters
        ----------
        im_bytes : bytes
            The image as bytes to add the caption to
        text : str
            The caption text

        Returns
        -------
        discord.File
            The captioned image
        '''
        im = Image.open(BytesIO(im_bytes))
        frames = []
        BEBASNEUE = str(Path('assets/fonts/BebasNeue.ttf'))
        font = ImageFont.truetype(BEBASNEUE, 1)
        ft = im.format.lower()
        W = im.size[0]

        # Calculate the size of the font by taking the length
        # of the text and increasing it depending on the amount
        # of text
        fontsize = 1
        if len(text) < 23:
            while font.getsize(text)[0] < (0.9 * W):
                fontsize += 1
                font = ImageFont.truetype(BEBASNEUE, fontsize)

        else:
            font = ImageFont.truetype(BEBASNEUE, 50)

        # Calculate width of text by taking the width of the image
        # and slowly increasing it untill it fits 90%
        width = 1
        lines = fill(text, width)
        while font.getsize_multiline(lines)[0] < (0.9 * W):
            width += 1
            lines = fill(text, width)
            if width > 50:
                break

        # Calculate bar height to fit the text on by getting the
        # total height of the text
        bar_height = font.getsize_multiline(lines)[1] + 8

        # Add text to each frame in the gif
        for frame in ImageSequence.Iterator(im):
            frame = frame.convert('RGBA')
            frame = ImageOps.expand(
                image=frame,
                border=(0, bar_height, 0, 0),
                fill='white'
            ).convert('RGBA')

            draw = ImageDraw.Draw(frame)
            draw.multiline_text(
                xy=(W / 2, 0),
                text=lines,
                fill='black',
                font=font,
                align='center', # Aligment for individual lines
                anchor='ma'     # Total text alignment relative to xy being middle top
            )

            frames.append(frame.convert('RGBA'))

        # Save Image as discord File ready to send
        fp = BytesIO()
        save_transparent_gif(frames, im.info.get('duration', 64), fp)
        fp.seek(0)
        return discord.File(fp, f'caption.{ft}'), ft


    @staticmethod
    def _format_joke(api_response: dict) -> str:
        '''Formats a joke based on whether the joke is of a twopart
           or singular setup

        Parameters
        ----------
        api_response : dict
            The response of the API containing the joke

        Returns
        -------
        str
            A message containing either a twopart or singular joke
        '''
        if api_response['type'] == 'twopart':
            return f'{api_response["setup"]}\n\n{api_response["delivery"]}'

        return api_response['joke']


    @staticmethod
    def _check_input(text: str) -> bool:
        '''Checks if text is okay to repeat back

        This is kinda useless but still funny if someone tries to say
        something with these and fails

        Parameters
        ----------
        text : str
            The input text to check

        Returns
        -------
        bool
            True if there is no blacklisted_words, and the length is below 100
            False if not
        '''
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


    async def _get_bytes(self, item: Union[discord.Attachment, discord.User, discord.Member, discord.ClientUser, str]) -> bytes:
        '''Returns image bytes for given item

        Parameters
        ----------
        item : Union[discord.Attachment, discord.User, discord.Member, discord.ClientUser, str]
            The item to convert into bytes by taking the image assocated with it

        Returns
        -------
        bytes
            The associated image as bytes
        '''
        if isinstance(item, discord.Attachment):
            return await item.read()

        if isinstance(item, (discord.User, discord.Member, discord.ClientUser)):
            item = str(item.display_avatar)

        async with self.bot.AIOHTTP_SESSION.get(item) as response:
            return await response.read()


    @channel_check()
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(aliases=['makememe', 'gifcaption', 'captiongif'])
    async def caption(self, ctx: Context, link: str, *, text: str):
        '''Will caption your <link> with <text>'''
        async with ctx.loading(initial_message='Downloading') as loader:
            b = await self._get_bytes(link)
            await loader.update('Generating')
            to_run = partial(self._generate_caption, b, text)
            _file, ft = await self.bot.loop.run_in_executor(None, to_run)
            await loader.update('Uploading')
            await ctx.send_response(image=f'attachment://caption.{ft}', files=_file)


    @role_check()
    @commands.cooldown(1, 60 * 15, commands.BucketType.guild)
    @commands.command()
    async def offline(self, ctx: Context):
        '''Sends an MP3 if Joc666 is offline'''
        guild = self.bot.get_guild(GuildType.big_rld.value)
        if guild:
            user = guild.get_member(234023954522701824)
        if not user.status is discord.Status.offline:
            await ctx.send('c\'mon joc666 where are you, aargh this guy is online')
            self.offline.reset_cooldown(ctx)
        else:
            await ctx.send(file=discord.File(str(Path('assets/audio/joc666_offline.mp3'))))


    @commands.cooldown(5, 60, commands.BucketType.guild)
    @commands.command()
    async def rand(self, ctx: Context, num1: int, num2: int, type: str = None):
        '''Chooses random number'''
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
    async def love(self, ctx: Context, *, thing: str):
        '''Determines how much you love something'''
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
    async def _8ball(self, ctx: Context):
        '''Ask magic 8ball a question'''
        await ctx.send(f'{ctx.author.mention}, {random.choice(self._8ball_responses)}')


    @channel_check(BigRLDChannelType.general)
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(aliases=['urbandict', 'define'])
    async def urban(self, ctx: Context, *, query: commands.clean_content):
        '''Defines a word using the urban dictionary'''
        r = await self.bot.AIOHTTP_SESSION.get(f'http://api.urbandictionary.com/v0/define?term={query}')
        data = await r.json()
        nl = '\n'
        try:
            msg = dedent(f'''
                **Word:** [{data['word']}]({data.get('permalink')})
                **Date:** {data.get('written_on', '1900-01-01')[0:10]}
                **Upvotes:** {data.get('thumbs_up', 'No Upvotes')}
                **Downvotes:** {data.get('thumbs_down', 'No Downvotes')}
                **Definition:** {escape_markdown(data.get('definition').replace(nl, ''))}

                *{escape_markdown(data.get('example').replace(nl, ''))}*
            '''.strip())
        except KeyError:
            msg = f'Word {query} not found'
        await ctx.send_response(msg, title='Urban Dictionary')


    @role_check(BigRLDRoleType.member, SmallRLDRoleType.member, BigRLDRoleType.onlyfans, BigRLDRoleType.small_rld)
    @commands.cooldown(1, 60 * 60 * 24, commands.BucketType.user)
    @commands.command(aliases=['createimage', 'dall-e', 'dalle'])
    async def generateimage(self, ctx: Context, size: Optional[int] = 2, *, prompt: str):
        '''Generates an image from your text'''
        sizes = {
            1: '256x256',
            2: '512x512',
            3: '1024x1024'
        }
        size = sizes.get(size, sizes[2])
        async with ctx.loading(initial_message='Generating') as loader:
            try:
                response = openai.Image.create(
                    prompt=prompt,
                    n=1,
                    size=size,
                    response_format='b64_json'
                )
                data = response['data'][0]['b64_json']
            except openai.InvalidRequestError:
                await loader.update('Invalid request (filtered response), try again')
                await loader.__aexit__(None, None, None)
                self.generateimage.reset_cooldown(ctx)

            await loader.update('Converting base64 to image')
            fp = BytesIO()
            image = Image.open(BytesIO(base64.b64decode(data)))
            image.save(fp, format='png')
            fp.seek(0)

            await loader.update('Uploading')
            await ctx.send(file=discord.File(fp, 'image.png'))


    @commands.is_owner()
    @commands.command(aliases=['adminai', 'adminaskai'])
    async def adminask(self, ctx: Context, prompt: commands.clean_content, *, flags: OpenAIFlags):
        '''Ask the bot a question using the OpenAI text-davinci 3 model'''
        if flags.personality is None:
            flags.personality = self.bot.PERSONALITY

        response = openai.Completion.create(
            prompt=flags.personality + ' ' + flags.context + ' ' + prompt,
            temperature=flags.temperature,
            max_tokens=flags.max_tokens,
            model=flags.model,
            presence_penalty=flags.presence_penalty,
            frequency_penalty=flags.frequency_penalty,
        )
        await ctx.send(response["choices"][0]["text"].strip(" \n"))


    @role_check(BigRLDRoleType.member, SmallRLDRoleType.member, BigRLDRoleType.onlyfans, BigRLDRoleType.small_rld)
    @commands.cooldown(5, 60 * 5, commands.BucketType.guild)
    @commands.command(aliases=['ai', 'askai'])
    async def ask(self, ctx: Context, *, prompt: commands.clean_content):
        '''Ask the bot a question using the OpenAI text-davinci 3 model. Note that the bot does not have or store any context.'''
        try:
            async with ctx.typing():
                response = openai.Completion.create(
                    prompt=self.bot.PERSONALITY + prompt,
                    temperature=0.6,
                    max_tokens=200,
                    model='text-davinci-003'
                )
                await ctx.send(response["choices"][0]["text"].strip(" \n"))

        except openai.OpenAIError:
            await ctx.send(f'OpenAI error try again lata')


    @is_connected()
    @commands.is_owner()
    @commands.cooldown(1, 60 * 15, commands.BucketType.guild)
    @commands.command(aliases=['voiceai', 'voiceaskai', 'tts'])
    async def voiceask(self, ctx: Context, *, prompt: str):
        '''Ask the bot a question using and he will say it in voice'''

        # Check if the bot is currently in a voice channel
        # If he's playing music, that music will need to be stopped and command tried again
        if ctx.voice_client is not None:
            await ctx.send(f'I am already in a voice channel {Emote.rolling_eyes}')
            self.voiceask.reset_cooldown(ctx)
            return

        # Generate AI response
        try:
            response = openai.Completion.create(
                prompt=self.bot.PERSONALITY + prompt,
                temperature=0.8,
                max_tokens=70,
                model='text-davinci-003'
            )
            response = response["choices"][0]["text"].strip(" \n")

        except openai.OpenAIError:
            await ctx.send('OpenAI error try again lata')

        # The speech will be a combination of the invokers name, the prompt, the AI response and what is in between the last two
        random_interlude = random.choice([', well, ', ', ', ', I guess, '])
        text = f'{ctx.author.name} asked: {prompt}{random_interlude}{response}'

        # Try to use the tiktok tts API, else use google tts api
        try:
            # Turn AI text into audio using tiktok tts API
            sound = tTTS(text, self.bot.AIOHTTP_SESSION, '73dbc3b8c6d94ee533c71c6570538fa0', self.bot.TIKTOK_VOICE)
            data = await sound.save('sound.mp3')
            status = data['status']

            if status == 'This voice is unavailable now':
                await ctx.send('voice unavailable in tiktok tts, using google tts instead...')
                raise
            elif status == 'Text too long to create speech audio':
                await ctx.send('text too long for tiktok tts, using google tts instead...')
                raise
            elif status == 'Couldn\'t load speech. Try again.':
                await ctx.send('new session id required for tiktok tts, using google tts instead...')
                raise
            elif status != 'success':
                await ctx.send(f'unknown error for tiktok tts: {status}, using google tts instead...')
                raise

        except:
            # Turn AI text into audio using google tts API
            sound = gTTS(text, lang=self.bot.SPEECH_LANGUAGE, tld=self.bot.SPEECH_ACCENT)
            sound.save('sound.mp3')

        # Join the voice channel
        destination = ctx.author.voice.channel
        try:
            await destination.connect()

        except asyncio.TimeoutError:
            raise VoiceChannelError('Timed out', destination)

        # Play the sound file
        vc = ctx.voice_client
        source = discord.FFmpegPCMAudio('sound.mp3')
        vc.play(source, after=None)

        # Sleep until the sound file is done playing, then disconnect
        while True:
            await asyncio.sleep(30)

            if vc.is_playing() is False:
                await vc.disconnect()
                break


    @commands.is_owner()
    @commands.group('voice', aliases=['tiktokvoice'], invoke_without_command=True)
    async def voice(self, _: Context):
        '''Commands for the bot's voice'''

    @commands.is_owner()
    @voice.command('set', aliases=['change', 'update'])
    async def voice_set(self, ctx: Context, voice: commands.clean_content):
        '''Set the voice of the bot'''
        self.bot.TIKTOK_VOICE = voice
        await ctx.send(f'Ofcourse, my liege {Emote.socialcredit.value} tiktok voice is set to {TikTokVoice[voice]}')

    @commands.is_owner()
    @voice.command('reset', aliases=['default', 'clear'])
    async def voice_reset(self, ctx: Context):
        '''Reset the voice of the bot to the default'''
        self.bot.TIKTOK_VOICE = self.bot.TIKTOK_VOICE
        await ctx.send(f'Ofcourse, my liege {Emote.socialcredit.value}')

    @voice.command('current', aliases=['show', 'get'])
    async def voice_current(self, ctx: Context):
        '''Get the current voice of the bot'''
        await ctx.send(f'Current (tiktok) voice: {TikTokVoice[self.bot.TIKTOK_VOICE]} ({self.bot.TIKTOK_VOICE})')


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


    @channel_check(BigRLDChannelType.memes, SmallRLDChannelType.memes)
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(aliases=['randommeme', 'meme'])
    async def reddit(self, ctx: Context, subreddit: str = 'memes'):
        '''Returns a random post from a subreddit'''
        r = await self.bot.AIOHTTP_SESSION.get(f'https://meme-api.herokuapp.com/gimme/{subreddit}')
        data = await r.json()
        try:
            if data['nsfw'] is False:
                fields = [
                    ('Subreddit', f'[{data["subreddit"]}](https://www.reddit.com/r/{data["subreddit"]})'),
                    ('Author', f'[{data["author"]}](https://www.reddit.com/r/{data["author"]})'),
                    ('Upvotes', f'{data["ups"]} 👍🏻')
                ]
                await ctx.send_response(
                    fields=fields,
                    title=data['title'],
                    image=data['url'],
                    url=data['postLink']
                )
            else:
                await ctx.reply('Can\'t send NSFW stuff', delete_after=60, mention_author=False)

        except KeyError:
            await ctx.reply(f'Couldn\'t find subreddit {subreddit}', delete_after=60, mention_author=False)


    @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    @commands.cooldown(1, 60 * 5, commands.BucketType.guild)
    @commands.command(aliases=['echo'])
    async def say(self, ctx: Context, *, message: str):
        '''Brankobot will repeat your message input'''
        if not self._check_input(message):
            await ctx.send(random.choice(self._echo_responses))
        else:
            await ctx.message.delete()
            msg = await ctx.send(message)
            await msg.add_reaction('🤡')


    @role_check()
    @commands.command(aliases=['chief', 'chieftain'], hidden=True)
    @commands.cooldown(1, 60 * 5, commands.BucketType.guild)
    async def outside(self, ctx: Context):
        '''Chieftains, outside outside outˢᶦᵈᵉ'''
        await ctx.send(file=discord.File(str(Path('assets/audio/h7_outside.mp3'))))


    @role_check()
    @commands.command(aliases=['uselessfact'])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fact(self, ctx: Context):
        '''Will send a random useless fact'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://uselessfacts.jsph.pl/random.json?language=en')).json()
        msg = r['text'].replace('`', '\'')
        await ctx.send_response(msg, title='Useless Fact')


    @role_check()
    @commands.command(aliases=['createpoll'])
    @commands.cooldown(1, 60 * 5, commands.BucketType.user)
    async def poll(self, ctx: Context, title: str, *answers: str):
        '''Will create a strawpoll with possible [answers...] and [options...]'''
        payload = {
            'poll': {
                'title': title,
                'answers': list(answers)
            }
        }
        r = await (await self.bot.AIOHTTP_SESSION.post('https://strawpoll.com/api/poll', headers={'Content-Type': 'application/json'}, json=payload)).json()
        await ctx.send(f'https://strawpoll.com/{r["content_id"]}')


    # @role_check(BigRLDRoleType.member, BigRLDRoleType.onlyfans, SmallRLDRoleType.member)
    # @commands.cooldown(1, 300, commands.BucketType.user)
    # @commands.group(
    #     invoke_without_command=True,
    #     aliases=['bday', 'anniversary'],
    #     usage='<birth_date (dd/mm/yyyy, dd-mm-yyyy or e.g 20 apr, 1889)>'
    # )
    # async def birthday(self, ctx: Context, birth_date: str):
    #     '''Registers your birthday for brankobot to sell on the dark web (and to congratulate)'''
    #     birth_date = dateparser.parse(birth_date, ['%d/%m/%Y', '%d-%m-%Y', '%-d %b, %Y'])
    #     cursor = await self.bot.CONN.cursor()
    #     try:
    #         # Check if user isn't already in database
    #         birthday = await self.bot.get_birthday(ctx.author.id)
    #         if birthday is not None:
    #             raise BirthdayAlreadyRegistered(birthday)

    #         # Since a user can only add his birthday once, we ask to confirm
    #         if not await ctx.confirm(f'you can only add your birthday once, is {format_dt(birth_date, "D")} right?'):
    #             return

    #         # Add birthday to DB
    #         insert_birthday_query = dedent('''
    #             INSERT INTO birthdays (
    #                 user_id,
    #                 server_id,
    #                 birthday_date
    #             ) VALUES (
    #                 ?, ?, ?
    #             )
    #         '''.strip())

    #         await cursor.execute(
    #             insert_birthday_query,
    #             (
    #                 ctx.author.id,
    #                 ctx.guild.id,
    #                 birth_date.strftime('%Y-%m-%d')
    #             )
    #         )
    #         await self.bot.CONN.commit()

    #         next_birthday = get_next_birthday(birth_date)
    #         await ctx.send_response(
    #             f'ok {Emote.monocle}, i will maybe wish you a happy **{ordinal(next_birthday.year - birth_date.year)}** birthday {format_dt(next_birthday, "R")}',
    #             title='Birthday Added',
    #             show_invoke_speed=False
    #         )

    #     finally:
    #         await cursor.close()

    # @commands.cooldown(1, 300, commands.BucketType.user)
    # @birthday.command('info', aliases=['daysleft', 'show'])
    # async def birthday_info(self, ctx: Context):
    #     '''Shows stuff about your own birthday'''
    #     birthday: Birthday = await self.bot.get_birthday(ctx.author.id)
    #     if not birthday:
    #         raise BirthdayDoesntExist(ctx.author)

    #     next_birthday = get_next_birthday(birthday.date)
    #     now = datetime.now()
    #     age = now - birthday.date
    #     msg = dedent(f'''
    #         **Current age:** {precisedelta(age)} old

    #         Your **{ordinal(next_birthday.year - birthday.date.year)}** birthday will be in {precisedelta(now - next_birthday, minimum_unit='minutes')} on {format_dt(next_birthday, 'F')}
    #     ''')
    #     fields = [
    #         ('Months', intcomma(round((now.year - birthday.date.year) * 12 + now.month - birthday.date.month))),
    #         ('Weeks', intcomma(round(age.days / 7))),
    #         ('Days', intcomma(age.days)),
    #         ('Hours', intcomma(round(age.total_seconds() / (60 * 60)))),
    #         ('Minutes', intcomma(round(age.total_seconds() / 60))),
    #         ('Seconds', intcomma(round(age.total_seconds())))
    #     ]
    #     await ctx.send_response(
    #         msg,
    #         fields=fields,
    #         title='Birthday Info'
    #     )

    # @birthday.command('remove', aliases=['delete', 'del'])
    # async def birthday_remove(self, ctx: Context, user: Union[discord.User, discord.Object]):
    #     '''Removes a birthday from database'''
    #     birthday: Birthday = await self.bot.get_birthday(user.id)
    #     if not birthday:
    #         raise BirthdayDoesntExist(user)

    #     if not await is_moderator(ctx):
    #         raise NotAModerator()

    #     if not await ctx.confirm('are you sure?'):
    #         return

    #     await self.bot.delete_birthday(user.id)
    #     await ctx.send_response(
    #         f'Removed birthday {format_dt(birthday.date, "d")} belonging to {self.bot.get_user(birthday.user_id)}',
    #         title='Birthday Removed'
    #     )

    # @commands.cooldown(1, 300, commands.BucketType.user)
    # @birthday.command('average', aliases=['averageage'])
    # async def birthday_average(self, ctx: Context):
    #     '''Shows the average age in current server'''
    #     cursor = await self.bot.CONN.cursor()
    #     try:
    #         select_birthdays_query = dedent('''
    #             SELECT *
    #             FROM birthdays
    #             WHERE server_id = ?;
    #         '''.strip())

    #         result = await cursor.execute(
    #             select_birthdays_query,
    #             (ctx.guild.id,)
    #         )
    #         rows = await result.fetchall()

    #         if rows:
    #             today = date.today()
    #             dates = [
    #                 date(year=year, month=month, day=day)
    #                 for year, month, day in [
    #                     map(int, row[3].split('-'))
    #                     for row in rows
    #                 ]
    #             ]
    #             average_age = average([
    #                 today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    #                 for birth_date in dates
    #             ])
    #             msg = dedent(f'''
    #                 The average age in **{ctx.guild.name}** is {average_age:.2f} years.
    #                 The oldest person is {naturaldelta(today - min(dates))} old and the youngest is {naturaldelta(today - max(dates))} old.
    #             ''')
    #             await ctx.send_response(
    #                 msg,
    #                 title='Average Age'
    #             )

    #         else:
    #             raise NoBirthdays()

    #     finally:
    #         await cursor.close()


    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def joke(self, _):
        '''Base command for sending jokes'''

    @joke.command('dad')
    async def joke_dad(self, ctx: Context):
        '''Will send a random dad joke from [this website](https://icanhazdadjoke.com)'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://icanhazdadjoke.com', headers={'Accept': 'application/json'})).json()
        msg = r['joke']
        await ctx.send_response(msg)

    @joke.command('dark')
    async def joke_dark(self, ctx: Context):
        '''Will send a random dark joke from [this website](https://sv443.net/jokeapi)'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://sv443.net/jokeapi/v2/joke/Dark')).json()
        await ctx.send_response(self._format_joke(r))

    @joke.command('pun')
    async def joke_pun(self, ctx: Context):
        '''Will send a random pun joke from [this website](https://sv443.net/jokeapi)'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://sv443.net/jokeapi/v2/joke/Pun')).json()
        await ctx.send_response(self._format_joke(r))

    @joke.command('misc')
    async def joke_misc(self, ctx: Context):
        '''Will send a random miscellaneous joke from [this website](https://sv443.net/jokeapi)'''
        r = await (await self.bot.AIOHTTP_SESSION.get('https://sv443.net/jokeapi/v2/joke/Miscellaneous')).json()
        await ctx.send_response(self._format_joke(r))


async def setup(bot):
    await bot.add_cog(Fun(bot))
