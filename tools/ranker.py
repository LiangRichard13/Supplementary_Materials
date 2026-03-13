from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from langchain.load import dumps, loads
from typing import List
from langchain.schema import Document
import math

def two_stage_rerank(query: str, 
                    multiple_results: List[List[Document]], 
                    rrf_k: int = 60, 
                    coarse_keep_ratio: float = 0.5, 
                    fine_keep_ratio: float = 0.8,
                    final_top_k: int = None):
    """
    两阶段重排序方法：先用RRF进行粗排序，再用modelscope模型进行精排序
    
    参数:
        query: 查询问题
        multiple_results: 多个排序列表的列表，每个列表包含已排序的文档
        rrf_k: RRF公式中使用的参数，默认为60
        coarse_keep_ratio: 粗排序后保留的文档比例，默认0.5（保留前50%）
        final_top_k: 最终返回的文档数量，默认为None（返回所有精排序结果）
        
    返回:
        两阶段重排序后的文档列表
    """
    # 第一阶段：RRF粗排序
    print(f"第一阶段：使用RRF对{sum(len(docs) for docs in multiple_results)}个文档进行粗排序")
    coarse_ranked = reciprocal_rank_fusion(multiple_results, k=rrf_k)
    
    # 计算粗排序后要保留的文档数量
    coarse_keep_count = max(1, math.ceil(len(coarse_ranked) * coarse_keep_ratio))
    print(f"粗排序结果：保留前{coarse_keep_count}/{len(coarse_ranked)}个文档进行精排序")
    
    # 保留前coarse_keep_ratio比例的文档
    coarse_filtered = coarse_ranked[:coarse_keep_count]
    
    # 第二阶段：使用modelscope模型进行精排序
    print(f"第二阶段：使用modelscope模型对{len(coarse_filtered)}个文档进行精排序")
    fine_ranked = modelscope_rerank(query, coarse_filtered, top_k=final_top_k)
    fine_keep_count = max(1, math.ceil(len(fine_ranked) * fine_keep_ratio))
    fine_filtered = fine_ranked[:fine_keep_count]
    print(f"精排序结果：保留前{fine_keep_count}/{len(fine_ranked)}个文档")
    
    return fine_filtered

def modelscope_rerank(query: str, documents: List[Document], top_k: int = None):
    """
    使用modelscope的文本排序模型对检索到的文档进行重排序
    
    参数:
        query: 查询问题
        documents: 检索到的文档列表，每个文档应该是一个字典，包含content字段
        top_k: 返回的文档数量，默认返回所有文档
        
    返回:
        重排序后的文档列表
    """
    # 初始化模型
    model_path=""
    pipeline_ins = pipeline(task=Tasks.text_ranking, model=model_path, model_revision='v1.4.0')
    
    # 准备输入数据
    inputs = {
        'source_sentence': [query],
        'sentences_to_compare': [doc.page_content for doc in documents]
    }
    
    # 执行排序
    result = pipeline_ins(input=inputs)
    
    # 将排序分数与文档匹配
    scored_docs = []
    for i, score in enumerate(result['scores']):
        doc_copy={}
        doc_copy["doc"] = documents[i].copy()
        doc_copy["score"] = float(score)
        scored_docs.append(doc_copy)
    
    # 按分数排序
    sorted_docs = sorted(scored_docs, key=lambda x: x["score"], reverse=True)
    
    # 如果指定了top_k，则只返回前top_k个文档
    if top_k is not None:
        sorted_docs = sorted_docs[:top_k]
    
    return [doc["doc"] for doc in sorted_docs]

def reciprocal_rank_fusion(results: List[List[Document]], k: int = 60, top_k: int = None):
    """
    实现倒数排名融合(Reciprocal Rank Fusion)算法，对多个排序列表进行融合
    
    参数:
        results: 多个排序列表的列表，每个列表包含已排序的文档
        k: RRF公式中使用的参数，默认为60
        top_k: 返回的文档数量，默认返回所有文档
        
    返回:
        融合后的排序文档列表
    """
    fused_scores = {}
    doc_map = {}  # 用于还原文档对象

    for docs in results:
        for rank, doc in enumerate(docs):
            # 用唯一字符串标识文档
            doc_key = str(doc.page_content)  # 或用 json.dumps(doc.metadata) + doc.page_content
            if doc_key not in fused_scores:
                fused_scores[doc_key] = 0
                doc_map[doc_key] = doc
            fused_scores[doc_key] += 1 / (rank + k)

    # 排序并还原文档对象
    reranked_keys = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    reranked_results = [doc_map[key] for key, _ in reranked_keys]

    if top_k is not None:
        reranked_results = reranked_results[:top_k]
    return reranked_results

def eliminate_after_rrf(coarse_ranked: List[Document],coarse_keep_ratio: float = 0.5):
    """
    对RRF粗排序后的文档进行处理，保留前coarse_keep_ratio比例的文档
    
    参数:
        documents: 粗排序后的文档列表
    """
    # 计算粗排序后要保留的文档数量
    coarse_keep_count = max(1, math.ceil(len(coarse_ranked) * coarse_keep_ratio))
    print(f"粗排序结果：保留前{coarse_keep_count}/{len(coarse_ranked)}个文档进行精排序")
    
    # 保留前coarse_keep_ratio比例的文档
    coarse_filtered = coarse_ranked[:coarse_keep_count]

    return coarse_filtered