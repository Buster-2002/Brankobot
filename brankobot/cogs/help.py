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

from contextlib import suppress
from textwrap import dedent

from discord.ext import commands
from discord.utils import escape_markdown

from .utils.enums import BigRLDChannelType, SmallRLDChannelType


class NewHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Shows help for the bot, commands and categories',
            'hidden': True,
            'checks': [lambda ctx: ctx.channel.id in {
                BigRLDChannelType.bot.value,
                SmallRLDChannelType.bot.value,
                764801756680290335,
                859739694635679794,
                869681728170639391
            }]
        })


    @property
    def _prefix(self) -> str:
        '''Returns the already mention transformed prefix with escaped markdown'''
        return escape_markdown(self.context.clean_prefix)


    async def send_bot_help(self, mapping):
        '''Invokes with <prefix>help'''
        ctx = self.context
        title = 'Brankobot | Help'
        formatted = '\n'.join(sorted([(
            f'**{cog.qualified_name}** \u279F {len(cog_commands)} commands and {sum([(len(group.commands)) for group in cog_commands if isinstance(group, commands.Group)])} subcommands')
            for cog, cog_commands in filter(lambda i: i[0], mapping.items()) if cog.qualified_name not in {'Help', 'Events'}
        ]))
        msg = dedent(f'''
            *Use {self._prefix}help [category] to see its available commands*

            {formatted}
        ''').strip()

        await ctx.send_response(
            msg,
            title=title,
            show_invoke_speed=False
        )


    async def send_cog_help(self, cog):
        '''Invokes with <prefix>help <category>'''
        ctx = self.context
        title = f'Brankobot | Help > {cog.qualified_name}'
        formatted = '\n'.join(sorted([
            f"**{self._prefix}{c.qualified_name}** \u279F {c.help}"
            for c in cog.get_commands() if not c.hidden
        ]))
        msg = dedent(f'''
            *Use {self._prefix}help [command] for more info on a command or commandgroup*

            {formatted}
        ''').strip()
        
        await ctx.send_response(
            msg,
            title=title,
            show_invoke_speed=False
        )


    async def send_group_help(self, group):
        '''Invokes with <prefix>help <group>'''
        ctx = self.context
        title = f'Brankobot | Help > {group.cog_name} > {group.qualified_name}'
        aliases = ', '.join(group.aliases) or 'This group doesn\'t have any aliases.'
        usage = group.usage or group.signature.replace('_', '') or 'This group doesn\'t take any arguments.'
        formatted = '\n'.join(sorted([(
            f"**{self._prefix}{c.qualified_name}** \u279F {c.help}")
            for c in group.commands
        ]))
        msg = dedent(f'''
            *Use {self._prefix}help [command] [subcommand] for more info on a subcommand*

            **{self._prefix}{group.qualified_name}** \u279F {group.help}

            **Usage:** {usage}
            **Aliases:** {aliases}

            {formatted}
        ''').strip()

        await ctx.send_response(
            msg,
            title=title,
            show_invoke_speed=False
        )


    async def send_command_help(self, command):
        '''Invokes with <prefix>help <command>'''
        ctx = self.context

        # Ensures variables added with for instance checks, are actually added to the bot instance
        with suppress(Exception):
            await command.can_run(ctx)

        get_limitations = lambda attr: ', '.join(set([
            str(r) for r in getattr(command, attr, [])
            if getattr(command, attr, [])] or ['No limitations']
        ))

        roles = get_limitations('allowed_role_types')
        channels = get_limitations('allowed_channel_types')

        title = f'Brankobot | Help > {command.cog_name} > {f"{command.parent} > " if command.parent else ""}{command.name}'
        aliases = ', '.join(command.aliases) or 'This command doesn\'t have any aliases.'
        usage = command.signature or 'This command doesn\'t take any arguments.'
        msg = dedent(f'''
            *Arguments in between <> are required, arguments in between [] have a default value*

            **{self._prefix}{command.qualified_name}** \u279F {command.help}

            **Usage:** {usage}
            **Aliases:** {aliases}
            **Limited to roles:** {roles}
            **Limited to channels:** {channels}
        ''').strip()

        await ctx.send_response(
            msg,
            title=title,
            show_invoke_speed=False
        )


class Help(commands.Cog):
    def __init__(self, bot):
        bot.help_command = NewHelpCommand()

def setup(bot):
    bot.add_cog(Help(bot))
