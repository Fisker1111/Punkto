"""Deterministic adversarial inputs and evidence; never implements validation policy."""
import base64
from collections import Counter
from copy import deepcopy
import hashlib
import json
import struct
import zlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from hostile.harness import HOME, ROOT

ROWS = {}
KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
S = 'INVALID-structural'
P = 'INVALID-provenance'
V = 'VALID'
U = 'UNVERIFIABLE-alg'
L = 'ResourceLimit'

def b64(raw):
    return base64.b64encode(raw).decode()

def lp(raw):
    return struct.pack('>I', len(raw)) + raw

def body(a):
    # Fixture encoder only: deliberately permits forbidden values. Production
    # canonicalization/validation is always exercised independently afterward.
    return b''.join(lp(str(a[k]).encode('utf-8')) for k in ('v','t','h','x','alg')) + lp(base64.b64decode(a['pk'])) + struct.pack('>I', len(a['refs'])) + b''.join(lp(r[k].encode()) for r in a['refs'] for k in ('target','rel')) + lp(base64.b64decode(a['ext']))

def atom(**updates):
    a = dict(v='punkti/0.6', t=0, h='gggh00000000', x='hostile', alg='ed25519',
             pk=b64(KEY.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)), refs=[], ext='', sig='')
    a.update(updates)
    a['sig'] = b64(KEY.sign(b'PUNKTI-L3-SIGN\0' + body(a)))
    return a

def wire(a):
    return lp(body(a)) + lp(base64.b64decode(a['sig']))

def dumps(a):
    return json.dumps(a, ensure_ascii=True, separators=(',', ':')).encode()

def exact(raw):
    if not isinstance(raw, bytes):
        raw = dumps(raw)
    if len(raw) <= 4096:
        return {'hex': raw.hex(), 'length': len(raw)}
    return {'zlib_base64': b64(zlib.compress(raw, 9)), 'length': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def row(group, case, kind, expected, observed, admitted=None, classification='AGREE', note='', raw=b''):
    assert classification in ('AGREE', 'DIVERGE', 'DEFECT')
    ROWS[group, case, kind] = dict(group=group, case=case, implementation=kind,
        expected_state=expected, observed_state=observed, admitted=admitted,
        classification=classification, note=note, input=exact(raw))

def report(group):
    rows = sorted(ROWS.values(), key=lambda r:(r['group'],r['case'],r['implementation']))
    counts = {k:dict(Counter(r['classification'] for r in rows if r['implementation']==k)) for k in ('ref','nb')}
    classes = {g:len({r['case'] for r in rows if r['group']==g}) for g in sorted({r['group'] for r in rows})}
    (HOME/'evidence/protocol.json').write_text(json.dumps(dict(schema=1, counts=counts, cases_per_class=classes, rows=rows), indent=2, sort_keys=True)+'\n')
    print('\n'+group+' | implementation | AGREE | DIVERGE | DEFECT')
    for k in ('ref','nb'):
        c=Counter(r['classification'] for r in rows if r['group']==group and r['implementation']==k)
        print(f'{group} | {k} | {c["AGREE"]} | {c["DIVERGE"]} | {c["DEFECT"]}')

def envelope_cases():
    cases=[]
    def add(name, raw, expected, pins=None, mode='json'):
        cases.append(dict(name=name, raw=raw, expected=expected, pins=pins or dict(ref=expected,nb=expected), mode=mode))
    def mutate(name, field, value, expected=S):
        a=atom(); a[field]=value; add(name,dumps(a),expected)
    def signed(name, expected=V, **values):
        add(name,dumps(atom(**values)),expected)
    raw=dumps(atom())
    add('duplicate-key',raw[:-1]+b',"t":0}',S)
    mutate('extra-field','extra',0)
    a=atom(); del a['x']; add('missing-field',dumps(a),S)
    for n,v in [('case','PUNKTI/0.6'),('space','punkti/0.6 '),('number',6)]: mutate('v-'+n,'v',v)
    for n,v in [('negative',-1),('string','1'),('bool',True),('overflow',2**53)]: mutate('t-'+n,'t',v)
    for n,v in [('negative-zero',b'-0'),('float',b'1.0'),('exponent',b'1e3'),('fraction',b'0.5'),('leading-zero',b'01')]:
        add('t-'+n,raw.replace(b'"t":0',b'"t":'+v), S)
    signed('t-max',t=2**53-1); signed('t-zero'); add('json-whitespace',b' \n'+raw+b'\t ',V)
    for n,h in [('11','g'*11),('13','g'*13),('uppercase','G'*12)]+[(c,c*12) for c in 'ailo']: mutate('h-'+n,'h',h)
    signed('h-empty',h=''); signed('h-valid',h='g'*12)
    for n,a in [('empty',''),('129','q'*129),('unicode','é')]: mutate('alg-'+n,'alg',a)
    for n,a in [('128','q'*128),('NUL','future\0x'),('uppercase','ED25519'),('space','ed25519 ')]: signed('alg-'+n,U,alg=a)
    for f in ('pk','sig','ext'):
        for n,v in [('padding','YQ='),('trailing-bits','YR=='),('whitespace','Y Q=='),('urlsafe','_w==')]: mutate(f+'-'+n,f,v)
    mutate('pk-empty','pk',''); mutate('sig-empty','sig',''); signed('ext-empty')
    for f,lengths in [('pk',(31,33)),('sig',(63,65))]:
        for length in lengths: mutate(f+'-'+str(length),f,b64(bytes(length)))
    mutate('refs-not-array','refs',{})
    signed('refs-257',L,refs=[dict(target='future:ab',rel='')]*257)
    for n,r in [('missing-rel',dict(target='future:ab')),('extra',dict(target='future:ab',rel='',extra=1)),('uppercase',dict(target='future:AB',rel='')),('odd',dict(target='future:a',rel='')),('namespace-129',dict(target='a'*129+':ab',rel=''))]: mutate('refs-'+n,'refs',[r])
    signed('refs-unknown-namespace',refs=[dict(target='future:ab',rel='')])
    signed('refs-rel-1024',refs=[dict(target='future:ab',rel='r'*1024)])
    signed('refs-rel-1025',L,refs=[dict(target='future:ab',rel='r'*1025)])
    mutate('x-surrogate','x','\ud800')
    for n,x in [('NUL','\0'),('emoji','😀'),('NFC','é'),('NFD','e\u0301')]: signed('x-'+n,x=x)
    overhead=len(body(atom(x='')))
    signed('body-exact-1MiB',x='a'*(2**20-overhead))
    signed('body-1MiB-plus-1',L,x='a'*(2**20-overhead+1))
    add('json-non-UTF8',raw.replace(b'hostile',b'\xff'),S)
    r=wire(atom()); c=body(atom())
    for n,r2,e in [('truncated-C',r[:20],S),('trailing-R',r+b'\0',S),('long-prefix',struct.pack('>I',len(r)+1)+r[4:],S),('zero-signature',lp(c)+lp(b''),S),('R-exact-2MiB',lp(body(atom(alg='future')))+lp(b'a'*(2**21-8-len(body(atom(alg='future'))))),U),('R-over-2MiB',b'\0'*(2**21+1),L),('C-over-1MiB',lp(b'a'*(2**20+1))+lp(b'a'),L)]: add(n,r2,e,mode='wire')
    return cases


def classify(carrier, kind, case):
    try:
        raw=case['raw']
        if case['mode']=='json':
            imported=carrier.import_json(raw)
            raw=imported if kind=='ref' else imported.R
        result=carrier.validate(raw)
        return result.state.value,raw
    except (carrier.ResourceLimit if kind=='ref' else carrier.ResourceError):
        return L,None
    except (ValueError,UnicodeError):
        return S,None
