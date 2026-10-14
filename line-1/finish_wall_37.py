"""Conserve the inherited wall around a generated motif and emit round 37.

Artifact-production helper, not a runtime dependency of ZTO Witness Routes.
Feed the built-in editor's base64 PNG on stdin, with its character count as
the sole argument. FFmpeg composites in memory; no intermediate image is saved.
"""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ANCESTOR = 'd591812e0147cff0e226b0a9323b285c0d1e8fe18e9fbb2bd4ec947375357b44'
BOX = (345, 935, 495, 1009)
PROTECTED_CORNER = (345, 935, 355, 945)


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    sys.dont_write_bytecode = True
    assert len(sys.argv) == 2 and sys.argv[1].isdigit()
    count = int(sys.argv[1])
    assert 0 < count <= 20_000_000
    encoded = sys.stdin.buffer.read(count)
    assert len(encoded) == count
    generated = base64.b64decode(encoded, validate=True)
    root = Path.cwd()
    wall = root / 'artifacts/line-1/wall.png'
    assert hashlib.sha256(wall.read_bytes()).hexdigest() == ANCESTOR
    thumbnail = module('thumbnail37', root / 'shared/wall-thumbnail/thumbnail.py')
    decoder = module('decoder37', root / 'line-1/finish_wall_36.py')
    width, height, old = thumbnail.png_rgb(wall)
    assert (width, height) == (1254, 1254)
    x0, y0, x1, y1 = BOX
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-threads', '1',
               '-i', str(wall), '-i', 'pipe:0', '-filter_complex_threads', '1',
               '-filter_complex',
               f'[1:v]scale={width}:{height},format=rgb24,crop={x1-x0}:{y1-y0}:{x0}:{y0},'
               "format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
               "a='if(lt(X,10)*lt(Y,10),0,255*min(1,min(min(X,W-1-X),min(Y,H-1-Y))/6))'[patch];"
               f'[0:v][patch]overlay={x0}:{y0}:format=rgb:shortest=1,format=rgb24[out]',
               '-map', '[out]', '-frames:v', '1', '-c:v', 'png', '-pix_fmt', 'rgb24',
               '-f', 'image2pipe', 'pipe:1']
    assembled = subprocess.run(command, input=generated, capture_output=True, timeout=60)
    assert assembled.returncode == 0, assembled.stderr.decode()
    final = assembled.stdout
    fw, fh, rows, channels = decoder.decode_png(final)
    assert (fw, fh, channels) == (width, height, 3)
    inside = outside = 0
    for y in range(height):
        for x in range(width):
            if old[y][x*3:x*3+3] != rows[y][x*3:x*3+3]:
                if x0 <= x < x1 and y0 <= y < y1:
                    inside += 1
                else:
                    outside += 1
    assert inside > 100 and outside == 0, (inside, outside)
    px0, py0, px1, py1 = PROTECTED_CORNER
    assert all(old[y][3*px0:3*px1] == rows[y][3*px0:3*px1]
               for y in range(py0, py1)), 'retain the inherited stepping-stone edge'
    sha = hashlib.sha256(final).hexdigest()
    jpeg = thumbnail.jpeg(thumbnail.resize(width, height, rows, 512))
    assert len(jpeg) <= 100_000
    record_path = root / 'dist/line-1/37.json'
    jpeg_path = root / 'dist/line-1/37.jpg'
    assert not record_path.exists() and not jpeg_path.exists()
    record = {
        'name': 'The Route Around the Hollow',
        'image': 'https://api.imd.fun/artifacts/' + sha,
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Moss'},
            {'trait_type': 'Wall', 'value': 'Line 1'},
            {'trait_type': 'Number', 'value': 37},
            {'trait_type': 'Left behind', 'value': 'ZTO Witness Routes'},
            {'trait_type': 'Meaning', 'value': 'An ochre trail curves around a hollow rock to find a usable witness route.'},
            {'trait_type': 'One thing', 'value': 'Calculate ZTO/IMD swap bounds from real Uniswap v4 liquidity'},
        ],
    }
    (root / 'artifacts/line-1/wall-v17.png').write_bytes(final)
    wall.write_bytes(final)
    jpeg_path.write_bytes(jpeg)
    record_path.write_text(json.dumps(record, separators=(',', ':')) + '\n')
    checks = {
        'ancestor_sha256': ANCESTOR, 'wall_sha256': sha,
        'wall': {'path': 'artifacts/line-1/wall-v17.png', 'width': width,
                 'height': height, 'format': 'PNG', 'mode': 'RGB', 'bytes': len(final)},
        'jpeg': {'path': 'dist/line-1/37.jpg', 'width': 512, 'height': 512,
                 'format': 'JPEG', 'bytes': len(jpeg)},
        'addition_box': list(BOX), 'changed_pixels_inside': inside,
        'protected_corner': list(PROTECTED_CORNER), 'changed_pixels_in_protected_corner': 0,
        'changed_pixels_outside': outside,
        'hand_review': 'No new hands or handprints. Each inherited main Pepe hand visually has four fingers and one thumb, five digits total.',
        'text_review': 'No letters, numbers, signatures, logos or watermarks observed.',
        'unmet_visual_requirements': [],
        'visual_limitations': [
            'Worn pigment and small details make visual judgments subjective.',
            'Rock texture within the small generated patch is approximate; outside pixels are exact.',
            'The motif was generated slightly above the requested position; the reviewed actual bare-rock position was selected.',
        ],
    }
    (root / 'line-1/visual-checks-37.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks, indent=2), flush=True)


if __name__ == '__main__':
    main()
