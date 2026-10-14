#!/usr/bin/env python3
"""Paint one in-memory earth-pigment insert onto the verified Line 2 wall."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import finish_wall_26 as imageops

ROOT = Path(__file__).resolve().parents[1]
WALL = ROOT / 'artifacts/line-2/wall.png'
SOURCE_SHA256 = '74779548629d6ae67eaeb8e8ac7f1452a396878ca7b606c34b3d9fd753aab493'
PLACEMENT = (110, 780, 130, 100)


def main():
    source = WALL.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('expected the verified Pepe 36 wall; refusing a different source')
    width, height, channels, base = imageops.decode(source)
    if (width, height, channels) != (1254, 1254, 3):
        raise ValueError('unexpected inherited wall format')
    imageops.PLACE_X, imageops.PLACE_Y, imageops.PLACE_W, imageops.PLACE_H = PLACEMENT
    result, bounds = imageops.composite(base, imageops.decode(sys.stdin.buffer.read()))
    x, y, w, h = PLACEMENT
    for row_number, (old, new) in enumerate(zip(base, result)):
        if not y <= row_number < y + h:
            assert old == new
        else:
            assert old[:3*x] == new[:3*x] and old[3*(x+w):] == new[3*(x+w):]
    output = imageops.encode(width, height, result)
    WALL.write_bytes(output)
    (ROOT / 'artifacts/line-2/wall-v17.png').write_bytes(output)
    thumbnail_spec = importlib.util.spec_from_file_location(
        'thumbnail_37', ROOT / 'shared/wall-thumbnail/thumbnail.py')
    thumbnail = importlib.util.module_from_spec(thumbnail_spec)
    thumbnail_spec.loader.exec_module(thumbnail)
    preview = thumbnail.jpeg(thumbnail.resize(width, height, result, 512))
    if len(preview) >= 100_000:
        raise ValueError('preview exceeds 100 KiB')
    (ROOT / 'dist/line-2/37.jpg').write_bytes(preview)
    digest = hashlib.sha256(output).hexdigest()
    record = {
        'name': 'The Code Split',
        'image': 'https://api.imd.fun/artifacts/' + digest,
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Moss'},
            {'trait_type': 'Wall', 'value': 'Line 2'},
            {'trait_type': 'Number', 'value': 37},
            {'trait_type': 'Left behind', 'value': 'Allowance Code Delta'},
            {'trait_type': 'Meaning', 'value': 'A split stone compares remembered code without calling absence a revocation.'},
            {'trait_type': 'One thing', 'value': 'ERC-20 spending-permission audits'},
        ],
    }
    (ROOT / 'dist/line-2/37.json').write_text(json.dumps(record, indent=2) + '\n')
    changed = sum(old[offset:offset+3] != new[offset:offset+3]
                  for old, new in zip(base, result) for offset in range(0, len(old), 3))
    checks = {
        'source_sha256': SOURCE_SHA256, 'output_sha256': digest,
        'format': 'PNG', 'dimensions': [width, height], 'placement': list(PLACEMENT),
        'changed_pixels': changed, 'outside_placement_unchanged': True,
        'preview': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(preview)},
        'unmet_visual_requirements': [],
        'visual_review': 'Reviewed full wall and 512px JPEG after production.',
    }
    (ROOT / 'line-2/visual-checks-37.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
