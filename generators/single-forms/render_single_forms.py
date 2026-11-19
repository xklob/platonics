import math, os, hashlib, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path('renders/stills')
OUTROOT = Path('renders/stills-single')
THUMBROOT = Path('renders/thumbnails-single')
SIZE = 1254
SS = 2
CANVAS = SIZE * SS
CENTER = CANVAS / 2

BLACK = (0,0,0)

def seeded(name):
    h = hashlib.sha256(name.encode()).digest()
    return random.Random(int.from_bytes(h[:8], 'big'))

def hsv_to_rgb(h, s=1.0, v=1.0):
    h = h % 1.0
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i %= 6
    if i == 0: r,g,b = v,t,p
    elif i == 1: r,g,b = q,v,p
    elif i == 2: r,g,b = p,v,t
    elif i == 3: r,g,b = p,q,v
    elif i == 4: r,g,b = t,p,v
    else: r,g,b = v,p,q
    return tuple(int(max(0,min(255, round(c*255)))) for c in (r,g,b))

def lerp(a,b,t):
    return a + (b-a)*t

def vec_add(a,b): return (a[0]+b[0], a[1]+b[1])
def vec_sub(a,b): return (a[0]-b[0], a[1]-b[1])
def vec_mul(a,s): return (a[0]*s, a[1]*s)
def vec_len(a): return math.hypot(a[0], a[1])

def rotate_point(p, angle):
    c,s = math.cos(angle), math.sin(angle)
    return (p[0]*c - p[1]*s, p[0]*s + p[1]*c)

def regular_polygon(n, radius, rotation=-math.pi/2, center=(CENTER,CENTER)):
    pts=[]
    for i in range(n):
        a = rotation + i*2*math.pi/n
        pts.append((center[0] + radius*math.cos(a), center[1] + radius*math.sin(a)))
    return pts

def circle_points(radius, count=240, center=(CENTER,CENTER), rotation=0):
    return [(center[0]+radius*math.cos(rotation+2*math.pi*i/count), center[1]+radius*math.sin(rotation+2*math.pi*i/count)) for i in range(count)]

def spiral_points(turns=5, start_r=30, end_r=480, count=600, center=(CENTER,CENTER), angle0=0, square=False):
    pts=[]
    for i in range(count):
        t = i/(count-1)
        a = angle0 + turns*2*math.pi*t
        r = lerp(start_r, end_r, t)
        if square:
            # map circle to squircle-ish square spiral
            x = math.cos(a); y = math.sin(a)
            m = max(abs(x), abs(y), 1e-6)
            x /= m; y /= m
        else:
            x = math.cos(a); y = math.sin(a)
        pts.append((center[0]+r*x, center[1]+r*y))
    return pts

def arc_points(radius, a0, a1, count=120, center=(CENTER,CENTER)):
    return [(center[0]+radius*math.cos(lerp(a0,a1,i/(count-1))), center[1]+radius*math.sin(lerp(a0,a1,i/(count-1)))) for i in range(count)]

def resample_polyline(points, closed=False, samples_per_seg=18):
    pts = list(points)
    if closed:
        pts2 = pts + [pts[0]]
    else:
        pts2 = pts
    out=[]
    for a,b in zip(pts2, pts2[1:]):
        for i in range(samples_per_seg):
            t = i / samples_per_seg
            out.append((lerp(a[0], b[0], t), lerp(a[1], b[1], t)))
    out.append(pts2[-1])
    return out

def draw_gradient_polyline(glow_draw, line_draw, points, base_hue, width=4, glow_width=14, alpha=110, closed=False):
    pts = resample_polyline(points, closed=closed, samples_per_seg=14)
    n = max(1, len(pts)-1)
    for i in range(n):
        p0, p1 = pts[i], pts[i+1]
        hue = (base_hue + i/n) % 1.0
        c = hsv_to_rgb(hue, 1.0, 1.0)
        glow_draw.line([p0,p1], fill=c+(alpha,), width=glow_width)
        line_draw.line([p0,p1], fill=c+(255,), width=width)

def draw_segments(glow_draw, line_draw, segments, base_hue, width=4, glow_width=14, alpha=110):
    n = max(1,len(segments))
    for i,(p0,p1) in enumerate(segments):
        hue = (base_hue + i/n) % 1.0
        c = hsv_to_rgb(hue, 1.0, 1.0)
        glow_draw.line([p0,p1], fill=c+(alpha,), width=glow_width)
        line_draw.line([p0,p1], fill=c+(255,), width=width)

def add_segments(segments, pts, closed=True):
    for a,b in zip(pts, pts[1:]):
        segments.append((a,b))
    if closed:
        segments.append((pts[-1], pts[0]))

def poly3d_vertices(shape):
    phi=(1+5**0.5)/2
    if shape=='tetrahedron':
        verts=[(1,1,1),(-1,-1,1),(-1,1,-1),(1,-1,-1)]
    elif shape=='cube':
        verts=[(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
    elif shape=='octahedron':
        verts=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
    elif shape=='icosahedron':
        verts=[]
        for s1 in (-1,1):
            for s2 in (-1,1):
                verts.extend([(0,s1,s2*phi),(s1,s2*phi,0),(s1*phi,0,s2)])
    elif shape=='dodecahedron':
        a=1/phi
        b=1
        c=phi
        verts=[(x,y,z) for x in (-b,b) for y in (-b,b) for z in (-b,b)]
        for s1 in (-1,1):
            for s2 in (-1,1):
                verts.extend([(0,s1*a,s2*c),(s1*a,s2*c,0),(s1*c,0,s2*a)])
    else:
        raise ValueError(shape)
    # normalize
    m=max(math.sqrt(x*x+y*y+z*z) for x,y,z in verts)
    return [(x/m,y/m,z/m) for x,y,z in verts]

def infer_edges(verts):
    dists=[]
    for i,a in enumerate(verts):
        for j,b in enumerate(verts[i+1:], i+1):
            d=((a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2)**0.5
            dists.append((d,i,j))
    edge_len=min(d for d,_,_ in dists if d>1e-6)
    thresh=edge_len*1.08
    return [(i,j) for d,i,j in dists if d<=thresh]

def rot_xyz(p, ax, ay, az):
    x,y,z=p
    cy,sy=math.cos(ay),math.sin(ay)
    x,z=x*cy+z*sy,-x*sy+z*cy
    cx,sx=math.cos(ax),math.sin(ax)
    y,z=y*cx-z*sx,y*sx+z*cx
    cz,sz=math.cos(az),math.sin(az)
    x,y=x*cz-y*sz,x*sz+y*cz
    return (x,y,z)

def project3d(p, scale=400, cam=3.5):
    x,y,z=p
    f=cam/(cam-z)
    return (CENTER + x*scale*f, CENTER + y*scale*f, z)

def project4d_tesseract(rot_ab=(0.5,0.4,0.3), scale=370):
    # axes xy xz xw yz yw zw angles
    axy,axz,axw,ayz,ayw,azw = rot_ab
    verts=[(x,y,z,w) for x in (-1,1) for y in (-1,1) for z in (-1,1) for w in (-1,1)]
    def rot4(p, i,j, ang):
        arr=list(p)
        c,s=math.cos(ang),math.sin(ang)
        ai,aj=arr[i],arr[j]
        arr[i]=ai*c-aj*s
        arr[j]=ai*s+aj*c
        return tuple(arr)
    out=[]
    for p in verts:
        for ij,ang in [((0,1),axy),((0,2),axz),((0,3),axw),((1,2),ayz),((1,3),ayw),((2,3),azw)]:
            p=rot4(p, ij[0], ij[1], ang)
        # 4D perspective to 3D
        x,y,z,w = p
        fw = 3.2/(3.2-w)
        p3=(x*fw, y*fw, z*fw)
        out.append(p3)
    edges=[]
    for i,a in enumerate(verts):
        for j,b in enumerate(verts[i+1:], i+1):
            if sum(aa!=bb for aa,bb in zip(a,b))==1:
                edges.append((i,j))
    pts=[project3d(p, scale=scale, cam=4.4) for p in out]
    return pts, edges

def fit_projected(points, target_fraction=0.80):
    """Center and uniformly scale a projected geometry to a safe square footprint."""
    xs=[p[0] for p in points]
    ys=[p[1] for p in points]
    xmin,xmax=min(xs),max(xs)
    ymin,ymax=min(ys),max(ys)
    cx=(xmin+xmax)/2
    cy=(ymin+ymax)/2
    scale=CANVAS*target_fraction/max(xmax-xmin,ymax-ymin,1.0)
    return [(CENTER+(p[0]-cx)*scale,CENTER+(p[1]-cy)*scale,*p[2:]) for p in points]

def draw_polyhedron(glow_draw, line_draw, shape, rng, base_hue, variant='single'):
    verts=poly3d_vertices(shape)
    ax=rng.uniform(0.4,1.0); ay=rng.uniform(0.3,1.1); az=rng.uniform(0.1,0.8)
    pts3=[rot_xyz(v,ax,ay,az) for v in verts]
    edges=infer_edges(verts)
    projection_scale=rng.uniform(770,900)
    proj=fit_projected([project3d(p, scale=projection_scale, cam=3.8) for p in pts3], target_fraction=0.79)
    edge_depth=[]
    for i,j in edges:
        z=(proj[i][2]+proj[j][2])/2
        edge_depth.append((z,i,j))
    edge_depth.sort()
    segments=[((proj[i][0],proj[i][1]),(proj[j][0],proj[j][1])) for _,i,j in edge_depth]
    draw_segments(glow_draw,line_draw,segments,base_hue,width=4,glow_width=16,alpha=110)
    if variant in ('double','nested'):
        scale2=rng.uniform(0.48,0.63)
        proj2=[(CENTER+(p[0]-CENTER)*scale2,CENTER+(p[1]-CENTER)*scale2,p[2]) for p in proj]
        segments2=[((proj2[i][0],proj2[i][1]),(proj2[j][0],proj2[j][1])) for _,i,j in edge_depth]
        draw_segments(glow_draw,line_draw,segments2,(base_hue+0.23)%1.0,width=3,glow_width=11,alpha=90)

def render_one(src_path, out_path, thumb_path):
    rel = src_path.relative_to(ROOT)
    name = src_path.stem
    rng = seeded(str(rel))
    hue0 = rng.random()
    glow = Image.new('RGBA', (CANVAS, CANVAS), (0,0,0,0))
    line = Image.new('RGBA', (CANVAS, CANVAS), (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    ld = ImageDraw.Draw(line)

    lname = name.lower()
    dimension = rel.parts[0]
    segments=[]

    def draw_nested_polygon(n, radius=None, inner=True, spokes=False, double=False):
        radius = radius or rng.uniform(CANVAS*0.28, CANVAS*0.38)
        rot = rng.uniform(-0.5, 0.5)
        pts=regular_polygon(n, radius, rotation=rot)
        draw_gradient_polyline(gd, ld, pts, hue0, width=5, glow_width=18, alpha=120, closed=True)
        if inner:
            pts2=regular_polygon(n, radius*rng.uniform(0.45,0.68), rotation=rot + rng.uniform(0.08,0.25))
            draw_gradient_polyline(gd, ld, pts2, (hue0+0.12)%1.0, width=3, glow_width=11, alpha=90, closed=True)
        if spokes:
            for a,b in zip(pts, pts2 if inner else pts):
                segments.append((a,b))
        if double:
            pts3=regular_polygon(n, radius*0.83, rotation=rot+rng.uniform(0.15,0.35))
            draw_gradient_polyline(gd, ld, pts3, (hue0+0.55)%1.0, width=2, glow_width=9, alpha=75, closed=True)

    # 2D families
    if dimension == '2d' and any(k in lname for k in ['triangle']):
        draw_nested_polygon(3, inner=True, spokes=True, double='tessellation' in lname)
    elif dimension == '2d' and 'square spiral' in lname:
        pts=spiral_points(turns=rng.uniform(4.8,6.0), start_r=40, end_r=CANVAS*0.34, count=900, angle0=rng.uniform(0,math.pi/4), square=True)
        draw_gradient_polyline(gd,ld,pts,hue0,width=4,glow_width=16,alpha=120,closed=False)
    elif dimension == '2d' and 'square' in lname:
        draw_nested_polygon(4, inner=True, spokes=False, double='grid' in lname or 'lattice' in lname)
    elif dimension == '2d' and 'pentagon' in lname:
        draw_nested_polygon(5, inner=True, spokes='tessellation' in lname, double='(1)' in lname)
    elif dimension == '2d' and ('hexagon' in lname or 'honeycomb' in lname):
        draw_nested_polygon(6, inner=True, spokes='honeycomb' in lname, double='lattice' in lname)
    elif dimension == '2d' and 'heptagon' in lname:
        draw_nested_polygon(7, inner=True, spokes=False, double='diagonal' in lname)
    elif dimension == '2d' and ('octagon' in lname or 'octagonal' in lname):
        draw_nested_polygon(8, inner=True, spokes='sparse' in lname, double=True)
    elif dimension == '2d' and 'nonagon' in lname:
        draw_nested_polygon(9, inner=True, double=True)
    elif dimension == '2d' and 'decagon' in lname and 'hendecagon' not in lname and 'dodecagon' not in lname:
        draw_nested_polygon(10, inner=True, double=True)
    elif dimension == '2d' and 'hendecagon' in lname:
        draw_nested_polygon(11, inner=True, double=True)
    elif dimension == '2d' and 'dodecagon' in lname:
        draw_nested_polygon(12, inner=True, double=True)
    elif dimension == '2d' and ('circle mosaic' in lname or 'tangent circle' in lname):
        for scale in [1.0,0.68,0.36]:
            pts=circle_points(CANVAS*0.34*scale, count=300, rotation=rng.uniform(0,0.2))
            draw_gradient_polyline(gd,ld,pts,(hue0+scale*0.15)%1.0,width=5 if scale==1.0 else 3,glow_width=18 if scale==1.0 else 10,alpha=115,closed=True)
        # six satellites touching outer ring but still one composition
        R=CANVAS*0.34*0.56
        sat=CANVAS*0.34*0.26
        for idx in range(6):
            ang=idx*2*math.pi/6 + rng.uniform(-0.03,0.03)
            c=(CENTER + math.cos(ang)*R, CENTER + math.sin(ang)*R)
            pts=circle_points(sat, count=140, center=c)
            draw_gradient_polyline(gd,ld,pts,(hue0+idx/6)%1.0,width=2,glow_width=8,alpha=75,closed=True)
    elif dimension == '2d' and 'concentric arcs' in lname:
        for i in range(6):
            radius=CANVAS*0.11 + i*CANVAS*0.045
            a0=0.65*math.pi + i*0.08
            a1=2.2*math.pi - i*0.09
            pts=arc_points(radius,a0,a1,count=170)
            draw_gradient_polyline(gd,ld,pts,(hue0+i*0.09)%1.0,width=4,glow_width=14,alpha=105,closed=False)
    elif dimension == '2d' and 'spiral' in lname:
        pts=spiral_points(turns=rng.uniform(4.4,5.6), start_r=22, end_r=CANVAS*0.35, count=1100, angle0=rng.uniform(0,math.pi*2))
        draw_gradient_polyline(gd,ld,pts,hue0,width=3,glow_width=12,alpha=100,closed=False)
    elif dimension == '2d' and 'truchet' in lname:
        # single truchet-style square tile
        s=CANVAS*0.62
        x0=CENTER-s/2; y0=CENTER-s/2; x1=CENTER+s/2; y1=CENTER+s/2
        for r,offset in [(s*0.5,0),(s*0.5,0.5)]:
            for (cx,cy),a0,a1 in [((x0,y0),0,math.pi/2),((x1,y1),math.pi,1.5*math.pi),((x1,y0),math.pi/2,math.pi),((x0,y1),1.5*math.pi,2*math.pi)]:
                pts=arc_points(r,a0,a1,count=100,center=(cx,cy))
                draw_gradient_polyline(gd,ld,pts,(hue0+offset)%1.0,width=4,glow_width=14,alpha=110,closed=False)
    elif dimension == '2d' and 'pinwheel' in lname:
        n=6
        outer=regular_polygon(n, CANVAS*0.32, rotation=rng.uniform(-0.3,0.3))
        inner=regular_polygon(n, CANVAS*0.10, rotation=rng.uniform(0,0.4))
        for i in range(n):
            tri=[inner[i], outer[i], outer[(i+1)%n]]
            draw_gradient_polyline(gd,ld,tri,(hue0+i/n)%1.0,width=4,glow_width=14,alpha=110,closed=True)
    elif dimension == '2d' and 'broken rings' in lname:
        for idx,rr in enumerate([CANVAS*0.33, CANVAS*0.25, CANVAS*0.17]):
            gap0=rng.uniform(0, 2*math.pi)
            for seg in [(gap0+0.4, gap0+2.2),(gap0+2.7, gap0+5.6)]:
                pts=arc_points(rr, seg[0], seg[1], count=160)
                draw_gradient_polyline(gd,ld,pts,(hue0+idx*0.2)%1.0,width=5-idx,glow_width=15-idx*2,alpha=110,closed=False)
    elif dimension == '2d' and 'maze' in lname:
        # one labyrinthine square motif
        s=CANVAS*0.62
        x0=CENTER-s/2; y0=CENTER-s/2
        step=s/6
        pts=[(x0,y0),(x0+s,y0),(x0+s,y0+s),(x0,y0+s),(x0,y0+step),(x0+s-step,y0+step),(x0+s-step,y0+s-step),(x0+step,y0+s-step),(x0+step,y0+2*step),(x0+s-2*step,y0+2*step),(x0+s-2*step,y0+s-2*step),(x0+2*step,y0+s-2*step)]
        draw_gradient_polyline(gd,ld,pts,hue0,width=5,glow_width=16,alpha=110,closed=False)
    elif dimension == '2d' and 'herringbone' in lname:
        # one interlocking chevron object
        base=[]
        w=CANVAS*0.12; h=CANVAS*0.10
        start=(-2*w,-2*h)
        for i in range(5):
            x=start[0]+i*w*0.95
            base.extend([(x,-h),(x+w*0.7,0),(x, h)])
        pts=[(CENTER+x, CENTER+y) for x,y in base]
        draw_gradient_polyline(gd,ld,pts,hue0,width=5,glow_width=15,alpha=110,closed=False)
    elif dimension == '2d' and 'penrose' in lname:
        # 5-rhombus star cluster
        R=CANVAS*0.26
        r=CANVAS*0.11
        for i in range(5):
            a= -math.pi/2 + i*2*math.pi/5
            b=a+2*math.pi/5
            c=a+math.pi/5
            p1=(CENTER+R*math.cos(a), CENTER+R*math.sin(a))
            p2=(CENTER+R*math.cos(b), CENTER+R*math.sin(b))
            p3=(CENTER+r*math.cos(c), CENTER+r*math.sin(c))
            p4=(CENTER-r*math.cos(c), CENTER-r*math.sin(c))
            draw_gradient_polyline(gd,ld,[p1,p3,p2,p4],(hue0+i/5)%1.0,width=4,glow_width=14,alpha=110,closed=True)
    elif dimension == '2d' and ('lattice' in lname or 'grid' in lname):
        draw_nested_polygon(6 if 'continuous' in lname else 8, inner=True, double=True)

    # 3D / 4D families
    if dimension == '3d' and 'tetrahedron' in lname:
        draw_polyhedron(gd,ld,'tetrahedron',rng,hue0,variant='nested' if 'lattice' in lname else 'single')
    elif dimension == '3d' and 'cube' in lname:
        draw_polyhedron(gd,ld,'cube',rng,hue0,variant='nested' if ('lattice' in lname or 'wireframe' in lname or 'isometric' in lname) else 'single')
    elif dimension == '3d' and 'octahedron' in lname:
        draw_polyhedron(gd,ld,'octahedron',rng,hue0,variant='nested' if ('lattice' in lname or 'wireframe' in lname or 'grid' in lname or 'constellation' in lname) else 'single')
    elif dimension == '3d' and ('icosahed' in lname or 'd20' in lname):
        draw_polyhedron(gd,ld,'icosahedron',rng,hue0,variant='nested' if ('array' in lname or 'wireframe' in lname or 'hexagonal' in lname) else 'single')
    elif dimension == '3d' and 'dodeca' in lname:
        draw_polyhedron(gd,ld,'dodecahedron',rng,hue0,variant='nested' if ('lattice' in lname or 'wireframe' in lname or 'staggered' in lname) else 'single')
    elif dimension == '4d' and 'tesseract' in lname:
        angles=[rng.uniform(0.15,1.15) for _ in range(6)]
        pts,edges=project4d_tesseract(tuple(angles), scale=rng.uniform(590,650))
        pts=fit_projected(pts,target_fraction=0.83)
        segs=[((pts[i][0],pts[i][1]), (pts[j][0],pts[j][1])) for i,j in edges]
        # sort by mean z using 3d z component stored in 3rd slot
        segs=sorted(segs, key=lambda s:(s[0][0]+s[1][0]))
        draw_segments(gd,ld,segs,hue0,width=4,glow_width=14,alpha=110)


    if segments:
        draw_segments(gd,ld,segments,(hue0+0.35)%1.0,width=2,glow_width=8,alpha=70)

    # faint outer vignette / stars
    bg = Image.new('RGB', (CANVAS,CANVAS), BLACK)
    rnd=seeded('stars-'+str(rel))
    bgd=ImageDraw.Draw(bg)
    for _ in range(240):
        x=rnd.uniform(0,CANVAS); y=rnd.uniform(0,CANVAS); a=rnd.randint(6,26)
        bgd.point((x,y), fill=(a,a,a))

    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(bg.convert('RGBA'), glow)
    img = Image.alpha_composite(img, line)
    vignette = Image.new('L',(CANVAS,CANVAS),0)
    vd=ImageDraw.Draw(vignette)
    vd.ellipse((CANVAS*0.05,CANVAS*0.05,CANVAS*0.95,CANVAS*0.95), fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=120))
    black = Image.new('RGBA',(CANVAS,CANVAS),(0,0,0,0))
    img = Image.composite(img, Image.alpha_composite(img, black), vignette)
    img = img.resize((SIZE,SIZE), resample=Image.Resampling.LANCZOS).convert('RGB')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, compress_level=6)
    thumb = img.resize((320,320), resample=Image.Resampling.LANCZOS)
    thumb.save(thumb_path, format='WEBP', quality=88, method=6)

def main():
    global ROOT, OUTROOT, THUMBROOT
    import argparse
    parser=argparse.ArgumentParser(description='Render one large central shape for each original still')
    parser.add_argument('--source',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,default=OUTROOT)
    parser.add_argument('--thumbnails',type=Path,default=THUMBROOT)
    args=parser.parse_args()
    ROOT=args.source
    OUTROOT=args.output
    THUMBROOT=args.thumbnails
    files=sorted(ROOT.rglob('*.png'))
    for src in files:
        rel=src.relative_to(ROOT)
        out=OUTROOT/rel
        thumb=THUMBROOT/rel.with_suffix('.webp')
        render_one(src, out, thumb)
        print('rendered', rel)
    print('done', len(files))

if __name__=='__main__':
    main()
