from artifact_optimizer import HpAttMultDamageModel, DefaultDamageModel, Character, Weapon, Effect


# Hu Tao, with a very budget setup (assuming you can also get your hands on Homa)
print("---------------------------------- Hu Tao ------------------------------")
print("")

character = Character('Hu Tao')
weapon = Weapon('Staff of Homa')
effects = [
    Effect('Paramita Papilio'),
    Effect('Sanguine Rouge'),
]

m = HpAttMultDamageModel(character, weapon, effects)
m.allocate_stats(HpAttMultDamageModel.FIRE_MELT_MULT, 20, False)

m.print_stats()
print("Damage calculation (melt + average damage, enemy is lv 90 with 10% RES):")
print(" - 100% DMG: " + str(m.max_dmg))
print(" - Charged Attack (lv10): " + str(2.4257 * m.max_dmg))
print(" - Spirit Soother (lv13): " + str(7.0597 * m.max_dmg))
print("")


# Ganyu, going for most invested build
# This assumes a team of Bennett, Klee, Mona with maximized buffs
print("---------------------------------- Ganyu ------------------------------")
print("")

character = Character('Ganyu')
weapon = Weapon('Amos Bow')
effects = [
    Effect("Stellaris Phantasm (Non Vaporize)"),
    Effect("Westward Sojourn (Max)"),
    Effect("Harmony between Heaven and Earth"),
    Effect("Undivided Heart"),
    Effect("Dew Drinker"),
    Effect("Explosive Frags"),
    Effect("Pyro Resonance"),
    Effect("Fantastic Voyage (Max)"),
    Effect("Only max 50% CrR"), # use this effect to force the solver to stay under 50% critrate
]

m2 = DefaultDamageModel(character, weapon, effects)
m2.allocate_stats(DefaultDamageModel.ICE_MELT_MULT, 45, True)

m2.print_stats()
print("Damage calculation (melt + average damage, enemy is lv 90 with 10% RES):")
print(" - 100% DMG: " + str(m2.max_dmg))
print(" - Frostflake Arrow Bloom (lv10): " + str(3.92 * m2.max_dmg))
print("")