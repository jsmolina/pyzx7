#!/usr/bin/env python
# Original @author is  Juan J Martinez.
# Modified by jsmolina

__version__ = "1.1"

import pyzx7
import json
import os
import tempfile
import textwrap
from argparse import ArgumentParser
from collections import defaultdict

DEF_ROOM_WIDTH = 20
DEF_ROOM_HEIGHT = 22
DEF_TS_SIZE = 16
DEF_BITS = 4
DEF_MAX_ENTS = 8

KEY = 0xf6


def find_name(data, name):
    for item in data:
        if item.get("name").lower() == name.lower():
            return item
    raise ValueError("%r not found" % name)


def split_multipart_text(text):
    parts = []
    for sub in text.upper().split("|"):
        parts.append('\n'.join(textwrap.wrap(sub, 30)))
    return '|'.join(parts)


def main():
    parser = ArgumentParser(description="Map importer",
                            epilog="Copyright (C) 2016 Juan J Martinez <jjm@usebox.net>",
                            )

    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    parser.add_argument("--room-width", dest="rw", default=DEF_ROOM_WIDTH, type=int,
                        help="room width (default: %s)" % DEF_ROOM_WIDTH)
    parser.add_argument("--room-height", dest="rh", default=DEF_ROOM_HEIGHT, type=int,
                        help="room height (default: %s)" % DEF_ROOM_HEIGHT)
    parser.add_argument("--base-tile", dest="base", default=0, type=int,
                        help="base tile (default: 0)")
    parser.add_argument("--ts-size", dest="tsz", default=DEF_TS_SIZE, type=int,
                        help="tileset size (default: %s)" % DEF_TS_SIZE)
    parser.add_argument("--max_ents", dest="max_ents", default=DEF_MAX_ENTS, type=int,
                        help="max entities per room (default: %s)" % DEF_MAX_ENTS)
    parser.add_argument("map_json", help="Map to import")
    parser.add_argument("id", help="variable name")

    args = parser.parse_args()

    with open(args.map_json, "rt") as fd:
        data = json.load(fd)

    mh = data.get("height", 0)
    mw = data.get("width", 0)

    if mh < args.rh or mh % args.rh:
        parser.error("Map size height not multiple of the room size")
    if mw < args.rw or mw % args.rw:
        parser.error("Map size witdh not multiple of the room size")

    tilewidth = data["tilewidth"]
    tileheight = data["tileheight"]

    TYPE_MAP = {
        "key": 16,
        "chest": 17,
        "potion": 18,
        "coin": 19,
        "oneup": 20,
        "chalice": 21,
        "door": 22,
        "slime": 23,
        "rslime": 24,
        "bat": 25,
        "elf": 26,
        "golem": 27,
        "undead": 28,
        "necro": 29,
        "soldier": 30,
        "lizardman": 31,
        "undeadw": 32,
        "swdoor": 33,
        "oracle": 34,
        "hint": 35,
        "knight": 36,
        "wizard": 37,
        "dknight": 38,
    }

    # extra tiles
    for t in range(16):
        TYPE_MAP["tile%d" % t] = t

    # tiles with text
    info = ("tile2", "tile4", "tile9",)
    map_info = dict()
    extra_info = dict()

    if "properties" in data:
        for prop, val in data["properties"].items():
            prop = prop.lower()
            if prop.endswith("_text"):
                extra_info[prop] = split_multipart_text(val)

    map_ents = defaultdict(list)

    entities_layer = find_name(data["layers"], "Entities")
    if len(entities_layer):
        objs = sorted(entities_layer["objects"], key=lambda o: TYPE_MAP[o["type"].lower()])
        for obj in objs:
            m = ((obj["x"] // tilewidth) // args.rw) \
                + (((obj["y"] // tileheight) // args.rh) * (mw // args.rw))
            x = obj["x"] % (args.rw * tilewidth)
            y = obj["y"] % (args.rh * tileheight) - 1  # entities are 16 pixels tall
            t = TYPE_MAP[obj["type"].lower()] & 127

            # door use tile coords instead, packed
            if obj["type"].lower() in ("door", "swdoor"):
                y += 1
                x //= tilewidth
                y //= tileheight

            param = int(obj.get("properties", {}).get("param", 0)) & 1

            if obj["type"].lower() in info:
                val = obj.get("properties", {}).get("text", "").upper()
                if val != "":
                    map_info[m] = split_multipart_text(val)

            map_ents[m].extend([(t << 1) | param, x, y])

    tile_layer = find_name(data["layers"], "Background")["data"]

    def_tileset = find_name(data["tilesets"], "default")
    firstgid = def_tileset.get("firstgid")

    # some tiles that can be swapped
    tile_swap = [0, 0, 47, 63, 79, 95, 111]

    tilesets = []
    out = []
    for y in range(0, mh, args.rh):
        for x in range(0, mw, args.rw):
            block = []
            ts = None
            for j in range(args.rh):
                for i in range(args.rw):
                    block.append(tile_layer[x + i + (y + j) * mw] - firstgid)

            # store the tileset
            for t in block:
                # skip tiles that will be swapped
                if t != 47:
                    ts = max((t // args.tsz) * args.tsz - args.base, 0)
                    break

            # pack
            current = []
            for i in range(0, args.rh * args.rw, 8 // DEF_BITS):
                tiles = []
                for k in range(8 // DEF_BITS):
                    tiles.append(block[i + k] - args.base)

                # perform tile swap
                for i in range(len(tiles)):
                    if tiles[i] == 47:
                        tiles[i] = tile_swap[ts // 16]

                # don't allow mixed tilesets
                for t in tiles:
                    if max((t // args.tsz) * args.tsz, 0) != ts:
                        parser.error("Mixed tilesets in room %d, tile: %d" % (len(out), t))

                # correct the tile as it was 1st tileset
                if tiles[0] > args.tsz - 1:
                    for k in range(8 // DEF_BITS):
                        tiles[k] %= args.tsz

                b = 0
                pos = 8
                for k in range(8 // DEF_BITS):
                    pos -= DEF_BITS
                    b |= (tiles[k] & ((2 ** DEF_BITS) - 1)) << pos

                current.append(b)

            tilesets.append(ts)
            out.append(current)
    # now compress
    compressed = []
    for i, block in enumerate(out):
        if all([byte == 0xff for byte in block]):
            # this map is empty, will be skipped
            compressed.append("")
            continue

        with tempfile.NamedTemporaryFile() as fd:
            fd.write(bytearray(block))
            fd.flush()

            zx7_name = fd.name + ".zx7"
            pyzx7.compress(fd.name)

        with open(zx7_name, "rb") as fd:
            output = fd.read()
        os.unlink(zx7_name)

        # size of compressed data first to be able to get to tileset and map entities
        compressed.append([len(output) + 1])
        compressed[-1].extend([ord(b) for b in output])

    out = compressed

    # append ts and any entities per map (0xff for none)
    for i in range(len(out)):
        ents = map_ents[i]
        if not out[i]:
            assert not ents, "map is empty but has entities!"
            continue
        if len(tilesets) > 1:
            out[i].append(tilesets[i])
        ent_cnt = 0
        for j in range(0, len(ents), 3):
            if (ents[j] >> 1) > 15:
                ent_cnt += 1
        if ent_cnt > args.max_ents:
            parser.error("too many entities in room %s" % i)
        ents.append(0xff)
        out[i].extend(ents)

    text_len = 0

    # append any info per map
    if map_info:
        if map_info:
            for i in range(len(out)):
                if i in map_info:
                    k = KEY
                    for c in map_info[i]:
                        k ^= ord(c)
                        out[i].append(k)
                        if c == "|":
                            k = KEY
                    # string terminator
                    out[i].append(0 ^ k)
                    text_len += len(out)

    data_out = ""
    for block in out:
        # skip empty
        if not block:
            continue
        for part in range(0, len(block), args.rw // 2):
            data_out += "\n\t.byte "
            data_out += ', '.join(["$%02x" % byte for byte in block[part: part + args.rw // 2]])

    print("%s:%s\n" % (args.id, data_out))

    # multiple maps, we need an index if they're compressed
    if len(out) > 1 and args.zx7:
        data_out = []
        length = 0
        for i in range(len(out)):
            length += 0 if i == 0 else len(out[i - 1])
            data_out.append("%s + $%02x" % (args.id, length))
        print("%s_idx:\n\t.word %s\n" % (args.id, ', '.join(data_out)))

    # if there's info, dump the dictionary
    if extra_info:
        for id, text in extra_info.items():
            out = []
            k = KEY
            for c in text:
                k ^= ord(c)
                out.append(k)
                if c == "|":
                    k = KEY
            # string terminator
            out.append(0 ^ k)
            text_len += len(out)
            print("%s:\n\t.byte %s\n" % (id, ", ".join(["$%02x" % t for t in out])))

    if text_len:
        print("; total text length %d\n" % text_len)


if __name__ == "__main__":
    main()
