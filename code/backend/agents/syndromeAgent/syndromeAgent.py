from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage
from agents.syndromeAgent.syndrome_agent_config import syndrome_agent_initial_assessment_system_message,syndrome_agent_fine_grained_assessment_system_message,syndrome_list,syndrome_agent_similar_syndrome_assessment_system_message
from tools.process_code_blocks import check_and_process_code_blocks
from tools.colorPrinter import ColorPrinter
from agents.syndromeAgent.syndrome_classifier import SyndromeClassifier
from agents.agents_model_config import SYNDROME_AGENT_BASE_URL,SYNDROME_AGENT_MODEL,SYNDROME_AGENT_API_KEY

class SyndromeAgent:
    def __init__(self)->None:
        self.llm = ChatOpenAI(base_url=SYNDROME_AGENT_BASE_URL, model=SYNDROME_AGENT_MODEL, api_key=SYNDROME_AGENT_API_KEY)
        self.syndrome_agent_initial_assessment_system_message_template = ChatPromptTemplate.from_template(syndrome_agent_initial_assessment_system_message)
        self.syndrome_agent_fine_grained_assessment_system_message_template = ChatPromptTemplate.from_template(syndrome_agent_fine_grained_assessment_system_message)
        self.syndrome_agent_similar_syndrome_assessment_system_message_template = ChatPromptTemplate.from_template(syndrome_agent_similar_syndrome_assessment_system_message)
        self.history = [HumanMessage(content=f"你选择的证候应当来自以下证候：{syndrome_list}")]

    def get_initial_assessment(self,patient_background_information:str,syndrome_information:str)->str:
        syndrome_agent_initial_assessment_system_prompt = self.syndrome_agent_initial_assessment_system_message_template.format_messages(
            patient_background_information=patient_background_information,
            syndrome_information=syndrome_information
        )[0]
        self.history.append(syndrome_agent_initial_assessment_system_prompt)
        response = self.llm.invoke(self.history)
        self.history.append(response)
        return check_and_process_code_blocks(response.content,action="extract")
    
    def get_similar_syndrome(self,patient_background_information:str,initital_assessment_syndrome:list)->str:
        syndrome_classifier = SyndromeClassifier()
        similar_syndrome_dict = syndrome_classifier.classify_syndromes(initital_assessment_syndrome)
        ColorPrinter.red("SystemMessage:")
        ColorPrinter.yellow(f"找到相关证候:{similar_syndrome_dict}")
        syndrome_agent_similar_syndrome_assessment_system_prompt = self.syndrome_agent_similar_syndrome_assessment_system_message_template.format_messages(
            patient_background_information=patient_background_information,
            initital_assessment_syndrome=initital_assessment_syndrome,
            similar_syndrome_information=similar_syndrome_dict
        )[0]
        self.history.append(syndrome_agent_similar_syndrome_assessment_system_prompt)
        response = self.llm.invoke(self.history)
        self.history.append(response)
        return check_and_process_code_blocks(response.content,action="extract")
    
    def get_fine_grained_assessment(self,patient_background_information:str,syndrome_graph_information:str,initital_assessment_syndrome:list)->str:
        syndrome_agent_fine_grained_assessment_system_prompt = self.syndrome_agent_fine_grained_assessment_system_message_template.format_messages(
            patient_background_information=patient_background_information,
            syndrome_graph_information=syndrome_graph_information,
            initital_assessment_syndrome=initital_assessment_syndrome
        )[0]
        self.history.append(syndrome_agent_fine_grained_assessment_system_prompt)
        response = self.llm.invoke(self.history)
        self.history.append(response)
        return check_and_process_code_blocks(response.content,action="extract")

    def clear_history(self)->list:
        self.history = [HumanMessage(content=f"你选择的证候应当来自以下证候：{syndrome_list}")]
