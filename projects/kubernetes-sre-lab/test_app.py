import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from app import Handler


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=3) as response:
            return response.status, response.read(), response.headers

    def test_health_and_readiness(self):
        for path in ("/healthz", "/readyz"):
            status, body, _ = self.get(path)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["status"], "ok")

    def test_metrics_increase(self):
        def count():
            text = self.get("/metrics")[1].decode()
            return int(next(x.split()[1] for x in text.splitlines() if x.startswith("demo_http_requests_total ")))
        before = count()
        self.get("/")
        self.assertGreater(count(), before)

    def test_unknown_route(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.get("/missing")
        self.assertEqual(error.exception.code, 404)

    def test_root_content_type_and_version(self):
        _, body, headers = self.get("/")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(body)["service"], "platform-demo")


if __name__ == "__main__":
    unittest.main()
