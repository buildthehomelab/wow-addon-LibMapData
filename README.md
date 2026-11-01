# LibMapData-1.0 for clients with Project Reforged HD's extra zone maps

LibMapData-1.0 for the WoW 3.3.5a client, with map data for the extra maps that Project Reforged HD adds.

Many 3.3.5a addons bundle LibMapData-1.0 (Grid2, GatherMate2, Routes, TomTom and others) to know how big each map is in yards.

## Why this copy

Project Reforged HD's patch-M adds 104 maps to `WorldMapArea.dbc`. 53 of them show up on Kalimdor and the Eastern Kingdoms: starting areas such as Northshire Valley and Ammen Vale, caves such as Fargodeep Mine and Fel Rock, plus Hyjal and GM Island. The rest are instance maps.

The stock library (minor version 57) doesn't know them, so on a client with those maps:

- every login prints two "LibMapData-1.0 is missing data for ..." lines in chat per map, about a hundred lines in all, and
- addons using it treat those maps as 0 by 0 yards.

This copy adds an entry for each of the 104 maps:

- zones and caves: bounds from `WorldMapArea.dbc`
- instance maps: floors from `DungeonMap.dbc` (the same numbers as the library's own Cataclysm data)

It is registered as minor version 1000 and the folder name starts with `!`, so it loads before other addons and LibStub gives every addon this copy. The older copies they bundle never run.

It also checks that `SetMapByID` and `GetCurrentMapZone` exist before calling them, and adds `GetContinentFromMap` from the later minor-99 copy, so its API covers both.

## Install

Copy the `!LibMapData` folder into `Interface\AddOns`. Nothing to configure. You can keep the addons that bundle the old copy as they are.

## Rebuild

`upstream/LibMapData-1.0.lua` is the unmodified minor-57 library. `tools/build.py` writes `!LibMapData/Libs/LibMapData-1.0/library.lua` from it and the client's patch-M. It needs StormLib (`brew install stormlib`):

    python3 tools/build.py /path/to/Data/patch-M.mpq

## Credits and license

LibMapData-1.0 is by moonfann ([WowAce](https://www.wowace.com/projects/libmapdata-1-0), [CurseForge](https://www.curseforge.com/wow/addons/libmapdata-1-0)). It is no longer maintained and is listed as "All Rights Reserved". This repo ships it the way addons embed it, with the map data added; the rights to the library stay with its author. The upstream file is taken from the copy in [bkader/Grid2-WoTLK](https://github.com/bkader/Grid2-WoTLK).

LibStub and CallbackHandler-1.0 are public domain / BSD as published by their WowAce authors.
