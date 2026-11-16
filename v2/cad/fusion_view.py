"""Open Rovable v2 in Autodesk Fusion (direct design), name and save the document, and save two views.

Geometry comes from rovable_v2_geom.py, the same file build.py makes the STLs from. Run it from Fusion's
Scripts dialog, or from any runner that calls run(context). Results go to out/fusion.json.
"""
import importlib
import json
import os
import sys
import traceback

import adsk.core
import adsk.fusion

CAD_DIR = os.environ.get("ROVABLE_V2_CAD") or os.path.dirname(os.path.abspath(__file__))
DOC_NAME = "Rovable v2 (Imperial, 2026)"
SAVE_PROJECT = "Extras"       # Fusion project the document is saved into; not saved if it does not exist
IMAGE_SIZE = (1600, 1000)
PRINTED_COLOUR = (236, 232, 222)
FUSION_ERRORS = (RuntimeError, AttributeError, ValueError, OSError, ImportError)
VIEWS = (("fusion_iso.png", "IsoTopRightViewOrientation", False),
         ("fusion_under.png", "IsoBottomLeftViewOrientation", True))


def run(context):
    out = os.path.join(CAD_DIR, "out")
    os.makedirs(out, exist_ok=True)
    report = {"doc": DOC_NAME}
    try:
        _build(out, report)
        report["ok"] = True
    except FUSION_ERRORS:      # Fusion swallows script errors; the file is how the caller sees them
        report["ok"] = False
        report["error"] = traceback.format_exc()
    with open(os.path.join(out, "fusion.json"), "w") as f:
        json.dump(report, f, indent=1)


def _build(out, report):
    sys.path.insert(0, CAD_DIR)
    import rovable_v2_geom as g
    importlib.reload(g)
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    doc.name = DOC_NAME
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    root = design.rootComponent
    tbm = adsk.fusion.TemporaryBRepManager.get()

    def P(x, y, z):
        return adsk.core.Point3D.create(x / 10, y / 10, z / 10)       # Fusion's API works in cm

    def op(a, b, kind):
        tbm.booleanOperation(a, b, kind)
        return a

    class K:
        @staticmethod
        def box(x0, x1, y0, y1, z0, z1):
            o = adsk.core.OrientedBoundingBox3D.create(
                P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), adsk.core.Vector3D.create(1, 0, 0),
                adsk.core.Vector3D.create(0, 1, 0), abs(x1 - x0) / 10, abs(y1 - y0) / 10, abs(z1 - z0) / 10)
            return tbm.createBox(o)

        cylx = staticmethod(lambda x0, x1, y, z, r: tbm.createCylinderOrCone(P(x0, y, z), r / 10, P(x1, y, z), r / 10))
        cylz = staticmethod(lambda x, y, z0, z1, r: tbm.createCylinderOrCone(P(x, y, z0), r / 10, P(x, y, z1), r / 10))
        U = staticmethod(lambda a, b: op(a, b, adsk.fusion.BooleanTypes.UnionBooleanType))
        D = staticmethod(lambda a, b: op(a, b, adsk.fusion.BooleanTypes.DifferenceBooleanType))

    def comp(name, brep):
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        return occ.component.bRepBodies.add(brep), occ

    printed = [("Chassis", g.chassis(K)), ("Electronics tray", g.tray(K))]
    for s, t in ((1, "front"), (-1, "back")):
        printed += [(f"Roller body {t}", g.roller_body(K, s)), (f"Roller cap {t}", g.roller_cap(K, s)),
                    (f"Motor cap {t}", g.motor_cap(K, s))]
    tray_occ = None
    for name, brep in printed:
        _, occ = comp(name, brep)
        if name == "Electronics tray":
            tray_occ = occ
    fabric_occ = None
    for name, brep in g.refs(K).items():
        _, occ = comp(name, brep)
        if name.startswith("Fabric"):
            fabric_occ = occ
    report["components"] = root.occurrences.count

    vp = app.activeViewport
    for fname, orientation, underside in VIEWS:
        if fabric_occ:
            fabric_occ.isLightBulbOn = not underside                    # the fabric hides the rollers from below
        cam = vp.camera
        cam.viewOrientation = getattr(adsk.core.ViewOrientations, orientation)
        cam.isFitView = True
        cam.isSmoothTransition = False
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()
        path = os.path.join(out, fname)
        report[fname] = bool(vp.saveAsImageFile(path, *IMAGE_SIZE))
    if fabric_occ:
        fabric_occ.isLightBulbOn = True
    if tray_occ:
        tray_occ.isLightBulbOn = True

    f3d = os.path.join(out, "rovable_v2.f3d")
    em = design.exportManager
    report["f3d"] = bool(em.execute(em.createFusionArchiveExportOptions(f3d)))
    try:
        # app.data.activeProject raised InternalValidationError when run from a spooled script, so the
        # project is found by name instead.
        projects = app.data.dataProjects
        project = next((projects.item(i) for i in range(projects.count) if projects.item(i).name == SAVE_PROJECT), None)
        report["project"] = project.name if project else None
        report["saved"] = bool(project and doc.saveAs(DOC_NAME, project.rootFolder,
                                                      "Rovable v2, built from rovable_v2_geom.py", ""))
    except FUSION_ERRORS:
        report["saved"] = False
        report["save_error"] = traceback.format_exc()
    report["doc_name_now"] = doc.name
