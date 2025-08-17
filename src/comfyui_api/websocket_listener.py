# src/comfyui_api/websocket_listener.py
# WebSocket监听器 - 专门处理WebSocket通信

import json
import websocket
from PyQt6.QtCore import QThread, pyqtSignal

class WebSocketListener(QThread):
    """WebSocket监听器 - 只负责接收和转发消息"""
    
    message_received = pyqtSignal(dict)
    connection_closed = pyqtSignal()
    
    def __init__(self, host: str, port: int, prompt_ids: set):
        super().__init__()
        self.url = f"ws://{host}:{port}/ws"
        self.prompt_ids = prompt_ids  # 要监听的任务ID集合
        self.ws = None
        self.running = False
    
    def run(self):
        """运行WebSocket监听"""
        self.running = True
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self.on_message,
            on_close=self.on_close
        )
        # 绕过代理
        self.ws.run_forever(http_proxy_host=None, http_proxy_port=None)
    
    def on_message(self, ws, message):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            # 只处理我们关心的任务
            prompt_id = data.get("data", {}).get("prompt_id")
            if prompt_id and prompt_id in self.prompt_ids:
                self.message_received.emit(data)
        except:
            pass
    
    def on_close(self, ws, close_status_code, close_msg):
        """连接关闭"""
        self.running = False
        self.connection_closed.emit()
    
    def stop(self):
        """停止监听"""
        self.running = False
        if self.ws:
            self.ws.close()