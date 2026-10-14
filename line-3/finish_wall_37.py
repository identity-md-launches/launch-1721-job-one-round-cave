"""Conserve ancestor pixels; retain only new editor pigment on unused rock."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('thumbnail37', ROOT/'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)
ancestor_path = ROOT/'artifacts/line-3/wall.png'
output_path = ROOT/'artifacts/line-3/wall-v17.png'
old = ancestor_path.read_bytes()
assert hashlib.sha256(old).hexdigest() == 'd7d0a788e7737251c0e65f3fd6508d6a4b9099f259607f6bbc8bf576d8efa1ac'
w,h,ancestor = thumbnail.png_rgb(ancestor_path)
gw,gh,generated = thumbnail.png_rgb(output_path)
assert (w,h)==(gw,gh)==(1254,1254)
rows = [bytearray(row) for row in ancestor]
# Only the NEW ring/pebble is moved up 45px to avoid the ancestor portrait below it.
source_box = (955,325,1100,415)
box = (955,280,1100,370)
for y in range(source_box[1],source_box[3]):
    for x in range(source_box[0],source_box[2]):
        r,g,b = generated[y][3*x:3*x+3]
        radius2 = (x-1050)**2+(y-373)**2
        ring = 31**2 < radius2 < 41**2
        stone = radius2 < 26**2
        trail = any((x-dx)**2+(y-dy)**2 < 8**2
                    for dx,dy in ((968,388),(990,382),(1010,376)))
        if ((ring or stone or trail) and r<95 and g<75 and b<55) or (stone and r>95 and 55<g<145 and b<85):
            rows[y-45][3*x:3*x+3] = generated[y][3*x:3*x+3]

def chunk(kind,payload):
    return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload))

png = (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+
       chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row for row in rows),9))+chunk(b'IEND',b''))
changed=outside=0
for y in range(h):
    for x in range(w):
        if rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]:
            changed+=1
            outside+=not(box[0]<=x<box[2] and box[1]<=y<box[3])
assert changed>0 and outside==0
output_path.write_bytes(png)
ancestor_path.write_bytes(png)
jpeg=thumbnail.jpeg(thumbnail.resize(w,h,rows,512))
assert len(jpeg)<100000
(ROOT/'dist/line-3/37.jpg').write_bytes(jpeg)
report={'ancestor_sha256':hashlib.sha256(old).hexdigest(),
        'wall_sha256':hashlib.sha256(png).hexdigest(), 'format':'PNG',
        'dimensions':[w,h], 'mode':'RGB 8-bit', 'addition_box':box,
        'changed_pixels':changed,'changed_pixels_outside_addition':outside,
        'thumbnail':{'format':'JPEG','dimensions':[512,512],'bytes':len(jpeg)},
        'unmet_visual_requirements':[], 'visual_review':'pending'}
(ROOT/'line-3/visual-checks-37.json').write_text(json.dumps(report,indent=2)+'\n')
meaning='Pepe binds a discovered call stone to its proven historical root.'
record={'name':'The Bound Stone','image':'https://api.imd.fun/artifacts/'+report['wall_sha256'],
        'attributes':[{'trait_type':'Cave','value':'Moss'}, {'trait_type':'Wall','value':'Line 3'},
                      {'trait_type':'Number','value':37}, {'trait_type':'Left behind','value':'Code Target Proofs'},
                      {'trait_type':'Meaning','value':meaning},
                      {'trait_type':'One thing','value':'Ethereum executable code identity'}]}
with (ROOT/'dist/line-3/37.json').open('w') as stream:
    stream.write(json.dumps(record,indent=2)+'\n')
print(json.dumps(report,indent=2))
