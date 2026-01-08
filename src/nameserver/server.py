import logging
import threading

class NameServerLogic:
    def __init__(self):
        self._peers = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger("NameServer")

    def register_peer(self, node_id: str, host: str, port: int):
        with self._lock:
            self._peers[node_id] = {"host": host, "port": port}
            self.logger.info(f"Registered peer {node_id} at {host}:{port}")

    def remove_peer(self, node_id: str):
        with self._lock:
            if node_id in self._peers:
                del self._peers[node_id]
                self.logger.info(f"Removed peer {node_id}")

    def get_peers(self) -> dict:
        with self._lock:
            return self._peers.copy()