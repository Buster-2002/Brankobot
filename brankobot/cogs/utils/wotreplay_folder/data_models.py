from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Union


class BattleType(Enum):
    regular           = 1
    training_room     = 2
    tank_company      = 3
    tutorial          = 6
    team_battle       = 7
    historical_battle = 8
    fun_events        = 9
    skirmish          = 10
    stronghold        = 11
    ladder            = 12
    last_stand        = 1009
    ranked            = 22
    grand_battle      = 24
    front_line        = 27
    bots              = 1001
    tournament1       = 4
    tournament2       = 14
    global_map1       = 5
    global_map2       = 13
    proving_ground1   = 16
    proving_ground2   = 17

    def __str__(self) -> str:
        return self.name


class GameModeType(Enum):
    ctf = 'capture the flag'

    def __str__(self) -> str:
        return self.value


@dataclass
class BattleEconomy:
    resupply_ammunition: int
    resupply_consumables: int
    credits_to_draw: int
    original_prem_squad_credits: int
    credits_contribution_in: int
    event_credits: int
    piggy_bank: int
    premium_credits_factor_100: int
    original_credits_contribution_in: int
    original_credits_penalty: int
    original_gold: int
    booster_credits: int
    referral_20_credits: int
    subtotal_event_coin: int
    booster_credits_factor_100: int
    credits_contribution_out: int
    credits: int
    gold_replay: int
    credits_penalty: int
    repair: int
    original_credits: int
    order_credits: int
    order_credits_factor_100: int
    original_crystal: int
    applied_premium_credits_factor_100: int
    prem_squad_credits: int
    event_gold: int
    gold: int
    original_credits_contribution_in_squad: int
    original_event_coin: int
    factual_credits: int
    event_coin: int
    crystal: int
    crystal_replay: int
    original_credits_to_draw_squad: int
    subtotal_credits: int
    credits_replay: int
    event_event_coin: int
    subtotal_crystal: int
    achievement_credits: int
    subtotal_gold: int
    event_crystal: int
    event_coin_replay: int
    auto_repair_cost: int
    original_credits_penalty_squad: int


@dataclass
class BattlePerformance:
    stunned: int
    achievements: List[int]
    direct_hits: int
    damage_assisted_radio: int
    stun_duration: float
    win_points: int
    damaged_while_moving: int
    kills: int
    percent_of_total_team_damage: float
    mark_of_mastery: int
    no_damage_direct_hits_received: int
    equipment_damage_dealt: int
    team_kills: int
    shots: int
    team: int
    death_count: int
    stun_number: int
    spotted: int
    killer_id: int
    solo_flag_capture: int
    marks_on_gun: int
    killed_and_damaged_by_all_squad_mates: int
    rollouts_count: int
    health: int
    stop_respawn: int
    team_damage_dealt: int
    resource_absorbed: int
    damaged_while_enemy_moving: int
    damage_received: int
    percent_from_second_best_damage: float
    committed_suicide: bool
    life_time: int
    damage_assisted_track: int
    sniper_damage_dealt: int
    fairplay_factor: int
    damage_blocked_by_armour: int
    dropped_capture_points: int
    damage_received_from_invisibles: int
    max_health: int
    moving_avg_damage: int
    flag_capture: int
    kills_before_team_was_damaged: int
    potential_damage_received: int
    direct_team_hits: int
    damage_dealt: int
    piercings_received: int
    piercings: int
    prev_mark_of_mastery: int
    damaged: int
    death_reason: int
    capture_points: int
    damage_before_team_was_damaged: int
    explosion_hits_received: int
    damage_rating: int
    meters_driven: int
    explosion_hits: int
    direct_hits_received: int
    is_team_killer: bool
    capturing_base: Optional[bool]
    damage_assisted_stun: int
    damage_assisted_smoke: int
    total_destroyed_modules: int
    damage_assisted_inspire: int


@dataclass
class BattlePlayer:
    id: int
    fake_name: str
    team: int
    clan_tag: str
    vehicle_type: str
    vehicle_tag: str
    vehicle_nation: str
    is_alive: bool
    forbid_in_battle_invitations: bool
    igr_type: int
    is_team_killer: bool
    name: str
    kills: Union[int, str]


@dataclass
class BattleXP:
    order_free_xp_factor_100: int
    order_xp_factor_100: int
    free_xp_replay: Optional[int]
    xp_other: int
    premium_t_men_xp_factor_100: int
    achievement_xp: int
    igr_xp_factor_10: int
    event_t_men_xp: int
    premium_plus_xp_factor_100: int
    premium_plus_t_men_xp_factor_100: int
    original_t_men_xp: int
    referral_20_xp: int
    subtotal_t_men_xp: int
    premium_vehicle_xp_factor_100: int
    additional_xp_factor_100: int
    factual_xp: int
    order_free_xp: int
    booster_t_men_xp_factor_100: int
    original_xp: int
    applied_premium_xp_factor_100: int
    booster_xp: int
    factual_free_xp: int
    daily_xp_factor_10: int
    event_free_xp: int
    player_rank_xp_factor_100: int
    xp_penalty: int
    xp: int
    booster_xp_factor_100: int
    order_t_men_xp: int
    original_xp_penalty: int
    order_t_men_xp_factor_100: int
    subtotal_xp: int
    squad_xp: int
    original_free_xp: int
    xp_assist: int
    free_xp: int
    premium_vehicle_xp: int
    referral_20_xp_factor_100: int
    event_xp: int
    subtotal_free_xp: int
    achievement_free_xp: int
    player_rank_xp: int
    squad_xp_factor_100: int
    applied_premium_t_men_xp_factor_100: int
    booster_t_men_xp: int
    xp_attack: int
    ref_system_xp_factor_10: int
    t_men_xp_replay: Optional[int]
    premium_xp_factor_100: int
    t_men_xp: int
    booster_free_xp_factor_100: int
    booster_free_xp: int
    battle_num: int


@dataclass
class MetaData:
    replay_date: datetime
    player_vehicle: str
    nation: str
    internal_tank_name: str
    version: str
    client_version: str
    client_version_executable: str
    region_code: str
    account_id: int
    server_name: str
    map_display_name: str
    map_name: str
    gameplay_id: str
    battle_type_id: int
    has_mods: bool
    player_name: str
    division: Optional[int]
    gui_type: int
    arena_create_time: int
    duration: int
    arena_type_id: int
    gas_attack_winner_team: int
    winner_team: int
    veh_lock_mode: int
    bonus_type: int

    @property
    def gameplay_mode(self) -> GameModeType:
        return GameModeType[self.gameplay_id]

    @property
    def battle_type(self) -> BattleType:
        return BattleType(self.battle_type_id)

