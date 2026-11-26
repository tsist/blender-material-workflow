# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the actual graph builder against recording sockets, without Blender."""
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch

pkg = ModuleType("material_layer_test")
pkg.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules[pkg.__name__] = pkg
contract, core, examples = (
    importlib.import_module(pkg.__name__ + "." + name)
    for name in ("procedural_contract", "procedural_core", "procedural_examples")
)


def recipe(weight=1):
    result = examples.make_recipe("painted_metal",
        dict(scene="Scene", view_layer="ViewLayer", frame=1),
        dict(object="Toolbox", uv_layer="UVMap", material_slot=0), "Toolbox")
    result["signals"] = [{"id": "Grip", "type": "constant", "parameters": {"value": weight}, "inputs": {}}]
    result["layers"] = [
        {"id": "Steel", "name": "Bare steel", "values": {
            "base_color": [.26, .28, .30, 1], "roughness": .34, "metallic": 1, "height": .2}},
        {"id": "GripPolish", "name": "Grip polish", "mask": "Grip", "values": {"roughness": .15}},
    ]
    return result


class Trace:
    def __init__(self, manifest):
        self.spec = contract.normalize_manifest(manifest)
        self.signals, self.result, self.controls = {}, {}, set()
        self.tree = NS(interface=NS(new_socket=lambda **kw: NS(name=kw["name"])))
        self.links = NS(new=lambda value, key: self.result.__setitem__(key, value))
        self.output = NS(inputs={name: name for name in core.CHANNEL_SOCKETS})

    def new(self, *_):
        return NS()

    def build_signal(self, signal, _):
        self.signals[signal["id"]] = signal["parameters"]["value"]

    def control(self, name, path):
        self.controls.add(name)
        return core._get_path(self.spec, path)

    def math(self, op, a, b, *args):
        if op != "MULTIPLY":
            raise AssertionError(op)
        return a * b

    def mix(self, t, a, b, color, *args):
        if color:
            return [self.mix(t, x, y, False) for x, y in zip(a, b)]
        return (1 - t) * a + t * b


def build(doc):
    tracer = Trace(doc)
    with patch.dict(sys.modules, {"bpy": ModuleType("bpy")}):
        core.Builder.build(tracer)
    return tracer


class LayerChannels(unittest.TestCase):
    def test_grip_weights_preserve_every_other_channel(self):
        base = recipe()
        base["layers"].pop()
        reference = build(base).result
        for weight, expected in [(0, .34), (.5, .245), (1, .15)]:
            with self.subTest(weight=weight):
                doc = recipe(weight)
                doc["layers"][1]["affects"] = ["roughness"]
                got = build(doc)
                self.assertAlmostEqual(got.result["roughness"], expected, places=6)
                self.assertEqual({k: v for k, v in got.result.items() if k != "roughness"},
                                 {k: v for k, v in reference.items() if k != "roughness"})
                self.assertEqual({k for k in got.controls if k.startswith("L/GripPolish/")},
                                 {"L/GripPolish/roughness", "L/GripPolish/opacity"})

    def test_explicit_zero_and_signal_binding(self):
        doc = recipe(.5)
        layer = doc["layers"][1]
        layer.update(affects=["roughness", "metallic"], values={"metallic": 0},
                     channels={"roughness": "Grip"})
        got = build(doc)
        self.assertAlmostEqual(got.result["roughness"], .42, places=6)
        self.assertEqual(got.result["metallic"], .5)
        self.assertNotIn("L/GripPolish/roughness", got.controls)

    def test_disjoint_overlays_and_disabled_layer_do_not_leak(self):
        doc = recipe(1)
        doc["layers"][1]["affects"] = ["roughness"]
        doc["layers"].extend([
            {"id": "Coat", "name": "Coat", "affects": ["coat_weight"], "values": {"coat_weight": .75}},
            {"id": "Disabled", "name": "Disabled", "enabled": False,
             "affects": ["roughness"], "values": {"roughness": .99}},
        ])
        got = build(doc)
        self.assertAlmostEqual(got.result["roughness"], .15, places=6)
        self.assertEqual(got.result["metallic"], 1)
        self.assertEqual(got.result["coat_weight"], .75)
        self.assertFalse(any(k.startswith("L/Disabled/") for k in got.controls))

    def test_legacy_route_and_normalized_payload_preserved(self):
        doc = recipe(.5)
        normalized = contract.normalize_manifest(doc)
        self.assertEqual(contract.normalize_manifest(normalized), normalized)
        self.assertNotIn("affects", normalized["layers"][1])
        got = build(doc)
        self.assertAlmostEqual(got.result["roughness"], .245, places=6)
        self.assertEqual(got.result["metallic"], .5)
        self.assertIn("L/GripPolish/base_color", got.controls)

    def test_invalid_selectors_and_canonical_order(self):
        cases = [(1, []), (1, ["roughness", "roughness"]), (1, ["normal"]), (0, ["roughness"])]
        for index, affects in cases:
            doc = recipe()
            doc["layers"][index]["affects"] = affects
            with self.subTest(index=index, affects=affects), self.assertRaises(contract.WorkflowError):
                contract.normalize_manifest(doc)
        doc = recipe()
        doc["layers"][1].update(affects=["roughness"], channels={"metallic": "Grip"})
        with self.assertRaisesRegex(contract.WorkflowError, "signal bindings outside affects"):
            contract.normalize_manifest(doc)
        doc["layers"][1]["affects"] = ["metallic", "roughness"]
        normalized = contract.normalize_manifest(doc)
        self.assertEqual(normalized["layers"][1]["affects"], ["roughness", "metallic"])
        self.assertEqual(contract.normalize_manifest(normalized), normalized)

    def test_preserves_live_roughness_edit_but_rejects_removing_it(self):
        baseline = contract.normalize_manifest(recipe())
        live = deepcopy(baseline)
        live["layers"][1]["values"]["roughness"] = .18
        controls = {"L/GripPolish/roughness": ["layers", 1, "values", "roughness"]}
        incoming = deepcopy(baseline)
        incoming["layers"][1]["affects"] = ["roughness"]
        merged = core._merge_live_controls(incoming, baseline, live, controls)
        self.assertAlmostEqual(merged["layers"][1]["values"]["roughness"], .18)
        incoming["layers"][1]["channels"]["roughness"] = "Grip"
        with self.assertRaisesRegex(contract.WorkflowError, "Removing edited layer channel"):
            core._merge_live_controls(incoming, baseline, live, controls)
        incoming["layers"][1].update(affects=["metallic"], channels={})
        with self.assertRaisesRegex(contract.WorkflowError, "Removing edited layer channel"):
            core._merge_live_controls(incoming, baseline, live, controls)
