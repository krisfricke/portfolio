#!/usr/bin/env python3
"""
Facsimile page builder for the portfolio reader.

For each PDF page we emit
  pages/<article-id>/<n>.html   - background JPEG + absolutely positioned live text
  pages/<article-id>/p<n>.jpg   - the page with its text removed (images + vector art kept)
  pages/<article-id>/cover.jpg  - first page, full render, for the cover card
  pages/<article-id>/text.json  - reading-order plain text (for the static article pages)

Coordinates: PDF points x 1.6 = page pixels (same convention as the ABJ reader).
"""
import json, os, re, sys, html
import pymupdf as fitz

SCALE = 1.6
PT_MM = 25.4 / 72.0

SERIF_HINTS = ('times', 'palatino', 'georgia', 'garamond', 'minion', 'book antiqua', 'palladio',
               'century schoolbook', 'baskerville', 'cambria', 'caslon', 'bodoni', 'didot', 'antigoni')
MONO_HINTS = ('courier', 'mono', 'consolas')

GLYPH = {0xF0B7: '•', 0xF0A7: '▪', 0xF0D8: '→', 0xF0FC: '✓', 0xF0A8: '□', 0xF06E: '■'}

def fam(fontname):
    f = fontname.lower()
    if any(h in f for h in MONO_HINTS):
        return "'Courier New',Courier,monospace"
    if any(h in f for h in SERIF_HINTS):
        if 'palatino' in f or 'palladio' in f:
            return "'TeX Gyre Pagella','Palatino Linotype',Palatino,'Book Antiqua',Georgia,serif"
        return "'Liberation Serif','Times New Roman',Times,serif"
    if 'calibri' in f:
        return "Carlito,Calibri,'Segoe UI',Arial,sans-serif"
    return "Carlito,Calibri,'Segoe UI','Helvetica Neue',Arial,sans-serif"

# The Australian issues were typeset with a font whose quote glyphs are mis-mapped
# in the PDF text layer; these are the corrections (only applied when AUQUOTES is set).
AUQ = {'\u201f': '\u2019', '\u2015': '\u201c', '\u2016': '\u201d', '\u2018': '\u2019', '\u2017': '\u2018', '\u201e': '\u201c'}
AUQUOTES = False

def clean(t):
    t = unlig(t)
    out = []
    for ch in t:
        if AUQUOTES and ch in AUQ: ch = AUQ[ch]
        o = ord(ch)
        if o in GLYPH: out.append(GLYPH[o])
        elif 0xF000 <= o <= 0xF0FF: out.append('•')
        elif o == 0xAD: continue
        else: out.append(ch)
    return ''.join(out)

def span_style(s):
    st = ["font-family:" + fam(s['font'])]
    fl = s['flags']; fn = s['font'].lower()
    if (fl & 16) or 'bold' in fn or 'black' in fn or 'semibold' in fn or 'heavy' in fn:
        st.append('font-weight:700')
    if (fl & 2) or 'italic' in fn or 'oblique' in fn:
        st.append('font-style:italic')
    if fl & 1:
        st.append('vertical-align:super;font-size:.7em')
    return ';'.join(st)

_VOWEL = set('aeiouyAEIOUY')
def wordlike(tok):
    t = tok.strip('.,;:!?()[]"\'‘’“”-–—')
    if not t: return False
    if t.lower() in ('a', 'i', 'oh', 'ok', 'us', 'nsw', 'qld', 'vic', 'wa', 'sa', 'nt', 'act', 'usa', 'uk', 'nz'): return True
    if not re.fullmatch(r"[A-Za-z][A-Za-z'’-]*|\d[\d.,%]*(st|nd|rd|th)?", t): return False
    if re.search(r'[a-z][A-Z]', t): return False          # mIxEd case is a picture, not a word
    if t[0].isdigit(): return True
    has_v = any(c in _VOWEL for c in t); has_c = any(c.isalpha() and c not in _VOWEL for c in t)
    return has_v and has_c
def ocr_keep(text):
    toks = text.split()
    good = [t for t in toks if wordlike(t)]
    if len(toks) == 1: return len(good) == 1 and len(good[0]) >= 6
    return len(good) >= 2 and len(good) / len(toks) >= 0.6

LIGFIX = False   # some PDFs carry a phantom space after every fi/fl ligature; set per article
def unlig(t):
    return re.sub(r'\b(\w*(?:fi|fl|ff|ffi|ffl)) (?=[a-z])', r'\1', t) if LIGFIX else t

def inter(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return max(0, x1 - x0) * max(0, y1 - y0)

def build_page(doc, pno, outdir, n, title, links_out, manual=(), ocr=False):
    page = doc[pno]
    W, H = page.rect.width, page.rect.height
    flags = fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_MEDIABOX_CLIP  # ligatures expanded
    if ocr:
        # scanned / rasterised page: recognise the text so it can be selected, searched and read aloud,
        # but draw it transparent over the untouched picture
        tp = page.get_textpage_ocr(full=True, dpi=220)
        d = page.get_text('dict', textpage=tp, flags=flags)
        for b_ in d['blocks']:                       # the usual misreads of a display face
            for l_ in b_.get('lines', []):
                for s_ in l_['spans']:
                    s_['text'] = re.sub(r'(?<![A-Za-z])ln(?![A-Za-z])', 'In', re.sub(r'(?<!\S)\|(?!\S)', 'I', s_['text']))
    else:
        d = page.get_text('dict', flags=flags)
    uris = [(l['from'], l['uri']) for l in page.get_links() if l.get('kind') == fitz.LINK_URI and l.get('uri')]

    lines_html, redact, textlines, paras = [], [], [], []
    for b in d['blocks']:
        if b['type'] != 0: continue
        blines = [l for l in b['lines'] if any(s['text'].strip() for s in l['spans'])]
        if ocr: blines = [l for l in blines if ocr_keep(''.join(s['text'] for s in l['spans']))]
        if not blines: continue
        ptxt = ''
        for l in blines:
            t = clean(''.join(s['text'] for s in l['spans'])).strip()
            if not t: continue
            if ptxt.endswith('-') and t[:1].islower(): ptxt = ptxt[:-1] + t
            else: ptxt = (ptxt + ' ' + t).strip()
        if ptxt and ocr:                                   # drop runs of two or more junk tokens
            toks, out, run = ptxt.split(), [], []
            for tk in toks + [None]:
                if tk is not None and not wordlike(tk): run.append(tk); continue
                if len(run) == 1: out += run
                run = []
                if tk is not None: out.append(tk)
            ptxt = ' '.join(out)
        if ptxt:
            sz = max(s['size'] for l in blines for s in l['spans'])
            paras.append({'t': ptxt, 'size': round(sz, 1), 'y': round(b['bbox'][1], 1), 'x': round(b['bbox'][0], 1)})
        widths = [l['bbox'][2] - l['bbox'][0] for l in blines]
        maxw = max(widths)
        for li, l in enumerate(blines):
            if abs(l['dir'][0]) < 0.9:      # rotated text: leave it in the picture
                continue
            x0, y0, x1, y1 = l['bbox']
            spans = [s for s in l['spans'] if s['text']]
            if not spans: continue
            size = max(s['size'] for s in spans)
            segs = []                      # (text, style, href)
            for s in spans:
                t = clean(s['text'])
                if not t: continue
                href = None
                sb = s['bbox']; sa = max(1e-6, (sb[2]-sb[0])*(sb[3]-sb[1]))
                for r, u in uris:
                    if inter(sb, (r.x0, r.y0, r.x1, r.y1)) > 0.5 * sa:
                        href = u; break
                if href: links_out.append(href)
                segs.append([t, span_style(s), href])
            if not segs: continue
            just = len(blines) >= 2 and li < len(blines) - 1 and widths[li] >= 0.985 * maxw
            attrs = ' data-w="%.1f"' % ((x1 - x0) * SCALE) + (' data-j="1"' if just else '')
            lines_html.append(['<p style="position:absolute;left:%.1fpx;top:%.1fpx;font-size:%.1fpx;white-space:nowrap"%s>'
                              % (x0 * SCALE, y0 * SCALE, size * SCALE, attrs), segs])
            redact.append(fitz.Rect(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5))
            textlines.append(''.join(clean(s['text']) for s in spans))

    apply_manual_links(lines_html, [m for m in manual if m.get('page') == n], links_out)
    lines_html = [head + ''.join(render_seg(t, st, h) for t, st, h in segs) + '</p>' for head, segs in lines_html]
    bg = fitz.open(); bg.insert_pdf(doc, from_page=pno, to_page=pno)
    bp = bg[0]
    for r in ([] if ocr else redact): bp.add_redact_annot(r)
    if not ocr: bp.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE, text=fitz.PDF_REDACT_TEXT_REMOVE)
    pix = bp.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), alpha=False)
    pix.save(os.path.join(outdir, 'p%d.jpg' % n), jpg_quality=82)
    if n == 1:
        page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0), alpha=False).save(os.path.join(outdir, 'cover.jpg'), jpg_quality=85)
    bg.close()

    pw, ph = round(W * SCALE), round(H * SCALE)
    wmm, hmm = W * PT_MM, H * PT_MM
    scaler = (wmm * 96 / 25.4) / pw
    doc_html = HEAD % dict(title=html.escape(title), n=n, wmm=wmm, hmm=hmm, scaler=scaler, pw=pw, ph=ph)
    if ocr: doc_html = doc_html.replace('p{margin:0;position:absolute}', 'p{margin:0;position:absolute;color:transparent}\np::selection,p *::selection{background:rgba(249,197,0,.45);color:transparent}')
    doc_html += '<img class="bg" src="p%d.jpg" alt="">\n' % n + '\n'.join(lines_html) + '\n</div></div></div>\n' + TAIL
    open(os.path.join(outdir, '%d.html' % n), 'w', encoding='utf-8').write(doc_html)
    return {'lines': textlines, 'paras': paras}

def render_seg(t, st, href):
    inner = '<span style="%s">%s</span>' % (st, html.escape(t, quote=False))
    return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (html.escape(href, quote=True), inner) if href else inner

def apply_manual_links(lines, specs, links_out):
    """Link a phrase given in the metadata, even when it runs across several lines or spans."""
    import re as _re
    for spec in specs:
        want = _re.sub(r'\s+', ' ', spec['text']).strip().lower()
        # flatten: character stream over all lines (lines separated by one space)
        stream, index = '', []          # index[i] = (line_no, seg_no, char_in_seg)
        for ln, (head, segs) in enumerate(lines):
            for sn, seg in enumerate(segs):
                for ci, ch in enumerate(seg[0]):
                    stream += ch; index.append((ln, sn, ci))
            stream += ' '; index.append(None)
        norm = _re.sub(r'\s+', ' ', stream.lower())
        # map normalised positions back: build norm with an index map
        npos, nstr = [], ''
        prev_sp = False
        for i, ch in enumerate(stream.lower()):
            sp = ch.isspace()
            if sp and prev_sp: continue
            nstr += ' ' if sp else ch; npos.append(i); prev_sp = sp
        k = nstr.find(want)
        if k < 0:
            print('   manual link phrase not found on this page:', spec['text']); continue
        hit = set(npos[k:k+len(want)])
        # split every touched segment at the hit boundaries and mark the inside part
        for ln, (head, segs) in enumerate(lines):
            new = []
            base = sum(1 for _ in ())  # placeholder
            for sn, seg in enumerate(segs):
                t, st, h = seg
                # character positions of this segment in the stream
                pos = [i for i, ix in enumerate(index) if ix and ix[0] == ln and ix[1] == sn]
                flags = [p in hit for p in pos]
                if not any(flags): new.append(seg); continue
                run, cur = [], flags[0]
                start = 0
                for ci in range(1, len(t) + 1):
                    if ci == len(t) or flags[ci] != cur:
                        new.append([t[start:ci], st, spec['url'] if cur else h])
                        if ci < len(t): start, cur = ci, flags[ci]
            lines[ln][1] = new
        links_out.append(spec['url'])

HEAD = '''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s &mdash; page %(n)d</title>
<link rel="stylesheet" href="../../assets/fonts.css">
<style>
html,body{margin:0;padding:0;background:#fff}
.sheet{width:calc(%(wmm).2fmm * var(--k,1));height:calc(%(hmm).2fmm * var(--k,1));overflow:hidden;position:relative}
.scaler{transform:scale(calc(%(scaler).5f * var(--k,1)));transform-origin:top left}
.page{position:relative;width:%(pw)dpx;height:%(ph)dpx}
.page img.bg{position:absolute;left:0;top:0;width:%(pw)dpx;height:%(ph)dpx}
p{margin:0;position:absolute}
a{color:inherit}
a:hover{text-decoration:underline}
</style></head><body><div class="sheet"><div class="scaler"><div class="page">
'''

TAIL = '''<script>
/* The reader tells this page how big to draw itself, so text is re-rendered at the new size
   instead of being stretched as a bitmap (which is what happens when an iframe is transform-scaled). */
(function(){
  function setK(k){ document.documentElement.style.setProperty('--k', String(k)); }
  window.addEventListener('message',function(e){ var m=e.data; if(m&&m.abj==='zoom'&&isFinite(m.k)&&m.k>0) setK(m.k); });
})();
</script>
<script>
/* Fit each line to the width it occupied in the PDF: stretch the spaces on
   justified lines, and tighten any line the substitute font renders too wide
   (which would otherwise run into the next column). Backs off rather than
   crushing the spacing when a line is too far off to fix. */
(function(){
  function fit(){
    var ps=document.querySelectorAll('p[data-w]');
    for(var i=0;i<ps.length;i++){
      var p=ps[i];
      p.style.wordSpacing=''; p.style.letterSpacing='';
      var target=parseFloat(p.getAttribute('data-w')), nat=p.offsetWidth;
      if(!target||!nat) continue;
      var d=target-nat, stretch=p.hasAttribute('data-j');
      if(Math.abs(d)<0.5) continue;
      if(d>0&&!stretch) continue;
      if(Math.abs(d)>target*0.18){ continue; }
      var txt=p.textContent||'', sp=(txt.match(/ /g)||[]).length;
      var fs=parseFloat(getComputedStyle(p).fontSize)||12;
      if(sp>0){
        var ws=d/sp, cap=fs*0.6, floor=-fs*0.06;
        if(ws>cap)ws=cap; if(ws<floor)ws=floor;
        p.style.wordSpacing=ws.toFixed(3)+'px';
        d=target-p.offsetWidth;
      }
      if(d<-0.5){
        var n=Math.max(1,txt.length-1), ls=d/n, lf=-fs*0.02;
        if(ls<lf)ls=lf;
        p.style.letterSpacing=ls.toFixed(3)+'px';
      }
    }
  }
  fit();
  if(document.fonts&&document.fonts.ready) document.fonts.ready.then(fit);
  window.addEventListener('resize',fit);
})();
</script>
<style>html.bee-on,html.bee-on *{cursor:none !important}</style>
<script>
/* Report the pointer to the parent reader so its bee can follow across the page,
   and hide this document's own cursor only once the parent confirms the bee is on. */
(function(){
  if(window.parent===window) return;
  /* a click on the page itself (not on one of its links) is the parent's business - in the stack it opens
     the card. A drag is a text selection, not a click. This runs on touch devices too. */
  var cx0=0, cy0=0;
  document.addEventListener('mousedown',function(e){ cx0=e.clientX; cy0=e.clientY; });
  document.addEventListener('click',function(e){
    if(e.target&&e.target.closest&&e.target.closest('a[href]')) return;
    if(Math.abs(e.clientX-cx0)>6||Math.abs(e.clientY-cy0)>6) return;
    try{ parent.postMessage({abj:'click'},'*'); }catch(err){}
  });
  if(!matchMedia('(hover:hover)').matches) return;
  if(matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  window.addEventListener('message',function(e){
    var m=e.data; if(m&&m.abj==='bee') document.documentElement.classList.toggle('bee-on',!!m.on);
  });
  try{ parent.postMessage({abj:'hello'},'*'); }catch(e){}
  var raf=0,px=0,py=0;
  var plink=false;
  document.addEventListener('mousemove',function(e){
    px=e.clientX; py=e.clientY;
    plink=!!(e.target&&e.target.closest&&e.target.closest('a[href]'));
    if(!raf) raf=requestAnimationFrame(function(){ raf=0;
      try{ parent.postMessage({abj:'pointer',x:px,y:py,link:plink},'*'); }catch(err){} });
  },{passive:true});
  document.addEventListener('mouseleave',function(){
    try{ parent.postMessage({abj:'pointerleave'},'*'); }catch(err){} });
})();
</script>
</body></html>
'''

def build_article(pdf_path, first_pno, last_pno, outdir, title, manual=(), ocr=False):
    os.makedirs(outdir, exist_ok=True)
    doc = fitz.open(pdf_path)
    alltext, links = [], []
    for n, pno in enumerate(range(first_pno, last_pno + 1), start=1):
        alltext.append(build_page(doc, pno, outdir, n, title, links, manual, ocr))
    W, H = doc[first_pno].rect.width, doc[first_pno].rect.height
    json.dump({'pages': alltext, 'links': sorted(set(links)), 'pt': [W, H]}, open(os.path.join(outdir, 'text.json'), 'w'), ensure_ascii=False, indent=0)
    doc.close()
    return last_pno - first_pno + 1, (W * PT_MM, H * PT_MM)

if __name__ == '__main__':
    site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meta = json.load(open(os.path.join(site, '_articles_meta.json')))
    src_us = os.path.dirname(site)
    src_au = os.environ.get('VBJ', os.path.join(os.path.dirname(os.path.dirname(site)), 'VBJ'))
    AU = {'apr': '2026 04 Victorian Bee Journal.pdf', 'may': '2026 05 Victorian Bee Journal.pdf', 'jun': '2026 06 Victorian Bee Journal.pdf',
          'jul': 'VABJ 2026 07 Final.pdf', 'aug': '2026 08 Victorian Bee Journal.pdf'}
    only = sys.argv[1:]
    for a in meta:
        if only and a['id'] not in only: continue
        out = os.path.join(os.environ.get('OUT', os.path.join(site, 'pages')), a['id'])
        AUQUOTES = a['id'].startswith('aus')
        LIGFIX = bool(a.get('ligfix'))
        if isinstance(a['src'], str):
            pdf = os.path.join(src_us, a['src']); f, l = 0, fitz.open(pdf).page_count - 1
        else:
            pdf = os.path.join(src_au, AU[a['src']['iss']]); f, l = a['src']['p'][0] - 1, a['src']['p'][1] - 1
        n, mm = build_article(pdf, f, l, out, a['title'], a.get('links', ()), a.get('ocr', False))
        a['n'] = n; a['mm'] = [round(mm[0], 2), round(mm[1], 2)]
        print('%-14s %2d pages  %.0fx%.0f mm  %s' % (a['id'], n, mm[0], mm[1], a['title'][:50]))
    json.dump(meta, open(os.path.join(site, '_articles_meta.json'), 'w'), indent=1)
