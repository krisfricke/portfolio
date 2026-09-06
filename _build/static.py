#!/usr/bin/env python3
"""Static, text-only front doors: article/<id>/index.html, article/index.html, sitemap.xml, robots.txt.
These are what search engines, screen readers, Lynx and anyone without JavaScript get."""
import json, os, re, html, datetime
site=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg=json.load(open(os.path.join(site,'_config.json')))
meta=json.load(open(os.path.join(site,'_articles_meta.json')))
BASE=cfg['base']; AUTHOR=cfg['author']; CITE_AU=cfg['author_cite']
MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December']
E=lambda s:html.escape(s,quote=True)
def when(a): return MONTHS[a['month']-1]+' '+str(a['year'])
def prange(a): p=a['pages']; return str(p[0]) if p[0]==p[1] else '%d–%d'%(p[0],p[1])
def cite(a,as_html=True):
    t=a['title'].rstrip('.'); end='' if re.search(r'[?!]$',t) else '.'
    vol=(', %s'%a['vol']+('(%s)'%a['no'] if a.get('no') else '')) if a.get('vol') else ''
    pp=', '+prange(a) if a.get('pages') else ''
    head='%s (%d). “%s%s” '%(CITE_AU,a['year'],t,end)
    return (E(head)+'<i>'+E(a['pub'])+'</i>'+E(vol+pp)+'.') if as_html else head+a['pub']+vol+pp+'.'
def sortkey(a): return (a['year'],a['month'],a['pages'][0])
CSS='''
:root{--ink:#14293b;--ink2:#3d6079;--gold:#f9c500}
body{margin:0;background:linear-gradient(180deg,#7db4dc,#a9d2ec 46%,#d3e8f7) fixed;color:#1d1b16;font:17px/1.6 Georgia,'Times New Roman',serif}
main{max-width:760px;margin:0 auto;padding:28px 22px 60px}
.card{background:#faf8f2;border-radius:14px;padding:32px 36px;box-shadow:0 18px 50px rgba(20,60,90,.25)}
h1{font:700 30px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);margin:0 0 6px}
h2{font:700 20px/1.3 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);margin:30px 0 8px}
.by{color:var(--ink2);font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin-bottom:14px}
.cite{background:#fff;border:1px solid #c0a06a;border-radius:8px;padding:12px 16px;margin:14px 0 20px;font-size:15px}
.cite small{display:block;color:#6a5a3a;font:12px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin-top:4px}
a{color:#0f4b70}
.btn{display:inline-block;background:var(--gold);color:#111;font:700 14px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:11px 18px;border-radius:22px;text-decoration:none;margin:2px 8px 12px 0}
.btn.sec{background:#fff;border:1px solid #7ea9c6;color:#17313f}
.tags{margin:6px 0 22px}
.tags a{display:inline-block;font:12px/1.7 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#fff;border:1px solid #cfe0ee;border-radius:11px;padding:0 9px;margin:0 5px 5px 0;text-decoration:none;color:#17313f}
.pg{color:#8a8472;font:12px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;margin:26px 0 10px;border-top:1px dashed #cbb083;padding-top:10px}
p{margin:0 0 1em}
.note{color:#6d6857;font:13px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin-top:28px;border-top:1px solid #e3dccb;padding-top:12px}
nav.top{font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin-bottom:14px;color:#2b4d63}
ul.list{list-style:none;padding:0;margin:0}
ul.list li{margin:0 0 16px;padding-left:0}
ul.list li a.t{font:600 17px/1.3 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;text-decoration:none;color:var(--ink)}
ul.list li a.t:hover{text-decoration:underline}
ul.list li .c{font-size:14px;color:#3a3a3a;margin-top:2px}
.links li{font-size:14px;word-break:break-all}
'''
def shell(title,body,canon,desc):
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>%s</title><meta name="description" content="%s"><link rel="canonical" href="%s"><link rel="icon" type="image/png" href="../../assets/bee/favicon.png"><style>%s</style></head><body><main><div class="card">%s</div></main></body></html>')%(E(title),E(desc),E(canon),CSS,body)

def clean_paras(a,pages):
    """Reading text from the block list: drop running heads, merge drop caps, keep body-sized blocks in order."""
    out=[]
    title_k=re.sub(r'\W+','',a['title']).lower()
    from collections import Counter
    vocab=Counter(w.lower() for pg in pages for p in pg['paras'] for w in re.findall(r"[A-Za-z']+",p['t']))
    W=a.get('ptw',576)
    for n,pg in enumerate(pages,1):
        paras=sorted(pg['paras'],key=lambda p:(int(p['x']//(W/3.0)),p['y'])); body=[]   # column by column, top to bottom
        sizes=sorted(p['size'] for p in paras if len(p['t'])>80)
        bodysz=sizes[len(sizes)//2] if sizes else 10
        pend=None
        for p in paras:
            t=p['t'].strip()
            if not t: continue
            k=re.sub(r'\W+','',t).lower()
            if re.fullmatch(r'(%s)\s+\d{4}\s*\d*|\d+\s*|american bee journal\s*\d*|\d*\s*australian bee journal\s*|(%s)\s+\d{4}'%('|'.join(MONTHS),'|'.join(MONTHS)),t,re.I): continue
            if k and (k==title_k or k in ('bykrisfricke','krisfricke')): continue
            if len(t)<=2 and t.isalpha():                  # drop cap: glue to the next block
                pend=t; continue
            if pend:
                first=re.match(r"[A-Za-z']+",t); first=first.group(0).lower() if first else ''
                # "I" + "have" -> "I have"; "R" + "ows" -> "Rows": glue only when the fragment is not itself a word used elsewhere
                t=(pend+' '+t) if (vocab[first]>1 and len(first)>1) else pend+t
                pend=None
            if p['size']>bodysz*1.35 and len(t)<90:        # display type: heading / caption title
                m=re.match(r'^(.*\S)\s+([A-Z])$',t)         # a drop cap swept into the heading's block
                if m: t,pend=m.group(1),m.group(2)
                if body and body[-1][0]=='h': body[-1]=('h',body[-1][1]+' '+t)
                else: body.append(('h',t))
                continue
            body.append(('p',t))
        body=[(k,t) for k,t in body if not (k=='h' and re.sub(r'\W+','',t).lower()==title_k)]
        if a.get('ocr'):                                   # OCR gives one block per line: rejoin into paragraphs
            merged=[]
            def shouty(t):
                L=[c for c in t if c.isalpha()]; return len(L)>=6 and sum(c.isupper() for c in L)/len(L)>0.85
            body=[('h' if (k=='p' and shouty(t)) else k,t) for k,t in body]
            for k,t in body:
                if merged and merged[-1][0]=='p' and k=='p' and not re.search(r'[.!?:”"\)]$',merged[-1][1]):
                    pt=merged[-1][1]; merged[-1]=('p',(pt[:-1]+t) if pt.endswith('-') and t[:1].islower() else pt+' '+t)
                else: merged.append((k,t))
            body=merged
        out.append(body)
    return out

adir=os.path.join(site,'article'); os.makedirs(adir,exist_ok=True)
urls=[BASE, BASE+'article/']
ordered=sorted(meta,key=sortkey,reverse=True)
for a in ordered:
    tj=json.load(open(os.path.join(site,'pages',a['id'],'text.json')))
    a['ptw']=tj['pt'][0]
    pages=clean_paras(a,tj['pages'])
    reader='../../index.html#/read/'+a['id']
    parts=['<nav class="top"><a href="../index.html">All articles</a> &rsaquo; %s, %s</nav>'%(E(a['pub']),E(when(a)))]
    parts.append('<h1>%s</h1><div class="by">by %s &middot; %s, %s%s</div>'%(E(a['title']),E(AUTHOR),E(a['pub']),E(when(a)),(' &middot; pp. '+prange(a)) if a.get('pages') else ''))
    parts.append('<div class="cite">%s<small>Suggested citation</small></div>'%cite(a))
    parts.append('<a class="btn" href="%s">Read the pages as printed</a><a class="btn sec" href="%s">Open this reader at page 1</a>'%(reader,'../../index.html#/article/'+a['id']+'/1'))
    parts.append('<div class="tags">'+''.join('<a href="../../index.html#/topic/%s">%s</a>'%(E(t.lower()),E(t)) for t in a['tags'])+'</div>')
    parts.append('<h2>Text of the article</h2>')
    manual=a.get('links',[])
    for n,body in enumerate(pages,1):
        parts.append('<div class="pg">Page %d of %d &middot; printed page %d</div>'%(n,a['n'],a['pages'][0]+n-1))
        for kind,t in body:
            h=E(t)
            for spec in manual:                      # phrase links given in the metadata
                if spec.get('page')==n:
                    pat=re.compile(r'\s+'.join(re.escape(w) for w in E(spec['text']).split()),re.I)
                    h,k=pat.subn(lambda m:'<a href="%s">%s</a>'%(E(spec['url']),m.group(0)),h,count=1)
                    if k: spec['_done']=True
            parts.append(('<h2>%s</h2>' if kind=='h' else '<p>%s</p>')%h)
    for spec in manual:
        if not spec.get('_done'): print('   manual link phrase not found in text page:',a['id'],spec['text'])
    if tj.get('links'):
        parts.append('<h2>Links in the article</h2><ul class="links">'+''.join('<li><a href="%s" rel="noopener">%s</a></li>'%(E(u),E(u)) for u in tj['links'])+'</ul>')
    parts.append('<p class="note">This is the plain-text version, extracted from the printed pages for readers who use screen readers, text-only browsers, or prefer reflowable text. Captions and sidebars appear where they fell in the page layout. The typeset pages are available in the <a href="%s">reader</a>.</p>'%reader)
    desc='%s — %s, %s. By %s.'%(a['title'],a['pub'],when(a),AUTHOR)
    d=os.path.join(adir,a['id']); os.makedirs(d,exist_ok=True)
    open(os.path.join(d,'index.html'),'w',encoding='utf-8').write(shell(a['title']+' — '+AUTHOR,''.join(parts),BASE+'article/'+a['id']+'/',desc))
    urls.append(BASE+'article/'+a['id']+'/')
# hub
pubs={}
for a in ordered: pubs.setdefault(a['pub'],[]).append(a)
hub=['<nav class="top"><a href="../index.html">Open the reader</a></nav><h1>Articles by %s</h1><div class="by">%d articles &middot; newest first &middot; each links to its plain-text version; the <a href="../index.html">reader</a> shows the pages as printed.</div>'%(E(AUTHOR),len(meta))]
for pub,items in pubs.items():
    hub.append('<h2>%s</h2><ul class="list">'%E(pub))
    for a in items:
        hub.append('<li><a class="t" href="%s/index.html">%s</a><div class="c">%s</div></li>'%(a['id'],E(a['title']),cite(a)))
    hub.append('</ul>')
open(os.path.join(adir,'index.html'),'w',encoding='utf-8').write(shell('Articles by '+AUTHOR,''.join(hub),BASE+'article/','All articles by %s, with citations and plain-text versions.'%AUTHOR).replace('href="../../assets/bee/favicon.png"','href="../assets/bee/favicon.png"'))
today=datetime.date.today().isoformat()
open(os.path.join(site,'sitemap.xml'),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n'%(E(u),today) for u in urls)+'</urlset>\n')
open(os.path.join(site,'robots.txt'),'w').write('User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n'%BASE)
print('wrote',len(meta),'article pages, hub, sitemap (%d urls), robots'%len(urls))
