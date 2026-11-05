#!/usr/bin/env python3
"""Build !LibMapData/Libs/LibMapData-1.0/library.lua for a client with Project Reforged HD.

Takes upstream LibMapData-1.0 (minor 57, the copy 3.3.5 addons ship) and adds
an entry for every WorldMapArea row the client's patch-M.mpq adds (start zones,
caves, Hyjal, GMIsland, instance maps). Bounds come from WorldMapArea.dbc and
instance floors from DungeonMap.dbc, in the library's own floor format.

    STORMLIB=/usr/local/lib/libstorm.dylib python3 tools/build.py /path/to/Data/patch-M.mpq
"""
import ctypes
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM = os.path.join(ROOT, "upstream", "LibMapData-1.0.lua")
OUT = os.path.join(ROOT, "!LibMapData", "Libs", "LibMapData-1.0", "library.lua")
MINOR = 1000  # above every 3.3.5 copy (57) and the Cata-era 99, so ours wins in LibStub
CONTINENT_MAPS = {0: 2, 1: 1, 530: 3, 571: 4}  # map id -> GetMapContinents() index
# WoW Forever's Riverglades, from its UiMapAssignment, for clients whose patch adds it.
EXTRA_ZONES = [(1100, "Riverlands", 0, -1891.666015625, -6741.666015625, -6466.666015625, -9700.0)]
# The same patch can bring Forever's Redridge: (left, right, top, bottom). The continent keeps the client's frame: the
# patch draws the new coast into the client's own map, so Quel'Danas and Eversong stay on it.
FOREVER_REDRIDGE = (36, -1681.25, -3852.083984375, -8575.0, -10022.916015625)
# Forever's Render's Camp overlay is four files and the client's two, so the third says which map a client has.
REDRIDGE_PROBE = r"Interface\\WorldMap\\Redridge\\RENDERSCAMP3"  # as Lua source

H = ctypes.c_void_p


def read_mpq(mpq, name):
    lib = ctypes.CDLL(os.environ.get("STORMLIB", "/usr/local/lib/libstorm.dylib"))
    lib.SFileOpenArchive.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(H)]
    lib.SFileOpenFileEx.argtypes = [H, ctypes.c_char_p, ctypes.c_uint, ctypes.POINTER(H)]
    lib.SFileGetFileSize.argtypes = [H, ctypes.POINTER(ctypes.c_uint)]
    lib.SFileGetFileSize.restype = ctypes.c_uint
    lib.SFileReadFile.argtypes = [H, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.c_void_p]
    lib.SFileCloseArchive.argtypes = [H]
    lib.SFileCloseFile.argtypes = [H]
    h, f = H(), H()
    if not lib.SFileOpenArchive(mpq.encode(), 0, 0x100, ctypes.byref(h)):
        sys.exit(f"cannot open {mpq}")
    if not lib.SFileOpenFileEx(h, name.encode(), 0, ctypes.byref(f)):
        sys.exit(f"{name} not in {mpq}")
    size = lib.SFileGetFileSize(f, None)
    buf, got = ctypes.create_string_buffer(size), ctypes.c_uint()
    lib.SFileReadFile(f, buf, size, ctypes.byref(got), None)
    lib.SFileCloseFile(f)
    lib.SFileCloseArchive(h)
    return buf.raw[:got.value]


def dbc_rows(data, fmt):
    _, count, _, size, _ = struct.unpack("<4s4I", data[:20])
    assert struct.calcsize("<" + fmt) == size, (fmt, size)
    rows = [struct.unpack("<" + fmt, data[20 + i * size:20 + (i + 1) * size]) for i in range(count)]
    return rows, data[20 + count * size:]


def num(v):
    return repr(float(v))


def floor_from_bounds(left, right, top, bottom):
    # WorldMapArea bounds -> {width, height, ulX, ulY, lrX, lrY}
    return [left - right, top - bottom, -left, top, -right, bottom]


def floor_from_dungeon(min_x, max_x, min_y, max_y):
    return [max_x - min_x, max_y - min_y, -min_x, min_y, -max_x, max_y]


def main():
    mpq = sys.argv[1]
    wma, strings = dbc_rows(read_mpq(mpq, "DBFilesClient\\WorldMapArea.dbc"), "4I4f3i")
    dmap, _ = dbc_rows(read_mpq(mpq, "DBFilesClient\\DungeonMap.dbc"), "3I4fI")
    src = open(UPSTREAM).read()

    wotlk_start = src.index("\n\telse\n")
    wotlk = src[wotlk_start:src.index("\t-- Create Reverse map")]
    cata = src[:wotlk_start]
    entry = r"mapData\[(\d+)\] = \{\s*\['floors'\] = (\d+), \['name'\] = \"(\w+)\".*?\['map_type'\] = (\d)"
    known = {name for _, _, name, _ in re.findall(entry, wotlk, re.S)}
    cata_type = {name: int(t) for _, _, name, t in re.findall(entry, cata, re.S)}

    floors_by_map = {}
    for _, map_id, level, min_x, max_x, min_y, max_y, _ in dmap:
        floors_by_map.setdefault(map_id, []).append((level, floor_from_dungeon(min_x, max_x, min_y, max_y)))

    lines = []
    for wid, map_id, area, name_ofs, left, right, top, bottom, vmap, _, _ in sorted(wma):
        name = strings[name_ofs:strings.index(b"\0", name_ofs)].decode()
        if area == 0 or name in known:
            continue
        if map_id in CONTINENT_MAPS:
            shown_on = vmap if vmap in (0, 1) else map_id
            continent, map_type = CONTINENT_MAPS[shown_on], 0
            transform = 1 if map_id == 530 and vmap in (0, 1) else 0
            floors = [floor_from_bounds(left, right, top, bottom)]
        else:
            continent, map_type, transform = 0, cata_type.get(name, 1), 0
            levels = [f for _, f in sorted(floors_by_map.get(map_id, []))]
            floors = levels if levels else [floor_from_bounds(left, right, top, bottom)]
        count = len(floors) if len(floors) > 1 else 0
        lines.append(f"\t\tmapData[{wid}] = {{")
        lines.append(f"\t\t\t['floors'] = {count}, ['name'] = \"{name}\", ['rzti'] = {map_id}, ['map_type'] = {map_type}, "
                     f"['continent'] = {continent}, ['link'] = 0, ['transform'] = {transform},")
        for i, f in enumerate(floors, 1):
            lines.append(f"\t\t\t[{i}] = {{{','.join(num(v) for v in f)}}},")
        lines.append("\t\t}")

    # Zones a client patch adds beyond patch-M: (WorldMapArea id, map file, map id, left, right, top, bottom).
    for wid, name, map_id, left, right, top, bottom in EXTRA_ZONES:
        lines.append(f"\t\tmapData[{wid}] = {{")
        lines.append(f"\t\t\t['floors'] = 0, ['name'] = \"{name}\", ['rzti'] = {map_id}, ['map_type'] = 0, "
                     f"['continent'] = {CONTINENT_MAPS[map_id]}, ['link'] = 0, ['transform'] = 0,")
        lines.append(f"\t\t\t[1] = {{{','.join(num(v) for v in floor_from_bounds(left, right, top, bottom))}}},")
        lines.append("\t\t}")

    def row(wid, left, right, top, bottom):
        return f"mapData[{wid}][1] = {{{','.join(num(v) for v in floor_from_bounds(left, right, top, bottom))}}}"

    lines.append(f"\t\tif CreateFrame(\"Frame\"):CreateTexture():SetTexture(\"{REDRIDGE_PROBE}\") then")
    lines.append("\t\t\t" + row(*FOREVER_REDRIDGE))
    lines.append("\t\tend")

    added = (len(lines) and sum(1 for l in lines if l.startswith("\t\tmapData[")))
    block = ("\t-- Project Reforged HD: maps its patch-M.mpq adds to WorldMapArea.dbc (start zones, caves, instances).\n"
             "\t-- Generated by tools/build.py from WorldMapArea.dbc + DungeonMap.dbc; do not edit by hand.\n"
             "\tif not CataMapsChanged then\n" + "\n".join(lines) + "\n\tend\n")
    src = src.replace("\t-- Create Reverse map", block + "\t-- Create Reverse map", 1)

    src = src.replace('tonumber("57") or 999', f'tonumber("{MINOR}") or 999', 1)
    # SetMapByID/GetCurrentMapZone are guarded so a client without them still loads the data.
    src = src.replace("\tSetMapByID(673)\n\tif GetCurrentMapAreaID() == 673 then",
                      "\tif SetMapByID then SetMapByID(673) end\n\tif GetCurrentMapAreaID() == 673 then", 1)
    old = "\t\tSetMapByID(k)\n\t\tlocal _,l,t,r,b = GetCurrentMapZone()\n"
    assert old in src
    src = src.replace(old, "\t\tlocal _,l,t,r,b\n\t\tif SetMapByID and GetCurrentMapZone then\n"
                           "\t\t\tSetMapByID(k)\n\t\t\t_,l,t,r,b = GetCurrentMapZone()\n\t\tend\n", 1)
    # GetContinentFromMap: in the Cata-era copy (minor 99) some addons call it; keep the API a superset.
    anchor = "--- API to list zones by continent"
    assert anchor in src and "GetContinentFromMap" not in src
    src = src.replace(anchor, "--- API to get the continent of a map\n-- @param mapfile or area id\n"
                              "-- @return continent index\nfunction lib:GetContinentFromMap(mapfile)\n"
                              "\tif type(mapfile) == \"string\" then\n\t\tmapfile = idToMap[mapfile]\n\tend\n"
                              "\tif mapfile == WORLDMAP_COSMIC_ID then return -1 end\n"
                              "\treturn mapData[mapfile].continent\nend\n\n" + anchor, 1)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(src)
    print(f"{OUT}: {added} maps added, minor {MINOR}")


if __name__ == "__main__":
    main()
