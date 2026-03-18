#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import logging
import unittest
from pathlib import Path

from bs4 import BeautifulSoup


MODULE_PATH = Path(__file__).with_name("gtfobins_scraper.py")


def load_scraper_module():
    spec = importlib.util.spec_from_file_location("gtfobins_scraper", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GTFOBinsScraperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_scraper_module()

    def setUp(self):
        logger = logging.getLogger("gtfobins_scraper_test")
        logger.handlers = []
        logger.propagate = False
        logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL)
        self.scraper = self.module.GTFOBinsScraper(logger=logger)

    def test_parse_executable_from_api_resolves_alias_and_context_metadata(self):
        payload = {
            "functions": {
                "shell": {
                    "label": "Shell",
                    "description": "Spawn shell.",
                    "mitre": ["T1059"],
                    "extra": {
                        "listener": {
                            "tcp-server": {
                                "comment": "Listen locally.",
                                "code": "nc -l -p 12345",
                            }
                        }
                    },
                }
            },
            "contexts": {
                "sudo": {
                    "label": "Sudo",
                    "description": "Run with sudo.",
                    "extra": {"environment": "Need env."},
                },
                "suid": {
                    "label": "SUID",
                    "description": "Run as suid.",
                    "extra": {
                        "shell": {
                            "true": "Shell note true",
                            "false": "Shell note false",
                        }
                    },
                },
                "capabilities": {
                    "label": "Capabilities",
                    "description": "Requires capabilities.",
                    "extra": {"list": "Needs capabilities:"},
                },
            },
            "executables": {
                "demo": {
                    "comment": "Demo comment.",
                    "functions": {
                        "shell": [
                            {
                                "code": "demo",
                                "contexts": {
                                    "sudo": None,
                                    "suid": {"code": "demo -p", "shell": False},
                                },
                                "listener": "tcp-server",
                            },
                            {
                                "code": "demo-cap",
                                "contexts": {"capabilities": {"list": ["CAP_SETUID"]}},
                            },
                        ]
                    },
                },
                "alias-demo": {"alias": "demo"},
            },
        }

        item = self.scraper.parse_executable_from_api(
            "demo",
            payload["executables"]["demo"],
            payload["functions"],
            payload["contexts"],
            payload["executables"],
        )
        alias_item = self.scraper.parse_executable_from_api(
            "alias-demo",
            payload["executables"]["alias-demo"],
            payload["functions"],
            payload["contexts"],
            payload["executables"],
        )

        self.assertEqual(item["functions"][0]["contexts"], ["Sudo", "SUID", "Capabilities"])
        self.assertEqual(
            item["functions"][0]["examples"][0]["contexts"][1]["notes"],
            ["Shell note false"],
        )
        self.assertEqual(
            item["functions"][0]["examples"][1]["contexts"][0]["notes"],
            ["Needs capabilities: CAP_SETUID"],
        )
        self.assertEqual(
            item["functions"][0]["examples"][0]["references"][0]["code"],
            "nc -l -p 12345",
        )
        self.assertEqual(alias_item["alias"], "demo")
        self.assertEqual(alias_item["alias_chain"], ["demo"])
        self.assertEqual(alias_item["functions"][0]["code_examples"], ["demo", "demo -p", "demo-cap"])

    def test_parse_binary_list_page_extracts_binary_names(self):
        html = """
        <table id="gtfobin-table">
          <tbody>
            <tr><th><a href="/gtfobins/bash/" class="bin-name">bash</a></th></tr>
            <tr><th><a href="/gtfobins/awk/" class="bin-name">awk</a></th></tr>
          </tbody>
        </table>
        """
        soup = BeautifulSoup(html, self.scraper.html_parser)
        self.assertEqual(self.scraper.parse_binary_list_page(soup), ["bash", "awk"])

    def test_parse_binary_page_extracts_functions_contexts_and_references(self):
        html = """
        <html>
          <body>
            <h1><div><a href="/">..</a> / awk</div></h1>
            <p>This is an alias of <a href="/gtfobins/mawk/"><code>mawk</code></a>.</p>
            <ul class="tag-list"></ul>

            <h2 id="shell" class="function-name">Shell</h2>
            <p>This executable can spawn an interactive system shell.</p>
            <ul class="examples">
              <li>
                <fieldset>
                  <legend>Comment</legend>
                  <p>Interactive only.</p>
                </fieldset>
                <div class="contexts">
                  <label>Unprivileged</label>
                  <div>
                    <p>This function can be performed by any unprivileged user.</p>
                    <pre><code>awk 'BEGIN {system("/bin/sh")}'</code></pre>
                  </div>
                  <label>Sudo</label>
                  <div>
                    <p>This function is performed by the privileged user.</p>
                    <fieldset>
                      <legend>Remarks</legend>
                      <p>Preserve environment values.</p>
                    </fieldset>
                    <pre><code>sudo awk 'BEGIN {system("/bin/sh")}'</code></pre>
                  </div>
                </div>
                <fieldset>
                  <legend>Listener</legend>
                  <p>Listen remotely.</p>
                  <pre><code>nc -l -p 12345</code></pre>
                </fieldset>
              </li>
            </ul>
          </body>
        </html>
        """

        soup = BeautifulSoup(html, self.scraper.html_parser)
        item = self.scraper.parse_binary_page(soup, "awk", "https://gtfobins.org/gtfobins/awk/")

        self.assertEqual(item["alias"], "mawk")
        self.assertIn("Alias of", item["description"])
        self.assertEqual(len(item["functions"]), 1)
        self.assertEqual(item["functions"][0]["name"], "Shell")
        self.assertEqual(item["functions"][0]["contexts"], ["Unprivileged", "Sudo"])
        self.assertEqual(
            item["functions"][0]["examples"][0]["contexts"][1]["notes"][0]["label"],
            "Remarks",
        )
        self.assertEqual(
            item["functions"][0]["examples"][0]["references"][0]["code"],
            "nc -l -p 12345",
        )
        self.assertIn("awk 'BEGIN {system(\"/bin/sh\")}'", item["examples"])
        self.assertIn("nc -l -p 12345", item["examples"])


if __name__ == "__main__":
    unittest.main()
