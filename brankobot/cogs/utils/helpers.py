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

import datetime
import re
from contextlib import suppress
from types import TracebackType
from typing import Iterable, Optional, Any

import discord
from discord.ext import commands

from .enums import Emote


def separate_capitals(word: str) -> str:
    '''Creates a proper title from camelCase words

    Example
    -------
    >>> separate_capitals('camelCaseWord')
    'Camel Case Word'

    Parameters
    ----------
    word : str
        The word to split up into a proper title

    Returns
    -------
    str
        A string separated on capitals
    '''
    return (' '.join(re.split(r'(?=[A-Z])', word))).strip().title()


def average(iterable: Iterable[int]) -> float:
    '''Returns the average number of a list/tuple/etc

    Parameters
    ----------
    iterable : Iterable[int]
        The iterable to return the average of

    Returns
    -------
    float
        The average of the iterable of numbers
    '''
    return sum(iterable) / len(iterable)


def get_next_birthday(birth_date: datetime.datetime) -> datetime.datetime:
    '''Returns next birthday date for a given birth date

    Parameters
    ----------
    birth_date : datetime.datetime
        The birth date

    Returns
    -------
    datetime.datetime
        The next birthday date, taking into account whether
        it has already been this year.
    '''
    today = datetime.date.today()
    year = today.year

    # If birthday has already been this year, we take the next year
    if (today.month > birth_date.month) or (today.month == birth_date.month and today.day > birth_date.day):
        year += 1

    return datetime.datetime(year, birth_date.month, birth_date.day)


class Loading:
    def __init__(self, ctx: commands.Context, initial_message: str):
        self.ctx = ctx
        self.initial_message: Optional[str] = initial_message
        self._message: discord.Message = None

    @staticmethod
    def _format_content(content: Optional[str]) -> str:
        '''Formats a message for the loader

        Parameters
        ----------
        content : Optional[str]
            The message content to format

        Returns
        -------
        str
            The message content + loading emote or just the loading emote
        '''
        if content:
            return f'{Emote.loading} {content}...'
        return Emote.loading.value

    async def update(self, content: Optional[str]) -> None:
        '''Updates the loading message content

        Parameters
        ----------
        content : Optional[str]
            The new content of the loading message
        '''
        with suppress(discord.HTTPException):
            if self._message.content != content:
                self._message = await self._message.edit(
                    content=self._format_content(content),
                    allowed_mentions=discord.AllowedMentions(replied_user=False)
                )

    async def __aenter__(self) -> 'Loading':
        self._message = await self.ctx.reply(self._format_content(self.initial_message), mention_author=False)
        return self # Necessary to return instance for "as" statement

    async def __aexit__(self, exc_type: Any, exc: Exception, tb: TracebackType) -> None:
        with suppress(discord.HTTPException, AttributeError):
            await self._message.delete()


class ConfirmUI(discord.ui.View):
    def __init__(self, timeout: int):
        super().__init__(timeout=timeout)
        self.value: bool = None

    @discord.ui.button(
        label='Confirm',
        style=discord.ButtonStyle.green,
        emoji='✔️'
    )
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.stop()

    @discord.ui.button(
        label='Cancel',
        style=discord.ButtonStyle.red,
        emoji='✖️'
    )
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message('no? alright, cancelled operation', ephemeral=True)
        self.value = False
        self.stop()
