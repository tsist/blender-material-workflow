# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the known 0.9.2 mask baseline with host node arithmetic, not Blender."""
from html import escape
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS

root = Path(__file__).resolve().parents[3]
pkg = ModuleType("lab_material")
pkg.__path__ = [str(root)]
sys.modules[pkg.__name__] = pkg
contract = importlib.import_module("lab_material.procedural_contract")
core = importlib.import_module("lab_material.procedural_core")
examples = importlib.import_module("lab_material.procedural_examples")
sys.modules["bpy"] = ModuleType("bpy")


class MathNodes:
    def __init__(self, manifest):
        self.spec = contract.normalize_manifest(manifest)
        self.signals, self.result = {}, {}
        self.tree = NS(interface=NS(new_socket=lambda **k: NS(name=k["name"])))
        self.links = NS(new=self.connect)
        self.output = NS(inputs={k: k for k in core.CHANNEL_SOCKETS})

    def connect(self, value, key):
        self.result[key] = value

    def new(self, *_):
        return NS()

    def control(self, key, path):
        v = self.spec
        for k in path:
            v = v[k]
        return v

    def build_signal(self, signal, index):
        self.signals[signal["id"]] = signal["parameters"]["value"]

    def mix(self, t, a, b, color, *_):
        if color:
            return [self.mix(t, x, y, False) for x, y in zip(a, b)]
        return (1 - t) * a + t * b

    def math(self, op, a, b, *_):
        assert op == "MULTIPLY"
        return a * b


def run():
    recipe = examples.make_recipe("painted_metal", dict(scene="Scene", view_layer="ViewLayer", frame=1),
                                  dict(object="Proxy", uv_layer="UVMap", material_slot=0), "WikiProbe")
    signals = {s["id"]: s for s in recipe["signals"]}
    same = all(signals["coating_loss"][k] == signals["oxide_coverage"][k]
               for k in ("type", "inputs", "parameters"))
    rows = []
    for w in (0, .5, 1):
        recipe["signals"] = [{"id": "grip", "type": "constant", "parameters": {"value": w}, "inputs": {}}]
        recipe["layers"] = [
            {"id": "steel", "name": "Steel", "values": {"base_color": [.26, .28, .30, 1], "roughness": .34, "metallic": 1}},
            {"id": "polish", "name": "Grip polish", "mask": "grip", "values": {"roughness": .15}},
        ]
        tracer = MathNodes(recipe)
        core.Builder.build(tracer)
        rows.append({"weight": w, "roughness": round(tracer.result["roughness"], 6),
                     "metallic": tracer.result["metallic"], "rgb": [round(x, 6) for x in tracer.result["base_color"][:3]]})
    assert [x["roughness"] for x in rows] == [.34, .245, .15]
    assert [x["metallic"] for x in rows] == [1, .5, 0] and same
    marks = {0: 1, 8: 1, 7: 0, 15: 0}
    old = [int(i % 8 >= 2) for i in range(64)]
    new = [int(i % 8 >= 4) for i in range(64)]
    compose = lambda values: [marks.get(i, v) for i, v in enumerate(values)]
    before, after = compose(old), compose(new)
    changed = sum(a != b for a, b in zip(before, after))
    retained = sum(after[i] == v for i, v in marks.items())
    overwritten = sum(new[i] != v for i, v in marks.items())
    assert (changed, retained, overwritten) == (16, 4, 4)
    return {"route": rows, "chip_and_rust_same": same, "mask_calibration": {
        "untouched_pixels_changed": changed, "paint_marks_retained": retained, "marks_lost_when_overwritten": overwritten},
        "gray_127_srgb": round(((127/255+.055)/1.055)**2.4, 6), "gray_127_linear": round(127/255, 6)}


if __name__ == "__main__":
    value = json.dumps(run(), indent=2)
    print(value)
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text("<!doctype html><meta charset=utf-8>"
            "<style>body{background:#101c2e;color:#e9f4ff;margin:28px;font:18px monospace}"
            "h1{font-size:22px;color:#7de5db}pre{line-height:1.25}p{color:#b1c5e0}</style>"
            "<h1>Material Workflow 0.9.2 | Linux host baseline</h1>"
            "<p>Real Builder routing / simulated sockets. Not a Blender render.</p><pre>"
            + escape(value) + "</pre>", encoding="utf-8")
