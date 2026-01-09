import socket
import threading
import logging
import sys
from src.common.protocol import PacketProtocol
from src.nameserver.server import NameServerLogic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NameServerNode")

HOST = "127.0.0.1"
PORT = 5000

class NameServerNode:
    def __init__(self):
        self.logic = NameServerLogic()
        self.running = False
        
    def start(self):
        self.running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen(5)
            logger.info(f"NameServer running on {HOST}:{PORT}")
            
            while self.running:
                try:
                    conn, addr = s.accept()
                    threading.Thread(target=self._handle_client, args=(conn,)).start()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Accept error: {e}")

    def _handle_client(self, conn):
        with conn:
            try:
                chunk = conn.recv(4096)
                if not chunk: return
                msg, _ = PacketProtocol.deserialize(chunk)
                
                if not msg: return
                
                msg_type = msg.get("type")
                
                if msg_type == "REGISTER":
                    node_id = msg.get("node_id")
                    port = msg.get("listening_port")
                    host = "127.0.0.1" 
                    
                    self.logic.register_peer(node_id, host, port)
                    
                    self._broadcast_update()
                    
            except Exception as e:
                logger.error(f"Handler error: {e}")

    def _broadcast_update(self):
        peers = self.logic.get_peers()
        logger.info(f"Broadcasting update to {len(peers)} peers")
        
        update_msg = {
            "type": "SYNC",
            "peers": peers
        }
        
        for pid, info in peers.items():
            try:
                self._send_packet(info['host'], info['port'], update_msg)
            except Exception as e:
                logger.warning(f"Failed to update peer {pid}: {e}")
                
    def _send_packet(self, host, port, msg):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((host, port))
            s.sendall(PacketProtocol.serialize(msg))

if __name__ == "__main__":
    try:
        ns = NameServerNode()
        ns.start()
    except KeyboardInterrupt:
        print("\nShutting down NameServer...")