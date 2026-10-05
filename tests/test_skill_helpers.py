# SPDX-License-Identifier: GPL-3.0-or-later
"""Public skill helpers through real subprocesses; no Blender or private assets."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
ROOT = Path(__file__).resolve().parents[1]
DISCOVER = ROOT / 'skills/blender-cli/scripts/discover.py'
NAMES = ROOT / 'skills/blender-asset-manager/scripts/check_names.py'
GATE = ROOT / 'skills/blender-material-authoring/scripts/image_gate.py'

class SkillToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.work = Path(self.temp.name)
        self.env = dict(os.environ); self.env.pop('BLENDERCTL_ROOT', None)
        self.env['PYTHONDONTWRITEBYTECODE'] = '1'
    def tearDown(self): self.temp.cleanup()
    def call(self, script, *args, cwd=None, env=None, isolated=False):
        return subprocess.run([sys.executable, *(['-S'] if isolated else []), str(script), *map(str, args)],
            cwd=cwd or self.work, env=env or self.env, capture_output=True, text=True, encoding='utf-8', timeout=30)
    def test_name_preflight_valid_invalid_collision_readonly(self):
        target = self.work / 'assets'; target.mkdir(); existing = target / 'MOD_Cube_v001.blend'
        existing.write_bytes(b'original source fixture'); before = existing.read_bytes()
        for names, good in [(['MAT_Ceramic_v001.blend'], True), (['MOD_Cube_v001.blend'], False),
                            (['MOD_cube_v001.blend'], False), (['MAT_Ceramic_v000.blend', '../escape.blend'], False),
                            (['MAT_Foo_v001.blend', 'MAT_foo_v001.blend'], False)]:
            path = self.work / 'names.json'; path.write_text(json.dumps({'directory': str(target), 'names': names}))
            p = self.call(NAMES, '--input', path); self.assertEqual(p.returncode, 0 if good else 2, p.stderr)
            result = json.loads(p.stdout); self.assertEqual(result['ok'], good); self.assertEqual(result['mutations'], 0)
            self.assertEqual(list(target.iterdir()), [existing]); self.assertEqual(existing.read_bytes(), before)
    def test_image_help_without_site_packages(self):
        p = self.call(GATE, '--help', isolated=True); self.assertEqual(p.returncode, 0, p.stderr)
    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow not installed; decoding requires optional Pillow')
    def test_original_png_gate_budgets_and_input_protection(self):
        def chunk(kind, payload):
            return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind+payload) & 0xffffffff)
        raw = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 4, 4, 8, 2, 0, 0, 0))
        raw += chunk(b'IDAT', zlib.compress((b'\0' + b'\x80\x40\x20'*4)*4)) + chunk(b'IEND', b'')
        image = self.work / 'own.png'; image.write_bytes(raw)
        for extra, code in [((), 0), (('--max-edge', '3'), 1), (('--max-preview-bytes', '1'), 1)]:
            p = self.call(GATE, image, '--purpose', 'preview', *extra); self.assertEqual(p.returncode, code, p.stderr)
            result = json.loads(p.stdout); self.assertEqual(result['pass'], code == 0); self.assertTrue(result['images'][0]['decoded'])
            self.assertEqual(result['images'][0]['sha256'], hashlib.sha256(raw).hexdigest())
        p = self.call(GATE, image, '--purpose', 'preview', '--report', image)
        self.assertNotEqual(p.returncode, 0); self.assertEqual(image.read_bytes(), raw)

if __name__ == '__main__': unittest.main()
