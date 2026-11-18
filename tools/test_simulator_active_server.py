"""The server exposes one current simulator UI and rejects historical pages."""
import json
import threading
import unittest
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen
from unittest.mock import patch

from simulator_inventory import VIEWER_FILES
from simulator_server import Handler


class LocalAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths=[]

    def handle_starttag(self, tag, attrs):
        for name,value in attrs:
            if name in {"href","src"} and value and value.startswith("/"):
                self.paths.append(urlsplit(value).path.lstrip("/"))


class ActiveServer(unittest.TestCase):
    def test_current_ui_and_rejected_routes(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        base=f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base+"/",timeout=5) as page:
                self.assertEqual(page.geturl(),base+"/simulator.html")
                self.assertIn(b"BP Simul",page.read())
            for route in ("/draft-editor.html", "/leo-reference-packet.html", "/api/legacy/presets"):
                with self.assertRaises(HTTPError) as error:urlopen(base+route,timeout=5)
                self.assertEqual(error.exception.code,404)
            for name in VIEWER_FILES:
                with urlopen(base+"/"+name,timeout=5) as asset:
                    self.assertEqual(asset.status,200)
                    self.assertTrue(asset.read(1),name)
            for page_name in ("simulator.html","technical-parameters.html"):
                parser=LocalAssets()
                with urlopen(base+"/"+page_name,timeout=5) as page:
                    parser.feed(page.read().decode())
                self.assertFalse(set(parser.paths)-VIEWER_FILES)
            with urlopen(base+"/api/simulator/editor/new",timeout=5) as response:
                draft=json.load(response)
                self.assertIn("world",draft)
                self.assertEqual(draft["scenario"]["schema_version"],7)
                self.assertEqual(draft["scenario"]["time_policy"],"ready_at_t0_full_duration")
            with urlopen(base+"/api/simulator/technical-model",timeout=5) as response:
                model=json.load(response)
                self.assertNotIn("service_profiles",model)
                self.assertEqual(model["start_offset_s"],0)
            with self.assertRaises(HTTPError) as error:
                urlopen(base+"/api/simulator/runs/nonexistent-run",timeout=5)
            self.assertEqual(error.exception.code,409)
            with patch("simulator_editor_api.verified_run",return_value={"status":"PASS","plan":{"cars":1}}):
                with urlopen(base+"/api/simulator/runs/audited-run",timeout=5) as response:
                    result=json.load(response)
                    self.assertEqual(result["status"],"complete")
                    self.assertEqual(result["run_id"],"audited-run")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


if __name__=="__main__":unittest.main()
