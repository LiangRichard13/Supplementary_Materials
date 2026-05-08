from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage,HumanMessage
from agents.reportGenAgents.reportGen_config import links_add_agent_system_message
from tools.process_code_blocks import check_and_process_code_blocks
from tools.search.serper_search import SerperSearch
from tools.search.baidu_search import BaiduSearch
from tools.colorPrinter import ColorPrinter
from agents.agents_model_config import LINKS_AGENT_BASE_URL,LINKS_AGENT_MODEL,LINKS_AGENT_API_KEY
from typing import Dict
import json
import concurrent.futures   

class LinksAddAgent:
    def __init__(self)->None:
        self.llm = ChatOpenAI(base_url=LINKS_AGENT_BASE_URL, model=LINKS_AGENT_MODEL, api_key=LINKS_AGENT_API_KEY)
        self.system_message=SystemMessage(content=links_add_agent_system_message)
        self.history=[self.system_message]

    def add_links(self,main_content:str)->Dict[str,str]:
        self.history.append(HumanMessage(content=f"请你从以下内容中提取:{main_content}\n 下面请直接输出json格式内容，请直接输出可解析的json源码，不要用```json或```包裹输出。"))
        response=self.llm.invoke(self.history)
        response_content=response.content
        # 再次检查处理是否存在```json```包裹的json字符串
        processed_content=check_and_process_code_blocks(text=response_content,action="extract")
        ColorPrinter.green("LinksAddAgent:")
        ColorPrinter.white(processed_content)
        try:
            # 解析JSON字符串为Python字典
            data = json.loads(processed_content)

            # 提取herbs、acupoints和keywords
            terms=data['terms'] # 获取terms列表
            herbs = data['herbs']  # 获取herbs列表
            acupoints = data['acupoints']  # 获取acupoints列表
            keyword = data['keyword']  # 获取keywords字符串

            serper_searcher=SerperSearch()
            baidu_searcher=BaiduSearch()

            # 使用并行执行搜索任务
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                # 提交所有搜索任务
                terms_future = executor.submit(serper_searcher.serper_search, terms)
                herbs_future = executor.submit(serper_searcher.serper_search, herbs)
                herbs_image_future = executor.submit(serper_searcher.serper_image_search, herbs)
                acupoints_future = executor.submit(serper_searcher.serper_search, acupoints)
                keyword_search_future = executor.submit(serper_searcher.serper_keyword_search, keyword)
                
                terms_search_result = terms_future.result()
                herbs_search_result = herbs_future.result()
                herbs_image_search_result = herbs_image_future.result()
                acupoints_search_result = acupoints_future.result()
                keyword_search_result, keyword_search_links = keyword_search_future.result()
                
                # 由于keyword_search_details依赖于keyword_search_links，需要在获得links后再执行
                # keyword_search_details = serper_searcher.serper_webpage_scraping(keyword_search_links)

            all_search_result={
                "terms_search_result":f"以下是中医术语搜索结果:\n{terms_search_result}",
                "herbs_search_result":f"以下是中药材搜索结果:\n{herbs_search_result}",
                "herbs_image_search_result":f"以下是中药材图片链接的搜索结果:\n{herbs_image_search_result}",
                "acupoints_search_result":f"以下是穴位搜索结果:\n{acupoints_search_result}",
                "keyword_search_result":f"以下是关于\"{keyword}\"的搜索结果:\n{keyword_search_result}"
                # "keyword_search_details":f"以下是关于\"{keyword}\"的搜索结果的详细内容:\n{keyword_search_details}"
                }
            ColorPrinter.red("SystemMessage:")
            ColorPrinter.yellow(f"搜索结果: {all_search_result}")

            return all_search_result
        
        except Exception as e:
            ColorPrinter.red("SystemMessage:")
            ColorPrinter.yellow(f"解析响应结果出错: {e}")
            all_search_result={
                "terms_search_result":"没有找到相关内容，请直接生成markdown文档",
                "herbs_search_result":"没有找到相关内容，请直接生成markdown文档",
                "herbs_image_search_result":"没有找到相关内容，请直接生成markdown文档",
                "acupoints_search_result":"没有找到相关内容，请直接生成markdown文档",
                "keyword_search_result":"没有找到相关内容，请直接生成markdown文档"
                    }
            return all_search_result

