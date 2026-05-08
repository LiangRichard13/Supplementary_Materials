from test_data import patient_background_information,image_path,tongue_coating_diagnosis_content
from agentsRunner import Runner
from langchain_core.messages import SystemMessage
from tools.colorPrinter import ColorPrinter
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from agents.agents_model_config import INFORMATION_AGENT_BASE_URL,INFORMATION_AGENT_MODEL,INFORMATION_AGENT_API_KEY
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

def load_test_data(max_num:int=None):
    test_json_data=[]
    with open("/home/ubuntu/linShuExp/syndrome_differentiation_experiment/TCM_SD/sampled_data_300_700_samled_100.jsonl", "r",encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            test_json_data.append(data)
    # 打乱顺序
    random.shuffle(test_json_data)
    return test_json_data[:max_num] if max_num else test_json_data

def run_information(runner,informer_input:SystemMessage,full_patient_info:str,max_turn=20)->str: # 运行informationAgent,用于收集用户背景信息
        response=runner.information_agent.get_response(informer_input)
        if "<CLINICAL_INTERVIEW_TASK_DONE>" in response.content:
                clinical_interview_response=runner.information_agent.get_summary(runner.information_agent.history)
                return clinical_interview_response.content
        
        ColorPrinter.green("InformationAgent: ")
        ColorPrinter.white(response.content)
        current_turn=1
        while current_turn<=max_turn:
            llm=ChatOpenAI(base_url=INFORMATION_AGENT_BASE_URL,model=INFORMATION_AGENT_MODEL,api_key=INFORMATION_AGENT_API_KEY)
            patient_response = llm.invoke(f"你是一名患者，以下是你的病情信息:{full_patient_info}\n请你根据病情信息如实给出下面问题的回答:{response.content}\n1.永远不要忘记你患者的身份 2.以患者的身份口吻进行回答 3.不要向我提问 4.不要编造病情信息,只回答患者提供的病情信息,若无法回答,则如实告知患者无法回答")
            ColorPrinter.green("UserAgent: ")
            ColorPrinter.white(patient_response.content)
            input_message=HumanMessage(content=patient_response.content)
            response=runner.information_agent.get_response(input_message)
            ColorPrinter.green("InformationAgent: ")
            ColorPrinter.white(response.content)
            current_turn=current_turn+1
            if "<CLINICAL_INTERVIEW_TASK_DONE>" in response.content:
                clinical_interview_response=runner.information_agent.get_summary(runner.information_agent.history)
                return clinical_interview_response.content

def run_syndrome(runner,full_patient_info:str,incomplete_patient_info:str)->str:
    patient_background_information=incomplete_patient_info
    chat_turn_limit = 5 # 对话轮次限制
    while chat_turn_limit>0:

        # 运行SyndromeAgent
        fine_grained_assessment_syndrome_json,chain_of_thought=runner.three_stage_syndrome_differential(patient_background_information)
        ColorPrinter.green("SyndromeAgent:")
        ColorPrinter.white(fine_grained_assessment_syndrome_json)

        if fine_grained_assessment_syndrome_json["need_more_information"]=="false":
            break
        else:
            chat_turn_limit=chat_turn_limit-1
            if fine_grained_assessment_syndrome_json["needed_information"] and chat_turn_limit>0:
                # 如果需要更多信息,则继续追问
                runner.information_agent.init_message_ask()
                patient_background_information=run_information(runner,SystemMessage(content=f"以下是现有的患者信息:\n{patient_background_information}\n还需要患者提供以下信息:{fine_grained_assessment_syndrome_json['needed_information']},请继续追问(同样以<CLINICAL_INTERVIEW_TASK_DONE>结束):"),full_patient_info)
                ColorPrinter.red("SystemMessage:")
                ColorPrinter.yellow(f"PatientBackgroundInformation:{patient_background_information}")

    fine_grained_assessment_syndrome=fine_grained_assessment_syndrome_json["syndrome"]
    return fine_grained_assessment_syndrome

def process_single_test_case(data, thread_id, results_lock, results_dict):
    """
    处理单个测试用例的函数，用于多线程执行
    """
    try:
        # 为每个线程创建独立的Runner实例
        # 添加小延迟避免并发初始化冲突，使用更合理的延迟策略
        time.sleep((thread_id % 10) * 0.05)  # 最多延迟0.45秒
        
        runner = Runner()
        runner.initial_rag_retriever()
        
        full_patient_info = data["chief_complaint"] + '\n' + data['description'] + '\n' + data['detection']
        incomplete_patient_info = data["chief_complaint"]
        
        # 运行诊断
        fine_grained_assessment_syndrome = run_syndrome(
            runner, 
            full_patient_info=full_patient_info, 
            incomplete_patient_info=incomplete_patient_info
        )
        
        # 判断结果
        fine_grained_judgement = (fine_grained_assessment_syndrome == data['norm_syndrome'])
        
        # 线程安全地记录结果
        with results_lock:
            results_dict['y_true'].append(data['norm_syndrome'])
            results_dict['y_fine_grained_pred'].append(fine_grained_assessment_syndrome)
            results_dict['results'].append({
                'true_label': data['norm_syndrome'],
                'predicted_label': fine_grained_assessment_syndrome,
                'correct': fine_grained_judgement,
                'thread_id': thread_id
            })
        
        # 线程安全的日志输出
        with results_lock:
            ColorPrinter.red(f"Thread-{thread_id} SystemMessage:")
            ColorPrinter.yellow(
                f"true_label: {data['norm_syndrome']}\n"
                f"predicted_label: {fine_grained_assessment_syndrome}\n"
                f"fine_grained_judgement: {fine_grained_judgement}\n"
                f"{'='*50}"
            )
        
        return {
            'success': True,
            'true_label': data['norm_syndrome'],
            'predicted_label': fine_grained_assessment_syndrome,
            'correct': fine_grained_judgement,
            'thread_id': thread_id
        }
        
    except Exception as e:
        # 线程安全的错误日志
        with results_lock:
            ColorPrinter.red(f"Thread-{thread_id} Error:")
            ColorPrinter.yellow(f"处理测试用例时出错: {str(e)}")
            # 如果是PyTorch相关错误，提供更详细的错误信息
            if "torch" in str(e).lower() or "meta tensor" in str(e).lower():
                ColorPrinter.yellow("这是ModelScope embedding模型多线程访问问题，建议减少线程数或使用单线程模式")
        
        return {
            'success': False,
            'error': str(e),
            'thread_id': thread_id
        }


def main(max_workers=1, use_multithreading=True):
    """
    主函数，支持多线程和单线程模式
    
    Args:
        max_workers: 最大线程数，默认为4
        use_multithreading: 是否使用多线程，默认为True
    """
    # 初始化日志系统
    ColorPrinter.init_logging(log_dir="exp_logs/huatuo_turn_4", log_level="INFO")
    
    # 加载测试数据
    test_json_data = load_test_data(max_num=100)
    total_cases = len(test_json_data)
    
    ColorPrinter.red("SystemMessage:")
    ColorPrinter.yellow(f"开始处理 {total_cases} 个测试用例")
    ColorPrinter.yellow(f"使用模式: {'多线程' if use_multithreading else '单线程'}")
    if use_multithreading:
        ColorPrinter.yellow(f"线程数: {max_workers}")
        if max_workers > 2:
            ColorPrinter.yellow("⚠️  警告: 线程数过多可能导致ModelScope embedding模型冲突")
            ColorPrinter.yellow("💡 建议: 如果出现错误，请尝试减少线程数或使用单线程模式")
    
    start_time = time.time()
    
    if use_multithreading:
        # 多线程模式
        results_lock = threading.Lock()
        results_dict = {
            'y_true': [],
            'y_fine_grained_pred': [],
            'results': []
        }
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务，使用唯一的线程ID
            future_to_data = {
                executor.submit(
                    process_single_test_case, 
                    data, 
                    i,  # 使用唯一的测试用例索引作为线程ID
                    results_lock, 
                    results_dict
                ): data for i, data in enumerate(test_json_data)
            }
            
            # 使用tqdm显示进度
            with tqdm(total=total_cases, desc="处理测试用例", unit="case") as pbar:
                completed_count = 0
                success_count = 0
                error_count = 0
                
                for future in as_completed(future_to_data):
                    result = future.result()
                    completed_count += 1
                    
                    if result['success']:
                        success_count += 1
                    else:
                        error_count += 1
                    
                    # 更新进度条
                    pbar.update(1)
                    pbar.set_postfix({
                        '成功': success_count,
                        '失败': error_count,
                        '完成率': f"{completed_count/total_cases*100:.1f}%"
                    })
        
        # 提取结果
        y_true = results_dict['y_true']
        y_fine_grained_pred = results_dict['y_fine_grained_pred']
        
    else:
        # 单线程模式（原始逻辑）
        runner = Runner()
        runner.initial_rag_retriever()
        y_true = []
        y_fine_grained_pred = []
        
        with tqdm(total=total_cases, desc="处理测试用例", unit="case") as pbar:
            for i, data in enumerate(test_json_data):
                full_patient_info = data["chief_complaint"] + '\n' + data['description'] + '\n' + data['detection']
                incomplete_patient_info = data["chief_complaint"]
                try:
                    fine_grained_assessment_syndrome = run_syndrome(
                        runner, 
                        full_patient_info=full_patient_info, 
                        incomplete_patient_info=incomplete_patient_info
                    )
                except Exception as e:
                    ColorPrinter.red(f"测试用例 {i+1} 处理失败:")
                    ColorPrinter.yellow(f"错误: {str(e)}")
                    pbar.update(1)
                    continue
                
                # 记录真实标签和预测标签
                y_true.append(data['norm_syndrome'])
                y_fine_grained_pred.append(fine_grained_assessment_syndrome)
                
                fine_grained_judgement = (fine_grained_assessment_syndrome == data['norm_syndrome'])
                
                ColorPrinter.red("SystemMessage:")
                ColorPrinter.yellow(
                    f"true_label: {data['norm_syndrome']}\n"
                    f"predicted_label: {fine_grained_assessment_syndrome}\n"
                    f"fine_grained_judgement: {fine_grained_judgement}\n"
                    f"{'='*50}"
                )
                
                pbar.update(1)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    # 计算多分类准确率、召回率和F1分数
    try:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        acc_fine_grained = accuracy_score(y_true, y_fine_grained_pred)
        precision_fine_grained = precision_score(y_true, y_fine_grained_pred, average='weighted', zero_division=0)
        recall_fine_grained = recall_score(y_true, y_fine_grained_pred, average='weighted', zero_division=0)
        f1_fine_grained = f1_score(y_true, y_fine_grained_pred, average='weighted', zero_division=0)
        
        ColorPrinter.red("SystemMessage:")
        ColorPrinter.yellow("="*60)
        ColorPrinter.yellow("测试结果汇总:")
        ColorPrinter.yellow(f"处理时间: {processing_time:.2f} 秒")
        ColorPrinter.yellow(f"处理模式: {'多线程' if use_multithreading else '单线程'}")
        if use_multithreading:
            ColorPrinter.yellow(f"线程数: {max_workers}")
        ColorPrinter.yellow(f"总测试用例: {total_cases}")
        ColorPrinter.yellow(f"成功处理: {len(y_true)}")
        ColorPrinter.yellow(f"失败数量: {total_cases - len(y_true)}")
        if total_cases - len(y_true) > 0:
            ColorPrinter.yellow(f"成功率: {len(y_true)/total_cases*100:.1f}%")
        ColorPrinter.yellow("="*60)
        ColorPrinter.yellow("性能指标:")
        ColorPrinter.yellow(f"sklearn weighted accuracy: {acc_fine_grained:.4f}")
        ColorPrinter.yellow(f"sklearn weighted precision: {precision_fine_grained:.4f}")
        ColorPrinter.yellow(f"sklearn weighted recall: {recall_fine_grained:.4f}")
        ColorPrinter.yellow(f"sklearn weighted F1: {f1_fine_grained:.4f}")
        ColorPrinter.yellow("="*60)

    except ImportError:
        ColorPrinter.red("SystemMessage:")
        ColorPrinter.yellow("请先安装scikit-learn以计算准确率、召回率和F1分数。pip install scikit-learn")

def run_multithreaded_test(max_workers=4):
    """
    运行多线程测试的便捷函数
    
    Args:
        max_workers: 最大线程数，默认为4
    """
    main(max_workers=max_workers, use_multithreading=True)

def run_single_threaded_test():
    """
    运行单线程测试的便捷函数
    """
    main(use_multithreading=False)

if __name__ == "__main__":
    # 由于ModelScope的embedding模型在多线程环境下可能出现PyTorch冲突
    # 建议使用较少的线程数或单线程模式
    # 默认使用2个线程，避免模型冲突
    main(max_workers=1, use_multithreading=True)
    
    # 其他运行选项示例：
    # main(max_workers=1, use_multithreading=True)  # 使用1个线程（推荐）
    # main(use_multithreading=False)  # 使用单线程模式（最稳定）
    # main(max_workers=4, use_multithreading=True)  # 使用4个线程（可能不稳定）