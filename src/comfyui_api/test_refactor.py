# src/comfyui_api/test_refactor.py
# 🧪 测试重构后的ComfyUI模块功能完整性

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.ImageBatchProcessor_model import ImageBatchModel
from src.comfyui_api.workflow_service import WorkflowService
from src.comfyui_api.comfy_model import ComfyModel, ComfyTask


class ComfyUIRefactorTest:
    """测试重构后的ComfyUI模块架构"""
    
    def __init__(self):
        self.app = QApplication([])
        self.main_model = ImageBatchModel()
        self.workflow_service = WorkflowService()
        
    def test_workflow_service_creation(self):
        """测试WorkflowService创建"""
        print("🧪 测试1: WorkflowService创建")
        try:
            service = WorkflowService()
            assert service is not None
            assert hasattr(service, 'comfy_model')
            assert hasattr(service, 'client')
            print("✅ WorkflowService创建成功")
            return True
        except Exception as e:
            print(f"❌ WorkflowService创建失败: {e}")
            return False
    
    def test_comfy_model_functionality(self):
        """测试ComfyModel基本功能"""
        print("🧪 测试2: ComfyModel功能")
        try:
            model = ComfyModel()
            
            # 测试任务管理
            task = ComfyTask(
                image_path="test_image.jpg",
                rel_input="test/input.jpg", 
                payload={"test": "payload"}
            )
            
            model.add_task(task)
            assert model.get_total_tasks() == 1
            
            pending = model.get_pending_tasks()
            assert len(pending) == 1
            assert pending[0].status == "pending"
            
            # 测试prompt_id注册
            model.register_task_prompt_id(task, "test_prompt_123")
            assert task.prompt_id == "test_prompt_123"
            
            retrieved_task = model.get_task_by_prompt_id("test_prompt_123")
            assert retrieved_task == task
            
            print("✅ ComfyModel功能测试通过")
            return True
        except Exception as e:
            print(f"❌ ComfyModel功能测试失败: {e}")
            return False
    
    def test_workflow_service_validation(self):
        """测试WorkflowService输入验证"""
        print("🧪 测试3: WorkflowService输入验证")
        try:
            service = WorkflowService()
            
            # 测试空文件列表验证
            empty_model = ImageBatchModel()
            task_info = {
                "workflow_path": "fake_path.json",
                "prompt_path": "fake_prompt.txt", 
                "local_network_drive_dir": "/fake/path"
            }
            
            # 连接错误信号
            error_received = []
            service.error_occurred.connect(lambda msg: error_received.append(msg))
            
            success = service.submit_tasks(empty_model, task_info)
            assert not success
            assert len(error_received) > 0
            assert "没有选择图片文件" in error_received[0]
            
            print("✅ WorkflowService输入验证测试通过")
            return True
        except Exception as e:
            print(f"❌ WorkflowService输入验证测试失败: {e}")
            return False
    
    def test_signal_connections(self):
        """测试信号连接机制"""
        print("🧪 测试4: 信号连接机制")
        try:
            service = WorkflowService()
            
            # 测试信号是否存在
            assert hasattr(service, 'status_updated')
            assert hasattr(service, 'progress_updated')
            assert hasattr(service, 'task_completed')
            assert hasattr(service, 'all_tasks_completed')
            assert hasattr(service, 'error_occurred')
            
            # 测试信号连接（简单测试）
            signal_received = []
            service.status_updated.connect(lambda msg: signal_received.append(msg))
            
            # 手动发射信号测试
            service.status_updated.emit("测试状态")
            assert len(signal_received) == 1
            assert signal_received[0] == "测试状态"
            
            print("✅ 信号连接机制测试通过")
            return True
        except Exception as e:
            print(f"❌ 信号连接机制测试失败: {e}")
            return False
    
    def test_directory_management(self):
        """测试目录管理功能"""
        print("🧪 测试5: 目录管理功能")
        try:
            service = WorkflowService()
            
            # 测试输出目录设置
            test_output_dir = "/test/output"
            service.set_output_dir(test_output_dir)
            assert service.comfy_model.get_output_dir() == test_output_dir
            
            # 测试临时输出目录设置
            test_network_dir = "/test/network"
            service.set_tmp_img_output_dir(test_network_dir)
            expected_tmp_dir = os.path.join(
                test_network_dir, 
                "100_Tools/ImageBatchProcessor",
                "AI_process_temp/comfy_api_output"
            )
            actual_tmp_dir = service.comfy_model.get_tmp_output_dir()
            assert actual_tmp_dir == expected_tmp_dir
            
            print("✅ 目录管理功能测试通过")
            return True
        except Exception as e:
            print(f"❌ 目录管理功能测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始ComfyUI重构功能测试...")
        print("=" * 50)
        
        tests = [
            self.test_workflow_service_creation,
            self.test_comfy_model_functionality, 
            self.test_workflow_service_validation,
            self.test_signal_connections,
            self.test_directory_management
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            print("-" * 30)
        
        print("=" * 50)
        print(f"🎯 测试结果: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有测试通过！重构成功！")
            return True
        else:
            print("⚠️  部分测试失败，需要进一步检查")
            return False


def main():
    """主函数"""
    print("ComfyUI模块重构测试")
    print("目的：验证轻量级MVP重构后的功能完整性")
    
    tester = ComfyUIRefactorTest()
    
    # 设置5秒后自动退出（避免Qt应用阻塞）
    QTimer.singleShot(100, lambda: [
        tester.run_all_tests(),
        tester.app.quit()
    ])
    
    # 运行Qt应用（处理信号槽）
    tester.app.exec()
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    main()