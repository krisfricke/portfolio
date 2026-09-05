#!/usr/bin/env python3
"""Render assets/og.jpg - the image link-preview scrapers show when the reader is shared.

Without it they pick the first image on the page, which is one of the bee cursor's wing layers:
a lone wing floating on a white card. Run again if the title or the publications change.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg  = json.load(open(os.path.join(site, '_config.json')))
meta = json.load(open(os.path.join(site, '_articles_meta.json')))

W, H = 1200, 630
SKY  = ((125,180,220), (169,210,236), (211,232,247))   # --sky1 / --sky2 / --sky3
NAVY, INK2, GOLD = (31,58,95), (61,96,121), (249,197,0)

FONTS = '/sessions/vibrant-clever-hawking/mnt/VBJ/2026 07/ABJ_July2026_site/fonts'
def f(name, size):
    for p in (os.path.join(FONTS, name),
              '/usr/share/fonts/truetype/crosextra/Carlito-%s.ttf' % name.split('-')[1][:-4]):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

# --- sky, matching the reader's own gradient ---
card = Image.new('RGB', (W, H))
d = ImageDraw.Draw(card)
for y in range(H):
    t = y / (H - 1)
    a, b, u = (SKY[0], SKY[1], t / 0.46) if t < 0.46 else (SKY[1], SKY[2], (t - 0.46) / 0.54)
    d.line([(0, y), (W, y)], fill=tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3)))

# --- the bee, from the full-resolution original rather than the 200px cursor cut ---
bee = Image.open(os.path.join(os.path.dirname(site), 'Bee 3bd.gif')).convert('RGBA')
bee = bee.crop(bee.getbbox())
bh = 330
bee = bee.resize((round(bee.width * bh / bee.height), bh), Image.LANCZOS)
bx, by = 96, (H - bee.height) // 2
shadow = Image.new('RGBA', card.size, (0, 0, 0, 0))
shadow.paste((14, 45, 70, 46), (bx + 6, by + 10), bee)
card.paste(Image.alpha_composite(shadow, Image.new('RGBA', card.size, (0,0,0,0))).convert('RGB'),
           (0, 0), shadow.split()[3])
card.paste(bee, (bx, by), bee)

# --- the words, measured so nothing runs off the edge ---
x     = bx + bee.width + 60
avail = W - x - 58
def fit(text, name, size, maxw):
    """largest size at or below `size` that keeps `text` inside `maxw`"""
    while size > 8:
        ft = f(name, size)
        if d.textlength(text, font=ft) <= maxw: return ft
        size -= 1
    return f(name, 8)
def wrap(text, name, size, maxw):
    ft, lines, cur = f(name, size), [], ''
    for w in text.split(' '):
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=ft) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return ft, lines

yrs = [a['year'] for a in meta]
pubs, seen = [], set()
for a in meta:
    q = a['pub'].replace('The ', '')
    if q not in seen: seen.add(q); pubs.append(q)

y = 170
d.text((x, y), 'Articles by', font=fit('Articles by', 'Carlito-Regular.ttf', 44, avail), fill=INK2); y += 52
ft = fit('Kris Fricke', 'Carlito-Bold.ttf', 100, avail)
d.text((x, y), 'Kris Fricke', font=ft, fill=NAVY); y += ft.size + 30
d.rectangle([x, y, x + 200, y + 8], fill=GOLD); y += 42

sub = '%d articles on bees and beekeeping, %d\u2013%d' % (len(meta), min(yrs), max(yrs))
ft, lines = wrap(sub, 'Carlito-Regular.ttf', 32, avail)
for ln in lines: d.text((x, y), ln, font=ft, fill=NAVY); y += ft.size + 9
y += 8
ft, lines = wrap('  \u00b7  '.join(pubs), 'Carlito-Regular.ttf', 24, avail)
for ln in lines: d.text((x, y), ln, font=ft, fill=INK2); y += ft.size + 7

out = os.path.join(site, 'assets', 'og.jpg')
card.save(out, 'JPEG', quality=88, optimize=True)
print('assets/og.jpg', card.size, os.path.getsize(out), 'bytes')
