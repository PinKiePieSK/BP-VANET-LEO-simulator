"""Orbit snapshots must be complete and byte-pinned before reuse."""
import gzip
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fetch_orbits
from fetch_orbits import ROOT, verify_snapshot


class OrbitArchiveGate(unittest.TestCase):
    def test_existing_three_group_archive_is_intact(self):
        path = ROOT / 'data/orbits/20261022T124815Z-retlector'
        manifest = verify_snapshot(path)
        self.assertEqual(set(manifest['groups']), {'iridium-NEXT', 'globalstar', 'starlink'})

    def test_corrupted_group_is_rejected_before_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            groups = {}
            for group in ('iridium-NEXT', 'globalstar', 'starlink'):
                raw = json.dumps([{'NORAD_CAT_ID': 12345, 'EPOCH': '2026-11-01T00:00:00Z'}]).encode()
                packed = gzip.compress(raw, mtime=0)
                (path / f'{group}.json.gz').write_bytes(packed)
                groups[group] = {'file': f'{group}.json.gz', 'objects': 1,
                                 'gzip_sha256': hashlib.sha256(packed).hexdigest(),
                                 'raw_sha256': hashlib.sha256(raw).hexdigest()}
            (path / 'manifest.json').write_text(json.dumps({'schema': 1, 'groups': groups}))
            self.assertEqual(len(verify_snapshot(path)['groups']), 3)
            (path / 'globalstar.json.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'compressed orbit hash mismatch'):
                verify_snapshot(path)

    def test_empty_download_never_becomes_a_snapshot(self):
        class EmptyResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, *_): return b'[]'
        class EmptyOpener:
            def open(self, *_args, **_kwargs): return EmptyResponse()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(fetch_orbits, 'DEST', Path(temporary)), \
                 patch.object(fetch_orbits, 'build_opener', return_value=EmptyOpener()):
                with self.assertRaisesRegex(ValueError, 'empty or invalid OMM JSON'):
                    fetch_orbits.fetch(datetime(2026, 11, 1, tzinfo=timezone.utc), 'celestrak')
                self.assertEqual(list(Path(temporary).rglob('*.json.gz')), [])
                self.assertEqual(list(Path(temporary).rglob('manifest.json')), [])


if __name__ == '__main__':
    unittest.main()
