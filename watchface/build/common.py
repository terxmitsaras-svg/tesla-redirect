import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, 'source_clock.png')     # the original clock image
OUT  = HERE + os.sep
CX,CY,R = 429.0, 391.5, 351.0

def load():
    return np.array(Image.open(SRC).convert('RGB')).astype(np.float64)

def dial_model(a, fig_box=None):
    H,W,_ = a.shape
    yy,xx = np.mgrid[0:H,0:W]
    r = np.hypot(xx-CX, yy-CY)
    if fig_box is None:
        fig_box = (xx>=285)&(xx<=632)&(yy>=218)&(yy<=672)
    clean = (r<=R+1)&(~fig_box)
    rb = (r/2.0).astype(int); nb = rb.max()+1
    prof=np.zeros((nb,3)); valid=np.zeros(nb,bool)
    for i in range(nb):
        m = clean&(rb==i)
        if m.sum()>150:
            prof[i]=np.median(a[m],axis=0); valid[i]=True
    idx=np.where(valid)[0]
    for i in range(nb):
        if not valid[i]:
            prof[i]=prof[idx[np.argmin(np.abs(idx-i))]]
    return prof[np.clip(rb,0,nb-1)], r

def figure_mask(a):
    model, r = dial_model(a)
    resid = np.abs(a-model).max(axis=2)
    m = (resid>55)&(r<R-8)
    m = ndi.binary_closing(m, np.ones((5,5)))
    lab,n = ndi.label(m)
    # component containing the torso
    seed = lab[430, 429]
    if seed==0:
        ys,xs=np.where(m); seed=lab[ys[len(ys)//2],xs[len(xs)//2]]
    m = lab==seed
    m = ndi.binary_fill_holes(m)
    m = ndi.binary_opening(m, np.ones((3,3)))
    m = ndi.binary_closing(m, np.ones((7,7)))
    m = ndi.binary_fill_holes(m)
    return m, model, r
