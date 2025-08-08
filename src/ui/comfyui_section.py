from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel, QProgressBar, QFileDialog, QMessageBox, QHBoxLayout,QLineEdit
from PyQt6.QtCore import Qt,QTimer,pyqtSignal,QSettings
from PyQt6.QtGui import QIcon
import os

from src import get_resource_path
from src.ui.common_widgets import CustomComboBox
from src.config import GlobalConfig

class ComfyUISection(QWidget):
    submit_comfy_task = pyqtSignal(dict) 
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ComfyUI 任务管理")
        self.settings = QSettings(GlobalConfig.APP_ORG, GlobalConfig.APP_NAME)
        
        layout = QVBoxLayout(self)
        self.local_network_root = None

        # Add section label
        self.title_label = QLabel("ComfyUI 任务管理", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        
        folder_layout = QHBoxLayout()
        # 本地共享网盘根目录输入框
        self.local_network_drive_input = QLineEdit(self)
        self.local_network_drive_input.setObjectName("local_network_drive_input")
        self.local_network_drive_input.setProperty("persist", True)
        self.local_network_drive_input.setPlaceholderText("选择本地共享网盘根目录")
        
        self.local_network_drive_input.returnPressed.connect(self.update_from_input_dir)
        self.local_network_drive_input.editingFinished.connect(self.update_from_input_dir) 
        lastPath = self.settings.value("local_network_drive_input", "")
        self.local_network_drive_input.setText(lastPath)
        

        # 按钮选择共享网盘目录
        self.select_folder_button = QPushButton("选择文件夹", self)
        self.select_folder_button.clicked.connect(self.select_folder)

        folder_layout.addWidget(self.local_network_drive_input)
        folder_layout.addWidget(self.select_folder_button)

        # 添加到主布局中
        layout.addLayout(folder_layout)
        # 工作流选择
        self.workflow_label = QLabel("选择工作流:", self)
        self.workflow_select = CustomComboBox(self.load_workflows,self)
        self.load_workflows()  # 加载工作流文件
        
        # 设置 QComboBox 更窄的宽度
        self.workflow_select.setFixedWidth(200)

        # 创建一行布局，包含标签和 QComboBox
        workflow_layout = QHBoxLayout()
        workflow_layout.addWidget(self.workflow_label, alignment=Qt.AlignmentFlag.AlignLeft)  # Align left
        workflow_layout.addWidget(self.workflow_select)
        workflow_layout.addStretch(0)  # Remove any additional space
        layout.addLayout(workflow_layout)


        # 提示词选择
        self.prompt_label = QLabel("选择提示词:", self)
        self.prompt_select = CustomComboBox(self.load_prompts, self)
        self.load_prompts()  # 加载提示词文件
        
        # 设置 QComboBox 更窄的宽度
        self.prompt_select.setFixedWidth(200)

        # 创建一行布局，包含标签和 QComboBox
        prompt_layout = QHBoxLayout()
        prompt_layout.addWidget(self.prompt_label, alignment=Qt.AlignmentFlag.AlignLeft)
        prompt_layout.addWidget(self.prompt_select)
        prompt_layout.addStretch(0) 
        layout.addLayout(prompt_layout)

        # 提交按钮
        self.submit_button = QPushButton("提交任务", self)
        self.submit_button.setIcon(QIcon("path/to/submit_icon.ico"))  # Optional icon for the button
        self.submit_button.clicked.connect(self.submit_task)
        layout.addWidget(self.submit_button)

        # 创建一行布局用于进度显示
        progress_layout = QHBoxLayout()

        # 进度文本
        self.progress_label = QLabel("任务进度:", self)

        # 进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)  # 可选：是否显示百分比文字

        # 添加到同一行
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)

        # 添加行布局到主布局
        layout.addLayout(progress_layout)

        self.setLayout(layout)
        
        #开始时需要调用函数区
        self.update_from_input_dir()
    def _update_project_paths(self):
        root_text = self.local_network_drive_input.text().strip()
        self.local_network_root = Path(root_text)
        self.comfy_assets_dir = self.local_network_root / GlobalConfig.code_project_root_rel_dir / GlobalConfig.comfy_assets_rel_dir
        
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择共享网盘根目录")
        if folder:
            self.local_network_drive_input.setText(folder)
            self.update_from_input_dir()
    
    def load_workflows(self):
        self._update_project_paths()
        workflows_dir = self.comfy_assets_dir/ "workflows"
        self.workflow_select.clear()
        if not workflows_dir.is_dir():
            self.workflow_select.addItem("<空>")
            return
        else:
            files = [f for f in workflows_dir.glob("*.json") if f.is_file()]
        if files:
            for f in files:
                self.workflow_select.addItem(f.name)
        else:
            self.workflow_select.addItem("<空>")

    def load_prompts(self):
        self._update_project_paths()
        prompts_dir = self.comfy_assets_dir/ "prompts"
        self.prompt_select.clear()
        if not prompts_dir.is_dir():
            self.prompt_select.addItem("<空>")
            return
        else:
            files = [f for f in prompts_dir.glob("*.txt") if f.is_file()]
        if files:
            for f in files:
                self.prompt_select.addItem(f.name)
        else:
            self.prompt_select.addItem("<空>")
    def update_from_input_dir(self):
        input_dir = self.local_network_drive_input.text().strip()
        self.local_network_root = Path(input_dir)
        self.load_workflows()
        self.load_prompts()

    def submit_task(self):
        """提交任务（仅负责收集UI选项）"""

        # Step 1: 获取用户在界面中选择的内容
        selected_workflow = self.workflow_select.currentText()
        selected_prompt = self.prompt_select.currentText()
        base_dir = self.local_network_drive_input.text().strip()

        # Step 2: 简单校验
        if not selected_workflow or selected_workflow == "<空>":
            self.show_error("请选择工作流文件！")
            return
        if not selected_prompt or selected_prompt == "<空>":
            self.show_error("请选择提示词文件！")
            return
        if not os.path.isdir(base_dir):
            self.show_error("共享根目录无效")
            return

        # Step 3: 收集信息传给 presenter/manager
        workflow_path = get_resource_path(os.path.join("comfyui_assets", "workflows", selected_workflow))
        prompt_path = get_resource_path(os.path.join("comfyui_assets", "prompts", selected_prompt))

        # 这里不处理任务，只发送给上层
        self.submit_comfy_task.emit({
            "workflow_path": workflow_path,
            "prompt_path": prompt_path,
            "local_network_drive_dir": base_dir
        })
