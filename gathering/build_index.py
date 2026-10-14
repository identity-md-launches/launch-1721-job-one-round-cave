#!/usr/bin/env python3
"""Build the complete, self-contained cave gallery from numbered records."""
import html
import json
from pathlib import Path

ROOT = Path('dist')
WALLS = [f'line-{n}' for n in range(1, 5)] + ['gathering']


def e(value):
    return html.escape(str(value), quote=True)


def trait(record, name):
    return next((x['value'] for x in record['attributes'] if x['trait_type'] == name), '')


def card(slug, number, record):
    pending = record['name'] == 'Not painted yet'
    image = record['image'] if pending else f'{slug}/{number:02}.jpg'
    name = record['name']
    meaning = trait(record, 'Meaning') or 'A place left for the next Pepe.'
    tool = trait(record, 'Left behind')
    return (f'<article class="card"><a href="{e(record["image"])}" aria-label="Open full wall: Round {number} · {e(name)}">'
            f'<img src="{e(image)}" width="512" height="512" loading="lazy" alt="{e(meaning)}"></a>'
            f'<h3>Round {number} · {e(name)}</h3><p>{e(meaning)}</p>'
            + (f'<p class="tool">Left behind: {e(tool)}</p>' if tool else '') + '</article>')


def main():
    goals = [{'line': n, 'goal': Path(f'line-{n}/GOAL.md').read_text().strip()} for n in range(1, 5)]
    (ROOT / 'goals.json').write_text(json.dumps(goals, indent=2) + '\n')
    records = {}
    for slug in WALLS:
        entries = []
        for path in (ROOT / slug).glob('[0-9][0-9].json'):
            entries.append((int(path.stem), json.loads(path.read_text())))
        records[slug] = sorted(entries, reverse=True)
    painted = sum(r['name'] != 'Not painted yet' for wall in records.values() for _, r in wall)
    pending = sum(r['name'] == 'Not painted yet' for wall in records.values() for _, r in wall)
    page = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
            '<title>Pepeolithic · Moss</title><meta name="description" content="Five cave walls, four useful crafts, one gathering.">',
            '<style>:root{color-scheme:dark;background:#17120e;color:#eee0c6;font:17px/1.55 system-ui,sans-serif}'
            '*{box-sizing:border-box}body{max-width:1180px;margin:auto;padding:28px}a{color:#ecc17a;text-underline-offset:4px}'
            'header{padding:36px 0 20px;border-bottom:1px solid #735039}h1{font:clamp(2.8rem,7vw,5.5rem)/1 Georgia,serif;margin:.2em 0}'
            'h2{font:2.2rem Georgia,serif;color:#f0bf78}h3{font-size:1.1rem;margin:15px 0 8px}p{margin:.6em 0}'
            '.eyebrow{color:#c89763}.intro{max-width:720px}nav{display:flex;flex-wrap:wrap;gap:24px;margin:28px 0}'
            'section{margin:55px 0;scroll-margin-top:20px}.goal{max-width:850px;color:#d9bf99;margin-bottom:24px}'
            '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:26px}'
            '.card{max-width:560px;min-width:0;padding-bottom:20px}img{width:100%;height:auto;display:block;border-radius:4px;background:#382819}'
            '.card p{max-width:55ch;color:#cdbba1}.tool{font-size:.85rem}details{margin-top:20px;border-top:1px solid #624632;padding-top:14px}'
            'summary{cursor:pointer;color:#cda677;padding:10px 0}.pending{margin-top:22px}.pending .card{opacity:.7}'
            'footer{border-top:1px solid #624632;padding:24px 0;color:#b69f81;font-size:.9rem}'
            'a:focus-visible,summary:focus-visible{outline:3px solid #f4bf67;outline-offset:5px}'
            '@media(max-width:520px){body{padding:18px}.grid{grid-template-columns:1fr}nav{gap:16px}}</style></head><body>',
            '<header><p class="eyebrow">Pepeolithic · Moss</p><h1>Four trails. One fire.</h1>'
            '<p class="intro">Each Pepe has one task and one short life. What remains is a mark, a working tool, and room for the next worker.</p>'
            '<p class="intro">Painted rounds appear newest first on each wall. Future rounds remain folded below them.</p>',
            f'<p>{painted} painted rounds · {pending} places still open</p><nav aria-label="Walls">']
    page += [f'<a href="#{slug}">{"Gathering" if slug == "gathering" else "Line " + slug[-1]}</a>' for slug in WALLS]
    page.append('</nav></header><main>')
    for slug in WALLS:
        heading = 'Gathering' if slug == 'gathering' else 'Line ' + slug[-1]
        goal = 'Four crafts meet, are tried, and become shared tools.' if slug == 'gathering' else goals[int(slug[-1])-1]['goal']
        ready = [(n, r) for n, r in records[slug] if r['name'] != 'Not painted yet']
        future = [(n, r) for n, r in records[slug] if r['name'] == 'Not painted yet']
        page.append(f'<section id="{slug}"><h2>{heading}</h2><p class="goal">{e(goal)}</p><div class="grid">')
        page += [card(slug, n, r) for n, r in ready]
        page.append('</div>')
        if future:
            page.append(f'<details><summary>{len(future)} future rounds · not painted yet</summary><div class="grid pending">')
            page += [card(slug, n, r) for n, r in future]
            page.append('</div></details>')
        page.append('</section>')
    page.append('</main><footer><p>ZTO first · IMD second · Ethereum</p>'
                '<p>ZTO: <code>0xd782bdea4ef02a0bd391eb9089470c8080f0a68e</code></p>'
                '<p>Historical tool observations are evidence to inspect, not a current price or a promise of execution.</p>'
                '<p><a href="goals.json">The four goals</a> · Images and words belong to their numbered records.</p>'
                '</footer></body></html>')
    (ROOT / 'index.html').write_text(''.join(page) + '\n')
    print(json.dumps({'records': painted + pending, 'painted': painted, 'pending': pending,
                      'page_bytes': (ROOT / 'index.html').stat().st_size}))


if __name__ == '__main__':
    main()
