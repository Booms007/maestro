# Maestro is Copyright (C) 2006 by Infiscape
#
# Original Author: Aron Bierbaum
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import sys, socket
from PyQt4 import QtGui, QtCore
import EnsembleViewBase
import maestro.core
const = maestro.core.const
env = maestro.core.Environment
from maestro.core import Ensemble
from maestro.gui import EnsembleModel

class EnsembleViewPlugin(maestro.core.IViewPlugin):
   def __init__(self):
      maestro.core.IViewPlugin.__init__(self)
      self.widget = EnsembleView()
      
   @staticmethod
   def getName():
      return "Ensemble View"

   @staticmethod
   def getIcon():
      return QtGui.QIcon(":/Maestro/images/management.png")
      
   def getViewWidget(self):
      return self.widget

class NodeSettingsModel(QtCore.QAbstractTableModel):
   """ TableModel that represents node settings returned from
       EnsembleService.
   """
   def __init__(self, parent=None):
      QtCore.QAbstractTableModel.__init__(self, parent)

      self.mNodeSettings = {}
      self.mNodeId = None

      env().mEventManager.connect("*", "ensemble.report_settings", self.onReportSettings)

   def onReportSettings(self, nodeId, settings):
      """ Slot that gets called when a node reports it's settings. """
      self.mNodeSettings[nodeId] = settings
      if nodeId == self.mNodeId:
         self.emit(QtCore.SIGNAL("modelChanged()"))

   def setNode(self, nodeId):
      """ Set the node that we want to view settings for. """
      if isinstance(nodeId, Ensemble.ClusterNode):
         self.mNodeId = nodeId.getId()
      elif type(nodeId) == types.StringType:
         self.mNodeId = nodeId
      else:
         self.mNodeId = None

      self.emit(QtCore.SIGNAL("modelChanged()"))

   def rowCount(self, parent=QtCore.QModelIndex()):
      """ Return the number of settings for node.. """
      if not self.mNodeSettings.has_key(self.mNodeId):
         return 0
      return len(self.mNodeSettings[self.mNodeId])

   def columnCount(self, parent=QtCore.QModelIndex()):
      """ Return the number of columns of data we are showing. """
      return 2

   def headerData(self, section, orientation, role):
      """ Return the header data for the given section and orientation.

          @param section: The row or column depending on the orientation.
          @param orientation: The orientation of the header.
          @param role: Data role being requested.
      """

      # We only want to return the title for each column.
      if orientation == QtCore.Qt.Horizontal and QtCore.Qt.DisplayRole == role:
         if section == 0:
            return QtCore.QVariant("Name")
         elif section == 1:
            return QtCore.QVariant("Value")
      return QtCore.QVariant()

   def data(self, index, role):
      """ Return the model data for the given cell and data role.

          @param index: Cell that we are requesting data for.
          @param role: Data role being requested.
      """
      if not index.isValid():
         print "Invalid index"
         return QtCore.QVariant()

      # Ensure that the row is valid
      row = index.row()
      if row < 0 or row >= self.rowCount():
         return QtCore.QVariant()
      if not self.mNodeSettings.has_key(self.mNodeId):
         return QtCore.QVariant()

      # Get the settings for the selected node.
      node_settings = self.mNodeSettings[self.mNodeId]
      (name, value) = node_settings.items()[index.row()]

      if role == QtCore.Qt.DisplayRole:
         if index.column() == 0:
            # Return the name of the node.
            return QtCore.QVariant(name)
         elif index.column() == 1:
            # Return the title of the boot target
            return QtCore.QVariant(value)
      elif role == QtCore.Qt.UserRole:
         # Return the node settings for easy access.
         return node_settings

      return QtCore.QVariant()

class EnsembleView(QtGui.QWidget, EnsembleViewBase.Ui_EnsembleViewBase):
   """ Presents the user with a high level view of the entire ensemble.
       They can add/remove nodes to the ensemble and view detailed settings
       for each node.
   """
   def __init__(self, parent = None):
      QtGui.QWidget.__init__(self, parent)
      self.setupUi(self)
      self.mEnsemble = None
      self.mSelectedNode = None

   def setupUi(self, widget):
      """
      Setup all initial gui settings that don't need to know about the cluster configuration.
      """
      EnsembleViewBase.Ui_EnsembleViewBase.setupUi(self, widget)

      self.mTitleLbl.setBackgroundRole(QtGui.QPalette.Mid)
      self.mTitleLbl.setForegroundRole(QtGui.QPalette.Shadow)
      
      QtCore.QObject.connect(self.mRefreshBtn,QtCore.SIGNAL("clicked()"), self.onRefresh)
      QtCore.QObject.connect(self.mAddBtn,QtCore.SIGNAL("clicked()"), self.onAdd)
      QtCore.QObject.connect(self.mRemoveBtn,QtCore.SIGNAL("clicked()"), self.onRemove)
      # Call if you want an icon view
      #self.mClusterListView.setViewMode(QtGui.QListView.IconMode)
      self.connect(self.mNameEdit, QtCore.SIGNAL("editingFinished()"), self.onNodeSettingsChanged)
      self.connect(self.mHostnameEdit, QtCore.SIGNAL("editingFinished()"), self.onNodeSettingsChanged)


   def init(self, ensemble):
      """ Configure the user interface.

          @param ensemble: The current Ensemble configuration.
          @param eventManager: Reference to Maestro's EventManager.
      """

      # If an ensemble already exists, disconnect it.
      if self.mEnsemble is not None:
         self.disconnect(self.mEnsemble, QtCore.SIGNAL("ensembleChanged()"), self.onEnsembleChanged)
         self.disconnect(self.mEnsemble, QtCore.SIGNAL("nodeChanged(QString)"), self.onNodeChanged)

      # Set the new ensemble configuration.
      self.mEnsemble = ensemble

      # Connect the new ensemble.
      self.connect(self.mEnsemble, QtCore.SIGNAL("ensembleChanged()"), self.onEnsembleChanged)
      self.connect(self.mEnsemble, QtCore.SIGNAL("nodeChanged(QString)"), self.onNodeChanged)

      # Create a model for our ListView
      self.mEnsembleModel = EnsembleModel.EnsembleModel(self.mEnsemble)

      # If selection model already exists then disconnect signal
      if not None == self.mClusterListView.selectionModel():
         QtCore.QObject.disconnect(self.mClusterListView.selectionModel(),
            QtCore.SIGNAL("currentChanged(QModelIndex,QModelIndex)"), self.onNodeSelected)

      # Set the model.
      self.mClusterListView.setModel(self.mEnsembleModel)

      # Create a settings model and pass it to the view.
      self.mNodeSettingsModel = NodeSettingsModel()
      self.mSettingsTableView.setModel(self.mNodeSettingsModel)

      # Tell the both columns to split the availible space.
      self.mSettingsTableView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
      self.mSettingsTableView.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)

      # Connect new selection model
      QtCore.QObject.connect(self.mClusterListView.selectionModel(),
         QtCore.SIGNAL("currentChanged(QModelIndex,QModelIndex)"), self.onNodeSelected)

      # Connect node settings model to update view when it changes.
      QtCore.QObject.connect(self.mNodeSettingsModel,
         QtCore.SIGNAL("modelChanged()"), self.onNodeModelChanged)

   def onNodeModelChanged(self):
      """ Slot that is called when the node settings model changes. """
      self.mSettingsTableView.reset()

   def onRefresh(self):
      """ Slot that requests information about all nodes in the Ensemble. """
      if not self.mEnsemble is None:
         self.mEnsemble.refreshConnections()

      env = maestro.core.Environment()
      env.mEventManager.emit("*", "ensemble.get_os", ())
      env.mEventManager.emit("*", "ensemble.get_settings", ())

   def onAdd(self):
      """ Called when user presses the add button. """
      if not None == self.mEnsembleModel:
         self.mEnsembleModel.insertRow(self.mEnsembleModel.rowCount())

   def onRemove(self):
      """ Called when user presses the remove button. """
      row = self.mClusterListView.currentIndex().row()
      if (not None == self.mEnsembleModel) and row >= 0:
         self.mEnsembleModel.removeRow(row)

   def onNodeSettingsChanged(self):
      """ Slot that is called when the user has finished editing a
          field in the node settings.
      """

      # Get the currently selected node.
      selected_node = self.mClusterListView.model().data(self.mClusterListView.currentIndex(), QtCore.Qt.UserRole)

      # Can't get a change if a node is not selected
      assert not None == selected_node

      modified = False
      # Process changes
      if self.mNameEdit.isModified():
         selected_node.setName(str(self.mNameEdit.text()))
         self.mNameEdit.setModified(False)
         modified = True

      if self.mHostnameEdit.isModified():
         # Disconnect and try to connect to new hostname later..
         try:
            ip_address = selected_node.getIpAddress()
            env = maestro.core.Environment()
            env.mEventManager.disconnectFromNode(ip_address)
         except:
            # Do nothing
            pass

         # Set the new hostname.
         selected_node.setHostname(str(self.mHostnameEdit.text()))
         self.mHostnameEdit.setModified(False)
         modified = True

         # Try to connect to new hostname.
         self.mEnsemble.refreshConnections()

      # Only update gui if something really changed.
      if modified:
         self.refreshNodeSettings()
         # Force the cluster model to generate a dataChanged signal.
         self.mClusterListView.model().setData(self.mClusterListView.currentIndex(), QtCore.QVariant(), QtCore.Qt.DisplayRole)
   
   def onNodeSelected(self, selected, deselected):
      """ Slot that is called when a cluster node is selected. """
      # Get the currently selected node and save it.
      selected_node = self.mClusterListView.model().data(self.mClusterListView.currentIndex(), QtCore.Qt.UserRole)
      self.mSelectedNode = selected_node
      # Refresh all node information.
      self.refreshNodeSettings()
      # Refresh the settings model.
      self.mNodeSettingsModel.setNode(selected_node)

   def refreshNodeSettings(self):
      """
      Fills in the node information for the currently selected node. This gets called
      whenever a new node is selected in the list.
      """

      # Clear all information
      self.mNameEdit.clear()
      self.mHostnameEdit.clear()
      self.mCurrentOsEdit.clear()
      self.mIpAddressEdit.clear()

      # Early out if there is no node selected.
      if self.mSelectedNode is not None:      
         # Set node information that we know
         self.mNameEdit.setText(self.mSelectedNode.getName())
         self.mHostnameEdit.setText(self.mSelectedNode.getHostname())

         # Get IP address
         try:
            self.mIpAddressEdit.setText(self.mSelectedNode.getIpAddress())
         except:
            self.mIpAddressEdit.setText('Unknown')

         # Get the name of the current platform.
         self.mCurrentOsEdit.setText(self.mSelectedNode.getPlatformName())
         
   def onNodeChanged(self, nodeId):
      """ Slot that is called when a node's state changes. If the currently
          selected node changes, we need to update the target list and the
          current default target.

          @param nodeId: The id of the node that changed.
      """
      if self.mSelectedNode is not None and nodeId == self.mSelectedNode.getId():
         self.mClusterListView.model().setData(self.mClusterListView.currentIndex(), QtCore.QVariant(), QtCore.Qt.DisplayRole)

   def onEnsembleChanged(self):
      """ Called when the cluster control has connected to another node. """
      self.mClusterListView.reset()
      # Refresh the information about the node.
      self.refreshNodeSettings()