import socket
import threading
import logging
from typing import Callable, Optional
from src.common.protocol import PacketProtocol

class Peer:
    def __init__(self, host: str, port: int, on_message_received: Callable[[dict, str], None]):
        self.host = host
        self.port = port
        self.on_message_received = on_message_received
        self.running = False
        self._server_socket = None
        self._server_thread = None
        self.logger = logging.getLogger(f"Node-{port}")

    def start(self):
        self.running = True
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        
        self._server_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._server_thread.start()

    def stop(self):
        self.running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except:
                pass

    def send_packet(self, target_host: str, target_port: int, message: dict):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0) 
                s.connect((target_host, target_port))
                data = PacketProtocol.serialize(message)
                s.sendall(data)
        except Exception as e:
            print(f"Error sending to {target_host}:{target_port} -> {e}")

    def _listen_loop(self):
        while self.running:
            try:
                client_sock, addr = self._server_socket.accept()
                client_handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True
                )
                client_handler.start()
            except OSError:
                break
            except Exception as e:
                print(f"Server error: {e}")

    def _handle_client(self, conn: socket.socket, addr):
        with conn:
            buffer = b""
            while True:
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk
                    
                    while True:
                        msg, remainder = PacketProtocol.deserialize(buffer)
                        if msg:
                            self.on_message_received(msg, addr[0])
                            buffer = remainder
                        else:
                            break
                except Exception:
                    break