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
from contextlib import suppress
from types import TracebackType
from typing import Iterable, Optional

import discord
from discord.ext import commands

from .enums import Emote


def separate_capitals(word: str) -> str:
    '''Creates a proper title from camelCase words

    Example
    -------

    >>> separate_capitals("camelCaseWord")
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
    return sum(iterable) / len(iterable)


class Loading:
    def __init__(self, ctx: commands.Context, /, initial_message: str = None):
        self.ctx = ctx
        self.initial_message: Optional[str] = initial_message
        self._message: discord.Message = None


    @staticmethod
    def _format_message(message: Optional[str]) -> str:
        if message:
            return f"{Emote.loading} {message}..."
        return str(Emote.loading)


    async def update(self, message: str = None) -> None:
        with suppress(discord.HTTPException):
            if self._message.content != message:
                self._message = await self._message.edit(content=self._format_message(message))


    async def __aenter__(self) -> "Loading":
        self._message = await self.ctx.send(self._format_message(self.initial_message))
        return self # Necessary to return instance for "as" statement


    async def __aexit__(self, exc_type: type, exc: Exception, tb: TracebackType) -> None:
        with suppress(discord.HTTPException, AttributeError):
            await self._message.delete()


class ConfirmUI(discord.ui.View):
    def __init__(self, timeout: int):
        super().__init__(timeout=timeout)
        self.value: bool = None


    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.stop()


    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message('no? alright, cancelled operation', ephemeral=True)
        self.value = False
        self.stop()


async def confirm(ctx: commands.Context, prompt: str, timeout: int = 30) -> bool:
    '''Uses a confirmation UI with Confirm and Cancel button

    Parameters
    ----------
    ctx : commands.Context
        The context under which to use this UI
    prompt : str
        The message to prompt the UI with

    Returns
    -------
    bool
        True if confirmed, False if cancelled or timed out
    '''
    view = ConfirmUI(timeout)
    msg = await ctx.send(prompt, view=view)
    await view.wait()
    await msg.delete()
    return bool(view.value)
