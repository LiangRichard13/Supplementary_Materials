import logging
import os
from datetime import datetime
from typing import Optional

class ColorPrinter:
    """
    支持打印加粗彩色文本的类，颜色包括：
    - 红色 (31)
    - 绿色 (32)
    - 黄色 (33)
    - 蓝色 (34)
    - 品红 (35)
    - 青色 (36)
    - 白色 (37)
    
    同时自动记录所有输出到日志文件
    """

    COLORS = {
        'red': 31,
        'green': 32,
        'yellow': 33,
        'blue': 34,
        'magenta': 35,
        'cyan': 36,
        'white': 37,
    }
    
    # 类级别的日志器
    _logger: Optional[logging.Logger] = None
    _log_file: Optional[str] = None
    
    @classmethod
    def init_logging(cls, log_dir: str = "logs", log_level: str = "INFO"):
        """
        初始化日志系统
        
        Args:
            log_dir: 日志文件保存目录
            log_level: 日志级别
        """
        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 生成日志文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cls._log_file = os.path.join(log_dir, f"{timestamp}.log")
        
        # 配置日志器
        cls._logger = logging.getLogger(f"{timestamp}")
        cls._logger.setLevel(getattr(logging, log_level.upper()))
        
        # 创建文件处理器
        file_handler = logging.FileHandler(cls._log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        cls._logger.addHandler(file_handler)
        
        # 记录初始化信息
        cls._logger.info(f"ColorPrinter日志系统初始化完成，日志文件: {cls._log_file}")
        return cls._log_file
    
    @classmethod
    def _log_output(cls, text: str, color: str = "default"):
        """记录输出到日志"""
        if cls._logger is not None:
            cls._logger.info(f"COLOR_PRINT[{color.upper()}]: {text}")
    
    @classmethod
    def get_log_file_path(cls) -> Optional[str]:
        """获取日志文件路径"""
        return cls._log_file

    @classmethod
    def _colorize(cls, text: str, color_code: int) -> str:
        """内部方法：给文本添加颜色和加粗样式"""
        return f"\033[1;{color_code}m{text}\033[0m"  # 添加 1; 表示加粗

    @classmethod
    def red(cls, text: str) -> None:
        """打印加粗红色文本"""
        print(cls._colorize(text, cls.COLORS['red']))
        cls._log_output(text, "red")

    @classmethod
    def green(cls, text: str) -> None:
        """打印加粗绿色文本"""
        print(cls._colorize(text, cls.COLORS['green']))
        cls._log_output(text, "green")

    @classmethod
    def yellow(cls, text: str) -> None:
        """打印加粗黄色文本"""
        print(cls._colorize(text, cls.COLORS['yellow']))
        cls._log_output(text, "yellow")

    @classmethod
    def blue(cls, text: str) -> None:
        """打印加粗蓝色文本"""
        print(cls._colorize(text, cls.COLORS['blue']))
        cls._log_output(text, "blue")

    @classmethod
    def magenta(cls, text: str) -> None:
        """打印加粗品红文本"""
        print(cls._colorize(text, cls.COLORS['magenta']))
        cls._log_output(text, "magenta")

    @classmethod
    def cyan(cls, text: str) -> None:
        """打印加粗青色文本"""
        print(cls._colorize(text, cls.COLORS['cyan']))
        cls._log_output(text, "cyan")

    @classmethod
    def white(cls, text: str) -> None:
        """打印加粗白色文本"""
        print(cls._colorize(text, cls.COLORS['white']))
        cls._log_output(text, "white")

    @classmethod
    def color_text(cls, text: str, color_name: str) -> str:
        """
        返回加粗的带颜色文本（不直接打印）
        可选颜色: red, green, yellow, blue, magenta, cyan, white
        """
        if color_name not in cls.COLORS:
            raise ValueError(f"未知颜色: {color_name}")
        return cls._colorize(text, cls.COLORS[color_name])
    
    @classmethod
    def log_info(cls, message: str):
        """记录信息日志"""
        if cls._logger is not None:
            cls._logger.info(message)
        print(f"[INFO] {message}")
    
    @classmethod
    def log_warning(cls, message: str):
        """记录警告日志"""
        if cls._logger is not None:
            cls._logger.warning(message)
        cls.yellow(f"[WARNING] {message}")
    
    @classmethod
    def log_error(cls, message: str):
        """记录错误日志"""
        if cls._logger is not None:
            cls._logger.error(message)
        cls.red(f"[ERROR] {message}")
    
    @classmethod
    def log_step(cls, step_name: str, step_description: str = ""):
        """记录执行步骤"""
        step_msg = f"=== 执行步骤: {step_name} ==="
        if step_description:
            step_msg += f" ({step_description})"
        
        if cls._logger is not None:
            cls._logger.info(step_msg)
        cls.cyan(step_msg)
    
    @classmethod
    def log_result(cls, step_name: str, result: str):
        """记录步骤结果"""
        result_msg = f"=== {step_name} 结果 ==="
        
        if cls._logger is not None:
            cls._logger.info(result_msg)
            cls._logger.info(result)
        cls.green(result_msg)
        cls.white(result)