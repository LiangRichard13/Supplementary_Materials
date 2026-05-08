from agents.planAgent.plan_config import system_prompt_template,treatment_plan
from langchain.prompts import SystemMessagePromptTemplate
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from tools.colorPrinter import ColorPrinter
from agents.agents_model_config import PLAN_AGENT_BASE_URL,PLAN_AGENT_MODEL,PLAN_AGENT_API_KEY

class PlanAgent:
    def __init__(self,patient_background_information:str,fine_grained_assessment_syndrome_json:dict)->None:
        self.llm = ChatOpenAI(base_url=PLAN_AGENT_BASE_URL, model=PLAN_AGENT_MODEL, api_key=PLAN_AGENT_API_KEY)
        system_message_template=SystemMessagePromptTemplate.from_template(system_prompt_template)
        self.system_message=system_message_template.format_messages(
        patient_background_information=patient_background_information,
        fine_grained_assessment_syndrome_json=fine_grained_assessment_syndrome_json,
        treatment_plan=treatment_plan)[0]
        self.history=[self.system_message]

    def get_plan(self)->list[str]: #获取计划
        while True:
            response=self.llm.invoke(self.history)
            plan_tasks = response.content.split("<TASK_SPLIT>")
            if len(plan_tasks)==len(treatment_plan):
                break
            else:
                ColorPrinter.red("SystemMessage:")
                ColorPrinter.yellow("任务数量和计划不一致，正在重新生成")
                self.history.append(HumanMessage(content=f"任务数量应该为{len(treatment_plan)},请重新生成"))
                continue
        return plan_tasks