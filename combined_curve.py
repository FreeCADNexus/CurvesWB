# -*- coding: utf-8 -*-

__title__ = "Combined projection curve"
__author__ = "Christophe Grellier (Chris_G)"
__license__ = "LGPL 2.1"
__doc__ = "Builds a 3D curve as the intersection of 2 projected curves."

import FreeCAD
import FreeCADGui
import Part
import _utils
import approximate_extension

TOOL_ICON = _utils.iconsPath() + '/combined_curve.svg'
debug = _utils.debug
#debug = _utils.doNothing

class CombinedProjectionCurve:
    """Builds a 3D curve as the intersection of 2 projected curves."""
    def __init__(self, sh1, sh2, dir1, dir2):
        self.shape1 = sh1
        self.shape2 = sh2
        if not dir1.Length == 0:
            self.dir1 = dir1
        else:
            raise ValueError("Vector is null")
        if not dir2.Length == 0:
            self.dir2 = dir2
        else:
            raise ValueError("Vector is null")
    def shape(self):
        proj1 = self.shape1.toNurbs().extrude(self.dir1)
        proj2 = self.shape2.toNurbs().extrude(self.dir2)
        curves = list()
        for f1 in proj1.Faces:
            for f2 in proj2.Faces:
                curves += f1.Surface.intersectSS(f2.Surface)
        intersect = [c.toShape() for c in curves]
        edges = []
        for sh in intersect:
            if isinstance(sh, Part.Edge) and sh.Length > 1e-7:
                edges.append(sh)
        se = Part.sortEdges(edges)
        wires = []
        for el in se:
            wires.append(Part.Wire(el))
        return Part.Compound(wires)



class CombinedProjectionCurveFP:
    """Builds a 3D curve as the intersection of 2 projected curves."""
    def __init__(self, obj, s1, s2, d1, d2):
        obj.addProperty("App::PropertyLink", "Shape1", "Combined Projection", "First shape").Shape1 = s1
        obj.addProperty("App::PropertyLink", "Shape2", "Combined Projection", "Second shape").Shape2 = s2
        obj.addProperty("App::PropertyVector", "Direction1", "Combined Projection", "Projection direction of the first shape.\nIf vector is null, shape's placement is used.").Direction1 = d1
        #obj.addProperty("App::PropertyPlacement", "Direction1", "Combined Projection", "Projection direction of the first shape").Direction1 = pl1
        obj.addProperty("App::PropertyVector", "Direction2", "Combined Projection", "Projection direction of the second shape.\nIf vector is null, shape's placement is used.").Direction2 = d2
        obj.Proxy = self

    def execute(self, obj):
        s1 = obj.Shape1.Shape
        s2 = obj.Shape2.Shape
        if obj.Direction1.Length < 1e-7:
            d1 = obj.Shape1.Placement.Rotation.multVec(FreeCAD.Vector(0,0,-1))
        else:
            d1 = obj.Direction1
        if obj.Direction2.Length < 1e-7:
            d2 = obj.Shape2.Placement.Rotation.multVec(FreeCAD.Vector(0,0,-1))
        else:
            d2 = obj.Direction2
        cc = CombinedProjectionCurve(s1,s2,d1,d2)
        if hasattr(obj,"ExtensionProxy"):
            obj.Shape = obj.ExtensionProxy.approximate(obj,cc.shape().Edges)
        else:
            obj.Shape = cc.shape()

    def onChanged(self, fp, prop):
        if hasattr(fp,"ExtensionProxy"):
            fp.ExtensionProxy.onChanged(fp, prop)

class CombinedProjectionCurveVP:
    def __init__(self,vobj):
        vobj.Proxy = self
       
    def getIcon(self):
        return (TOOL_ICON)

    def attach(self, vobj):
        self.Object = vobj.Object

    def __getstate__(self):
        return {"name": self.Object.Name}

    def __setstate__(self,state):
        self.Object = FreeCAD.ActiveDocument.getObject(state["name"])
        return None

    def claimChildren(self):
        return [self.Object.Shape1,self.Object.Shape2]

class CombinedProjectionCmd:
    """Splits the selected edges."""
    def makeCPCFeature(self,o1,o2,d1,d2):
        cc = FreeCAD.ActiveDocument.addObject("Part::FeaturePython","Combined_projection_curve")
        CombinedProjectionCurveFP(cc, o1,o2,d1,d2)
        approximate_extension.ApproximateExtension(cc)
        cc.Active = False
        CombinedProjectionCurveVP(cc.ViewObject)
        FreeCAD.ActiveDocument.recompute()

    def Activated(self):
        vd = [FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,0)]
        try:
            sel = FreeCADGui.activeWorkbench().Selection
            vd =  FreeCADGui.activeWorkbench().View_Directions
        except AttributeError:
            sel = FreeCADGui.Selection.getSelectionEx()
        if not len(sel) == 2:
            FreeCAD.Console.PrintError("Select 2 objects !\n")
            return
        for selobj in sel:
            selobj.Object.ViewObject.Visibility = False
        if len(vd) == 2 and vd[0].dot(vd[1]) < 0.999:
            d1, d2 = vd
        else:
            d1,d2 = [FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,0)]
        self.makeCPCFeature(sel[0].Object,sel[1].Object,d1,d2)
        
    def IsActive(self):
        if FreeCAD.ActiveDocument:
            sel = FreeCADGui.Selection.getSelection()
            if len(sel) == 2:
                return True
        return False

    def GetResources(self):
        return {'Pixmap' : TOOL_ICON, 'MenuText': 'Combined projection curve', 'ToolTip': 'Builds a 3D curve as the intersection of 2 projected curves'}

FreeCADGui.addCommand('combined_projection', CombinedProjectionCmd())
