from langchain.prompts import SystemMessagePromptTemplate
from agents.tongueCoatingAgent.tongueCoating5Classifier import TongueCoatingClassifier
from tools.colorPrinter import ColorPrinter
from agents.agents_model_config import TONGUE_COATING_AGENT_BASE_URL_MLLM,TONGUE_COATING_AGENT_MODEL_MLLM,TONGUE_COATING_AGENT_API_KEY_MLLM,TONGUE_COATING_AGENT_BASE_URL_LLM,TONGUE_COATING_AGENT_MODEL_LLM,TONGUE_COATING_AGENT_API_KEY_LLM
from langchain_openai import ChatOpenAI
import base64
import openai

class TongueCoatingAgent:
    def __init__(self)->None:
        self.mllm=openai.Client(api_key=TONGUE_COATING_AGENT_API_KEY_MLLM,base_url=TONGUE_COATING_AGENT_BASE_URL_MLLM) #调用多模态大模型
        self.llm = ChatOpenAI(base_url=TONGUE_COATING_AGENT_BASE_URL_LLM, model=TONGUE_COATING_AGENT_MODEL_LLM, api_key=TONGUE_COATING_AGENT_API_KEY_LLM)
        self.system_prompt="""
            你是一个舌苔诊断专家，你的任务是帮助用户诊断舌苔问题。\n
            你需要根据用户提供的舌苔病理图片、舌苔分类结果和置信度来进行综合诊断。\n
            请描述舌苔的特征（如舌质、舌苔颜色厚薄等）和可能的健康问题。\n
            不要给出任何医疗建议或治疗方案。\n
            """

    def multimodal_llm_call(self,predict_result:str,image_path:str)->str:
        try:
            with open(image_path, "rb") as image_file:
                #获取图片类型
                image_type = image_path.split('.')[-1]
                if image_type not in ['jpg', 'jpeg', 'png']:
                    raise ValueError("Unsupported image format. Please use jpg, jpeg, or png.")
                #读取图片并转换为base64编码
                base64_bytes = base64.b64encode(image_file.read())
        
                completion = self.mllm.chat.completions.create(
                model=TONGUE_COATING_AGENT_MODEL_MLLM,
                messages=[
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                # 在对话中传入图片，来实现基于图片的理解
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"以下是舌苔分类结果:{predict_result}\n这是你可以完全相信的参考的结果(来自resnet18舌苔分类器):\n{predict_result}\n请你根据图片描述舌苔特征（如舌质、舌苔颜色厚薄等）:\n",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_type};base64,{base64_bytes.decode('utf-8')}",
                            },
                        },
                    ],
                },
            ],
            )
        except FileNotFoundError: # 捕获文件未找到异常
            ColorPrinter.red("SystemMessage:")
            ColorPrinter.yellow(f"错误: 文件 {image_path} 没找到")
        except ValueError as ve:  # 捕获值错误
            ColorPrinter.red("SystemMessage:")
            ColorPrinter.yellow(f"错误: {ve}")
        except Exception as e: # 捕获其他异常
            ColorPrinter.red("SystemMessage:")
            ColorPrinter.yellow(f"错误: 未知错误: {e}")
        # 返回模型的输出
        return completion.choices[0].message.content

    def llm_call(self,tongue_coating_description:str,predict_result:str)->str:
        response=self.llm.invoke(f"""
            这是你可以完全相信的参考的结果(来自resnet18舌苔分类器):\n{predict_result}\n
            请你根据以下舌苔特征描述（如舌质、舌苔颜色厚薄等）给出诊断结果:\n{tongue_coating_description}\n
            诊断结果应该包含以下内容:\n
            1.可能的健康问题\n
            2.可能的中医诊断\n
            3.需要记录舌苔分类的置信度结果\n
            输出格式:不要使用markdown格式,直接输出文本\n
            """)
        return response.content

    def tongue_coating_diagnosis(self,image_path:str)->str:
        classifier=TongueCoatingClassifier() #创建舌苔分类器实例
        predict_result=classifier.predict_image(image_path) #对图像进行舌苔分类
        #调用多模态LLM进行舌苔描述
        response_content=self.multimodal_llm_call(
            predict_result=predict_result,
            image_path=image_path) 
        tongue_diagnosis=self.llm_call(
            tongue_coating_description=response_content,
            predict_result=predict_result,
            )
        return tongue_diagnosis