from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage,BaseMessage,HumanMessage,AIMessage
from langchain_core.prompts import SystemMessagePromptTemplate
from agents.informationAgent.information_config import system_message_ask,system_message_summary
from agents.agents_model_config import INFORMATION_AGENT_BASE_URL,INFORMATION_AGENT_MODEL,INFORMATION_AGENT_API_KEY
from typing import List,Dict

class informationAgent:
    def __init__(self)->None:
        self.llm=ChatOpenAI(base_url=INFORMATION_AGENT_BASE_URL,model=INFORMATION_AGENT_MODEL,api_key=INFORMATION_AGENT_API_KEY) #用于创建LLM实例
        self.system_message_ask=SystemMessage(content=system_message_ask) #用于创建系统消息
        self.system_message_summary_template=SystemMessagePromptTemplate.from_template(template=system_message_summary)
        self.history=[self.system_message_ask]  #用于存储对话历史, 使用系统消息初始化

    def init_message_ask(self)->None:
        self.history=[self.system_message_ask]  #使用系统消息初始化

    def update_history(self,input_message:BaseMessage)->list[BaseMessage]:
        self.history.append(input_message) #更新对话历史
        return self.history #返回对话历史
    
    def get_response(self,input_message:BaseMessage)->AIMessage: #获取响应
        if self.history==[]:
            self.init_message_ask()
        self.history=self.update_history(input_message)
        response=self.llm.invoke(self.history)
        self.update_history(response)
        return response
    
    def get_summary(self,information_dialogue:List[BaseMessage])->AIMessage:
        llm=ChatOpenAI(base_url=INFORMATION_AGENT_BASE_URL,model=INFORMATION_AGENT_MODEL,api_key=INFORMATION_AGENT_API_KEY) #用于创建Summary LLM实例
        history=self.system_message_summary_template.format_messages(information_dialogue=information_dialogue)
        summary=llm.invoke(history)
        return summary