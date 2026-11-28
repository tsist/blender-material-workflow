"""Test a pinned first-party helper with fake images; no Blender or UI."""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace as NS

BASE = "31850a1bea59acf3f6f5bf501704b768f670261f"
raw = subprocess.check_output(["git", "show", BASE + ":procedural_core.py"])
root = ast.parse(raw)
fn, = [x for x in root.body if isinstance(x, ast.FunctionDef) and x.name == "_image_identity"]
ns = {"hashlib": hashlib}
exec(compile(ast.Module(body=[fn],type_ignores=[]),BASE,"exec"),ns)
signature = ns["_image_identity"]

class Pixels(list):
    def foreach_get(self, dest):
        arr = importlib.import_module("array")
        dest[:] = arr.array("f", self)

def image(name, file):
    return NS(name=name, filepath=file, size=(2,2),
              colorspace_settings=NS(name="Non-Color"), pixels=Pixels([.25]*16))

a, independent = image("mask", "//original.png"), image("copy", "//fork.png")
alias = a
start = signature(a)
assert a is not independent and a.filepath != independent.filepath
assert signature(alias)==signature(independent)==start
alias.pixels[0]=.75
assert signature(a)==signature(alias)!=start
assert signature(independent)==start
independent.colorspace_settings.name="sRGB"
assert signature(independent)!=start
print(json.dumps({"source":BASE,"source_sha256":hashlib.sha256(raw).hexdigest(),
    "initial_shared_equals_independent_signature":True,
    "alias_mutation_visible_in_original":True,
    "independent_pixels_and_signature_unchanged_by_alias_edit":True,
    "color_space_change_visible":True,
    "scope":"only _image_identity with fake images; no Blender or broader managed transaction"},
    indent=2))
