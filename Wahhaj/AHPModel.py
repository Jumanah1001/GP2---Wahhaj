from AhpAnpLib import inputs_AHPLib as input
from AhpAnpLib import structs_AHPLib as str


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

        self.solar_radiance = str.Node("1solar radiance", 1)
        self.sunshine_hours = str.Node("2sunshine hours", 2)
        self.slope = str.Node("3slope", 3)
        self.elevation = str.Node("4elevation", 4)
        self.surface_temperature = str.Node("5surface temperature", 5)

        criteria_cluster.addMultipleNodes2Cluster(
            self.solar_radiance,
            self.sunshine_hours,
            self.slope,
            self.elevation,
            self.surface_temperature
        )

        self.model.addCluster2Model(criteria_cluster)

    def add_alternatives(self, area_names):
        alternatives_cluster = str.Cluster(self.alternatives_cluster_name, 2)

        self.alternative_nodes = []
        start_id = 10

        for i, area_name in enumerate(area_names, start=start_id):
            area_node = str.Node(area_name, i)
            self.alternative_nodes.append(area_node)
            alternatives_cluster.addNode2Cluster(area_node)

        self.model.addCluster2Model(alternatives_cluster)

    def connect_hierarchy(self):
        self.model.addNodeConnectionFromAllNodesToAllNodesOfCluster(
            self.goal_cluster_name,
            self.criteria_cluster_name
        )

        self.model.addNodeConnectionFromAllNodesToAllNodesOfCluster(
            self.criteria_cluster_name,
            self.alternatives_cluster_name
        )

    def build_model(self, area_names):
        self.build_goal()
        self.build_criteria()
        self.add_alternatives(area_names)
        self.connect_hierarchy()

    def print_structure(self):
        self.model.printStruct()

    def export_questionnaire_excel(self, filename="WAHHAJ_AHP_Questionnaire.xlsx"):
        input.export4ExcelQuestFull(self.model, filename, True)