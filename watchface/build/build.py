import numpy as np, sys, os, math
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

SEC_L=(-78,-27); SEC_R=(29,80)          # what rotates
IP_L=(-88,-25);  IP_R=(27,118)          # what is erased from the dial (arm + sleeve drape)
R_CUT=22; R_KEEP=72
K_HOUR=1.20; K_MIN=1.50
FADE=(32.0,50.0)                        # soft dissolve into the chest, in face px @480
HEAD_C=(430.0,312.0); HEAD_R=56.0
# writes assets/<N>x<N>/ and preview/ next to the watchface folder
OUTD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '')

a=load(); m,model,r=figure_mask(a); H,W,_=a.shape
yy,xx=np.mgrid[0:H,0:W]
th=np.degrees(np.arctan2(xx-CX,-(yy-CY)))
resid=np.abs(a-model).max(axis=2)

def piece_of(sec):
    p=m&(th>=sec[0])&(th<=sec[1])&(r>=R_CUT)
    p=ndi.binary_opening(p,np.ones((3,3)))
    lab,n=ndi.label(p); sizes=ndi.sum(p,lab,range(1,n+1))
    return ndi.binary_fill_holes(lab==int(np.argmax(sizes))+1)
L=piece_of(SEC_L); Rt=piece_of(SEC_R)
def tip(p):
    rr=r[p]; i=int(np.argmax(rr)); return rr[i], th[p][i]
rl,tl=tip(L); rr_,tr=tip(Rt)
print(f'HOUR reach {rl*K_HOUR:.0f}px ({rl*K_HOUR/R*100:.0f}%)   MINUTE reach {rr_*K_MIN:.0f}px ({rr_*K_MIN/R*100:.0f}%)   robe hem ~224px (64%)')

clean=(r<R-8)&(~m)&(resid<40)
ipm=m&(((th>=IP_L[0])&(th<=IP_L[1]))|((th>=IP_R[0])&(th<=IP_R[1])))&(r>=R_KEEP)
hole=ndi.binary_dilation(ipm,np.ones((3,3)),iterations=3)
kf=(clean&~hole).astype(float)
fill=np.zeros_like(a); got=np.zeros(a.shape[:2],bool)
for sig,thr in [(6,0.10),(12,0.06),(24,0.03),(48,0.012),(96,0.003)]:
    den=ndi.gaussian_filter(kf,sig)
    num=np.stack([ndi.gaussian_filter(a[...,c]*kf,sig) for c in range(3)],-1)
    est=num/np.maximum(den,1e-9)[...,None]
    take=(den>thr)&(~got)&hole
    fill[take]=est[take]; got|=take
fill[~got]=a[~got]
strict=clean&~ndi.binary_dilation((resid>55)&(~m)&(r<R-8),np.ones((9,9)))
gstd=float(np.std((a-ndi.gaussian_filter(a,(1.5,1.5,0)))[strict]))
rng=np.random.default_rng(7)
g=ndi.gaussian_filter(rng.normal(0,1,a.shape[:2]),0.6); g*=gstd/(g.std()+1e-9)
print(f'paper grain sigma={gstd:.2f} (from {strict.sum()} clean px)')
inp=np.clip(fill+g[...,None],0,255)
al=np.clip(ndi.gaussian_filter(hole.astype(float),1.5),0,1)[...,None]
bg=a*(1-al)+inp*al
print(f'inpaint hole: {hole.sum()} px')

def rgba(arr,alpha):
    o=np.zeros((H,W,4),np.uint8); o[...,:3]=np.clip(arr,0,255).astype(np.uint8)
    o[...,3]=np.clip(alpha*255,0,255).astype(np.uint8); return Image.fromarray(o,'RGBA')
def to_face(src,theta=0.0,k=1.0,N=480):
    s=(2*R)/N/k; t=math.radians(theta)
    A,B=math.cos(t)*s,-math.sin(t)*s; D,E=math.sin(t)*s,math.cos(t)*s; o=0.5-N/2
    return src.transform((N,N),Image.AFFINE,(A,B,CX+o*(A+B),D,E,CY+o*(D+E)),resample=Image.BICUBIC)
def arm_src(p):
    al=np.clip(ndi.gaussian_filter(ndi.binary_dilation(p,np.ones((3,3))).astype(float),0.7),0,1)
    sh=np.clip(ndi.gaussian_filter(al,2.2)*2.0,0,1)*0.38
    oa=np.clip(al+sh*(1-al),0,1)
    num=a*al[...,None]+np.array([44,31,21],float)*(sh*(1-al))[...,None]
    return rgba(np.where(oa[...,None]>1e-4,num/np.maximum(oa[...,None],1e-4),0),oa)
def hand(p,theta,k,N):
    im=np.array(to_face(arm_src(p),theta,k,N)).astype(float)
    yo,xo=np.mgrid[0:N,0:N]; rf=np.hypot(xo+0.5-N/2,yo+0.5-N/2)*(480.0/N)
    im[...,3]*=np.clip((rf-FADE[0])/(FADE[1]-FADE[0]),0,1)
    return Image.fromarray(im.astype(np.uint8),'RGBA')

head=np.clip(ndi.gaussian_filter((m&(np.hypot(xx-HEAD_C[0],yy-HEAD_C[1])<HEAD_R)).astype(float),1.0),0,1)
for N in (480,432):
    d=os.path.join(OUTD,'assets',f'{N}x{N}')+os.sep; os.makedirs(d,exist_ok=True)
    yo,xo=np.mgrid[0:N,0:N]; circ=(np.hypot(xo+0.5-N/2,yo+0.5-N/2)<=N/2-0.5)
    fa=np.array(to_face(rgba(bg,np.ones((H,W))),0,1,N)); fa[...,3]=(fa[...,3]*circ).astype(np.uint8)
    Image.fromarray(fa,'RGBA').save(d+'background.png')
    hand(L,tl,K_HOUR,N).save(d+'hour_hand.png')
    hand(Rt,tr,K_MIN,N).save(d+'minute_hand.png')
    to_face(rgba(bg,head),0,1,N).save(d+'head_overlay.png')

def preview(h,mi,N=480):
    d=os.path.join(OUTD,'assets',f'{N}x{N}')+os.sep; b=Image.open(d+'background.png').convert('RGBA')
    for f,ang in ((d+'hour_hand.png',(h%12+mi/60)*30),(d+'minute_hand.png',mi*6)):
        b.alpha_composite(Image.open(f).convert('RGBA').rotate(-ang,resample=Image.BICUBIC,center=(N/2,N/2)))
    b.alpha_composite(Image.open(d+'head_overlay.png').convert('RGBA'))
    o=Image.new('RGB',(N,N),(0,0,0)); o.paste(b,(0,0),b); o.save(os.path.join(PV,f'preview_{h:02d}{mi:02d}.png'))
PV=os.path.join(OUTD,'preview'); os.makedirs(PV,exist_ok=True)
for t in [(10,10),(1,50),(6,30),(3,0),(12,0),(9,15),(5,0),(7,20)]: preview(*t)
from PIL import ImageDraw
fs=['preview_1010','preview_0150','preview_0630','preview_0300','preview_1200','preview_0915','preview_0500','preview_0720']
sh=Image.new('RGB',(240*4,240*2),(20,20,20)); dr=ImageDraw.Draw(sh)
for i,f in enumerate(fs):
    sh.paste(Image.open(os.path.join(PV,f+'.png')).resize((240,240),Image.LANCZOS),((i%4)*240,(i//4)*240))
    dr.text(((i%4)*240+6,(i//4)*240+6),f[-4:],fill=(255,80,80))
sh.save(os.path.join(PV,'all-positions.png')); print('done')
