from test_data import patient_background_information, image_path, tongue_coating_diagnosis_content
from agentsRunner import Runner
from langchain_core.messages import SystemMessage, AIMessage
from tools.colorPrinter import ColorPrinter
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from agents.agents_model_config import INFORMATION_AGENT_BASE_URL, INFORMATION_AGENT_MODEL, INFORMATION_AGENT_API_KEY
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import argparse  # [新增] 用于命令行参数解析

# ==========================================
# 辅助函数：Token 提取
# ==========================================
def _get_token_from_response(response) -> int:
    """从 LangChain 响应对象中安全提取 Token"""
    try:
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            return response.usage_metadata.get('total_tokens', 0)
        if hasattr(response, 'response_metadata'):
            return response.response_metadata.get('token_usage', {}).get('total_tokens', 0)
        return 0
    except Exception:
        return 0

def load_test_data(max_num: int = None):
    test_json_data = []
    # 建议将此路径也改为参数配置，此处保持原样
    with open("/home/ubuntu/linShuExp/syndrome_differentiation_experiment/TCM_SD/sampled_data_300_700_samled_100.jsonl", "r", encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            test_json_data.append(data)
    random.shuffle(test_json_data)
    return test_json_data[:max_num] if max_num else test_json_data

# ==========================================
# 核心逻辑修改：加入 Token 返回
# ==========================================

def run_information(runner, informer_input: SystemMessage, full_patient_info: str, max_turn=20) -> tuple[str, int]:
    """
    运行问诊 Agent
    Returns: (clinical_interview_content, total_tokens_used)
    """
    accumulated_tokens = 0
    
    # 1. Information Agent 第一轮提问
    response = runner.information_agent.get_response(informer_input)
    accumulated_tokens += _get_token_from_response(response)

    if "<CLINICAL_INTERVIEW_TASK_DONE>" in response.content:
        summary_response = runner.information_agent.get_summary(runner.information_agent.history)
        accumulated_tokens += _get_token_from_response(summary_response)
        return summary_response.content, accumulated_tokens
    
    ColorPrinter.green("InformationAgent: ")
    ColorPrinter.white(response.content)
    
    current_turn = 1
    while current_turn <= max_turn:
        # 2. User Agent (模拟患者) 回答
        llm = ChatOpenAI(base_url=INFORMATION_AGENT_BASE_URL, model=INFORMATION_AGENT_MODEL, api_key=INFORMATION_AGENT_API_KEY)
        user_prompt = f"你是一名患者，以下是你的病情信息:{full_patient_info}\n请你根据病情信息如实给出下面问题的回答:{response.content}\n1.永远不要忘记你患者的身份 2.以患者的身份口吻进行回答 3.不要向我提问 4.不要编造病情信息,只回答患者提供的病情信息,若无法回答,则如实告知患者无法回答"
        
        patient_response = llm.invoke(user_prompt)
        accumulated_tokens += _get_token_from_response(patient_response) # 计入模拟患者的消耗

        ColorPrinter.green("UserAgent: ")
        ColorPrinter.white(patient_response.content)
        
        # 3. Information Agent 继续追问
        input_message = HumanMessage(content=patient_response.content)
        response = runner.information_agent.get_response(input_message)
        accumulated_tokens += _get_token_from_response(response)

        ColorPrinter.green("InformationAgent: ")
        ColorPrinter.white(response.content)
        
        current_turn += 1
        
        if "<CLINICAL_INTERVIEW_TASK_DONE>" in response.content:
            summary_response = runner.information_agent.get_summary(runner.information_agent.history)
            accumulated_tokens += _get_token_from_response(summary_response)
            return summary_response.content, accumulated_tokens
            
    # 如果达到最大轮次仍未完成，返回当前摘要
    summary_response = runner.information_agent.get_summary(runner.information_agent.history)
    accumulated_tokens += _get_token_from_response(summary_response)
    return summary_response.content, accumulated_tokens

def run_syndrome(runner, full_patient_info: str, incomplete_patient_info: str, chat_turn_limit: int) -> tuple[str, int]:
    """
    运行辨证 Agent
    Returns: (syndrome_result, total_tokens_used)
    """
    patient_background_information = incomplete_patient_info
    total_tokens = 0
    current_turn_limit = chat_turn_limit

    while current_turn_limit > 0:
        # 运行SyndromeAgent
        # [注意] 这里假设 runner.three_stage_syndrome_differential 已经修改为返回 (json, cot, tokens)
        # 如果 Runner 未修改，此处会报错。请确保 Runner 与之前的修改一致。
        try:
            result = runner.three_stage_syndrome_differential(patient_background_information)
            # 兼容性解包：检查返回长度
            if len(result) == 3:
                fine_grained_assessment_syndrome_json, chain_of_thought, run_tokens = result
            else:
                fine_grained_assessment_syndrome_json, chain_of_thought = result
                run_tokens = 0 # Fallback if no token returned
            
            total_tokens += run_tokens
            
        except Exception as e:
            ColorPrinter.red(f"Error calling three_stage_syndrome_differential: {e}")
            raise e

        ColorPrinter.green("SyndromeAgent:")
        ColorPrinter.white(fine_grained_assessment_syndrome_json)

        if fine_grained_assessment_syndrome_json["need_more_information"] == "false":
            break
        else:
            current_turn_limit -= 1
            if fine_grained_assessment_syndrome_json["needed_information"] and current_turn_limit > 0:
                # 追问环节
                runner.information_agent.init_message_ask()
                
                info_prompt = f"以下是现有的患者信息:\n{patient_background_information}\n还需要患者提供以下信息:{fine_grained_assessment_syndrome_json['needed_information']},请继续追问(同样以<CLINICAL_INTERVIEW_TASK_DONE>结束):"
                
                # 调用 run_information 并累加 Token
                new_info, info_tokens = run_information(
                    runner,
                    SystemMessage(content=info_prompt),
                    full_patient_info
                )
                total_tokens += info_tokens
                patient_background_information = new_info # 更新信息
                
                ColorPrinter.red("SystemMessage:")
                ColorPrinter.yellow(f"PatientBackgroundInformation:{patient_background_information}")

    fine_grained_assessment_syndrome = fine_grained_assessment_syndrome_json["syndrome"]
    return fine_grained_assessment_syndrome, total_tokens

def process_single_test_case(data, thread_id, results_lock, results_dict, chat_turn_limit):
    """
    处理单个测试用例
    """
    try:
        time.sleep((thread_id % 10) * 0.05)
        
        runner = Runner()
        runner.initial_rag_retriever()
        
        full_patient_info = data["chief_complaint"] + '\n' + data['description'] + '\n' + data['detection']
        incomplete_patient_info = data["chief_complaint"]
        
        # 运行诊断并获取 Token
        fine_grained_assessment_syndrome, tokens_used = run_syndrome(
            runner, 
            full_patient_info=full_patient_info, 
            incomplete_patient_info=incomplete_patient_info,
            chat_turn_limit=chat_turn_limit
        )
        
        fine_grained_judgement = (fine_grained_assessment_syndrome == data['norm_syndrome'])
        
        with results_lock:
            results_dict['y_true'].append(data['norm_syndrome'])
            results_dict['y_fine_grained_pred'].append(fine_grained_assessment_syndrome)
            # [新增] 记录 Token
            results_dict['tokens'].append(tokens_used)
            
            results_dict['results'].append({
                'true_label': data['norm_syndrome'],
                'predicted_label': fine_grained_assessment_syndrome,
                'correct': fine_grained_judgement,
                'tokens': tokens_used,
                'thread_id': thread_id
            })
        
        with results_lock:
            ColorPrinter.red(f"Thread-{thread_id} Result:")
            ColorPrinter.yellow(
                f"True: {data['norm_syndrome']} | Pred: {fine_grained_assessment_syndrome}\n"
                f"Correct: {fine_grained_judgement} | Tokens: {tokens_used}\n"
                f"{'-'*30}"
            )
        
        return {'success': True}
        
    except Exception as e:
        with results_lock:
            ColorPrinter.red(f"Thread-{thread_id} Error: {str(e)}")
        return {'success': False}

# ==========================================
# 主程序逻辑修改：参数解析与统计
# ==========================================

def main():
    # 1. 定义命令行参数
    parser = argparse.ArgumentParser(description="TCM Syndrome Differentiation Experiment Runner")
    parser.add_argument('--max_workers', type=int, default=1, help='最大线程数 (建议: 1)')
    parser.add_argument('--chat_turn_limit', type=int, default=5, help='医患问诊最大轮次')
    parser.add_argument('--log_dir', type=str, default="exp_logs/huatuo_turn_4", help='日志保存目录')
    parser.add_argument('--no_multithreading', action='store_true', help='强制使用单线程模式')
    parser.add_argument('--sample_num', type=int, default=100, help='测试样本数量')
    
    args = parser.parse_args()
    
    use_multithreading = not args.no_multithreading and args.max_workers > 1

    # 2. 初始化日志
    ColorPrinter.init_logging(log_dir=args.log_dir, log_level="INFO")
    
    test_json_data = load_test_data(max_num=args.sample_num)
    total_cases = len(test_json_data)
    
    ColorPrinter.red("Experiment Configuration:")
    ColorPrinter.yellow(f"Mode: {'Multi-thread' if use_multithreading else 'Single-thread'}")
    ColorPrinter.yellow(f"Workers: {args.max_workers}")
    ColorPrinter.yellow(f"Chat Turn Limit: {args.chat_turn_limit}")
    ColorPrinter.yellow(f"Log Directory: {args.log_dir}")
    
    start_time = time.time()
    
    # 初始化结果容器
    results_lock = threading.Lock()
    results_dict = {
        'y_true': [],
        'y_fine_grained_pred': [],
        'tokens': [], # [新增] Token 列表
        'results': []
    }
    
    # 3. 执行任务
    if use_multithreading:
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_to_data = {
                executor.submit(
                    process_single_test_case, 
                    data, i, results_lock, results_dict, args.chat_turn_limit
                ): data for i, data in enumerate(test_json_data)
            }
            
            with tqdm(total=total_cases, desc="Processing", unit="case") as pbar:
                for future in as_completed(future_to_data):
                    future.result()
                    pbar.update(1)
    else:
        # 单线程回退模式
        with tqdm(total=total_cases, desc="Processing", unit="case") as pbar:
            for i, data in enumerate(test_json_data):
                process_single_test_case(data, i, results_lock, results_dict, args.chat_turn_limit)
                pbar.update(1)

    end_time = time.time()
    
    # 4. 计算指标
    y_true = results_dict['y_true']
    y_pred = results_dict['y_fine_grained_pred']
    tokens = results_dict['tokens']
    
    try:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        ColorPrinter.red("\n" + "="*20 + " FINAL RESULTS " + "="*20)
        ColorPrinter.yellow(f"Total Time: {end_time - start_time:.2f}s")
        ColorPrinter.yellow(f"Valid Samples: {len(y_true)}/{total_cases}")
        
        # Token 统计
        if tokens:
            avg_tokens = sum(tokens) / len(tokens)
            ColorPrinter.yellow(f"Total Tokens: {sum(tokens)}")
            ColorPrinter.yellow(f"Avg Tokens/Task: {avg_tokens:.2f}")
        
        if len(y_true) > 0:
            acc = accuracy_score(y_true, y_pred)
            prec = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            rec = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            
            ColorPrinter.yellow("-" * 30)
            ColorPrinter.yellow(f"Accuracy:  {acc:.4f}")
            ColorPrinter.yellow(f"Precision: {prec:.4f}")
            ColorPrinter.yellow(f"Recall:    {rec:.4f}")
            ColorPrinter.yellow(f"F1 Score:  {f1:.4f}")
            ColorPrinter.yellow("="*60)
            
    except ImportError:
        ColorPrinter.yellow("Please install sklearn: pip install scikit-learn")

if __name__ == "__main__":
    main()