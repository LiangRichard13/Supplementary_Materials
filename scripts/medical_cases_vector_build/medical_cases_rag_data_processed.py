import json

#引入Chroma向量库，Chroma是一个轻量级的向量存储库，用于保存和检索向量
from langchain_chroma import Chroma

from gteEmbeddings import GTEEmbeddings

from langchain.retrievers import BM25Retriever
from langchain.schema import Document

import pickle

import os

import jieba
from typing import List

def get_chunks(directory:str)->List[dict]:
    '''
    用于加载和分块文档
    参数: directory 用于rag的文档目录路径
    返回: 分块后的文档列表
    '''
    print('开始加载')
    # 以jsonl的格式加载
    with open(directory, 'r', encoding='utf-8') as f:
        data = f.readlines()
    assemble_list = []
    for line in data:
        json_obj = json.loads(line)
        assemble_list.append(json_obj)
    return assemble_list # 返回切分后的分块

def convert_to_langchain_documents(chunks_list: List[dict]) -> List[Document]:
    '''
    将文本列表转换为LangChain的Document对象列表
    参数: texts 文本列表
    返回: Document对象列表
    '''
    documents = []
    for i, chunk in enumerate(chunks_list):
        # 创建Document对象，为每个文档添加源信息和id
        doc = Document(
            page_content='患者主诉:'+chunk['chief_complaint']+'\n'+'病情描述:'+chunk['description']+'\n'+'中医四诊摘要:'+chunk['detection'],
            metadata={"source": f"meidical_cases_{i}", "id": str(i), "syndrome": chunk['norm_syndrome']}
        )
        documents.append(doc)
    return documents

def load_embedding_model():
    '''
    用于加载来自openai的embedding model
    返回一个OpenAIEmbeddings的实例
    '''
    embeddings=GTEEmbeddings()
    return embeddings

def store_chroma(docs,embeddings,persist_directory=''):
    '''
    1.将分块后的文本数据通过embedding model进行嵌入生成向量
    2.将向量数据持久化到磁盘
    3.返回Chroma数据库对象以供后续使用
    '''
    db = Chroma.from_documents(documents=docs, embedding=embeddings, persist_directory=persist_directory)
    #这里的向量数据应该和分块后的文档块数量一致
    print(f"数据库中的向量数据: {db._collection.count()}")
    return db

def create_bm25_index(docs):
    '''
    创建BM25索引，使用jieba进行中文分词
    '''
    # 对文档进行中文分词
    def tokenize_chinese(text: str) -> List[str]:
        tokens = list(jieba.cut(text))
        return tokens
    
    # 测试分词效果
    if len(docs) > 0:
        test_text = docs[0].page_content[:200]  # 取第一个文档的前200个字符测试
        print("\n分词测试示例：")
        print("原文：", test_text)
        print("分词结果：", " ".join(tokenize_chinese(test_text)))
    
    # 创建bm25检索数据库，使用中文分词
    bm25_retriever = BM25Retriever.from_documents(
        docs,
        tokenizer=tokenize_chinese
    )
    bm25_retriever.k = 5

    # 创建存储目录
    os.makedirs("", exist_ok=True)

    with open("", "wb") as f:
        pickle.dump(bm25_retriever, f)

    print("BM25检索器已成功保存到磁盘")


if __name__ == "__main__":
    chunk_list=get_chunks(directory='')
    print(len(chunk_list))
    # 将文本列表转换为LangChain Document对象
    documents = convert_to_langchain_documents(chunk_list)
    print(len(documents))
    print(documents[0])
    embedding_model=load_embedding_model()
    store_chroma(documents, embedding_model)
    create_bm25_index(documents)