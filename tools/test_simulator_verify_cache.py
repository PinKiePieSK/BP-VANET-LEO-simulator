"""The UI may reuse an audit only while the checked run and source stay unchanged."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import simulator_editor_api as editor


class VerifyCacheTest(unittest.TestCase):
    def test_recheck_after_result_or_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tools').mkdir()
            source = root / 'tools/check.py'
            source.write_text('first\n')
            run = root / 'run'
            run.mkdir()
            (run / 'run-manifest.json').write_text(json.dumps({'sources': {'tools/check.py': 'recorded'}}))
            trace = run / 'trace.csv'
            trace.write_text('first\n')
            editor._verified.clear()
            with patch.object(editor, 'ROOT', root), patch.object(editor, 'verify', return_value={'status': 'PASS'}) as audit:
                editor.verified_run(run)
                editor.verified_run(run)
                self.assertEqual(audit.call_count, 1)
                trace.write_text('second version\n')
                editor.verified_run(run)
                self.assertEqual(audit.call_count, 2)
                source.write_text('second version\n')
                editor.verified_run(run)
                self.assertEqual(audit.call_count, 3)
            editor._verified.clear()


if __name__ == '__main__':
    unittest.main()
