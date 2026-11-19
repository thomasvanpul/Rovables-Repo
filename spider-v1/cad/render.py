import glob, os, numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
C = {"tray": (0.20,0.20,0.23), "hat": (0.30,0.30,0.34), "roller": (0.80,0.62,0.30), "lid": (0.80,0.62,0.30),
     "pilllid": (0.80,0.62,0.30), "pill": (0.80,0.62,0.30), "n20": (0.62,0.64,0.70), "shaft": (0.85,0.85,0.9),
     "mag": (0.45,0.50,0.62), "pillmag": (0.45,0.50,0.62), "oled": (0.15,0.35,0.65), "speaker": (0.75,0.30,0.25),
     "vibration": (0.25,0.60,0.45), "leather": (0.50,0.30,0.16)}
def col(n):
    for k in sorted(C, key=len, reverse=True):
        if n.startswith(k): return C[k]
    return (.5,.5,.5)
P = {os.path.basename(f)[:-4]: trimesh.load(f) for f in glob.glob("out/assy/*.stl")}
def draw(ax, names, elev, azim, dz=lambda n: 0, alpha={}, title="", zoom=0.62):
    light = np.array([0.3,-0.4,0.85]); light/=np.linalg.norm(light)
    view = np.array([np.cos(np.radians(elev))*np.cos(np.radians(azim)), np.cos(np.radians(elev))*np.sin(np.radians(azim)), np.sin(np.radians(elev))])
    T=[];K=[];V=[]
    for n in names:
        m=P[n].copy(); m.apply_translation([0,0,dz(n)])
        sh=0.35+0.65*np.clip(m.face_normals@light,0,1)
        c=np.clip(np.array(col(n))[None,:]*sh[:,None],0,1)
        a=alpha.get(n,1.0)
        T.append(m.triangles); K.append(np.hstack([c,np.full((len(c),1),a)])); V.append(m.vertices)
    T=np.vstack(T);K=np.vstack(K);o=np.argsort(T.mean(1)@view)
    ax.add_collection3d(Poly3DCollection(T[o],facecolors=K[o],edgecolors="none"))
    v=np.vstack(V);c=(v.max(0)+v.min(0))/2;r=(v.max(0)-v.min(0)).max()/2*zoom
    ax.set_xlim(c[0]-r,c[0]+r);ax.set_ylim(c[1]-r,c[1]+r);ax.set_zlim(c[2]-r,c[2]+r)
    ax.set_box_aspect([1,1,1]);ax.view_init(elev,azim);ax.axis("off");ax.set_title(title,fontsize=12)
allp=[n for n in P if n!="leather"]
top=[n for n in allp if not n.startswith("pill")]
fig=plt.figure(figsize=(16,8),dpi=110)
draw(fig.add_subplot(1,2,1,projection="3d"), top+["leather"]+[n for n in allp if n.startswith("pill")], 28, -58,
     alpha={"hat":0.25,"tray":0.45,"leather":0.35}, title="Assembled on the leather (hat and tray see-through)")
draw(fig.add_subplot(1,2,2,projection="3d"), [n for n in allp if n.startswith("pill")]+["leather"], -30, -58,
     alpha={"leather":0.85}, title="Inside the vest: just two magnet pills")
plt.tight_layout(); plt.savefig("out/render_v1.png")
def ex(n):
    if n in ("hat","oled","speaker","vibration"): return 26
    if n.startswith(("roller","lid","n20","shaft","mag")): return 13
    if n=="leather": return -4
    if n.startswith("pill"): return -14
    return 0
fig=plt.figure(figsize=(11,11),dpi=110)
draw(fig.add_subplot(1,1,1,projection="3d"), allp+["leather"], 20, -55, dz=ex, alpha={"leather":0.5,"hat":0.55}, zoom=0.7,
     title="Exploded: hat (screen, speaker, purr) / motor+roller units / tray / leather / pills")
plt.tight_layout(); plt.savefig("out/render_v1_exploded.png")
