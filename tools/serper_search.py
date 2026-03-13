import http.client
import json
from dotenv import load_dotenv
from typing import List,Dict
import os 
load_dotenv()

class SerperSearch:
    def __init__(self)->None:
        self.api_key=os.getenv("")
        
    def serper_search(self,query_list:list[str])->List[Dict[str,any]]: # 用于执行serper批量搜索
        conn = http.client.HTTPSConnection("google.serper.dev")
        processed_query_list=[{
            "q": query,
            "gl": "cn",
            "hl": "zh-cn"
        } for query in query_list]
        payload = json.dumps(processed_query_list)
        headers = {
        'X-API-KEY': self.api_key,
        'Content-Type': 'application/json'
        }
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = res.read()
        processed_search_result=[]
        
        try:
            response_data = json.loads(data.decode("utf-8"))
            # 检查响应是否为数组
            if isinstance(response_data, list):
                for search_result in response_data:
                    if 'organic' in search_result and len(search_result['organic']) > 0:
                        processed_search_result.append(search_result['organic'][0])
                    else:
                        # 如果没有organic结果，创建一个空结果
                        processed_search_result.append({"title": "无搜索结果", "link": "", "snippet": ""})
            else:
                # 如果响应不是数组，可能是单个结果
                if 'organic' in response_data and len(response_data['organic']) > 0:
                    processed_search_result.append(response_data['organic'][0])
                else:
                    processed_search_result.append({"title": "无搜索结果", "link": "", "snippet": ""})
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"解析搜索结果时出错: {e}")
            # 为每个查询创建空结果
            processed_search_result = [{"title": "无搜索结果", "link": "", "snippet": ""} for _ in query_list]
        
        all_search_result=[{"item":item,"item_search_result":item_search_result} for item,item_search_result in zip(query_list,processed_search_result)]
        return all_search_result
    
    def serper_keyword_search(self,query:str)->tuple[Dict[str,any],List[str]]: # 用于执行serper关键字搜索
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps(
            {
            "q": query,
            "gl": "cn",
            "hl": "zh-cn"
            }
        )
        headers = {
        'X-API-KEY': self.api_key,
        'Content-Type': 'application/json'
        }
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = res.read()
        processed_search_result=[]
        search_links=[]
        
        try:
            response_data=json.loads(data.decode("utf-8"))
            if 'organic' in response_data and len(response_data['organic']) > 0:
                for search_result in response_data['organic'][:5]: #获取前5个搜索结果
                    processed_search_result.append(search_result)
                    search_links.append(search_result["link"])
            else:
                # 如果没有搜索结果，创建空结果
                processed_search_result = [{"title": "无搜索结果", "link": "", "snippet": ""}]
                search_links = [""]
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"解析关键字搜索结果时出错: {e}")
            processed_search_result = [{"title": "无搜索结果", "link": "", "snippet": ""}]
            search_links = [""]
        
        all_search_result={"item":query,"item_search_result":processed_search_result}
        return all_search_result,search_links
    
    def serper_image_search(self,query_list:list[str])->List[Dict[str,any]]: # 用于执行serper图片搜索
        conn = http.client.HTTPSConnection("google.serper.dev")
        processed_query_list=[{
            "q": query,
            "gl": "cn",
            "hl": "zh-cn"
        } for query in query_list]
        payload = json.dumps(processed_query_list)
        headers = {
        'X-API-KEY': self.api_key,
        'Content-Type': 'application/json'
        }
        conn.request("POST", "/images", payload, headers)
        res = conn.getresponse()
        data = res.read()
        processed_search_result=[]
        
        try:
            response_data = json.loads(data.decode("utf-8"))
            # 检查响应是否为数组
            if isinstance(response_data, list):
                for search_result in response_data:
                    if 'images' in search_result and len(search_result['images']) > 0:
                        processed_search_result.append(search_result['images'][0]['imageUrl'])
                    else:
                        # 如果没有图片结果，创建一个空结果
                        processed_search_result.append("")
            else:
                # 如果响应不是数组，可能是单个结果
                if 'images' in response_data and len(response_data['images']) > 0:
                    processed_search_result.append(response_data['images'][0]['imageUrl'])
                else:
                    processed_search_result.append("")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"解析图片搜索结果时出错: {e}")
            # 为每个查询创建空结果
            processed_search_result = ["" for _ in query_list]
        
        all_search_result=[{"item":item,"item_image_search_result":item_search_result} for item,item_search_result in zip(query_list,processed_search_result)]
        return all_search_result
    
    def serper_webpage_scraping(self,links_list:List[str])->List[Dict[str,str]]:
        conn = http.client.HTTPSConnection("scrape.serper.dev")
        all_results=[]
        for link in links_list[:3]:
            payload = json.dumps({
            "url": link,
            })
            headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
            }
            conn.request("POST", "/", payload, headers)
            res = conn.getresponse()
            data = res.read()
            response_data=json.loads(data.decode("utf-8"))
            one_result={"link":link,"content":response_data}
            all_results.append(one_result)
        return all_results
    
    