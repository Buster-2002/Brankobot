# -*- coding: utf-8 -*-
from typing import List

from .data_models import (BattleEconomy, BattlePerformance, BattlePlayer,
                          BattleXP, MetaData)
from .extract_data_from_replay import Replay


class ReplayData:
    '''Extracts data from a wotreplay
    '''
    def __init__(self, file_path: str):
        self.replay = Replay(file_path)


    @property
    def battle_metadata(self) -> MetaData:
        return MetaData(**self.replay.get_battle_metadata())


    @property
    def battle_performance(self) -> BattlePerformance:
        return BattlePerformance(**self.replay.get_battle_performance())

    @property
    def battle_players(self) -> List[BattlePlayer]:
        return [BattlePlayer(**player) for player in self.replay.get_battle_players()]


    @property
    def battle_economy(self) -> dict:
        return BattleEconomy(**self.replay.get_battle_economy())
    
    
    @property
    def battle_xp(self) -> dict:
        return BattleXP(**self.replay.get_battle_xp())
