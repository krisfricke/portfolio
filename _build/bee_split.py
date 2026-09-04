import numpy as np, cv2, json, os
from PIL import Image
im=Image.open('Bee 3bd.gif').convert('RGBA'); a=np.array(im); H,W=a.shape[:2]
alpha=a[...,3]>0; rgb=a[...,:3].astype(int); r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
E=lambda k:cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k))
def bigcomps(m,minarea):
    n,lab,st,_=cv2.connectedComponentsWithStats(m.astype(np.uint8),8)
    return np.isin(lab,[i for i in range(1,n) if st[i][4]>=minarea])
wingfill=bigcomps(alpha&(b>200)&(r>180)&(g>220),500)
yellow=alpha&(r>200)&(g>150)&(b<120)
ys,xs=np.where(yellow); X=np.arange(W)[None,:]; Y=np.arange(H)[:,None]
col=(X>=xs.min()-16)&(X<=xs.max()+16)
wingzone=cv2.dilate(wingfill.astype(np.uint8),E(11))>0
body=bigcomps(alpha&col&~wingzone,400)
thorax=yellow&(Y<330); cy,cx=np.mean(np.where(thorax),axis=1); cx=int(cx); cy=int(cy)
rows=(Y>252)&(Y<445)
closed=cv2.morphologyEx((body&rows).astype(np.uint8),cv2.MORPH_CLOSE,E(45))>0
hole=closed&~body&rows&~wingfill
out=np.zeros_like(a); out[body]=a[body]
# fill holes with the nearest body colour in the same row, walking toward the centre line
hy,hx=np.where(hole)
for y,x in zip(hy,hx):
    step=1 if x<cx else -1; xx=x
    while 0<=xx<W and not body[y,xx]: xx+=step
    out[y,x]=a[y,xx] if 0<=xx<W else [247,204,30,255]
body2=body|hole
outl=(cv2.dilate(body2.astype(np.uint8),E(3))>0)&~(cv2.erode(body2.astype(np.uint8),E(11))>0)&(cv2.dilate(hole.astype(np.uint8),E(9))>0)&rows
out[outl]=[40,40,45,255]
body3=body2|outl
wings=bigcomps(alpha&~body3,300)
wl=wings&(X<cx); wr=wings&(X>=cx)
layers={'body':out}
for nm,m in (('wl',wl),('wr',wr)):
    o=np.zeros_like(a); o[m]=a[m]; layers[nm]=o
roots={}
for nm,tx in (('wl',cx-45),('wr',cx+45)):
    yy,xx=np.where(layers[nm][...,3]>0); d=(xx-tx)**2+(yy-(cy+5))**2; j=d.argmin(); roots[nm]=(int(xx[j]),int(yy[j]))
ys,xs=np.where(alpha); x0,x1,y0,y1=xs.min()-6,xs.max()+7,ys.min()-6,ys.max()+7
S=200/(x1-x0)
for nm,arr in layers.items():
    Image.fromarray(arr[y0:y1,x0:x1]).resize((200,round((y1-y0)*S)),Image.LANCZOS).save(f'/tmp/bee/{nm}.png')
meta={'w':200,'h':int(round((y1-y0)*S)),'roots':{k:[float(round((v[0]-x0)*S,1)),float(round((v[1]-y0)*S,1))] for k,v in roots.items()},'centre':[float(round((cx-x0)*S,1)),float(round((cy-y0)*S,1))]}
json.dump(meta,open('/tmp/bee/meta.json','w')); print(meta)
def compose(rot,scale,wing_alpha=1.0):
    base=Image.open('/tmp/bee/body.png').convert('RGBA'); cw,ch=base.size
    wings=Image.new('RGBA',(cw,ch),(0,0,0,0))
    for nm,sgn in (('wl',1),('wr',-1)):
        w=Image.open(f'/tmp/bee/{nm}.png').convert('RGBA'); rx,ry=meta['roots'][nm]; sw,sh=scale
        if scale!=(1,1):
            w2=w.resize((round(cw*sw),round(ch*sh)),Image.LANCZOS); tmp=Image.new('RGBA',(cw,ch)); tmp.paste(w2,(round(rx-rx*sw),round(ry-ry*sh))); w=tmp
        w=w.rotate(sgn*rot,resample=Image.BICUBIC,center=(rx,ry))
        if wing_alpha<1:
            wa=np.array(w); wa[...,3]=(wa[...,3]*wing_alpha).astype(np.uint8); w=Image.fromarray(wa)
        wings.alpha_composite(w)
    c=Image.new('RGBA',(cw,ch))
    if rot==0: c.alpha_composite(wings); c.alpha_composite(base)
    else: c.alpha_composite(base); c.alpha_composite(wings)
    return c
fly=compose(0,(1,1)); fold=compose(76,(0.95,0.6),0.9); bodyonly=Image.open('/tmp/bee/body.png').convert('RGBA')
bg=Image.new('RGBA',(fly.width*3+40,fly.height),(158,201,230,255)); bg.alpha_composite(fly,(0,0)); bg.alpha_composite(bodyonly,(fly.width+20,0)); bg.alpha_composite(fold,(2*fly.width+40,0))
bg.convert('RGB').resize((bg.width*2,bg.height*2),Image.LANCZOS).save('/sessions/wizardly-festive-rubin/mnt/outputs/logo_bee_states.png')
