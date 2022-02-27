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
import re
from contextlib import suppress
from dataclasses import asdict
from datetime import datetime, timedelta
from io import BytesIO
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import List, Optional, Tuple

import discord
import iso639
import matplotlib.pyplot as plt
from async_lru import alru_cache
from bs4 import BeautifulSoup
from discord.ext import commands
from discord.ext.menus.views import ViewMenuPages
from discord.utils import escape_markdown, format_dt
from humanize import intcomma
from matplotlib.dates import DateFormatter, date2num
from matplotlib.ticker import MaxNLocator
from PIL import Image, ImageDraw, ImageFont, ImageOps

from main import Bot, Context
from .utils.checks import channel_check
from .utils.converters import RegionConverter
from .utils.enums import (BigRLDChannelType, Emote, EventStatusType, FrontType,
                          LoseReasons, MarkType, Region, SmallRLDChannelType,
                          WN8Colour, WotApiType, try_enum)
from .utils.errors import (ApiError, ClanNotFound, InvalidClan, InvalidFlags,
                           InvalidNickname, NoMoe, PlayerNotFound, ReplayError)
from .utils.flags import MarkCollageFlags, RequirementsFlags, TankStatFlags
from .utils.helpers import separate_capitals
from .utils.models import (Achievement, Clan, GlobalmapEvent, GlobalMapFront,
                           Player, Tank, TankStats)
from .utils.paginators import (ClanWarsPaginator, ReplayPaginator,
                               TankStatsPaginator)
from .utils.wotreplay_folder import ReplayData


class WoT(commands.Cog):
    '''All the World of Tanks related commands are in this category'''

    def __init__(self, bot):
        self.bot: Bot = bot
        self._wn8_colour_mapping = {
            range(0, 300): WN8Colour.black,
            range(300, 599): WN8Colour.red,
            range(599, 899): WN8Colour.orange,
            range(899, 1249): WN8Colour.yellow,
            range(1249, 1599): WN8Colour.light_green,
            range(1599, 1899): WN8Colour.dark_green,
            range(1899, 2349): WN8Colour.blue,
            range(2349, 2899): WN8Colour.light_purple,
            range(2899, 100000): WN8Colour.dark_purple
        }
        self._moe_values = (
            '95',
            '85',
            '65'
        )


    @staticmethod
    def _combine_images(images: List[Image.Image], columns: int, image_size: Tuple[int]) -> Image.Image:
        '''Combines a list of equal sized Image into one image collage

        Parameters
        ----------
        images : List[Image.Image]
            A list of images to combine into one
        columns : int
            The amount of columns to fit all rows on
        image_size : Tuple[int]
            The size of each image

        Returns
        -------
        Image.Image
            The combined image
        '''
        width, height = image_size
        images = [images[i:i + columns] for i in range(0, len(images), columns)]
        combined = Image.new('RGB', (columns * width, len(images) * height), '#070906')
        for row_num, row in enumerate(images):
            for im_num, im in enumerate(row):
                combined.paste(im, (im_num * width, row_num * height))

        return combined


    @staticmethod
    def _get_sizes(total_marks: int) -> Tuple[str, Tuple[int, int], int, int, int]:
        '''Gets the size of stuff based on total amount of marks.

        If the mark amount is low, we can afford to use higher quality images.
        If the mark amount if higher, we use lower quality images to reduce
        processing time.

        Parameters
        ----------
        total_marks : int
            The total amount of marks to determine sizes on

        Returns
        -------
        Tuple[str, Tuple[int, int], int, int, int]
            In order:
            Image size for herhor.net (Large, Medium Small),
            image size (width, height) (px),
            footer bar height (px),
            font size (px),
            column amount
        '''
        to_image_size = {
            range(1, 14): (
                'Large',
                (271, 100),
                40,
                14
            ),
            range(14, 28): (
                'Medium',
                (204, 75),
                50,
                18
            ),
            range(28, 1000): (
                'Small',
                (135, 50),
                75,
                24
            )
        }

        # Minimum of 4 columns and maximum of 10
        columns = (max(4, min(10, total_marks // 10)),)
        for mark_amount_range, sizes in to_image_size.items():
            if total_marks in mark_amount_range:
                return sizes + columns


    @staticmethod
    def _format_clan_log(data: dict) -> Tuple[str, str]:
        '''Formats a data entry for the /clan/{clan_id}/log endpoint

        Parameters
        ----------
        data : dict
            The data to make readable

        Returns
        -------
        Tuple[str, str]
            Tuple[str, str]: A readable representation of a clan log item
        '''
        clan_tag = data.get('enemy_clan', {}).get('tag') or 'placeholder'
        opponent_clan = f'[{escape_markdown(clan_tag)}](https://wot-life.com/eu/clan/{clan_tag}/)'
        province_name = data.get('target_province', {}).get('name')
        province_alias = data.get('target_province', {}).get('alias')
        province = f'[{province_name}](https://eu.wargaming.net/globalmap/#province/{province_alias}/)'
        reason = try_enum(LoseReasons, data.get('finish_reason'))
        messages = {
            # Campaign and clan wars
            'TOURNAMENT_BATTLE_WON': (Emote.victory, f'The clan defeated {opponent_clan} in a landing tournament for {province} ({reason}).'),
            'TOURNAMENT_BATTLE_LOST': (Emote.defeat, f'The clan lost a battle against {opponent_clan} in a landing tournament for {province} ({reason}).'),
            'CLAN_CAPTURED_FREE_PROVINCE': (Emote.add, f'The clan has captured {province} without a battle.'),
            'CLAN_CAPTURED_PROVINCE': (Emote.add, f'The clan has defeated {opponent_clan} and captured {province}.'),
            'CLAN_LOST_PROVINCE': (Emote.remove, f'The clan has lost {province} due to a defeat in battle against {opponent_clan}.'),
            'SUPER_FINAL_BATTLE_WON': (Emote.victory, f'The clan defeated {opponent_clan} in a battle for {province} ({reason}).'),
            'SUPER_FINAL_BATTLE_LOST': (Emote.defeat, f'The clan lost a battle against {opponent_clan} for {province} ({reason}).'),
            'MAP_LEAVE_APPLIED': (Emote.leave, f'The clan has left the Global Map and lost **{data.get("lost_provinces", "N/A")}** provinces.'),
            'LANDING_BET_CREATED': (Emote.add, f'The clan has applied for a landing tournament on {province}.'),
            'LANDING_BET_CANCELLED': (Emote.remove, f'The clan has cancelled an application for the landing tournament on {province}.'),

            # Clan wars specific
            'VICTORY_POINTS_CHANGED_FOR_COLLECT_TAXES': (Emote.add, f'**{data.get("victory_points")}** Victory Points added in tier **X** for ownership of provinces.'),
            'REVOLT_STARTED_ON_PROVINCE': (Emote.revolt, f'A revolt has started in {province} in the **{data.get("front_name")}**.')
        }
        return messages.get(
            data.get('type'),
            ('N/A', 'Couldn\'t resolve data')
        )


    @staticmethod
    def _get_trend(value: Optional[int]) -> str:
        '''Gets a trend based on a change value

        Example
        -------
        >>> self._get_trend(10)
        '↑ 10'
        >>> self._get_trend(-5)
        '↓ 5'
        >>> self._get_trend(0)
        '→ 0'

        Parameters
        ----------
        value : int
            The value to base the trend on

        Returns
        -------
        str
            <arrow up/down/right> <absolute change value>
        '''
        char = '→'
        value = value or 0
        if value > 0:
            char = '↑'
        elif value < 0:
            char = '↓'
        return f'{char} {abs(value)}'


    @alru_cache(maxsize=1024)
    async def _get_image_from_url(self, url: str) -> Image.Image:
        '''Cached

        Retrieves an Image from URL

        Parameters
        ----------
        url : str
            The web url to get the image from

        Returns
        -------
        Image.Image
            The Image found on the url
        '''
        r = await self.bot.AIOHTTP_SESSION.get(url)
        fp = await r.read()
        return Image.open(BytesIO(fp))


    @alru_cache()
    async def _get_current_campaign(self) -> GlobalmapEvent:
        '''Cached

        Retrieves the latest clanwars campaign data

        Returns
        -------
        GlobalmapEvent
            The latest global map event, currently active or not

        Raises
        ------
        ApiError
            Getting the data failed
        '''
        data = await self.bot.wot_api('/wot/globalmap/events/')
        event_data = data['data'][0]
        str_to_dt = lambda dt_str: datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
        return GlobalmapEvent(
            name=event_data['event_name'],
            id=event_data['event_id'],
            status=try_enum(EventStatusType, event_data['status'].lower()),
            start=str_to_dt(event_data['start']),
            end=str_to_dt(event_data['end']),
            fronts=[GlobalMapFront(d['front_name'], d['front_id'], d['url']) for d in event_data['fronts']]
        )


    def _generate_requirements_image(self, moe_data: dict, moe_days: int, tank: Tank) -> discord.File:
        '''Generates a requirements image from previous Mark of Excellence
        requirements data

        Parameters
        ----------
        moe_data : dict
            The MoE data to base the image on
        moe_days : int
            The amount of days to graph the data for
        tank : Tank
            The tank to graph the data for

        Returns
        -------
        discord.File
            The MoE graph image
        '''
        plt.rcParams.update({
            'axes.facecolor': (0.3, 0.32, 0.36, 0.45),
            'savefig.facecolor': (0, 0, 0, 0)
        })
        dates = date2num([d['date'] for d in moe_data[:moe_days]])

        fig, axes = plt.subplots(len(self._moe_values), 1, sharex=True)
        fig.suptitle(
            f'MoE history for {tank.short_name}',
            fontsize=20,
            color='w'
        )
        for value, ax in zip(self._moe_values, axes.flatten()):
            ax.plot_date(
                x=dates,
                y=[d['marks'][value] for d in moe_data[:moe_days]],
                fmt='.-',
                color='w',
                label=value
            )
            ax.text(
                0.005,
                0.87,
                f'{value}%',
                ha='left',
                transform=ax.transAxes,
                color='w',
                fontsize=10
            )
            ax.tick_params(axis='both', colors='w')
            ax.xaxis.set_major_formatter(DateFormatter('%d-%m'))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=3, min_n_ticks=3))

        fig.autofmt_xdate(rotation=40)
        fig.tight_layout()

        fp = BytesIO()
        plt.savefig(fp, format='png')
        plt.close()
        fp.seek(0)
        return discord.File(fp, 'moe_history.png')


    async def _generate_mark_image(self, player: Player, separate_nations: bool, data: List[TankStats]) -> discord.File:
        '''Combines data into image displaying marks of excellence

        Parameters
        ----------
        player : Player
            The player the marks belong to
        separate_nations : bool
            Whether to separate nations with blank tiles
        data : List[TankStats]
            A list of TankStats containing a mark value

        Returns
        -------
        discord.File
            The image collage of all marks
        '''
        total_3_marks: int = sum([item.mark is MarkType.third_mark for item in data])
        total_2_marks: int = sum([item.mark is MarkType.second_mark for item in data])
        total_1_marks: int = sum([item.mark is MarkType.first_mark for item in data])
        total_marks: int = sum((total_1_marks, total_2_marks, total_3_marks))
        string_size, image_size, bar_height, font_size, columns = self._get_sizes(total_marks)

        # Needed to insert a blank tile
        blank_image = Image.new('RGBA', image_size, '#070906')

        images, last_nation, num_added = [], '', 0
        for tank_stats in data:
            # If we want to separate the nations from each other, we insert blank tiles
            if separate_nations:
                if tank_stats.nation != last_nation and last_nation:
                    images.extend([
                        blank_image.copy()
                        for _ in range((
                            (columns - (num_added % columns)) + (columns if num_added % columns else 0)
                        ))
                    ])
                    num_added = 0

                num_added += 1
                last_nation = tank_stats.nation

            # Get images
            tank_image = (await self._get_image_from_url(tank_stats.full_tank_image(string_size))).convert('RGBA')
            transparent_mark_image = (await self._get_image_from_url(tank_stats.mark_image_url)).convert('RGBA')

            # Make mark image background black
            mark_image = Image.new('RGBA', transparent_mark_image.size, '#070906')
            mark_image.paste(transparent_mark_image, (0, 0), transparent_mark_image)

            # Resize mark image to fit the tank image size
            mark_w, mark_h = mark_image.size
            mark_ratio = mark_w / mark_h
            new_mark_w = int(mark_ratio * tank_image.height)
            mark_image = mark_image.resize((new_mark_w, tank_image.height), Image.ANTIALIAS)

            # Combine mark and tank image
            new = Image.new('RGBA', (tank_image.width + mark_image.width, tank_image.height))
            new.paste(tank_image, (0, 0), tank_image)
            new.paste(mark_image, (tank_image.width, 0), mark_image)

            # Add image to iterable that we will combine into one image later
            images.append(new)

        combined = self._combine_images(images, columns, image_size)

        # Add text to the combined image
        final = ImageOps.expand(combined, (0, 0, 0, bar_height), '#070906')
        font = ImageFont.truetype('assets/fonts/Warhelios-Bold.ttf', font_size)
        draw = ImageDraw.Draw(final)
        footer = f"{player.nickname}'s 3 marks: {total_3_marks} - 2 marks: {total_2_marks} - 1 marks: {total_1_marks}\nGenerated by brankobot using herhor.net tank/moe images"
        text_w = draw.textsize(footer, font=font)[0]
        draw.text(
            xy=((combined.width - text_w) / 2, combined.height),
            text=footer,
            fill='white',
            font=font,
            align='center'
        )

        # Save the file to byte stream and return it as a discord.File
        fp = BytesIO()
        final.save(fp, format='png')
        fp.seek(0)
        return discord.File(fp, 'marks.png')


    async def _get_tank_stats(
        self,
        account_id: int,
        region: Region,
        nations: List[str],
        types: List[str],
        tiers: List[str],
        roles: List[str] = [],
        include_premiums: bool = True,
        include_normal: bool = True,
        include_collector: bool = True
    ) -> List[TankStats]:
        '''Returns tank stats for a player by their account ID

        Parameters
        ----------
        account_id : int
            The WoT account ID of the player you want tank stats for
        nations : List[str]
            The tank nations to filter to
        types : List[str]
            The tank types to filter to
        tiers : List[str]
            The tank tiers to filter to
        roles : List[str], optional
            The tank roles to filter to, by default []
        include_premiums : bool, optional
            Whether to include premium tanks, by default True
        include_normal : bool, optional
            Whether to include non-premium/non-collector tanks, by default True
        include_collector : bool, optional
            Whether to include collector tanks, by default True

        Returns
        -------
        List[TankStats]
            A list of TankStats for each tank de player has ever played

        Raises
        ------
        ApiError
            Getting the data failed
        '''
        premium, collector = [], []
        if include_normal:
            premium.append(0)
            collector.append(0)
        if include_premiums:
            premium.append(1)
        if include_collector:
            collector.append(1)

        payload = {
            'battle_type': 'random',
            'only_in_garage': False,
            'language': 'en',
            'spa_id': account_id,
            'premium': premium,
            'collector_vehicle': collector,
            'nation': nations,
            'role': roles,
            'type': types,
            'tier': tiers
        }

        data = await self.bot.wot_api(
            '/wotup/profile/vehicles/list/',
            method='POST',
            payload=payload,
            api_type=WotApiType.unofficial,
            region=region
        )
        # I have to do this because for some unholy reason,
        # the data here is a list of lists and not a mapping.
        # They also randomly change the order of this data 😃
        parsed_data = [
            dict(zip(data['data']['parameters'], stats))
            for stats in data['data']['data']
        ]

        tank_stats = []
        for stats in parsed_data:
            tank = self.bot.search_tank(stats['tech_name'])
            tank_stats.append(TankStats(
                **asdict(tank),
                total_kills=stats['frags_count'],
                average_kills=stats['frags_per_battle_average'],
                _mark=stats['marksOnGun'],
                damage_dealt_received_ratio=stats['damage_dealt_received_ratio'],
                wins_ratio=stats['wins_ratio'],
                total_wins=stats['wins_count'],
                total_hits=stats['hits_count'],
                total_damage_received=stats['damage_received'],
                _mastery=stats['markOfMastery'],
                kills_deaths_ratio=stats['frags_deaths_ratio'],
                total_damage=stats['damage_dealt'],
                average_xp=stats['xp_per_battle_average'],
                total_xp=stats['xp_amount'],
                total_survived_battles=stats['survived_battles'],
                total_battles=stats['battles_count'],
                average_damage=stats['damage_per_battle_average']
            ))

        return tank_stats


    async def _search_player(self, player_search: str, player_region: Region) -> Player:
        '''Searches for a WoT player on a region by player name

        Parameters
        ----------
        player_search : str
            The player name to search by
        player_region : Region
            The region to search in

        Returns
        -------
        Player
            The player, if found

        Raises
        ------
        InvalidNickname
            The player search doesn't match a valid WoT nickname
        PlayerNotFound
            No player was found by the player search query
        '''
        pattern = re.compile(r'^\w{3,24}$')
        if pattern.match(player_search) is None:
            raise InvalidNickname()

        data = await self.bot.wot_api(
            '/wot/account/list/',
            region=player_region,
            params={
                'limit': 1,
                'search': player_search
            }
        )

        if data['meta']['count'] == 0:
            raise PlayerNotFound(player_search, player_region)

        player_data = data['data'][0]
        return Player(
            player_data['nickname'],
            player_data['account_id'],
            player_region
        )


    async def _search_clan(self, clan_search: str, clan_region: Region) -> Clan:
        '''Searches for a WoT clan on a region by clan tag or name

        Parameters
        ----------
        clan_search : str
            The clan tag or name to search by
        clan_region : Region
            The region to search in

        Returns
        -------
        Clan
            The clan, if found

        Raises
        ------
        InvalidClan
            The clan search doesn't match a valid WoT clan name or tag
        ClanNotFound
            No clan was found by the clan search query
        '''
        pattern = re.compile(r'^[\w-]{2,20}$')
        if pattern.match(clan_search) is None:
            raise InvalidClan()

        data = await self.bot.wot_api(
            '/wot/clans/list/',
            region=clan_region,
            params={
                'limit': 1,
                'search': clan_search,
                'fields': 'clan_id,tag'
            }
        )

        if data['meta']['count'] == 0:
            raise ClanNotFound(clan_search, clan_region)

        clan_data = data['data'][0]
        return Clan(
            clan_data['tag'],
            clan_data['clan_id'],
            clan_region
        )



    @channel_check(BigRLDChannelType.battle_results, SmallRLDChannelType.battle_results)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(aliases=['replay'])
    async def replayinfo(self, ctx: Context, replay_message: discord.Message):
        '''Extracts info from a .wotreplay file'''
        async with ctx.loading(initial_message='Downloading') as loader:
            try:
                # Check if replay_message contains a .wotreplay file
                if atts := replay_message.attachments:
                    replay_file = atts[0]
                    if not replay_file.filename.endswith('.wotreplay'):
                        raise
                else:
                    raise ReplayError('No replays found in message')

                # Create tempfile and write replay data to it
                temp_file = NamedTemporaryFile(delete=False)
                temp_file.write(await replay_file.read())

                # Extract replay info
                await loader.update('Extracting')
                try:
                    replay = ReplayData(temp_file.name)
                    if not replay.replay.battle_data:
                        raise ReplayError('No data found in replay, did you quit before the game ended?')
                except:
                    raise ReplayError('Couldn\'t extract data from replay')

                achievements: List[Achievement] = list(filter(None, [
                    self.bot.ACHIEVEMENTS.get(id)
                    for id in replay.battle_performance.achievements
                ]))

                data = [
                    replay.battle_metadata,
                    replay.battle_performance,
                    replay.battle_players,
                    achievements,
                    replay.battle_economy,
                    replay.battle_xp
                ]

                # Start paginated view
                pages = ViewMenuPages(
                    source=ReplayPaginator(
                        data,
                        ctx,
                        replay.battle_metadata
                    ),
                    clear_reactions_after=True
                )
                await pages.start(ctx)

            finally: # Close temp file
                with suppress(PermissionError):
                    temp_file.close()
                    os.unlink(temp_file.name)


    @channel_check()
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(
        aliases=['markimage', 'markcollage'],
        usage='<player_search> [region: eu] [separate_nations: no (no for sorting by mark > tier, yes for sorting by nation > mark)] [nations: all (filter to nations)] [types: all (filter to types, can be lightTank, mediumTank, heavyTank, AT-SPG or SPG)] [tiers: all (filter to tiers)]'
    )
    async def showmarks(self, ctx: Context, player_search: str, *, flags: MarkCollageFlags):
        '''Will create a collage of all marks achieved by player'''
        player_region = flags.region
        separate_nations = flags.separate_nations
        nations = flags.nations
        types = flags.types
        tiers = flags.tiers

        async with ctx.loading(initial_message='Searching') as loader:
            player = await self._search_player(player_search, player_region)
            await loader.update('Filtering')
            filtered_data = list(filter(
                lambda item: item.mark is not MarkType.no_mark,
                await self._get_tank_stats(
                    player.id,
                    player_region,
                    nations,
                    types,
                    tiers
                )
            ))

            if not filtered_data:
                raise NoMoe(player.nickname, player_region)

            if separate_nations:
                sort_key = lambda item: (sum([d.nation == item.nation for d in filtered_data]), item.mark.value)
            else:
                sort_key = lambda item: (item.mark.value, item.tier)

            sorted_data = sorted(
                filtered_data,
                key=sort_key,
                reverse=True
            )
            await loader.update('Generating')
            _file = await self._generate_mark_image(
                player,
                separate_nations,
                sorted_data
            )
            player_name = escape_markdown(player.nickname)
            msg = dedent(f'''
                Marks of excellence achieved by **[{player_name}](https://wot-life.com/{player_region}/player/{player_name}/)**

                Types: {', '.join([separate_capitals(t) for t in types]) or 'all'}
                Nations: {', '.join(nations) or 'all'}
                Tiers: {', '.join(tiers) or 'all'}
            ''')
            await loader.update('Uploading')
            await ctx.send_response(
                msg,
                image='attachment://marks.png',
                files=_file
            )


    @channel_check(BigRLDChannelType.general, SmallRLDChannelType.general, BigRLDChannelType.recruiters, SmallRLDChannelType.recruiters)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(
        aliases=['servicerecord', 'showtankstats'],
        usage=f'<player_search> [region: eu] [nations: all (filter to nations)] [types: all (filter to types, can be lightTank, mediumTank, heavyTank, AT-SPG or SPG)] [tiers: all (filter to tiers)] [roles: all (filter to tank roles)] [includepremiums: yes] [includenormal: yes] [includecollectors: yes] [sortby: total_battles (can be {", ".join([k for k in TankStats.__dataclass_fields__.keys() if not k.startswith("_")])})]'
    )
    async def showstats(self, ctx: Context, player_search: str, *, flags: TankStatFlags):
        '''Shows tank stats for each tank played by a player'''
        player_region = flags.region
        nations = flags.nations
        types = flags.types
        tiers = flags.tiers
        roles = flags.roles
        sortby = flags.sort_by
        include_premiums = flags.include_premiums
        include_normal = flags.include_normal
        include_collectors = flags.include_collectors

        async with ctx.typing():
            player = await self._search_player(player_search, player_region)
            data = await self._get_tank_stats(
                player.id,
                player_region,
                nations,
                types,
                tiers,
                roles,
                include_premiums,
                include_normal,
                include_collectors
            )

            if not data:
                raise InvalidFlags()

            sorted_data = sorted(
                data,
                key=lambda item: tuple(getattr(item, sb, item.total_battles) for sb in sortby),
                reverse=True
            )

            data_formatted = []
            for stats in sorted_data:
                data_formatted.append((
                    stats.short_name,
                    dedent(f'''
                        {stats.tank_summary}

                        **Battles:** {intcomma(stats.total_battles)} ({intcomma(stats.total_survived_battles)} total battles survived)
                        **DPG:** {intcomma(stats.average_damage)} ({intcomma(stats.total_damage)} total damage)
                        **XP:** {intcomma(stats.average_xp)} ({intcomma(stats.total_xp)} XP total)
                        **Wins:** {stats.wins_ratio:.2f}% ({intcomma(stats.total_wins)} total wins)
                        **K/D ratio:** {stats.kills_deaths_ratio:.2f} ({intcomma(stats.total_kills)} total kills)
                        **Damage ratio:** {stats.damage_dealt_received_ratio:.2f} ({intcomma(stats.total_damage_received)} total received)
                        **Mark:** {getattr(Emote, f'{stats.nation}_{stats._mark}', 'No Mark')}
                        **Mastery:** {getattr(Emote, stats.mastery.name, 'No Mastery')}
                    '''),
                    stats.big_icon
                ))

            pages = ViewMenuPages(
                source=TankStatsPaginator(
                    data_formatted,
                    ctx,
                    player.nickname,
                    player.wotlife_url
                ), clear_reactions_after=True
            )
            await pages.start(ctx)


    @channel_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(
        aliases=['moe', 'reqs', 'marks'],
        usage='<tank_search (input names with spaces should be surrounded with quotes: ")> [region: eu] [moedays: 10 (days to graph moe history for)]'
    )
    async def requirements(self, ctx: Context, tank_search: str, *, flags: RequirementsFlags):
        '''Retrieves information about moe/mastery/expected values and more'''
        moe_region = flags.region
        moe_days = flags.moe_days

        async with ctx.loading(initial_message='Gathering') as loader:
            tank = self.bot.search_tank(tank_search, 'short_name')
            embed = await ctx.send_response(
                tank.tank_summary,
                title=f'{str(moe_region).upper()} requirements for {tank.short_name}',
                thumbnail=tank.big_icon,
                send=False
            )

            # MoE information
            if tank.tier >= 5:
                async with self.bot.AIOHTTP_SESSION.get(f'https://gunmarks.poliroid.ru/api/{str(moe_region).lower()}/vehicle/{tank.id}/65,85,95,100') as r:
                    if r.status != 200:
                        raise ApiError(r.status)

                    json_r = await r.json()
                    moe_data = json_r['data']
                    curr_marks = moe_data[0]['marks'] # Latest mark data is first in list

                await loader.update('Generating')
                _file = self._generate_requirements_image(moe_data, moe_days, tank)
                embed.set_image(url=f'attachment://moe_history.png')
                embed.add_field(
                    name='MoE (combined)',
                    value=dedent(f'''
                        {try_enum(Emote, f'{tank.nation}_1')} {curr_marks['65']}
                        {try_enum(Emote, f'{tank.nation}_2')} {curr_marks['85']}
                        {try_enum(Emote, f'{tank.nation}_3')} {curr_marks['95']}
                        :100: {curr_marks['100']}
                    ''')
                )

            await loader.update('Gathering')

            # Mastery information
            async with self.bot.AIOHTTP_SESSION.get(f'https://mastery.poliroid.ru/api/{str(moe_region).lower()}/vehicle/{tank.id}') as r:
                if r.status != 200:
                    raise ApiError(r.status)

                json_r = await r.json()
                mastery_data = json_r['data'][0]['mastery']
                embed.add_field(
                    name='Mastery (XP)',
                    value=dedent(f'''
                        {Emote.third_class} {mastery_data[0]}
                        {Emote.second_class} {mastery_data[1]}
                        {Emote.first_class} {mastery_data[2]}
                        {Emote.mastery} {mastery_data[3]}
                    ''')
                )

            # Requirements information
            if moe_region is Region.eu:
                async with self.bot.AIOHTTP_SESSION.get(f'https://www.wotgarage.net/{tank.nation}/{tank.tier}/{tank.id}/{tank.internal_name}') as r:
                    if r.status != 200:
                        raise ApiError(r.status)

                    text_r = await r.text()
                    soup = BeautifulSoup(text_r, 'html.parser')
                    wn8_row = soup.find('div', {'class': 'col-md-5 tank-wn8'})
                    wn8_yellow = wn8_row.find('div', {'class': 'col-xs-3 wn8 wn8-yellow'}).string
                    wn8_green = wn8_row.find('div', {'class': 'col-xs-3 wn8 wn8-green'}).string
                    wn8_blue = wn8_row.find('div', {'class': 'col-xs-3 wn8 wn8-blue'}).string
                    wn8_purple = wn8_row.find('div', {'class': 'col-xs-3 wn8 wn8-purple'}).string

                    expected_row = soup.find('div', {'class': 'col-md-7 tank-exp clearfix'}).find_all('div', {'class': 'col-xs-6 col-sm-3'})
                    expected_kills = expected_row[0].find('strong').string
                    expected_spots = expected_row[1].find('strong').string
                    expected_defense = expected_row[2].find('strong').string
                    expected_winrate = expected_row[3].find('strong').string

                    shots_row = soup.find_all('div', {'class': 'guns-wrapper'})[-1]
                    if wn8_row:
                        shots_yellow = shots_row.find_all('div', {'class': 'col-xs-3 wn8 wn8-yellow'})[-1].string
                        shots_green = shots_row.find_all('div', {'class': 'col-xs-3 wn8 wn8-green'})[-1].string
                        shots_blue = shots_row.find_all('div', {'class': 'col-xs-3 wn8 wn8-blue'})[-1].string
                        shots_purple = shots_row.find_all('div', {'class': 'col-xs-3 wn8 wn8-purple'})[-1].string
                        embed.url = f'https://www.wotgarage.net/{tank.nation}/{tank.tier}/{tank.id}/'
                        embed.add_field(
                            name='WN8 (dmg)',
                            value=dedent(f'''
                                :yellow_circle: {wn8_yellow} ({shots_yellow} shots)
                                :green_circle: {wn8_green} ({shots_green} shots)
                                :blue_circle: {wn8_blue} ({shots_blue} shots)
                                :purple_circle: {wn8_purple} ({shots_purple} shots)
                            ''')
                        )
                        embed.add_field(
                            name='Average',
                            value=dedent(f'''
                                {Emote.kill} {expected_kills} kills
                                {Emote.spot} {expected_spots} spots
                                {Emote.defend} {expected_defense} def points
                                {Emote.win} {expected_winrate} winrate
                            ''')
                        )
                        embed.add_field(
                            name='\u200b',
                            value='\u200b'
                        )

            embed.insert_field_at(
                2,
                name='\u200b',
                value='\u200b'
            )
            if tank.tier >= 5:
                await loader.update('Uploading')
                await ctx.send(embed=embed, file=_file)
            else:
                await ctx.send(embed=embed)


    @channel_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(aliases=['clansearch', 'c'], usage='<clan_search> [clan_region=eu]')
    async def clan(self, ctx: Context, clan_search: str, clan_region: RegionConverter = Region.eu):
        '''Uses WoTs API and WoT-life to return clan statistics'''
        async with ctx.typing():
            clan = await self._search_clan(clan_search, clan_region)
            clean_clan_tag = escape_markdown(clan.tag)

            # clan languages
            data = await self.bot.wot_api(
                f'/clans/wot/{clan.id}/api/claninfo/',
                api_type=WotApiType.wargaming,
                region=clan_region
            )
            try:
                languages = []
                for abbrv in data['clanview']['profiles'][1]['languages_list']:
                    languages.append(iso639.to_name(abbrv).split(';', maxsplit=1)[0])
            except KeyError:
                languages = ['Not Found']

            # average WN8
            async with self.bot.AIOHTTP_SESSION.get(clan.wotlife_url) as r:
                if r.status != 200:
                    raise ApiError(r.status)

                text_r = await r.text()
                soup = BeautifulSoup(text_r, 'html.parser')
                table = soup.find('table', {'class': 'fulltable'})
                td = table.find('td', text='Ø WN8')
                td2 = td.find_next_siblings('td')
                clan_average_wn8 = int(td2[0].text.replace(',', '')) / 100

            # ELO ratings, efficiency
            data = await self.bot.wot_api(
                '/wot/clanratings/clans/',
                region=clan_region,
                params={
                    'clan_id': clan.id,
                    'fields': 'fb_elo_rating_10,fb_elo_rating_8,fb_elo_rating_6,efficiency,wins_ratio_avg,battles_count_avg,global_rating_avg'
                }
            )
            data = data['data'][str(clan.id)]

            # Average winrate of players
            _data = data['wins_ratio_avg']
            winrate_v = _data['value']
            winrate_r = _data['rank']
            winrate_t = self._get_trend(_data['rank_delta'])

            # Average amount of battles of players
            _data = data['battles_count_avg']
            battles_v = _data['value']
            battles_r = _data['rank']
            battles_t = self._get_trend(_data['rank_delta'])

            # Average personal rating of players
            _data = data['global_rating_avg']
            rating_v = _data['value']
            rating_r = _data['rank']
            rating_t = self._get_trend(_data['rank_delta'])

            # ELO tier 10
            _data = data['fb_elo_rating_10']
            eSH_10_v = _data['value']
            eSH_10_r = _data['rank']
            eSH_10_t = self._get_trend(_data['rank_delta'])

            # ELO tier 8
            _data = data['fb_elo_rating_8']
            eSH_8_v = _data['value']
            eSH_8_r = _data['rank']
            eSH_8_t = self._get_trend(_data['rank_delta'])

            # ELO tier 6
            _data = data['fb_elo_rating_6']
            eSH_6_v = _data['value']
            eSH_6_r = _data['rank']
            eSH_6_t = self._get_trend(_data['rank_delta'])

            # Clan efficiency
            _data = data['efficiency']
            efficiency_v = _data['value']
            efficiency_r = _data['rank']
            efficiency_t = self._get_trend(_data['rank_delta'])

            # Other details
            data = await self.bot.wot_api(
                '/wot/clans/info/',
                region=clan_region,
                params={
                    'clan_id': clan.id,
                    'fields': 'leader_name,members_count,tag,motto,name,emblems.x256,color,created_at,old_tag'
                }
            )
            clan_data = data['data'][str(clan.id)]
            creation_date = datetime.fromtimestamp(clan_data['created_at'])

            previous_tag = ''
            if old := clan_data.get('old_tag'):
                if old != clan.tag and old is not None:
                    previous_tag = f', previously [{escape_markdown(old)}]'

            if len(languages) >= 3:
                languages = f'{", ".join(languages[0:2])}\nand {languages[2]}'
            else:
                languages = ' and '.join(languages)

            rating = lambda i: '#' + str(i) if i else 'unranked'
            fields = [
                ('Commander', f'[{escape_markdown(clan_data["leader_name"])}](https://en.wot-life.com/{clan_region}/player/{clan_data["leader_name"]}/)'),
                ('Created', format_dt(creation_date, 'R')),
                ('Members', clan_data['members_count']),
                ('Speaking', languages),
                ('Efficiency', f'{efficiency_v} ({efficiency_t}, {"#" + str(efficiency_r) if efficiency_r else "unranked"})'),
                ('Avg WN8', int(clan_average_wn8)),
                ('Avg winrate ', f'{winrate_v:.1f}% ({winrate_t}, {rating(winrate_r)})'),
                ('Avg battles', f'{battles_v:.0f} ({battles_t}, {rating(battles_r)})'),
                ('Avg PR', f'{rating_v:.0f} ({rating_t}, {rating(rating_r)})'),
                ('T10 ELO', f'{eSH_10_v} ({eSH_10_t}, {rating(eSH_10_r)})'),
                ('T8 ELO', f'{eSH_8_v} ({eSH_8_t}, {rating(eSH_8_r)})'),
                ('T6 ELO', f'{eSH_6_v} ({eSH_6_t}, {rating(eSH_6_r)})')
            ]

            if clan_data.get('motto'):
                fields.append(('Clan motto', f'*{escape_markdown(clan_data["motto"])}*', False))

            await ctx.send_response(
                f'• __*{clan.official_md_url}*__ ‎‏‏‎ ‎‏‏‎ ‎‏‏‎ ‎‏‏‎ ‏‏‎ ‎‎• __*{clan.wotlife_md_url}*__',
                colour=int(clan_data['color'].replace('#', ''), 16),
                fields=fields,
                title=f'{clan_data["name"]} [{clean_clan_tag}] ({str(clan_region).upper()}){previous_tag}',
                thumbnail=clan_data['emblems']['x256']['wowp']
            )


    @channel_check(BigRLDChannelType.recruiters, SmallRLDChannelType.recruiters)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(aliases=['playersearch'], usage='<player_search> [player_region=eu]')
    async def player(self, ctx: Context, player_search: str, player_region: RegionConverter = Region.eu):
        '''Uses WoTs API and WoT-life to return player statistics'''
        async with ctx.typing():
            player = await self._search_player(player_search, player_region)

            # Account details
            data = await self.bot.wot_api(
                '/wot/account/info/',
                region=player_region,
                params={
                    'account_id': player.id,
                    'fields': 'created_at,last_battle_time,statistics.all,global_rating'
                }
            )
            data = data['data'][str(player.id)]
            stats = data['statistics']['all']
            max_damage = stats['max_damage']
            max_xp = stats['max_xp']
            max_frags = stats['max_frags']
            creation_date = datetime.fromtimestamp(data['created_at'])
            last_battle = datetime.fromtimestamp(data['last_battle_time'])
            personal_rating = data['global_rating']

            # MoE amounts
            async with self.bot.AIOHTTP_SESSION.get(f'https://stats.modxvm.com/en/stats/players/{player.id}') as r:
                _3_marks, _2_marks, _1_marks = 'N/A', 'N/A', 'N/A'
                text_r = await r.text()
                soup = BeautifulSoup(text_r, 'html.parser')
                div = soup.find('div', {'class': 'col-12 col-md-6 col-lg-3 px-2 py-4'})
                if div:
                    _3_marks, _2_marks, _1_marks = div.find('div', {'class': 'h2'}).string.split('/')

            # Tanks played with
            data = await self.bot.wot_api(
                '/wot/account/tanks/',
                region=player_region,
                params={
                    'account_id': player.id,
                    'fields': 'statistics.battles,tank_id'
                }
            )
            data = data['data'][str(player.id)]
            battles_per_class = {
                'LT: ': 0,
                'MT: ': 0,
                'HT: ': 0,
                'TD: ': 0,
                'SPG:': 0
            }
            for dic in data:
                battles = dic['statistics']['battles']
                tank = self.bot.TANKS.get(dic['tank_id'])
                if tank:
                    tank_type = tank.formatted_type
                    if tank_type == 'light tank':
                        battles_per_class['LT: '] += battles
                    elif tank_type == 'medium tank':
                        battles_per_class['MT: '] += battles
                    elif tank_type == 'heavy tank':
                        battles_per_class['HT: '] += battles
                    elif tank_type == 'tank destroyer':
                        battles_per_class['TD: '] += battles
                    else:
                        battles_per_class['SPG:'] += battles

            # WoT-life values
            async with self.bot.AIOHTTP_SESSION.get(player.wotlife_url) as r:
                if r.status != 200:
                    raise ApiError(r.status)

                text_r = await r.text()
                soup = BeautifulSoup(text_r, 'html.parser')
                table = soup.find('table', {'class': 'stats-table table-md'})

                clan_div = soup.find('div', {'class': 'clan'})
                clan_tag, clan_logo = None, None
                if clan_div:
                    clan_logo = clan_div.find('img').get('src')
                    clan_tag = clan_div.find('div', {'class': 'clan-tag'}).find('a').get_text().split(' ')[0]

                # WN8
                td1 = table.find('th', text='WN8').find_next_siblings('td')
                _total_wn8 = int(td1[0].text.replace(',', '')) / 100
                _24h_wn8 = int(td1[1].text.replace(',', '')) / 100
                _30d_wn8 = int(td1[3].text.replace(',', '')) / 100

                # Average tier
                td2 = table.find('th', text='Ø Tier').find_next_siblings('td')
                _total_tier = float(td2[0].text.replace(',', '.'))
                _24h_tier = float(td2[1].text.replace(',', '.'))
                _30d_tier = float(td2[3].text.replace(',', '.'))

                # DPG
                td3 = table.find('th', text='Damage dealt').find_next_siblings('td')
                _total_dpg = int(td3[0].text.replace(',', '').replace('.', '')) / 100
                _24h_dpg = int(td3[1].text.replace(',', '').replace('.', '')) / 100
                _30d_dpg = int(td3[3].text.replace(',', '').replace('.', '')) / 100

                # Battles played
                td4 = table.find('th', text='Battles').find_next_siblings('td')
                _total_battles = int(td4[0].text)
                _24h_battles = int(td4[1].text)
                _30d_battles = int(td4[3].text)

                # Winrate
                td5 = table.find('th', text='Victories').find_next_siblings('td')
                _total_winrate = int(td5[1].text.replace(',', '').replace('%', '')) / 100
                _24h_winrate = int(td5[3].text.replace(',', '').replace('%', '')) / 100
                _30d_winrate = int(td5[7].text.replace(',', '').replace('%', '')) / 100

            for wn8_range, colour in self._wn8_colour_mapping.items():
                if int(_total_wn8) in wn8_range:
                    colour = colour.value
                    break

            nl = '\n'
            # this actually throws an OSError on my windows
            # pc when the user hasn't ever played the game,
            # because UNIX epoch won't work with whatever WG
            # is using
            # https://stackoverflow.com/questions/59199985/why-is-datetimes-timestamp-method-returning-oserror-errno-22-invalid-a
            fields = [
                ('Personal rating', personal_rating),
                ('Created', format_dt(creation_date, 'R')),
                ('Last played', format_dt(last_battle, 'R')),
                ('Battles', f'''```\n{nl.join([(f'{k.ljust(9)}{v}') for k, v in sorted(battles_per_class.items(), key=lambda item: item[1], reverse=True)])}\n```''')
            ]
            fields.append((
                'Record',
                dedent(f'''
                ```
                Damage:  {max_damage}
                XP:      {max_xp}
                Kills:   {max_frags}
                \u200b
                \u200b
                ```
                ''')
            ))
            fields.append((
                'MoE',
                dedent(f'''
                ```
                1 marks: {_1_marks}
                2 marks: {_2_marks}
                3 marks: {_3_marks}
                \u200b
                \u200b
                ```
                ''')
            ))
            fields.append((
                'Total avg',
                dedent(f'''
                ```
                Battles: {_total_battles}
                Tier:    {_total_tier}
                Winrate: {_total_winrate:.1f}
                DPG:     {_total_dpg:.0f}
                WN8:     {_total_wn8:.0f}
                ```
                ''')
            ))
            fields.append((
                'Last 30d avg',
                dedent(f'''
                ```
                Battles: {_30d_battles}
                Tier:    {_30d_tier}
                Winrate: {_30d_winrate:.1f}
                DPG:     {_30d_dpg:.0f}
                WN8:     {_30d_wn8:.0f}
                ```
                ''')
            ))
            fields.append((
                'Last 24h avg',
                dedent(f'''
                ```
                Battles: {_24h_battles}
                Tier:    {_24h_tier}
                Winrate: {_24h_winrate:.1f}
                DPG:     {_24h_dpg:.0f}
                WN8:     {_24h_wn8:.0f}
                ```
                ''')
            ))

            await ctx.send_response(
                f'• __*{player.official_md_url}*__‎‎‎‏‏‎ ‎‏‏‎ ‎‏‏‎ ‎‏‏‎ ‎‏‏‎ ‎‏‏‎ ‎• __*{player.wotlife_md_url}*__',
                title=f'{escape_markdown(player.nickname)} {clan_tag or ""} ({str(player_region).upper()})',
                colour=colour,
                thumbnail=f'https://wot-life.com/{clan_logo}',
                fields=fields
            )


    # Doesn't work anymore; responds with http 403 even with a bunch of obscure headers
    # the API is bunch of trouble to sign up for so fuck that
    # @channel_check()
    # @role_check()
    # @commands.cooldown(1, 30, commands.BucketType.guild)
    # @commands.command(aliases=['status', 'wot_status'])
    # async def wotstatus(self, ctx: Context):
    #     '''Pings WoT servers and shows reported server problems if any'''
    #     async with ctx.typing():
    #         async with self.bot.AIOHTTP_SESSION.get('https://downdetector.com/status/world-of-tanks/') as r:
    #             if r.status != 200:
    #                 raise ApiError(r.status)

    #             text_r = await r.text()
    #             soup = BeautifulSoup(text_r, 'html.parser')
    #             container = soup.find('div', class_='container main-container px-3 px-md-0')
    #             status_string = container.find('div', class_='text-center').find(string=re.compile('problems|Problems'))
    #             problems_container = container.find('div', class_='card p-4 w-100 h-100 d-inline-block').find('div', class_='row')
    #             problems = problems_container.find_all('div', class_='text-center text-muted')
    #             percentages = problems_container.find_all('div', class_='text-center font-weight-bold')

    #             # Ping some servers
    #             flags = {'verbose': False, 'count': 5, 'size': 40}
    #             EU1_status = ping('login.p1.worldoftanks.eu', **flags).rtt_avg_ms
    #             EU2_status = ping('login.p2.worldoftanks.eu', **flags).rtt_avg_ms
    #             USC_status = ping('wotna3.login.wargaming.net', **flags).rtt_avg_ms

    #             fields = [
    #                 ('EU1 ping', f'{EU1_status:.0f}ms'),
    #                 ('EU2 ping', f'{EU2_status:.0f}ms'),
    #                 ('USC ping', f'{USC_status:.0f}ms')
    #             ]
    #             for problem, percentage in zip(problems, percentages):
    #                 fields.append((problem.text, percentage.text))

    #             await ctx.send_response(
    #                 f'**Global Status:** {status_string}',
    #                 title='World of Tanks Status',
    #                 url='https://downdetector.com/status/world-of-tanks/',
    #                 fields=fields
    #             )


    @commands.group(invoke_without_command=True, aliases=['clanwars', 'gm', 'globalmap'])
    @commands.cooldown(5, 60, commands.BucketType.guild)
    async def cw(self, _):
        '''Group command for cw clanlogs/battles/rewards/provinces/leaderboards'''

    @cw.command('clanlog', aliases=['history', 'log', 'activity', 'logs'])
    async def cw_clanlog(self, ctx: Context, clan_search: str = '-RLD-', page: int = 1):
        '''Shows a clans activity log'''
        async with ctx.typing():
            clan = await self._search_clan(clan_search, Region.eu)
            clean_clan_tag = escape_markdown(clan.tag)

            # Getting clanlogs
            data = await self.bot.wot_api(
                f'/globalmap/game_api/clan/{clan.id}/log',
                api_type=WotApiType.wargaming,
                params={
                    'category': 'all',
                    'page_size': 30,
                    'page_number': page
                }
            )
            log_data = data['data']

            if not log_data:
                return await ctx.reply(f'{clean_clan_tag} has no battles registered yet', delete_after=60, mention_author=False)

            # Formatting clanlogs
            data_formatted = []
            for dic in log_data:
                dt = format_dt(datetime.strptime(dic['created_at'], '%Y-%m-%d %H:%M:%S.%f'), 'R')
                emote, message = self._format_clan_log(dic)
                data_formatted.append((
                    f'{emote} {dt}',
                    message
                ))

            # Paginating clanlogs
            description = '*Times are in CET*'
            pages = ViewMenuPages(
                source=ClanWarsPaginator(
                    data_formatted,
                    ctx,
                    description,
                    title=f'Clan log for {clean_clan_tag}',
                    url=f'https://eu.wargaming.net/globalmap/#clanlog/{clan.id}'
                ), clear_reactions_after=True
            )
            await pages.start(ctx)

    @cw.command('battles')
    async def cw_battles(self, ctx: Context, clan_search: str = '-RLD-'):
        '''Shows upcoming battles information for specified clan'''
        async with ctx.typing():
            clan = await self._search_clan(clan_search, Region.eu)
            clean_clan_tag = escape_markdown(clan.tag)

            # Getting battles
            data = await self.bot.wot_api(
                '/wot/globalmap/clanbattles/',
                params={'clan_id': clan.id}
            )
            battle_data = [
                d for d in data['data'] if not
                (datetime.now() - timedelta(minutes=15)) > datetime.fromtimestamp(d['time'])
            ]

            if not battle_data:
                return await ctx.reply(f'{clean_clan_tag} has no battles registered yet', delete_after=60, mention_author=False)

            # Formatting battles
            data_formatted = []
            total_battles = 0
            for dic in battle_data:
                battle_start = datetime.fromtimestamp(dic['time'])
                total_battles += 1
                front = try_enum(FrontType, dic['front_id'])

                # Opponent clantag
                data = await self.bot.wot_api(
                    '/wot/globalmap/claninfo/',
                    params={
                        'clan_id': dic['competitor_id'],
                        'fields': 'tag'
                    }
                )
                clean_opponent_clan_tag = escape_markdown(data['data'][str(dic['competitor_id'])]['tag'])

                # Province map
                data = await self.bot.wot_api(
                    '/wot/globalmap/provinces/',
                    params={
                        'front_id': dic['front_id'],
                        'province_id': dic['province_id'],
                        'fields': 'arena_name'
                    }
                )
                map = data['data'][0]['arena_name']

                data_formatted.append((
                    f'{dic["province_name"]} (t{dic["vehicle_level"]})',
                    dedent(f'''
                        **Map:** {map}
                        **Type:** {dic['type']} ({dic['attack_type'] or 'landing'})
                        **Start time:** {format_dt(battle_start, 'T')}
                        **Against:** [{clean_opponent_clan_tag}](https://wot-life.com/eu/clan/{clean_opponent_clan_tag}/)
                        **Front:** {front}
                    ''')
                ))

            # Paginating battles
            description = dedent(f'''
                **Total battles:** {total_battles}
                *Times are in CET*
            ''')
            pages = ViewMenuPages(
                source=ClanWarsPaginator(
                    data_formatted,
                    ctx,
                    description,
                    title=f'Battles for {clean_clan_tag}',
                    url=f'https://eu.wargaming.net/globalmap/#battles/{clan.id}'
                ), clear_reactions_after=True
            )
            await pages.start(ctx)

    # COMMAND DOESNT WORK BECAUSE WOT API JUST SENDS BACK EMPTY RESULTS LOL
    # {'award_level': None, 'account_id': 500600567, 'clan_rank': None, 'rank_delta': None, 'fame_points_to_improve_award': None, 'updated_at': None, 'battles': 0, 'event_id': 'confrontation', 'clan_id': None, 'rank': None, 'fame_points_since_turn': 0, 'url': None, 'battles_to_award': 0, 'fame_points': 0, 'front_id': 'confrontation_bg'}
    # @cw.command('rewards', aliases=['accstatus', 'status'])
    # async def cw_rewards(self, ctx: Context, player_search: str):
    #     '''Shows some data about your account, including current rewards in CW'''
    #     async with ctx.typing():
    #         player = await self._search_player(player_search, Region.eu)
    #         event = await self._get_current_campaign()
    #         front_id = event.fronts[0].id

    #         # Player information
    #         data = await self.bot.wot_api(
    #             '/wot/globalmap/eventaccountinfo/',
    #             params={
    #                 'account_id': player.id,
    #                 'event_id': event.id,
    #                 'front_id': front_id
    #             }
    #         )
    #         player_data = data['data'][str(player.id)]['events'][event.id][0]
    #         clan_id = player_data['clan_id']

    #         # Clan information
    #         data = await self.bot.wot_api(
    #             '/wot/globalmap/eventclaninfo/',
    #             params={
    #                 'clan_id': clan_id,
    #                 'event_id': event.id,
    #                 'front_id': front_id
    #             }
    #         )
    #         clan_data = data['data'][str(clan_id)]['events'][event.id][0]

    #         # Get player rewards
    #         data = await self.bot.wot_api(
    #             '/en/clanwars/rating/alley/users/search/byaccount/',
    #             params={
    #                 'event_id': event.id,
    #                 'front_id': front_id,
    #                 'page': 0,
    #                 'page_size': 1,
    #                 'user': player.nickname
    #             },
    #             api_type=WotApiType.unofficial
    #         )

    #         for dic in data['accounts_ratings']:
    #             if dic['name'] == player.nickname:
    #                 player_reward_data = dic
    #                 clan_tag = player_reward_data['clan']['tag']

    #         # Get clan rewards
    #         data = await self.bot.wot_api(
    #             '/en/clanwars/rating/alley/clans/search/',
    #             params={
    #                 'event_id': event.id,
    #                 'front_id': front_id,
    #                 'page': 0,
    #                 'page_size': 1,
    #                 'clan': clan_tag
    #             },
    #             api_type=WotApiType.unofficial
    #         )

    #         for dic in data['clans_ratings']:
    #             if dic['clan_tag'] == clan_tag:
    #                 clan_reward_data = dic

    #         player_rank_trend = self._get_trend(player_data['rank_delta'])
    #         clan_rank_trend = self._get_trend(clan_data['rank_delta'])
    #         fields = []
    #         fields.append((
    #             player.nickname,
    #             dedent(f'''
    #                 **Rank:** {player_data['rank']}
    #                 **Trend:** {player_rank_trend}
    #                 **Fame points:** {intcomma(player_data['fame_points'])}
    #                 **Battles:** {player_data['battles']}
    #                 **Fame points for improved reward:** {intcomma(player_reward_data['fame_points_to_improve_award'])}
    #             ''')
    #         ))
    #         fields.append((
    #             escape_markdown(clan_tag),
    #             dedent(f'''
    #                 **Rank:** {player_data['clan_rank']}
    #                 **Trend:** {clan_rank_trend}
    #                 **Fame points:** {intcomma(clan_data['fame_points'])}
    #                 **Battles/winrate:** {clan_data['battles']}/{(clan_data['wins'] / clan_data['battles'] * 100):.2f}%
    #                 **Fame points for improved reward:** {intcomma(clan_reward_data['fame_points_to_improve_award'])}
    #             ''')
    #         ))
    #         fields.append((
    #             'Player Rewards',
    #             '\n'.join([(f'**{d["reward_type"].replace("_", " ").title()}:** {d["value"]}') for d in player_reward_data['rewards']]) if player_reward_data['rewards'] else 'N/A'
    #         ))
    #         fields.append((
    #             'Clan Rewards',
    #             '\n'.join([(f'**{d["reward_type"].replace("_", " ").title()}:** {d["value"]}') for d in clan_reward_data['rewards']]) if clan_reward_data['rewards'] else 'N/A'
    #         ))

    #         await ctx.send_response(
    #             f'Last updated {format_dt(datetime.fromtimestamp(player_data["updated_at"]), "R")}',
    #             title='GM Status',
    #             fields=fields,
    #             url=f'https://worldoftanks.eu/en/clanwars/rating/alley/#wot&aof_front={event.id}&aof_rating=accounts&aof_filter=search_acc&aof_str={player_search}&aof_page=0&aof_size=1',
    #         )

    @cw.command('provinces', aliases=['prov'])
    async def cw_provinces(self, ctx: Context, clan_search: str = '-RLD-'):
        '''Shows all provinces for specified clan'''
        async with ctx.typing():
            clan = await self._search_clan(clan_search, Region.eu)
            clean_clan_tag = escape_markdown(clan.tag)

            # Getting provinces
            data = await self.bot.wot_api(
                '/wot/globalmap/clanprovinces/',
                params={
                    'clan_id': clan.id,
                    'fields': 'arena_name,daily_revenue,front_name,landing_type,max_vehicle_level,pillage_end_at,prime_time,province_name,revenue_level,turns_owned,front_id'
                }
            )
            province_data = data['data'][str(clan.id)]

            if not province_data:
                return await ctx.reply(f'{clean_clan_tag} has no provinces yet', delete_after=60, mention_author=False)

            # Formatting provinces
            data_formatted, total_income = [], 0
            for dic in province_data:
                total_income += dic.get('daily_revenue', 0)
                front = try_enum(FrontType, dic['front_id'])
                data_formatted.append((
                    f'{dic["province_name"]} (t{dic["max_vehicle_level"]})',
                    dedent(f'''
                        **Map:** {dic['arena_name']}
                        **Type:** {dic['landing_type'] or 'landing'}
                        **Prime time:** {dic['prime_time']}
                        **Turns owned:** {dic['turns_owned']}
                        **Front:** {front}
                    ''')
                ))

            # Paginating provinces
            description = dedent(f'''
                **Total provinces:** {len(data)}
                **Daily income:** {total_income} gold
                *Times are in CET*
            ''')
            pages = ViewMenuPages(
                source=ClanWarsPaginator(
                    data_formatted,
                    ctx,
                    description,
                    title=f'Provinces for {clean_clan_tag}',
                    url=f'https://eu.wargaming.net/globalmap/#clanlog/{clan.id}'
                ), clear_reactions_after=True
            )
            await pages.start(ctx)


    @cw.group('leaderboard', aliases=['top10'])
    async def cw_leaderboard(self, _):
        '''Shows top 10 clans and players for the current campaign'''

    @cw_leaderboard.command(
        'clans',
        aliases=['clan'],
        usage='[page=1 (page 1 shows clans 1 through 25, page 2 25 through 50, etc)]'
    )
    async def cw_leaderboard_clans(self, ctx: Context, page: int = 1):
        async with ctx.typing():
            page -= 1
            event = await self._get_current_campaign()
            front_id = event.fronts[0].id

            # Getting clan leaderboard
            data = await self.bot.wot_api(
                '/en/clanwars/rating/alley/clans/',
                api_type=WotApiType.unofficial,
                params={
                    'event_id': event.id,
                    'front_id': front_id,
                    'page_size': 25,
                    'page': page
                }
            )
            top_clans = data['clans_ratings']

            # Formatting clan leaderboard
            data_formatted = []
            for dic in top_clans:
                rank_trend = self._get_trend(dic['rank_change'])
                data_formatted.append((
                    f'#{dic["rank"]} - {escape_markdown(dic["clan_tag"])}',
                    dedent(f'''
                        **Fame points:** {intcomma(dic['total_fame_points'])}
                        **Needed to ascend:** {dic['fame_points_to_improve_award']}
                        **Trend:** {rank_trend}
                        **Bond multiplier:** {dic['rewards'][0]['value']}
                        **Gold reward:** {intcomma(dic['rewards'][1]['value'])}
                    ''')
                ))

            # Paginating clan leaderboard
            pages = ViewMenuPages(
                source=ClanWarsPaginator(
                    data_formatted,
                    ctx,
                    f'{event.name.capitalize()} started {format_dt(event.start, "R")}, and ends {format_dt(event.end, "R")}',
                    title='Clan Leaderboard',
                    url=f'https://worldoftanks.eu/en/clanwars/rating/alley/#wot&aof_front={front_id}&aof_rating=clans&aof_filter=all&aof_page={page}&aof_size=50'
                ), clear_reactions_after=True
            )
            await pages.start(ctx)

    @cw_leaderboard.command(
        'players',
        aliases=['player', 'people'],
        usage='[page=1 (page 1 shows players 1 through 25, page 2 25 through 50, etc)]'
    )
    async def cw_leaderboard_players(self, ctx: Context, page: int = 1):
        async with ctx.typing():
            page -= 1
            event = await self._get_current_campaign()
            front_id = event.fronts[0].id

            # Getting player leaderboard
            data = await self.bot.wot_api(
                '/en/clanwars/rating/alley/users/',
                api_type=WotApiType.unofficial,
                params={
                    'event_id': event.id,
                    'front_id': front_id,
                    'page_size': 25,
                    'page': page
                }
            )
            top_players = data['accounts_ratings']

            # Formatting player leaderboard
            data_formatted = []
            for dic in top_players:
                rank_trend = self._get_trend(dic['rank_change'])
                data_formatted.append((
                    f'#{dic["rank"]} - {dic["name"]}',
                    dedent(f'''
                        **Fame points:** {intcomma(dic['fame_points'])}
                        **Clan:** [{dic['clan']['tag']}](https://wot-life.com/eu/clan/{dic['clan']['tag']}/) (#{dic['clan_rank']} ranking)
                        **Trend:** {rank_trend}
                        **Battles played:** {dic['battles_count']}
                        **Rewards:** {', '.join(dic['rewards'][0]['data']['styles_list']).replace('_', ' ')}, {intcomma(dic['rewards'][2]['value'])} bonds{', tank' if dic['rewards'][1]['value'] else ''}
                    ''')
                ))

            # Paginating player leaderboard
            pages = ViewMenuPages(
                source=ClanWarsPaginator(
                    data_formatted,
                    ctx,
                    f'{event.name.capitalize()} started {format_dt(event.start, "R")}, and ends {format_dt(event.end, "R")}',
                    title='Player Leaderboard',
                    url=f'https://worldoftanks.eu/en/clanwars/rating/alley/#wot&aof_front={front_id}&aof_rating=accounts&aof_filter=all&aof_page={page}&aof_size=50'
                ), clear_reactions_after=True
            )
            await pages.start(ctx)


def setup(bot):
    bot.add_cog(WoT(bot))
