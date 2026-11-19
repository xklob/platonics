#!/usr/bin/env python3
"""Render centered single-object variants of the original 2D, 3D and 4D animations.

Frame count, duration, fps, and output dimensions are read from the original video.
The rendered geometry is new and procedural; no original video frames are copied.

Requirements: numpy, opencv-python, ffmpeg and ffprobe in PATH.
"""
from __future__ import annotations
import argparse
import colorsys
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

SOURCE = Path('renders/videos')
DEST = Path('renders/videos-single')
FRAME_SIZE = 1080


def ffprobe(path: Path) -> dict:
    result = subprocess.run(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=width,height,r_frame_rate,nb_frames,duration',
        '-of','json',str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)['streams'][0]


def eased(t: float) -> float:
    t=max(0.0,min(1.0,t))
    return t*t*t*(t*(t*6-15)+10)


def polygon_outline(sides: int | None, samples=360) -> np.ndarray:
    angles=np.linspace(-math.pi/2,3*math.pi/2,samples,endpoint=False)
    if sides is None:
        rad=np.ones_like(angles)
    else:
        step=2*math.pi/sides
        phase=math.pi/sides if sides%4==0 else 0.0
        local=(angles+math.pi/2-phase+step/2)%step-step/2
        rad=np.cos(step/2)/np.cos(local)
    return np.stack([rad*np.cos(angles),rad*np.sin(angles)],axis=-1)


def verts_and_edges(shape: str):
    phi=(1+math.sqrt(5))/2
    if shape=='tetrahedron': vertices=[(1,1,1),(-1,-1,1),(-1,1,-1),(1,-1,-1)]
    elif shape=='cube': vertices=[(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
    elif shape=='octahedron': vertices=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
    elif shape=='icosahedron':
        vertices=[]
        for a in (-1,1):
            for b in (-1,1): vertices.extend([(0,a,b*phi),(a,b*phi,0),(a*phi,0,b)])
    elif shape=='dodecahedron':
        vertices=[(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        for a in (-1,1):
            for b in (-1,1): vertices.extend([(0,a/phi,b*phi),(a/phi,b*phi,0),(a*phi,0,b/phi)])
    else: raise ValueError(shape)
    vertices=np.asarray(vertices,dtype=np.float64)
    vertices/=np.linalg.norm(vertices,axis=1).max()
    distances=np.linalg.norm(vertices[:,None]-vertices[None,:],axis=-1)
    np.fill_diagonal(distances,np.inf)
    shortest=distances.min()
    edges=[(i,j) for i in range(len(vertices)) for j in range(i+1,len(vertices)) if distances[i,j]<shortest*1.08]
    return vertices,edges


def rotate3(v: np.ndarray, angle: float):
    ca,sa=math.cos(angle),math.sin(angle)
    cb,sb=math.cos(angle*0.63+0.6),math.sin(angle*0.63+0.6)
    cc,sc=math.cos(angle*0.31+0.33),math.sin(angle*0.31+0.33)
    rx=np.array([[1,0,0],[0,cb,-sb],[0,sb,cb]])
    ry=np.array([[ca,0,sa],[0,1,0],[-sa,0,ca]])
    rz=np.array([[cc,-sc,0],[sc,cc,0],[0,0,1]])
    return v@rx.T@ry.T@rz.T


def project3(v: np.ndarray):
    return v[:,:2]*(3.5/(3.5-v[:,2:3]))


def tesseract(time_norm: float):
    verts=np.array([(x,y,z,w) for x in (-1,1) for y in (-1,1) for z in (-1,1) for w in (-1,1)],dtype=np.float64)
    edges=[(i,j) for i,a in enumerate(verts) for j,b in enumerate(verts) if j>i and np.count_nonzero(a!=b)==1]
    v=verts.copy()
    angles=[0.36+0.28*math.sin(2*math.pi*time_norm),0.72+0.26*math.cos(2*math.pi*time_norm),
            math.pi*2*time_norm,0.42+0.25*math.sin(2*math.pi*time_norm),
            0.55+0.35*math.cos(2*math.pi*time_norm),math.pi*2*time_norm]
    for (axis1,axis2),theta in zip([(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)],angles):
        c,s=math.cos(theta),math.sin(theta)
        v1=v[:,axis1].copy();v2=v[:,axis2].copy()
        v[:,axis1]=c*v1-s*v2
        v[:,axis2]=s*v1+c*v2
    fw=3.3/(3.3-v[:,3])
    p3=v[:,:3]*fw[:,None]
    return project3(p3),edges


def fit(points: np.ndarray, frame: int, fraction:float=0.84):
    p=np.array(points,dtype=np.float64)
    center=(np.max(p,axis=0)+np.min(p,axis=0))/2
    p-=center
    side=max(np.ptp(p[:,0]),np.ptp(p[:,1]),1e-6)
    p*=frame*fraction/side
    p+=frame/2
    return p


def segments_2d(u:float):
    # 3..12 polygons then circle for the long polygon morph
    states=list(range(3,13))+[None]
    index=int(u*len(states))%len(states)
    amount=eased((u*len(states)%1-0.72)/0.28)
    current=polygon_outline(states[index]);nextp=polygon_outline(states[(index+1)%len(states)])
    return current*(1-amount)+nextp*amount


def animation_state(stem:str, fraction:float, frame_size:int):
    if 'hypercube' in stem:
        pts,edges=tesseract(fraction)
        frame_fraction=0.87 if '2x-zoom' in stem else 0.81
        pts=fit(pts,frame_size,frame_fraction)
        return [(pts[i],pts[j]) for i,j in edges]
    if 'platonic-solids' in stem:
        states=['tetrahedron','cube','octahedron','dodecahedron','icosahedron']
        if 'slow' not in stem:states.append('sphere')
        phase=fraction*len(states);index=int(phase)%len(states)
        s=states[index]
        if s=='sphere':
            angles=np.linspace(0,2*math.pi,180,endpoint=False)
            c=np.stack([np.cos(angles),np.sin(angles)],axis=-1)
            pp=fit(c,frame_size,0.80)
            return [(pp[i],pp[(i+1)%len(pp)]) for i in range(len(pp))]
        verts,edges=verts_and_edges(s)
        pts=fit(project3(rotate3(verts,2*math.pi*fraction)),frame_size,0.80)
        return [(pts[i],pts[j]) for i,j in edges]
    if 'triangle-to-hexagon' in stem:
        states=[3,4,5,6]
        phase=fraction*len(states)
        idx=int(phase)%len(states)
        amount=eased((phase%1-0.72)/0.28)
        pp=polygon_outline(states[idx])*(1-amount)+polygon_outline(states[(idx+1)%len(states)])*amount
    else:
        pp=segments_2d(fraction)
    pp=fit(pp,frame_size,0.82)
    return [(pp[i],pp[(i+1)%len(pp)]) for i in range(len(pp))]


def palette(t:float):
    rgb=colorsys.hsv_to_rgb(t%1.0,0.97,1)
    return tuple(int(x*255) for x in reversed(rgb))


def draw_frame(stem, fraction, size):
    base=np.zeros((size,size,3),np.uint8)
    segments=animation_state(stem,fraction,size)
    # One rainbow cycle across the connected geometry
    glow=np.zeros_like(base)
    for i,(p,q) in enumerate(segments):
        col=palette(i/len(segments)+0.13)
        a=tuple(np.rint(p).astype(int));b=tuple(np.rint(q).astype(int))
        cv2.line(glow,a,b,col,5,cv2.LINE_AA)
        cv2.line(base,a,b,col,2,cv2.LINE_AA)
    glow=cv2.GaussianBlur(glow,(0,0),3.4)
    return cv2.addWeighted(base,1.0,glow,0.48,0)


def render(src:Path,dest:Path,internal_size=960,crf=25,preset='ultrafast'):
    info=ffprobe(src)
    fps=float(eval_fps(info['r_frame_rate']))
    count=int(info['nb_frames'])
    w,h=int(info['width']),int(info['height'])
    dest.parent.mkdir(parents=True,exist_ok=True)
    command=['ffmpeg','-hide_banner','-loglevel','error','-y',
             '-f','rawvideo','-pix_fmt','bgr24','-s',f'{internal_size}x{internal_size}',
             '-r',str(fps),'-i','-', '-an',
             '-vf',f'scale={w}:{h}:flags=lanczos,format=yuv420p',
             '-c:v','libx264','-preset',preset,'-crf',str(crf),'-movflags','+faststart',str(dest)]
    p=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for i in range(count):
            frame=draw_frame(src.stem,i/count,internal_size)
            p.stdin.write(frame.tobytes())
            if i%200==0:print(f'{src.name}: {i}/{count}',flush=True)
        p.stdin.close();code=p.wait()
        if code!=0:raise RuntimeError(f'ffmpeg returned {code}')
    except Exception:
        p.kill();p.wait();raise
    check=ffprobe(dest)
    assert int(check['nb_frames'])==count and int(check['width'])==w and int(check['height'])==h
    assert check['r_frame_rate']==info['r_frame_rate']
    print(f'COMPLETE {dest} {dest.stat().st_size} bytes, {count} frames at {fps}fps',flush=True)


def eval_fps(value:str)->float:
    a,b=value.split('/')
    return int(a)/int(b)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--output',type=Path,default=DEST)
    parser.add_argument('--only',nargs='*',default=[])
    parser.add_argument('--internal-size',type=int,default=960)
    parser.add_argument('--crf',type=int,default=25)
    args=parser.parse_args()
    for src in sorted(args.source.rglob('*.mp4')):
        if args.only and src.stem not in args.only:continue
        rel=src.relative_to(args.source)
        render(src,args.output/rel,args.internal_size,args.crf)

if __name__=='__main__':main()
