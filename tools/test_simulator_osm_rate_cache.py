"""Regression checks for bounded OSM downloads and external tile reuse."""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import simulator_osm_road_graph as roads


class Response:
    def __init__(self, raw):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.raw[:limit]


class RoadCacheTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = patch.object(roads, "CACHE_DIR", Path(self.temp.name))
        self.cache.start()
        self.addCleanup(self.cache.stop)
        roads._RATE_LIMIT_UNTIL = 0

    def test_successful_xml_reused_without_network(self):
        bbox = (17.1, 48.1, 17.11, 48.11)
        raw = b'<osm version="0.6"><node id="1" lat="48.1" lon="17.1"/></osm>'
        with patch.object(roads, "urlopen", return_value=Response(raw)) as net:
            self.assertEqual(roads.download(bbox), [(bbox, raw)])
            self.assertEqual(roads.download(bbox), [(bbox, raw)])
            self.assertEqual(net.call_count, 1)
        self.assertTrue(roads._tile_paths(bbox)[0].is_file())

    def test_509_sets_cooldown_without_repeating_request(self):
        bbox = (17.2, 48.2, 17.21, 48.21)
        def limited(*_args, **_kwargs):
            raise HTTPError(roads.API, 509, "Bandwidth Limit Exceeded",
                            {}, io.BytesIO(b"Please try again in 30 seconds."))
        with patch.object(roads, "urlopen", side_effect=limited) as net:
            with self.assertRaises(roads.OsmRateLimit) as first:
                roads.download(bbox)
            self.assertEqual(first.exception.retry_after_s, 30)
            with self.assertRaises(roads.OsmRateLimit):
                roads.download(bbox)
            self.assertEqual(net.call_count, 1)


if __name__ == "__main__":
    unittest.main()
