#!/usr/bin/env python3
"""Build the icon set from assets/bee/gold.png.

gold.png is the bee as drawn for the masthead: 176x128, ink to all four edges. It is wider than it is
tall, so in a square icon slot it letterboxes - that is inherent, and filling the square would mean
stretching the drawing. Every icon here therefore puts the bee at full width, centred. Run after
changing gold.png.
"""
import os
from PIL import Image

site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bee  = Image.open(os.path.join(site, 'assets/bee/gold.png')).convert('RGBA')
bee  = bee.crop(bee.split()[3].getbbox())          # no-op for gold.png, but keeps this honest

def square(px):
    c = Image.new('RGBA', (px, px), (0, 0, 0, 0))
    h = max(1, round(bee.height * px / bee.width))
    c.alpha_composite(bee.resize((px, h), Image.LANCZOS), (0, (px - h) // 2))
    return c

square(192).save(os.path.join(site, 'assets/bee/favicon.png'))
square(180).save(os.path.join(site, 'assets/bee/apple-touch-icon.png'))
ico = [square(s) for s in (48, 32, 16)]
ico[0].save(os.path.join(site, 'favicon.ico'), sizes=[(48, 48), (32, 32), (16, 16)])
print('favicon.png 192, apple-touch-icon.png 180, favicon.ico 16/32/48 - from gold.png')
