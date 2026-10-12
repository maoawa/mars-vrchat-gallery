import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_photos_json import build_photos, parse_photo
from tags import build_tag_templates
from process_photos import thumbnail_size
from upload_photos import build_upload_tasks


class PhotoScriptsTest(unittest.TestCase):
    def test_variants_and_migration_preserve_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            stem = 'VRChat_2026-10-13_01-00-00'
            other = 'VRChat_2026-10-13_02-00-00'
            for filename in [stem + '.png', stem + '.jpg', other + '.png', other + '.jpg']:
                (folder / filename).touch()
            existing = [{'id': 15, 'filename': stem + '.png', 'description_en': 'Keep me', 'parent': 14}]
            result = build_photos(folder, existing)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0], existing[0])
            self.assertEqual(result[1]['filename'], other + '.jpg')
            self.assertEqual(result[1]['id'], 16)
            self.assertEqual(build_photos(folder, result), result)

    def test_photo_parser(self):
        self.assertEqual(parse_photo('VRChat_2026-10-13_01-02-03.png').captured, '2026-10-13T01:02:03')
        self.assertIsNone(parse_photo('unrelated.png'))

    def test_processing_thumbnail_limit(self):
        self.assertEqual(thumbnail_size(3840, 2160, 640), (640, 360))
        self.assertEqual(thumbnail_size(500, 900, 640), (356, 640))
        self.assertEqual(thumbnail_size(640, 360, 640), (640, 360))

    def test_upload_tasks_use_r2_variant_prefixes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            full = folder / 'full'
            thumbnail = folder / 'thumbnail'
            full.mkdir()
            thumbnail.mkdir()
            (folder / 'VRChat_2026-10-13_01-00-00.png').touch()
            (full / 'VRChat_2026-10-13_01-00-00.jpg').touch()
            (thumbnail / 'VRChat_2026-10-13_01-00-00.jpg').touch()
            tasks = build_upload_tasks(folder)
            self.assertEqual([(task.variant, task.key) for task in tasks], [
                ('original', 'original/VRChat_2026-10-13_01-00-00.png'),
                ('full', 'full/VRChat_2026-10-13_01-00-00.jpg'),
                ('thumbnail', 'thumbnail/VRChat_2026-10-13_01-00-00.jpg'),
            ])

    def test_tags_preserved_and_generated(self):
        existing = [{'photo': 1, 'tags': [{'friend': 'a', 'x': 20, 'y': 30}]}]
        result = build_tag_templates([{'id': 1, 'friend': ['a']}, {'id': 2, 'friend': ['b']}], existing)
        self.assertEqual(result[0], existing[0])
        self.assertEqual(result[1]['tags'][0]['friend'], 'b')


if __name__ == '__main__':
    unittest.main()
