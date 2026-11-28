# SPDX-License-Identifier: GPL-3.0-or-later
"""Host probes of the current UV contract, plus math controls for texture sampling."""
import hashlib
import importlib
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
import zlib

root = Path(__file__).resolve().parents[3]
package = ModuleType("texture_lab_material")
package.__path__ = [str(root)]
sys.modules[package.__name__] = package
bake = importlib.import_module("texture_lab_material.procedural_bake")
MWError = importlib.import_module("texture_lab_material.contract").WorkflowError


def make_mesh(triangles, slots):
    return NS(uv_layers={"UVMap": NS(data=[NS(uv=xy) for t in triangles for xy in t])},
              calc_loop_triangles=lambda: None,
              loop_triangles=[NS(polygon_index=i, loops=list(range(i*3, i*3+3))) for i in range(len(triangles))],
              polygons=[NS(material_index=s) for s in slots])


def uv_report():
    a = [(0, 0), (.5, 0), (0, .5)]
    b = [(.5, 0), (.5, .5), (0, .5)]
    flipped_disjoint = [(.8, 0), (.6, 0), (.8, .3)]
    rules = {
        "shared_diagonal": ([a, b], [0, 0], True),
        "disjoint_mirrored": ([a, flipped_disjoint], [0, 0], True),
        "stacked_mirrored": ([a, list(reversed(a))], [0, 0], False),
        "overlap_other_slot": ([a, a], [0, 1], True),
        "degenerate_target": ([a, [(0, 0), (.25, 0), (.5, 0)]], [0, 0], False),
        "target_outside_tile": ([a, [(1, 0), (1.1, 0), (1, .5)]], [0, 0], False),
    }
    result = {}
    for key, (triangles, slots, accept) in rules.items():
        try:
            bake._uv_check(make_mesh(triangles, slots), "UVMap", {0})
        except MWError as e:
            assert not accept
            result[key] = str(e)
        else:
            assert accept
            result[key] = "pass"
    return result


def angle(y1, y2):
    z = math.sqrt(1 - .6**2)
    return round(math.degrees(math.acos(max(-1., min(1., y1*y2+z*z)))), 3)


def tangent_control():
    # At a flat mirrored UV, test a tilted normal with a nonzero Y.
    # With this fixture T=(1,0,0), N=(0,0,1), the mirrored fSign is -1.
    y = .6
    keep_sign = angle(-y, -y)
    flip_green = angle(-y, y)
    assert keep_sign == 0 and flip_green > 70
    # Center of this warped quad lies halfway along whichever diagonal is used.
    heights = [0, 0, 1, 0]
    center_02 = (heights[0] + heights[2])/2
    center_13 = (heights[1] + heights[3])/2
    return {"same_signed_basis_deg": keep_sign, "extra_green_flip_deg": flip_green,
            "warped_quad_center_02": center_02, "warped_quad_center_13": center_13}


def padding_control():
    # One linear scalar scanline, exact aligned box averages, no GPU claim.
    def map_at(border):
        a = [0.] * 16
        a[4-border:8+border] = [1.]*(4+2*border)
        return a

    def levels(a):
        return [sum(a[i:i+4])/4 for i in range(0, len(a), 4)]

    # Sample around the outside edge 4 from mip texels straddling it.
    no_padding = sum(levels(map_at(0))[:2])/2
    with_padding = sum(levels(map_at(4))[:2])/2
    assert (no_padding, with_padding)==(.5,1.)
    return {"four_pixel_mip_then_edge_mix_no_padding": no_padding,
            "four_pixel_mip_then_edge_mix_with_padding": with_padding}


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind+data))


def file_control():
    with tempfile.TemporaryDirectory() as t:
        p, q = (Path(t) / k for k in ("original.png", "copy.png"))
        data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB",1,1,16,0,0,0,0))
        def png(value):
            return data+chunk(b"IDAT", zlib.compress(struct.pack(">BH",0,value)))+chunk(b"IEND",b"")
        p.write_bytes(png(32768))
        q.write_bytes(p.read_bytes())
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        same = digest(p)==digest(q)
        q.write_bytes(png(32769))
        changed = digest(p)!=digest(q)
        h1, h2 = bake._image_header(p), bake._image_header(q)
        assert h1 == h2 and h1["bit_depth"] == "16" and same and changed
        return {"parser": h1, "copies_match_by_sha256": same, "one_level_change_detected_by_sha256": changed}


def export_contract():
    allowed = bake._settings({"channels": ["normal", "height"], "size": 128})["channels"]
    assert allowed == ["normal", "height"]
    try:
        bake._settings({"channels": ["ao"], "size": 128})
    except MWError as e:
        return {"normal_height_accepted": True, "ao_rejected": str(e)}
    raise AssertionError("AO unexpectedly accepted by the procedural export contract")


if __name__ == "__main__":
    print(json.dumps({"uv_contract_0_9_2": uv_report(), "tangent_math": tangent_control(),
          "margin_math": padding_control(), "disk_header_and_digest": file_control(), "procedural_export": export_contract()}, indent=2))
