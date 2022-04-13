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

    Example
    -------
    >>> await RegionConverter().convert(ctx, "eu")
    <Region.eu: 'eu'>

    >>> await RegionConverter().convert(ctx, "RuSsIA")
    <Region.ru: 'ru'>

    Parameters
    ----------
    argument : str
        The argument as passed to the converter

    Returns
    -------
    Region
        The region converted from string

    Raises
    ------
    NotARegion
        The region argument wasn't found
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
        region_map.update(dict.fromkeys(
            ['sg', 'asia', 'eastern_hemisphere', 'orient'],
            Region.asia
        ))

        region = region_map.get(argument, None)
        if not region:
            raise NotARegion(argument)

        return region


class CommandNameCheck(commands.Converter):
    '''Checks if the command name is of a valid format

    This potentially saves having to look through database
    if the format is wrong

    Example
    -------
    >>> await CommandNameCheck().convert(ctx, "#!$!$")
    Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
    InvalidCommandName: you can't name your command ...

    >>> await CommandNameCheck().convert(ctx, "bubby")
    bubby

    Parameters
    ----------
    argument : str
        The argument as passed to the converter

    Returns
    -------
    str
        The input argument if valid

    Raises
    ------
    InvalidCommandName
        The argument didn't consist of juist spaces and latin
        characters, and/or wasn't at most 50 chars long
    '''
    async def convert(self, _, argument: str) -> str:
        if not re.match(r'^[\w ]{1,50}$', argument):
            raise InvalidCommandName()

        return argument


class ReminderConverter(commands.Converter):
    '''Extracts a time from argument and converts it
    into a datetime

    Example
    -------
    >>> datetime.now()
    datetime.datetime(2021, 11, 7, 14, 13, 38, 699029)
    >>> await ReminderConverter().convert(ctx, 'in 3 hours do the dishes')
    ('do the dishes', datetime.datetime(2021, 11, 7, 17, 13, 43, 61210))

    Parameters
    ----------
    argument : str
        The argument as passed to the converter

    Returns
    -------
    Tuple[str, datetime]
        The part of the argument that wasn't part of the extracted time

    Raises
    ------
    NoTimeFound
        Couldn't find a time in the argument
    TimeTravelNotPossible
        The time argument wasn't prefixed with 'in' so the parser
        interprets it as a time in the past
    '''
    @staticmethod
    def _clean_argument(argument: str, detected: str) -> str:
        return argument.replace(detected, '').strip().lstrip(', ')

    async def convert(self, _, argument: str) -> Tuple[str, datetime]:
        dates = search_dates(argument, languages=['en'])
        now = datetime.now()
        if not dates:
            raise NoTimeFound('Couldn\'t find a time in your argument')

        detected, date = dates[0]
        if now > date:
            raise TimeTravelNotPossible(detected, date)

        return self._clean_argument(argument, detected), date
