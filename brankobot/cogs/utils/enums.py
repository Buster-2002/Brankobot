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

from enum import Enum
from typing import Any


def try_enum(cls: Any, value: Any, *, reverse_lookup: bool = False) -> Any:
    '''Tries to return cls Enum by value or key

    Parameters
    ----------
    cls : Any
        The Enum to get the value or key from
    value : Any
        The value to find in the cls Enum
    reverse_lookup : bool, optional
        True to map value to key
        False to map key to value, by default False

    Returns
    -------
    Any
        The enum value if reveerse_lookup is False
        else the enum key as string
    '''
    try:
        if reverse_lookup:
            return cls._value2member_map_[value]

        return cls._member_map_[value].value

    except (KeyError, TypeError, AttributeError):
        return value


class _StrIsValue:
    def __str__(self) -> str:
        return self.value


class _StrIsName:
    def __str__(self) -> str:
        return self.name


class GuildType(Enum):
    big_rld   = 459431848003502091
    small_rld = 684885552906240053


class BigRLDChannelType(_StrIsName, Enum):
    general        = 459431848939094028
    bot            = 651159185635016715
    battle_results = 459434351722102784
    complain       = 709414135246487583
    classified     = 477082279424819211
    recruiters     = 600313572722999296
    memes          = 459434377739370506


class BigRLDRoleType(_StrIsName, Enum):
    xo       = 459433742088273920
    po       = 600307495893729301
    co       = 600306954803347486
    ro       = 600306780832137248
    private  = 459435327438716928
    member   = 467814689699528709
    onlyfans = 714512751946498070
    friends  = 502955822247182337


class SmallRLDChannelType(_StrIsName, Enum):
    general        = 684885552906240148
    bot            = 684888041508306986
    battle_results = 684887476283769023
    complain       = 777584309384773642
    classified     = 684887256842108933
    recruiters     = 684887773207068738
    memes          = 684887675257618517


class SmallRLDRoleType(_StrIsName, Enum):
    xo      = 684886587670265880
    po      = 684886549501968491
    co      = 684886483672629264
    ro      = 684886434737291341
    private = 684886038086549607
    member  = 684886009242058786
    friends = 684899235317284924


class WotApiType(Enum):
    official   = 'api.worldoftanks.{}'
    unofficial = 'worldoftanks.{}'
    wargaming  = '{}.wargaming.net'


class WN8Colour(Enum):
    black        = 0
    red          = 13447987
    orange       = 14121216
    yellow       = 14136832
    light_green  = 7181601
    dark_green   = 5010990
    blue         = 4887223
    light_purple = 8607645
    dark_purple  = 5910901


class MasteryType(Enum):
    mastery      = 4
    first_class  = 3
    second_class = 2
    third_class  = 1
    no_mastery   = 0


class MarkType(Enum):
    third_mark  = 3
    second_mark = 2
    first_mark  = 1
    no_mark     = 0


class LoseReasons(_StrIsValue, Enum):
    base          = 'base capture'
    extermination = 'all tanks killed'
    technical     = 'technical victory'
    timeout       = 'time ran out'


# TODO: Add statusses for globalmap events
class EventStatusType(Enum):
    finished = 0


class Region(_StrIsValue, Enum):
    eu   = 'eu'
    na   = 'na'
    ru   = 'ru'
    asia = 'asia'


class FormattedNationType(_StrIsValue, Enum):
    ussr    = 'the USSR'
    usa     = 'the USA'
    uk      = 'the UK'
    germany = 'Germany'
    china   = 'China'
    japan   = 'Japan'
    sweden  = 'Sweden'
    poland  = 'Poland'
    italy   = 'Italy'
    france  = 'France'
    czech   = 'Czechoslovakia'


class FormattedTankType(_StrIsValue, Enum):
    heavyTank  = 'heavy tank'
    mediumTank = 'medium tank'
    lightTank  = 'light tank'
    AT_SPG     = 'tank destroyer'
    SPG        = 'spg'


class FrontType(_StrIsValue, Enum):
    league1 = 'Basic'
    league2 = 'Advanced'
    league3 = 'Elite'


class Emote(_StrIsValue, Enum):
    # GENERAL
    flushed_pumpkin    = '<:flushed_pumpkin:905125381475037195>'
    feels_birthday_man = '<:feels_birthday_man:905125599079702578>'
    loading            = '<a:loading:905516653931016252>'
    cry                = ':cry:'
    joy                = ':joy:'
    heart              = ':heart:'
    oncoming_bus       = ':oncoming_bus:'
    eyes               = ':eyes:'
    bus                = ':bus:'
    shush              = ':shushing_face:'
    rolling_eyes       = ':rolling_eyes:'
    mad                = ':triumph:'
    monocle            = ':face_with_monocle:'
    tada               = ':tada:'
    cake               = ':birthday:'

    # PLAYBAR
    start        = '<:start:904076967492595792>'
    end          = '<:end:904076967538733106>'
    middle       = '<:middle:904076967622631464>'
    center_empty = '<:center_empty:904076967505174528>'
    center_full  = '<:center_full:904076967190618193>'

    # MASTERY
    mastery      = '<:mastery:870650067541962802>'
    first_class  = '<:first_class:870650067395182592>'
    second_class = '<:second_class:870650067625840660>'
    third_class  = '<:third_class:870650067604893726>'

    # MEDALS
    # 3
    armored_fist         = '<:armored_fist:902520927311511552>'
    brothers_in_arms     = '<:brothers_in_arms:902520927357640726>'
    crucial_contribution = '<:crucial_contribution:902520927709982730>'
    sudden_strike        = '<:sudden_strike:902520927865176074>'
    tactical_supremacy   = '<:tactical_supremacy:902520928032919573>'
    # 4
    arsonist             = '<:arsonist:902520967073501196>'
    bruiser              = '<:bruiser:902520967635566592>'
    first_merit          = '<:first_merit:902520967673311243>'
    demolition_expert    = '<:demolition_expert:902520967857840159>'
    cool_headed          = '<:cool_headed:902520967874633768>'
    eye_for_an_eye       = '<:eye_for_an_eye:902520968117878805>'
    lucky                = '<:lucky:902520968243740674>'
    king_of_the_hill     = '<:king_of_the_hill:902520968273080381>'
    god_of_war           = '<:god_of_war:902520968315023360>'
    hand_of_god          = '<:hand_of_god:902520968319238144>'
    rock_solid           = '<:rock_solid:902520968788979752>'
    no_mans_land         = '<:no_mans_land:902520968797364284>'
    spartan              = '<:spartan:902520968948355112>'
    # 6
    operation_winter     = '<:operation_winter:902521004432175125>'
    rocket_scientist     = '<:rocket_scientist:902521004889341962>'
    tank_sniper          = '<:tank_sniper:902521005120040990>'
    # 0
    confederate          = '<:confederate:902520730082754640>'
    defender             = '<:defender:902520730204381185>'
    high_caliber         = '<:high_caliber:902520730502197278>'
    invader              = '<:invader:902520730619641896>'
    scout                = '<:scout:902520730946773083>'
    steel_wall           = '<:steel_wall:902520731177459732>'
    top_gun              = '<:top_gun:902520731487854602>'
    war_genius           = '<:war_genius:902520731513012234>'
    wolf_among_sheep     = '<:wolf_among_sheep:902520731814985738>'
    patrol_duty          = '<:patrol_duty:902520732800679946>'
    # 1
    bombardier           = '<:bombardier:902520775624503346>'
    duelist              = '<:duelist:902520775754522655>'
    cold_blood           = '<:cold_blood:902520775821623357>'
    counter_battery_fire = '<:counter_battery_fire:902520775972622376>'
    fighter              = '<:fighter:902520776165580801>'
    kamikaze             = '<:kamikaze:902520776324956160>'
    raider               = '<:raider:902520776467578911>'
    reaper               = '<:reaper:902520776660508682>'
    shell_proof          = '<:shell_proof:902520776798900264>'
    shoot_to_kill        = '<:shoot_to_kill:902520776983449610>'
    spotter              = '<:spotter:902520777071546368>'
    tactical_genius      = '<:tactical_genius:902520777218326618>'
    tactical_superiority = '<:tactical_superiority:902520777298038784>'
    will_to_win          = '<:will_to_win:902520777570648064>'
    # 2
    bruno                = '<:bruno:902520869031673877>'
    billotte             = '<:billotte:902520869165883492>'
    burda                = '<:burda:902520869170081834>'
    de_langlade          = '<:de_langlade:902520869778243655>'
    dumitru              = '<:dumitru:902520869874704444>'
    fadin                = '<:fadin:902520870117965835>'
    gore                 = '<:gore:902520870231232542>'
    halonen              = '<:halonen:902520870419972127>'
    kolobanov            = '<:kolobanov:902520870633897984>'
    lehveslaiho          = '<:lehveslaiho:902520870860386325>'
    naidin               = '<:naidin:902520871007162418>'
    nicols               = '<:nicols:902520871128805427>'
    pascucci             = '<:pascucci:902520871292375092>'
    orlik                = '<:orlik:902520871464366080>'
    oskin                = '<:oskin:902520871527252028>'
    pool                 = '<:pool:902520871732793385>'
    radley_walters       = '<:radley_walters:902520872261263370>'
    raseiniai            = '<:raseiniai:902520872282259486>'
    stark                = '<:stark:902520872462614558>'
    yoshio_tamada        = '<:yoshio_tamada:902520872563265577>'
    tarczay              = '<:tarczay:902520872940732436>'

    # ICONS
    # Stats
    spot    = '<:spots:870680573067284512>'
    win     = '<:winrate:870680573583187988>'
    defend  = '<:defense:870680573457346580>'
    kill    = '<:kills:870680573482512405>'
    # Clan logs
    leave   = '<:leave:871808718847758356>'
    add     = '<:add:871808718721933322>'
    remove  = '<:remove:871808718830981170>'
    victory = '<:victory:871808718419939399>'
    defeat  = '<:defeat:871808719074230272>'
    revolt  = '<:revolt:903703095995953202>'

    # MOE
    # Germany
    germany_1 = '<:germany_1:870654024817459270>'
    germany_2 = '<:germany_2:870654024892964864>'
    germany_3 = '<:germany_3:870654024968441896>'
    # Union of Soviet Socialist Republics
    ussr_1    = '<:ussr_1:870654025304002642>'
    ussr_2    = '<:ussr_2:870654025601777734>'
    ussr_3    = '<:ussr_3:870654025706659870>'
    # United States of America
    usa_1     = '<:usa_1:870654025551454228>'
    usa_2     = '<:usa_2:870654025530494996>'
    usa_3     = '<:usa_3:870654025782132786>'
    # France
    france_1  = '<:france_1:870654024725184522>'
    france_2  = '<:france_2:870654024779702343>'
    france_3  = '<:france_3:870654024846802984>'
    # United Kingdom
    uk_1      = '<:uk_1:870654025404645387>'
    uk_2      = '<:uk_2:870654025454997555>'
    uk_3      = '<:uk_3:870654025517912094>'
    # China
    china_1   = '<:china_1:870654024649670666>'
    china_2   = '<:china_2:870654024662257694>'
    china_3   = '<:china_3:870654024628719627>'
    # Japan
    japan_1   = '<:japan_1:870654024951693373>'
    japan_2   = '<:japan_2:870654025236893716>'
    japan_3   = '<:japan_3:870654025228501042>'
    # Czechoslovakia
    czech_1   = '<:czech_1:870654024574185503>'
    czech_2   = '<:czech_2:870654025031352350>'
    czech_3   = '<:czech_3:870654024767111228>'
    # Poland
    poland_1  = '<:poland_1:870654025148821504>'
    poland_2  = '<:poland_2:870654025207533618>'
    poland_3  = '<:poland_3:870654025291427870>'
    # Sweden
    sweden_1  = '<:sweden_1:870654025052356629>'
    sweden_2  = '<:sweden_2:870654025429839892>'
    sweden_3  = '<:sweden_3:870654025043947532>'
    # Italy
    italy_1   = '<:italy_1:870654025002024970>'
    italy_2   = '<:italy_2:870654025002000454>'
    italy_3   = '<:italy_3:870654024964255745>'
