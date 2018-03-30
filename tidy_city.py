# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TidyCity
                                 A QGIS plugin
 A simple QGIS python plugin for building tidy cities.
                              -------------------
        begin                : 2016-11-30
        git sha              : $Format:%H$
        copyright            : (C) 2016 by IGN
        email                : julien.perret@gmail.com
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
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant, Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QTransform
from PyQt5.QtWidgets import QAction, QProgressBar, QCheckBox, QFrame, QVBoxLayout
from .indicatorCalculation import *
from .classification import *
from .resources import *
# Initialize Qt resources from file resources.py
#import resources
# Import the code for the dialog
from .tidy_city_dialog import TidyCityDialog
import os.path
import math
from qgis.core import *
from qgis.gui import *

from random import randrange

class TidyCity:
    """QGIS Plugin Implementation."""

    """
    Initialisation du plugin.
    """

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        print("Initialisation")
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'TidyCity_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&TidyCity')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'TidyCity')
        self.toolbar.setObjectName(u'TidyCity')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('TidyCity', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
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

        # Create the dialog (after translation) and keep reference
        self.dlg = TidyCityDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/TidyCity/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Build a tidy city'),
            callback=self.run,
            parent=self.iface.mainWindow())
        #Button to process calculation
        self.dlg.pushButtonCalculation.clicked.connect(self.processCalculation)
        self.dlg.pushButtonClassification.clicked.connect(self.processClassification)        
        
        self.dlg.inputPolygonLayer.activated.connect(self.updatePolygonLayer)
        self.dlg.inputPolygonLayerClass.activated.connect(self.updatePolygonLayerClass)
        scrollArea = self.dlg.scrollArea;
        scrollArea.setWidgetResizable(True)
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        inner = QFrame(scrollArea)
        inner.setLayout(QVBoxLayout())
        scrollArea.setWidget(inner)
        self.updateDropBoxes()
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&TidyCity'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    #def select_output_file(self):
        #filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.shp')
        #self.dlg.fileLineEdit.setText(filename)

    #def toggle_save(self):
        #self.save = self.dlg.saveCheckBox.isChecked()
        #self.dlg.fileLineEdit.setEnabled(self.save)
        #self.dlg.fileButton.setEnabled(self.save)
    """
    Fonction run.
    """

    def run(self):
        """Run method that performs all the real work"""

        # show the dialog
        self.dlg.show()
        
        # Run the dialog event loop
        result = self.dlg.exec_()


        return 
        # Calcul de y_new (selon la taille) :
            
        level = 0
        prec_highest_feature = 0
        # Parcours de tous les groupes
        for i in range(1,39):
            highest_feature = 0
            # Parcours des îlots
            for h in vl.dataProvider().getFeatures():
                SMBR_height = h.attributes()[5]
                # L'entité est-elle membre du groupe en cours ?
                if h.attributes()[15] == i:
                    # On récupère la plus haute entité du groupe
                    if SMBR_height > highest_feature:
                        highest_feature = SMBR_height
            
            # On peut ainsi connaître l'espace à laisser en hauteur entre les 2 groupes successifs
            level += highest_feature/1.5 + prec_highest_feature/1.5
            prec_highest_feature = highest_feature
            
            for h in vl.dataProvider().getFeatures():
                if h.attributes()[15] == i:
                    # Attribution du y correspondant
                    vl.changeAttributeValue(h.id(), 14, level)
                                                
        vl.commitChanges()
        vl.startEditing()
        
        # Calcul de x_new :
        

        
        # Rangement suivant la taille des îlots 
        for i in range(1, 39):
            liste = []
            level = 0
            prec_width = 0
            width = 0
            height = 0
            for j in vl.dataProvider().getFeatures():
                if j.attributes()[15] == i:
                    liste += [j.attributes()[5]]
            liste.sort()
            k = 0
            while k in range(1000):
                for j in vl.dataProvider().getFeatures():
                    if j.attributes()[15] == i and liste != []:
                        if j.attributes()[5] == liste[-1]:
                            liste.pop()
                            width = j.attributes()[4]
                            height = j.attributes()[5]
                            level += width + prec_width + height
                            vl.changeAttributeValue(j.id(), 13, level)
                            prec_width = width
                k += 1
                                            
        vl.commitChanges()
        vl.startEditing()
        
        #On range la ville !
        for g in vl.dataProvider().getFeatures():
            geom = g.geometry()
            
            # On récupère les anciennes et nouvelles coordonnées.
            x_init = g.attributes()[11]
            y_init = g.attributes()[12]
            x_new = g.attributes()[13]
            y_new = g.attributes()[14]
                            
            # Calcul des paramètres du déplacement.
            dx = x_new - x_init
            dy = y_new - y_init
            centre_rota = QgsPointXY(x_new,y_new)
            if SMBR_angle < 90:
                angle_rota = 90 - SMBR_angle #en degré
            else:
                angle_rota = SMBR_angle - 90
            
            # Translation.
            isTransformOk = geom.translate(dx,dy)
            if (isTransformOk != 0):
                return "error"
            vl.dataProvider().changeGeometryValues({g.id():geom})
            
            # Rotation des îlots
            if SMBR_angle < 90:
                isRotOk = geom.rotate(angle_rota, centre_rota)
                if (isRotOk != 0):
                    return "error"
                vl.dataProvider().changeGeometryValues({g.id():geom})
            else:
                isRotOk = geom.rotate(-angle_rota, centre_rota)
                if (isRotOk != 0):
                    return "error"
                vl.dataProvider().changeGeometryValues({g.id():geom})

        vl.commitChanges()

        self.iface.messageBar().clearWidgets()

	
    
    """
    
    Refresh/updating interface
    
    """    
        #Update the dropboxes that contains the layer list
    def updateDropBoxes(self):
        """Update the  dropdowns with layers"""
        layers = QgsProject.instance().mapLayers().values()

        self.dlg.inputPolygonLayer.clear()
        self.dlg.inputPolygonLayerClass.clear()

        
        for layer in layers:
            self.dlg.inputPolygonLayer.addItem(layer.name(),layer)
            self.dlg.inputPolygonLayerClass.addItem(layer.name(),layer)
        #Refresh the dropbox with attribute list    
        self.refreshAttributeDropBox()
        self.updatePolygonLayerClass()
        
    """
    
    Section 1
    
    """          
        
        
         
    #Refresh the ID attribute list from indicator calculation step
    def refreshAttributeDropBox(self):  
        #Listing layers  
        layers = QgsProject.instance().mapLayers().values()
        self.dlg.intputIDChoice.clear()        
        
        selectedInputLayerIndex = self.dlg.inputPolygonLayer.currentIndex()
        
        if selectedInputLayerIndex > -1 :
            #Getting the selected layer 
            selectedInputLayer = self.dlg.inputPolygonLayer.itemData(selectedInputLayerIndex)
            
            count = selectedInputLayer.featureCount();

            for a in selectedInputLayer.fields():
                    self.dlg.intputIDChoice.addItem(a.displayName(),a)
 

     
    #Action when layer from indicator calculation is refreshed    
    def updatePolygonLayer(self):
         self.refreshAttributeDropBox()
   
        
    """
    
    Section 2
    
    """          
    #Action when layer from classification is refreshed
    def updatePolygonLayerClass(self):
        self.refreshDropDownLayerPanel()
        self.refreshAttributeDropBoxClassif()

        #Refresh the ID attribute list from indicator calculation step
    def refreshAttributeDropBoxClassif(self):  
        #Listing layers  
        layers = QgsProject.instance().mapLayers().values()
        self.dlg.intputIDChoiceClassif.clear()        
        
        selectedInputLayerIndex = self.dlg.inputPolygonLayerClass.currentIndex()
        
        if selectedInputLayerIndex > -1 :
            #Getting the selected layer 
            selectedInputLayer = self.dlg.inputPolygonLayerClass.itemData(selectedInputLayerIndex)
            
            count = selectedInputLayer.featureCount();

            for a in selectedInputLayer.fields():
                    self.dlg.intputIDChoiceClassif.addItem(a.displayName(),a)
                    
    
    
    

                    
    def refreshDropDownLayerPanel(self):
        layout =  self.dlg.scrollArea.widget().layout()
        #Cleaning layout
        
        for i in reversed(range(layout.count())): 
            widgetToRemove = layout.itemAt( i ).widget()
            # remove it from the layout list
            layout.removeWidget( widgetToRemove )
            # remove it from the gui
            widgetToRemove.setParent( None )
        
        layers = QgsProject.instance().mapLayers().values()
        
        selectedInputLayerIndex = self.dlg.inputPolygonLayerClass.currentIndex()
        
        if selectedInputLayerIndex > -1 :
            #Getting the selected layer 
            selectedInputLayer = self.dlg.inputPolygonLayerClass.itemData(selectedInputLayerIndex)
            
            count = selectedInputLayer.featureCount();


            for a in selectedInputLayer.fields():
                if (a.isNumeric()) :
                    checkBox = QCheckBox(a.displayName())
                    layout.addWidget(checkBox)


    def categorizedColor(self, vectorLayer, classAttNam):
        # provide file name index and field's unique values
        fni = vectorLayer.fields().indexFromName(classAttNam)
        unique_values = vectorLayer.uniqueValues(fni)
        
        # fill categories
        categories = []
        for unique_value in unique_values:
            # initialize the default symbol for this geometry type
            symbol =     QgsSymbol.defaultSymbol(vectorLayer.geometryType())
        
            # configure a symbol layer
            layer_style = {}
            layer_style['color'] = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
            layer_style['outline'] = '#000000'
            symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
        
            # replace default symbol layer with the configured one
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)
        
            # create renderer object
            category = QgsRendererCategory(unique_value, symbol, str(unique_value))
            # entry for the list of category items
            categories.append(category)
        
        # create renderer object
        renderer = QgsCategorizedSymbolRenderer(classAttNam, categories)
        
        # assign the created renderer to the layer
        if renderer is not None:
            vectorLayer.setRenderer(renderer)
        
        vectorLayer.triggerRepaint() 


    """
    
    
    Execution interractions
    
    """    
    
    #Processing calculation when ok button from Indicator calculation is pressed
    def processCalculation(self):
        #Getting the polygonlayer
        selectedInputLayerIndex = self.dlg.inputPolygonLayer.currentIndex()
        selectedInputLayer = self.dlg.inputPolygonLayer.itemData(selectedInputLayerIndex)
        QgsMessageLog.logMessage("Layer selected : " + selectedInputLayer.name(), "Tidy City", Qgis.Info)
        layername = self.dlg.LineEditTemporaryLayerName.text()    
        QgsMessageLog.logMessage("Calculating indicator on layer : " + layername, "Tidy City", Qgis.Info)
        intputIDChoiceIndex = self.dlg.intputIDChoice.currentIndex()
        intputIDChoiceValue = self.dlg.intputIDChoice.itemData(intputIDChoiceIndex).displayName()
        QgsMessageLog.logMessage("ID value : " + intputIDChoiceValue, "Tidy City", Qgis.Info)     
        QgsMessageLog.logMessage("Calculating indicator on layer : " + layername, "Tidy City", Qgis.Info)            
        vlOut = calculate(layername, selectedInputLayer,intputIDChoiceValue);
        QgsMessageLog.logMessage("Adding layer to map", "Tidy City", Qgis.Info)
        QgsProject.instance().addMapLayer(vlOut)
        self.updateDropBoxes()
        self.updatePolygonLayerClass()
        self.selectItem(self.dlg.inputPolygonLayerClass,vlOut.name())
        self.selectItem(self.dlg.intputIDChoiceClassif, intputIDChoiceValue)
        self.selectItem(self.dlg.inputPolygonLayer,selectedInputLayer.name())
    
    def processClassification(self):
        selectedInputLayerIndex = self.dlg.inputPolygonLayerClass.currentIndex()
        selectedInputLayer = self.dlg.inputPolygonLayerClass.itemData(selectedInputLayerIndex)
        QgsMessageLog.logMessage("Layer selected : " + selectedInputLayer.name(), "Tidy City", Qgis.Info)
        attributes = self.listingCheckedAttributes()
        QgsMessageLog.logMessage("Attributes selected : " + str(len(attributes)), "Tidy City", Qgis.Info)
         
        strNumberOfClasses = self.dlg.classifNumberOfClasses.text()
        numberOfClasses = int(strNumberOfClasses)
        
        QgsMessageLog.logMessage("Number of classes : " + str(numberOfClasses), "Tidy City", Qgis.Info)
        
        layername = self.dlg.classLayerName.text()    
        QgsMessageLog.logMessage("Calculating indicator on layer : " + layername, "Tidy City", Qgis.Info)
        
        intputIDChoiceIndex = self.dlg.intputIDChoiceClassif.currentIndex()
        intputIDChoiceValue = self.dlg.intputIDChoiceClassif.itemData(intputIDChoiceIndex).displayName()
        QgsMessageLog.logMessage("ID value : " + intputIDChoiceValue, "Tidy City", Qgis.Info)
        
        
        attributeClass = self.dlg.lineEditAttClass.text()
        
        QgsMessageLog.logMessage("Attribute for classification: " + attributeClass, "Tidy City", Qgis.Info)               
        
        layerClassified = kmeans(selectedInputLayer, attributes, numberOfClasses, layername, attributeClass, intputIDChoiceValue)
        QgsMessageLog.logMessage("Adding layer to map", "Tidy City", Qgis.Info)
        QgsProject.instance().addMapLayer(layerClassified)
        self.categorizedColor(layerClassified, attributeClass)

    def selectItem(self, dialog, text):
        for i in range(0,dialog.count()):
            if text in dialog.itemText(i):
                dialog.setCurrentIndex(i)
    
    def listingCheckedAttributes(self):
        attributes = []
        layout =  self.dlg.scrollArea.widget().layout()
        for i in reversed(range(layout.count())):
            if  layout.itemAt(i).widget().isChecked():
                attributes.append(layout.itemAt(i).widget().text())
            #QgsMessageLog.logMessage("--WIDGET---", "Tidy City", Qgis.Info)
            #QgsMessageLog.logMessage(""+str(type(layout.itemAt(i).widget())), "Tidy City", Qgis.Info)
        return attributes


