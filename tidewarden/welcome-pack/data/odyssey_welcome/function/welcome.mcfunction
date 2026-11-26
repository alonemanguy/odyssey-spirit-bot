# Runs once for each player, on their first tick. Triggered by the first_join
# advancement, not a #minecraft:load tag - load did not fire on this server,
# and an advancement needs no scoreboard and cannot repeat.
title @s times 10 80 20
title @s subtitle {"text":"the landing - x 566, z -470","color":"gray"}
title @s title {"text":"ODYSSEY LANDS","color":"gold","bold":true}

give @s minecraft:bread 16
give @s minecraft:torch 16
give @s minecraft:stone_pickaxe
give @s minecraft:stone_axe
give @s minecraft:stone_sword
give @s minecraft:oak_planks 32
give @s minecraft:white_bed

tellraw @s [{"text":"You're at the Landing. ","color":"gold"},{"text":"The quay is on the water side, the harbour town is east along the road. Everything already built is somebody's - don't take it apart.","color":"gray"}]
tellraw @s [{"text":"Java ","color":"gray"},{"text":"odysseyland.aternos.me","color":"aqua"},{"text":"  -  Bedrock: same address, port ","color":"gray"},{"text":"19132","color":"aqua"},{"text":"  -  everyone is in #general, say hi there.","color":"gray"}]
tellraw @s [{"text":"Two evenings a week, 8pm UTC+3: wednesday session, sunday build night. Say hi in #general - that's where everyone actually is.","color":"gray"}]

playsound minecraft:entity.player.levelup master @s ~ ~ ~ 0.6 1.2
