from langchain_openai import ChatOpenAI
from langchain_core.prompts import SystemMessagePromptTemplate
from langchain_core.messages import HumanMessage
from agents.ragAgent.rag_agents_config import query_generator_system_message,rag_information_filter_system_message,entity_extraction_system_message,graph_rag_filter_system_message,web_search_system_message,web_search_filter_system_message,query_generator_system_message_for_plan_rag
from tools.process_code_blocks import check_and_process_code_blocks
from tools.graph_rag.graph_search import GraphSearch
from tools.search.serper_search import SerperSearch
from tools.colorPrinter import ColorPrinter
from agents.agents_model_config import RAG_AGENT_BASE_URL,RAG_AGENT_MODEL,RAG_AGENT_API_KEY
from typing import Dict,List
import json

class RagAgent:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(base_url=RAG_AGENT_BASE_URL, model=RAG_AGENT_MODEL, api_key=RAG_AGENT_API_KEY)
        self.query_generator_system_template=SystemMessagePromptTemplate.from_template(query_generator_system_message)
        self.rag_information_filter_system_template=SystemMessagePromptTemplate.from_template(rag_information_filter_system_message)
        self.entity_extraction_system_template=SystemMessagePromptTemplate.from_template(entity_extraction_system_message)
        self.graph_filter_system_template=SystemMessagePromptTemplate.from_template(graph_rag_filter_system_message)
        self.web_search_system_template=SystemMessagePromptTemplate.from_template(web_search_system_message)
        self.web_search_filter_system_template=SystemMessagePromptTemplate.from_template(web_search_filter_system_message)
        self.query_generator_system_template_for_plan_rag=SystemMessagePromptTemplate.from_template(query_generator_system_message_for_plan_rag)
    
    # def query_generator(self,patient_background_information:str)->list[str]:
    #     response=self.llm.invoke(self.query_generator_system_template.format_messages(patient_background_information=patient_background_information))
    #     process_response=check_and_process_code_blocks(response.content,action="extract")
    #     try:
    #         result_json=json.loads(process_response)
    #         queries=result_json["queries"]
    #     except:
    #         queries=[]
    #     return queries

    def rag_information_filter(self,patient_background_information:str,rag_information:str,fine_grained_assessment_syndrome:str)->str:
        rag_information_filter_prompt=self.rag_information_filter_system_template.format_messages(patient_background_information=patient_background_information,rag_information=rag_information,fine_grained_assessment_syndrome=fine_grained_assessment_syndrome)
        response=self.llm.invoke(rag_information_filter_prompt)
        return response.content
    
    # def entity_extraction(self,patient_background_information:str)->list[str]:
    #     response=self.llm.invoke(self.entity_extraction_system_template.format_messages(patient_background_information=patient_background_information))
    #     process_response=check_and_process_code_blocks(response.content,action="extract")
    #     try:
    #         result_json=json.loads(process_response)
    #         entities=result_json["entities"]
    #     except:
    #         entities=[]
    #     return entities

    # def graph_search(self,entities:list[str])->list[str]:
    #     graph_searcher=GraphSearch()
    #     entities_str_list=[]
    #     for entity in entities:
    #         search_result=graph_searcher.search_relations_with_frequency(entity, depth=3,min_frequency=3)
    #         print(f"对于{entity}的搜索结果长度为{len(search_result)}")
    #         entity_str_list=[]
    #         for result in search_result:
    #             entity_str_list.append(f"{result['source']}{result['relation']}{result['target']}")
    #         entities_str_list.append(f"{entity}的相关结果:{entity_str_list}")
    #     return entities_str_list

    # def graph_filter_relation(self,patient_background_information:str,relation_graph:str)->str:
    #     graph_filter_prompt=self.graph_filter_system_template.format_messages(patient_background_information=patient_background_information,relation_graph=relation_graph)
    #     response=self.llm.invoke(graph_filter_prompt)
    #     return response.content
    
    # def graph_search_filter_chain(self,patient_background_information:str,chunk_size=5)->str:
    #     entities=self.entity_extraction(patient_background_information=patient_background_information)
    #     ColorPrinter.green("RagAgent:")
    #     ColorPrinter.white(f"已提取以下实体,准备进行知识图谱检索:\n{entities}")
        
    #     if len(entities) <= chunk_size:
    #         graph_search_result=self.graph_search(entities=entities)
    #         graph_filter_content=self.graph_filter_relation(patient_background_information=patient_background_information,relation_graph=graph_search_result)
    #         return graph_filter_content
    #     else:
    #         graph_filter_content_list=[]
    #         entities_in_list=[entities[i:i + chunk_size] for i in range(0, len(entities), chunk_size)]
    #         for entities_list in entities_in_list:
    #             one_turn_graph_search_result=self.graph_search(entities=entities_list)
    #             one_turn_graph_filter_content=self.graph_filter_relation(patient_background_information=patient_background_information,relation_graph=one_turn_graph_search_result)
    #             graph_filter_content_list.append(one_turn_graph_filter_content)
    #         graph_filter_summary_content=self.llm.invoke([HumanMessage(content=f"请你汇总以下资料:{graph_filter_content_list}")])
    #         return graph_filter_summary_content.content

    def web_search_syndrome(self,syndrome:str)->List[Dict[str,str]]:
        # response=self.llm.invoke(self.web_search_system_template.format_messages(patient_background_information=patient_background_information))
        serper_search=SerperSearch()
        # keyword_search_result, keyword_search_links=serper_search.serper_keyword_search(query=response.content)
        keyword_search_result, keyword_search_links=serper_search.serper_keyword_search(query=syndrome)
        web_pages=serper_search.serper_webpage_scraping(keyword_search_links)
        return web_pages
    
    def web_search_plan_rag(self,queries:list[str])->List[Dict[str,str]]:
        serper_search=SerperSearch()
        keyword_search_result_list=[]
        for query in queries:
            keyword_search_result, keyword_search_links=serper_search.serper_keyword_search(query=query)
            keyword_search_result_list.append(keyword_search_result)
        return keyword_search_result_list
    
    # def web_search_filter(self,patient_background_information:str,web_search_result:List[Dict[str,str]])->str:
    #     response=self.llm.invoke(self.web_search_filter_system_template.format_messages(patient_background_information=patient_background_information,web_search_result=web_search_result))
    #     return response.content
    
    def query_generator_for_plan_rag(self,fine_grained_assessment_syndrome:str,patient_background_information:str,plan_tasks:list[str])->list[str]:
        prompt=self.query_generator_system_template_for_plan_rag.format_messages(fine_grained_assessment_syndrome=fine_grained_assessment_syndrome,patient_background_information=patient_background_information,plan_tasks=plan_tasks)
        while True:
            response=self.llm.invoke(prompt)
            process_response=check_and_process_code_blocks(response.content,action="extract")
            try:
                result_json=json.loads(process_response)
                queries=result_json["query"]
            except:
                queries=[]
            # if len(plan_tasks)==len(queries):
            #     break
            # else:
            #     ColorPrinter.red("SystemMessage:")
            #     ColorPrinter.yellow("Query数量和任务数量不一致，正在重新生成")
            #     prompt.append(HumanMessage(content=f"Query数量应该为{len(plan_tasks)},请重新生成"))
            #     continue
            return queries
