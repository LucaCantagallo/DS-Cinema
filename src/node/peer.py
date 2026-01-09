import socket
import threading
import logging
from typing import Callable, Dict, Tuple
from src.common.protocol import PacketProtocol

class Peer:
    def __init__(self, node_id: str, host: str, port: int, on_message_received: Callable[[dict, str], None]):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.on_message_received = on_message_received
        
        self.running = False
        self._server_socket = None
        self._server_thread = None
        
        self._peers_directory: Dict[str, Dict] = {}
        self._directory_lock = threading.Lock()
        
        self.logger = logging.getLogger(f"Node-{node_id}")

    def start(self):
        self.running = True
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(10)
        
        self._server_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._server_thread.start()
        self.logger.info(f"Peer started on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except:
                pass

    def update_directory(self, new_directory: Dict):
        with self._directory_lock:
            self._peers_directory = new_directory

    def get_known_peers(self):
        with self._directory_lock:
            return list(self._peers_directory.keys())

    def send_to_node(self, target_node_id: str, message: dict):
        target = None
        with self._directory_lock:
            target = self._peers_directory.get(target_node_id)
        
        if target:
            message["sender"] = self.node_id
            self._send_direct(target["host"], target["port"], message)
        else:
            self.logger.warning(f"Cannot send to {target_node_id}: unknown address")

    def broadcast(self, message: dict, exclude_self=True) -> list:
        successful_recipients = []
        dead_nodes = []

        with self._directory_lock:
            targets = list(self._peers_directory.items())

        message["sender"] = self.node_id
        
        for pid, data in targets:
            if exclude_self and pid == self.node_id:
                continue
            
            success = self._send_direct(data["host"], data["port"], message)
            
            if success:
                successful_recipients.append(pid)
            else:
                self.logger.warning(f"Detected crash of node {pid}. Removing from directory.")
                dead_nodes.append(pid)

        if dead_nodes:
            with self._directory_lock:
                for dead_id in dead_nodes:
                    self._peers_directory.pop(dead_id, None)

        return successful_recipients

    def _send_direct(self, host: str, port: int, message: dict) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((host, port))
                data = PacketProtocol.serialize(message)
                s.sendall(data)
            return True
        except Exception:
            return False

    def _listen_loop(self):
        while self.running:
            try:
                client_sock, addr = self._server_socket.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True
                ).start()
            except OSError:
                break

    def _handle_client(self, conn: socket.socket, addr):
        with conn:
            buffer = b""
            while True:
                try:
                    chunk = conn.recv(4096)
                    if not chunk: break
                    buffer += chunk
                    
                    while True:
                        msg, remainder = PacketProtocol.deserialize(buffer)
                        if msg:
                            self.on_message_received(msg)
                            buffer = remainder
                        else:
                            break
                except Exception:
                    break