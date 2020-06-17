import os
import FreeCAD, FreeCADGui, Part
from pivy import coin
import CoinNodes
import HUD
import dummy

path_curvesWB = os.path.dirname(dummy.__file__)
path_curvesWB_icons =  os.path.join( path_curvesWB, 'Resources', 'icons')

class bezierCurve:
    """Create a Bspline curve"""
    def Activated(self):
        self.view = FreeCADGui.ActiveDocument.ActiveView
        self.viewer = self.view.getViewer()
        self.oldRadius = self.viewer.getPickRadius()
        self.viewer.setPickRadius(25.0)

        self.obj = FreeCAD.ActiveDocument.addObject("Part::Spline","BSplineCurve")

        self.stack = [FreeCAD.Vector(0,0,0)]
        self.markerPos = None
        self.snap = False
        self.snapShape = None
        self.point = FreeCAD.Vector(0,0,0)
        self.curve = Part.BSplineCurve()
        self.degree = 1
        self.mults = [2,2]
        self.knots = [0.]

        self.clicCB     = self.view.addEventCallbackPivy( coin.SoMouseButtonEvent.getClassTypeId(), self.clic_cb)
        self.keyboardCB = self.view.addEventCallbackPivy( coin.SoKeyboardEvent.getClassTypeId(), self.kb_cb)
        self.cursorCB   = self.view.addEventCallbackPivy( coin.SoLocation2Event.getClassTypeId(), self.cursor_cb)

        self.nodeInit()
        for st in self.info:
            FreeCAD.Console.PrintError(st+"\n")

    def nodeInit(self):
        self.sg = self.view.getSceneGraph()
        self.coord = CoinNodes.coordinate3Node([(0,0,0)])
        self.markers = CoinNodes.markerSetNode((1,0.35,0.8),70)
        self.polygon = coin.SoLineSet() #CoinNodes.sensorPolyNode((0.0,0.5,0.0),1)
        #self.polygon.transparency = 0.7
        #self.polygon.linkTo(self.coord)
        self.switch = coin.SoSwitch()
        self.empty = coin.SoSeparator()
        self.sepa = coin.SoSeparator()
        self.switch.addChild(self.sepa)
        self.switch.addChild(self.empty)
        self.switch.whichChild = 0
        self.sepa.addChild(self.coord)
        self.sepa.addChild(self.markers)
        self.sg.addChild(self.switch)

        self.info = ["LMB : add pole",
                     "Del : remove last pole",
                     "I / D : Increase / Decrease degree",
                     "Left CTRL : snap",
                     "Enter : Accept",
                     "Esc : Abort"]
        self.Block1 = HUD.textArea()
        self.Block1.setFont("Sans", 12.0, (0.,0.,0.))
        self.Block1.text = self.info + ["Degree : %s"%self.curve.Degree]

        self.myHud = HUD.HUD()
        self.myHud.addBlock(self.Block1)
        self.myHud.add()

    def getGeomPoint(self):
        obj = FreeCAD.getDocument(self.snapShape[0]).getObject(self.snapShape[1])
        FreeCAD.Console.PrintMessage('%s\n'%str(self.snapShape))
        if 'Vertex' in self.snapShape[2]:
            n = eval(self.snapShape[2].lstrip('Vertex'))
            shape = obj.Shape.Vertexes[n-1]
        if 'Point' in self.snapShape[2]: # Datum Point
            shape = obj.Shape
        elif 'Edge' in self.snapShape[2]:
            n = eval(self.snapShape[2].lstrip('Edge'))
            shape = obj.Shape.Edges[n-1]
        elif 'Face' in self.snapShape[2]:
            n = eval(self.snapShape[2].lstrip('Face'))
            shape = obj.Shape.Faces[n-1]
        v = Part.Vertex(self.point)
        dist, pts, sols = v.distToShape(shape)
        if len(pts) == 2:
            self.point = pts[1]

    def increaseDegree(self):
        if len(self.stack) > self.degree + 1:
            self.mults.pop(-2)
            self.mults[0] += 1
            self.mults[-1] += 1
            self.knots.pop(-1)
            self.degree += 1
            self.updateCurve()

    def decreaseDegree(self):
        if (self.degree > 1):
            self.mults.insert(-1,1)
            self.mults[0] -= 1
            self.mults[-1] -= 1
            self.knots.append(self.knots[-1]+1.)
            self.degree -= 1
            self.updateCurve()

    def addPole(self):
        if self.snap:
            self.getGeomPoint()
        self.stack.append(self.point)
        self.coord.add((self.point.x, self.point.y, self.point.z))
        if len(self.stack) > self.degree + 1:
            self.mults.insert(-1,1)
        self.knots.append(self.knots[-1]+1.)
        if len(self.stack) == 2:
            self.sepa.addChild(self.polygon) # polygon can be added several times !!!!
        elif len(self.stack) in [3,4]:
            self.increaseDegree()
        #elif len(self.stack) >= 24:
            #self.finish()
        if len(self.stack) > 2:
            self.updateCurve()

    def removePole(self):
        if (len(self.stack) > 2):
            if (len(self.stack) <= self.degree + 1):
                self.decreaseDegree()
            self.stack.pop(-1)
            self.coord.pop(-1)
            self.mults.pop(-2)
            self.knots.pop(-1)
            self.cursorUpdate()

    def updateCurve(self):
        self.curve = Part.BSplineCurve()
        self.curve.buildFromPolesMultsKnots(self.stack,self.mults,self.knots,False,self.degree)
        self.obj.Shape = self.curve.toShape()
        self.Block1.text = self.info + ["Degree : %s"%self.curve.Degree]

    def cursorUpdate(self):
        l = len(self.coord.point.getValues())
        self.coord.point.set1Value(l-1,self.point)
        self.stack[-1] = self.point
        if len(self.stack) >1:
            self.updateCurve()

    def accept(self):
        if len(self.stack) > 2:
            #discards the last moving pole
            if self.degree == len(self.stack) - 1:
                self.decreaseDegree()
            self.stack.pop(-1)
            if len(self.mults) > 2:
                self.mults.pop(-2)
            if len(self.knots) > 2:
                self.knots.pop(-1)
        self.updateCurve()

    def finish(self):
        self.view.removeEventCallbackPivy( coin.SoLocation2Event.getClassTypeId(), self.cursorCB)
        self.view.removeEventCallbackPivy( coin.SoKeyboardEvent.getClassTypeId(), self.keyboardCB)
        self.view.removeEventCallbackPivy( coin.SoMouseButtonEvent.getClassTypeId(), self.clicCB)

        #self.polygon.unlink()
        self.myHud.remove()
        self.viewer.setPickRadius(self.oldRadius)

        self.switch.whichChild = 1

    def abort(self):
        FreeCAD.ActiveDocument.removeObject(self.obj.Name)

    def getSnapPoint(self,pos):
        listObjects = FreeCADGui.ActiveDocument.ActiveView.getObjectsInfo((pos[0],pos[1]))
        if not listObjects == None:
            for dic in listObjects:
                if not dic['Object'] == self.obj.Name:
                    self.point = FreeCAD.Vector(dic['x'], dic['y'], dic['z'])
                    self.snapShape = (dic['Document'], dic['Object'], dic['Component'])
                    return()

    def kb_cb(self, event_callback):
        event = event_callback.getEvent()
        if (type(event) == coin.SoKeyboardEvent):
            key = ""
            try:
                key = event.getKey()
            except ValueError:
                # there is no character for this value
                key = ""
            if key == coin.SoKeyboardEvent.LEFT_CONTROL:
                if event.getState() == coin.SoButtonEvent.DOWN:
                    self.snap = True
                elif event.getState() == coin.SoButtonEvent.UP:
                    self.snap = False
            elif key == coin.SoKeyboardEvent.RETURN:
                self.accept()
                self.finish()
            elif key == coin.SoKeyboardEvent.BACKSPACE and event.getState() == coin.SoButtonEvent.UP:
                self.removePole()
            elif key == coin.SoKeyboardEvent.I and event.getState() == coin.SoButtonEvent.UP:
                self.increaseDegree()
            elif key == coin.SoKeyboardEvent.D and event.getState() == coin.SoButtonEvent.UP:
                self.decreaseDegree()
            elif key == coin.SoKeyboardEvent.ESCAPE:
                self.abort()
                self.finish()

    def clic_cb(self, event_callback):
        event = event_callback.getEvent()
        if (type(event) == coin.SoMouseButtonEvent and
                event.getState() == coin.SoMouseButtonEvent.DOWN
                and event.getButton() == coin.SoMouseButtonEvent.BUTTON1):
            self.addPole()
            #FreeCADGui.Selection.clearSelection()

    def cursor_cb(self, event_callback):
        pos = FreeCADGui.ActiveDocument.ActiveView.getCursorPos()
        self.point = self.view.getPoint(pos[0],pos[1])
        if self.snap:
            self.getSnapPoint(pos)
        self.cursorUpdate()


    def GetResources(self):
        return {'Pixmap' : path_curvesWB_icons+'/bezier.svg', 'MenuText': 'BSpline Curve', 'ToolTip': 'Creates a BSpline curve'}
FreeCADGui.addCommand('bezierCurve', bezierCurve())
