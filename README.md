# Brankobot
Made by Buster#5741

### Summary
A private bot for the [-RLD-](https://eu.wargaming.net/clans/wot/500075680/) and [\_RLD\_](https://eu.wargaming.net/clans/wot/500018519/) WoT clan Discord servers.  
You are allowed to use this code, however it is purely designed for the two aforementioned servers, so you would need to edit some code.

### Requirements
* A .env file with two values: `DISCORD_TOKEN` and `WOT_API_TOKEN`
* Python 3.9
* Python sqlite3 version 3.35.5 +
* `requirements.txt` installed

### Features
* Decent error handling
* Response on mention
* Response on server join
* fully fledged birthdays, music, reminders and custom commands

### Commands

#### World of Tanks
* `replayinfo`
* `showmarks`
* `showstats`
* `requirements`
* `clan`
* `player`
* `clanwars`
  - `clanlog`
  - `battles`
  - `rewards`
  - `provinces`
  - `leaderboard`
    - `clans`
    - `players`

#### Music
* `connect`
* `current`
* `pause`
* `play`
* `queue`
* `resume`
* `skip`
* `stop`
* `volume`

#### Fun
* `caption`
* `birthday`
* `offline` (inside joke)
* `rand`
* `love`
* `8ball`
* `urban`
* `reddit`
* `say`
* `outside`
* `fact`
* `poll`
* `birthday`
  - `average`
  - `info`
  - `remove`
* `joke`
  - `dad`
  - `dark`
  - `pun`
  - `misc`

#### Misc
* `ping`
* `cleanup`
* `restart`
* `botlog`
* `reload`
* `processinfo`

#### Utilities
* `userinfo`
* `download`
* `reminder`
  - `list`
  - `remove`
  - `clear`
* `customcommand`
  - `add`
  - `remove`
  - `rename`
  - `info`
  - `search`
  - `list`


### Mentions
* [WotReplay](https://pypi.org/project/wotreplay/) - Used their way of getting json data from replay files.
* [herhor.net](https://herhor.net/wot/) - Use of their tank and mark images which imitate in game look.
* [EvieePy](https://github.com/EvieePy) - Use of their basic music bot gist [code](https://gist.github.com/EvieePy/ab667b74e9758433b3eb806c53a19f34)
