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
                       QgsProject,
                       QgsProcessingParameterString)
from qgis.utils import iface
import pandas as pd
import numpy as np


class binEncoder(QgsProcessingAlgorithm):
    
    """
    This script performs a bin encoding on a given spreadsheet
    """

    inputTab = 'inputTab'
    colEnc = 'colEnc'
    lw_bound = 'lw_bound'
    up_bound = 'up_bound'
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
                self.colEnc,
                self.tr('Columns to be one hot encoded'),
                None,
                self.inputTab,
                -1
            )
        )
        
        self.addParameter(
            QgsProcessingParameterString(
                self.lw_bound,
                self.tr('Lower bounds of bins (comma seperated)')
            )
        )
        
        self.addParameter(
            QgsProcessingParameterString(
                self.up_bound,
                self.tr('Upper bounds of bins (comma seperated)')
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
        colEnc = self.parameterAsFields(parameters, self.colEnc, context)
        lw_bound = self.parameterAsString(parameters, self.lw_bound, context)
        up_bound = self.parameterAsString(parameters, self.up_bound, context)
        outTab = self.parameterAsString(parameters, self.OUTPUT, context)
        

                  
        # convert bound strings to lists
        lw_bound = lw_bound.split(',')
        up_bound = up_bound.split(',')
                  
        # import qgis attribute table as pandas data frame
        def qgsTabToDataFrame(inputTab):
#             QgsMessageLog.logMessage('Converting QGIS table to pandas data frame.', level = Qgis.Info, notifyUser = True)
            allAtts = inputTab.dataProvider().fields().names()
            atts = pd.DataFrame([], columns = allAtts)
            i = 0
            for feature in inputTab.getFeatures():
                atts.loc[i] = feature.attributes()
                i += 1
            return atts
         
        atts = qgsTabToDataFrame(inputTab)
             
        import pydevd;pydevd.settrace() 
        
        # perform bin encoding
        def binEncoding(inDataFrame = atts, col = colEnc,
                           lw_bound = lw_bound, up_bound = up_bound):
         
            # iterate over each bin
            for b in list(range(0, len(lw_bound))):
                 
#                 QgsMessageLog.logMessage('Encoding bin...' + str(b) + '/' + str(len(lw_bound)) + ')', level = Qgis.Info, notifyUser = True)
                
                # create new bin column
                binName = 'bin_' + lw_bound[b] + '_' + up_bound[b]
                inDataFrame[binName] = 0
                
                # set 1s for rows which fall within this bin
                cond = ((inDataFrame[col] >= float(lw_bound[b])) &
                        (inDataFrame[col] < float(up_bound[b])))
#                 cond = inDataFrame[col] == "01.01.1985"
                inDataFrame[binName].iloc[np.where(cond[col] == True)[0]] = 1
                
            return inDataFrame
        
        
        
        outDat = binEncoding()
                 
         
        # write encoded table to file
#         QgsMessageLog.logMessage('Writing encoded data set to file.', , level = Qgis.Info, notifyUser = True)
        outDat.to_csv(outTab, index = False, encoding = 'ANSI')
        
        
            
        return {self.OUTPUT: inputTab}

    def name(self):
        return 'binEncoder'

    def displayName(self):
        return self.tr('binEncoder')

    def group(self):
        return self.tr('Raumanalaysen - Christian Mueller')

    def groupId(self):
        return 'Raumanalysen'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return binEncoder()

        
  