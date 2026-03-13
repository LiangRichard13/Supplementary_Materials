from py2neo import Graph, Node, Relationship
from typing import List, Tuple, Dict, Set

class GraphBuilder:
    def __init__(self, url="", user="", password=""):
        """初始化Neo4j连接"""
        self.graph = Graph(url, auth=(user, password))
        self.entity_cache = {}  # 缓存已创建的实体节点
        
    def create_schema(self):
        """创建图数据库模式"""
        # 使用新的约束语法
        constraints = [
            "CREATE CONSTRAINT syndrome_name IF NOT EXISTS FOR (s:Syndrome) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT definition_name IF NOT EXISTS FOR (d:Definition) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT symptom_name IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT common_disease_and_diagnosis_name IF NOT EXISTS FOR (c:CommonDiseaseAndDiagnosis) REQUIRE c.name IS UNIQUE"
        ]
        
        for constraint in constraints:
            try:
                self.graph.run(constraint)
            except Exception as e:
                print(f"创建约束失败: {str(e)}")
                # 继续执行其他约束
                continue
    
    def get_or_create_entity(self, label: str, name: str, properties: Dict = None) -> Node:
        """获取或创建实体节点，使用缓存提高效率"""
        cache_key = f"{label}:{name}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]
        
        # 尝试查找现有节点
        node = self.graph.nodes.match(label, name=name).first()
        if not node:
            # 如果不存在则创建新节点
            if properties is None:
                properties = {}
            properties['name'] = name
            node = Node(label, **properties)
            self.graph.create(node)
        
        self.entity_cache[cache_key] = node
        return node
    
    def create_entity(self, label: str, properties: Dict):
        """创建实体节点"""
        if "name" not in properties:
            raise ValueError("实体必须包含name属性")
            
        # 提取name用于缓存键，其他属性用于节点创建
        name = properties["name"]
        node_properties = {k: v for k, v in properties.items() if k != "name"}
        
        return self.get_or_create_entity(label, name, node_properties)
    
    def create_relation(self, start_node: Node, end_node: Node, rel_type: str, properties: Dict = None):
        """创建关系"""
        if properties is None:
            properties = {}
        relation = Relationship(start_node, rel_type, end_node, **properties)
        self.graph.create(relation)
    
    def add_triple(self, subject: str, predicate: str, object: str):
        """添加三元组"""
        # 检查主体和客体是否存在于缓存中，如果存在直接使用
        subject_node = None
        object_node = None
        
        # 首先尝试在实体类型标签中查找
        for label in ["Syndrome", "Definition", "Symptom", "CommonDiseaseAndDiagnosis"]:
            if f"{label}:{subject}" in self.entity_cache:
                subject_node = self.entity_cache[f"{label}:{subject}"]
            if f"{label}:{object}" in self.entity_cache:
                object_node = self.entity_cache[f"{label}:{object}"]
        
        # 如果没有找到，则尝试使用通用Entity标签
        if subject_node is None:
            subject_node = self.get_or_create_entity("Entity", subject)
        
        if object_node is None:
            object_node = self.get_or_create_entity("Entity", object)
        
        # 创建关系
        self.create_relation(subject_node, object_node, predicate)
    
    def find_isolated_nodes(self) -> List[Dict]:
        """查找孤立节点"""
        query = """
        MATCH (n)
        WHERE NOT (n)-[]-()
        RETURN n.name AS name, labels(n) AS types
        """
        return self.graph.run(query).data()
    
    def delete_isolated_nodes(self) -> int:
        """删除所有孤立节点，返回删除的节点数量"""
        query = """
        MATCH (n)
        WHERE NOT (n)-[]-()
        WITH count(n) AS count_before
        MATCH (n)
        WHERE NOT (n)-[]-()
        DELETE n
        RETURN count_before
        """
        result = self.graph.run(query).data()
        return result[0]['count_before'] if result else 0
    
    def search_entity(self, name: str) -> List[Dict]:
        """搜索实体"""
        query = """
        MATCH (n)
        WHERE n.name CONTAINS $name
        RETURN n.name AS name, labels(n) AS types
        """
        return self.graph.run(query, name=name).data()
    
    def search_relations(self, entity_name: str) -> List[Dict]:
        """搜索与实体相关的关系"""
        query = """
        MATCH (n)-[r]-(m)
        WHERE n.name CONTAINS $name
        RETURN n.name AS source, type(r) AS relation, m.name AS target
        """
        return self.graph.run(query, name=entity_name).data()

    def search_relations_by_depth(self, entity_name: str, depth: int = 3) -> List[Dict]:
        """搜索与实体相关的指定深度的关系路径
        
        Args:
            entity_name: 实体名称
            depth: 搜索深度，默认为3
        
        Returns:
            关系列表，每个关系包含source, relation, target
        """
        query = f"""
        MATCH path=(n)-[*1..{depth}]-(m)
        WHERE n.name CONTAINS $name
        UNWIND relationships(path) AS r
        WITH startNode(r) AS s, type(r) AS relation, endNode(r) AS e
        RETURN DISTINCT s.name AS source, relation, e.name AS target
        """
        return self.graph.run(query, name=entity_name).data()
    
    def search_relations_with_centrality(self, entity_name: str, depth: int = 3, min_degree: int = 2, limit: int = 100) -> List[Dict]:
        """使用节点度中心性筛选重要节点的关系（不需要GDS库）
        
        Args:
            entity_name: 实体名称
            depth: 搜索深度，默认为3
            min_degree: 最小连接度，默认2
            limit: 返回结果数量限制，默认100
            
        Returns:
            重要关系列表
        """
        query = f"""
        // 先找出度数高的重要节点
        MATCH (n)-[r]-()
        WITH n, count(r) AS degree
        WHERE degree >= $min_degree
        WITH collect(id(n)) AS importantNodes
        
        // 然后从指定起点出发，只获取包含重要节点的路径
        MATCH path=(start)-[*1..{depth}]-(m)
        WHERE start.name CONTAINS $name
        // 确保路径中的至少一个节点是重要节点（除了起点）
        AND any(node IN nodes(path)[1..] WHERE id(node) IN importantNodes)
        
        // 提取关系
        UNWIND relationships(path) AS r
        WITH startNode(r) AS s, type(r) AS relation, endNode(r) AS e
        
        // 返回结果
        RETURN DISTINCT s.name AS source, relation, e.name AS target
        LIMIT $limit
        """
        return self.graph.run(query, name=entity_name, min_degree=min_degree, limit=limit).data()
    
    def search_relations_optimized(self, entity_name: str, depth: int = 3, limit: int = 100) -> List[Dict]:
        """优化的关系查询，控制路径多样性并限制结果数量
        
        Args:
            entity_name: 实体名称
            depth: 搜索深度，默认为3
            limit: 返回结果数量限制，默认100
            
        Returns:
            关系列表，每个关系包含source, relation, target
        """
        query = f"""
        MATCH (n) WHERE n.name CONTAINS $name
        MATCH path=(n)-[*1..{depth}]-(m)
        WITH path, length(path) AS len
        ORDER BY len ASC
        LIMIT $path_limit
        UNWIND relationships(path) AS r
        WITH startNode(r) AS s, type(r) AS relation, endNode(r) AS e
        RETURN DISTINCT s.name AS source, relation, e.name AS target
        LIMIT $limit
        """
        return self.graph.run(query, name=entity_name, path_limit=limit*2, limit=limit).data()
    
    def search_relations_with_frequency(self, entity_name: str, depth: int = 3, min_frequency: int = 2, limit: int = 200) -> List[Dict]:
        """基于关系出现频率的关系查询，筛选高频关系
        
        Args:
            entity_name: 实体名称
            depth: 搜索深度，默认为3
            min_frequency: 最小出现频率，默认2
            limit: 返回结果数量限制，默认100
            
        Returns:
            高频关系列表
        """
        query = f"""
        MATCH path=(n)-[*1..{depth}]-(m)
        WHERE n.name CONTAINS $name
        UNWIND relationships(path) AS r
        WITH startNode(r) AS s, type(r) AS relation, endNode(r) AS e
        WITH s.name AS source, relation, e.name AS target, count(*) AS frequency
        WHERE frequency >= $min_frequency
        RETURN DISTINCT source, relation, target, frequency
        ORDER BY frequency DESC
        LIMIT $limit
        """
        return self.graph.run(query, name=entity_name, min_frequency=min_frequency, limit=limit).data()
    
    def find_path(self, start_name: str, end_name: str, max_depth: int = 3) -> List[Dict]:
        """查找两个实体之间的路径"""
        query = """
        MATCH path = shortestPath((n)-[*1..%d]-(m))
        WHERE n.name CONTAINS $start_name AND m.name CONTAINS $end_name
        RETURN path
        """ % max_depth
        return self.graph.run(query, start_name=start_name, end_name=end_name).data()
        
    def clear_all(self):
        """清空数据库中的所有节点和关系"""
        self.graph.run("MATCH (n) DETACH DELETE n")
        # 重置缓存
        self.entity_cache = {}

# 查询测试
if __name__ == "__main__":
    builder = GraphBuilder()
    search_result=builder.search_relations("湿重热轻证")
    print(search_result)
