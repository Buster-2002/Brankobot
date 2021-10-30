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

from typing import Tuple

from discord.ext import commands
from discord.ext.commands import FlagConverter

from .converters import RegionConverter
from .enums import Region


class MarkCollageFlags(FlagConverter, case_insensitive=True):
    region: RegionConverter = Region.eu
    separate_nations: bool = commands.flag(aliases=['separatenations'], default=False)
    nations: Tuple[str, ...] = commands.flag(aliases=['nation'], default=[])
    types: Tuple[str, ...] = commands.flag(aliases=['type'], default=[])
    tiers: Tuple[int, ...] = commands.flag(aliases=['tier'], default=[])


class TankStatFlags(FlagConverter, case_insensitive=True):
    region: RegionConverter = Region.eu
    sort_by: Tuple[str, ...] = commands.flag(aliases=['sortby'], default=['total_battles'])
    nations: Tuple[str, ...] = commands.flag(aliases=['nation'], default=[])
    types: Tuple[str, ...] = commands.flag(aliases=['type'], default=[])
    tiers: Tuple[int, ...] = commands.flag(aliases=['tier'], default=[])
    roles: Tuple[str, ...] = commands.flag(aliases=['role'], default=[])
    include_premiums: bool = commands.flag(aliases=['includepremiums'], default=True)
    include_normal: bool = commands.flag(aliases=['includenormal', 'includedefault'], default=True)
    include_collectors: bool = commands.flag(aliases=['includecollectors'], default=True)


class RequirementsFlags(FlagConverter, case_insensitive=True):
    region: RegionConverter = Region.eu
    moe_days: int = commands.flag(aliases=['moedays'], default=15)
