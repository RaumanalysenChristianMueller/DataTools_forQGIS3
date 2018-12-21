# -*- coding: utf-8 -*-

import processing
from PyQt5.QtCore import (QCoreApplication,
                          QVariant)
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFileDestination,
                       QgsMessageLog,
                       QgsField,
                       QgsExpression,
                       QgsGeometry,
                       QgsPointXY,
                       QgsFeature,
                       QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsProject)
from qgis.utils import iface
import pandas as pd


class oneHotEncoder(QgsProcessingAlgorithm):
    
    """
    This script performs a one hot encoding on a given spreadsheet
    """

    inputTab = 'inputTab'
    colsEnc = 'colsEnc'
    OUTPUT = 'output'
    

    def initAlgorithm(self, config = None):
        
        # define input parameters
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.inputTab,
                self.tr('Input table'),
                [QgsProcessing.TypeFile]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.colsEnc,
                self.tr('Columns to be one hot encoded'),
                None,
                self.inputTab,
                -1,
                True
            )
        )
        
       
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Output table'),
                fileFilter = 'csv'
            )
        )
        
        
    def processAlgorithm(self, parameters, context, feedback):
        
        # get inputs
        inputTab = self.parameterAsVectorLayer(parameters, self.inputTab, context)
        colsEnc = self.parameterAsFields(parameters, self.colsEnc, context)
        outTab = self.parameterAsString(parameters, self.OUTPUT, context)
        
        
                  
        # import qgis attribute table as pandas data frame
        def qgsTabToDataFrame(inputTab):
            allAtts = inputTab.dataProvider().fields().names()
            atts = pd.DataFrame([], columns = allAtts)
            i = 0
            for feature in inputTab.getFeatures():
                atts.loc[i] = feature.attributes()
                i += 1
            return atts
        
        atts = qgsTabToDataFrame(inputTab)
            
        
        # perform one hot encoding
        def oneHotEncoding(inDataFrame, cols):
        
            # iterate over each column to be one hot encoded
            for c in cols:
                
                # get column as series
                dat = inDataFrame[c]
                
                # get unique values
                unis = dat.unique()
                
                # iterate over each unique value
                for u in unis:
                    
                    # create new series for this unique value and hot code this series
                    inDataFrame[u] = 0
                    cond = inDataFrame[c] == u
                    inDataFrame.loc[cond, u] = 1
                    
            return inDataFrame
        
        outDat = oneHotEncoding(atts, colsEnc)
                
        
        # write encoded table to file
        outDat.to_csv(outTab, index = False, encoding = 'ANSI')
        
        
            

        return {self.OUTPUT: inputTab}

    def name(self):
        return 'oneHotEncoder'

    def displayName(self):
        return self.tr('oneHotEncoder')

    def group(self):
        return self.tr('Raumanalaysen - Christian Mueller')

    def groupId(self):
        return 'Raumanalysen'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return oneHotEncoder()

        
  