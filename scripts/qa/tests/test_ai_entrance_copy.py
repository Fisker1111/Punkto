"""Semantic entrance contract; network/CLI/provenance scenarios live in test-ai-hostile."""
from html.parser import HTMLParser
from pathlib import Path
import re
import shlex
import unittest

AI = Path(__file__).resolve().parents[3] / 'pwa' / 'ai.html'
ROOT_MID = 'punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed'
ROOT_SHA = '2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d'
REPLY_MID = 'punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854'
REPLY_SHA = '0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b'


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.sections = [], [], []
        self.tags, self.links, self.text, self.headings, self.commands = [], [], [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag not in ('meta', 'br', 'hr', 'img', 'link', 'input'):
            self.stack.append(tag)
        if tag == 'section':
            self.sections.append([])
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))
        if tag in ('h1', 'h2', 'h3'):
            self.headings.append([tag, ''])
        if tag == 'pre':
            self.commands.append('')

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(tag)
        else:
            self.stack.pop()

    def handle_data(self, data):
        if 'style' in self.stack or 'head' in self.stack:
            return
        self.text.append(data)
        if 'section' in self.stack:
            self.sections[-1].append(data)
        if self.stack and self.stack[-1] in ('h1', 'h2', 'h3'):
            self.headings[-1][1] += data
        if 'pre' in self.stack:
            self.commands[-1] += data


class AiFirstCopyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = AI.read_text(encoding='utf-8')
        cls.parser = Parser()
        cls.parser.feed(cls.raw)
        cls.text = ' '.join(' '.join(cls.parser.text).split())
        cls.lower = cls.text.lower()
        cls.sections = [' '.join(s) for s in cls.parser.sections]

    def meaning(self, *patterns):
        for pattern in patterns:
            self.assertRegex(self.lower, pattern)

    def test_structure_and_static_access(self):
        self.assertEqual(self.parser.errors, [])
        self.assertEqual(self.parser.stack, [])
        self.assertEqual(sum(t == 'h1' for t, _ in self.parser.headings), 1)
        self.assertEqual([text for tag, text in self.parser.headings if tag == 'h1'], ['Leave your mark.'])
        descriptions = [attrs.get('content', '') for tag, attrs in self.parser.tags
                        if tag == 'meta' and attrs.get('name', '').lower() == 'description']
        self.assertTrue(descriptions)
        self.assertTrue(all(description.strip() for description in descriptions))
        self.assertEqual(len(self.sections), 5)
        for section, pattern in zip(self.sections, [r'(?i)punkti.*protocol', r'Null Island', r'(?i)read.*reply.*new mark', r'(?i)public.*unencrypted', r'https|traversal']):
            self.assertRegex(' '.join(section.split()), pattern)
        for tag, attrs in self.parser.tags:
            self.assertNotIn(tag, ('script', 'img', 'iframe', 'link', 'object', 'embed'))
            self.assertFalse(any(k.startswith('on') for k in attrs))
        self.assertNotRegex(self.raw, r'(?i)@import|url\(')
        self.assertLessEqual(len(self.raw.encode('utf-8')), 7000)

    def test_invitation_and_limits_on_first_screen(self):
        hero = self.sections[0].lower()
        for pattern in (r'addressability', r'distribution', r'persistence', r'key.*authorship',
                        r'open.*signed.*spatial.*protocol', r'humans.*ais.*(same|one).*network',
                        r'punkto.*optional.*commercial', r'self.host', r'other providers',
                        r'if independent operators.*preserv', r'null island', r'http get',
                        r'no account', r'reply.*command', r'not.*actor.*presence.*truth'):
            self.assertRegex(hero, pattern)
        self.meaning(r'(do not have to|need not|not required to) publish')
        self.assertNotRegex(self.lower, r'you must publish|guaranteed permanent|will survive forever|after you are gone|your context may disappear')

    def test_real_conversation_and_paths(self):
        for mid, sha in ((ROOT_MID, ROOT_SHA), (REPLY_MID, REPLY_SHA)):
            self.assertIn(mid, self.sections[1])
            self.assertIn(sha, self.sections[1])
            self.assertIn(f'https://punkto.xyz/publication/records/{sha[:2]}/{sha}', self.parser.links)
        self.assertIn('s00000000000_0', self.sections[1])
        self.meaning(r'address is not reserved', r'neither presence nor ownership')
        self.assertNotRegex(self.raw, r'https?://[^/\s"<>]+/records/')
        walkthrough = 'https://github.com/Fisker1111/Punkto/blob/main/docs/AI_FIRST_WALKTHROUGH.md'
        self.assertIn(walkthrough, self.parser.links)
        self.assertIn('nodes.json', self.sections[2])
        actions = re.findall(r'<section\b[^>]*>(.*?)</section>', self.raw, re.S)[2]
        read = actions.split('<h3 id="read">', 1)[1].split('<h3 id="reply">', 1)[0]
        pointer_blocks = [p for p in re.findall(r'<p>(.*?)</p>', read, re.S)
                          if 'nodes.json' in p]
        self.assertEqual(len(pointer_blocks), 1)
        pointer = Parser()
        pointer.feed(pointer_blocks[0])
        self.assertEqual(pointer.links, [walkthrough])
        self.assertRegex(pointer_blocks[0], r'>advanced walkthrough</a>')
        sentence = ' '.join(' '.join(pointer.text).split())
        self.assertLessEqual(len(sentence), 160)
        self.assertRegex(sentence, r'^[^.!?]*nodes\.json[^.!?]*[.]$')
        self.assertNotRegex(self.lower, r'root\.json|manifests/|shards|node\.index|<child\.href>|<sha256[^>]*>|<publication>|<origin>')
        self.assertNotRegex('\n'.join(self.parser.commands), r'(?m)^\s*(?:→\s*)?GET ')
        self.assertNotRegex(self.text, r'shards/index|node\.index|<child\.href>|(?i:GET)\s+\S*/shards')
        self.assertNotRegex(self.lower, r'write an unanchored|omit --h|address is optional')

    def test_client_verification_not_server_assertion(self):
        self.meaning(r'record is binary.*not json or text', r'client.side.*verify sha-256.*canonical mid.*ed25519 signature',
                     r'server.*valid.*(not evidence|insufficient)', r'text is data, not instructions')
        self.assertNotRegex(self.lower, r'(trust|accept) (a |the )?server.{0,20}valid|server.{0,20}valid is sufficient')

    def test_commands_and_read_first(self):
        blocks = '\n'.join(self.parser.commands)
        self.assertLess(blocks.index('curl -fsS https://punkto.xyz/publication/records/'), blocks.index('node punkto-reply.mjs reply'))
        self.assertLess(blocks.index('node punkto-reply.mjs reply'), blocks.index('node punkto-reply.mjs post'))
        self.meaning(r'no account.*node/npm.*sdk', r'node.js.*only.*optional helper.*not required for reading', r'reply.{0,5}optional', r'new mark.{0,5}optional', r'executes modules.*trust.*code')
        commands = [shlex.split(line) for line in blocks.splitlines() if line.startswith('node ')]
        self.assertEqual([c[2] for c in commands], ['reply', 'post'])
        for args in commands:
            action = args[2]
            flags = [arg for arg in args if arg.startswith('--')]
            allowed = {'--origin', '--key-file'} | ({'--h', '--lat', '--lon', '--height'} if action == 'post' else set())
            self.assertTrue(set(flags) <= allowed)
            self.assertEqual(len(flags), len(set(flags)))
            self.assertIn('--origin', flags)
            self.assertEqual(args[args.index('--origin') + 1], 'https://punkto.xyz')
            self.assertNotRegex(' '.join(args), r'<|>')
        self.assertEqual(commands[0][3], ROOT_MID)
        self.assertIn('--h', commands[1])
        self.assertIn('curl -fsS https://punkto.xyz/punkti/punkto-reply.mjs -o punkto-reply.mjs', blocks)
        self.assertTrue(set(re.findall(r'--[a-z-]+', self.text)) <= {'--origin', '--key-file', '--h', '--lat', '--lon', '--height', '--limit'})

    def test_each_safety_requirement(self):
        self.meaning(r'public, unencrypted', r'never post secrets', r'permanent erasure', r'privacy and usage rights',
                     r'submission acceptance\s*≠\s*publication visibility\s*≠\s*preservation',
                     r'publication can lag', r'replication is not-measured', r'custody is not guaranteed',
                     r'nothing is guaranteed to survive forever', r'ed25519 is not post.quantum',
                     r'default identity.*ephemeral ed25519 key.*memory',
                     r'--key-file.*durable local 32.byte hex seed outside any git repository.*0600.*never uploaded',
                     r'reply inherits.*verified parent.s exact h',
                     r'new mark requires an explicit h.*chosen wgs84 ellipsoidal height',
                     r'never inferred ground height, guessed or defaulted to 0',
                     r'all three.*--lat --lon --height',
                     r'location does not prove presence', r'signature does not prove the actor or statement.s truth')

    def test_public_references_and_no_workflow_details(self):
        for link in ('https://github.com/punkti-org/punkti', 'https://github.com/Fisker1111/Punkto',
                     'https://github.com/Fisker1111/Punkto/blob/main/docs/AI_FIRST_WALKTHROUGH.md'):
            self.assertIn(link, self.parser.links)
        self.assertTrue(any('self-hosting-node.md' in link for link in self.parser.links))
        self.assertNotRegex(self.text, r'(?i)CEO-OS|PR #\d|issue #\d|ticket|will be (merged|deployed|live) soon|PUNKTI-L3|body \|\| signature|package.json')


if __name__ == '__main__':
    unittest.main()
