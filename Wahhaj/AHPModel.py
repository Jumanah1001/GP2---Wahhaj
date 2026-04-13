from AhpAnpLib import inputs_AHPLib as input
from AhpAnpLib import structs_AHPLib as str

import numpy as np
from Wahhaj.models import Raster

class AHPModel:
    def __init__(self):
        self.model = str.Model("AHP Location Selection")
        self.goal_cluster_name = "1Goal"
        self.criteria_cluster_name = "2Criteria"
        self.alternatives_cluster_name = "3Alternatives"

    def build_goal(self):
        goal_cluster = str.Cluster(self.goal_cluster_name, 0)
        goal_node = str.Node("GoalNode", 0)
        goal_cluster.addNode2Cluster(goal_node)
        self.model.addCluster2Model(goal_cluster)

    def build_criteria(self):
        criteria_cluster = str.Cluster(self.criteria_cluster_name, 1)
        self.solar_radiance     = str.Node("1solar radiance", 1)
        self.sunshine_hours     = str.Node("2sunshine hours", 2)
        self.slope              = str.Node("3slope", 3)
        self.elevation          = str.Node("4elevation", 4)
        self.surface_temperature= str.Node("5surface temperature", 5)
        criteria_cluster.addMultipleNodes2Cluster(
            self.solar_radiance, self.sunshine_hours,
            self.slope, self.elevation, self.surface_temperature
        )
        self.model.addCluster2Model(criteria_cluster)

    
    def computeSuitabilityScore(self, layers):
        WEIGHTS = {
            'ghi':       0.30,
            'slope':     0.22,
            'sunshine':  0.18,
            'obstacle':  0.13,
            'lst':       0.10,
            'elevation': 0.07,
        }
        INVERTED = {'slope', 'lst', 'obstacle'}

        shape  = layers[0].data.shape
        score  = np.zeros(shape, dtype=np.float32)
        total_w = 0.0

        EXPECTED_ORDER = ['ghi', 'sunshine', 'slope', 'elevation', 'lst', 'obstacle']

        for i, raster in enumerate(layers):
            name = raster.metadata.get('layer') if raster.metadata else None
            if not name or name not in WEIGHTS:
                name = EXPECTED_ORDER[i] if i < len(EXPECTED_ORDER) else None
            if not name:
                continue

            weight = WEIGHTS.get(name, 0.0)
            data = raster.data.astype(np.float32).copy()
            valid = data != raster.nodata
            if not valid.any():
                continue
            if name in INVERTED:
                data[valid] = 1.0 - data[valid]
            data[valid] = np.clip(data[valid], 0.0, 1.0)
            score   += weight * data
            total_w += weight

        if total_w > 0:
            score /= total_w

        return Raster(
            data=score,
            nodata=-9999.0,
            metadata={'layer': 'suitability', 'source': 'AHP', 'cr': 0.015}
        )

    def add_alternatives(self, area_names):
        alternatives_cluster = str.Cluster(self.alternatives_cluster_name, 2)
        self.alternative_nodes = []
        for i, area_name in enumerate(area_names, start=10):
            area_node = str.Node(area_name, i)
            self.alternative_nodes.append(area_node)
            alternatives_cluster.addNode2Cluster(area_node)
        self.model.addCluster2Model(alternatives_cluster)

    def connect_hierarchy(self):
        self.model.addNodeConnectionFromAllNodesToAllNodesOfCluster(
            self.goal_cluster_name, self.criteria_cluster_name)
        self.model.addNodeConnectionFromAllNodesToAllNodesOfCluster(
            self.criteria_cluster_name, self.alternatives_cluster_name)

    def build_model(self, area_names):
        self.build_goal()
        self.build_criteria()
        self.add_alternatives(area_names)
        self.connect_hierarchy()

    def print_structure(self):
        self.model.printStruct()

    def export_questionnaire_excel(self, filename="WAHHAJ_AHP_Questionnaire.xlsx"):
        input.export4ExcelQuestFull(self.model, filename, True)

    def get_label(self, score: float) -> tuple:
        s = score * 100
        if s >= 75: return 'Highly Suitable', 'green'
        if s >= 55: return 'Suitable', 'orange'
        if s >= 35: return 'Moderately Suitable', 'yellow'
        return 'Not Suitable', 'red'
