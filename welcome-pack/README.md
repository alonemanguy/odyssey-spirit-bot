# Welcome pack

A datapack, not a plugin, so Aternos will take it. It runs **once per player** on
their first tick in the world: a title, a starter kit, and three lines naming the
spawn, the address and the two evenings.

## Install

1. Zip the contents of this folder so that `pack.mcmeta` sits at the top level of
   the zip (not inside a `welcome-pack/` folder).
2. Panel → **Files** → `world/datapacks/` → Upload the zip.
3. Restart. `datapack list` in the console should show
   `file/odyssey-welcome.zip` as enabled.

`pack_format` 107 plus `min_format`/`max_format` `[107, 1]` is what Minecraft
26.2 wants - the version this server actually runs (PaperMC 26.2). The first
build shipped 81, which is 1.21.7-1.21.8, and the server would have refused it.
If a future Minecraft version refuses the pack, bump those numbers - nothing
else in here is version-specific.

## Why an advancement instead of a load tag

A `#minecraft:load` function did not run on this server, and a tick-tag
scoreboard check needs an objective that has to be created exactly once - a
failing `scoreboard objectives add` inside a function silently aborts the rest
of that function. `minecraft:tick` as an advancement criterion is granted to
each player once and then never again, so there is nothing to clean up and no
state to get wrong.

## Removing it

`datapack disable "file/odyssey-welcome.zip"` in the console. Players who
already arrived keep their kit; the advancement is already granted, so nobody
gets a second one, and re-enabling it will not re-give anything.
