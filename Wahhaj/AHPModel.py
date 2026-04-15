# AhpAnpLib is optional — only needed for build_model/export_questionnaire
# computeSuitabilityScore uses numpy only and always works
try:
    from AhpAnpLib import inputs_AHPLib as _ahp_input
    from AhpAnpLib import structs_AHPLib as _ahp_str
    _AHP_LIB_AVAILABLE = True
except ImportError:
    _AHP_LIB_AVAILABLE = False
    _ahp_input = None
    _ahp_str   = None

import numpy as np

try:
    from .models import Raster
except ImportError:
    from Wahhaj.models import Raster


class AHPModel:
    def __init__(self):
        # Only build the AhpAnpLib model object if the library is available
        if _AHP_LIB_AVAILABLE:
            self.model = _ahp_str.Model("AHP Location Selection")
        else:
            self.model = None
        self.goal_cluster_name         = "1Goal"
        self.criteria_cluster_name     = "2Criteria"
        self.alternatives_cluster_name = "3Alternatives"

    # ── Core method — numpy only, always works ────────────────────────────
    def computeSuitabilityScore(self, layers):
        WEIGHTS = {
            'ghi':       0.30,
            'slope':     0.22,
            'sunshine':  0.18,
            'obstacle':  0.13,
            'lst':       0.10,
            'elevation': 0.07,
        }
        INVERTED       = {'slope', 'lst', 'obstacle'}
        EXPECTED_ORDER = ['ghi', 'sunshine', 'slope', 'elevation', 'lst', 'obstacle']

        shape   = layers[0].data.shape
        score   = np.zeros(shape, dtype=np.float32)
        total_w = 0.0

        for i, raster in enumerate(layers):
            name = raster.metadata.get('layer') if raster.metadata else None
            if not name or name not in WEIGHTS:
                name = EXPECTED_ORDER[i] if i < len(EXPECTED_ORDER) else None
            if not name:
                continue

            weight = WEIGHTS.get(name, 0.0)
            data   = raster.data.astype(np.float32).copy()
            valid  = data != raster.nodata
            if not valid.any():
                continue
            if name in INVERTED:
                data[valid] = 1.0 - data[valid]
            data[valid]  = np.clip(data[valid], 0.0, 1.0)
            score       += weight * data
            total_w     += weight

        if total_w > 0:
            score /= total_w

        return Raster(
            data=score, nodata=-9999.0,
            metadata={'layer': 'suitability', 'source': 'AHP', 'cr': 0.015})

    # ── AhpAnpLib-dependent methods — skip if library not installed ───────
    def build_goal(self):
        if not _AHP_LIB_AVAILABLE: return
        gc = _ahp_str.Cluster(self.goal_cluster_name, 0)
        gc.addNode2Cluster(_ahp_str.Node("GoalNode", 0))
        self.model.addCluster2Model(gc)

    def build_criteria(self):
        if not _AHP_LIB_AVAILABLE: return
        cc = _ahp_str.Cluster(self.criteria_cluster_name, 1)
        self.solar_radiance      = _ahp_str.Node("1solar radiance", 1)
        self.sunshine_hours      = _ahp_str.Node("2sunshine hours", 2)
        self.slope               = _ahp_str.Node("3slope",          3)
        self.elevation           = _ahp_str.Node("4elevation",      4)
        self.surface_temperature = _ahp_str.Node("5surface temperature", 5)
        cc.addMultipleNodes2Cluster(
            self.solar_radiance, self.sunshine_hours,
            self.slope, self.elevation, self.surface_temperature)
        self.model.addCluster2Model(cc)

    def add_alternatives(self, area_names):
        if not _AHP_LIB_AVAILABLE: return
        ac = _ahp_str.Cluster(self.alternatives_cluster_name, 2)
        self.alternative_nodes = []
        for i, name in enumerate(area_names, start=10):
            node = _ahp_str.Node(name, i)
            self.alternative_nodes.append(node)
            ac.addNode2Cluster(node)
        self.model.addCluster2Model(ac)

    def connect_hierarchy(self):
        if not _AHP_LIB_AVAILABLE: return
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
        if not _AHP_LIB_AVAILABLE: return
        self.model.printStruct()

    def export_questionnaire_excel(self, filename="WAHHAJ_AHP_Questionnaire.xlsx"):
        if not _AHP_LIB_AVAILABLE: return
        _ahp_input.export4ExcelQuestFull(self.model, filename, True)

    def get_label(self, score: float) -> tuple:
        s = score * 100
        if s >= 75: return 'Highly Suitable',     'green'
        if s >= 55: return 'Suitable',             'orange'
        if s >= 35: return 'Moderately Suitable',  'yellow'
        return          'Not Suitable',            'red'
