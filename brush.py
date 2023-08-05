# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Brush
                                 A QGIS plugin
 This plugin provides a tool for drawing polygons like with a brush in photoshop and GIMP
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-02-18
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Joseph Burkhart
        email                : josephburkhart.public@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import QGIS Qt libraries
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon, QColor, QPixmap, QCursor, QGuiApplication
from qgis.PyQt.QtWidgets import QAction

# Import necessary QGIS classes
from qgis.core import QgsFeature, QgsProject, QgsGeometry, QgsVectorLayer,\
    QgsRenderContext, QgsLayerTreeGroup, QgsWkbTypes, QgsMapLayer

# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
from .brush_dockwidget import BrushDockWidget
import os.path

# Import the brush tool code
from .brushtools import BrushTool

class Brush:
    """QGIS Plugin Implementation."""

    #------------------------------- INITIATION -------------------------------
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # Save reference to the QGIS status bar
        self.iface.statusBarIface()

        # Save additional references
        self.tool = None
        self.tool_name = None
        self.prev_tool = None
        self.active_layer = None

        self.layer_color = QColor(60, 151, 255, 127)

        self.sb = self.iface.statusBarIface()

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Brush_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Draw by Brush')
        self.toolbar = self.iface.addToolBar(u'Brush')
        self.toolbar.setObjectName(u'Brush')

        self.pluginIsActive = False
        self.dockwidget = None

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/brush/resources/paintbrush.png'
        self.brush_action = self.add_action(
            icon_path,
            text=self.tr(u'Brush Tool'),
            checkable=True,
            callback=self.activate_brush_tool,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        # Get necessary info whenever active layer changes -- TODO: move to init??
        self.iface.currentLayerChanged.connect(self.get_active_layer)

        # Save reference to prev map tool whenever brush action is toggled on
        self.brush_action.toggled.connect(lambda x: self.set_prev_tool(self.brush_action))

        # Only enable brush action if a Polygon or MultiPolygon Vector layer
        # is selected
        self.iface.currentLayerChanged.connect(self.enable_brush_action_check)

    #------------------------------ COMMUNICATION -----------------------------
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('Brush', message)

    def updateSB(self):
        """Update the status bar"""
        pass #TODO: placeholder

    def resetSB(self):
        """Reset the status bar"""
        message = {
            'draw_brush': 'Maintain the left click to draw with a brush.'
        }
        self.sb.showMessage(self.tr(message[self.tool_name]))

    def set_prev_tool(self, action):
        """Reset prev_tool to the current active map tool. To be called
        whenever the action is toggled."""
        if action.isChecked():
            self.prev_tool = self.iface.mapCanvas().mapTool()

    #------------------------------- ACTIVATION -------------------------------
    def activate_brush_tool(self):
        """Activate and run the brush tool"""
        # Load and start the plugin
        if not self.pluginIsActive:
            self.pluginIsActive = True

        # Reset the tool if another one is active -- TODO: this is not useful
        if self.tool:
            self.tool.reset()

        # Initialize and configure self.tool
        self.tool=BrushTool(self.iface)
        self.tool.setAction(self.actions[0])
        self.tool.rbFinished.connect(lambda g: self.draw(g))
        self.tool.move.connect(self.updateSB)
        
        # Select the tool in the current interface
        self.iface.mapCanvas().setMapTool(self.tool)
        
        # Set tool name -- TODO: this is not useful
        self.tool_name = 'draw_brush'

        # Update tool attribute
        self.tool.active_layer = self.active_layer

        # Reset the status bar
        self.resetSB()

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Draw by Brush'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    #------------------------------ UPPDATE STATE -----------------------------
    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        checkable=False,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        menu=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def disable_action(self, action):
        """Procedure for disabling actions"""
        # Toggle off
        action.setChecked(False)  #uncheck

        # Disable the tool
        action.setEnabled(False)  #disable

        # Restore previous map tool (if any)
        # TODO: account for selected layer type
        if self.prev_tool != None:
            self.iface.mapCanvas().setMapTool(self.prev_tool)

    def enable_brush_action_check(self):
        """Enable/Disable brush action as necessary when different types of
        layers are selected. Tool can only be activated when editing is on."""

        # No layer is selected
        if self.active_layer == None:
            self.disable_action(self.brush_action)

        # Polygon Layer is selected
        elif ((self.active_layer.type() == QgsMapLayer.VectorLayer) and
            (self.active_layer.geometryType() == QgsWkbTypes.PolygonGeometry) and
            self.active_layer.isEditable()):
                self.brush_action.setEnabled(True)
        
        # Non-polygon layer is selected
        else:
            self.disable_action(self.brush_action)

    def draw(self, g):
        """This is the actual drawing state"""
        # Get current active layer used in the drawing tool
        self.active_layer = self.tool.active_layer

        # Create new feature
        new_feature = QgsFeature()
        new_feature.setGeometry(g)

        # If drawing, add new feature
        if self.tool.drawing_mode == 'drawing_with_brush':
            # If merging, recalculate the geometry of new_feature and delete
            # all overlapping features
            # TODO: if attributes are present, prompt user to select which
            #       overlapping feature to take attribute data from
            if self.tool.merging:
                overlapping_features = self.features_overlapping_with(new_feature)    
                for f in overlapping_features['any_overlap']:
                    new_feature.setGeometry(new_feature.geometry().combine(f.geometry()))
                    self.active_layer.deleteFeature(f.id())
            
            # Add new feature and commit changes
            self.active_layer.dataProvider().addFeatures([new_feature])
            self.active_layer.commitChanges(stopEditing=False)

        # If erasing, modify existing features
        elif self.tool.drawing_mode == 'erasing_with_brush':
            # Calculate overlapping features
            overlapping_features = self.features_overlapping_with(new_feature)
            
            # Cut a hole through all features that new_feature is contained by
            contained_by_features = overlapping_features['contained_by']
            for f in contained_by_features:
                # Get current and previous geometries
                current_geometry = new_feature.geometry()
                current_geometry.convertToMultiType() #sometimes there is only one part
                current_polygon = current_geometry.asMultiPolygon()[0]  #TODO: I don't know why it's multipolygon instead of polygon...
                current_exterior = current_polygon[0]
                current_holes = current_polygon[1:] 
                
                previous_geometry = f.geometry()
                previous_geometry.convertToMultiType() #sometimes previous feature is not multitype
                previous_polygon = previous_geometry.asMultiPolygon()[0]
                previous_exterior = previous_polygon[0]
                previous_holes = previous_polygon[1:]

                # Calculate new holes
                previous_holes_geometry = QgsGeometry().fromMultiPolygonXY([previous_holes])
                new_holes_geometry = QgsGeometry().fromMultiPolygonXY([[current_exterior]])
                new_holes_geometry.combine(previous_holes_geometry)
                new_holes = new_holes_geometry.asMultiPolygon()

                # Calculate new island parts, if any
                if current_holes != []:
                    print(current_holes)
                    current_holes_geometry = QgsGeometry().fromMultiPolygonXY([current_holes])
                    new_parts_geometry = current_holes_geometry.intersection(previous_geometry)
                    new_parts_geometry.convertToMultiType()  #sometimes there is only one part
                    new_parts = new_parts_geometry.asMultiPolygon()

                # Add calculated holes and parts
                new_geometry = QgsGeometry(previous_geometry)   # copy the previous geometry
                for hole in new_holes:
                    new_geometry.addRing(hole[0])
                if current_holes != []:
                    for part in new_parts_geometry.constParts():
                        #TODO: something in the two lines below was causing an immediate crash. Crashes eventually stopped unexpectedly when I restarted QGIS
                        #print(part)
                        new_geometry.addPart(part.boundary()) # I don't understand why part is a QgsPolygon, but it is
                
                # Change feature geometry to what was calculated above
                f.setGeometry(new_geometry)
                self.active_layer.updateFeature(f)

            # Delete all features that new_feature contains
            contains_features = overlapping_features['contains']
            for f in contains_features:
                self.active_layer.deleteFeature(f.id())

            # For all other features, modify their geometry
            # TODO: revise variable names to match pattern in brushtools.py
            for f in overlapping_features['partial_overlap']:
                old_geom = f.geometry()
                new_geom = old_geom.difference(new_feature.geometry())
                f.setGeometry(new_geom)
                self.active_layer.updateFeature(f)

            self.active_layer.commitChanges(stopEditing=False)

        # Delete the instance of new_feature to free up memory
        # TODO: delete other expensive variables as well
        del new_feature

        # Refresh the interface
        self.iface.layerTreeView().refreshLayerSymbology(self.active_layer.id())
        self.iface.mapCanvas().refresh()

        # Clean up at the end
        self.tool.reset()
        self.resetSB()

    #------------------------------- CALCULATION ------------------------------
    def features_overlapping_with(self, feature):
        """Returns a dict of features in self.active_layer that overlap with
        a given `feature`. Both `feature` and self.active_layer must be in
        the same CRS.
        
        The returned dict is of the following form:
            {
                'contains':        `feature` contains these features
                'contained_by':    `feature` is contained by these features
                'partial_overlap': `feature` only partially overlaps these features
                'any_overlap':     `feature` has partial or total overlap with these
                                   features
            }

        If the two features have equivalent geometries, f is added to "contained_by"

        Note: if this method causes performance issues, QgsGeometryEngine
        may provide a more efficient approach.
        """
        overlapping_features = {
            'contains': [],
            'contained_by': [],
            'partial_overlap': [],
            'any_overlap': []
        }
        for f in self.active_layer.getFeatures():
            if feature.geometry().contains(f.geometry()):
                overlapping_features['contains'].append(f)
                overlapping_features['any_overlap'].append(f)
            
            elif (feature.geometry().within(f.geometry()) or
                  QgsGeometry.compare(feature.geometry(), f.geometry())):
                overlapping_features['contained_by'].append(f)
                overlapping_features['any_overlap'].append(f)            
            
            elif feature.geometry().overlaps(f.geometry()):
                overlapping_features['partial_overlap'].append(f)
                overlapping_features['any_overlap'].append(f)
        
        return overlapping_features

    def get_active_layer(self):
        """Reset the reference to the current active layer and reconnect 
        signals to slots as necessary. To be called whenever the active layer changes."""
        self.active_layer = self.iface.activeLayer()
        if ((self.active_layer != None) and
            (self.active_layer.type() == QgsMapLayer.VectorLayer)):
            self.active_layer.editingStarted.connect(self.enable_brush_action_check)
            self.active_layer.editingStopped.connect(self.enable_brush_action_check)
