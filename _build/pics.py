#!/usr/bin/env python3
"""Photos: cut each picture out of the PDF at its native resolution and lay an invisible hotspot over it
on the page, so the reader can grow it on hover / open it on click. Run after buildpages.py; idempotent."""
import json, os, re, sys, html
import pymupdf as fitz
site=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
meta=json.load(open(os.path.join(site,'_articles_meta.json')))
src_us=os.path.dirname(site); src_au=os.environ.get('VBJ',os.path.join(os.path.dirname(os.path.dirname(site)),'VBJ'))
AU={'apr':'2026 04 Victorian Bee Journal.pdf','may':'2026 05 Victorian Bee Journal.pdf','jun':'2026 06 Victorian Bee Journal.pdf','jul':'VABJ 2026 07 Final.pdf','aug':'2026 08 Victorian Bee Journal.pdf'}
SCALE=1.6
CSS='<style>a.pic{position:absolute;display:block;z-index:4;cursor:zoom-in}</style>\n'
JS='''<script>
/* Pictures: tell the reader when the pointer is over one (it grows it there); on its own, open the file. */
(function(){
  var inParent=(window.parent&&window.parent!==window);
  document.querySelectorAll('a.pic').forEach(function(a,i){
    var src=new URL(a.getAttribute('data-src'),location.href).href;
    a.href=src; a.target='_blank'; a.rel='noopener';
    function rect(){ var r=a.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height}; }
    a.addEventListener('mouseenter',function(){ if(!inParent) return;
      try{ parent.postMessage({abj:'pic',id:location.pathname+'#'+i,src:src,r:rect(),nw:+a.getAttribute('data-nw'),nh:+a.getAttribute('data-nh')},'*'); }catch(e){} });
    a.addEventListener('mouseleave',function(){ if(!inParent) return; try{ parent.postMessage({abj:'picleave',id:location.pathname+'#'+i},'*'); }catch(e){} });
    a.addEventListener('click',function(e){ if(inParent){ e.preventDefault(); try{ parent.postMessage({abj:'picclick',id:location.pathname+'#'+i,src:src,r:rect(),nw:+a.getAttribute('data-nw'),nh:+a.getAttribute('data-nh')},'*'); }catch(err){} } });
  });
})();
</script>
'''
only=sys.argv[1:]
tot=0
for a in meta:
    if only and a['id'] not in only: continue
    if isinstance(a['src'],str): pdf=os.path.join(src_us,a['src']); f,l=0,None
    else: pdf=os.path.join(src_au,AU[a['src']['iss']]); f,l=a['src']['p'][0]-1,a['src']['p'][1]-1
    d=fitz.open(pdf); l=d.page_count-1 if l is None else l
    outdir=os.path.join(site,'pages',a['id'])
    for pno in range(f,l+1):
        n=pno-f+1; pg=d[pno]; W,H=pg.rect.width,pg.rect.height
        hp=os.path.join(outdir,'%d.html'%n)
        if not os.path.exists(hp): continue
        s=open(hp,encoding='utf-8').read()
        s=re.sub(r'\n<a class="pic"[^>]*></a>','',s); s=s.replace(CSS,'').replace(JS,'')
        tags=''; i=0
        for im in pg.get_image_info(xrefs=True):
            b=fitz.Rect(im['bbox']) & pg.rect
            if b.width<60 or b.height<60 or b.get_area()/(W*H)>0.85: continue
            ppi=im['width']/(b.width/72); dpi=int(min(300,max(110,ppi)))
            if dpi<=118: continue                       # nothing to gain over the page render
            i+=1; fn='hi%d_%d.jpg'%(n,i)
            pix=pg.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),clip=b,alpha=False)
            pix.save(os.path.join(outdir,fn),jpg_quality=86)
            tags+='\n<a class="pic" data-src="%s" data-nw="%d" data-nh="%d" style="left:%.1fpx;top:%.1fpx;width:%.1fpx;height:%.1fpx" title="Enlarge picture" aria-label="Picture"></a>'%(fn,pix.width,pix.height,b.x0*SCALE,b.y0*SCALE,b.width*SCALE,b.height*SCALE)
            tot+=1
        if tags:
            s=s.replace('\n</div></div></div>',tags+'\n</div></div></div>',1)
            s=s.replace('</style></head>','</style>'+CSS+'</head>',1) if CSS not in s else s
            s=s.replace('<style>html.bee-on',JS+'<style>html.bee-on',1)
        open(hp,'w',encoding='utf-8').write(s)
    print(a['id'],'done')
print('pictures:',tot)
