# src/submit_worker.py
from PyQt6.QtCore import QThread, pyqtSignal
import time as pyt
import traceback

class ComfySubmitWorker(QThread):
    status = pyqtSignal(str)           # 文本状态
    progress = pyqtSignal(int, int)    # 已完成, 总数
    finished_ok = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, client, tasks, wait_timeout=180, wait_interval=2, parent=None):
        super().__init__(parent)
        self.client = client
        self.tasks = tasks
        self.wait_timeout = wait_timeout
        self.wait_interval = wait_interval

    def run(self):
        try:
            # 1) 健康检查
            self.status.emit("检查端口连通性...")
            if not self.client.is_port_open():
                raise RuntimeError("ComfyUI 端口无法访问")

            self.status.emit("检查服务状态...")
            if not self.client.is_comfy_alive():
                raise RuntimeError("ComfyUI 未响应 /system_stats")

            total = len(self.tasks)
            done = 0

            # 2) 逐任务等待 → 提交
            for t in self.tasks:
                rel_input = t.get("rel_input")
                if rel_input:
                    self.status.emit(f"等待文件同步到服务器: {rel_input}")
                    self._wait_input(rel_input)

                self.status.emit("提交任务到 /prompt ...")
                self.client.submit(t["payload"])

                done += 1
                self.progress.emit(done, total)

            self.status.emit("全部任务已提交。")
            self.finished_ok.emit()

        except Exception as e:
            tb = traceback.format_exc(limit=5)
            self.failed.emit(f"{e}\n{tb}")

    def _wait_input(self, rel_input: str):
        # 轻量轮询，避免卡 UI（在子线程里不会卡主界面）
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
