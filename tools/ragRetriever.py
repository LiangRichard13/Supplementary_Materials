from model.embedding_model.gteEmbeddings import GTEEmbeddings
from langchain_chroma import Chroma
from langchain.retrievers import EnsembleRetriever
from langchain.schema import Document
from langchain_core.runnables import RunnableParallel
from tools.rag.ranker import two_stage_rerank,modelscope_rerank,reciprocal_rank_fusion,eliminate_after_rrf
from typing import Dict
import pickle

class Retriever:

    tcm_texts_persist_directory = ''
    medical_cases_persist_directory = ''

    def __init__(self)->None:
        """
        初始化检索器
        
        参数:
            persist_directory: 向量存储的持久化目录路径
        """
        self.embedding_model = GTEEmbeddings()
        tcm_texts_db = Chroma(
            persist_directory=self.tcm_texts_persist_directory,
            embedding_function=self.embedding_model
        )

        # 创建检索中医典籍的融合检索器
        self.tcm_texts_chroma_retriever = tcm_texts_db.as_retriever()
        self.tcm_texts_chroma_retriever.search_kwargs['k'] = 5
        
        # 获取bm25 retriever
        with open("", "rb") as f:
            self.tcm_texts_bm25_retriever = pickle.load(f)

        # 创建融合检索器,chroma-based和bm25检索权重分别为0.6和0.4
        self.tcm_texts_ensemble_retriever_64 = EnsembleRetriever(
            retrievers=[self.tcm_texts_chroma_retriever, self.tcm_texts_bm25_retriever],
            weights=[0.6, 0.4],
        )

        # 创建检索中医医案病例的融合检索器
        medical_cases_db = Chroma(
            persist_directory=self.medical_cases_persist_directory,
            embedding_function=self.embedding_model
        )
        self.medical_cases_chroma_retriever = medical_cases_db.as_retriever()
        self.medical_cases_chroma_retriever.search_kwargs['k'] = 5
        
        # 获取bm25 retriever
        with open("", "rb") as f:
            self.medical_cases_bm25_retriever = pickle.load(f)

        # 创建融合检索器,chroma-based和bm25检索权重分别为0.6和0.4
        self.medical_cases_ensemble_retriever_64 = EnsembleRetriever(
            retrievers=[self.medical_cases_chroma_retriever, self.medical_cases_bm25_retriever],
            weights=[0.6, 0.4],
        )

        # 创建并行检索器
        self.parallel_retrievers = RunnableParallel({
            "chroma_retriever": self.chroma_retriever,
            "bm25_retriever": self.bm25_retriever,
            "ensemble_retriever_55": self.ensemble_retriever_55
        })

    def get_medical_cases_information(self,query:str)->list[Dict[str,str]]:
        results=self.medical_cases_ensemble_retriever_64.invoke(query)
        # 进行精排序
        ranked_results=modelscope_rerank(query=query,documents=results)
        cases_results=[{"证候":doc.metadata["syndrome"],"病情描述及四诊摘要":doc.page_content} for doc in ranked_results]
        return cases_results

    # 获取chroma-based检索器的检索结果并通过modelscope model进行一次排序
    def get_tcm_texts_documents_with_rerank(self, query:str)->list[Dict[str,str]]:
        """
        获取与查询语义最接近的文档
        
        参数:
            query: 查询文本
            
        返回:
            相关文档的内容列表
        """
        results = self.tcm_texts_ensemble_retriever_64.invoke(query)

        # 进行精排序
        ranked_results=modelscope_rerank(query=query,documents=results)
        
        return [{"source":doc.metadata["source"],"content":doc.page_content} for doc in ranked_results]
    
    # 获取chroma-based检索器对多个基于任务查询的检索结果
    def get_chroma_based_batch_relevant_documents(self,queries:list[str])->list[list[Document]]:
        results=self.chroma_retriever.batch(queries,config={"max_concurrency":5})
        return results
    
    # 获取并行检索器的结果
    def get_parallel_retrievers_relevant_documents(self,query:str)->list[list[Document]]:
        results = self.parallel_retrievers.invoke(query)
        results=self.dict_to_list_of_lists(results)
        return results
    
    # 获取多查询融合检索器的结果
    def get_multi_query_ensemble_retriever_relevant_documents(self,queries:list[str])->list[list[Document]]:
        results=self.ensemble_retriever_64.batch(queries,config={"max_concurrency":5})
        return results

    # 获取并行检索器+排序的结果
    def multi_retriever_with_two_stage_rerank_chain(self,query:str)->list[Dict[str,str]]:
        parallel_results = self.get_parallel_retrievers_relevant_documents(query)     

        # 使用两阶段重排序
        ranked_results = two_stage_rerank(query,parallel_results,rrf_k=20)
        
        # 返回最终结果
        return [{"source":doc.metadata["source"],"content":doc.page_content} for doc in ranked_results]
    
    # 获取多查询融合检索器+排序的结果
    def multi_query_with_two_stage_rerank_chain(self,queries:str,original_query)->list[Dict[str,str]]:
        # 获取多查询融合检索器的检索结果
        ensemble_results = self.get_multi_query_ensemble_retriever_relevant_documents(queries)     

        eliminate_ensembnle_results=[result_list[:5] for result_list in ensemble_results]

        # 通过rrf算法融合每个结果列表得到最终排序
        ranked_results=reciprocal_rank_fusion(results=eliminate_ensembnle_results,top_k=10,k=60)

        # 通过modelscope model精排
        fine_ranked_results=modelscope_rerank(query=original_query,documents=ranked_results,top_k=5)

        # 返回最终结果
        return [{"source":doc.metadata["source"],"content":doc.page_content} for doc in fine_ranked_results]
    
    def dict_to_list_of_lists(self,retriever_results:dict)->list[list[Document]]:
        # 从字典中提取检索结果并转换为列表的列表
        return [
            retriever_results["chroma_retriever"],
            retriever_results["bm25_retriever"],
            retriever_results["ensemble_retriever_55"][:5]
        ]

    