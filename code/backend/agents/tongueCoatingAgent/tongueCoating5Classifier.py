import torch
import torchvision
import torchvision.transforms as transforms
from tools.colorPrinter import ColorPrinter
from PIL import Image
import os
import torch.nn as nn

class TongueResNet(nn.Module):
    def __init__(self, num_classes=5):
        """
        基于ResNet的舌头分类模型
        
        Args:
            num_classes: 分类数量
        """
        super(TongueResNet, self).__init__()
        
        # 选择骨干网络
        base_model = torchvision.models.resnet18(weights=None)
        
        # 移除最后的全连接层
        self.features = nn.Sequential(*list(base_model.children())[:-1])
        
        # 获取特征维度
        feature_dim = 512
        
        # 添加分类器头
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(feature_dim, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, x):
        """
        前向传播
        
        Args:
            x: 输入图像张量，形状为 [batch_size, 3, height, width]
            
        Returns:
            logits: 分类logits，形状为 [batch_size, num_classes]
        """
        features = self.features(x)
        logits = self.classifier(features)
        return logits
    
    def load_pretrained(self, checkpoint_path):
        """
        加载预训练权重
        
        Args:
            checkpoint_path: 检查点文件路径
        """
        self.load_state_dict(torch.load(checkpoint_path))

class TongueCoatingClassifier:
    def __init__(self, model_path="/home/ubuntu/MCM/backend/agents/tongueCoatingAgent/tongue_coating_resnet18_5classes.pth")->None:
        # 参数设置
        self.IMG_SIZE = 224 # 输入图片大小
        # self.NUM_CLASSES = 6 # 类别数量
        self.NUM_CLASSES = 5 # 类别数量
        self.DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.MODEL_PATH = model_path # 权重文件路径
        self.CLASS_NAMES = [
                '无苔',
                '薄白苔',
                '厚白苔',
                '黄腻苔',
                '灰黑苔'
            ]
        
        # 定义图像预处理（与训练时一致）
        self.test_transforms = transforms.Compose([
            transforms.Resize((self.IMG_SIZE, self.IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        # 加载模型
        self._initialize_model()
        
    def _initialize_model(self)->None:
        # 加载并初始化模型
        self.model = TongueResNet(num_classes=self.NUM_CLASSES)
        self.model.load_pretrained(self.MODEL_PATH)
        self.model = self.model.to(self.DEVICE)
        self.model.eval()

    def predict_image(self, image_path:str)->str:
        # 检查图片路径是否存在
        if not os.path.exists(image_path):
            # ColorPrinter.yellow("SystemMessage:")
            # ColorPrinter.red(f"错误: 图片文件 {image_path} 不存在!")
            print(f"错误: 图片文件 {image_path} 不存在!")
            return f"预测类别: 无", f"置信度: 无"
        
        # 打开图片并转换为 RGB
        image = Image.open(image_path).convert('RGB')
        
        # 应用预处理
        image_tensor = self.test_transforms(image).unsqueeze(0)
        image_tensor = image_tensor.to(self.DEVICE)

        ColorPrinter.green("TongueCoatingAgent:")
        ColorPrinter.white("正在进行舌苔病理诊断...")

        # 进行预测
        with torch.no_grad():
            output = self.model(image_tensor)
            probabilities = torch.softmax(output, dim=1)  # 计算概率
            confidence, predicted = torch.max(probabilities, 1)  # 获取最高概率及其索引

        # 获取预测结果
        predicted_class = self.CLASS_NAMES[predicted.item()]
        confidence_score = confidence.item() * 100

        predicted_result_str=f"预测类别: {predicted_class}\n置信度: {confidence_score:.2f}%\n"
        all_probabilities = probabilities[0].cpu().numpy()
        for i, prob in enumerate(all_probabilities):
            predicted_result_str+=f"{self.CLASS_NAMES[i]}: {prob * 100:.2f}%\n"

        ColorPrinter.green("TongueCoatingAgent:")
        ColorPrinter.white(predicted_result_str)

        return predicted_result_str
