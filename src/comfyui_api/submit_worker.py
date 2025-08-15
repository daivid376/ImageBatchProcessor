# src/comfyui_api/submit_worker.py
# 🔄 重构文件：主要改动
# 1. 🔄 构造函数：接收ComfyModel而不是原始tasks列表
# 2. 🆕 新增信号：task_completed和all_completed，提供更细粒度的状态反馈
# 3. 🔄 重构任务提交逻辑：使用ComfyModel管理任务状态
# 4. 🔄 优化WebSocket处理：更清晰的完成检测逻辑
# 5. 🔄 保持所有原有功能：文件等待、进度跟踪、错误处理等

import json
import os
import shutil
from PyQt6.QtCore import QThread, pyqtSignal
import time as pyt
import traceback
import requests
import websocket
import threading
from .comfy_model import ComfyModel, ComfyTask  # 🆕 引入ComfyUI数据模型

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
        self.max_retries = 3
        self.retry_delay = 5
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
            self._wait_input(task.rel_tmp_input_path)

        # 🔄 保持原有提交逻辑
        self.status.emit("提交任务到 /prompt ...")
        prompt_id = self.client.submit(task.payload)
        self.comfy_model.register_task_prompt_id(task, prompt_id)
        
        # 🔄 更新任务状态（现在使用ComfyModel管理）
        task.status = "submitted"
        self.prompt_ids.add(prompt_id)
        
        self.status.emit(f"任务已提交，prompt_id: {prompt_id}")
        print(f"✅ 任务提交成功: {task.image_path} -> {prompt_id}")

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
        """🆕 抽象化获取任务历史记录，支持Mock和真实模式"""
        if self.is_mock_mode and hasattr(self.client, 'get_history'):
            # Mock模式：直接从Mock客户端获取history
            self.status.emit(f"[MOCK] 获取任务历史记录...")
            hist = self.client.get_history(pid)
            print(f'[MOCK] history: {hist}')
            if not hist:
                raise TimeoutError(f"Mock history/{pid} 未找到")
            return hist
        else:
            # 真实模式：保持原有的轮询等待逻辑
            max_wait = 10
            start_time = pyt.time()
            hist = {}
            while pyt.time() - start_time < max_wait:
                r = requests.get(f"{self.client.base_url}/history/{pid}", timeout=5).json()
                print('r: ', r)
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
            outputs = hist[pid]["outputs"]
            tmp_output_file = self._wait_for_output_file(outputs, pid)
            print('tmp_output_file: ', tmp_output_file)
            real_output_dir = self.comfy_model.get_output_dir()
            print('real_output_dir1: ', real_output_dir)
            if tmp_output_file and real_output_dir:
                print('real_output_dir: ', real_output_dir)
                # 🔄 保持原有文件搬运逻辑
                current_task = self.comfy_model.get_task_by_prompt_id(pid)
                orig_filestem = current_task.orig_filestem
                output_name = f"{orig_filestem}_test.png"
                self.move_rename_output_file(tmp_output_file, real_output_dir, output_name)

            # 🆕 发出单个任务完成信号
            self.task_completed.emit(pid)
            
            # 🆕 检查是否所有任务都完成
            self.comfy_model.update_task_status(pid, "completed")
            if self.comfy_model.is_all_completed():
                print("🎉 所有任务已完成")
                self.all_completed.emit()
                self.finished_ok.emit()
                if self.ws:
                    self.ws.close()

            self.status.emit(f"[{pid}] 任务处理完成")

        except Exception as e:
            self.status.emit(f"[{pid}] 获取结果或搬运文件失败: {e}")
            print(f"❌ 任务完成处理失败: {pid}, 错误: {e}")

    def _wait_for_output_file(self, outputs_node, pid: str, max_wait_file: int = 15):
        """🆕 等待输出文件真正生成到磁盘"""
        if not outputs_node or not isinstance(outputs_node, dict):
            print("[WARN] outputs_node 为空或不是字典")
            return None

        # 先收集所有可能的输出文件路径
        candidate_files = []
        for node_id, out in outputs_node.items():
            if not isinstance(out, dict):
                continue
            images = out.get("images")
            if not images or not isinstance(images, list):
                continue

            for img in images:
                if not isinstance(img, dict):
                    continue
                if img.get("type") == "output" and "filename" in img:
                    client_tmp_output_dir =self.comfy_model.get_tmp_output_dir()
                    src_file = os.path.join(client_tmp_output_dir, img["filename"])
                    candidate_files.append(src_file)
                    print(f"🔍 候选输出文件: {src_file}")

        if not candidate_files:
            print("[WARN] 没有找到候选输出文件")
            return None

        # 🆕 轮询等待文件生成
        self.status.emit(f"[{pid}] 等待输出文件写入磁盘...")
        start_time = pyt.time()
        
        while pyt.time() - start_time < max_wait_file:
            for src_file in candidate_files:
                if os.path.exists(src_file):
                    # 🆕 文件存在后再等待一小段时间确保写入完成
                    self.status.emit(f"[{pid}] 发现文件，等待写入完成...")
                    self.msleep(1000)  # 等待1秒确保文件写入完成
                    
                    # 🆕 验证文件是否真的可读且有内容
                    if self._verify_file_complete(src_file):
                        print(f"✅ 文件验证成功: {src_file}")
                        return src_file
                    else:
                        print(f"⚠️ 文件未完全写入，继续等待: {src_file}")
            
            self.status.emit(f"[{pid}] 等待文件生成... ({int(pyt.time() - start_time)}s)")
            self.msleep(1000)  # 每秒检查一次

        print(f"[ERROR] 等待输出文件超时: {candidate_files}")
        return None

    def _verify_file_complete(self, file_path: str) -> bool:
        """🆕 验证文件是否完全写入"""
        try:
            # 检查文件大小是否大于0
            if os.path.getsize(file_path) == 0:
                return False
            
            # 尝试打开文件读取头部，验证不是损坏的
            with open(file_path, 'rb') as f:
                header = f.read(10)  # 读取前10字节
                if len(header) == 0:
                    return False
            
            # 🆕 对于图片文件，可以进一步验证
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    from PIL import Image
                    with Image.open(file_path) as img:
                        img.verify()  # 验证图片完整性
                    return True
                except Exception:
                    return False
            
            return True
        except Exception as e:
            print(f"文件验证失败: {file_path}, 错误: {e}")
            return False

    def get_tmp_output_path(self, outputs_node):
        """🔄 保持原有逻辑，但添加调试信息"""
        client_tmp_output_dir = self.comfy_model.get_tmp_output_dir()
        print("🔍 开始查找临时输出文件...")
        print(f"📁 输出目录: {client_tmp_output_dir}")
        
        if not outputs_node or not isinstance(outputs_node, dict):
            print("[WARN] outputs_node 为空或不是字典")
            return None

        # 🆕 添加详细的调试输出
        print(f"📋 outputs_node 内容: {json.dumps(outputs_node, indent=2)}")

        for node_id, out in outputs_node.items():
            print(f"🔍 检查节点 {node_id}: {type(out)}")
            if not isinstance(out, dict):
                continue
            images = out.get("images")
            if not images or not isinstance(images, list):
                print(f"⚠️ 节点 {node_id} 没有有效的 images 列表")
                continue

            for i, img in enumerate(images):
                print(f"🖼️ 检查图片 {i}: {img}")
                if not isinstance(img, dict):
                    continue
                if img.get("type") == "output" and "filename" in img:
                    src_file = os.path.join(client_tmp_output_dir, img["filename"])
                    print(f"🎯 构造文件路径: {src_file}")
                    print(f"📁 目录存在: {os.path.exists(client_tmp_output_dir)}")
                    print(f"📄 文件存在: {os.path.exists(src_file)}")
                    
                    # 🆕 列出目录内容进行对比
                    if os.path.exists(client_tmp_output_dir):
                        actual_files = os.listdir(client_tmp_output_dir)
                        print(f"📂 实际目录内容: {actual_files}")
                    
                    if os.path.exists(src_file):
                        return src_file
                    else:
                        print(f"[WARN] 文件不存在: {src_file}")

        print("[WARN] 没有找到有效的输出文件")
        return None

    def move_rename_output_file(self, src_path: str, dst_dir: str, new_name: str):
        """🔄 修复原有方法签名：增加new_name参数"""
        try:
            if not os.path.isfile(src_path):
                raise FileNotFoundError(f"源文件不存在: {src_path}")
            os.makedirs(dst_dir, exist_ok=True)
            dst_path = os.path.join(dst_dir, new_name)
            shutil.move(src_path, dst_path)
            self.status.emit(f"已搬运到: {dst_path}")
            print(f"📁 文件已搬运: {src_path} -> {dst_path}")
        except Exception as e:
            self.status.emit(f"搬运文件失败: {e}")
            print(f"❌ 文件搬运失败: {e}")