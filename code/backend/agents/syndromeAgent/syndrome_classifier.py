import json
from typing import List, Dict, Tuple

class SyndromeClassifier:
    def __init__(self, classification_file: str = "/home/ubuntu/MCM/backend/agents/syndromeAgent/syndrome_classification_table.json"):
        """
        初始化证候分类器
        
        Args:
            classification_file: 证候分类表的JSON文件路径
        """
        with open(classification_file, 'r', encoding='utf-8') as f:
            self.classification_data = json.load(f)
        
        # 创建证候到类别的映射
        self.syndrome_to_category = {}
        # 创建类别到所有证候的映射
        self.category_to_syndromes = {}
        
        for category_name, category_info in self.classification_data.items():
            self.category_to_syndromes[category_name] = category_info['patterns']
            for syndrome in category_info['patterns']:
                self.syndrome_to_category[syndrome] = {
                    'category': category_name,
                    'description': category_info['description']
                }
    
    def classify_syndromes(self, syndromes: List[str]) -> Dict[str, Dict[str, any]]:
        """
        对输入的证候列表进行分类
        
        Args:
            syndromes: 证候列表
            
        Returns:
            字典，键为证候名，值为包含类别、描述和同类证候的字典
        """
        result = {}
        
        for syndrome in syndromes:
            if syndrome in self.syndrome_to_category:
                category = self.syndrome_to_category[syndrome]['category']
                result[syndrome] = {
                    'category': category,
                    'description': self.syndrome_to_category[syndrome]['description'],
                    'same_category_syndromes': self.category_to_syndromes[category]
                }
            else:
                result[syndrome] = {
                    'category': '未分类',
                    'description': '该证候在分类表中未找到',
                    'same_category_syndromes': []
                }
        
        return result
    
    def get_syndrome_info(self, syndrome: str) -> Dict[str, any]:
        """
        获取单个证候的分类信息
        
        Args:
            syndrome: 证候名称
            
        Returns:
            包含类别、描述和同类证候的字典
        """
        if syndrome in self.syndrome_to_category:
            category = self.syndrome_to_category[syndrome]['category']
            return {
                'category': category,
                'description': self.syndrome_to_category[syndrome]['description'],
                'same_category_syndromes': self.category_to_syndromes[category]
            }
        else:
            return {
                'category': '未分类',
                'description': '该证候在分类表中未找到',
                'same_category_syndromes': []
            }
    
    def get_same_category_syndromes(self, syndrome: str) -> List[str]:
        """
        获取与指定证候同类的所有证候
        
        Args:
            syndrome: 证候名称
            
        Returns:
            同类证候列表
        """
        if syndrome in self.syndrome_to_category:
            category = self.syndrome_to_category[syndrome]['category']
            return self.category_to_syndromes[category]
        else:
            return []
    
    def get_all_categories(self) -> Dict[str, str]:
        """
        获取所有类别及其描述
        
        Returns:
            类别名称到描述的映射
        """
        return {name: info['description'] for name, info in self.classification_data.items()}


def main():
    """示例用法"""
    # 初始化分类器
    classifier = SyndromeClassifier()
    
    # 示例证候列表
    test_syndromes = ["气虚证", "血虚证", "阴虚证", "阳虚证", "痰湿证", "不存在的证候"]
    
    # 进行分类
    results = classifier.classify_syndromes(test_syndromes)
    
    # 打印结果
    print("证候分类结果：")
    print(results)
    # print("=" * 50)
    # for syndrome, info in results.items():
    #     print(f"证候: {syndrome}")
    #     print(f"类别: {info['category']}")
    #     print(f"描述: {info['description']}")
    #     print(f"同类证候: {', '.join(info['same_category_syndromes'])}")
    #     print("-" * 30)


if __name__ == "__main__":
    main() 