#-----------------------------------------------------------
#
# QGIS Combo Manager is a python module to easily manage a combo
# box with a layer list and eventually relate it with one or
# several combos with list of corresponding fields.
#
# Copyright    : (C) 2013 Denis Rouzaud
# Email        : denis.rouzaud@gmail.com
#
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from PyQt4.QtCore import Qt
from qgis.core import QGis, QgsMapLayerRegistry, QgsMapLayer

from optiondictionary import OptionDictionary

AvailableOptions = {"groupLayers": (False, True),
                    "hasGeometry": (None, False, True),
                    "geomType": (None, QGis.Point, QGis.Line, QGis.Polygon),
                    "dataProvider": None,
                    "finishInit": (True, False),
                    "legendInterface": None,
                    "skipLayers": list}


class LayerCombo():
    def __init__(self, widget, initLayer="", options={}, layerType=None):
        self.widget = widget
        self.options = OptionDictionary(AvailableOptions, options)
        if hasattr(initLayer, '__call__'):
            self.initLayer = initLayer()
        else:
            self.initLayer = initLayer
        self.layerType = layerType

        # finish init (set to false if LayerCombo must be returned before items are completed)
        if self.options["finishInit"]:
            self.finishInit()

    def finishInit(self):
        # connect signal for layers and populate combobox
        QgsMapLayerRegistry.instance().layersAdded.connect(self.__canvasLayersChanged)
        if self.options["groupLayers"]:
            self.options["legendInterface"].groupRelationsChanged.connect(self.__canvasLayersChanged)
        self.__canvasLayersChanged()

    def getLayer(self):
        i = self.widget.currentIndex()
        if i == 0:
            return None
        layerId = self.widget.itemData(i)
        return QgsMapLayerRegistry.instance().mapLayer(layerId)
		
    def setLayer(self, layer):
        if layer is None:
            idx = -1
        else:
            idx = self.widget.findData(layer.id(), Qt.UserRole)
        self.widget.setCurrentIndex(idx)

    def __canvasLayersChanged(self, layerList=[]):
        self.widget.clear()
        self.widget.addItem("")
        if not self.options["groupLayers"]:
            for layerId, layer in QgsMapLayerRegistry.instance().mapLayers().iteritems():
                if not self.__checkLayer(layer):
                    continue
                self.widget.addItem(layer.name(), layerId)
                if layerId == self.initLayer:
                    self.widget.setCurrentIndex(self.widget.count()-1)
        else:
            if self.options["legendInterface"] is None:
                raise NameError("Cannot display layers grouped if legendInterface is not given in the options.")
            for layerGroup in self.options["legendInterface"].groupLayerRelationship():
                groupName = layerGroup[0]
                foundParent = False
                insertPosition = self.widget.count()
                indent = 0
                for i in range(self.widget.count()):
                    lineData = self.widget.itemData(i) or []
                    if len(lineData) > 0 and lineData[0] == groupName:
                        foundParent = True
                        insertPosition = i+1
                        lineData[0] = "groupTaken"
                        self.widget.setItemData(i, lineData)
                        indent = lineData[1] + 1
                        break
                if not foundParent and groupName != "":
                    self.__addLayerToCombo(groupName, insertPosition)
                    insertPosition += 1
                    indent += 1
                for layerid in layerGroup[1]:
                    if self.__addLayerToCombo(layerid, insertPosition, indent):
                        insertPosition += 1

    def __addLayerToCombo(self, layerid, position, indent=0):
        layer = QgsMapLayerRegistry.instance().mapLayer(layerid)
        preStr = "  "*2*indent
        if layer is None:  # this is a group
            # save in userdata a list ["group",indent]
            self.widget.insertItem(position, preStr+layerid, [layerid, indent])
            j = self.widget.model().index(position, 0)
            self.widget.model().setData(j, 0, Qt.UserRole - 1)
        else:
            if not self.__checkLayer(layer):
                return False
            self.widget.insertItem(position, preStr+layer.name(), layer.id())
            if layer.id() == self.initLayer:
                self.widget.setCurrentIndex(self.widget.count() - 1)
        return True

    def __checkLayer(self, layer):
        # skip layer
        for skip in self.options["skipLayers"]:
            if hasattr(skip, '__call__'):
                if layer.id() == skip():
                    return False
            else:
                if layer.id() == skip:
                    return False
        # data provider
        if self.options["dataProvider"] is not None and layer.dataProvider().name() != self.options["dataProvider"]:
            return False
        # vector layer
        if self.layerType == QgsMapLayer.VectorLayer:
            if layer.type() != QgsMapLayer.VectorLayer:
                return False
            # if wanted, filter on hasGeometry
            if self.options["hasGeometry"] is not None and layer.hasGeometryType() != self.options["hasGeometry"]:
                return False
            # if wanted, filter on the geoetry type
            if self.options["geomType"] is not None and layer.geometryType() != self.options["geomType"]:
                return False
        # raster layer
        if self.layerType == QgsMapLayer.RasterLayer:
            if layer.type() != QgsMapLayer.RasterLayer:
                return False
        return True


class VectorLayerCombo(LayerCombo):
    def __init__(self, widget, initLayer="", options={}):
        LayerCombo.__init__(self, widget, initLayer, options, QgsMapLayer.VectorLayer)


class RasterLayerCombo(LayerCombo):
    def __init__(self, widget, initLayer="", options={}):
        LayerCombo.__init__(self, widget, initLayer, options, QgsMapLayer.RasterLayer)
