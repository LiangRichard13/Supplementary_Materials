from agents.informationAgent.informationAgent import informationAgent
from agents.tongueCoatingAgent.tongueCoatingAgent import TongueCoatingAgent
from agents.syndromeAgent.syndromeAgent import SyndromeAgent
from agents.planAgent.planAgent import PlanAgent
from agents.draftingAgents.draftingAgents import InstructorAgent,ActorAgent,SummaryAgent
from agents.draftingAgents.drafting_config import chat_turn_limit
from agents.reportGenAgents.linksAddAgent import LinksAddAgent
from agents.reportGenAgents.reporGenAgent import ReportGenAgent
from agents.ragAgent.ragAgent import RagAgent
from tools.colorPrinter import ColorPrinter
from tools.rag.ragRetriever import Retriever
from tools.graph_rag.graph_search import GraphSearch
from langchain.schema import HumanMessage,SystemMessage,Document
from typing import List, Dict
import concurrent.futures
import json

class Runner:
    def __init__(self)->None:
        # 提前初始化informationAgent和syndromeAgent,避免在运行时重复初始化
        self.information_agent=informationAgent()
        self.syndrome_agent=SyndromeAgent()

    def run_tongue_coating(self, image_path:str)->str: # 运行舌苔诊断
        self.tongue_coating_agent = TongueCoatingAgent()
        return self.tongue_coating_agent.tongue_coating_diagnosis(image_path)
    
    def initial_rag_retriever(self)->None:
        ColorPrinter.red("SystemMessage: ")
        ColorPrinter.yellow("正在初始化RAG检索器...")
        self.retriever=Retriever()
        self.graph_search=GraphSearch()
        ColorPrinter.red("已加载RAG检索器")

    def run_information(self,informer_input:SystemMessage)->str: # 运行informationAgent,用于收集用户背景信息
        response=self.information_agent.get_response(informer_input)
        if "<CLINICAL_INTERVIEW_TASK_DONE>" in response.content:
                response=self.information_agent.get_summary(self.information_agent.history)
                return response.content
        
        ColorPrinter.green("InformationAgent: ")
        ColorPrinter.white(response.content)
        while True:
            user_input = input(ColorPrinter.color_text("User: ", "blue")) 
            # 记录输入
            ColorPrinter.log_info(f"用户输入: {user_input}")
            if user_input=="exit":
                break
            input_message=HumanMessage(content=user_input)
            response=self.information_agent.get_response(input_message)
            ColorPrinter.green("InformationAgent: ")
            ColorPrinter.white(response.content)
            if "<CLINICAL_INTERVIEW_TASK_DONE>" in response.content:
                response=self.information_agent.get_summary(self.information_agent.history)
                return response.content
    
    def three_stage_syndrome_differential(self,patient_info:str)->Dict[str,str]:
        diagnosis_chain_of_thought = []
        cases_information=self.retriever.get_medical_cases_information(patient_info)
        ColorPrinter.red("SystemMessage:")
        ColorPrinter.yellow(f"检索到相关医案:{cases_information}")
        try:
            initial_assessment_json=self.syndrome_agent.get_initial_assessment(patient_info,cases_information)
            ColorPrinter.green("SyndromeAgent:")
            ColorPrinter.white(f"已生成以下初步判断的证候:\n{initial_assessment_json}")

            initial_assessment_json=json.loads(initial_assessment_json)
            initital_assessment_syndrome=initial_assessment_json["syndrome"]
            diagnosis_chain_of_thought.append(initial_assessment_json["thinking"])

            similar_syndrome_json=self.syndrome_agent.get_similar_syndrome(patient_info,initital_assessment_syndrome)
            ColorPrinter.green("SyndromeAgent:")
            ColorPrinter.white(f"已生成以下相似证候:\n{similar_syndrome_json}")
            
            similar_syndrome_json=json.loads(similar_syndrome_json)
            similar_syndrome=similar_syndrome_json["syndrome"]
            diagnosis_chain_of_thought.append(similar_syndrome_json["thinking"])

            syndrome_graph_information_list=[]
            
            for syndrome in similar_syndrome:
                syndrome_graph_information=self.graph_search.search_relations(syndrome)
                syndrome_graph_information_list.append(syndrome_graph_information)

            ColorPrinter.red("SystemMessage:")
            ColorPrinter.yellow(f"检索到证候知识图谱:{syndrome_graph_information_list}")
            fine_grained_assessment_json=self.syndrome_agent.get_fine_grained_assessment(patient_info,syndrome_graph_information_list,similar_syndrome)
            
            ColorPrinter.green("SyndromeAgent:")
            ColorPrinter.white(f"已生成以下证候判断结果:\n{fine_grained_assessment_json}")

            # 解析大模型的
            fine_grained_assessment_json=json.loads(fine_grained_assessment_json)
            fine_grained_syndrome=fine_grained_assessment_json["syndrome"]
            diagnosis_chain_of_thought.append(fine_grained_assessment_json["thinking"])

            # 如果不需要更多信息则清除该agent的推理历史
            if fine_grained_assessment_json["need_more_information"]=="false":
                self.syndrome_agent.clear_history()

            return fine_grained_assessment_json, diagnosis_chain_of_thought

        except Exception as e:
            ColorPrinter.red("SyndromeAgent:")
            ColorPrinter.white(f"出现错误:{e}")
            self.syndrome_agent.clear_history()
            return 'None'


    def run_rag_agent(self,fine_grained_assessment_syndrome:str,patient_background_information:str,plan_tasks:list[str])->Dict[str,any]:
        self.rag_agent=RagAgent()
        
        ColorPrinter.red("SystemMessage:")
        ColorPrinter.yellow("正在并行RAG检索相关参考资料...")
        
        def run_plan_rag():
            # 生成任务匹配的查询:通过任务改写得到多个query并进行网络查询
            queries=self.rag_agent.query_generator_for_plan_rag(fine_grained_assessment_syndrome=fine_grained_assessment_syndrome,patient_background_information=patient_background_information,plan_tasks=plan_tasks)
            ColorPrinter.green("RagAgent:")
            ColorPrinter.white(f"已生成以下任务匹配的查询:\n{queries}")
            # plan_rag_info=self.retriever.get_chroma_based_batch_relevant_documents(queries)
            # return plan_rag_info
            return self.rag_agent.web_search_plan_rag(queries)

        # def run_unstructured_rag():
        #     # 生成查询
        #     queries=self.rag_agent.query_generator_for_plan_rag(patient_background_information=patient_background_information,plan_tasks=plan_tasks)
        #     ColorPrinter.green("RagAgent:")
        #     ColorPrinter.white(f"已生成以下多角度辩证查询:\n{queries}")
        #     # 用于提供查询的多样性,多角度辩证思维
        #     supplement_info = self.retriever.multi_query_with_two_stage_rerank_chain(
        #         original_query=patient_background_information,
        #         queries=queries
        #     )
        #     # 过滤补充的非结构化参考资料
        #     filter_supplement = self.rag_agent.rag_information_filter(
        #         patient_background_information=patient_background_information,
        #         rag_information=supplement_info
        #     )
        #     return filter_supplement
            
        # 直接通过用户的主诉信息进行rag查询    
        def run_direct_rag():
            # 用于保证查询的准确性,整体辩证思维
            direct_info= self.retriever.get_tcm_texts_documents_with_rerank(
                query=patient_background_information
            )
            # 过滤直接检索到的非结构化参考资料
            filter_direct = self.rag_agent.rag_information_filter(
                patient_background_information=patient_background_information,
                rag_information=direct_info,
                fine_grained_assessment_syndrome=fine_grained_assessment_syndrome
            )
            return filter_direct
            
        # 知识图谱用于查询用户确诊的证候 
        def run_graph_search():
            return self.graph_search.search_relations(
                fine_grained_assessment_syndrome
            )
        
        # 网络检索证候相关信息
        def run_web_search():
            return  self.rag_agent.web_search_syndrome(
                syndrome=fine_grained_assessment_syndrome
            )
            # return self.rag_agent.web_search_filter(
            #     web_search_result=web_pages,
            #     patient_background_information=patient_background_information
            # )
        
        # 使用ThreadPoolExecutor并行执行所有检索任务
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 提交所有任务
            future_to_task = {
                # executor.submit(run_unstructured_rag): "supplement",
                executor.submit(run_direct_rag): "direct",
                executor.submit(run_graph_search): "graph",
                executor.submit(run_web_search): "web",
                executor.submit(run_plan_rag): "plan"
            }
            
            # 收集结果
            results = {}
            for future in concurrent.futures.as_completed(future_to_task):
                task_name = future_to_task[future]
                try:
                    result = future.result()
                    results[task_name] = result
                    
                    # 打印进度
                    # if task_name == "supplement":
                    #     ColorPrinter.green("RagAgent:")
                    #     ColorPrinter.white(f"已过滤以下补充的非结构化参考资料:\n{result}")
                    if task_name == "direct":
                        ColorPrinter.green("RagAgent:")
                        ColorPrinter.white(f"已检索到以下非结构化参考资料:\n{result}")
                    elif task_name == "graph":
                        ColorPrinter.green("RagAgent:")
                        ColorPrinter.white(f"已检索到以下关系:\n{result}")
                    elif task_name == "web":
                        ColorPrinter.green("RagAgent:")
                        ColorPrinter.white(f"已从网络检索出以下相关内容:\n{result}")
                    elif task_name == "plan":
                        ColorPrinter.green("RagAgent:")
                        ColorPrinter.white(f"已检索到以下任务匹配的参考资料:\n{result}")

                except Exception as e:
                    ColorPrinter.red(f"任务 {task_name} 执行出错: {e}")
                    results[task_name] = ""
        
        base_rag_information = {
            "非结构化资料:": results["direct"],
            "知识图谱检索资料": results["graph"],
            "网络检索资料": results["web"]
        }
        plan_rag_information=results["plan"]

        return base_rag_information,plan_rag_information

    def run_plan_agent(self,patient_background_information:str,fine_grained_assessment_syndrome_json:dict)->list[str]: # 运行PlanAgent
        self.plan_agent=PlanAgent(patient_background_information,fine_grained_assessment_syndrome_json)
        plan_tasks=self.plan_agent.get_plan()
        return plan_tasks

    def run_actor_agent(self,input_message:str)->HumanMessage:
        actor_ai_msg=self.actor_agent.step(HumanMessage(content=input_message))
        actor_msg=HumanMessage(content=actor_ai_msg.content)
        ColorPrinter.green("ActorAgent: ")
        ColorPrinter.white(actor_msg.content)
        return actor_msg
    
    def run_instructor_agent(self,input_message:str)->HumanMessage:
        instructor_ai_msg=self.instructor_agent.step(HumanMessage(content=input_message)) 
        instructor_msg=HumanMessage(content=instructor_ai_msg.content)
        ColorPrinter.green("InstructorAgent: ")
        ColorPrinter.white(instructor_msg.content)
        return instructor_msg   
    
    def run_drafting_agents(self,patient_background_information:str,fine_grained_assessment_syndrome_json:dict,plan_tasks:list,base_rag_information:Dict[str,any],plan_rag_information:List[Dict[str,str]])->List[Dict[str, str]]: # actor和instructor的对话
        def process_task(task, task_rag_info, task_index):
            ColorPrinter.red("SystemMessage:")
            ColorPrinter.yellow(f"开始并行任务:{task}")
            
            # 为每个任务创建新的agent实例
            task_actor_agent = ActorAgent(patient_background_information+'\n以下是患者确诊的证候:\n'+str(fine_grained_assessment_syndrome_json))
            task_instructor_agent = InstructorAgent(patient_background_information+'\n以下是患者确诊的证候:\n'+str(fine_grained_assessment_syndrome_json))

            # 在任务开始前，将参考资料加入到actor_agent的对话中
            task_actor_agent.update_message(SystemMessage(content=f"以下是参考资料:\n{base_rag_information},如果在执行任务过程中用到了以上资料，请引用参考资料原文,并标注参考资料来源(如:来自脉症治方,来自续名医类案,来自知识图谱检索,来自网络检索等)"))
            task_actor_agent.update_message(SystemMessage(content=f"以下是任务匹配的参考资料:\n{task_rag_info},如果在执行任务过程中用到了以上资料，请引用参考资料原文,并标注参考资料来源(如:来自脉症治方,来自续名医类案等)"))

            # 将参考资料加入到instructor_agent的对话中
            task_instructor_agent.update_message(SystemMessage(content=f"以下是参考资料:\n{base_rag_information},如果在指导我执行任务过程中用到了以上资料，请引用参考资料原文,并标注参考资料来源(如:来自脉症治方,来自续名医类案,来自知识图谱检索,来自网络检索等)"))
            task_instructor_agent.update_message(SystemMessage(content=f"以下是任务匹配的参考资料:\n{task_rag_info},如果在指导我执行任务过程中用到了以上资料，请引用参考资料原文,并标注参考资料来源(如:来自脉症治方,来自续名医类案等)"))

            dialogue_content = []
            
            # 运行actor_agent，但使用task特定的实例
            actor_ai_msg = task_actor_agent.step(HumanMessage(content=f"现在开始我们的任务:{task}"))
            actor_msg = HumanMessage(content=actor_ai_msg.content)
            ColorPrinter.green(f"ActorAgent (任务{task_index}):")
            ColorPrinter.white(actor_msg.content)
            dialogue_content.append({"role":"actor","content":actor_msg.content})
            
            n = 0
            while n < chat_turn_limit:
                # 运行instructor_agent，但使用task特定的实例
                instructor_ai_msg = task_instructor_agent.step(HumanMessage(content=f"这是我的任务:{task}\n\n这是我的内容{actor_msg.content}\n\n"))
                instructor_msg = HumanMessage(content=instructor_ai_msg.content)
                ColorPrinter.green(f"InstructorAgent (任务{task_index}):")
                ColorPrinter.white(instructor_msg.content)
                dialogue_content.append({"role":"instructor","content":instructor_msg.content})
                
                if "<CAMEL_TASK_DONE>" in instructor_msg.content:
                    ColorPrinter.red("SystemMessage:")
                    ColorPrinter.yellow(f"并行任务完成:{task}")
                    summary_content=self.return_summary_content(task,dialogue_content)
                    ColorPrinter.green(f"SummaryAgent (任务{task_index}):")
                    ColorPrinter.white(summary_content)
                    return {"task": task, "summary": summary_content, "index": task_index}
                
                # 运行actor_agent，但使用task特定的实例
                actor_ai_msg = task_actor_agent.step(HumanMessage(content=instructor_msg.content))
                actor_msg = HumanMessage(content=actor_ai_msg.content)
                ColorPrinter.green(f"ActorAgent (任务{task_index}):")
                ColorPrinter.white(actor_msg.content)
                dialogue_content.append({"role":"actor","content":actor_msg.content})
                n += 1
            
            # 超过交互次数限制，结束任务
            if n >= chat_turn_limit:
                ColorPrinter.red("SystemMessage:")
                ColorPrinter.yellow(f"并行任务完成(达到交互限制):{task}")
                summary_content=self.return_summary_content(task,dialogue_content)
                ColorPrinter.green(f"SummaryAgent (任务{task_index}):")
                ColorPrinter.white(summary_content)
                return {"task": task, "summary": summary_content, "index": task_index}
        
        # 使用ThreadPoolExecutor并行处理所有任务
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 同时遍历plan_tasks和plan_rag_information
            future_to_task = {executor.submit(process_task, task, plan_rag_information, i): i 
                             for i, task in enumerate(plan_tasks)}
            parallel_results = {}
            
            for future in concurrent.futures.as_completed(future_to_task):
                task_index = future_to_task[future]
                try:
                    result = future.result()
                    parallel_results[result["index"]] = result["summary"]
                except Exception as e:
                    ColorPrinter.red(f"任务 {plan_tasks[task_index]} 生成错误: {e}")
        
        # 按照原始plan_tasks的顺序整理结果
        summary_content_list = []
        for i in range(len(plan_tasks)):
            if i in parallel_results:
                summary_content_list.append(parallel_results[i])
            else:
                # 如果某个任务失败，添加空字符串占位
                summary_content_list.append("")
                
        drafting_result=[{"task":task,"answer":one_turn_content} for task,one_turn_content in zip(plan_tasks,summary_content_list)]
        ColorPrinter.red("SystemMessage:")
        ColorPrinter.yellow(f"以下是所有任务执行内容:{str(drafting_result)}")
        return drafting_result
    
    def run_summary_agent(self,one_task_dialogue:List[Dict[str,str]],task:str)->str: 
        self.summary_agent=SummaryAgent(one_task_dialogue,task)
        input_message=HumanMessage(content=f"请输出:")
        summary_content=self.summary_agent.step(input_message)
        return summary_content.content
    
    def add_to_summary_list(self,task:str,dialogue_content:List[Dict[str,str]],summary_content_list:list[str])->list[str]:
        summary_content=self.run_summary_agent(dialogue_content,task)
        ColorPrinter.green("SummaryAgent: ")
        ColorPrinter.white(summary_content)
        summary_content_list.append(summary_content)
        return summary_content_list
    
    def return_summary_content(self,task:str,dialogue_content:List[Dict[str,str]])->str:
        summary_content=self.run_summary_agent(dialogue_content,task)
        ColorPrinter.green("SummaryAgent: ")
        ColorPrinter.white(summary_content)
        return summary_content

    def run_links_add_agent(self,drafting_result:List[Dict[str,str]])->dict: 
        self.links_add_agent=LinksAddAgent()
        main_content=""
        for content in drafting_result:
            main_content += content["answer"]+"\n"
        search_reference=self.links_add_agent.add_links(main_content)
        return search_reference

    def run_report_gen_agent(
            self,
            patient_background_information:str, # 患者背景信息
            main_content:List[Dict[str,str]], # 主要内容
            tongue_coating_image_path:str, # 舌苔图片路径
            tongue_coating_diagnosis:str, # 舌苔诊断结果
            search_reference:Dict[str,str] # 搜索参考
            )->str: # 运行ReportGenAgent
        self.report_gen_agent=ReportGenAgent()
        self.report_gen_agent.init_meta_data_system_message(
            patient_background_information=patient_background_information,
            tongue_coating_image_path=tongue_coating_image_path,
            tongue_coating_diagnosis=tongue_coating_diagnosis
        ) # 将患者的舌苔诊断结果、舌苔图片路径、患者背景信息作为初始化信息
        # 先生成报告的第一部分（患者背景信息、舌苔诊断等）
        report_content=self.report_gen_agent.get_content()
        ColorPrinter.green("ReportGenAgent:")
        ColorPrinter.white(report_content)
        
        # 如果只有一个内容项，则直接顺序处理
        if len(main_content) <= 1:
            for index, content in enumerate(main_content):
                # 将当前内容作为初始化信息
                self.report_gen_agent.init_main_content_system_message(main_content=content) 
                # 添加参考资料
                self.report_gen_agent.add_reference_to_history(index,search_reference)
                # 生成内容
                new_report_content=self.report_gen_agent.get_content()
                ColorPrinter.green("ReportGenAgent:")
                ColorPrinter.white(new_report_content)
                report_content = report_content+'\n\n'+ new_report_content
        else:
            # 并行生成报告的其他部分
            def generate_report_content(content_item, index):
                ColorPrinter.red("SystemMessage:")
                ColorPrinter.yellow(f"并行生成报告内容，主题:{content_item['task']}")
                
                # 为每个内容创建新的ReportGenAgent实例
                report_agent = ReportGenAgent()
                # 初始化背景信息
                report_agent.init_meta_data_system_message(
                    patient_background_information=patient_background_information,
                    tongue_coating_image_path=tongue_coating_image_path,
                    tongue_coating_diagnosis=tongue_coating_diagnosis
                )
                # 初始化主要内容
                report_agent.init_main_content_system_message(main_content=content_item)
                # 添加参考资料
                report_agent.add_reference_to_history(index, search_reference)
                # 生成内容
                content = report_agent.get_content()
                ColorPrinter.green("ReportGenAgent (并行):")
                ColorPrinter.white(content)
                return {"index": index, "content": content}
            
            # 使用ThreadPoolExecutor并行处理报告内容生成
            report_contents = {}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # 多线程生成报告的剩余部分
                future_to_index = {executor.submit(generate_report_content, content, i): i 
                                  for i, content in enumerate(main_content)}
                
                for future in concurrent.futures.as_completed(future_to_index):
                    index = future_to_index[future]
                    try:
                        result = future.result()
                        report_contents[result["index"]] = result["content"]
                    except Exception as e:
                        ColorPrinter.red(f"生成报告内容 {index} 时出错: {e}")
            
            # 按照原始main_content的顺序添加内容
            for i in range(len(main_content)):
                if i in report_contents:
                    report_content = report_content + '\n\n' + report_contents[i]
        # 最后生成总结
        self.report_gen_agent.init_report_summary_system_message(report_content)
        report_summary=self.report_gen_agent.get_content()
        ColorPrinter.green("ReportGenAgent:")
        ColorPrinter.white(report_summary)
        report_content=report_content+'\n\n'+report_summary
        save_path=self.report_gen_agent.save_report(report_content)
        return save_path
