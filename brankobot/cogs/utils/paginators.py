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

from collections.abc import Iterable
from textwrap import dedent
from typing import List, Tuple, Union

import discord
from discord.ext import commands, menus
from discord.utils import escape_markdown, format_dt
from humanize import intcomma, precisedelta

from .helpers import separate_capitals
from .models import Achievement, CustomCommand, Reminder
from .wotreplay_folder import (BattleEconomy, BattlePerformance, BattlePlayer,
                               BattleXP, MetaData)


class MusicQueuePaginator(menus.ListPageSource):
    def __init__(self, data, ctx: commands.Context):
        super().__init__(
            data,
            per_page=1
        )
        self.ctx = ctx

    async def format_page(self, menu, entry: dict) -> discord.Embed:
        fields = [
            ('Song', f"[{entry['title']}]({entry['webpage_url']})"),
            ('Channel', f"[{entry['uploader']}]({entry['uploader_url']})"),
            ('Requested by', entry['requester'].mention),
            ('Views', intcomma(entry['view_count'])),
            ('Likes/Dislikes', f"{intcomma(entry['likes'])}/{intcomma(entry['dislikes'])}"),
            ('Uploaded', discord.utils.format_dt(entry['upload_date'], 'R'))
        ]
        embed = (await self.ctx.send_response(
            f"**Duration:** {precisedelta(entry['duration'])}",
            title=f'Queue position {menu.current_page + 1}',
            thumbnail=entry['thumbnail'],
            fields=fields,
            send=False,
            show_invoke_speed=False
        )).set_footer(
            text=f'page {menu.current_page + 1}/{self.get_max_pages()}',
            icon_url=self.ctx.bot.user.display_avatar
        )
        return embed


class CustomCommandsPaginator(menus.ListPageSource):
    def __init__(self, data, ctx: commands.Context, user: discord.User = None):
        super().__init__(
            data,
            per_page=10
        )
        self.ctx = ctx
        self.user = user

    async def format_page(self, menu, entries: List[CustomCommand]) -> discord.Embed:
        embed = (await self.ctx.send_response(
            '\n'.join(f'**{cc.id}.** {cc.name}' for cc in entries),
            title=(f'{self.user.display_name}\'s ' if self.user else '') + f"Custom Commands ({menu.current_page + 1}/{self.get_max_pages()})",
            send=False,
            show_invoke_speed=False
        )).set_footer(
            text=f'page {menu.current_page + 1}/{self.get_max_pages()}',
            icon_url=self.ctx.bot.user.display_avatar
        )
        return embed


class ReminderPaginator(menus.ListPageSource):
    def __init__(self, data, ctx: commands.Context):
        super().__init__(data, per_page=3)
        self.ctx = ctx

    async def format_page(self, menu, entries: List[Reminder]) -> discord.Embed:
        msg = '\n\n'.join([
            f"**Reminder {reminder.id}**\nends {format_dt(reminder.ends_at, 'R')}\n[jump to message]({reminder.context_message_link})\n\n*{escape_markdown(reminder.message)}*"
            for reminder in sorted(
                entries,
                key=lambda item: item.ends_at
            )
        ])
        embed = (await self.ctx.send_response(
            msg,
            title='Reminders',
            send=False,
            show_invoke_speed=False
        )).set_footer(
            text=f'page {menu.current_page + 1}/{self.get_max_pages()}',
            icon_url=self.ctx.bot.user.display_avatar
        )
        return embed


class ReplayPaginator(menus.ListPageSource):
    def __init__(self, data, ctx: commands.Context, meta_data: dict):
        super().__init__(data, per_page=1)
        self.ctx = ctx
        self.meta_data = meta_data

    async def format_page(self, menu, entry: Union[BattleEconomy, BattlePerformance, BattlePlayer, BattleXP, MetaData]) -> discord.Embed:
        fields, description = [], ''
        thumbnail_url, image_url = discord.Embed.Empty, discord.Embed.Empty

        if isinstance(entry, MetaData):
            tank = self.ctx.bot.search_tank(entry.internal_tank_name)
            thumbnail_url = tank.big_icon
            image_url = f'http://static.wotbase.net/img/maps/300/{entry.map_name}.jpg'
            player_name = escape_markdown(entry.player_name)
            title = 'Meta'
            description = dedent(f'''
                {tank.tank_summary}

                **Player:** [{player_name}](https://wot-life.com/{entry.region_code.lower()}/player/{player_name}-{entry.account_id}/)
                **Map:** {separate_capitals(entry.map_display_name)}
                **Game mode:** {entry.gameplay_mode}
                **Battle type:** {str(entry.battle_type).replace('_', ' ')}
                **Played:** {format_dt(entry.replay_date, ('R' if entry.region_code == 'EU' else 'D'))}
                **Game duration:** {precisedelta(entry.duration)}
                **Game version:** {entry.client_version_executable} ({entry.region_code})
                **Has mods:** {'yes' if entry.has_mods is True else 'no'}
            ''')

        elif isinstance(entry, BattlePerformance):
            title = 'Performance'
            description = dedent(f'''
                **Kills:** {entry.kills} ({entry.team_kills} team kills)
                **Spotted:** {entry.spotted}
                **Capped:** {entry.solo_flag_capture}/{entry.flag_capture}
                **Driven:** {entry.meters_driven / 1000:.2f} km
                **Modules destroyed:** {entry.total_destroyed_modules}
                **Life time:** {precisedelta(entry.life_time)}
                **Fairplay factor:** {entry.fairplay_factor}
                **Committed suicide:** {'yes' if entry.committed_suicide is True else 'no'}
            ''')
            fields = [
                ('Damage', f"Dealt: {intcomma(entry.damage_dealt)}\nReceived: {intcomma(entry.damage_received)}\nTeam percent {entry.percent_of_total_team_damage:.2f}%"),
                ('Assist', f"Spot: {intcomma(entry.damage_assisted_radio)}\nTrack: {intcomma(entry.damage_assisted_track)}\nStun: {intcomma(entry.damage_assisted_stun)}"),
                ('Shots', f"Fired: {intcomma(entry.shots)}\nHit: {intcomma(entry.direct_hits)}\nPenned: {entry.piercings}"),
                ('Stun', f"Tanks: {entry.stunned}\nDuration: {entry.stun_duration}\nNumber: {entry.stun_number}"),
                ('Blocked', f"Damage: {intcomma(entry.damage_blocked_by_armour)}\nShots: {intcomma(entry.direct_hits_received - entry.piercings_received)}"),
                ('\u200b', '\u200b')
            ]

        elif isinstance(entry, Iterable) and all([isinstance(i, BattlePlayer) for i in entry]):
            title = 'Teams'
            replay_owner = escape_markdown(self.meta_data.player_name)
            region = self.meta_data.region_code.lower()
            team1, team2 = [], []

            for player in entry:
                tank = self.ctx.bot.search_tank(player.vehicle_tag)
                alive = player.is_alive
                player_name = escape_markdown(player.name)
                (team1 if player.team == 1 else team2).append((
                    ('~~' if not alive else '') +
                    f'[{player_name}](https://wot-life.com/{region}/player/{player_name}-{player.id}/ "{player.fake_name}") | {tank.short_name} | {player.kills}'
                    + ('~~' if not alive else ''),
                    tank,
                    alive
                ))

            format_teams_list = lambda team: '\n'.join([
                t[0] for t in list(sorted(
                    team,
                    key=lambda item: (item[2], item[1].tier),
                    reverse=True
                ))
            ])

            team1 = format_teams_list(team1)
            team2 = format_teams_list(team2)
            description = f"Name (hover for fake name) | Tank | Kills\n\n**Team 1**\n{team1}\n\n**Team 2**\n{team2}".replace(replay_owner, f'__**{replay_owner}**__')

        elif isinstance(entry, Iterable) and all([isinstance(i, Achievement) for i in entry]):
            title = 'Achievements'
            fields = [
                (f"{achievement.emote} {achievement.name}", achievement.description)
                for achievement in entry
            ] or 'No achievements'

        elif isinstance(entry, BattleEconomy):
            title = 'Economy'
            has_premium = True if entry.applied_premium_credits_factor_100 == 150 else False
            sub_total = entry.subtotal_credits + entry.prem_squad_credits + entry.referral_20_credits + entry.achievement_credits + entry.booster_credits + entry.event_credits + entry.piggy_bank
            description = dedent(f'''
                **Premium:** {'yes' if has_premium else 'no'}
                ```diff
                Received: {intcomma(entry.original_credits)}
                -----------------------------
                + {intcomma(entry.subtotal_credits - entry.original_credits)} (premium bonus x1.5)
                + {intcomma(entry.prem_squad_credits)} (platoon bonus)
                + {intcomma(entry.referral_20_credits)} (referral bonus)
                + {intcomma(entry.achievement_credits)} (achievement bonus)
                + {intcomma(entry.booster_credits)} (boosters/reserves bonus)
                + {intcomma(entry.event_credits)} (mission reward)
                + {intcomma(entry.piggy_bank)} (piggy bank bonus)

                Subtotal: {intcomma(sub_total)}
                -----------------------------
                - {intcomma(entry.repair)} (repair)
                - {intcomma(entry.resupply_ammunition)} (resupply ammunition)
                - {intcomma(entry.resupply_consumables)} (resupply consumables)
                - {intcomma(entry.credits_penalty)} (penalty)

                -----------------------------
                Total: {intcomma(sub_total - entry.repair - entry.credits_penalty - entry.resupply_ammunition - entry.resupply_consumables)}
                -----------------------------
                ```
            ''')

        elif isinstance(entry, BattleXP):
            title = 'XP'
            has_premium = True if entry.applied_premium_xp_factor_100 == 150 else False
            sub_total = entry.subtotal_xp + entry.squad_xp + entry.referral_20_xp + entry.achievement_xp + entry.booster_xp + entry.premium_vehicle_xp
            description = dedent(f'''
                **Premium:** {'yes' if has_premium else 'no'}
                ```diff
                Received: {intcomma(entry.original_xp)}
                -----------------------------
                + {intcomma(entry.subtotal_xp - entry.original_xp)} (premium bonus x1.5)
                + {intcomma(entry.squad_xp)} (platoon bonus)
                + {intcomma(entry.premium_vehicle_xp)} (premium vehicle bonus)
                + {intcomma(entry.referral_20_xp)} (referral bonus)
                + {intcomma(entry.achievement_xp + entry.achievement_free_xp)} (achievement bonus)
                + {intcomma(entry.booster_xp + entry.booster_t_men_xp)} (boosters/reserves bonus)

                Subtotal: {intcomma(sub_total)}
                -----------------------------
                - {intcomma(entry.xp_penalty)} (penalty)

                -----------------------------
                Total XP: {intcomma(sub_total - entry.xp_penalty)}
                Total free XP: {intcomma(entry.free_xp)}
                -----------------------------
                ```
            ''')

        return (await self.ctx.send_response(
            description,
            thumbnail=thumbnail_url,
            image=image_url,
            fields=fields,
            title=title,
            send=False,
            show_invoke_speed=False
        )).set_footer(
            text=f'page {menu.current_page + 1}/{self.get_max_pages()}',
            icon_url=self.ctx.bot.user.display_avatar
        )


class TankStatsPaginator(menus.ListPageSource):
    def __init__(self, data, ctx: commands.Context, player: str, url: str):
        super().__init__(data, per_page=1)
        self.ctx = ctx
        self.player = player
        self.url = url

    async def format_page(self, menu, entry: Tuple[str, str]) -> discord.Embed:
        embed = (await self.ctx.send_response(
            entry[1],
            url=self.url,
            title=f'{self.player}\'s stats for {entry[0]}',
            thumbnail=entry[2],
            send=False,
            show_invoke_speed=False
        )).set_footer(
            text=f'page {menu.current_page + 1}/{self.get_max_pages()}',
            icon_url=self.ctx.bot.user.display_avatar
        )
        return embed


class ClanWarsPaginator(menus.ListPageSource):
    def __init__(self, data, ctx: commands.Context, *args, **kwargs):
        super().__init__(data, per_page=6)
        self.ctx = ctx
        self.args = args
        self.kwargs = kwargs

    async def format_page(self, menu, entries: List[Tuple[str, str]]) -> discord.Embed:
        offset = menu.current_page * self.per_page + 1
        fields = []
        for i, items in enumerate(entries, offset):
            fields.append((f'{i}. {items[0]}', items[1]))

        embed = (await self.ctx.send_response(
            *self.args,
            **self.kwargs,
            fields=fields,
            send=False,
            show_invoke_speed=False
        )).set_footer(
            text=f'page {menu.current_page + 1}/{self.get_max_pages()}',
            icon_url=self.ctx.bot.user.display_avatar
        )

        return embed
