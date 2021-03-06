import sys, math, random
from  PyQt4 import QtCore, QtGui

class Edge(QtGui.QGraphicsItem):
   def __init__(self, sourceNode, destNode):
      QtGui.QGraphicsItem.__init__(self)
      self.arrowSize = 10.0
      self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
      self.source = sourceNode
      self.dest = destNode
      self.source.addEdge(self)
      self.dest.addEdge(self)
      self.adjust()

   def sourceNode(self):
      return self.source

   def setSourceNode(self, node):
      self.source = node
      self.adjust()

   def destNode(self):
      return self.dest

   def setDestNode(self, node):
      self.dest = node
      self.adjust()

   def adjust(self):
      if self.source is None or self.dest is None:
         return

      line = QtCore.QLineF(self.mapFromItem(self.source, 0, 0),
                           self.mapFromItem(self.dest, 0, 0))
      length = line.length()
      if length == 0:
         edgeOffset = QtCore.QPointF(0, 0)
      else:
         edgeOffset = QtCore.QPointF((line.dx() * 10) / length, (line.dy() * 10) / length)

      self.removeFromIndex()
      self.sourcePoint = line.p1() + edgeOffset
      self.destPoint = line.p2() - edgeOffset
      self.addToIndex()

   Type = QtGui.QGraphicsItem.UserType + 2

   def type(self):
      return self.Type
    
   def boundingRect(self):
      if self.source is None or self.dest is None:
         return QtCore.QRectF()

      penWidth = 1.0
      extra = (penWidth + self.arrowSize) / 2.0

      return QtCore.QRectF(self.sourcePoint, QtCore.QSizeF(self.destPoint.x() - self.sourcePoint.x(),
                                                           self.destPoint.y() - self.sourcePoint.y())).normalized().adjusted(-extra, -extra, extra, extra)

   def paint(self, painter, option, widget):
      if self.source is None or self.dest is None:
         return QtCore.QRectF()

      line = QtCore.QLineF(self.sourcePoint, self.destPoint)
      painter.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.SolidLine,
                                QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
      painter.drawLine(line)

      if line.length() == 0:
         angle = 0.0
      else:
         angle = math.acos(line.dx() / line.length())
      if line.dx() >= 0:
         angle = 6.28 - angle

      sourceArrowP1 = self.sourcePoint + QtCore.QPointF(math.sin(angle + 3.14 / 3.0) * self.arrowSize,
                                                        math.cos(angle + 3.14 / 3.0) * self.arrowSize)
      sourceArrowP2 = self.sourcePoint + QtCore.QPointF(math.sin(angle + 3.14 - 3.14 / 3.0) * self.arrowSize,
                                                        math.cos(angle + 3.14 - 3.14 / 3.0) * self.arrowSize)

      destArrowP1 = self.destPoint + QtCore.QPointF(math.sin(angle - 3.14 / 3.0) * self.arrowSize,
                                                    math.cos(angle - 3.14 / 3.0) * self.arrowSize)
      destArrowP2 = self.destPoint + QtCore.QPointF(math.sin(angle - 3.14 + 3.14 / 3.0) * self.arrowSize,
                                                    math.cos(angle - 3.14 + 3.14 / 3.0) * self.arrowSize)

      painter.setBrush(QtCore.Qt.black)

      polygon1 = QtGui.QPolygonF()
      polygon1.append(line.p1())
      polygon1.append(sourceArrowP1)
      polygon1.append(sourceArrowP2)
      painter.drawPolygon(polygon1)

      polygon2 = QtGui.QPolygonF()
      polygon2.append(line.p2())
      polygon2.append(destArrowP1)
      polygon2.append(destArrowP2)
      painter.drawPolygon(polygon2)

class ChoiceItem(QtGui.QGraphicsItem):
   def __init__(self, graphWidget):
      QtGui.QGraphicsItem.__init__(self)
      self.edgeList = []
      self.newPos = QtCore.QPointF()
      self.graph = graphWidget
      self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
      self.setZValue(1)
      self.dropShadowWidth = 5.0
      self.penWidth = 1
      self.mSize = QtCore.QSizeF(100.0, 100.0)

   def addEdge(self, edge):
      self.edgeList.append(edge)
      edge.adjust()

   def edges(self):
      return self.edgeList

   Type = QtGui.QGraphicsItem.UserType + 1

   def type(self):
      return self.Type

   def calculateForces(self):
      if self.scene() is None or self.scene().mouseGrabberItem() is self:
         self.newPos = self.pos()
         return

      xvel = 0.0
      yvel = 0.0
      for item in self.scene().items():
         if not isinstance(item, Node):
            continue

         line = QtCore.QLineF(self.mapFromItem(item, 0, 0), QtCore.QPointF(0, 0))
         dx = line.dx()
         dy = line.dy()
         l = 2.0 * (dx * dx + dy * dy)
         if l > 0:
            xvel += (dx * 150.0) / l
            yvel += (dy * 150.0) / l

      weight = (len(self.edgeList) + 1) * 10.0
      for edge in self.edgeList:
         if edge.sourceNode() is self:
            pos = self.mapFromItem(edge.destNode(), 0, 0)
         else:
            pos = self.mapFromItem(edge.sourceNode(), 0, 0)
         xvel += pos.x() / weight
         yvel += pos.y() / weight

      if math.fabs(xvel) < 0.1 and math.fabs(yvel) < 0.1:
         xvel = 0.0
         yvel = 0.0

      sceneRect = self.scene().sceneRect()
      self.newPos = self.pos() + QtCore.QPointF(xvel, yvel)
      self.newPos.setX(min(max(self.newPos.x(), sceneRect.left() + 10), sceneRect.right() - 10))
      self.newPos.setY(min(max(self.newPos.y(), sceneRect.top() + 10), sceneRect.bottom() - 10))

   def advance(self):
      if self.newPos == self.pos():
         return False

      self.setPos(self.newPos)
      return True

   def boundingRect(self):
      """ This pure virtual function defines the outer bounds of the item as a
          rectangle; all painting must be restricted to inside an item's bounding
          rect. QGraphicsView uses this to determine whether the item requires
          redrawing.
      """

      rect = QtCore.QRectF(-self.mSize.width()/2.0, -self.mSize.height()/2.0, self.mSize.width(), self.mSize.height())
      rect.adjust(-(self.penWidth/2), -(self.penWidth/2),
                  self.dropShadowWidth, self.dropShadowWidth)
      return rect

   def shape(self):
      """ Returns the shape of this item as a QPainterPath in local
          coordinates. The shape is used for many things, including
          collision detection, hit tests, and for the QGraphicsScene::items()
          functions.
      """
      path = QtGui.QPainterPath()
      rect = self.boundingRect()
      path.addRect(rect)
      return path

   def paint(self, painter, option, widget):
      rect = QtCore.QRectF(-self.mSize.width()/2.0, -self.mSize.height()/2.0, self.mSize.width(), self.mSize.height())
      shadow_rect = rect.translated(self.dropShadowWidth, self.dropShadowWidth)

      color = QtGui.QColor(QtCore.Qt.darkGray)
      color.setAlpha(100)
      painter.setPen(QtCore.Qt.NoPen)
      painter.setBrush(color)
      painter.drawRoundRect(shadow_rect)

      painter.setPen(QtCore.Qt.NoPen)
      color = QtGui.QColor(0, 127, 127, 191)
      painter.setBrush(color)

      painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
      painter.setRenderHint(QtGui.QPainter.Antialiasing)
      painter.drawRoundRect(rect)

   def itemChange(self, change, value):
      if change == QtGui.QGraphicsItem.ItemPositionChange:
         for edge in self.edgeList:
            edge.adjust()
         #self.graph.itemMoved()

      return QtGui.QGraphicsItem.itemChange(self, change, value)

   def mousePressEvent(self, event):
      self.update()
      QtGui.QGraphicsItem.mousePressEvent(self, event)

   def mouseReleaseEvent(self, event):
      self.update()
      QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

class GraphWidget(QtGui.QGraphicsView):
   def __init__(self):
      QtGui.QGraphicsView.__init__(self)
      #self.timerId = 0
      scene = QtGui.QGraphicsScene(self)
      scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
      scene.setSceneRect(-200, -200, 400, 400)
      self.setScene(scene)
      self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
      self.setRenderHint(QtGui.QPainter.Antialiasing)
      self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
      self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)

      self.scale(0.8, 0.8)
      self.setMinimumSize(400, 400)
      self.setWindowTitle("Maestro Test Nodes")

      self.mChoices = []

      for i in xrange(5):
         choice = ChoiceItem(self)
         scene.addItem(choice)
         self.mChoices.append(choice)
         choice.setPos(i*10, i*10)

      self.mEdges = []
      edge0 = Edge(self.mChoices[0], self.mChoices[1])
      edge1 = Edge(self.mChoices[1], self.mChoices[2])
      edge2 = Edge(self.mChoices[2], self.mChoices[3])
      edge3 = Edge(self.mChoices[3], self.mChoices[4])

      scene.addItem(edge0)
      self.mEdges.append(edge0)
      scene.addItem(edge1)
      self.mEdges.append(edge1)
      scene.addItem(edge2)
      self.mEdges.append(edge2)
      scene.addItem(edge3)
      self.mEdges.append(edge3)

      self.mChoices[0].setPos(0, 0)
      self.mChoices[1].setPos(-150, 150)
      self.mChoices[2].setPos(150, 150)
      self.mChoices[3].setPos(-150, -150)
      self.mChoices[4].setPos(150, -150)

      for e in self.mEdges:
         e.adjust()

      #choice_item.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
      #choice_item.setPos(0, 0)
      #self.setInteractive(True)

   def keyPressEvent(self, event):
      key = event.key()

      if key == QtCore.Qt.Key_Plus:
         self.scaleView(1.2)
      elif key == QtCore.Qt.Key_Minus:
         self.scaleView(1 / 1.2)
      else:
         QtGui.QGraphicsView.keyPressEvent(self, event)

   def wheelEvent(self, event):
      self.scaleView(math.pow(2.0, -event.delta() / 240.0))

   def scaleView(self, scaleFactor):
      factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()
      if factor < 0.07 or factor > 100:
         return

      self.scale(scaleFactor, scaleFactor)

if __name__ == '__main__':
   app = QtGui.QApplication(sys.argv)
   random.seed(QtCore.QTime(0, 0, 0).secsTo(QtCore.QTime.currentTime()))
   widget = GraphWidget()
   widget.show()
   sys.exit(app.exec_())
