from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import uuid
import threading
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import os
import base64
from io import BytesIO
from PIL import Image
import zipfile
import tempfile
import shutil

from agentsRunner import Runner
from langchain_core.messages import SystemMessage, HumanMessage
from tools.colorPrinter import ColorPrinter

app = Flask(__name__)
CORS(app)

class ConversationContainer:
    """对话容器，用于存储和管理agent运行过程中的信息"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.status = "idle"  # idle, running, completed, error
        self.current_step = ""
        self.messages = []  # 存储所有输出信息
        self.data = {}  # 存储中间数据
        self.error_message = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.log_file_path = None  # 存储ColorPrinter日志文件路径
        # 异步消息泵: 用户消息队列 + 事件
        self._user_message_queue: List[str] = []
        self._user_message_event = threading.Event()
        
    def add_message(self, agent_name: str, message: str, message_type: str = "info"):
        """添加消息到对话容器"""
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "message": message,
            "type": message_type  # info, warning, error, success
        }
        self.messages.append(message_data)
        self.updated_at = datetime.now()
        
    def update_status(self, status: str, step: str = ""):
        """更新状态"""
        self.status = status
        self.current_step = step
        self.updated_at = datetime.now()
        
    def set_data(self, key: str, value):
        """设置数据"""
        self.data[key] = value
        self.updated_at = datetime.now()
        
    def get_data(self, key: str, default=None):
        """获取数据"""
        return self.data.get(key, default)
        
    def to_dict(self):
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "current_step": self.current_step,
            "messages": self.messages,
            "data": self.data,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    # ===== 异步消息泵 API =====
    def enqueue_user_message(self, message: str):
        """将用户消息放入队列并唤醒等待线程"""
        self._user_message_queue.append(message)
        self._user_message_event.set()
        self.updated_at = datetime.now()

    def wait_for_user_message(self, timeout: Optional[float] = None) -> Optional[str]:
        """等待用户消息; 返回消息或None(超时)"""
        # 快速路径: 队列已有
        if self._user_message_queue:
            return self._user_message_queue.pop(0)
        # 阻塞等待
        is_set = self._user_message_event.wait(timeout=timeout)
        if not is_set:
            return None
        # 消费一条
        msg = self._user_message_queue.pop(0) if self._user_message_queue else None
        # 若队列空则复位事件
        if not self._user_message_queue:
            self._user_message_event.clear()
        return msg

# 全局对话容器存储
conversation_containers: Dict[str, ConversationContainer] = {}

# 自定义的ColorPrinter，用于将输出重定向到对话容器
class ContainerColorPrinter:
    """将ColorPrinter的输出重定向到对话容器"""
    
    def __init__(self, container: ConversationContainer):
        self.container = container
        
    def red(self, text: str):
        self.container.add_message("System", text, "error")
        
    def green(self, text: str):
        self.container.add_message("System", text, "success")
        
    def yellow(self, text: str):
        self.container.add_message("System", text, "warning")
        
    def blue(self, text: str):
        self.container.add_message("System", text, "info")
        
    def white(self, text: str):
        self.container.add_message("System", text, "info")
        
    def color_text(self, text: str, color: str) -> str:
        return text  # 简化处理，直接返回原文本
        
    def log_info(self, message: str):
        self.container.add_message("System", f"[INFO] {message}", "info")

def run_agent_chain(container: ConversationContainer, image_path: str):
    """在后台线程中运行agent链"""
    try:
        container.update_status("running", "Initializing System")
        container.add_message("System", "Initializing Multi-Agent System 🚀", "info")
        
        # 创建Runner实例
        runner = Runner()
        
        # 初始化日志系统
        log_file_path = ColorPrinter.init_logging(log_dir="logs", log_level="INFO")
        
        # 将日志文件路径存储到容器中
        container.log_file_path = log_file_path
        
        # 初始化RAG检索器
        container.update_status("running", "Initializing Multi-Path Parallel RAG")
        container.add_message("System", "Initializing Multi-Path Parallel RAG... 🔍", "info")
        runner.initial_rag_retriever()
        container.add_message("System", "Multi-Path Parallel RAG initialization completed ✅", "success")
        
        # 运行舌苔诊断
        container.update_status("running", "Tongue Diagnosis")
        container.add_message("TongueDiagnosisAgent", "Starting tongue diagnosis analysis 🔍", "info")
        tongue_coating_diagnosis_content = runner.run_tongue_coating(image_path)
        container.add_message("TongueDiagnosisAgent", tongue_coating_diagnosis_content, "success")
        ColorPrinter.green("TongueDiagnosisAgent:")
        ColorPrinter.white(str(tongue_coating_diagnosis_content))
        container.set_data("tongue_coating_diagnosis", tongue_coating_diagnosis_content)
        container.set_data("tongue_coating_image_path", image_path)
        
        # ========== 信息收集（异步消息泵） ==========
        container.update_status("running", "Clinical Interview")
        container.add_message("ClinicalInterviewAgent", "Starting patient background information collection 🔍", "info")

        def run_information_with_message_pump(init_system_content: str) -> str:
            """使用容器消息泵驱动 ClinicalInterviewAgent 的多轮对话，直到 <CLINICAL_INTERVIEW_TASK_DONE>。返回总结文本。"""
            # 1) 首次以 SystemMessage 触发
            response = runner.information_agent.get_response(SystemMessage(content=init_system_content))
            container.add_message("ClinicalInterviewAgent", response.content, "info")
            ColorPrinter.green("ClinicalInterviewAgent:")
            ColorPrinter.white(str(response.content))
            # 2) 若已完成，直接总结
            if "<CLINICAL_INTERVIEW_TASK_DONE>" in response.content:
                summary = runner.information_agent.get_summary(runner.information_agent.history).content
                return summary
            # 3) 否则进入用户驱动的循环
            while True:
                # container.add_message("ClinicalInterviewAgent", "需要更多信息，请在下方输入框继续提供", "warning")
                user_msg = container.wait_for_user_message(timeout=None)
                if user_msg is None:
                    continue
                container.add_message("User", user_msg, "info")
                ColorPrinter.green("User:")
                ColorPrinter.white(str(user_msg))
                ai_resp = runner.information_agent.get_response(HumanMessage(content=user_msg))
                container.add_message("ClinicalInterviewAgent", ai_resp.content, "info")
                ColorPrinter.green("ClinicalInterviewAgent:")
                ColorPrinter.white(str(ai_resp.content))
                if "<CLINICAL_INTERVIEW_TASK_DONE>" in ai_resp.content:
                    summary = runner.information_agent.get_summary(runner.information_agent.history).content
                    return summary

        init_info_prompt = (
            f"以下是用户上传的舌苔图片的诊断结果：{tongue_coating_diagnosis_content}\n"
            "在经过多轮对话后，你需要在患者信息描述中加入患者舌苔的特征和可能的健康问题(结合患者信息进一步缩小范围)。"
        )
        patient_background_information = run_information_with_message_pump(init_info_prompt)
        ColorPrinter.green("ClinicalInterviewAgent:")
        ColorPrinter.white(str(patient_background_information))

        container.add_message("ClinicalInterviewAgent", f"Patient background information collection completed: {patient_background_information} ✅", "success")
        container.set_data("patient_background_information", patient_background_information)
        
        # 运行证候诊断（可能需要多轮）
        chat_turn_limit = 5
        while chat_turn_limit > 0:
            container.update_status("running", "Syndrome Differentiation")
            container.add_message("Reflexive Evidence-Aware Diagnostic Loop", "Starting syndrome differentiation analysis 🔍", "info")
            
            fine_grained_assessment_syndrome_json, diagnosis_chain_of_thought = runner.three_stage_syndrome_differential(patient_background_information)
            # container.add_message("SyndromeDifferentiationAgent", f"Syndrome differentiation results 🎯: {json.dumps(fine_grained_assessment_syndrome_json, ensure_ascii=False)} ✅", "success")
            for thought in diagnosis_chain_of_thought:
                container.add_message("SyndromeDifferentiationAgent", f"💡Thinking: {thought} ✅", "success")
            
            if fine_grained_assessment_syndrome_json["need_more_information"] == "false":
                break
            else:
                chat_turn_limit -= 1
                if fine_grained_assessment_syndrome_json["needed_information"]:
                    # 回退到信息收集阶段
                    container.add_message("ClinicalInterviewAgent", "Need more information, continuing collection 🔍", "warning")
                    container.update_status("running", "Clinical Interview")
                    runner.information_agent.init_message_ask()
                    prompt = (
                        f"以下是现有的患者信息:\n{patient_background_information}\n"
                        f"还需要患者提供以下信息:{fine_grained_assessment_syndrome_json['needed_information']}，"
                        "请逐条追问并在用户满足信息后以 <CLINICAL_INTERVIEW_TASK_DONE> 结束。"
                    )
                    patient_background_information = run_information_with_message_pump(prompt)
                    container.add_message("ClinicalInterviewAgent", f"Updated patient information: {patient_background_information}✅", "success")
                    container.set_data("patient_background_information", patient_background_information)
                    # 信息收集完成，回到证候诊断阶段
                    container.update_status("running", "Syndrome Differentiation")
        
        fine_grained_assessment_syndrome = fine_grained_assessment_syndrome_json["syndrome"]
        container.set_data("fine_grained_assessment_syndrome_json", fine_grained_assessment_syndrome_json)
        
        # 运行PlanAgent
        container.update_status("running", "Treatment Planning")
        container.add_message("ContentPlanningAgent", "Starting treatment plan generation 📋", "info")
        plan_tasks = runner.run_plan_agent(patient_background_information, fine_grained_assessment_syndrome_json)
        container.add_message("ContentPlanningAgent", f"Treatment plan generation completed ✅: {json.dumps(plan_tasks, ensure_ascii=False)}", "success")
        container.set_data("plan_tasks", plan_tasks)
        
        # 运行RagAgent
        container.update_status("running", "Reference Retrieval")
        container.add_message("Multi-Path Parallel RAG", "Starting reference material retrieval 📚", "info")
        base_rag_information, plan_rag_information = runner.run_rag_agent(
            fine_grained_assessment_syndrome, 
            patient_background_information, 
            plan_tasks
        )
        container.add_message("Multi-Path Parallel RAG", "Reference material retrieval completed ✅", "success")
        container.set_data("base_rag_information", base_rag_information)
        container.set_data("plan_rag_information", plan_rag_information)
        
        # 运行drafting agents
        container.update_status("running", "Content Generation")
        container.add_message("Reflexive Argumentation & Iterative Drafting", "Starting detailed treatment content generation, please wait a few minutes... ⏱️", "info")
        drafting_result = runner.run_drafting_agents(
            patient_background_information,
            fine_grained_assessment_syndrome_json,
            plan_tasks,
            base_rag_information,
            plan_rag_information
        )
        container.add_message("Reflexive Argumentation & Iterative Drafting", "Detailed content generation completed ✅", "success")
        container.set_data("drafting_result", drafting_result)
        ColorPrinter.green("Reflexive Argumentation & Iterative Drafting:")
        ColorPrinter.white(str(drafting_result))
        
        # 运行链接添加agent
        container.update_status("running", "Adding References")
        container.add_message("ReportAgent", "Starting reference links addition 📌", "info")
        search_reference = runner.run_links_add_agent(drafting_result=drafting_result)
        container.add_message("ReportAgent", "Reference links addition completed ✅", "success")
        container.set_data("search_reference", search_reference)
        
        # 生成最终报告
        container.update_status("running", "Final Report Generation")
        container.add_message("ReportAgent", "Starting final report generation 📋", "info")
        save_path = runner.run_report_gen_agent(
            patient_background_information=patient_background_information,
            main_content=drafting_result,
            tongue_coating_image_path=image_path,
            tongue_coating_diagnosis=tongue_coating_diagnosis_content,
            search_reference=search_reference
        )
        container.add_message("ReportAgent", f"Final report generation completed, saved to: {save_path}", "success")
        container.set_data("report_save_path", save_path)
        
        # 完成
        container.update_status("completed", "All Tasks Completed")
        container.add_message("System", "All Agent tasks execution completed! ✅", "success")
        
    except Exception as e:
        container.update_status("error", f"Execution error: {str(e)}")
        container.add_message("System", f"Error occurred during execution: {str(e)}", "error")
        container.error_message = str(e)

@app.route('/api/start_diagnosis', methods=['POST'])
def start_diagnosis():
    """开始诊断流程"""
    try:
        data = request.get_json()
        if not data or 'image_path' not in data:
            return jsonify({"error": "Missing image_path parameter"}), 400
        
        # 创建新的会话
        session_id = str(uuid.uuid4())
        container = ConversationContainer(session_id)
        conversation_containers[session_id] = container
        
        # 存储图片路径和原始文件名到容器中
        container.set_data('image_path', data['image_path'])
        
        # 在后台线程中运行agent链
        thread = threading.Thread(
            target=run_agent_chain, 
            args=(container, data['image_path'])
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "session_id": session_id,
            "status": "started",
            "message": "Diagnosis process started"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<session_id>', methods=['GET'])
def get_status(session_id):
    """获取会话状态"""
    if session_id not in conversation_containers:
        return jsonify({"error": "Session does not exist"}), 404
    
    container = conversation_containers[session_id]
    return jsonify(container.to_dict())

@app.route('/api/messages/<session_id>', methods=['GET'])
def get_messages(session_id):
    """获取会话消息"""
    if session_id not in conversation_containers:
        return jsonify({"error": "Session does not exist"}), 404
    
    container = conversation_containers[session_id]
    return jsonify({
        "session_id": session_id,
        "messages": container.messages,
        "status": container.status,
        "current_step": container.current_step
    })

@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    """上传舌苔图片"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file uploaded"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # 保存图片到临时目录
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        return jsonify({
            "image_path": file_path,
            "filename": filename,
            "message": "Image uploaded successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """获取所有会话列表"""
    sessions = []
    for session_id, container in conversation_containers.items():
        sessions.append({
            "session_id": session_id,
            "status": container.status,
            "current_step": container.current_step,
            "created_at": container.created_at.isoformat(),
            "updated_at": container.updated_at.isoformat()
        })
    
    return jsonify({"sessions": sessions})

@app.route('/api/clear_session/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    """清除指定会话"""
    if session_id not in conversation_containers:
        return jsonify({"error": "Session does not exist"}), 404
    
    del conversation_containers[session_id]
    return jsonify({"message": "Session cleared successfully"})

@app.route('/api/clear_all_sessions', methods=['DELETE'])
def clear_all_sessions():
    """清除所有会话"""
    conversation_containers.clear()
    return jsonify({"message": "All sessions cleared successfully"})

@app.route('/api/send_message/<session_id>', methods=['POST'])
def send_message(session_id):
    """发送消息给ClinicalInterviewAgent"""
    try:
        if session_id not in conversation_containers:
            return jsonify({"error": "Session does not exist"}), 404
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Missing message parameter"}), 400
        
        container = conversation_containers[session_id]
        
        # 检查会话状态
        if container.status != "running":
            return jsonify({"error": "Session is not in running state"}), 400
        
        # 检查是否在信息收集阶段
        if "Clinical Interview" not in container.current_step and "ClinicalInterviewAgent" not in container.current_step:
            return jsonify({"error": "Currently not in clinical interview stage"}), 400
        
        # 将用户消息注入容器队列并唤醒信息收集流程
        # 注意：不再额外追加 User 消息到 messages，避免与 ClinicalInterviewAgent 消费后重复
        container.enqueue_user_message(data['message'])
        
        return jsonify({
            "status": "success",
            "message": "Message sent successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(conversation_containers)
    })

@app.route('/api/submit_survey', methods=['POST'])
def submit_survey():
    """提交问卷调查"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing survey data"}), 400
        
        # 创建survey目录
        survey_dir = "survey"
        os.makedirs(survey_dir, exist_ok=True)
        
        # 生成文件名（时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"survey_{timestamp}.json"
        filepath = os.path.join(survey_dir, filename)
        
        # 保存问卷数据
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "status": "success",
            "message": "Survey submitted successfully",
            "filename": filename
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/report', methods=['GET'])
def download_report():
    """下载生成的报告文件: /api/report?path=<file_path>"""
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({"error": "Missing path parameter"}), 400
        if not os.path.isfile(file_path):
            return jsonify({"error": "File does not exist"}), 404
        # 简单安全限制：仅允许下载位于工作目录内的文件
        abs_path = os.path.abspath(file_path)
        cwd = os.path.abspath(os.getcwd())
        if not abs_path.startswith(cwd):
            return jsonify({"error": "Invalid path"}), 400
        return send_file(abs_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download_package/<session_id>', methods=['GET'])
def download_complete_package(session_id):
    """下载完整的诊断包：包含舌苔图片、交互日志和诊断报告"""
    try:
        # 获取会话数据
        container = conversation_containers.get(session_id)
        if not container:
            return jsonify({"error": "Session does not exist"}), 404
        
        # 创建临时目录
        temp_dir = f"temp_package_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 1. 复制舌苔图片
        image_path = container.get_data('tongue_coating_image_path') or container.get_data('image_path')
        if image_path and os.path.isfile(image_path):
            image_filename = os.path.basename(image_path)
            shutil.copy2(image_path, os.path.join(temp_dir, f"{image_filename}"))
        
        # 2. 复制ColorPrinter日志文件
        if container.log_file_path and os.path.isfile(container.log_file_path):
            log_filename = os.path.basename(container.log_file_path)
            shutil.copy2(container.log_file_path, os.path.join(temp_dir, f"system_log_{log_filename}"))
        else:
            # 如果没有ColorPrinter日志文件，则生成简化的交互日志
            log_content = f"MedMirror 诊断会话日志\n"
            log_content += f"会话ID: {session_id}\n"
            log_content += f"创建时间: {container.created_at.isoformat()}\n"
            log_content += f"更新时间: {container.updated_at.isoformat()}\n"
            log_content += f"状态: {container.status}\n"
            log_content += f"当前步骤: {container.current_step}\n\n"
            
            log_content += "=== 交互日志 ===\n"
            for msg in container.messages:
                log_content += f"[{msg['timestamp']}] {msg['agent']} ({msg['type']}): {msg['message']}\n"
            
            # 保存交互日志
            log_file = os.path.join(temp_dir, "interaction_log.txt")
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
        
        # 3. 复制诊断报告
        report_path = container.get_data('report_save_path')
        if report_path and os.path.isfile(report_path):
            report_filename = os.path.basename(report_path)
            shutil.copy2(report_path, os.path.join(temp_dir, f"diagnosis_report_{report_filename}"))
        
        # 4. 创建压缩包
        zip_filename = f"medmirror_diagnosis_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != zip_filename:  # 不包含压缩包本身
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # 5. 返回压缩包并安排清理
        def delayed_cleanup():
            """延迟清理临时文件"""
            time.sleep(30)  # 等待30秒确保下载完成
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        # 在后台线程中清理临时文件
        cleanup_thread = threading.Thread(target=delayed_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
        
    except Exception as e:
        # 确保清理临时文件
        try:
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir)
        except:
            pass
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs("logs", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)
    
    print("启动Flask服务器...")
    print("API接口:")
    print("  POST /api/start_diagnosis - 开始诊断流程")
    print("  GET  /api/status/<session_id> - 获取会话状态")
    print("  GET  /api/messages/<session_id> - 获取会话消息")
    print("  POST /api/upload_image - 上传舌苔图片")
    print("  GET  /api/sessions - 获取所有会话列表")
    print("  DELETE /api/clear_session/<session_id> - 清除指定会话")
    print("  DELETE /api/clear_all_sessions - 清除所有会话")
    print("  GET  /api/health - 健康检查")
    print("  POST /api/submit_survey - 提交问卷调查")
    print("  GET  /api/report - 下载报告文件包")
    print("  GET  /api/download_package/<session_id> - 下载完整诊断包")
    
    app.run(host='0.0.0.0', port=8000, debug=True)
