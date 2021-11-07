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

from datetime import datetime
from typing import Set

import discord
from discord.ext import commands

from .enums import Region
from .models import Birthday, CustomCommand, Reminder

__all__ = (
    # Birthday errors
    'BirthdayDoesntExist',
    'NoBirthdays',
    'NotAModerator',
    'BirthdayAlreadyRegistered',

    # Music errors
    'VoiceChannelError',
    'NotPlaying',
    'EmptyQueue',
    'InvalidVolume',

    # Reminder errors
    'NoTimeFound',
    'NoReminders',
    'ReminderDoesntExist',
    'TimeTravelNotPossible',
    'NotReminderOwner',

    # Custom Command errors
    'CommandExists',
    'CommandDoesntExist',
    'NotCommandOwner',
    'NoCustomCommands',
    'InvalidCommandName',
    'InvalidCommandContent',

    # WoT errors
    'InvalidNickname',
    'InvalidClan',
    'InvalidFlags',
    'ReplayError',
    'NoMoe',
    'PlayerNotFound',
    'ClanNotFound',
    'TankNotFound',
    'NotARegion',

    # Other errors
    'ChannelNotAllowed',
    'MissingRoles',
    'ApiError'
)


# Birthday errors
class BirthdayError(commands.CommandError):
    pass

class BirthdayDoesntExist(BirthdayError):
    def __init__(self, user: discord.User):
        self.user = user

class NoBirthdays(BirthdayError):
    pass

class NotAModerator(BirthdayError):
    pass

class BirthdayAlreadyRegistered(commands.CommandError):
    def __init__(self, birthday: Birthday):
        self.birthday = birthday


# Music errors
class MusicError(commands.CommandError):
    pass

class VoiceChannelError(MusicError):
    def __init__(self, message: str, destination: discord.VoiceChannel = None):
        self.message = message
        self.destination = destination

class NotPlaying(MusicError):
    pass

class EmptyQueue(MusicError):
    pass

class InvalidVolume(MusicError):
    def __init__(self, volume: float):
        self.volume = volume


# Reminder errors
class ReminderError(commands.CommandError):
    pass

class NoTimeFound(ReminderError):
    pass

class NoReminders(ReminderError):
    pass

class ReminderDoesntExist(ReminderError):
    def __init__(self, id: int):
        self.id = id

class TimeTravelNotPossible(ReminderError):
    def __init__(self, detected: str, date: datetime):
        self.detected = detected
        self.date = date

class NotReminderOwner(ReminderError):
    def __init__(self, reminder: Reminder):
        self.reminder = reminder


# Custom command errors
class CustomCommandError(commands.CommandError):
    pass

class CommandExists(CustomCommandError):
    '''Custom exception for command already existing when trying to add it'''
    def __init__(self, command_name: str):
        self.command_name = command_name

class CommandDoesntExist(CustomCommandError):
    '''Custom exception for command not existing when trying to remove it'''
    def __init__(self, command_name: str):
        self.command_name = command_name

class NotCommandOwner(CustomCommandError):
    def __init__(self, command: CustomCommand):
        self.command = command

class NoCustomCommands(CustomCommandError):
    def __init__(self, user: discord.User = None):
        self.user = user

class InvalidCommandName(CustomCommandError):
    pass

class InvalidCommandContent(CustomCommandError):
    pass


# WoT errors
class WoTError(commands.CommandError):
    pass

class InvalidNickname(WoTError):
    pass

class InvalidClan(WoTError):
    pass

class InvalidFlags(WoTError):
    pass

class ReplayError(WoTError):
    def __init__(self, message: str):
        self.message = message

class NoMoe(WoTError):
    def __init__(self, nickname: str, region: Region):
        self.nickname = nickname
        self.region = region

class PlayerNotFound(WoTError):
    def __init__(self, nickname: str, region: Region):
        self.nickname = nickname
        self.region = region

class ClanNotFound(WoTError):
    def __init__(self, clan: str, region: Region):
        self.clan = clan
        self.region = region

class TankNotFound(WoTError):
    def __init__(self, tank: str):
        self.tank = tank

class NotARegion(WoTError):
    def __init__(self, region_argument: str):
        self.region = region_argument


# Other
class ApiError(commands.CommandError):
    def __init__(self, http_code: int, error_message: str = 'Error Ocurred'):
        self.http_code = http_code
        self.error_message = error_message

class ChannelNotAllowed(commands.CommandError):
    def __init__(self, allowed_ids: Set[int]):
        self.allowed_ids = allowed_ids

class MissingRoles(commands.CommandError):
    def __init__(self, allowed_ids: Set[int]):
        self.allowed_ids = allowed_ids
