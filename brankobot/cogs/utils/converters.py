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

import re
from datetime import datetime
from typing import Tuple

from dateparser.search import search_dates
from discord.ext import commands

from .enums import Region
from .errors import (InvalidCommandName, NotARegion, NoTimeFound,
                     TimeTravelNotPossible)


class RegionConverter(commands.Converter):
    '''Converts a region argument into Region

    >>> await RegionConverter().convert(ctx, "eu")
    <Region.eu: 'eu'>

    >>> await RegionConverter().convert(ctx, "RuSsIA")
    <Region.ru: 'ru'>
    '''
    async def convert(self, _, argument: str) -> Region:
        argument = argument.lower()

        region_map = dict.fromkeys(
            ['eu', 'europe', 'european_union'],
            Region.eu
        )
        region_map.update(dict.fromkeys(
            ['na', 'america', 'western_hemisphere'],
            Region.na
        ))
        region_map.update(dict.fromkeys(
            ['ru', 'russia', 'rf', 'russian_federation'],
            Region.ru
        ))

        region = region_map.get(argument, None)
        if not region:
            raise NotARegion(argument)

        return region


class CommandNameCheck(commands.Converter):
    '''Checks if the command name is valid

    This potentially saves having to look through database
    if the format is wrong

    >>> await CommandNameCheck().convert(ctx, "#!$!$")
    Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
    InvalidCommandName: you can't name your command ...

    >>> await CommandNameCheck().convert(ctx, "bubby")
    bubby
    '''
    async def convert(self, _, argument: str) -> str:
        if not re.match(r'^[\w ]{1,50}$', argument):
            raise InvalidCommandName()
        return argument


class ReminderConverter(commands.Converter):
    '''Extracts a time from argument

    >>> await ReminderConverter().convert(ctx, "In 3 hours, do the dishes")
    ('do the dishes', datetime.datetime(2021, 10, 3, 15, 22, 19, 139779))
    '''
    async def convert(self, _, argument: str) -> Tuple[str, datetime]:
        dates = search_dates(argument, ['en'])
        now = datetime.now()
        if not dates:
            raise NoTimeFound('Couldn\'t find a time in your argument')

        detected, date = dates[0]
        if now > date:
            raise TimeTravelNotPossible(date)

        return argument.replace(detected, '').strip(), date
