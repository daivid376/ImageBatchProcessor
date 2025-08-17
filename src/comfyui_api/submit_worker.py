# src/comfyui_api/submit_worker.py
# 🔄 重构文件：主要改动
# 1. 🔄 构造函数：接收ComfyModel而不是原始tasks列表
# 2. 🆕 新增信号：task_completed和all_completed，提供更细粒度的状态反馈
# 3. 🔄 重构任务提交逻辑：使用ComfyModel管理任务状态
# 4. 🔄 优化WebSocket处理：更清晰的完成检测逻辑
# 5. 🔄 保持所有原有功能：文件等待、进度跟踪、错误处理等

import json
import os
from PyQt6.QtCore import QThread, pyqtSignal
import time as pyt
import traceback
import requests
import websocket
import threading
from .comfy_model import ComfyModel, ComfyTask  # 🆕 引入ComfyUI数据模型
from .task_completion_handler import TaskCompletionHandler  # 🆕 引入任务完成处理器

class ComfySubmitWorker(QThread):
    # 🔄 保持原有信号，🆕 新增细粒度状态信号
    status = pyqtSignal(str)           # 保持：文本状态
    progress = pyqtSignal(int, int)    # 保持：已完成, 总数
    task_completed = pyqtSignal(str)   # 🆕 新增：单个任务完成信号(prompt_id)
    all_completed = pyqtSignal()       # 🆕 新增：所有任务完成信号
    finished_ok = pyqtSignal()         # 🔄 保持：向后兼容
    failed = pyqtSignal(str)           # 保持：错误信号

    def __init__(self, client, comfy_model: ComfyModel, wait_timeout=180, wait_interval=2, parent=None):
        super().__init__(parent)
        self.client = client
        # 🔄 主要改动：接收ComfyModel而不是原始tasks列表
        # 原因：使用结构化的数据模型，便于状态管理和追踪
        self.comfy_model = comfy_model  # 🆕 ComfyUI数据模型
        
        # 🔄 保持原有配置参数
        self.wait_timeout = wait_timeout
        self.wait_interval = wait_interval
        
        # 🔄 保持原有WebSocket相关属性
        self.ws_thread = None
        self.ws = None
        self.prompt_ids = set()
        self.completed_task_ids = set()
        
        # 🆕 新增：重连相关属性
        self.is_running = False

    def run(self):
        """🔄 重构主运行逻辑，但保持原有功能流程"""
        self.is_running = True
        try:
            # 🔄 保持原有健康检查
            self.status.emit("检查端口连通性...")

            # 🔄 获取任务列表（从ComfyModel而不是self.tasks）
            pending_tasks = self.comfy_model.get_pending_tasks()
            total = len(pending_tasks)
            
            if total == 0:
                raise RuntimeError("没有待处理任务")

            print(f"📋 准备处理 {total} 个任务")

            # 🔄 保持原有WebSocket启动逻辑
            if not self._start_ws_listener():
                raise RuntimeError("WebSocket连接失败")

            # 🔄 重构任务提交循环，使用ComfyTask对象
            for i, task in enumerate(pending_tasks):
                if not self.is_running:
                    break
                self._submit_single_task(task)  # 🆕 提取为独立方法
                self.progress.emit(i + 1, total)

            if self.is_running:
                self.status.emit("全部任务已提交，等待WebSocket推送完成事件...")
                # 🔄 注意：不再直接emit finished_ok，而是等待WebSocket事件

        except Exception as e:
            tb = traceback.format_exc(limit=5)
            self.failed.emit(f"{e}\n{tb}")
        finally:
            self.is_running = False

    def _submit_single_task(self, task: ComfyTask):
        """
        🆕 新增方法：提交单个ComfyTask
        职责：处理单个任务的文件等待和提交逻辑
        """
        # 🔄 保持原有文件等待逻辑
        if task.rel_tmp_input_path:
            self.status.emit(f"等待文件同步到服务器: {task.rel_tmp_input_path}")
            if not self.client.is_mock:
                self._wait_input(task.rel_tmp_input_path)

        # 🔄 保持原有提交逻辑
        self.status.emit("提交任务到 /prompt ...")
        print('client in using: ', self.client)
        prompt_id = self.client.submit(task.payload)
        self.comfy_model.register_task_prompt_id(task, prompt_id)
        
        # 🔄 更新任务状态（现在使用ComfyModel管理）
        task.status = "submitted"
        self.prompt_ids.add(prompt_id)
        
        self.status.emit(f"任务已提交，prompt_id: {prompt_id}")
        print(f"✅ 任务提交成功: {task.image_path} -> {prompt_id}")
        if self.client.is_mock:
            self._handle_task_complete(prompt_id)
    def _wait_input(self, rel_input: str):
        """🔄 保持原有文件等待逻辑，无改动"""
        if "/" not in rel_input:
            raise ValueError(f"rel_input 格式应为 'subfolder/filename': {rel_input}")
        subfolder, filename = rel_input.split("/", 1)

        deadline = pyt.time() + self.wait_timeout
        last_status = None
        while pyt.time() < deadline:
            try:
                r = self.client.session.get(
                    f"{self.client.base_url}/view",
                    params={"filename": filename, "subfolder": subfolder, "type": "input"},
                    timeout=5
                )
                last_status = r.status_code
                if r.status_code == 200:
                    return
            except Exception as ex:
                last_status = str(ex)

            self.status.emit(f"等待中（最后状态: {last_status}）...")
            self.msleep(int(self.wait_interval * 1000))

        raise TimeoutError(f"等待文件可读超时: {rel_input}，最后状态: {last_status}")

    def _start_ws_listener(self):
        """🔄 保持原有WebSocket启动逻辑，🆕 添加代理绕过和连接状态检测"""
        ws_url = f"ws://{self.client.host}:{self.client.port}/ws"
        self.status.emit(f"连接 WebSocket: {ws_url}")

        # 🆕 添加连接状态标志
        self.ws_connected = False
        self.ws_connect_error = None

        def on_open(ws):
            self.ws_connected = True
            self.status.emit("WebSocket连接已建立")

        def on_error(ws, error):
            self.ws_connect_error = error
            self._on_ws_error(ws, error)

        def run_ws():
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=self._on_ws_message,
                on_error=on_error,
                on_close=self._on_ws_close
            )
            # 绕过代理设置，避免本地服务器连接问题
            self.ws.run_forever(http_proxy_host=None, http_proxy_port=None, proxy_type=None)

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()
        
        # 🆕 等待连接建立或失败（最多等待5秒）
        import time
        for _ in range(50):  # 50 * 0.1 = 5秒
            if self.ws_connected:
                return True
            if self.ws_connect_error:
                self.status.emit(f"WebSocket连接错误: {self.ws_connect_error}")
                return False
            time.sleep(0.1)
        
        self.status.emit("WebSocket连接超时")
        return False

  
    def _get_task_history(self, pid: str):
        """🆕 抽象化获取任务历史记录"""
        # 真实模式：保持原有的轮询等待逻辑
        max_wait = 10
        start_time = pyt.time()
        hist = {}
        print('im get task history')
        while pyt.time() - start_time < max_wait:
            
            print(f"🌐 发送HTTP请求... 已等待{int(pyt.time() - start_time)}秒")
            if self.client.is_mock:
                return self.client.get_history(pid)
            r = requests.get(f"{self.client.base_url}/history/{pid}", timeout=5).json()
            print('r: ', r)
            
            print(f"🌐 HTTP响应状态: {r.status_code}")
            if pid in r and "outputs" in r[pid] and r[pid]["outputs"]:
                hist = r
                break
            self.msleep(500)
        else:
            raise TimeoutError(f"history/{pid} 超时未写入")
        return hist

    def _on_ws_message(self, ws, message):
        """🔄 保持原有WebSocket消息处理逻辑"""
        try:
            data = json.loads(message)
            ptype = data.get("type")
            pdata = data.get("data", {})
            pid = pdata.get("prompt_id")
            
            # 只处理我们自己提交的任务
            if pid and pid in self.prompt_ids:
                if ptype == "executed":
                    self.status.emit(f"[{pid}] 节点执行完成: {pdata.get('node_id')}")
                elif ptype == "progress":
                    self._handle_progress_update(pid, pdata)
                elif ptype == "execution_success":
                    self.status.emit(f"[{pid}] 任务执行成功")
                    print(f'✅ 检测到任务完成: {pid}')
        except Exception as e:
            self.status.emit(f"WebSocket 消息解析失败: {e}")

    def _on_ws_error(self, ws, error):
        """🔄 保持原有WebSocket错误处理"""
        self.status.emit(f"WebSocket 错误: {error}")

    def _on_ws_close(self, ws, code, msg):
        """🔄 保持原有WebSocket关闭处理"""
        self.status.emit("WebSocket 连接已关闭")

    def _handle_progress_update(self, pid: str, pdata: dict):
        """🔄 重构进度处理逻辑，增加完成检测"""
        value = pdata.get("value", 0)
        maxv = pdata.get("max", 1)

        # 🔄 保持原有进度显示
        self.status.emit(f"[{pid}] 进度: {value}/{maxv}")

        # 🔄 保持原有进度条更新
        if maxv > 0:
            self.progress.emit(value, maxv)

        # 🔄 重构任务完成检测逻辑
        if value >= maxv:
            print(f'🎯 任务进度完成: {pid}')
            self._handle_task_complete(pid)

    def _handle_task_complete(self, pid: str):
        """🔄 重构任务完成处理逻辑 - 修复文件延迟问题"""
        if pid in self.completed_task_ids:
            print(f"⚠️ 任务 {pid} 已经处理过，跳过")
            return
        self.completed_task_ids.add(pid)
        try:
            # 🔄 保持原有history获取逻辑，现在抽象为独立方法
            self.status.emit(f"[{pid}] 等待 history 写入...")
            print("=== ComfyModel 状态检查 ===")
            print(f"tmp_img_output_dir: {self.comfy_model.tmp_img_output_dir}")
            print(f"get_tmp_output_dir(): {self.comfy_model.get_tmp_output_dir()}")
            print(f"get_tmp_output_dir_str(): {self.comfy_model.get_output_dir()}")
            
            # 🆕 调用抽象化的history获取方法（真实模式保持原有等待逻辑）
            hist = self._get_task_history(pid)
            

            # 🆕 增加文件等待逻辑
            completion_handler = TaskCompletionHandler(file_wait_timeout=15)
            final_path = completion_handler.handle_completion(self.comfy_model, pid, hist)
            # 3. 根据结果处理
            if final_path:
                self.status.emit(f"文件已保存: {os.path.basename(final_path)}")
                self._finalize_completion(pid)
            else:
                self.status.emit(f"文件处理失败")
        except Exception as e:
            self.status.emit(f"[{pid}] 获取结果或搬运文件失败: {e}")
            print(f"❌ 任务完成处理失败: {pid}, 错误: {e}")

    def _finalize_completion(self, pid: str):
        """完成任务的最终处理"""
        # 更新状态
        self.comfy_model.update_task_status(pid, "completed")
        
        # 发出信号
        self.task_completed.emit(pid)
        
        # 检查是否全部完成
        if self.comfy_model.is_all_completed():
            print("🎉 所有任务已完成")
            self.all_completed.emit()
            self.finished_ok.emit()
            if self.ws:
                self.ws.close()
        
        self.status.emit(f"[{pid}] 任务处理完成")

    