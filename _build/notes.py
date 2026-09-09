"""Footnotes and references as hover text.

An article's superscript markers (1, 2, *, †) point at notes that sit at the foot of a page or in a
references list at the end. This finds those notes in the PDF text and hands back
    NOTES  - {marker: note text}
    STARTS - {(page number, round(y))} the lines where a note itself begins, so the number that opens
             a note is not treated as a reference to itself
The page builder wraps each body superscript that has a note in a <span class="fn" data-note="...">, and the
page script shows the note when the pointer rests on it (or it is tapped, or it takes keyboard focus).

What counts as a note: a line that opens with a small number (or symbol), then text starting with a capital,
a quote, a bracket or a web address. Numbers must run in sequence from 1 - a "2)" or a "13 years" in body
copy does not qualify - unless the line is set smaller than the body text, which is how footnotes and
reference lists are usually set. The note runs on through the lines beneath it in the same column until the
next note, a change of type size, or a gap. Line-end hyphens are healed when the next line starts lower-case.
"""
import re
from collections import Counter

MARK = re.compile(r'^\s*(\d{1,2}|\*{1,3}|†|‡)\s*(?:[.)]\s*|\s+)(\S.*)$')
GOOD_START = re.compile(r'^[A-Z“"\'‘(\[]|^https?://|^www\.')

def _lines(page, clean, n):
    """Sewn lines on one page: page n, x0, y0, size, text, sup (a leading superscript marker, or '')."""
    d = page.get_text('dict')
    out = []
    W = page.rect.width
    for b in d['blocks']:
        if b['type'] != 0: continue
        rows = {}
        for l in b['lines']:
            if abs(l['dir'][0]) < 0.9: continue
            if not any(s['text'] for s in l['spans']): continue
            rows.setdefault(round(l['bbox'][3]), []).append(l)
        for key, ls in rows.items():
            ls.sort(key=lambda l: l['bbox'][0])
            spans = [s for l in ls for s in l['spans'] if s['text']]
            def _t(k, s):
                t = clean(s['text'])
                # a superscript reference inside a note reads as "[3]" rather than fusing with the word before it
                if k and (s['flags'] & 1) and re.fullmatch(r'\s*(\d{1,2}|\*{1,3}|†|‡)\s*', t): return '[' + t.strip() + ']'
                return t
            text = ''.join(_t(k, s) for k, s in enumerate(spans))
            if not text.strip(): continue
            sup = ''
            first = next((s for s in spans if s['text'].strip()), None)
            if first is not None and (first['flags'] & 1):
                m = re.fullmatch(r'\s*(\d{1,2}|\*{1,3}|†|‡)\s*', clean(first['text']))
                if m: sup = m.group(1)
            sizes = Counter()
            for s in spans:
                if s['text'].strip() and not (s['flags'] & 1): sizes[round(s['size'] * 2) / 2] += len(s['text'].strip())   # by characters: a small note number does not set the line's size
            size = sizes.most_common(1)[0][0] if sizes else round(spans[0]['size'] * 2) / 2
            x0 = min(l['bbox'][0] for l in ls); y0 = min(l['bbox'][1] for l in ls)
            out.append({'n': n, 'x': x0, 'y': y0, 'size': size, 'text': text, 'sup': sup, 'col': 0})
    # columns: cluster the left edges - a new column wherever the sorted edges jump by more than 40 pt
    xs = sorted(set(round(l['x']) for l in out)); cols = {}; c = 0
    for i, x in enumerate(xs):
        if i and x - xs[i - 1] > 40: c += 1
        cols[x] = c
    for l in out: l['col'] = cols[round(l['x'])]
    return out

def _join(parts):
    out = ''
    for p in parts:
        p = p.strip()
        if not p: continue
        if out.endswith('-') and p[:1].islower(): out = out[:-1] + p
        else: out = (out + ' ' + p).strip()
    return out

def harvest(doc, pnos, clean):
    """doc: an open fitz document; pnos: the article's page indexes in order; clean: the builder's text cleaner."""
    lines = []
    for n, pno in enumerate(pnos, start=1):
        lines += _lines(doc[pno], clean, n)
    if not lines: return {}, set()
    cnt = Counter()
    for l in lines: cnt[l['size']] += len(l['text'])
    body = cnt.most_common(1)[0][0]                      # the body size: the commonest by characters
    lines.sort(key=lambda l: (l['n'], l['col'], l['y'], l['x']))
    cands = []
    for i, l in enumerate(lines):
        if l['sup']:
            rest = l['text'].strip()
            if rest.startswith(l['sup']): rest = rest[len(l['sup']):]
            rest = re.sub(r'^\s*[.)]?\s*', '', rest)
            mark = l['sup']
        else:
            m = MARK.match(l['text'])
            if not m: continue
            mark, rest = m.group(1), m.group(2)
        if len(rest.strip()) < 3 or not GOOD_START.match(rest.strip()): continue
        cands.append((i, mark, rest))
    small = lambda l: l['size'] <= body - 0.9
    expect = 1; starts = []
    for i, mark, rest in cands:
        l = lines[i]
        if mark.isdigit():
            num = int(mark)
            if num == expect: starts.append((i, mark, rest)); expect = num + 1
            elif num > expect and small(l) and num - expect <= 3: starts.append((i, mark, rest)); expect = num + 1
            elif small(l) and 1 <= num < expect and not any(s[1] == mark for s in starts): starts.append((i, mark, rest))
        else:
            if small(l) or l['sup']: starts.append((i, mark, rest))
    notes = {}; start_keys = set()
    start_idx = {i for i, _, _ in starts}
    for i, mark, rest in starts:
        l0 = lines[i]; parts = [rest]; prev = l0
        # the note continues down its own column: lines below it whose left edge sits within the column's
        # window (flush, or indented under a hanging number); other columns' lines are simply not looked at
        below = [(j, l) for j, l in enumerate(lines) if l['n'] == l0['n'] and l['y'] > l0['y'] + 1 and -24 <= l['x'] - l0['x'] <= 70]   # flush, hanging either way, or indented
        below.sort(key=lambda jl: jl[1]['y'])
        exhausted = True
        for j, l in below:
            if j in start_idx: exhausted = False; break
            if abs(l['size'] - l0['size']) > 0.6 or l['y'] - prev['y'] > l0['size'] * 2.1: break
            parts.append(l['text']); prev = l
        sofar = _join(parts)
        unfinished = sofar.endswith(('-', ',', ';', ':')) or not sofar.rstrip().endswith(('.', ')', ']', '”', '"', '/'))
        if exhausted and (unfinished or small(l0)):
            # the column ran out under the note: it may carry on at the top of the next column (or page)
            nxt = [(j, l) for j, l in enumerate(lines) if l['n'] == l0['n'] and l['x'] > l0['x'] + 70 and abs(l['size'] - l0['size']) <= 0.6]
            if not nxt: nxt = [(j, l) for j, l in enumerate(lines) if l['n'] == l0['n'] + 1 and abs(l['size'] - l0['size']) <= 0.6]
            if nxt:
                cx = min(l['x'] for _, l in nxt)
                col = sorted([(j, l) for j, l in nxt if abs(l['x'] - cx) <= 24 and (l['n'] != l0['n'] or l['y'] < l0['y'])], key=lambda jl: jl[1]['y'])
                prev = None; broken = _join(parts).endswith('-')     # a word split at the column break
                for j, l in col:
                    if j in start_idx: break
                    if broken and prev is None and not l['text'].strip()[:1].islower(): continue   # a caption or heading sits above the continuation
                    if prev is not None and l['y'] - prev['y'] > l0['size'] * 2.1: break
                    parts.append(l['text']); prev = l
        text = _join(parts)
        if mark not in notes and len(text) >= 4: notes[mark] = text
        start_keys.add((l0['n'], round(l0['y'])))
    return notes, start_keys

MARKS_IN_SUP = re.compile(r'^\s*((?:\d{1,2}|\*{1,3}|†|‡)(?:\s*,\s*(?:\d{1,2}|\*{1,3}|†|‡))*)\s*$')

def markers(text):
    """The markers in a superscript span's text: '1' -> ['1'], '1,2' -> ['1','2'], 'nd' -> []."""
    m = MARKS_IN_SUP.match(text or '')
    if not m: return []
    return [p.strip() for p in m.group(1).split(',')]

def note_for(marks, notes):
    """The hover text for a marker list, or None when nothing is known for any of them."""
    got = [(k, notes[k]) for k in marks if k in notes]
    if not got: return None
    if len(got) == 1: return got[0][1]
    return '\n\n'.join('%s  %s' % (k, v) for k, v in got)

CSS = '''
.fn{cursor:help;border-bottom:1px dotted rgba(0,0,0,.35)}
.fn:hover,.fn:focus{outline:none;background:rgba(249,197,0,.28)}
.fnpop{position:fixed;z-index:20;display:none;max-width:380px;padding:9px 12px 10px;border-radius:8px;background:#fffdf5;color:#1a1a1a;
  border:1px solid #c9a95f;box-shadow:0 8px 24px rgba(0,0,0,.22);font:13px/1.45 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;white-space:pre-line;pointer-events:none}
.fnpop b{color:#6a5a3a;font-weight:700;margin-right:6px}
'''

JS = '''
/* Footnotes as hover text: rest on a superscript that has a note and the note appears beside it;
   a tap does the same on a touch screen; Esc or moving away hides it. */
(function(){
  var pop=null, cur=null;
  function show(el){
    if(!pop){ pop=document.createElement('div'); pop.className='fnpop'; pop.setAttribute('role','tooltip'); document.body.appendChild(pop); }
    var n=el.getAttribute('data-n'); pop.innerHTML=(n?'<b>'+n+'</b>':'')+el.getAttribute('data-note').replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});
    pop.style.display='block'; pop.style.left='0px'; pop.style.top='0px';
    var r=el.getBoundingClientRect(), pw=pop.offsetWidth, ph=pop.offsetHeight;
    var x=Math.min(Math.max(6,r.left+r.width/2-pw/2), innerWidth-pw-6), y=r.top-ph-8;
    if(y<4) y=r.bottom+8;
    pop.style.left=x+'px'; pop.style.top=y+'px'; cur=el;
  }
  function hide(){ if(pop) pop.style.display='none'; cur=null; }
  var fns=document.querySelectorAll('.fn');
  for(var i=0;i<fns.length;i++){
    var el=fns[i];
    el.addEventListener('mouseenter',function(){ show(this); });
    el.addEventListener('mouseleave',hide);
    el.addEventListener('focus',function(){ show(this); });
    el.addEventListener('blur',hide);
    el.addEventListener('click',function(e){ e.preventDefault(); e.stopPropagation(); if(cur===this) hide(); else show(this); });
  }
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') hide(); });
  document.addEventListener('click',function(){ hide(); });
  window.addEventListener('scroll',hide,true);
})();
'''
