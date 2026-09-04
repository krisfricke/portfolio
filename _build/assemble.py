#!/usr/bin/env python3
"""Assemble index.html from the template halves, the article metadata and the bee geometry."""
import json, os
site=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl=os.path.join(site,'_build','templates')
cfg=json.load(open(os.path.join(site,'_config.json')))
meta=json.load(open(os.path.join(site,'_articles_meta.json')))
bee=json.load(open(os.path.join(site,'assets/bee/meta.json')))
arts=[{k:a.get(k) for k in ('id','pub','year','month','vol','no','pages','title','tags','n','mm')} for a in meta]
head=open(os.path.join(tpl,'index_head.html'),encoding='utf-8').read()
scr=open(os.path.join(tpl,'index_script.html'),encoding='utf-8').read()
def pct(p): return '%.1f%% %.1f%%'%(p[0]/bee['w']*100,p[1]/bee['h']*100)
head=head.replace('WL_ORIGIN',pct(bee['roots']['wl'])).replace('WR_ORIGIN',pct(bee['roots']['wr']))
head=head.replace('width:64px;height:47px','width:64px;height:%dpx'%round(64*bee['h']/bee['w']))
scr=scr.replace('__BASE__',cfg['base']).replace('__ARTS__',json.dumps(arts,ensure_ascii=False,separators=(',',':')))
scr=scr.replace("const HOME='https://krisfricke.github.io/';","const HOME=%s;"%json.dumps(cfg['home']))
scr=scr.replace("const AUTHOR_CITE='Fricke, K.';","const AUTHOR_CITE=%s;"%json.dumps(cfg['author_cite']))
out=head+scr
open(os.path.join(site,'index.html'),'w',encoding='utf-8').write(out)
print('index.html',len(out),'bytes,',len(arts),'articles')
