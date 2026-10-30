"""A blocked upstream must not reach visitors or overwrite a valid cached image."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('site_assets', Path(__file__).resolve().parents[1] / 'scripts/cache_site_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class SiteAssets(unittest.TestCase):
    def test_includes_secondary_logos_and_players_outside_leaderboard(self):
        paths = assets.asset_paths({'standings': [{'logo': 'https://assets.nhle.com/logos/nhl/svg/WSH_secondary_light.svg'}],
                                    'heads': {'Reserve Player': '20262027/WSH/1234', 'bad': '../unsafe'}})
        self.assertIn('logos/nhl/svg/WSH_secondary_dark.svg', paths)
        self.assertIn('mugs/nhl/20262027/WSH/1234.png', paths)
        self.assertFalse(any('unsafe' in p for p in paths))

    def test_cached_portrait_is_bundled_without_upstream_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = 'mugs/nhl/20262027/WSH/1234.png'
            cached = root / 'cache' / relative
            cached.parent.mkdir(parents=True)
            cached.write_bytes(b'\x89PNG\r\n\x1a\nexisting portrait')
            with patch.object(assets, 'CACHE', root / 'cache'), patch.object(assets, 'DEST', root / 'site'), \
                    patch.object(assets.urllib.request, 'urlopen', side_effect=AssertionError('upstream blocked')):
                self.assertIsNone(assets.bundle_one(relative))
            self.assertEqual((root / 'site' / relative).read_bytes(), cached.read_bytes())

    def test_error_page_is_not_a_portrait(self):
        self.assertFalse(assets.valid_image(b'<html>Access denied</html>', '.png'))
        self.assertFalse(assets.valid_image(b'<html>Access denied</html>', '.svg'))


if __name__ == '__main__':
    unittest.main()
