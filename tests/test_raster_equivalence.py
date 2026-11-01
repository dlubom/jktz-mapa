from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_rasters import compare


class EquivalenceTests(unittest.TestCase):
    def test_full_comparison_ignores_only_build_report_telemetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference, candidate = root / 'old', root / 'new'
            for path in (reference, candidate):
                path.mkdir()
                (path / 'image.webp').write_bytes(b'exact encoded image')
                (path / 'metadata.json').write_text('{"coordinate":[560000,150000],"id":"001"}\n')
                (path / 'build-report.json').write_text('{"buildSeconds":1,"bytes":42,"counts":{"plans":1}}')
            (candidate / 'build-report.json').write_text('{"buildSeconds":2,"bytes":43,"counts":{"plans":1}}')
            result = compare(reference, candidate)
            self.assertEqual(result['filesCompared'], 3)
            self.assertEqual(result['webpFiles'], 1)
            for name, changed in [('image.webp', b'other encoding'), ('metadata.json', b'{"id":"other"}'),
                                  ('build-report.json', b'{"buildSeconds":2,"bytes":43,"counts":{"plans":2}}')]:
                with self.subTest(name=name):
                    before = (candidate / name).read_bytes()
                    (candidate / name).write_bytes(changed)
                    with self.assertRaisesRegex(ValueError, 'differs'):
                        compare(reference, candidate)
                    (candidate / name).write_bytes(before)
            (candidate / 'image.webp').unlink()
            with self.assertRaisesRegex(ValueError, 'inventory'):
                compare(reference, candidate)


if __name__ == '__main__':
    unittest.main()
