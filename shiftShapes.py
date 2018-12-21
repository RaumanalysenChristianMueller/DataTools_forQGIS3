# -*- coding: utf-8 -*-

import processing
from PyQt5.QtCore import (QCoreApplication, QVariant)
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFileDestination,
                       QgsMessageLog,
                       QgsVectorFileWriter,
                       QgsExpression,
                       QgsField,
                       QgsProject,
                       QgsExpressionContext,
                       QgsExpressionContextScope)


class shiftShapes(QgsProcessingAlgorithm):
    
    """
    This script aggregates values from one polygon shape to another
    """

    inShape = 'inShape'
    outShape = 'outShape'
    colApply = 'colApply'
    OUTPUT = 'output'
    

    def initAlgorithm(self, config = None):
        
        # define input parameters
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.inShape,
                self.tr('Eingabedatensatz'),
                [QgsProcessing.TypeFile]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.outShape,
                self.tr('Zielflächen'),
                [QgsProcessing.TypeFile]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.colApply,
                self.tr('Spalten, die auf die Zielflächen übertragen werden sollen'),
                None,
                self.inShape,
                -1,
                True
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
        inShape = self.parameterAsVectorLayer(parameters, self.inShape, context)
        outShape = self.parameterAsVectorLayer(parameters, self.outShape, context)
        colApply = self.parameterAsFields(parameters, self.colApply, context)
        outPath = self.parameterAsString(parameters, self.OUTPUT, context)
        

        # get field indices of interest
        QgsMessageLog.logMessage('Getting field names and indices...', 'User notification', 0)
        fieldIdx_names = []
        fieldIdx_temp_names = []
        fieldIdx_temp_names_sum = []
        fieldNames = inShape.fields().names()
        for f in list(range(0, len(fieldNames))):
            if fieldNames[f] in colApply:
                fieldIdx_names.append(fieldNames[f])
                fieldIdx_temp_names.append(fieldNames[f] + '_temp')
                fieldIdx_temp_names_sum.append(fieldNames[f] + '_temp_sum')
               
        
        # calculating area of source polygons
        QgsMessageLog.logMessage('Calculating area of source polygons...', 'User notification', 0)
        parameters = {'FIELD_LENGTH' : 10,
                      'FIELD_NAME' : 'ShaShif_AT',
                      'FIELD_PRECISION' : 10,
                      'FIELD_TYPE' : 1,
                      'FORMULA' : 'value = $geom.area()',
                      'GLOBAL' : '',
                      'INPUT' : outShape,
                      'OUTPUT' : 'memory:'}
        outShape_area = processing.run('qgis:advancedpythonfieldcalculator', parameters)['OUTPUT'] 
        
        
        # perform union of source and target polygons
        QgsMessageLog.logMessage('Performing union of source and target polygons...', 'User notification', 0)
        parameters = {'INPUT' : inShape,
                      'OVERLAY' : outShape_area,
                      'OUTPUT' : 'memory:'}
        unionShape = processing.run('native:union', parameters)['OUTPUT']
        
        
        # calculate union areas
        QgsMessageLog.logMessage('Calculating union areas...', 'User notification', 0)
        parameters = {'FIELD_LENGTH' : 10,
                      'FIELD_NAME' : 'ShaShif_Ai',
                      'FIELD_PRECISION' : 10,
                      'FIELD_TYPE' : 1,
                      'FORMULA' : 'value = $geom.area()',
                      'GLOBAL' : '',
                      'INPUT' : unionShape,
                      'OUTPUT' : 'memory:'}
        unionShape_area = processing.run('qgis:advancedpythonfieldcalculator', parameters)['OUTPUT']
        
        
                
        # define function for simple field calculation
        def calcField(lyr, field_name, expres):
            lyr.dataProvider().addAttributes([ QgsField(field_name, QVariant.Double)])
            expression = QgsExpression(expres)
            context = QgsExpressionContext()
            scope = QgsExpressionContextScope()
            context.appendScope(scope)
            lyr.startEditing()
            for feature in lyr.getFeatures():
                scope.setFeature(feature)
                feature[field_name] = expression.evaluate(context)
                lyr.updateFeature(feature)

            lyr.commitChanges()
        
        # iterate over each field to be processed
        QgsMessageLog.logMessage('Calculating new field values...', 'User notification', 0)
        
        unionShape_calc = unionShape_area
        for v in list(range(0, len(fieldIdx_names))):
        
            expres = '"ShaShif_Ai" / "ShaShif_AT" * "' +  fieldIdx_names[v] + '"'
            calcField(unionShape_calc, fieldIdx_temp_names[v], expres)
        
        
        # add buffer of one centimeter to ensure location by position will detect all appropriate polygons
        parameters = {'INPUT' : outShape,
                      'DISSOLVE' : False,
                      'DISTANCE' : 0.01,
                      'END_CAP_STYLE' : 0,
                      'JOIN_STYLE' : 0,
                      'MITER_LIMIT' : 2,
                      'SEGMENTS' : 5,
                      'OUTPUT' : 'memory:'}
        outShape_buf = processing.run('native:buffer', parameters)['OUTPUT']
        
        
        # aggregate new values to target geometries
        QgsMessageLog.logMessage('Aggregating new values to target geometries...', 'User notification', 0)
        parameters = {'DISCARD_NONMATCHING' : False,
                      'INPUT' : outShape_buf,
                      'JOIN' : unionShape_calc,
                      'JOIN_FIELDS' : fieldIdx_temp_names,
                      'PREDICATE' : [1],
                      'SUMMARIES' : [5],
                      'OUTPUT' : 'memory:'}
        outShape_join = processing.run('qgis:joinbylocationsummary', parameters)['OUTPUT']
        
        
        # iterate over each temporary field
        QgsMessageLog.logMessage('Transmitting values to new fields...', 'User notification', 0)
        outShape_rename = outShape_join
        
        for v in list(range(0, len(fieldIdx_temp_names))):
            
            QgsMessageLog.logMessage('...' + str(v) + '/' + str(len(fieldIdx_temp_names)), 'User notification', 0)
            
            # transmit values to new fields
            parameters = {'FIELD_LENGTH' : 10,
                          'FIELD_NAME' : fieldIdx_names[v],
                          'FIELD_PRECISION' : 10,
                          'FIELD_TYPE' : 1,
                          'FORMULA' : 'value = <' + fieldIdx_temp_names_sum[v] + '>',
                          'GLOBAL' : '',
                          'INPUT' : outShape_rename,
                          'OUTPUT' : 'memory:'}
            outShape_rename = processing.run('qgis:advancedpythonfieldcalculator', parameters)['OUTPUT']
        
        # delete redundant fields
        QgsMessageLog.logMessage('Dropping redundant fields...', 'User notification', 0)
        parameters = {'INPUT' : outShape_rename,
                      'COLUMN' : fieldIdx_temp_names_sum,
                      'OUTPUT' : 'memory:'}
        outShape_done = processing.run('qgis:deletecolumn', parameters)['OUTPUT']
        
        
        # write results to file
        QgsMessageLog.logMessage('Writing results to file...', 'User notification', 0)
        QgsVectorFileWriter.writeAsVectorFormat(outShape_done, outPath, 'ANSI', outShape.crs(), 'GPKG')
        
        # load result to canvas
        QgsProject.instance().addMapLayer(outShape_done)
        
        
        return {self.OUTPUT: outShape_done}
    

    def name(self):
        return 'shiftShapes'

    def displayName(self):
        return self.tr('Werte auf andere Flächen übertragen')

    def group(self):
        return self.tr('Raumanalaysen - Christian Mueller')

    def groupId(self):
        return 'Raumanalysen'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return shiftShapes()