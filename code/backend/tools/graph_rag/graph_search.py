from py2neo import Graph
from typing import List, Tuple, Dict, Set

class GraphSearch:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="12345678"):
        """初始化Neo4j连接"""
        self.graph = Graph(uri, auth=(user, password))
        self.entity_cache = {}  # 缓存已创建的实体节点

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
    
    def search_relations_with_centrality(self, entity_name: str, depth: int = 2, min_degree: int = 2, limit: int = 150) -> List[Dict]:
        """使用节点度中心性筛选重要节点的关系（不需要GDS库）
        
        Args:
            entity_name: 实体名称
            depth: 搜索深度，默认为2
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
    
    def search_relations_with_frequency(self, entity_name: str, depth: int = 3, min_frequency: int = 2, limit: int = 100) -> List[Dict]:
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
    
    def search_relations_(self, entity_name: str) -> Dict:
        """搜索与实体相关的关系，并按关系类型分组整理结果，直接从知识图谱获取嵌入向量"""
        
        # 查询实体关系，同时获取Syndrome节点的嵌入向量
        query = """
        MATCH (n:Syndrome)-[r]-(m)
        WHERE n.name CONTAINS $name
        RETURN n.name AS source, type(r) AS relation, m.name AS target, n.embedding AS embedding
        """
        raw_results = self.graph.run(query, name=entity_name).data()
        
        # 初始化变量
        grouped_results = {}
        embedding = []
        # 集合用于收集所有查询到的Syndrome节点名称
        found_entity_names = set() 
        
        # 整理数据结构：按关系类型分组
        for item in raw_results:
            source = item["source"]
            relation = item["relation"]
            target = item["target"]
            
            # 记录查询到的实体名称
            found_entity_names.add(source) 
            
            # 初始化分组结构
            if relation not in grouped_results:
                grouped_results[relation] = {
                    "source": source,
                    "relation": relation,
                    "targets": []
                }
            
            # 添加到分组中（避免重复）
            if target not in grouped_results[relation]["targets"]:
                grouped_results[relation]["targets"].append(target)

        final_entity_name = next(iter(found_entity_names), entity_name) 

        # 2. 转换为最终列表格式
        full_content = [
            f"{item['source']}{item['relation']}{item['targets']}" 
            for item in list(grouped_results.values())
        ]
    
        return {
            "full_content": full_content,
            "entity_name": final_entity_name, # <-- 修改点：将确定的实体名称放进来
        }

if __name__ == "__main__":
    # 创建GraphDB实例
    graph = GraphSearch()
    
    # 测试关系查询
    entity_name = "脾胃虚寒证"
    results = graph.search_relations_(entity_name)
    print(results)