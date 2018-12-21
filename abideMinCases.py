# -*- coding: utf-8 -*-

import processing
from PyQt5.QtCore import (QCoreApplication)
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFileDestination,
                       QgsMessageLog,
                       QgsVectorFileWriter,
                       QgsProcessingParameterString,
                       QgsProcessingFeatureSourceDefinition,
                       QgsProcessingUtils,
                       QgsVectorLayer,
                       QgsProject)
from qgis.gui import QgsMapCanvas
import os


class abideMinCases(QgsProcessingAlgorithm):
    
    """
    This script selects features with attribute values lesser than a user provided threshold and tries to average these values with adjacent features above this threshold
    """

    inputTab = 'inputTab'
    colApply = 'colApply'
    thresh = 'thresh'
    maxIter = 'maxIter'
    OUTPUT = 'output'
    

    def initAlgorithm(self, config = None):
        
        # define input parameters
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.inputTab,
                self.tr('Eingabedatensatz'),
                [QgsProcessing.TypeFile]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.colApply,
                self.tr('Spalten auf die, die Mindestfallzahl angewendet werden soll'),
                None,
                self.inputTab,
                -1,
                True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterString(
                self.thresh,
                self.tr('Mindestfallzahl')
            )
        )
        
        self.addParameter(
            QgsProcessingParameterString(
                self.maxIter,
                self.tr('Maximalanzahl der Iterationen')
            )
        )
        
       
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Ausgabedatensatz'),
                fileFilter = '*.gpkg'
            )
        )
        
        
    def processAlgorithm(self, parameters, context, feedback):
        
        # get inputs
        inputTab = self.parameterAsVectorLayer(parameters, self.inputTab, context)
        colApply = self.parameterAsFields(parameters, self.colApply, context)
        thresh = self.parameterAsString(parameters, self.thresh, context)
        maxIter = self.parameterAsString(parameters, self.maxIter, context)
        outPath = self.parameterAsString(parameters, self.OUTPUT, context)
        
        
        
        
        # create output layer from input data
        outTab = QgsVectorLayer('Polygon', 'outTab', 'memory')
        CRS = inputTab.crs()
        outTab.setCrs(CRS)
        outTab.dataProvider().addAttributes(inputTab.dataProvider().fields().toList())
        outTab.updateFields()
        feats = [feat for feat in inputTab.getFeatures()]
        outTab.dataProvider().addFeatures(feats)
        outTab.updateExtents()
        

        # redefine data types
        thresh = float(thresh)
        maxIter = int(maxIter)
        
        # generate temp folder
        QgsMessageLog.logMessage('Creating temporary output directory...', 'User notification', 0)
        tempDir = QgsProcessingUtils.tempFolder()
        if not os.path.exists(tempDir):
            os.makedirs(tempDir)
        
            
        
        # get field indices of interest
        QgsMessageLog.logMessage('Getting field names and indeces...', 'User notification', 0)
        fieldIdx = []
        fieldNames = outTab.fields().names()
        for f in list(range(0, len(fieldNames))):
            if fieldNames[f] in colApply:
                fieldIdx.append(fieldNames.index(fieldNames[f]))       
        
          
        
        def abideMinCases_func():
        
            # create container for information about processed features
            allProc = []
            
            # iterate over each feature
            feats = outTab.getFeatures()
            feat_iter_count = 0
            n_feats = outTab.featureCount()
            for feat in feats:
                
                feat_iter_count += 1
                QgsMessageLog.logMessage('Processing feature...(' + str(feat_iter_count) + '/' + str(n_feats) + ')', 'User notification', 0)
                
                # get attributes
                atts = feat.attributes()
                
                # iterate over fields of interest
                for a in list(range(0, len(atts))):
                    
                    QgsMessageLog.logMessage('Processing field...(' + str(a+1) + '/' + str(len(atts)) + ')', 'User notification', 0)
                    
                    # get active if current field is within the fields of interest
                    if a in fieldIdx:
                        
    
                        # extract value in question and area size for the respective features
                        to_val = atts[a]
                        
                        # get active if attribute value is lower than defined threshold
                        if atts[a] < thresh:
                            
                            # select current feature and create new layer
                            outTab.selectByIds([feat.id()])
                            temp_fileName = tempDir + '/temp_selected_' + str(feat_iter_count) + '_' + str(a) + '.gpkg'
                            QgsVectorFileWriter.writeAsVectorFormat(outTab, temp_fileName, 'ANSI', outTab.crs(), 'GPKG', 1)
            
                            
                            
                            # get adjacent features
                            params = {'INPUT' : outTab,
                                      'INTERSECT' : QgsProcessingFeatureSourceDefinition(temp_fileName, False),
                                      'METHOD' : 0,
                                      'PREDICATE' : [4] }
                            adjSel = processing.run('native:selectbylocation', params)['OUTPUT']
                            adj_feats = adjSel.selectedFeatures()
                            adjSel.removeSelection()
                            
                            
                            # get attribute values of adjacent features
                            adjIdx = []
                            adjAtts = []
                            for adj_feat in adj_feats:
                                adjIdx.append(adj_feat.id())
                                adjAtts.append(adj_feat[a])
                            
                            QgsMessageLog.logMessage('Feature comparison with ' + str(len(adjIdx)) + ' adjacent features...', 'User notification', 0)
                            
                            
                            # sort adjacent features by attribute values
                            adjIdx = [x for _, x in sorted(zip(adjAtts, adjIdx))]
                            adjAtts = sorted(adjAtts)
                                                        
                            
                            # iterate over each appropriate adjacent feature pair as long as the threshold is not reached
                            new_val = to_val
                            for p in list(range(0, len(adjIdx))):
                                 
                                 
                                # collect information about current feature pair
                                pair1 = str(feat.id()) + '_' + str(adjIdx[p])
                                pair2 = str(adjIdx[p]) + '_' + str(feat.id())
                                 
                                 
                                # get active if this feature pair has not been processed before
                                if (pair1 not in allProc) and (pair2 not in allProc) and (new_val < thresh):
                                       
                                    # get values of adjacent polygon 
                                    outTab.selectByIds([adjIdx[p]])
                                    comp_val = outTab.selectedFeatures()[0].attributes()[a]
                                    outTab.removeSelection()
       
                                    # calculate new value as mean
                                    new_val = (to_val + comp_val) / 2
                                        
                                                                        
                                    # update attribute values in respective features
                                    outTab.startEditing()
                                    outTab.changeAttributeValue(adjIdx[p], a, new_val)
                                    outTab.changeAttributeValue(feat.id(), a, new_val)
                                    outTab.commitChanges()
                                    
                                         
                                     
                                    # collect information about this processed feature pair
                                    allProc.append(pair1)
                                    
                                    # update value in question
                                    to_val = new_val
                                                                
                                
            return outTab
                
        # execute function
        for l in list(range(0, maxIter)):
            QgsMessageLog.logMessage('Start iterative processing...(' + str(l+1) + '/' + str(maxIter) + ')', 'User notification', 0)
            outTab = abideMinCases_func()
        
        # write to file
        QgsMessageLog.logMessage('Writing results to file...', 'User notification', 0)
        QgsVectorFileWriter.writeAsVectorFormat(outTab, outPath, 'ANSI', CRS, 'GPKG')
        
        
        # add the new layer to canvas
        QgsProject.instance().addMapLayer(outTab)
        QgsMapCanvas().setExtent(outTab.extent())
        QgsMapCanvas().setLayers([outTab])
        
        return {self.OUTPUT: outTab}
    

    def name(self):
        return 'abideMinCases'

    def displayName(self):
        return self.tr('Mindestfallzahlen einhalten')

    def group(self):
        return self.tr('Raumanalaysen - Christian Mueller')

    def groupId(self):
        return 'Raumanalysen'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return abideMinCases()