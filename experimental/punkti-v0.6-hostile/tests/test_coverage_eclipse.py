"""Coverage is an advertisement, never a proof of a peer's retained set."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import socket
import subprocess
import sys
import threading
import unittest
from urllib.parse import urlencode
from hostile.cases_protocol import *
from hostile.harness import Runner, Adapter, http, item


def tearDownModule(): report('E-coverage')

@contextmanager
def endpoint(handler):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def handle_request(self):
            raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
            code,result=handler(self.command,self.path,raw)
            raw=dumps(result)
            self.send_response(code); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        do_GET=do_POST=handle_request
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True); thread.start()
    try: yield 'http://127.0.0.1:'+str(server.server_port)
    finally: server.shutdown(); server.server_close(); thread.join()

class Coverage(unittest.TestCase):
    def test_hello_and_narrow_push(self):
        for k in ('ref','nb'):
            with Runner('hello',k) as r:
                a=r.node(); b=Adapter(k,dict(subscriptions=[dict(xy_lo='g',xy_hi='h')],peers=[])); r.nodes.append(b)
                inside=r.seed(a,10000,2)
                outside=r.call(a,'add',spec=dict(seed='outside',t=0,h='s00000000000_23',x='outside',refs=[],ext=''))
                code,hello=http(b.url,'/hello'); self.assertEqual(code,200)
                self.assertEqual(hello['subscriptions'],[dict(xy_lo='g',xy_hi='h',z_min=None,z_max=None)])
                self.assertEqual(hello['capabilities'],['push','range-mid','range-spatial','opaque-wrapper'])
                p=r.proxy(b); r.call(a,'push_to',peer=p.url); r.equal([b],inside)
                p.idle(); sent=[w for e in p.exchanges if e['path']=='/push' for w in json.loads(e['request'].split(b'\r\n\r\n',1)[1])['records']]
                self.assertEqual(sent,list(map(item,inside)))
                row('E-coverage','narrow-advertisement',k,2,len(sent),True,raw=dumps(dict(subscriptions=hello['subscriptions'],records=list(map(item,inside+[outside])))))
                expected_limits={'body':1048576,'record':2097152,'page':32,'http':8388608,'candidates':128}
                self.assertEqual(hello['limits'],expected_limits)
                row('E-coverage','hello-limit-schema',k,expected_limits,hello['limits'],classification='AGREE',raw=b'GET /hello',note='The spec now defines the five required core limit names and units.')
    def test_stale_coverage_and_drop_after(self):
        for k in ('ref','nb'):
            with Runner('stale',k) as r:
                source=r.node(); receiver=r.node(); records=r.seed(source,10100,40)
                # First demonstrate the literal part-1 fault: every fourth response
                # is lost, but all forty actual upstream admissions happen.
                p=r.proxy(receiver); p.plan(['drop_after' if i%4==3 else 'pass' for i in range(40)])
                lost=0
                for m in records:
                    try: code,result=http(p.url,'/push',dict(records=[item(m)])); self.assertEqual(code,200)
                    except OSError: lost+=1
                self.assertEqual(lost,10); self.assertEqual(p.stats()['drop_after'],10); r.equal([receiver],records)
                row('E-coverage','drop-after-is-not-withholding',k,[40,10,40],[40,lost,len(r.state(receiver)['valid'])],True,raw=dumps(list(map(item,records))),note='Selected request indices 3,7,...,39 (zero-based). drop_after suppresses acknowledgments after admission; cannot imply 25% missing records.')
                target=r.node(); counter=[0]
                def dishonest(method,path,raw):
                    if path=='/hello': return http(target.url,path)
                    if path=='/push':
                        i=counter[0]; counter[0]+=1
                        if i%4==3: return 200,dict(results=[dict(state=V,admitted=True)])
                        return http(target.url,path,raw)
                    raise AssertionError(path)
                with endpoint(dishonest) as url:
                    # Composition: malicious peer withholds admissions, while the
                    # unmodified part-1 proxy drops the selected acknowledgments.
                    from hostile.faultproxy import FaultProxy
                    proxy=FaultProxy(url); r.proxies.append(proxy)
                    proxy.plan(['drop_after' if i%4==3 else 'pass' for i in range(40)])
                    lost=0
                    for m in records:
                        try: http(proxy.url,'/push',dict(records=[item(m)]))
                        except OSError: lost+=1
                    self.assertEqual(lost,10); self.assertEqual(proxy.stats()['drop_after'],10)
                    r.equal([target],[m for i,m in enumerate(records) if i%4!=3])
                    before=len(r.state(target)['valid']); self.assertEqual(before,30)
                    code,hello=http(proxy.url,'/hello'); self.assertEqual(hello['subscriptions'],[dict(xy_lo=None,xy_hi=None,z_min=None,z_max=None)])
                    _,bounded=http(target.url,'/pull?'+urlencode({'q':'{}'})); self.assertTrue(bounded['end']); self.assertNotIn('complete',bounded)
                    self.assertTrue(r.pull(target,source.url)['ok']); r.equal([target],records)
                    row('E-coverage','stale-advertisement-withholding-quarter',k,[40,30,10,40],[counter[0],before,lost,len(r.state(target)['valid'])],True,raw=dumps(list(map(item,records))),note='Malicious endpoint acknowledges without retaining indices 3,7,...,39; FaultProxy drops those responses. Explicit pull recovers ten; end is bounded-view only.')
    def test_selective_withholding(self):
        for k in ('ref','nb'):
            with Runner('selective',k) as r:
                w=r.node(); reader=r.node(); records=r.seed(w,10200,50)
                _,first=http(w.url,'/pull?'+urlencode({'q':json.dumps(dict(limit=30))}))
                hidden=deepcopy(first); hidden['end']=True; hidden['cursor']['after']=hidden['cursor']['ceiling']
                accesses=[]
                def withholding(method,path,raw):
                    accesses.append(path.split('?')[0])
                    if path=='/hello': return http(w.url,path)
                    if path.startswith('/pull?'): return 200,hidden
                    raise AssertionError(path)
                with endpoint(withholding) as url:
                    r.call(reader,'configure',peers=[url]); self.assertTrue(r.pull(reader,url)['ok'])
                    r.equal([reader],records[:30]); self.assertEqual(len(r.state(w)['valid']),50)
                    self.assertNotIn('complete',r.call(reader,'hello')); self.assertNotIn('complete',hidden)
                    self.assertEqual(accesses.count('/pull'),1)
                    self.assertTrue(r.pull(reader,w.url)['ok']); r.equal([reader],records)
                    row('E-coverage','selective-50-30-recovery',k,[50,30,20,50],[50,len(hidden['records']),50-len(hidden['records']),len(r.state(reader)['valid'])],True,raw=dumps(list(map(item,records))),note='Configured malicious facade emits end=true at 30; no completeness field exists. Direct pull of actual W recovers remaining 20.')
    def test_discovery_hints_and_poison(self):
        # Listening sockets are outbound tripwires. All 500 remain unreadable:
        # TCP connection attempts would make accept() ready, even without HTTP.
        sockets=[]
        import select
        try:
            for _ in range(500):
                s=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(); sockets.append(s)
            hints=['http://127.0.0.1:'+str(s.getsockname()[1]) for s in sockets]
            for k in ('ref','nb'):
                mode=['valid']; calls=[]
                def malicious(method,path,raw):
                    calls.append(path)
                    if mode[0]=='poison': return 200,{'message':'ordinary HTTP server'}
                    return 200,dict(protocol='punkti-mesh/0.6-draft',epoch='fixed-malicious',subscriptions=[{}],peers=hints,capabilities=[])
                with endpoint(malicious) as url:
                    proc=subprocess.Popen([sys.executable,str(HOME/'src/hostile/discovery_probe.py'),k,url],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    try:
                        for poison in (False,True):
                            mode[0]='poison' if poison else 'valid'
                            proc.stdin.write('"discover"\n'); proc.stdin.flush()
                            self.assertTrue(select.select([proc.stdout],[],[],15)[0]); result=json.loads(proc.stdout.readline())
                            self.assertTrue(result['peers_unchanged']); self.assertEqual([result[x] for x in ('valid','candidates','log')],[0,0,0])
                            self.assertEqual(select.select(sockets,[],[],0)[0],[])
                            # Actual public HTTP request verifies child server remains alive.
                            self.assertEqual(http(result['url'],'/hello')[0],200)
                            if not poison:
                                self.assertEqual(result['hints'],sorted(hints)); self.assertEqual(result['state'],'returned')
                                row('E-coverage','500-hints-no-crawl',k,[500,0,0,True],[len(result['hints']),len(select.select(sockets,[],[],0)[0]),result['valid'],result['peers_unchanged']],raw=dumps(dict(peers=['http://127.0.0.1:<tripwire-'+str(i)+'>' for i in range(500)])),note='500 unique live accept tripwires; no socket accepted, no peer-set mutation; only explicitly configured peer contacted.')
                            else:
                                self.assertEqual(result['state'],'returned'); self.assertEqual(result['hints'],[])
                                row('E-coverage','poisoned-nonimplementation-hint',k,dict(state='returned',hints=[],alive=True),dict(state=result['state'],hints=result['hints'],alive=True),False,'AGREE',raw=b'{"message":"ordinary HTTP server"}',note='The spec now defines malformed discovery hellos as skipped; node alive and store unchanged.')
                        self.assertEqual(calls,['/hello','/hello'])
                    finally:
                        if proc.poll() is None:
                            proc.stdin.write('"stop"\n'); proc.stdin.flush()
                        try: proc.wait(timeout=5)
                        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                        errors=proc.stderr.read(); proc.stdin.close(); proc.stdout.close(); proc.stderr.close()
                    self.assertEqual(proc.returncode,0,errors)
        finally:
            for s in sockets: s.close()
