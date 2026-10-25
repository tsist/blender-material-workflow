# SPDX-License-Identifier: GPL-3.0-or-later
import sys
sys.dont_write_bytecode = True
"""Contract tests for procedural_contract.py.

Run with:
    python tests/procedural_contract.py --output ABSOLUTE_NEW_DIRECTORY
"""

from copy import deepcopy
import json
import math
import struct
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from procedural_test_support import bootstrap, prepare_output
ROOT = bootstrap()
OUT = prepare_output('contract', require_blender=False)
from material_workflow_addon import contract as legacy_contract

# Snapshot before importing the new module so the regression test detects any
# accidental mutation of the legacy schema at import time.
LEGACY_SCHEMA_SNAPSHOT = deepcopy(legacy_contract.MANIFEST_SCHEMA)
LEGACY_PREVIEW_SNAPSHOT = deepcopy(legacy_contract.PREVIEW)

from material_workflow_addon import procedural_contract as pc


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64


def absolute(*parts):
    return str((Path.cwd() / Path(*parts)).resolve())


def rgba(red=0.5, green=0.5, blue=0.5, alpha=1.0):
    return [red, green, blue, alpha]


def f32(value):
    """Independent expected RNA precision, retaining every exact assertion."""
    if isinstance(value, list):
        return [f32(v) for v in value]
    if isinstance(value, dict):
        return {key: f32(v) for key, v in value.items()}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return struct.unpack('f', struct.pack('f', value))[0]
    return value


def signal(signal_id, signal_type, parameters=None, inputs=None):
    return {
        "id": signal_id,
        "type": signal_type,
        "parameters": {} if parameters is None else parameters,
        "inputs": {} if inputs is None else inputs,
    }


def image_document(color_space, path=None, digest=HASH_A):
    return {
        "file": absolute("textures", "base.png") if path is None else path,
        "expected_sha256": digest,
        "color_space": color_space,
    }


def image_signal(signal_id, output, color_space, path=None, digest=HASH_A):
    params = {"image": image_document(color_space, path, digest)}
    if output is not None:
        params["output"] = output
    return signal(signal_id, "image", params)


class ContractTestCase(unittest.TestCase):
    def make_manifest(self, signals=None, layers=None, **overrides):
        if signals is None:
            signals = [signal("base_noise", "noise")]
        if layers is None:
            layers = [{"id": "base", "name": "Base"}]
        manifest = {
            "schema_version": "2.0",
            "context": {"scene": "Scene", "view_layer": "ViewLayer"},
            "target": {"object": "Crate", "uv_layer": "UVMap"},
            "material": {"id": "mat_test", "name": "Test Material"},
            "signals": signals,
            "layers": layers,
            "preview": {
                "device": {"backend": "CPU"},
                "views": [{"id": "front"}],
            },
        }
        manifest.update(deepcopy(overrides))
        return manifest

    def assert_invalid(self, value, fragment=None):
        with self.assertRaises(pc.WorkflowError) as caught:
            pc.normalize_manifest(value)
        self.assertEqual(caught.exception.code, "INVALID_REQUEST")
        if fragment is not None:
            self.assertIn(fragment, str(caught.exception))
        return caught.exception

    def assert_signal_invalid(self, bad_signal, extra_signals=(), fragment=None):
        manifest = self.make_manifest(signals=[bad_signal, *extra_signals])
        return self.assert_invalid(manifest, fragment)

    def test_schema_is_inherited_and_legacy_schema_is_not_mutated(self):
        self.assertEqual(legacy_contract.MANIFEST_SCHEMA, LEGACY_SCHEMA_SNAPSHOT)
        self.assertEqual(legacy_contract.PREVIEW, LEGACY_PREVIEW_SNAPSHOT)
        legacy_context = legacy_contract.MANIFEST_SCHEMA["properties"]["context"]
        legacy_target = legacy_contract.MANIFEST_SCHEMA["properties"]["target"]
        legacy_preview = legacy_contract.MANIFEST_SCHEMA["properties"]["preview"]

        self.assertEqual(pc.CONTEXT_SCHEMA, legacy_context)
        self.assertEqual(pc.TARGET_SCHEMA, legacy_target)
        self.assertEqual(pc.PREVIEW_SCHEMA, legacy_preview)
        self.assertIsNot(pc.CONTEXT_SCHEMA, legacy_context)
        self.assertIsNot(pc.TARGET_SCHEMA, legacy_target)
        self.assertIsNot(pc.PREVIEW_SCHEMA, legacy_preview)
        self.assertEqual(pc.PREVIEW, legacy_contract.PREVIEW)
        self.assertIsNot(pc.PREVIEW, legacy_contract.PREVIEW)

        self.assertEqual(
            legacy_contract.MANIFEST_SCHEMA["properties"]["schema_version"],
            {"enum": ["1.0", "1.1"]},
        )
        self.assertEqual(
            pc.MANIFEST_SCHEMA["properties"]["schema_version"], {"const": "2.0"}
        )
        self.assertNotIn("export", pc.MANIFEST_SCHEMA["properties"])
        self.assertEqual(
            pc.MANIFEST_SCHEMA["properties"]["material"]["properties"]["template"],
            {"const": "procedural_pbr_v1", "default": "procedural_pbr_v1"},
        )
        self.assertEqual(
            pc.CYCLES_GEOMETRIC_SIGNAL_TYPES, frozenset({"edge", "cavity"})
        )
        json.dumps(pc.MANIFEST_SCHEMA, allow_nan=False)
        json.dumps(pc.EXPORT_SCHEMA, allow_nan=False)
        self.assertNotIn("bpy", sys.modules)

    def test_valid_manifest_normalizes_defaults_order_and_images(self):
        source = self.make_manifest(
            signals=[
                signal(
                    "tint",
                    "mix",
                    {},
                    {
                        "b": "tint_color",
                        "factor": "grain",
                        "a": "albedo",
                    },
                ),
                signal(
                    "metal_variation",
                    "math",
                    {"operation": "MULTIPLY"},
                    {"b": "half", "a": "grain"},
                ),
                signal(
                    "grain",
                    "noise",
                    {
                        "scale": 3,
                        "coordinate": {
                            "space": "UV",
                            "rotation": [0, 0, 30],
                        },
                    },
                ),
                image_signal(
                    "albedo",
                    "COLOR",
                    "sRGB",
                    path=absolute("textures", "albedo.png"),
                ),
                image_signal(
                    "data_map",
                    "VALUE",
                    "Non-Color",
                    path=absolute("textures", "roughness.png"),
                    digest=HASH_B,
                ),
                signal(
                    "tint_color",
                    "constant",
                    {"value": rgba(0.3, 0.2, 0.1, 1)},
                ),
                signal("half", "constant", {"value": 0.5}),
            ],
            layers=[
                {
                    "id": "base",
                    "name": "Base",
                    "channels": {
                        "base_color": "tint",
                        "roughness": "data_map",
                    },
                },
                {
                    "id": "overlay",
                    "name": "Overlay",
                    "enabled": False,
                    "opacity": 0.4,
                    "mask": "grain",
                    "channels": {"metallic": "metal_variation"},
                    "values": {"roughness": 0.65},
                },
            ],
        )
        snapshot = deepcopy(source)
        result = pc.normalize_manifest(source)

        self.assertEqual(source, snapshot)
        self.assertEqual(result["schema_version"], "2.0")
        self.assertEqual(result["material"]["template"], "procedural_pbr_v1")
        self.assertEqual(result["height_distance"], f32(0.001))
        self.assertEqual(result["mesh_map_size"], 512)
        self.assertEqual(result["preview"]["engine"], "CYCLES")
        self.assertTrue(result["preview"]["denoise"])
        self.assertEqual(result["preview"]["width"], 384)
        self.assertEqual(result["preview"]["views"][0]["azimuth"], 45)
        self.assertEqual(result["preview"]["views"][0]["lighting"], "soft")

        self.assertEqual(
            [item["id"] for item in result["signals"]],
            [
                "tint",
                "metal_variation",
                "grain",
                "albedo",
                "data_map",
                "tint_color",
                "half",
            ],
        )
        by_id = {item["id"]: item for item in result["signals"]}
        self.assertEqual(
            list(by_id["tint"]["inputs"]), ["b", "factor", "a"]
        )
        self.assertEqual(
            list(by_id["metal_variation"]["inputs"]), ["b", "a"]
        )
        self.assertEqual(
            by_id["grain"]["parameters"]["coordinate"],
            {
                "space": "UV",
                "scale": [1, 1, 1],
                "rotation": [0, 0, 30],
                "translation": [0, 0, 0],
            },
        )
        self.assertEqual(by_id["grain"]["parameters"]["detail"], 2)
        self.assertEqual(by_id["albedo"]["parameters"]["output"], "COLOR")
        self.assertEqual(
            by_id["albedo"]["parameters"]["image"]["file"],
            absolute("textures", "albedo.png"),
        )
        self.assertEqual(by_id["data_map"]["parameters"]["output"], "VALUE")
        self.assertEqual(by_id["tint"]["parameters"], {})

        base = result["layers"][0]
        self.assertEqual(
            set(base["values"]), set(pc.MATERIAL_CHANNELS)
        )
        self.assertEqual(base["values"]["base_color"], [0.5, 0.5, 0.5, 1])
        self.assertEqual(base["values"]["ior"], 1.5)
        self.assertEqual(base["values"]["coat_roughness"], f32(0.03))
        self.assertEqual(result["layers"][1]["values"]["roughness"], f32(0.65))
        self.assertEqual(result["layers"][1]["channels"]["metallic"], "metal_variation")
        self.assertEqual(result["layers"][1]["mask"], "grain")

        self.assertEqual(pc.signal_types(result)["tint"], "COLOR")
        self.assertEqual(pc.signal_types(result)["metal_variation"], "VALUE")
        self.assertEqual(
            list(pc.signal_types(result)),
            [item["id"] for item in result["signals"]],
        )
        order = pc.signal_order(result)
        positions = {signal_id: index for index, signal_id in enumerate(order)}
        for item in result["signals"]:
            for dependency in item["inputs"].values():
                self.assertLess(positions[dependency], positions[item["id"]])
        self.assertEqual(
            [doc["file"] for doc in pc.image_documents(result)],
            [
                absolute("textures", "albedo.png"),
                absolute("textures", "roughness.png"),
            ],
        )

    def test_all_registered_types_and_defaults(self):
        color = rgba(0.2, 0.4, 0.6, 1)
        stops = [
            {"position": 0.0, "color": rgba(0, 0, 0, 1)},
            {"position": 1.0, "color": rgba(1, 1, 1, 1)},
        ]
        manifest = self.make_manifest(
            signals=[
                signal("c_value", "constant", {"value": 0.25}),
                signal("c_color", "constant", {"value": color}),
                image_signal(
                    "img_color",
                    None,
                    "sRGB",
                    path=absolute("textures", "color.png"),
                ),
                image_signal(
                    "img_value",
                    "VALUE",
                    "Non-Color",
                    path=absolute("textures", "value.png"),
                    digest=HASH_B,
                ),
                signal("noise", "noise"),
                signal("wood", "wood"),
                signal("edge", "edge"),
                signal("cavity", "cavity"),
                signal("band", "height_band"),
                signal("facing", "normal_direction"),
                signal(
                    "math",
                    "math",
                    {"operation": "ADD"},
                    {"a": "c_value", "b": "noise"},
                ),
                signal(
                    "ramp",
                    "ramp",
                    {"stops": stops},
                    {"value": "noise"},
                ),
                signal(
                    "mix_value",
                    "mix",
                    {},
                    {"factor": "noise", "a": "c_value", "b": "math"},
                ),
                signal(
                    "mix_color",
                    "mix",
                    {},
                    {"factor": "noise", "a": "c_color", "b": "img_color"},
                ),
            ],
            layers=[
                {
                    "id": "base",
                    "name": "Base",
                    "channels": {
                        "base_color": "mix_color",
                        "roughness": "img_value",
                        "metallic": "math",
                        "height": "band",
                        "alpha": "c_value",
                        "transmission": "edge",
                        "ior": "cavity",
                        "coat_weight": "facing",
                        "coat_roughness": "wood",
                    },
                },
                {
                    "id": "overlay",
                    "name": "Overlay",
                    "enabled": False,
                    "mask": "noise",
                },
            ],
        )
        result = pc.normalize_manifest(manifest)
        by_id = {item["id"]: item for item in result["signals"]}

        self.assertEqual(by_id["c_value"]["parameters"], {"value": 0.25})
        self.assertEqual(by_id["c_color"]["parameters"], {"value": f32(color)})
        self.assertEqual(by_id["img_color"]["parameters"]["output"], "COLOR")
        self.assertEqual(by_id["img_value"]["parameters"]["output"], "VALUE")
        expected_coordinate = {
            "space": "OBJECT",
            "scale": [1, 1, 1],
            "rotation": [0, 0, 0],
            "translation": [0, 0, 0],
        }
        self.assertEqual(
            by_id["noise"]["parameters"],
            {
                "scale": 5,
                "detail": 2,
                "roughness": 0.5,
                "lacunarity": 2,
                "distortion": 0,
                "seed": 0,
                "coordinate": expected_coordinate,
            },
        )
        self.assertEqual(
            by_id["wood"]["parameters"],
            {
                "scale": 5,
                "detail": 2,
                "roughness": 0.5,
                "distortion": 0,
                "seed": 0,
                "coordinate": expected_coordinate,
                "direction": "Z",
                "rings": False,
                "detail_scale": 1,
                "profile": "SIN",
            },
        )
        self.assertEqual(
            by_id["edge"]["parameters"],
            f32({"width": 0.003, "samples": 4, "gain": 10}),
        )
        self.assertEqual(
            by_id["cavity"]["parameters"],
            f32({"distance": 0.1, "samples": 8, "only_local": True}),
        )
        self.assertEqual(
            by_id["band"]["parameters"],
            {
                "axis": "Z",
                "low": 0,
                "high": 1,
                "coordinate": expected_coordinate,
            },
        )
        self.assertEqual(
            by_id["facing"]["parameters"], {"axis": "Z", "invert": False}
        )
        self.assertEqual(
            by_id["math"]["parameters"],
            {"operation": "ADD", "clamp": True},
        )
        self.assertEqual(by_id["ramp"]["parameters"]["stops"], stops)
        self.assertEqual(by_id["mix_value"]["parameters"], {})
        self.assertEqual(by_id["mix_color"]["parameters"], {})

        types = pc.signal_types(result)
        self.assertEqual(types["c_value"], "VALUE")
        self.assertEqual(types["c_color"], "COLOR")
        self.assertEqual(types["img_color"], "COLOR")
        self.assertEqual(types["img_value"], "VALUE")
        self.assertEqual(types["noise"], "VALUE")
        self.assertEqual(types["wood"], "VALUE")
        self.assertEqual(types["edge"], "VALUE")
        self.assertEqual(types["cavity"], "VALUE")
        self.assertEqual(types["band"], "VALUE")
        self.assertEqual(types["facing"], "VALUE")
        self.assertEqual(types["math"], "VALUE")
        self.assertEqual(types["ramp"], "COLOR")
        self.assertEqual(types["mix_value"], "VALUE")
        self.assertEqual(types["mix_color"], "COLOR")
        self.assertEqual(
            [doc["file"] for doc in pc.image_documents(result)],
            [
                absolute("textures", "color.png"),
                absolute("textures", "value.png"),
            ],
        )

    def test_constant_value_matrix_and_nan(self):
        for value in (0, -2.5, 2**100, 0.0, 1.0):
            with self.subTest(valid=value):
                result = pc.normalize_manifest(
                    self.make_manifest(
                        signals=[signal("constant", "constant", {"value": value})]
                    )
                )
                self.assertEqual(result["signals"][0]["parameters"]["value"], value)

        for value in ([0, 0, 0, 1], [1, 0.5, 0, 0], rgba()):
            with self.subTest(valid_color=value):
                result = pc.normalize_manifest(
                    self.make_manifest(
                        signals=[signal("constant", "constant", {"value": value})]
                    )
                )
                self.assertEqual(pc.signal_types(result)["constant"], "COLOR")

        invalid = [
            10**100,
            True,
            False,
            float("nan"),
            float("inf"),
            float("-inf"),
            [0, 0, 0],
            [0, 0, 0, 1, 2],
            [-0.01, 0, 0, 1],
            [0, 0, 0, 1.01],
            "red",
            None,
        ]
        for value in invalid:
            with self.subTest(invalid=value):
                self.assert_signal_invalid(
                    signal("constant", "constant", {"value": value})
                )

        self.assert_signal_invalid(
            signal("constant", "constant", {"value": 1, "extra": True})
        )
        self.assert_signal_invalid(
            {
                "id": "constant",
                "type": "constant",
                "parameters": {},
                "inputs": {},
            }
        )
        self.assert_signal_invalid(
            {
                "id": "constant",
                "type": "constant",
                "parameters": {"value": 1},
            }
        )

    def test_noise_wood_edge_cavity_band_and_facing_ranges(self):
        cases = [
            ("noise", "scale", 0.0001, True),
            ("noise", "scale", 10000, True),
            ("noise", "scale", 0.00009, False),
            ("noise", "scale", 10000.01, False),
            ("noise", "detail", 0, True),
            ("noise", "detail", 15, True),
            ("noise", "detail", -0.01, False),
            ("noise", "detail", 15.01, False),
            ("noise", "roughness", 0, True),
            ("noise", "roughness", 1, True),
            ("noise", "roughness", 1.01, False),
            ("noise", "distortion", 0, True),
            ("noise", "distortion", 100, True),
            ("noise", "distortion", -0.1, False),
            ("noise", "seed", 0, True),
            ("noise", "seed", 100000, True),
            ("noise", "seed", -1, False),
            ("noise", "seed", 100001, False),
            ("noise", "seed", 1.5, False),
            ("noise", "seed", True, False),
            ("edge", "width", 0.00001, True),
            ("edge", "width", 1, True),
            ("edge", "width", 0.000001, False),
            ("edge", "width", 1.1, False),
            ("edge", "samples", 1, True),
            ("edge", "samples", 16, True),
            ("edge", "samples", 0, False),
            ("edge", "samples", 17, False),
            ("edge", "gain", 0.1, True),
            ("edge", "gain", 100, True),
            ("edge", "gain", 0.09, False),
            ("edge", "gain", 101, False),
            ("cavity", "distance", 0.00001, True),
            ("cavity", "distance", 100, True),
            ("cavity", "distance", 0, False),
            ("cavity", "distance", 100.1, False),
            ("cavity", "samples", 1, True),
            ("cavity", "samples", 16, True),
            ("cavity", "samples", 0, False),
            ("cavity", "only_local", True, True),
            ("cavity", "only_local", False, True),
            ("height_band", "low", -10000, True),
            ("height_band", "low", 10000, True),
            ("height_band", "low", -10000.1, False),
            ("height_band", "high", 10000, True),
            ("height_band", "high", 10000.1, False),
            ("normal_direction", "invert", True, True),
        ]
        for signal_type, key, value, valid in cases:
            with self.subTest(type=signal_type, key=key, value=value):
                candidate = signal(
                    "candidate", signal_type, {key: value}
                )
                manifest = self.make_manifest(signals=[candidate])
                if valid:
                    pc.normalize_manifest(manifest)
                else:
                    with self.assertRaises(pc.WorkflowError):
                        pc.normalize_manifest(manifest)

        for operation in pc.MATH_OPERATIONS:
            with self.subTest(operation=operation):
                candidate = signal(
                    "candidate",
                    "math",
                    {"operation": operation},
                    {"a": "base_noise", "b": "base_noise"},
                )
                pc.normalize_manifest(
                    self.make_manifest(
                        signals=[candidate, signal("base_noise", "noise")]
                    )
                )
        for axis in ("X", "Y", "Z"):
            for signal_type in ("height_band", "normal_direction"):
                with self.subTest(axis=axis, type=signal_type):
                    candidate = signal(
                        "candidate", signal_type, {"axis": axis}
                    )
                    pc.normalize_manifest(
                        self.make_manifest(signals=[candidate])
                    )

        self.assert_signal_invalid(
            signal("noise", "noise", {"scale": float("nan")})
        )
        self.assert_signal_invalid(
            signal("noise", "noise", {"unknown": 1})
        )
        self.assert_signal_invalid(
            signal("edge", "edge", {"samples": True})
        )
        self.assert_signal_invalid(
            signal("cavity", "cavity", {"only_local": 1})
        )
        self.assert_signal_invalid(
            signal("height_band", "height_band", {"axis": "W"})
        )
        self.assert_signal_invalid(
            signal("normal_direction", "normal_direction", {"axis": "W"})
        )
        self.assert_signal_invalid(signal("wood", "wood", {"direction": "W"}))
        self.assert_signal_invalid(signal("wood", "wood", {"rings": 1}))
        valid_wood = signal(
            "wood",
            "wood",
            {"direction": "X", "rings": True, "seed": 42},
        )
        result = pc.normalize_manifest(self.make_manifest(signals=[valid_wood]))
        self.assertEqual(result["signals"][0]["parameters"]["direction"], "X")
        self.assertTrue(result["signals"][0]["parameters"]["rings"])
        self.assertEqual(result["signals"][0]["parameters"]["seed"], 42)

    def test_coordinate_contract(self):
        coordinate = {
            "space": "UV",
            "scale": [2, 3, 4],
            "rotation": [10, 20, 30],
            "translation": [-1, 0, 1],
        }
        result = pc.normalize_manifest(
            self.make_manifest(
                signals=[
                    signal("noise", "noise", {"coordinate": coordinate})
                ]
            )
        )
        self.assertEqual(
            result["signals"][0]["parameters"]["coordinate"], coordinate
        )

        invalid = [
            {"space": "GENERATED"},
            {"space": "UV", "scale": [0, 1, 1]},
            {"space": "UV", "scale": [-1, 1, 1]},
            {"space": "UV", "scale": [1, 1]},
            {"space": "UV", "rotation": ["x", 0, 0]},
            {"space": "UV", "translation": [0, 0, math.inf]},
            {"space": "UV", "translation": [0, float("nan"), 0]},
            {"space": "UV", "extra": 1},
        ]
        for value in invalid:
            with self.subTest(coordinate=value):
                self.assert_signal_invalid(
                    signal("noise", "noise", {"coordinate": value})
                )

    def test_math_ramp_and_mix_types(self):
        self.assert_signal_invalid(
            signal(
                "math",
                "math",
                {"operation": "DIVIDE"},
                {"a": "base_noise", "b": "base_noise"},
            ),
            extra_signals=[signal("base_noise", "noise")],
        )
        self.assert_signal_invalid(
            signal(
                "math",
                "math",
                {"operation": "ADD"},
                {"a": "base_noise"},
            ),
            extra_signals=[signal("base_noise", "noise")],
        )
        self.assert_signal_invalid(
            signal(
                "math",
                "math",
                {"operation": "ADD", "clamp": 1},
                {"a": "base_noise", "b": "base_noise"},
            ),
            extra_signals=[signal("base_noise", "noise")],
        )
        self.assert_signal_invalid(
            signal(
                "math",
                "math",
                {"operation": "ADD"},
                {"a": "base_color", "b": "base_noise"},
            ),
            extra_signals=[
                signal("base_color", "constant", {"value": rgba()}),
                signal("base_noise", "noise"),
            ],
        )

        valid_stops = [
            {"position": 0, "color": rgba(0, 0, 0, 1)},
            {"position": 0.5, "color": rgba(0.5, 0.5, 0.5, 1)},
            {"position": 1, "color": rgba(1, 1, 1, 1)},
        ]
        ramp_result = pc.normalize_manifest(
            self.make_manifest(
                signals=[
                    signal(
                        "ramp",
                        "ramp",
                        {"stops": valid_stops},
                        {"value": "base_noise"},
                    ),
                    signal("base_noise", "noise"),
                ]
            )
        )
        self.assertEqual(
            pc.signal_types(ramp_result)["ramp"], "COLOR"
        )

        bad_stops = [
            valid_stops[:1],
            [
                {"position": index / 8, "color": rgba()}
                for index in range(9)
            ],
            [
                {"position": 0.6, "color": rgba()},
                {"position": 0.5, "color": rgba()},
            ],
            [
                {"position": 0.5, "color": rgba()},
                {"position": 0.5, "color": rgba()},
            ],
            [
                {"position": -0.1, "color": rgba()},
                {"position": 1, "color": rgba()},
            ],
            [
                {"position": 0, "color": [0.5, 0.5, 0.5]},
                {"position": 1, "color": rgba()},
            ],
            [
                {"position": 0, "color": rgba()},
                {"position": 1},
            ],
        ]
        for stops in bad_stops:
            with self.subTest(stops=stops):
                self.assert_signal_invalid(
                    signal(
                        "ramp",
                        "ramp",
                        {"stops": stops},
                        {"value": "base_noise"},
                    ),
                    extra_signals=[signal("base_noise", "noise")],
                )

        color = signal("color", "constant", {"value": rgba()})
        value = signal("value", "constant", {"value": 0.5})
        noise = signal("noise", "noise")
        self.assert_signal_invalid(
            signal(
                "ramp",
                "ramp",
                {"stops": valid_stops},
                {"value": "color"},
            ),
            extra_signals=[color],
        )
        self.assert_signal_invalid(
            signal(
                "mix",
                "mix",
                {},
                {"factor": "color", "a": "value", "b": "value"},
            ),
            extra_signals=[color, value],
        )
        self.assert_signal_invalid(
            signal(
                "mix",
                "mix",
                {},
                {"factor": "noise", "a": "value", "b": "color"},
            ),
            extra_signals=[color, value, noise],
        )
        self.assert_signal_invalid(
            signal(
                "mix",
                "mix",
                {"unexpected": 1},
                {"factor": "noise", "a": "value", "b": "value"},
            ),
            extra_signals=[value, noise],
        )
        self.assert_signal_invalid(
            signal(
                "mix",
                "mix",
                {},
                {"factor": "noise", "a": "value"},
            ),
            extra_signals=[value, noise],
        )

    def test_graph_references_cycles_and_duplicate_ids(self):
        ramp = signal(
            "ramp",
            "ramp",
            {
                "stops": [
                    {"position": 0, "color": rgba(0, 0, 0, 1)},
                    {"position": 1, "color": rgba(1, 1, 1, 1)},
                ]
            },
            {"value": "missing"},
        )
        self.assert_signal_invalid(ramp, fragment="references unknown signal ID")

        value = signal("value", "constant", {"value": 0.5})
        self.assert_signal_invalid(
            signal(
                "math_self",
                "math",
                {"operation": "ADD"},
                {"a": "math_self", "b": "value"},
            ),
            extra_signals=[value],
            fragment="dependency cycle",
        )
        math_a = signal(
            "math_a",
            "math",
            {"operation": "ADD"},
            {"a": "math_b", "b": "value"},
        )
        math_b = signal(
            "math_b",
            "math",
            {"operation": "ADD"},
            {"a": "math_a", "b": "value"},
        )
        self.assert_signal_invalid(
            math_a,
            extra_signals=[math_b, value],
            fragment="dependency cycle",
        )
        self.assert_signal_invalid(
            signal("duplicate", "noise"),
            extra_signals=[signal("duplicate", "noise")],
            fragment="duplicate stable ID",
        )
        self.assert_signal_invalid(
            signal("unknown", "unsupported_procedural_source"),
        )

    def test_layer_channel_and_mask_types(self):
        value = signal("value", "constant", {"value": 0.5})
        color = signal("color", "constant", {"value": rgba()})

        self.assert_invalid(
            self.make_manifest(
                signals=[value, color],
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "channels": {"base_color": "value"},
                    }
                ],
            ),
            "requires COLOR",
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[value, color],
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "channels": {"roughness": "color"},
                    }
                ],
            ),
            "requires VALUE",
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[value],
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "channels": {"roughness": "missing"},
                    }
                ],
            ),
            "references unknown signal ID",
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[value],
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "channels": {"normal": "value"},
                    }
                ],
            )
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[color],
                layers=[
                    {"id": "base", "name": "Base"},
                    {"id": "overlay", "name": "Overlay", "mask": "color"},
                ],
            ),
            "requires VALUE",
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[value],
                layers=[
                    {"id": "base", "name": "Base"},
                    {"id": "overlay", "name": "Overlay", "mask": "missing"},
                ],
            ),
            "references unknown signal ID",
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[value],
                layers=[
                    {"id": "base", "name": "Base"},
                    {"id": "base", "name": "Duplicate"},
                ],
            ),
            "duplicate stable ID",
        )

        valid = pc.normalize_manifest(
            self.make_manifest(
                signals=[value, color],
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "channels": {
                            "base_color": "color",
                            "roughness": "value",
                        },
                    },
                    {
                        "id": "overlay",
                        "name": "Overlay",
                        "enabled": False,
                        "mask": "value",
                    },
                ],
            )
        )
        self.assertEqual(valid["layers"][1]["mask"], "value")

    def test_layer_values_bounds_and_defaults(self):
        result = pc.normalize_manifest(self.make_manifest())
        values = result["layers"][0]["values"]
        expected = {
            "base_color": [0.5, 0.5, 0.5, 1],
            "roughness": 0.5,
            "metallic": 0,
            "height": 0,
            "alpha": 1,
            "transmission": 0,
            "ior": 1.5,
            "coat_weight": 0,
            "coat_roughness": 0.03,
        }
        self.assertEqual(values, f32(expected))

        invalid_values = [
            {"base_color": [0.5, 0.5, 0.5]},
            {"base_color": [0, 0, 0, 1.1]},
            {"roughness": 1.1},
            {"metallic": -0.1},
            {"height": 1.1},
            {"height": -1.1},
            {"alpha": 1.1},
            {"transmission": -0.1},
            {"ior": 0.9},
            {"ior": 4.1},
            {"coat_weight": 1.1},
            {"coat_roughness": -0.1},
            {"normal": 1},
            {"roughness": float("nan")},
        ]
        for values_override in invalid_values:
            with self.subTest(values=values_override):
                self.assert_invalid(
                    self.make_manifest(
                        layers=[
                            {
                                "id": "base",
                                "name": "Base",
                                "values": values_override,
                            }
                        ]
                    )
                )

        self.assert_invalid(
            self.make_manifest(
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "opacity": float("nan"),
                    }
                ]
            )
        )
        self.assert_invalid(
            self.make_manifest(
                layers=[
                    {"id": "base", "name": "Base", "enabled": "yes"}
                ]
            )
        )
        self.assert_invalid(
            self.make_manifest(
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "mask": {"file": "x"},
                    }
                ]
            )
        )

    def test_base_layer_invariant(self):
        noise = signal("noise", "noise")
        cases = [
            {"enabled": False},
            {"opacity": 0.5},
            {"mask": "noise"},
        ]
        for overrides in cases:
            layer = {"id": "base", "name": "Base"}
            layer.update(overrides)
            with self.subTest(base=overrides):
                self.assert_invalid(
                    self.make_manifest(signals=[noise], layers=[layer]),
                    "base layer must be enabled, opaque and unmasked",
                )

    def test_counts_and_top_level_bounds(self):
        self.assert_invalid(self.make_manifest(signals=[]))
        self.assert_invalid(
            self.make_manifest(
                signals=[
                    signal("signal_" + str(index), "noise")
                    for index in range(97)
                ]
            )
        )
        self.assert_invalid(
            self.make_manifest(
                layers=[
                    {"id": "layer_" + str(index), "name": "Layer " + str(index)}
                    for index in range(9)
                ]
            )
        )
        self.assert_invalid(self.make_manifest(layers=[]))
        self.assert_invalid(self.make_manifest(height_distance=-0.1))
        self.assert_invalid(self.make_manifest(height_distance=1.1))
        self.assert_invalid(self.make_manifest(mesh_map_size=63))
        self.assert_invalid(self.make_manifest(mesh_map_size=2049))
        self.assert_invalid(self.make_manifest(mesh_map_size=512.0))

        valid = pc.normalize_manifest(
            self.make_manifest(
                signals=[
                    signal("signal_" + str(index), "noise")
                    for index in range(96)
                ],
                layers=[
                    {"id": "layer_" + str(index), "name": "Layer " + str(index)}
                    for index in range(8)
                ],
                height_distance=1,
                mesh_map_size=2048,
            )
        )
        self.assertEqual(len(valid["signals"]), 96)
        self.assertEqual(len(valid["layers"]), 8)
        self.assertEqual(valid["height_distance"], 1)
        self.assertEqual(valid["mesh_map_size"], 2048)

    def test_unknown_fields_everywhere(self):
        manifest = self.make_manifest()
        manifest["extra"] = 1
        self.assert_invalid(manifest)

        bad_signal = signal("noise", "noise")
        bad_signal["extra"] = 1
        self.assert_signal_invalid(bad_signal)

        self.assert_signal_invalid(
            signal("noise", "noise", {"scale": 1, "extra": 1})
        )
        self.assert_signal_invalid(
            signal(
                "height_band",
                "height_band",
                {"coordinate": {"space": "UV", "extra": 1}},
            )
        )
        self.assert_signal_invalid(
            signal(
                "noise",
                "noise",
                {},
                {"extra": "noise"},
            )
        )
        self.assert_invalid(
            self.make_manifest(
                layers=[
                    {"id": "base", "name": "Base", "extra": True}
                ]
            )
        )
        self.assert_invalid(
            self.make_manifest(
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "values": {"normal_strength": 1},
                    }
                ]
            )
        )
        self.assert_invalid(
            self.make_manifest(
                material={"id": "mat", "name": "Mat", "extra": 1}
            )
        )

    def test_image_color_spaces_and_source_conflicts(self):
        color = image_signal(
            "color_image",
            "COLOR",
            "sRGB",
            path=absolute("textures", "color.png"),
        )
        color_layer = {
            "id": "base",
            "name": "Base",
            "channels": {"base_color": "color_image"},
        }
        normalized = pc.normalize_manifest(
            self.make_manifest(signals=[color], layers=[color_layer])
        )
        self.assertEqual(
            normalized["signals"][0]["parameters"]["image"]["color_space"],
            "sRGB",
        )

        self.assert_invalid(
            self.make_manifest(
                signals=[
                    image_signal(
                        "color_image",
                        "COLOR",
                        "Non-Color",
                        path=absolute("textures", "color.png"),
                    )
                ],
                layers=[color_layer],
            ),
            "requires sRGB",
        )
        data = image_signal(
            "data_image",
            "VALUE",
            "Non-Color",
            path=absolute("textures", "data.png"),
        )
        data_layer = {
            "id": "base",
            "name": "Base",
            "channels": {"roughness": "data_image"},
        }
        pc.normalize_manifest(
            self.make_manifest(signals=[data], layers=[data_layer])
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[
                    image_signal(
                        "data_image",
                        "VALUE",
                        "sRGB",
                        path=absolute("textures", "data.png"),
                    )
                ],
                layers=[data_layer],
            ),
            "requires Non-Color",
        )

        color_via_mix = [
            color,
            signal(
                "mix",
                "mix",
                {},
                {"factor": "factor", "a": "color_image", "b": "color_image"},
            ),
            signal("factor", "constant", {"value": 0.5}),
        ]
        self.assert_invalid(
            self.make_manifest(
                signals=[
                    image_signal(
                        "color_image",
                        "COLOR",
                        "Non-Color",
                        path=absolute("textures", "color.png"),
                    ),
                    *color_via_mix[1:],
                ],
                layers=[
                    {
                        "id": "base",
                        "name": "Base",
                        "channels": {"base_color": "mix"},
                    }
                ],
            ),
            "requires sRGB",
        )

        same_path = absolute("textures", "same.png")
        self.assert_invalid(
            self.make_manifest(
                signals=[
                    image_signal(
                        "one", "VALUE", "Non-Color", path=same_path, digest=HASH_A
                    ),
                    image_signal(
                        "two", "VALUE", "Non-Color", path=same_path, digest=HASH_B
                    ),
                ]
            ),
            "conflicting hashes",
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[
                    image_signal(
                        "one", "VALUE", "Non-Color", path=same_path, digest=HASH_A
                    ),
                    image_signal(
                        "two",
                        "VALUE",
                        "Non-Color",
                        path=same_path.upper(),
                        digest=HASH_B,
                    ),
                ]
            ),
            "conflicting hashes",
        )
        same_hash = pc.normalize_manifest(
            self.make_manifest(
                signals=[
                    image_signal(
                        "one", "VALUE", "Non-Color", path=same_path, digest=HASH_A
                    ),
                    image_signal(
                        "two", "VALUE", "Non-Color", path=same_path, digest=HASH_A
                    ),
                ]
            )
        )
        self.assertEqual(len(pc.image_documents(same_hash)), 2)

        self.assert_signal_invalid(
            image_signal(
                "relative",
                "VALUE",
                "Non-Color",
                path="textures/relative.png",
            )
        )
        self.assert_signal_invalid(
            image_signal(
                "udim",
                "VALUE",
                "Non-Color",
                path=absolute("textures", "tile_<UDIM>.png"),
            )
        )
        self.assert_signal_invalid(
            image_signal(
                "bad_sha",
                "VALUE",
                "Non-Color",
                path=absolute("textures", "bad.png"),
                digest="A" * 64,
            )
        )
        self.assert_signal_invalid(
            image_signal(
                "bad_output",
                "VECTOR",
                "Non-Color",
                path=absolute("textures", "bad.png"),
            )
        )

    def test_windows_names_views_and_gpu_checks(self):
        self.assert_invalid(
            self.make_manifest(
                material={"id": "mat", "name": "Bad/Name"}
            )
        )
        self.assert_invalid(
            self.make_manifest(
                material={"id": "CON", "name": "Material"}
            )
        )
        self.assert_invalid(
            self.make_manifest(
                layers=[{"id": "base", "name": "Bad:Name"}]
            )
        )
        self.assert_invalid(
            self.make_manifest(
                layers=[{"id": "aux", "name": "Base"}]
            )
        )
        self.assert_invalid(
            self.make_manifest(
                signals=[signal("CON", "noise")]
            )
        )
        self.assert_invalid(
            self.make_manifest(
                preview={
                    "device": {"backend": "CPU"},
                    "views": [{"id": "con"}],
                }
            )
        )
        self.assert_invalid(
            self.make_manifest(
                preview={
                    "device": {"backend": "CPU"},
                    "views": [{"id": "Front"}, {"id": "front"}],
                }
            ),
            "unique ignoring case",
        )
        self.assert_invalid(
            self.make_manifest(
                preview={
                    "device": {"backend": "CUDA"},
                    "views": [{"id": "front"}],
                }
            )
        )
        self.assert_invalid(
            self.make_manifest(
                preview={
                    "device": {"backend": "CPU", "id": "GPU-1"},
                    "views": [{"id": "front"}],
                }
            )
        )
        self.assert_invalid(
            self.make_manifest(
                preview={
                    "engine": "BLENDER_EEVEE",
                    "device": {"backend": "GRAPHICS"},
                    "denoise": True,
                    "views": [{"id": "front"}],
                }
            )
        )
        gpu = pc.normalize_manifest(
            self.make_manifest(
                preview={
                    "device": {"backend": "OPTIX", "id": "GPU-1"},
                    "views": [{"id": "front"}],
                }
            )
        )
        self.assertEqual(gpu["preview"]["device"]["id"], "GPU-1")
        self.assert_invalid(
            self.make_manifest(
                material={
                    "id": "mat",
                    "name": "Mat",
                    "template": "pbr_layers_v1",
                }
            )
        )

    def test_export_normalization_and_rejection(self):
        defaults = pc.normalize_export({})
        self.assertEqual(
            defaults,
            {
                "channels": ["base_color", "roughness", "metallic", "normal"],
                "size": 2048,
                "margin": 16,
                "samples": 16,
                "bit_depth": "16",
            },
        )
        custom = pc.normalize_export(
            {
                "channels": list(reversed(pc.EXPORT_CHANNELS)),
                "size": 64,
                "margin": 0,
                "samples": 1,
                "bit_depth": "8",
            }
        )
        self.assertEqual(
            custom["channels"], list(reversed(pc.EXPORT_CHANNELS))
        )
        self.assertEqual(custom["size"], 64)
        self.assertEqual(custom["margin"], 0)
        self.assertEqual(custom["samples"], 1)
        self.assertEqual(custom["bit_depth"], "8")
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_export({"channels": []})

        invalid = [
            {"channels": ["roughness", "roughness"]},
            {"channels": ["normal", "normal"]},
            {"channels": ["vector"]},
            {"size": 63},
            {"size": 2049},
            {"size": 2048.0},
            {"margin": -1},
            {"margin": 129},
            {"samples": 0},
            {"samples": 257},
            {"bit_depth": 16},
            {"bit_depth": "32"},
            {"manifest": {}},
            {"extra": 1},
        ]
        for value in invalid:
            with self.subTest(export=value):
                with self.assertRaises(pc.WorkflowError):
                    pc.normalize_export(value)

        self.assertEqual(
            pc.normalize_export({"size": 2048, "margin": 128, "samples": 256})[
                "size"
            ],
            2048,
        )
        self.assert_invalid(self.make_manifest(export={"size": 2048}))
        self.assert_invalid(self.make_manifest(size=2048))

    def test_normalize_params_resource_protection(self):
        color_path = absolute("textures", "color.png")
        data_path = absolute("textures", "data.png")
        manifest = self.make_manifest(
            signals=[
                image_signal(
                    "color_image", "COLOR", "sRGB", path=color_path, digest=HASH_A
                ),
                image_signal(
                    "data_image",
                    "VALUE",
                    "Non-Color",
                    path=data_path,
                    digest=HASH_B,
                ),
                signal(
                    "tint",
                    "mix",
                    {},
                    {
                        "b": "color_image",
                        "factor": "mask_noise",
                        "a": "color_image",
                    },
                ),
                signal("mask_noise", "noise"),
            ],
            layers=[
                {
                    "id": "base",
                    "name": "Base",
                    "channels": {
                        "base_color": "tint",
                        "roughness": "data_image",
                    },
                },
                {
                    "id": "overlay",
                    "name": "Overlay",
                    "enabled": False,
                    "mask": "mask_noise",
                },
            ],
        )
        blend_path = absolute("source", "asset.blend")
        value = {
            "file": blend_path,
            "expected_sha256": HASH_C,
            "manifest": manifest,
            "resources": [
                {"file": color_path, "expected_sha256": HASH_A},
                {"file": data_path, "expected_sha256": HASH_B},
            ],
        }
        snapshot = deepcopy(value)
        result = pc.normalize_params(value)
        self.assertEqual(value, snapshot)
        self.assertEqual(result["file"], blend_path)
        self.assertEqual(len(pc.image_documents(result["manifest"])), 2)
        result_signals = {
            item["id"]: item for item in result["manifest"]["signals"]
        }
        self.assertEqual(
            list(result_signals["tint"]["inputs"]),
            ["b", "factor", "a"],
        )
        self.assertEqual(
            [doc["file"] for doc in pc.image_documents(result["manifest"])],
            [color_path, data_path],
        )

        missing = deepcopy(value)
        missing["resources"].pop()
        with self.assertRaises(pc.WorkflowError) as caught:
            pc.normalize_params(missing)
        self.assertEqual(caught.exception.code, "INVALID_REQUEST")

        wrong_hash = deepcopy(value)
        wrong_hash["resources"][0]["expected_sha256"] = HASH_D
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_params(wrong_hash)

        duplicate = deepcopy(value)
        duplicate["resources"].append(
            {"file": color_path, "expected_sha256": HASH_A}
        )
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_params(duplicate)

        duplicate_case = deepcopy(value)
        duplicate_case["resources"].append(
            {"file": color_path.upper(), "expected_sha256": HASH_A}
        )
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_params(duplicate_case)

        conflicting = deepcopy(value)
        conflicting["resources"].pop(1)
        conflicting["resources"][0]["expected_sha256"] = HASH_D
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_params(conflicting)

        relative_resource = deepcopy(value)
        relative_resource["resources"][0]["file"] = "textures/color.png"
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_params(relative_resource)

        wrong_suffix = deepcopy(value)
        wrong_suffix["file"] = absolute("source", "asset.py")
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_params(wrong_suffix)

        extra = deepcopy(value)
        extra["extra"] = 1
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_params(extra)

    def test_legacy_contract_still_works_and_is_distinct(self):
        legacy_manifest = {
            "schema_version": "1.0",
            "context": {"scene": "Scene", "view_layer": "ViewLayer"},
            "target": {"object": "Crate", "uv_layer": "UVMap"},
            "material": {"id": "mat_legacy", "name": "Legacy"},
            "layers": [{"id": "base", "name": "Base"}],
            "preview": {
                "device": {"backend": "CPU"},
                "views": [{"id": "front"}],
            },
        }
        result = legacy_contract.normalize_manifest(legacy_manifest)
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["material"]["template"], "pbr_layers_v1")
        self.assertEqual(result["layers"][0]["values"]["normal_strength"], 1)
        self.assertEqual(result["layers"][0]["values"]["emission_strength"], 0)
        self.assertEqual(legacy_contract.image_documents(result), [])

        with self.assertRaises(legacy_contract.WorkflowError):
            legacy_contract.normalize_manifest(self.make_manifest())
        with self.assertRaises(pc.WorkflowError):
            pc.normalize_manifest(legacy_manifest)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    (OUT / 'report.json').write_text(json.dumps({'status': 'pass' if result.wasSuccessful() else 'fail', 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}, indent=2), encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
