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

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union

from discord import Object
from discord.utils import escape_markdown

from .enums import (Emote, EventStatusType, FormattedNationType,
                    FormattedTankType, MarkType, MasteryType, Region, try_enum)


@dataclass
class Birthday:
    id: int
    user_id: int
    server_id: int
    date_string: str

    @property
    def date(self) -> datetime:
        year, month, day = map(int, self.date_string.split('-'))
        return datetime(year=year, month=month, day=day)


@dataclass
class Achievement:
    id: int
    name: str
    internal_name: str
    emote: Emote
    description: str


@dataclass
class Reminder:
    id: int
    creator_id: int
    channel_id: int
    context_message_link: str
    creation_timestamp: float
    end_timestamp: float
    message: str

    @property
    def creator(self) -> Object:
        return Object(self.creator_id)

    @property
    def channel(self) -> Object:
        return Object(self.channel_id)

    @property
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self.creation_timestamp)
    
    @property
    def ends_at(self) -> datetime:
        return datetime.fromtimestamp(self.end_timestamp)


@dataclass
class CustomCommand:
    id: int
    creator_id: int
    times_used: Optional[int]
    creation_timestamp: float
    name: str
    content: str

    @property
    def creator(self) -> Object:
        return Object(self.creator_id)

    @property
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self.creation_timestamp)


@dataclass
class GlobalMapFront:
    name: str
    id: str
    url: Optional[str]


@dataclass
class GlobalmapEvent:
    name: str
    id: str
    status: Union[EventStatusType, str]
    start: datetime
    end: datetime
    id: str
    fronts: List[GlobalMapFront]


@dataclass
class Clan:
    tag: str
    id: int
    region: Region

    @property
    def official_url(self) -> str:
        return f'https://{self.region}.wargaming.net/clans/wot/{self.id}/'

    @property
    def official_md_url(self) -> str:
        return f'[{escape_markdown(self.tag)} wot]({self.official_url})'

    @property
    def wotlife_url(self) -> str:
        return f'https://wot-life.com/{self.region}/clan/{self.tag}-{self.id}/'

    @property
    def wotlife_md_url(self) -> str:
        tag = escape_markdown(self.tag)
        return f'[{tag} wot-life](https://wot-life.com/{self.region}/clan/{tag}-{self.id}/)'


@dataclass
class Player:
    nickname: str
    id: int
    region: Region

    @property
    def _link_region(self) -> str:
        return str(self.region) if not self.region is Region.na else 'com'

    @property
    def official_url(self) -> str:
        return f'https://worldoftanks.{self._link_region}/en/community/accounts/{self.id}-{self.nickname}/'

    @property
    def official_md_url(self) -> str:
        nick = escape_markdown(self.nickname)
        return f'[{nick} wot](https://worldoftanks.{self._link_region}/en/community/accounts/{self.id}-{nick}/)'

    @property
    def wotlife_url(self) -> str:
        return f'https://wot-life.com/{self.region}/player/{self.nickname}-{self.id}/'

    @property
    def wotlife_md_url(self) -> str:
        nick = escape_markdown(self.nickname)
        return f'[{nick} wot-life](https://wot-life.com/{self.region}/player/{nick}-{self.id})'


# TODO: add max alpha so I can calculate
# amount of shots it takes to reach certain
# wn8 level instead of scraping it
@dataclass
class Tank:
    id: int
    type: str
    name: str
    short_name: str
    internal_name: str
    nation: str
    tier: int
    big_icon: str
    small_icon: str
    contour_icon: str
    is_premium: bool
    is_reward: bool
    is_collector: bool

    @property
    def formatted_type(self):
        return try_enum(FormattedTankType, self.type.replace('-', '_'))

    @property
    def formatted_nation(self):
        return try_enum(FormattedNationType, self.nation)

    @property
    def tank_summary(self):
        return f'*The {self.short_name} is a tier {self.tier}{" reward " if self.is_reward else " premium " if self.is_premium else " collectors " if self.is_collector else " "}{self.formatted_type} from {self.formatted_nation}.*'


@dataclass
class TankStats(Tank):   
    total_kills: int
    average_kills: float
    _mark: int
    damage_dealt_received_ratio: float
    wins_ratio: float
    total_wins: int
    total_hits: int
    total_damage_received: int
    _mastery: int
    kills_deaths_ratio: float
    total_damage: int
    average_xp: int
    total_xp: int
    total_survived_battles: int
    total_battles: int
    average_damage: int

    @property
    def mastery(self) -> Optional[MasteryType]:
        return try_enum(MasteryType, self._mastery, reverse_lookup=True)

    @property
    def mark(self) -> Optional[MarkType]:
        return try_enum(MarkType, self._mark, reverse_lookup=True)

    def full_tank_image(self, size: str = 'Medium') -> Optional[str]:
        if self.tier > 4:
            return f'https://herhor.net/wot/moe/prepared/{size}/tanks/{self.id}.png'
        return None

    @property
    def mark_image_url(self) -> Optional[str]:
        if self.tier > 4:
            return f'https://herhor.net/wot/moe/original/marks/{self.nation}_{self._mark}.png'
        return None

