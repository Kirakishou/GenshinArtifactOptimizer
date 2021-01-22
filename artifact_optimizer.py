import math
import copy
import functools
import json
from collections import Counter
from integer_composition_tools import *


class EntityStats:
    def __init__(self, entity_name, entity_class):
        self.name = entity_name
        with open('bin/' + entity_class + '.json') as f:
            data = json.load(f)
            entity = next(item for item in data if item["name"] == entity_name)
            self.stats = Counter(entity["stats"])


class Character(EntityStats):
    def __init__(self, character_name):
        super().__init__(character_name, 'characters')


class Weapon(EntityStats):
    def __init__(self, weapon_name):
        super().__init__(weapon_name, 'weapons')


class Effect(EntityStats):
    def __init__(self, effect_name):
        super().__init__(effect_name, 'effects')


class DefaultDamageModel:
    BASE_CRIT_RATE = 0.05
    BASE_CRIT_DMG = 0.5
    FEATHER_ATT = 311
    SUBSTAT_ATT_MULT = 0.04975
    SUBSTAT_EM = 19.75
    SUBSTAT_CRIT_RATE = 0.033
    SUBSTAT_CRIT_DMG = 0.066
    STAT_ATT_MULT = 0.466
    STAT_EM = 187
    STAT_ELEM_DMG = 0.466
    STAT_CRIT_RATE = 0.311
    STAT_CRIT_DMG = 0.622
    FIRE_MELT_MULT = 2
    ICE_MELT_MULT = 1.5
    WATER_VAPOR_MULT = 2
    FIRE_VAPOR_MULT = 1.5
    REACTIONLESS_MULT = 1
    CHAR_LEVEL = 90

    STATS = ["AttMult", "EM", "ElemDmg", "CritRate", "CritDmg"]
    STAT_UPPER_LIMITS = [3,3,1,1,1]

    SUBSTATS = ["AttMult", "EM", "CritRate", "CritDmg"]


    def __init__(self, character=None, weapon=None, effects=[], enemy_level=93, enemy_res=0.1):
        self.max_dmg = 0
        self.opt_stats = None
        self.opt_substats = None
        self.character = character.name
        self.weapon = weapon.name
        self.effects = [effect.name for effect in effects]
        self.character_stats = character.stats
        self.weapon_stats = weapon.stats
        self.effect_bonuses = functools.reduce(lambda a,b : a + b.stats, effects, Counter({}))
        self.modifiers = self.character_stats + self.weapon_stats + self.effect_bonuses
        self.enemy_level = enemy_level
        self.enemy_res = enemy_res
        self.mitigated_dmg_mult = self.calc_dmg_mitigated()

    
    def calc_dmg_mitigated(self):
        def_mitigated_mult = (self.CHAR_LEVEL + 100) / ((1 - self.modifiers["DefReduced"]) * (self.enemy_level + 100) + self.CHAR_LEVEL + 100)
        total_res = self.enemy_res - self.modifiers["ResReduced"]
        if total_res < 0:
            res_mitigated_mult = 1 - (total_res / 2)
        elif total_res < 0.75:
            res_mitigated_mult = 1 - total_res
        else:
            res_mitigated_mult = 1 / (4 * total_res + 1)
        return def_mitigated_mult * res_mitigated_mult


    def total_att(self, stat_allocs, substat_allocs):
        base_att = self.modifiers["BaseAtt"]
        stat_att_mult = self.STAT_ATT_MULT * stat_allocs["AttMult"]
        substat_att_mult = self.SUBSTAT_ATT_MULT * substat_allocs["AttMult"]
        base_att_mult = 1 + stat_att_mult + substat_att_mult + self.modifiers["AttMult"]

        flat_att = self.FEATHER_ATT + self.modifiers["FlatAtt"]

        return base_att * base_att_mult + flat_att


    def crit_mult(self, stat_allocs, substat_allocs):
        stat_crit_rate = self.STAT_CRIT_RATE * stat_allocs["CritRate"]
        substat_crit_rate = self.SUBSTAT_CRIT_RATE * substat_allocs["CritRate"]
        stat_crit_dmg = self.STAT_CRIT_DMG * stat_allocs["CritDmg"]
        substat_crit_dmg = self.SUBSTAT_CRIT_DMG * substat_allocs["CritDmg"]

        raw_critrate = stat_crit_rate + substat_crit_rate + self.BASE_CRIT_RATE + self.modifiers["CritRate"]

        crR = min(1, (self.modifiers["CritRateMult"] + 1) * raw_critrate)
        crD = stat_crit_dmg + substat_crit_dmg + self.BASE_CRIT_DMG + self.modifiers["CritDmg"]
        return 1 + crD * crR


    def reaction_mult(self, stat_allocs, substat_allocs, reaction_multiplier):
        stat_em = self.STAT_EM * stat_allocs["EM"]
        substat_em =self.SUBSTAT_EM * substat_allocs["EM"]

        em = stat_em + substat_em + self.modifiers["EM"]
        return (self.modifiers["ReactionMult"] + 1) * reaction_multiplier * (1 + 0.001893 * em * math.exp(-0.000505 * em))


    def dmg_mult(self, stat_allocs, substat_allocs):
        stat_elem_dmg = self.STAT_ELEM_DMG * stat_allocs["ElemDmg"]

        return 1 + stat_elem_dmg + self.modifiers["ElemDmg"]


    def compute_damage(self, stats, substats, reaction_multiplier):
        # convert stats and substats to a more readable format
        stat_allocs = {self.STATS[i]: stats[i] for i in range(len(self.STATS))}
        substat_allocs = {self.SUBSTATS[i]: substats[i] for i in range(len(self.SUBSTATS))}

        raw_dmg = self.total_att(stat_allocs, substat_allocs) * \
            self.dmg_mult(stat_allocs, substat_allocs) * \
            self.crit_mult(stat_allocs, substat_allocs) * \
            self.reaction_mult(stat_allocs, substat_allocs, reaction_multiplier)
        
        return raw_dmg * self.mitigated_dmg_mult

    
    def stats_conflicted(self, stats):
        return stats[3] and stats[4] # you cannot allocate critrate and critdmg as main artifact stats simultaneously


    def allocate_substats(self, stats, reaction_multiplier, substat_rolls, enforce_min_substat_rolls):
        substats = [substat_rolls] + [0] * (len(self.SUBSTATS) - 1)
        substats_itr = 0

        while not is_iteration_finished(substats, substat_rolls):
            if not enforce_min_substat_rolls or k_slots_at_least_d(substats, 5, 4):
                dmg = self.compute_damage(stats, substats, reaction_multiplier)
                if dmg > self.max_dmg:
                    self.max_dmg = dmg
                    self.opt_stats = copy.deepcopy(stats)
                    self.opt_substats = copy.deepcopy(substats)
            (substats, substats_itr) = iterate_integer_composition(substats, substats_itr)
            if enforce_min_substat_rolls:
                while not (k_slots_at_least_d(substats, 5, 4) or is_iteration_finished(substats, substat_rolls)):
                    (substats, substats_itr) = iterate_integer_composition(substats, substats_itr)
            
        if not enforce_min_substat_rolls or (k_slots_at_least_d(substats, 5, 4) and not is_iteration_finished(substats, substat_rolls)):
            dmg = self.compute_damage(stats, substats, reaction_multiplier)
            if dmg > self.max_dmg:
                self.max_dmg = dmg
                self.opt_stats = copy.deepcopy(stats)
                self.opt_substats = copy.deepcopy(substats)


    def allocate_stats(self, reaction_multiplier, substat_rolls=45, enforce_min_substat_rolls=True):
        self.max_dmg = 0
        self.opt_stats = []
        self.opt_substats = []

        stats = [3] + [0] * (len(self.STATS) - 1)
        stats_lims = self.STAT_UPPER_LIMITS
        stats_itr = 0

        while not is_iteration_finished(stats, 3, stats_lims):
            self.allocate_substats(stats, reaction_multiplier, substat_rolls, enforce_min_substat_rolls)

            (stats, stats_itr) = iterate_integer_composition(stats, stats_itr)
            while not is_iteration_finished(stats, 3) and (comp_over_limits(stats, stats_lims) or self.stats_conflicted(stats)):
                (stats, stats_itr) = iterate_integer_composition(stats, stats_itr)

        if not (comp_over_limits(stats, stats_lims) or self.stats_conflicted(stats)):
            self.allocate_substats(stats, reaction_multiplier, substat_rolls, enforce_min_substat_rolls)

        return (self.max_dmg, self.opt_stats, self.opt_substats)


    def print_stats(self):
        print("Using [" + self.character + "] with [" + self.weapon + "] and the following effects:")
        for name in self.effects:
            print(" - " + name)
        print("")
        print("Optimal stat allocation:")
        for i in range(len(self.STATS)):
            if self.opt_stats[i]:
                print(" - " + self.STATS[i]  + ": " + str(self.opt_stats[i]))
        print("")
        print("Optimal substat allocation:")
        for i in range(len(self.SUBSTATS)):
            if self.opt_substats[i]:
                print(" - " + self.SUBSTATS[i]  + ": " + str(self.opt_substats[i]))
        print("")


class PhysDamageModel(DefaultDamageModel):
    STAT_PHYS_DMG = 0.583

    STATS = ["AttMult", "EM", "PhysDmg", "CritRate", "CritDmg"]
    
    def dmg_mult(self, stat_allocs, substat_allocs):
        stat_phys_dmg = self.STAT_PHYS_DMG * stat_allocs["PhysDmg"]

        return 1 + stat_phys_dmg + self.modifiers["PhysDmg"]

# Note: The child classes below require much more time to solve since they add another
#       variable to the solver (hp, def, energy recharge)

# For Hu Tao
class HpAttMultDamageModel(DefaultDamageModel):
    FLOWER_HP = 4780
    SUBSTAT_HP_MULT = 0.04975
    STAT_HP_MULT = 0.466

    STATS = ["HpMult", "AttMult", "EM", "ElemDmg", "CritRate", "CritDmg"]
    STAT_UPPER_LIMITS = [3,3,3,1,1,1]

    SUBSTATS = ["HpMult", "AttMult", "EM", "CritRate", "CritDmg"]
    
    def stats_conflicted(self, stats):
        return stats[4] and stats[5] # you cannot allocate critrate and critdmg as main artifact stats simultaneously


    def max_hp(self, stat_allocs, substat_allocs):
        base_hp = self.modifiers["BaseHp"]
        stat_hp_mult = self.STAT_HP_MULT * stat_allocs["HpMult"]
        substat_hp_mult = self.SUBSTAT_HP_MULT * substat_allocs["HpMult"]

        flat_hp_bonus = self.FLOWER_HP + self.modifiers["FlatHp"]
        hp_mult = 1 + stat_hp_mult + substat_hp_mult + self.modifiers["HpMult"]
        return base_hp * hp_mult + flat_hp_bonus


    def total_att(self, stat_allocs, substat_allocs):
        hp = self.max_hp(stat_allocs, substat_allocs)
        hp_to_att_mult = self.modifiers["HpAttMult"]
        return super().total_att(stat_allocs, substat_allocs) + hp * hp_to_att_mult


# For Noelle, Xinyan
class DefAttMultDamageModel(DefaultDamageModel):
    SUBSTAT_DEF_MULT = 0.062
    STAT_DEF_MULT = 0.583

    STATS = ["DefMult", "AttMult", "EM", "ElemDmg", "CritRate", "CritDmg"]
    STAT_UPPER_LIMITS = [3,3,3,1,1,1]

    SUBSTATS = ["DefMult", "AttMult", "EM", "CritRate", "CritDmg"]
    
    def stats_conflicted(self, stats):
        return stats[4] and stats[5] # you cannot allocate critrate and critdmg as main artifact stats simultaneously


    def max_def(self, stat_allocs, substat_allocs):
        base_def = self.modifiers["BaseDef"]
        stat_def_mult = self.STAT_DEF_MULT * stat_allocs["DefMult"]
        substat_def_mult = self.SUBSTAT_DEF_MULT * substat_allocs["DefMult"]

        flat_def_bonus = self.modifiers["FlatDef"]
        def_mult = 1 + stat_def_mult + substat_def_mult + self.modifiers["DefMult"]
        return base_def * def_mult + flat_def_bonus


    def total_att(self, stat_allocs, substat_allocs):
        defense = self.max_def(stat_allocs, substat_allocs)
        def_to_att_mult = self.modifiers["DefAttMult"]
        return super().total_att(stat_allocs, substat_allocs) + defense * def_to_att_mult


# For Mona
class RechargeDmgMultDamageModel(DefaultDamageModel):
    SUBSTAT_RECHARGE_MULT = 0.055
    STAT_RECHARGE_MULT = 0.518

    STATS = ["AttMult", "EM", "ElemDmg", "EnergyRecharge", "CritRate", "CritDmg"]
    STAT_UPPER_LIMITS = [3,3,1,1,1,1]

    SUBSTATS = ["AttMult", "EM", "EnergyRecharge", "CritRate", "CritDmg"]
    
    def stats_conflicted(self, stats):
        return stats[4] and stats[5] # you cannot allocate critrate and critdmg as main artifact stats simultaneously


    def total_energy_recharge(self, stat_allocs, substat_allocs):
        stat_recharge = self.STAT_RECHARGE_MULT * stat_allocs["EnergyRecharge"]
        substat_recharge = self.SUBSTAT_RECHARGE_MULT * substat_allocs["EnergyRecharge"]
        return stat_recharge + substat_recharge + self.modifiers["EnergyRecharge"]


    def dmg_mult(self, stat_allocs, substat_allocs):
        energy_recharge = self.total_energy_recharge(stat_allocs, substat_allocs)
        recharge_att_mult = self.modifiers["RechargeDmgMult"]
        return super().dmg_mult(stat_allocs, substat_allocs) + energy_recharge * recharge_att_mult
