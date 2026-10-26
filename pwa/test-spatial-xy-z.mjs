import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import * as codec from './spatial-xy-z.js';
const root = fileURLToPath(new URL('../', import.meta.url));
let count = 0;
function check(actual, expected) { assert.deepEqual(actual, expected); count++; }
const rows = [
  [55.675398,12.561895,'u3butz7k9q7v'], [51.5074,-.1278,'gcpvj0duq533'],
  [35.6762,139.6503,'xn76cydhzven'], [40.7128,-74.006,'dr5regw3ppyz'],
  [59.9139,10.7522,'u4xsudvxb2mq'], [0,0,'s000000000000'],
  [-90,-180,'000000000000'], [90,180,'zzzzzzzzzzzz']
];
const measured = [23.0254,-.0001,0,23,-18,23.025,1.2345,-1.2345,.0625,.1875,-.0625,-.1875,1e20];
const zOrder = ['-18','-0.5','0','0.05','0.5','23','23.02','23.025','999999999999999999999999998','999999999999999999999999999'];
const invalid = ['+23','2.3e1','023','23.','23.0','23.50','-0','0.0','٢٣','.5','23\n'];
const python = `import sys,json,importlib
root,kind=sys.argv[1:]
sys.path.insert(0,root+'/experimental/'+('punkti-v0.6-mesh/src' if kind=='ref' else 'nairobidot-l3/src'))
s=importlib.import_module('spatial' if kind=='ref' else 'nairobidot.spatial')
data=json.load(sys.stdin)
print(json.dumps({'cells':[[s.encode_xy(lat,lon,p),s.decode_xy(xy[:p])] for lat,lon,xy in data['rows'] for p in (4,10,12)],'heights':[s.format_z(x) for x in data['measured']]}))`;
const expectedCells = [];
for (const [lat, lon, xy] of rows) for (const p of [4,10,12]) {
  check(codec.encodeXY(lat,lon,p),xy.slice(0,p));
  const cell = codec.decodeXY(xy.slice(0,p));
  check(codec.encodeXY(cell.lat,cell.lon,p),xy.slice(0,p));
  assert(cell.lat_min <= lat && cell.lat_max >= lat && cell.lon_min <= lon && cell.lon_max >= lon); count++;
  expectedCells.push([xy.slice(0,p),cell]);
}
for (const kind of ['ref','nb']) {
  const run = spawnSync('python3',['-c',python,root,kind],{input:JSON.stringify({rows,measured}),encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  const result = JSON.parse(run.stdout);
  check(result.cells,expectedCells);
  check(result.heights,measured.map(codec.formatZ));
}
for (const z of invalid) { assert.throws(()=>codec.parseZ(z)); count++; }
for (const h of ['u3b_0','u'.repeat(13)+'_0','u3bu0','u3bu__0','u3bu_','u3bu_'+'1'.repeat(28)]) {
  assert.throws(()=>codec.parseH(h)); count++;
}
for (const z of ['23','-18','23.025']) check(codec.encodeH(55.675398,12.561895,z),'u3butz7k9q_'+z);
for (let i=0;i<zOrder.length;i++) for (let j=0;j<zOrder.length;j++) check(codec.compareZ(zOrder[i],zOrder[j]),Math.sign(i-j));
check(['23','23.02','23.025','22.999'].map(z=>codec.matches('u3bu_'+z,{z_min:'23',z_max:'23.025'})),[true,true,false,false]);
check(codec.matches('u3bu_0',{xy_lo:'u3bu',xy_hi:'u3bu000001'}),true);
check(codec.matches('u3bu_0',{xy_lo:'u3butz7k9q',xy_hi:'u3butz7k9r'}),false);
for (const [lo,hi,xy,selected] of [
  ['u3b','u3c','u3bu',true], ['u3b','u3c','u3b',true],
  ['u3b','u3c','u3butz7k9q',true], ['u3b','u3c','u3c',false],
  ['u3butz7k9q','u3butz7k9r','u3bu',false],
  ['u3butz7k9q','u3butz7k9r','u3butz7k9q',true],
  ['u3butz7k9q','u3butz7k9r','u3butz7k9r',false],
  ['u3bu','u3bu000001','u3bu',true]
]) {
  // Three-character examples in §9.4 are keys; append 0 for a valid address
  // with exactly the same lower edge, without admitting short address XY.
  check(codec.matches(xy.padEnd(4,'0')+'_0',{xy_lo:lo,xy_hi:hi}),selected);
}
check(codec.encodeH(0,0,'1'.repeat(27),4).length,32);
assert.throws(()=>codec.encodeH(0,0,'1'.repeat(27),12)); count++;
assert.throws(()=>codec.formatZ('23.50')); count++;
for (const scope of [{xy_lo:'u3b',xy_hi:'u3b0'},{z_min:23},{z_min:'23.0'},{z_min:'1',z_max:'1'},{h_lo:'u'}]) {
  assert.throws(()=>codec.normalizeScope(scope)); count++;
}
check(codec.matches('',{}),true);
check(codec.matches('',{z_min:'0'}),false);
check(codec.subscribed('u3bu_0',[]),false);
check(codec.subscribed('u3bu_0',[{xy_hi:'g'},{xy_lo:'u'}]),true);
console.log(`XY_Z: ${count} assertions passed; reference and clean-room Python agreement verified.`);
