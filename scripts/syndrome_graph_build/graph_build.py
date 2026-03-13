from graphBuilder import GraphBuilder
import argparse
import json
def process_json_file(file_path: str, builder: GraphBuilder):
    """处理单个JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                
                # 处理实体
                syndrome_name = data.get('Name', {}) # str
                syndrome_definition = data.get('Definition', {}) # str
                syndrome_symptoms = data.get('Typical_performance', {}) # list
                syndrome_diagnosis = data.get('Common_diseases', {}) # list
                syndrome_embedding = data.get('embedding', {}) # list
                
                # 创建证候节点，包含embedding属性
                syndrome_properties = {'name': syndrome_name}
                if syndrome_embedding:
                    syndrome_properties['embedding'] = syndrome_embedding
                
                builder.create_entity('Syndrome', syndrome_properties) # 创建证候节点
                builder.create_entity('Definition', {'name': syndrome_definition}) # 创建证候定义节点
                for symptom in syndrome_symptoms: # 创建证候症状节点
                    builder.create_entity('Symptom', {'name': symptom}) 
                for diagnosis in syndrome_diagnosis: # 创建证候诊断节点
                    builder.create_entity('CommonDiseaseAndDiagnosis', {'name': diagnosis})


                syndrome_to_definition = [syndrome_name,"的定义是",syndrome_definition]
                syndrome_to_symptoms = [[syndrome_name,"有症状：",symptom] for symptom in syndrome_symptoms]
                syndrome_to_diagnosis = [[syndrome_name,"对应常见病及治疗方法：",diagnosis] for diagnosis in syndrome_diagnosis]
                
                # 合并为一个列表
                triples = [syndrome_to_definition] + syndrome_to_symptoms + syndrome_to_diagnosis
                
                # 处理关系
                for triple in triples:
                    if len(triple) == 3:
                        builder.add_triple(*triple)
                        
            except Exception as e:
                print(f"处理记录失败: {str(e)}")
                continue


def main():
    parser = argparse.ArgumentParser(description="构建中医知识图谱")
    parser.add_argument("--input_dir", type=str, default="", help="JSON文件目录")
    parser.add_argument("--neo4j_uri", type=str, default="", help="Neo4j URI")
    parser.add_argument("--neo4j_user", type=str, default="", help="Neo4j用户名")
    parser.add_argument("--neo4j_password", type=str, default="", help="Neo4j密码")
    
    args = parser.parse_args()
    
    # 初始化图构建器
    builder = GraphBuilder(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    
    # 清空现有数据
    builder.clear_all()
    
    # 创建约束
    builder.create_schema()

    try:
        file_path=args.input_dir
        process_json_file(file_path, builder)
    except Exception as e:
        print(f"处理文件 {file_path} 失败: {str(e)}")

    print("知识图谱构建完成！")

if __name__ == "__main__":
    main()
