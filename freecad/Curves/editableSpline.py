from __future__ import division # allows floating point division from integers
import FreeCAD, Part, math
import os, dummy, FreeCADGui
from FreeCAD import Base
from pivy import coin
import CoinNodes
import selFilter

path_curvesWB = os.path.dirname(dummy.__file__)
path_curvesWB_icons =  os.path.join( path_curvesWB, 'Resources', 'icons')

DEBUG = 1

def debug(string):
    if DEBUG:
        FreeCAD.Console.PrintMessage(string)
        FreeCAD.Console.PrintMessage("\n")

def getString(weights):
    weightStr = []
    for w in weights:
        if w == 1.0:
            weightStr.append("")
        elif w.is_integer():
            weightStr.append(" %d"%int(w))
        else:
            weightStr.append(" %0.2f"%w)
    return(weightStr)

class makeSpline:
    def __init__(self, obj , edge):
        ''' Add the properties '''
        debug("\Spline class Init\n")
        obj.addProperty("App::PropertyIntegerConstraint", "Degree",    "General", "Degree")
        obj.addProperty("App::PropertyInteger",           "Pole",      "Poles",   "Pole number").Pole = 1
        obj.addProperty("App::PropertyFloat",             "X",         "Poles",   "X coordinate of the selected pole").X=0.0
        obj.addProperty("App::PropertyFloat",             "Y",         "Poles",   "Y coordinate of the selected pole").Y=0.0
        obj.addProperty("App::PropertyFloat",             "Z",         "Poles",   "Z coordinate of the selected pole").Z=0.0
        obj.addProperty("App::PropertyFloatConstraint",   "W",         "Poles",   "Weight of the selected pole")
        obj.addProperty("App::PropertyVectorList",        "Poles",     "General", "Poles")
        obj.addProperty("App::PropertyVectorList",        "KnotPoints","General", "KnotPoints")
        obj.addProperty("App::PropertyFloatList",         "Weights",   "General", "Weights")
        obj.addProperty("App::PropertyFloatList",         "Knots",     "General", "Knots")
        obj.addProperty("App::PropertyIntegerList",       "Mults",     "General", "Mults")
        obj.addProperty("App::PropertyVectorList",        "CurvePts",  "General", "CurvePts")
        #obj.addProperty("Part::PropertyPartShape",        "Shape",     "General", "Shape")
        obj.Proxy = self
        try:
            self.curve = edge.Curve.toBSpline()
            self.curve.segment(edge.FirstParameter,edge.LastParameter)
        except:
            e = edge.toNurbs().Edges[0]
            self.curve = e.Curve.toBSpline()
            self.curve.segment(e.FirstParameter,e.LastParameter)
        obj.Poles = self.curve.getPoles()
        obj.Weights = self.curve.getWeights()
        if isinstance(self.curve,Part.BSplineCurve):
            obj.Knots = self.curve.getKnots()
            self.getKnotPoints(obj)
            obj.Mults = [int(i) for i in self.curve.getMultiplicities()]
        else:
            obj.Knots = []
            obj.KnotPoints = []
            obj.Mults = []
        obj.Degree = (int(self.curve.Degree),1,8,1)
        obj.W = (1.0,0.0001,1000.0,0.1)
        obj.setEditorMode("Weights", 2)
        self.execute(obj)

    #def curve(self, obj):
        #if obj.Knots:
            #bs = Part.BSplineCurve()
            #bs.buildFromPolesMultsKnots(obj.Poles, obj.Mults, obj.Knots, False, obj.Degree, obj.Weights)
        #else:
            #bs = Part.BezierCurve()
            #bs.increase(obj.Degree)
            #bs.setPoles(obj.Poles)
            #for i in range(len(obj.Weights)):
                #bs.setWeight(i+1,obj.Weights[i])
        #return(bs)

    def getKnotPoints(self, obj):
        knotPoints = []
        for k in obj.Knots:
            p = self.curve.value(k)
            knotPoints.append((p.x,p.y,p.z))
        obj.KnotPoints = knotPoints

    def checkCurve(self, obj):
        try:
            c = self.curve
        except:
            if hasattr(obj.Shape,'Curve'):
                self.curve = obj.Shape.Curve

    def execute(self, obj):
        debug("\n* Spline : execute *\n")
        self.checkCurve(obj)
        obj.CurvePts = self.curve.discretize(100)
        obj.Shape = self.curve.toShape()

    def onChanged(self, fp, prop):
        self.checkCurve(fp)
        if (prop == "Degree"):
            if fp.Degree > int(self.curve.Degree):
                if isinstance(self.curve,Part.BezierCurve):
                    self.curve.increase(fp.Degree)
                elif isinstance(self.curve,Part.BSplineCurve):
                    self.curve.increaseDegree(fp.Degree)
            elif fp.Degree < int(self.curve.Degree):
                pts = self.curve.discretize(Number = 100)
                bscurve = Part.BSplineCurve() #self.curve.approximateBSpline(0.1,12,fp.Degree,'C2')
                bscurve.approximate(Points = pts, DegMin = fp.Degree, DegMax = fp.Degree, Tolerance = 0.01)
                self.curve = bscurve
                fp.Degree = int(bscurve.Degree)
            fp.Poles = self.curve.getPoles()
            fp.Weights = self.curve.getWeights()
            if isinstance(self.curve,Part.BSplineCurve):
                fp.Knots = self.curve.getKnots()
                self.getKnotPoints(fp)
                fp.Mults = [int(i) for i in self.curve.getMultiplicities()]
            fp.Pole = fp.Pole
            fp.CurvePts = self.curve.discretize(100)
            debug("Spline : Degree changed to "+str(fp.Degree)+"\n")
        if prop == "Pole":
            if fp.Pole < 1:
                fp.Pole = 1
            elif fp.Pole > len(self.curve.getPoles()):
                fp.Pole = len(self.curve.getPoles())
            v = self.curve.getPole(fp.Pole)
            w = self.curve.getWeight(fp.Pole)
            fp.X = v.x
            fp.Y = v.y
            fp.Z = v.z
            fp.W = w
            #fp.Poles = self.curve.getPoles()
            #fp.Weights = self.curve.getWeights()
            #fp.touch()
            debug("Spline : Pole changed to "+str(fp.Pole)+"\n")
        if (prop == "X") | (prop == "Y") | (prop == "Z"):
            v = FreeCAD.Vector(fp.X,fp.Y,fp.Z)
            self.curve.setPole(fp.Pole,v)
            fp.Poles = self.curve.getPoles()
            debug("Spline : Coordinate changed\n")
        if (prop == "W"):
            #v = FreeCAD.Vector(fp.X,fp.Y,fp.Z)
            self.curve.setWeight(fp.Pole,fp.W)
            fp.Weights = self.curve.getWeights()
            debug("Spline : Weight changed\n")
        if (prop == "Poles"):
            #fp.Weights = self.curve.getWeights()
            debug("Spline : Poles changed\n")
        if (prop == "Weights"):
            #fp.Poles = self.curve.getPoles()
            debug("Spline : Weights changed\n")
        if (prop == "Knots"):
            if fp.Knots:
                self.getKnotPoints(fp)
            #fp.Mults = [int(i) for i in self.curve.getMultiplicities()]
            debug("Spline : Knots changed\n")
        if (prop == "Mults"):
            #fp.Knots = self.curve.getKnots()
            debug("Spline : Mults changed\n")
            oldMults = self.curve.getMultiplicities()
            if len(fp.Mults) == len(oldMults):
                for i in range(len(fp.Mults)):
                    if fp.Mults[i] > oldMults[i]:
                        self.curve.increaseMultiplicity(i+1,fp.Mults[i])
                    elif fp.Mults[i] < oldMults[i]:
                        self.curve.removeKnot(i+1, fp.Mults[i], 0.01) # add property tolerance here
            fp.Mults = [int(i) for i in self.curve.getMultiplicities()]

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None


class SplineVP:
    def __init__(self, obj ):
        ''' Add the properties '''
        self.oldDM = 'Wireframe'
        obj.Proxy = self

    def attach(self, obj):
        debug("\nSplineVP.attach \n")

        self.curveDM = coin.SoSeparator()
        self.polesDM = coin.SoSeparator()
        self.polesDM.setName("Poles")
        self.curveDM.setName("Curve")
        self.curvePolesDM = coin.SoSeparator()
        
        # *** Set the Poles view nodes *** 
        self.polesnode = CoinNodes.coordinate3Node()
        self.weightStr = []
        self.polySep = CoinNodes.polygonNode((0.5,0.5,0.5),1)
        self.markerSep = CoinNodes.markerSetNode((1,0,0),coin.SoMarkerSet.DIAMOND_FILLED_7_7)
        self.weightSep = CoinNodes.multiTextNode((1,0,0),"osiFont,FreeSans,sans",16,0)

        # *** Set knots ***
        #knotPoints = []
        #for k in knots:
            #p = cur.value(k)
            #knotPoints.append((p.x,p.y,p.z))
        
        # *** Set the knots view nodes *** 
        self.knotsnode = CoinNodes.coordinate3Node() #knotPoints)
        self.multStr = []
        self.knotMarkerSep = CoinNodes.markerSetNode((0,0,1),coin.SoMarkerSet.CIRCLE_FILLED_7_7)      
        self.multSep = CoinNodes.multiTextNode((0,0,1),"osiFont,FreeSans,sans",16,1)

        # *** Set the active pole view nodes *** 
        self.activePole = CoinNodes.markerSetNode((1,1,0),coin.SoMarkerSet.CIRCLE_LINE_9_9)
        self.activePole.markers.startIndex = 0
        self.activePole.markers.numPoints = 1

        # *** Set the curve view node *** 
        self.curvePts = CoinNodes.coordinate3Node()
        self.curveSep = CoinNodes.polygonNode((0,0,0),1)

        self.polesDM.addChild(self.polesnode)
        self.polesDM.addChild(self.polySep)
        self.polesDM.addChild(self.markerSep)
        self.polesDM.addChild(self.weightSep)
        self.polesDM.addChild(self.activePole)
        self.polesDM.addChild(self.knotsnode)
        self.polesDM.addChild(self.knotMarkerSep)
        self.polesDM.addChild(self.multSep)

        self.curveDM.addChild(self.curvePts)
        self.curveDM.addChild(self.curveSep)
        
        #self.selectionNode = coin.SoType.fromName("SoFCSelection").createInstance()
        #self.selectionNode.documentName.setValue(FreeCAD.ActiveDocument.Name)
        #self.selectionNode.objectName.setValue(obj.Object.Name) # here obj is the ViewObject, we need its associated App Object
        #self.selectionNode.subElementName.setValue("Curve")
        #self.selectionNode.addChild(self.curveDM)

        self.curvePolesDM.addChild(self.curveDM)
        self.curvePolesDM.addChild(self.polesDM)

        #self.curveDM.addChild(self.selectionNode)        
        #self.curvePolesDM.addChild(self.selectionNode)  
        
        
        
        #obj.addDisplayMode(self.curveDM,"Curve")
        obj.addDisplayMode(self.curvePolesDM,"Poles")

    def updateData(self, fp, prop):
        #debug("updateData : "+str(prop)+"\n")
        if prop == "Poles":
            self.polesnode.points = fp.Poles
            self.weightStr = getString(fp.Weights)
            self.polySep.vertices = self.polesnode.points
            debug("--- "+str(len(self.weightStr))+"\n")
            debug("--- "+str(len(self.polesnode.points))+"\n")
            self.weightSep.data = (self.polesnode.points,self.weightStr)
        if prop == "Weights":
            self.polesnode.points = fp.Poles
            self.weightStr = getString(fp.Weights)
            debug("--- "+str(len(self.weightStr))+"\n")
            debug("--- "+str(len(self.polesnode.points))+"\n")
            #self.polySep.vertices = self.polesnode.points
            self.weightSep.data = (self.polesnode.points,self.weightStr)
        if prop == "Knots":
            if fp.Knots:
                self.knotsnode.points = fp.KnotPoints
                self.multStr = []
                for m in fp.Mults:
                    self.multStr.append("%d"%m)
                #self.polySep.vertices = self.polesnode.points
                self.multSep.data = (self.knotsnode.points,self.multStr)
            else:
                self.knotsnode.points = [fp.Poles[0]]
            #elif fp.Poles:
                #self.knotsnode.points = [fp.Poles[0]]
                #self.multStr = [""]
                #self.multSep.data = (self.knotsnode.points,self.multStr)
            #else:
                #debug("%s"%str(fp.Poles[0]))
        if prop == "Mults":
            if fp.Mults:
                #self.polesnode.points = fp.Poles
                self.multStr = []
                for m in fp.Mults:
                    self.multStr.append("%d"%m)
                #self.polySep.vertices = self.polesnode.points
                self.multSep.data = (self.knotsnode.points,self.multStr)
        if prop == "Pole":
            self.activePole.markers.startIndex = fp.Pole - 1
        if prop == "CurvePts":
            self.curvePts.points = fp.CurvePts
            self.curveSep.vertices = self.curvePts.points

    def getDisplayModes(self,obj):
         "Return a list of display modes."
         modes=[]
         #modes.append("Curve")
         modes.append("Poles")
         return modes

    def getDefaultDisplayMode(self):
         '''Return the name of the default display mode. It must be defined in getDisplayModes.'''
         return "Wireframe"

    def setDisplayMode(self,mode):
         return mode

    def onChanged(self, vp, prop):
        '''Here we can do something when a single property got changed'''
        debug("\nonChanged : "+str(prop)+"\n")
        #if prop == "Edge":
            #debug("\n\n\nvp detected a Edge change\n\n\n")
        #if prop == "CurveColor":
            #self.curveColor.rgb = (vp.CurveColor[0],vp.CurveColor[1],vp.CurveColor[2])
        #elif prop == "CombColor":
            #self.combColor.rgb  = (vp.CombColor[0],vp.CombColor[1],vp.CombColor[2])
        return

    def doubleClicked(self,vobj):
        debug("Double-clicked")
        if not vobj.DisplayMode == "Poles":
            self.oldDM = vobj.DisplayMode
            vobj.DisplayMode = "Poles"
        else:
            vobj.DisplayMode = self.oldDM
        return True

    def getIcon(self):
        return (path_curvesWB_icons+'/editableSpline.svg')

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None


class editableSpline:

    def Activated(self):
        s = FreeCADGui.Selection.getSelectionEx()
        f = selFilter.selFilter(s)
        edges = f.getEdgeShapes()
        vertexes = f.getVertexShapes()
        for i in range(0,len(vertexes)-1,2):
            pts = [vertexes[i].Point,vertexes[i+1].Point]
            bez = Part.BezierCurve()
            bez.setPoles(pts)
            print(bez)
            edges.append(bez.toShape())
        for e in edges:
            obj=FreeCAD.ActiveDocument.addObject("Part::FeaturePython","Spline") #add object to document
            makeSpline(obj,e)
            SplineVP(obj.ViewObject)
            obj.ViewObject.DisplayMode = "Poles"
        f.hideAll()
        FreeCAD.ActiveDocument.recompute()
            
    def GetResources(self):
        return {'Pixmap' : path_curvesWB_icons+'/editableSpline.svg', 'MenuText': 'editableSpline', 'ToolTip': 'Creates an editable spline from selected edges'}

FreeCADGui.addCommand('editableSpline', editableSpline())



