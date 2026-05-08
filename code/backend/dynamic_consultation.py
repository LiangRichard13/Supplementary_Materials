from agentsRunner import Runner
from langchain_core.messages import SystemMessage
from tools.colorPrinter import ColorPrinter
import json

def run_chain(runner)->str: # 运行整个链路
    # 初始化日志系统
    ColorPrinter.init_logging(log_dir="logs",log_level="INFO")
    # 初始化rag检索器
    runner.initial_rag_retriever()

    ColorPrinter.green("TongueCoatingAgent:")
    ColorPrinter.white("请输入舌苔图片路径:")
    image_path = input(ColorPrinter.color_text("User: ", "blue"))
    # 记录输入
    ColorPrinter.log_info(f"用户输入的舌苔图片路径: {image_path}")

    # 运行舌苔诊断
    tongue_coating_diagnosis_content=runner.run_tongue_coating(image_path)
    ColorPrinter.green("TongueCoatingAgent:")
    ColorPrinter.white(tongue_coating_diagnosis_content)

    # 运行InformationAgent
    patient_background_information=runner.run_information(
    SystemMessage(
        content=f"""
        以下是用户上传的舌苔图片的诊断结果：{tongue_coating_diagnosis_content}\n
        在经过多轮对话后，你需要在患者信息描述中加入患者舌苔的特征和可能的健康问题(结合患者信息进一步缩小范围)。\n
        """
        ))
    
    ColorPrinter.red("SystemMessage:")
    ColorPrinter.yellow(f"PatientBackgroundInformation:{patient_background_information}")
 
    from test_data import patient_background_information,image_path,tongue_coating_diagnosis_content
    
    chat_turn_limit = 5 # 对话轮次限制
    while chat_turn_limit>0:

        # 运行SyndromeAgent
        fine_grained_assessment_syndrome_json, diagnosis_chain_of_thought=runner.three_stage_syndrome_differential(patient_background_information)
        ColorPrinter.green("SyndromeAgent:")
        ColorPrinter.white(fine_grained_assessment_syndrome_json)

        if fine_grained_assessment_syndrome_json["need_more_information"]=="false":
            break
        else:
            chat_turn_limit-=1
            if fine_grained_assessment_syndrome_json["needed_information"]:
                # 如果需要更多信息,则继续追问
                runner.information_agent.init_message_ask()
                patient_background_information=runner.run_information(SystemMessage(content=f"以下是现有的患者信息:\n{patient_background_information}\n还需要患者提供以下信息:{fine_grained_assessment_syndrome_json['needed_information']},请继续追问(同样以<CLINICAL_INTERVIEW_TASK_DONE>结束):"))
                ColorPrinter.red("SystemMessage:")
                ColorPrinter.yellow(f"PatientBackgroundInformation:{patient_background_information}")

    fine_grained_assessment_syndrome=fine_grained_assessment_syndrome_json["syndrome"]


    # 运行PlanAgentww
    plan_tasks=runner.run_plan_agent(patient_background_information,fine_grained_assessment_syndrome_json)
    ColorPrinter.green("PlanAgent:")
    ColorPrinter.white(str(plan_tasks))

    # 运行RagAgent
    base_rag_information,plan_rag_information=runner.run_rag_agent(fine_grained_assessment_syndrome,patient_background_information,plan_tasks)
    
    ColorPrinter.red("SystemMessage:")
    ColorPrinter.yellow(f"BaseRagInformation:{base_rag_information}")
    ColorPrinter.yellow(f"PlanRagInformation:{plan_rag_information}")

    # 运行actor和instructor的对话
    drafting_result=runner.run_drafting_agents(patient_background_information,fine_grained_assessment_syndrome_json,plan_tasks,base_rag_information,plan_rag_information)

    ColorPrinter.red("SystemMessage:")
    ColorPrinter.yellow("正在网络搜索参考内容...")
    search_reference=runner.run_links_add_agent(drafting_result=drafting_result)
    ColorPrinter.green("LinksAddAgent:")
    ColorPrinter.white(str(search_reference))

    ColorPrinter.red("SystemMessage:")
    ColorPrinter.yellow("正在生成报告...")
    # 生成报告
    save_path=runner.run_report_gen_agent(
        patient_background_information=patient_background_information,
        main_content=drafting_result,
        tongue_coating_image_path=image_path,
        tongue_coating_diagnosis=tongue_coating_diagnosis_content,
        search_reference=search_reference
        )
    return save_path

if __name__ == "__main__":
    runner = Runner()
    run_chain(runner)