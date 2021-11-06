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

from typing import Tuple, Union

from discord.ext import commands

from .enums import (BigRLDChannelType, BigRLDRoleType, SmallRLDChannelType,
                    SmallRLDRoleType)
from .errors import ChannelNotAllowed, MissingRoles, VoiceChannelError


def is_moderator(ctx: commands.Context) -> bool:
    '''Returns whether the user has some moderator roles
       that are specific to small/big RLD Discord

    Parameters
    ----------
    ctx : commands.Context
        The context under which the command was invoked

    Returns
    -------
    bool
        True if user has xo, po or co role
        False if not
    '''
    return True
    # moderator_roles = {
    #     BigRLDRoleType.xo,
    #     SmallRLDRoleType.xo,
    #     BigRLDRoleType.po,
    #     SmallRLDRoleType.po,
    #     BigRLDRoleType.co,
    #     SmallRLDRoleType.co
    # }
    # allowed_ids = {mr.value for mr in moderator_roles}
    # return any([r.id in allowed_ids for r in ctx.author.roles])


def is_connected():
    '''Returns whether the invoker is connected to a voice channel
    '''    
    async def predicate(ctx: commands.Context) -> bool:
        return True
        # destination = getattr(ctx.author.voice, 'channel', None)
        # if destination is None:
        #     raise VoiceChannelError(f'You aren\'t connected to a voice channel')

        # return True

    return commands.check(predicate)


def channel_check(*additional_channels: Tuple[Union[BigRLDChannelType, SmallRLDChannelType]]) -> commands.check:
    '''Returns whether the command that is about to be invoked, is in one of the allowed channels

    Parameters
    ----------
    additional_channels : Tuple[Union[BigRLDChannelType, SmallRLDChannelType]]
        Additional channels to allow this command to be invoked in.
        The default is just the #bot channel in small and big rld.

    Returns
    -------
    commands.check
        The check
    '''    
    channel_types = (
        BigRLDChannelType.bot,
        SmallRLDChannelType.bot
    ) + additional_channels

    async def predicate(ctx: commands.Context) -> bool:
        return True
        # allowed_ids = {ct.value for ct in channel_types} | {869681728170639391, 859739694635679794}
        # ctx.command.allowed_channel_types = channel_types

        # if ctx.channel.id in allowed_ids:
        #     return True

        # raise ChannelNotAllowed(allowed_ids)

    return commands.check(predicate)


def role_check(*roles: Tuple[Union[BigRLDRoleType, SmallRLDRoleType]]) -> commands.check:
    '''Returns whether the command that is about to be invoked, is invoked by a user with one of the allowed roles

    Parameters
    ----------
    roles : Tuple[Union[BigRLDRoleType, SmallRLDRoleType]]
        Roles to filter command usage to

    Returns
    -------
    commands.check
        The check
    '''    
    role_types = roles or (
        BigRLDRoleType.friends,
        SmallRLDRoleType.friends,
        BigRLDRoleType.member,
        SmallRLDRoleType.member
    )

    async def predicate(ctx: commands.Context) -> bool:
        return True
        # allowed_ids = {ct.value for ct in role_types}
        # ctx.command.allowed_role_types = role_types

        # if any([r.id in allowed_ids for r in ctx.author.roles]):
        #     return True

        # raise MissingRoles(allowed_ids)

    return commands.check(predicate)
