"""Real encoder/PNG decoder measurements. Never persist private payloads or PNGs."""
import importlib.metadata
import zxingcpp
import base64
import io
import json
import os
import pathlib
import subprocess
import sys
import segno
import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEVELS = 'LMQH'

def encode(data, level, mode, version=None):
    return segno.make(data, error=level, mode=mode, version=version,
                      micro=False, boost_error=False)

def capacity(level, mode):
    lo, hi = 0, 10000
    while lo + 1 < hi:
        n = (lo + hi) // 2
        try:
            encode(b'1' * n, level, mode, 40)
            lo = n
        except segno.DataOverflowError:
            hi = n
    assert encode(b'1' * lo, level, mode, 40).version == 40
    try:
        encode(b'1' * (lo + 1), level, mode, 40)
    except segno.DataOverflowError:
        return lo
    raise AssertionError('capacity boundary')

def measure(case, level, caps):
    data = base64.b64decode(case['data'])
    mode = case['mode']
    row = {k: v for k, v in case.items() if k != 'data'}
    row.update(error_correction=level, payload_bytes=len(data), version=None,
               modules=None, fits=False, decode_cvp2=False, decode_zxingcpp=False, decode_ok=False, decode_result='not encodable',
               shortfall_bytes=max(0, len(data) - caps[mode][level]))
    try:
        qr = encode(data, level, mode)
    except segno.DataOverflowError:
        row['verdict'] = 'INFASIBLE'
        return row
    row.update(fits=True, version=qr.version, modules=len(qr.matrix), verdict='FITS')
    attempts = []
    # Each decoder independently retries at two scales; never short-circuit the other.
    # No decoded bytes, private payloads or PNGs are persisted, including on errors.
    for scale in (5, 9):
        buf = io.BytesIO()
        qr.save(buf, kind='png', scale=scale, border=4)
        png = cv2.imdecode(np.frombuffer(buf.getvalue(), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        for decoder in ('cvp2', 'zxingcpp'):
            key = 'decode_' + decoder
            if row[key]:
                continue
            try:
                if decoder == 'cvp2':
                    decoded, _, _ = cv2.QRCodeDetector().detectAndDecodeBytes(png)
                    ok = decoded == data
                else:
                    results = zxingcpp.read_barcodes(png)
                    ok = any(result.bytes == data for result in results)
                assert ok, 'decoded bytes differ or no payload decoded'
                attempts.append({'decoder': decoder, 'scale': scale, 'ok': True})
                row[key] = True
            except (AssertionError, cv2.error, RuntimeError, ValueError) as exc:
                attempts.append({'decoder': decoder, 'scale': scale, 'ok': False,
                                 'error': type(exc).__name__})
    row['decode_ok'] = row['decode_cvp2'] or row['decode_zxingcpp']
    row['decode_result'] = '; '.join(
        label + (': byte-identical PNG decode' if row[key] else ': no byte-identical decode')
        for label, key in (('cv2', 'decode_cvp2'), ('zxing-cpp', 'decode_zxingcpp')))
    row['decode_attempts'] = attempts
    return row

def markdown(result):
    lines = ['| Mode | v40-L | v40-M | v40-Q | v40-H |', '|---|---:|---:|---:|---:|']
    for mode, levels in result['capacities'].items():
        lines.append('| ' + mode + ' | ' + ' | '.join(str(levels[l]) for l in LEVELS) + ' |')
    lines += ['', '| Algorithm | PK bytes | Sig bytes | PK base64 | PK base32 | Sig base64 | Sig base32 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for s in result['sizes']:
        lines.append('| ' + s['algorithm'] + ' | ' + ' | '.join(str(s[k]) for k in
                     ('public_key','signature','public_key_base64','public_key_base32','signature_base64','signature_base32')) + ' |')
    lines += ['', '| Algorithm | PK + signature | v40-L bytes | Exact shortfall bytes |', '|---|---:|---:|---:|']
    for s in result['sizes']:
        total = s['public_key'] + s['signature']
        lines.append(f"| {s['algorithm']} | {s['public_key']} + {s['signature']} = {total} | {result['capacities']['byte']['L']} | {total - result['capacities']['byte']['L']} |")
    lines += ['', '| Payload | Mode | EC | Raw bytes | Payload bytes | Encoded characters | Version | Modules/side | Verdict | Shortfall bytes | PNG decode |',
              '|---|---|---|---:|---:|---:|---:|---:|---|---:|---|']
    for r in result['cases']:
        lines.append('| ' + ' | '.join(str(r[k]) if r[k] is not None else 'N/A' for k in
            ('name','mode','error_correction','raw_bytes','payload_bytes','encoded_characters','version','modules','verdict','shortfall_bytes','decode_result')) + ' |')
    return '\n'.join(lines) + '\n'

def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--probe':
        n, level = int(sys.argv[2]), sys.argv[3]
        try:
            qr = encode(b'x' * n, level, 'byte', 40)
            print(json.dumps({'fits': True, 'version': qr.version}))
        except segno.DataOverflowError:
            print(json.dumps({'fits': False}))
        return
    caps = {mode: {l: capacity(l, mode) for l in LEVELS} for mode in ('byte','alphanumeric','numeric')}
    print('CAPACITIES ' + json.dumps(caps), flush=True)
    # A dedicated anonymous pipe carries private payloads; stdout is never used.
    read_fd, write_fd = os.pipe()
    proc = subprocess.Popen(['node', str(ROOT / 'tools/payloads.mjs'), '--private-ipc'],
        pass_fds=(write_fd,), env={**os.environ, 'QR_PAYLOAD_FD': str(write_fd)},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(write_fd)
    with os.fdopen(read_fd, 'rb') as stream:
        private_data = stream.read()
    if proc.wait():
        raise RuntimeError('payload generation failed (private output suppressed)')
    payloads = json.loads(private_data)
    rows = []
    for case in payloads['cases']:
        for level in LEVELS:
            row = measure(case, level, caps)
            rows.append(row)
            print(f"{row['name']} {level}: {row['verdict']} shortfall={row['shortfall_bytes']} bytes decode={row['decode_result']}", flush=True)
    result = {'encoder': 'segno ' + segno.__version__, 'decoders': {'cvp2': 'OpenCV ' + cv2.__version__,
                           'zxingcpp': 'zxing-cpp ' + importlib.metadata.version('zxing-cpp')},
              'python': sys.version.split()[0], 'capacities': caps, 'sizes': payloads['sizes'], 'cases': rows}
    out = ROOT / 'out'
    out.mkdir(exist_ok=True)
    (out / 'measurements.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'measurements.md').write_text(markdown(result))
    print(json.dumps({'cases': len(rows), 'fits': sum(r['fits'] for r in rows),
                      'decode_cvp2_pass': sum(r['decode_cvp2'] for r in rows),
                      'decode_zxingcpp_pass': sum(r['decode_zxingcpp'] for r in rows),
                      'decode_pass': sum(r['decode_ok'] for r in rows),
                      'decode_fail': sum(r['fits'] and not r['decode_ok'] for r in rows),
                      'infeasible': sum(not r['fits'] for r in rows)}))

if __name__ == '__main__':
    main()
