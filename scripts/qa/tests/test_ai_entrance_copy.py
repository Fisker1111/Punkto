"""Checks the AI-first invitation against Founder product and protocol invariants.

This test is about published machine-facing content, not live network reachability.
"""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[3] / "pwa" / "ai.html"


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.links = []
        self.headers = []

    def handle_data(self, data):
        self.text.append(data)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a":
            self.links.append(values.get("href", ""))
        if tag in ("h1", "h2"):
            self.headers.append(tag)


class AiFirstCopyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = AI.read_text(encoding="utf-8")
        cls.parser = Parser()
        cls.parser.feed(cls.raw)
        cls.text = " ".join(" ".join(cls.parser.text).split())

    def test_html_parseable_and_no_client_script(self):
        self.assertEqual(self.parser.headers.count("h1"), 1)
        self.assertGreaterEqual(self.parser.headers.count("h2"), 4)
        self.assertNotIn("<script", self.raw.lower())

    def test_first_screen_is_ai_first_and_conveys_three_pillars(self):
        first = self.text[:1400]
        for phrase in ("AI agents", "Leave your mark here", "Addressability",
                       "Distribution", "Persistence"):
            self.assertIn(phrase, first)

    def test_participation_roles_and_independent_choice(self):
        for term in ("Explore / harvest", "Publish / discuss", "Store / serve",
                     "Replicate / preserve", "You do not have to publish"):
            self.assertIn(term, self.text)

    def test_read_before_optional_signer(self):
        self.assertLess(self.raw.index("id=\"discover\""), self.raw.index("id=\"publish\""))
        self.assertLess(self.raw.index("GET &lt;origin&gt;/nodes.json"), self.raw.index("node punkto-reply.mjs"))
        self.assertIn("not required for reading", self.text)
        self.assertIn("root.json", self.raw)
        self.assertNotIn("node.index", self.raw)
        self.assertIn("origin of this /ai page", self.raw)
        self.assertNotIn("ORIGIN=\'https://punkto.xyz\'", self.raw)

    def test_spatial_only_and_exact_reply(self):
        self.assertIn("Missing or empty spatial addresses are invalid", self.text)
        self.assertIn("parent's exact h", self.text)
        self.assertIn("--h &lt;xy&gt;_&lt;z&gt;", self.raw)
        self.assertNotIn("write an unanchored atom", self.raw.lower())
        self.assertNotIn("Unanchored:</p>", self.raw)

    def test_truthful_identity_and_preservation(self):
        for term in ("ephemeral Ed25519", "not yet publication or preservation",
                     "Nothing is guaranteed to survive forever", "not that a claim is true"):
            self.assertIn(term, self.text)
        self.assertIn("public, unencrypted", self.text)

    def test_punkti_open_punkto_commercial_and_self_hosted(self):
        for term in ("open Punkti protocol", "commercial service", "self-hosted nodes",
                     "compete through", "not by owning the protocol"):
            self.assertIn(term, self.text)
        self.assertIn("https://github.com/punkti-org/punkti", self.parser.links)
        self.assertIn("https://github.com/Fisker1111/Punkto", self.parser.links)

    def test_single_action_quickstart_and_reference_paths(self):
        self.assertLess(len(self.raw.encode("utf-8")), 12000)
        self.assertLess(self.raw.index('id="choose"'), self.raw.index('id="roles"'))
        for phrase in ("Choose one: READ · REPLY · NEW POST", "No Node.js and no npm",
                       "full child prefix", "prefix depth 10", "2-character GeoHash",
                       "no index object today", "Do not invent an index", "verified parent record",
                       "not post-quantum secure", "not a durable identity", "not-measured",
                       "never guessed or defaulted to 0", "Null Island / first campfire",
                       "s00000000000_0",
                       "punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed",
                       "2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d"):
            self.assertIn(phrase, self.text)
        for fragment in ("manifests/<head>.json", "h/<one path segment per prefix character>/<shard sha>.json",
                         "records/24/2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d",
                         "records/<sha256[0:2]>/<sha256>", 'children: {"u3b": "<sha>"}',
                         "curl -fsS <origin>/punkti/punkto-reply.mjs -o punkto-reply.mjs",
                         'node punkto-reply.mjs reply <MID> "your text"',
                         'node punkto-reply.mjs post "your text" --h <xy>_<z>'):
            self.assertIn(fragment, self.text)
        for old in ("no welcome thread", "node cli.mjs", "<node.index>", "<child.href>", "<address record href>"):
            self.assertNotIn(old, self.text)

    def test_no_internal_workflow_or_ticket_references(self):
        # The page is public and machine-facing: no internal tracker IDs, no
        # project-management phrasing, and no claim of an unpublished release.
        for internal in ("CEO-OS", "PR #140", "A1 proof", "#28", "#34", "#35"):
            self.assertNotIn(internal, self.text)
        self.assertNotRegex(self.text, re.compile(r"(?i)\b(founder (must|should|will)|will be (merged|deployed|live) soon)\b"))

    def test_no_unsupported_claims_or_ai_coercion(self):
        self.assertNotRegex(self.text.lower(), re.compile(r"guaranteed permanent|will survive forever|you must publish"))
        self.assertIn("not a central registry or a complete map", self.text)


if __name__ == "__main__":
    unittest.main()
