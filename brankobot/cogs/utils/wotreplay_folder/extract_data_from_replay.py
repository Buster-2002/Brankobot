# -*- coding: utf-8 -*-
import json
from datetime import datetime
from typing import Any, Generator, List


class Parser:
    def __init__(self, filename: str):
        self.file_content = self._open_file(filename)
        self.raw_json = self._extract_json_objects(self.file_content)
        self.battle_data = []
        self.replay_metadata = None

        for i, string_obj in enumerate(self.raw_json):
            if i == 0:
                self.replay_metadata = string_obj
            else:
                self.battle_data.append(string_obj)


    @staticmethod
    def _open_file(file: str) -> str:
        '''Opens wotreplay file and returns raw json data

        Args:
            file (str): The file to extract data from

        Returns:
            str: Raw json data
        '''        
        with open(file, 'r', encoding='utf-8', errors='ignore') as infile:
            for i, line in enumerate(infile):
                if i == 0:
                    # Only the first line contains data. The rest is binary metadata to replay the record.
                    raw_data = []
                    raw_line = line.split()
                    for record in raw_line:
                        for letter in record:
                            if ord(letter) < 34 or ord(letter) > 127:
                                pass
                            else:
                                raw_data.append(letter)

        return ''.join(raw_data)


    @staticmethod
    def _extract_json_objects(text: str) -> Generator[Any, None, None]:
        '''Find valid data in text and yield decoded json

        Args:
            text (str): The text to extract json from

        Yields:
            Any: The json data
        '''        
        decoder = json.JSONDecoder()
        pos = 0

        while True:
            match = text.find('{', pos)
            if match == -1:
                break
            try:
                result, index = decoder.raw_decode(text[match:])
                yield result
                pos = match + index
            except ValueError:
                pos = match + 1


class Replay:
    def __init__(self, file_name: str):
        self.file_name = file_name
        self._extract_data()


    def _extract_data(self):
        '''
        Extract json data from a single replay.
        '''
        c = Parser(self.file_name)
        self.battle_data = c.battle_data
        self.meta_data = c.replay_metadata

        # Debug purposes
        with open('battle_data.json', 'w', encoding='utf-8') as file:
            json.dump(self.battle_data, file, indent=2)
        with open('meta_data.json', 'w', encoding='utf-8') as file:
            json.dump(self.meta_data, file, indent=2)


    @property
    def replay_date(self) -> datetime:
        '''
        Gets the replay date from the metadata
        '''
        date_string = self.meta_data.get('dateTime')
        return datetime.strptime(date_string, '%d.%m.%Y%H:%M:%S')


    def get_battle_metadata(self) -> dict:
        '''
        Returns meta data
        '''
        data = self.meta_data
        raw_data = self.battle_data[0]['common']
        meta_data = {
            'replay_date': self.replay_date,
            'player_vehicle': data.get('playerVehicle'),
            'nation': str(data.get('playerVehicle')).split('-')[0],
            'internal_tank_name': str(data.get('playerVehicle')).split('-')[1],
            'version': str(data.get('clientVersionFromXml')).split('#')[0].split('v.')[1],
            'client_version': data.get('clientVersionFromXml'),
            'client_version_executable': data.get('clientVersionFromExe'),
            'region_code': data.get('regionCode'),
            'account_id': int(self.meta_data.get('playerID')),
            'server_name': data.get('serverName'),
            'map_display_name': data.get('mapDisplayName'),
            'map_name': data.get('mapName'),
            'gameplay_id': data.get('gameplayID'),
            'battle_type_id': data.get('battleType'),
            'has_mods': data.get('hasMods'),
            'player_name': data.get('playerName'),
            'division': raw_data.get('division'),
            'gui_type': raw_data.get('guiType'),
            'arena_create_time': raw_data.get('arenaCreateTime'),
            'duration': raw_data.get('duration'),
            'arena_type_id': raw_data.get('arenaTypeID'),
            'gas_attack_winner_team': raw_data.get('gasAttackWinnerTeam'),
            'winner_team': raw_data.get('winnerTeam'),
            'veh_lock_mode': raw_data.get('vehLockMode'),
            'bonus_type': raw_data.get('bonusType')
        }

        return meta_data


    def get_battle_performance(self) -> dict:
        '''
        Returns performance data
        '''
        raw_data = self.battle_data[0]['personal']
        battle_id = list(raw_data.keys())[0]
        data = raw_data[battle_id]

        battle_performance = {
            'stunned': data.get('stunned', 0),
            'achievements': data.get('achievements', []),
            'direct_hits': data.get('directHits', 0),
            'damage_assisted_radio': data.get('damageAssistedRadio', 0),
            'stun_duration': data.get('stunDuration', 0.0),
            'win_points': data.get('winPoints', 0),
            'damaged_while_moving': data.get('damagedWhileMoving', 0),
            'kills': data.get('kills', 0),
            'percent_of_total_team_damage': data.get('percentFromTotalTeamDamage', 0.0),
            'mark_of_mastery': data.get('markOfMastery', 0),
            'no_damage_direct_hits_received': data.get('noDamageDirectHitsReceived', 0),
            'equipment_damage_dealt': data.get('equipmentDamageDealt', 0),
            'team_kills': data.get('tkills', 0),
            'shots': data.get('shots', 0),
            'team': data.get('team', 0),
            'death_count': data.get('deathCount', 0),
            'stun_number': data.get('stunNum', 0),
            'spotted': data.get('spotted', 0),
            'killer_id': data.get('killerID', 0),
            'solo_flag_capture': data.get('soloFlagCapture', 0),
            'marks_on_gun': data.get('marksOnGun', 0),
            'killed_and_damaged_by_all_squad_mates': data.get('killedAndDamagedByAllSquadmates', 0),
            'rollouts_count': data.get('rolloutsCount', 0),
            'health': data.get('health', 0),
            'stop_respawn': data.get('stopRespawn', False),
            'team_damage_dealt': data.get('tdamageDealt', 0),
            'resource_absorbed': data.get('resourceAbsorbed', 0),
            'damaged_while_enemy_moving': data.get('damagedWhileEnemyMoving', 0),
            'damage_received': data.get('damageReceived', 0),
            'percent_from_second_best_damage': data.get('percentFromSecondBestDamage', 0),
            'committed_suicide': data.get('committedSuicide', False),
            'life_time': data.get('lifeTime', 0),
            'damage_assisted_track': data.get('damageAssistedTrack', 0),
            'sniper_damage_dealt': data.get('sniperDamageDealt', 0),
            'fairplay_factor': data.get('fairplayFactor10', 0),
            'damage_blocked_by_armour': data.get('damageBlockedByArmor', 0),
            'dropped_capture_points': data.get('droppedCapturePoints', 0),
            'damage_received_from_invisibles': data.get('damageReceivedFromInvisibles', 0),
            'max_health': data.get('maxHealth', 0),
            'moving_avg_damage': data.get('movingAvgDamage', 0),
            'flag_capture': data.get('flagCapture', 0),
            'kills_before_team_was_damaged': data.get('killsBeforeTeamWasDamaged', 0),
            'potential_damage_received': data.get('potentialDamageReceived', 0),
            'direct_team_hits': data.get('directTeamHits', 0),
            'damage_dealt': data.get('damageDealt', 0),
            'piercings_received': data.get('piercingsReceived', 0),
            'piercings': data.get('piercings', 0),
            'prev_mark_of_mastery': data.get('prevMarkOfMastery', 0),
            'damaged': data.get('damaged', 0),
            'death_reason': data.get('deathReason', 0),
            'capture_points': data.get('capturePoints', 0),
            'damage_before_team_was_damaged': data.get('damageBeforeTeamWasDamaged', 0),
            'explosion_hits_received': data.get('explosionHitsReceived', 0),
            'damage_rating': data.get('damageRating', 0),
            'meters_driven': data.get('mileage', 0),
            'explosion_hits': data.get('explosionHits', 0),
            'direct_hits_received': data.get('directHitsReceived', 0),
            'is_team_killer': data.get('isTeamKiller', False),
            'capturing_base': data.get('capturingBase', False),
            'damage_assisted_stun': data.get('damageAssistedStun', 0),
            'damage_assisted_smoke': data.get('damageAssistedSmoke', 0),
            'total_destroyed_modules': data.get('tdestroyedModules', 0),
            'damage_assisted_inspire': data.get('damageAssistedInspire', 0)
        }

        return battle_performance


    def get_battle_players(self) -> List[dict]:
        '''
        Returns player data
        '''
        data = self.battle_data
        player_ids = list(data[1].keys())
        battle_players = []

        for player_id in player_ids:
            raw_data = data[1][player_id]
            vehicle = str(raw_data['vehicleType']).split(':')

            battle_players.append({
                'id': int(player_id),
                'fake_name': raw_data.get('fakeName', 'None'),
                'team': raw_data['team'],
                'clan_tag': raw_data['clanAbbrev'],
                'vehicle_type': raw_data['vehicleType'],
                'vehicle_tag': vehicle[-1],
                'vehicle_nation': vehicle[0],
                'is_alive': raw_data['isAlive'],
                'forbid_in_battle_invitations': raw_data['forbidInBattleInvitations'],
                'igr_type': raw_data['igrType'],
                'is_team_killer': bool(raw_data['isTeamKiller']),
                'name': raw_data['name'],
                'kills': data[2].get(player_id, {'frags': 'N/A'})['frags']
            })

        return battle_players


    def get_battle_economy(self) -> dict:
        '''
        Returns economy data
        '''
        raw_data = self.battle_data[0]['personal']
        battle_id = list(raw_data.keys())[0]
        data = raw_data[battle_id]

        battle_economy = {
            'resupply_ammunition': data.get('autoLoadCost', [0])[0],
            'resupply_consumables': data.get('autoEquipCost', [0])[0],
            'credits_to_draw': data.get('creditsToDraw', 0),
            'original_prem_squad_credits': data.get('originalPremSquadCredits', 0),
            'credits_contribution_in': data.get('creditsContributionIn', 0),
            'event_credits': data.get('eventCredits', 0),
            'piggy_bank': data.get('piggyBank', 0),
            'premium_credits_factor_100': data.get('premiumCreditsFactor100', 0),
            'original_credits_contribution_in': data.get('originalCreditsContributionIn', 0),
            'original_credits_penalty': data.get('originalPremSquadCredits', 0),
            'original_gold': data.get('originalGold', 0),
            'booster_credits': data.get('boosterCredits', 0),
            'referral_20_credits': data.get('referral20Credits', 0),
            'subtotal_event_coin': data.get('subtotalEventCoin', 0),
            'booster_credits_factor_100': data.get('boosterCreditsFactor100', 0),
            'credits_contribution_out': data.get('creditsContributionOut', 0),
            'credits': data.get('originalPremSquadCredits', 0),
            'gold_replay': data.get('goldReplay', 0),
            'credits_penalty': data.get('creditsPenalty', 0),
            'repair': data.get('repair', 0),
            'original_credits': data.get('originalCredits', 0),
            'order_credits': data.get('orderCredits', 0),
            'order_credits_factor_100': data.get('orderCreditsFactor100', 0),
            'original_crystal': data.get('originalCrystal', 0),
            'applied_premium_credits_factor_100': data.get('appliedPremiumCreditsFactor100', 0),
            'prem_squad_credits': data.get('premSquadCredits', 0),
            'event_gold': data.get('eventGold', 0),
            'gold': data.get('gold', 0),
            'original_credits_contribution_in_squad': data.get('originalCreditsContributionInSquad', 0),
            'original_event_coin': data.get('originalEventCoin', 0),
            'factual_credits': data.get('factualCredits', 0),
            'event_coin': data.get('eventCoin', 0),
            'crystal': data.get('crystal', 0),
            'crystal_replay': data.get('crystalReplay', 0),
            'original_credits_to_draw_squad': data.get('originalCreditsToDrawSquad', 0),
            'subtotal_credits': data.get('subtotalCredits', 0),
            'credits_replay': data.get('creditsReplay', 0),
            'event_event_coin': data.get('eventEventCoin', 0),
            'subtotal_crystal': data.get('subtotalCrystal', 0),
            'achievement_credits': data.get('achievementCredits', 0),
            'subtotal_gold': data.get('subtotalGold', 0),
            'event_crystal': data.get('eventCrystal', 0),
            'event_coin_replay': data.get('eventCoinReplay', 0),
            'auto_repair_cost': data.get('autoRepairCost', 0),
            'original_credits_penalty_squad': data.get('originalCreditsPenaltySquad', 0)
        }

        return battle_economy


    def get_battle_xp(self) -> dict:
        '''
        Returns XP data
        '''
        raw_data = self.battle_data[0]['personal']
        battle_id = list(raw_data.keys())[0]
        data = raw_data[battle_id]

        battle_xp = {
            'order_free_xp_factor_100': data.get('orderFreeXPFactor100', 0),
            'order_xp_factor_100': data.get('orderXPFactor100', 0),
            'free_xp_replay': data.get('freeXPReplay', 0),
            'xp_other': data.get('xp/other', 0),
            'premium_t_men_xp_factor_100': data.get('premiumTmenXPFactor100', 0),
            'achievement_xp': data.get('achievementXP', 0),
            'igr_xp_factor_10': data.get('igrXPFactor10', 0),
            'event_t_men_xp': data.get('eventTMenXP', 0),
            'premium_plus_xp_factor_100': data.get('premiumPlusXPFactor100', 0),
            'premium_plus_t_men_xp_factor_100': data.get('premiumPlusTmenXPFactor100', 0),
            'original_t_men_xp': data.get('originalTMenXP', 0),
            'referral_20_xp': data.get('referral20XP', 0),
            'subtotal_t_men_xp': data.get('subtotalTMenXP', 0),
            'premium_vehicle_xp_factor_100': data.get('premiumVehicleXPFactor100', 0),
            'additional_xp_factor_100': data.get('additionalXPFactor10', 0),
            'factual_xp': data.get('factualXP', 0),
            'order_free_xp': data.get('orderFreeXP', 0),
            'booster_t_men_xp_factor_100': data.get('boosterTMenXPFactor100', 0),
            'original_xp': data.get('originalXP', 0),
            'applied_premium_xp_factor_100': data.get('appliedPremiumXPFactor100', 0),
            'booster_xp': data.get('boosterXP', 0),
            'factual_free_xp': data.get('factualFreeXP', 0),
            'daily_xp_factor_10': data.get('dailyXPFactor10', 0),
            'event_free_xp': data.get('eventFreeXP', 0),
            'player_rank_xp_factor_100': data.get('playerRankXPFactor100', 0),
            'xp_penalty': data.get('xpPenalty', 0),
            'xp': data.get('xp', 0),
            'booster_xp_factor_100': data.get('boosterXPFactor100', 0),
            'order_t_men_xp': data.get('orderTMenXP', 0),
            'original_xp_penalty': data.get('originalXPPenalty', 0),
            'order_t_men_xp_factor_100': data.get('orderTMenXPFactor100', 0),
            'subtotal_xp': data.get('subtotalXP', 0),
            'squad_xp': data.get('squadXP', 0),
            'original_free_xp': data.get('originalFreeXP', 0),
            'xp_assist': data.get('xp/assist', 0),
            'free_xp': data.get('freeXP', 0),
            'premium_vehicle_xp': data.get('premiumVehicleXP', 0),
            'referral_20_xp_factor_100': data.get('referral20XPFactor100', 0),
            'event_xp': data.get('eventXP', 0),
            'subtotal_free_xp': data.get('subtotalFreeXP', 0),
            'achievement_free_xp': data.get('achievementFreeXP', 0),
            'player_rank_xp': data.get('playerRankXP', 0),
            'squad_xp_factor_100': data.get('squadXPFactor100', 0),
            'applied_premium_t_men_xp_factor_100': data.get('appliedPremiumTmenXPFactor100', 0),
            'booster_t_men_xp': data.get('boosterTMenXP', 0),
            'xp_attack': data.get('xp/attack', 0),
            'ref_system_xp_factor_10': data.get('refSystemXPFactor10', 0),
            't_men_xp_replay': data.get('tmenXPReplay', 0),
            'premium_xp_factor_100': data.get('premiumXPFactor100', 0),
            't_men_xp': data.get('tmenXP', 0),
            'booster_free_xp_factor_100': data.get('boosterFreeXPFactor100', 0),
            'booster_free_xp': data.get('boosterFreeXP', 0),
            'battle_num': data.get('battleNum', 0)
        }

        return battle_xp
