import glob, os, numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
COL = {"chassis": (0.18,0.18,0.20), "strap": (0.30,0.30,0.34), "roller": (0.80,0.62,0.30), "cap": (0.80,0.62,0.30),
       "n20": (0.62,0.64,0.70), "shaft": (0.85,0.85,0.9), "mag": (0.55,0.58,0.65), "frame": (0.30,0.30,0.36),
       "froller": (0.80,0.62,0.30), "fcap": (0.80,0.62,0.30), "leather": (0.45,0.26,0.14)}
def col(n):
    k = n.split("_",1)[1] if "_" in n else n
    for key in sorted(COL, key=len, reverse=True):
        if k.startswith(key): return COL[key]
    return (0.5,0.5,0.5)
parts = {os.path.basename(f)[:-4]: trimesh.load(f) for f in glob.glob("out/assy/*.stl")}
def draw(ax, names, elev, azim, dz=None, alpha=None, title=""):
    light = np.array([0.3,-0.4,0.85]); light/=np.linalg.norm(light)
    V=[]
    # painter's order: sort faces of all meshes by depth
    view = np.array([np.cos(np.radians(elev))*np.cos(np.radians(azim)), np.cos(np.radians(elev))*np.sin(np.radians(azim)), np.sin(np.radians(elev))])
    tris=[]; cols=[]
    for n in names:
        m = parts[n].copy()
        if dz: m.apply_translation([0,0,dz(n)])
        sh = 0.35+0.65*np.clip(m.face_normals@light,0,1)
        c = np.array(col(n))[None,:]*sh[:,None]
        a = (alpha or {}).get(n.split("_",1)[-1] if n!="leather" else "leather", 1.0)
        tris.append(m.triangles); cols.append(np.hstack([np.clip(c,0,1), np.full((len(c),1),a)])); V.append(m.vertices)
    T=np.vstack(tris); C=np.vstack(cols)
    d = T.mean(1)@view; o=np.argsort(d)
    ax.add_collection3d(Poly3DCollection(T[o], facecolors=C[o], edgecolors="none"))
    v=np.vstack(V); c=(v.max(0)+v.min(0))/2; r=(v.max(0)-v.min(0)).max()/2*0.75
    ax.set_xlim(c[0]-r,c[0]+r); ax.set_ylim(c[1]-r,c[1]+r); ax.set_zlim(c[2]-r,c[2]+r)
    ax.set_box_aspect([1,1,1]); ax.view_init(elev,azim); ax.axis("off"); ax.set_title(title, fontsize=11)
bot=[n for n in parts if n.startswith("bot_")]
fol=[n for n in parts if n.startswith("fol_")]
fig=plt.figure(figsize=(16,8),dpi=110)
draw(fig.add_subplot(1,2,1,projection="3d"), bot, 30, -60, alpha={"chassis":0.35,"strap":0.6}, title="Spider v0, chassis see-through: 2 x N20, magnet rollers at opposite corners")
draw(fig.add_subplot(1,2,2,projection="3d"), bot, -40, -60, title="Underside: rollers touch the leather, strap with 3 x M2")
plt.tight_layout(); plt.savefig("out/render_bot.png")
def ex(n):
    if n.startswith("fol_"): return -18
    if n=="leather": return -6
    if n=="bot_strap": return 8
    if n.startswith(("bot_roller","bot_cap","bot_n20","bot_shaft","bot_mag")): return 16
    if n=="bot_chassis": return 30
    return 0
fig=plt.figure(figsize=(11,10),dpi=110)
draw(fig.add_subplot(1,1,1,projection="3d"), bot+fol+["leather"], 22, -55, dz=ex, alpha={"leather":0.55,"chassis":0.9},
     title="Exploded: chassis / motor+roller units / strap / leather / follower")
plt.tight_layout(); plt.savefig("out/render_exploded.png")
