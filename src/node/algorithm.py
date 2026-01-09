import threading
import logging
from enum import Enum
from src.common.models import MessageType
import time

class State(Enum):
    RELEASED = 0
    WANTED = 1
    HELD = 2

class RicartAgrawala:
    def __init__(self, node_id, clock, peers_list_func, peer_transport):
        self.node_id = node_id
        self.clock = clock
        self.get_peers = peers_list_func
        self.transport = peer_transport 
        
        self.state = State.RELEASED
        self.request_ts = 0
        self.replies_received = 0
        self.deferred_queue = []
        
        self._lock = threading.Lock()
        self._entry_callback = None
        self.logger = logging.getLogger(f"Algo-{node_id}")

    def request_critical_section(self, callback):
        with self._lock:
            if self.state != State.RELEASED:
                self.logger.warning("Attempted to request CS while already WANTED/HELD. Ignoring.")
                return False 

            self.state = State.WANTED
            self.clock.increment()
            self.request_ts = self.clock.value
            self.replies_received = 0
            self._entry_callback = callback
            
            others = [p_id for p_id in self.get_peers() if p_id != self.node_id]
            num_others = len(others)
            
            self.logger.info(f"REQUESTING CS at TS {self.request_ts}. Waiting for {num_others} replies.")

        if num_others == 0:
            self._enter_critical_section()
            return True

        msg = {
            "type": MessageType.REQUEST,
            "sender": self.node_id,
            "ts": self.request_ts
        }
        self.transport.broadcast(msg, exclude_self=True)
        return True

    def handle_message(self, msg):
        msg_type = msg.get("type")
        sender = msg.get("sender")
        ts = msg.get("ts", 0)
        
        self.clock.update(ts)

        if msg_type == MessageType.REQUEST:
            time.sleep(3)
            self._handle_request(sender, ts)
        elif msg_type == MessageType.REPLY:
            self._handle_reply()

    def _handle_request(self, sender, ts):
        with self._lock:
            my_ts = self.request_ts
            defer = False
            
            if self.state == State.HELD:
                defer = True
            elif self.state == State.WANTED:
                if (my_ts < ts) or (my_ts == ts and self.node_id < sender):
                    defer = True
            
            if defer:
                self.logger.info(f"Deferred REQUEST from {sender}")
                self.deferred_queue.append(sender)
            else:
                self.logger.info(f"Replying to {sender}")
                self._send_reply(sender)

    def _handle_reply(self):
        with self._lock:
            self.replies_received += 1
            others = [p for p in self.get_peers() if p != self.node_id]
            others_count = len(others)
            
            self.logger.info(f"Reply received. Total: {self.replies_received}/{others_count}")
            
            if self.state == State.WANTED and self.replies_received >= others_count:
                self._enter_critical_section()

    def _enter_critical_section(self):
        self.state = State.HELD
        self.logger.info(">>> ENTERED CRITICAL SECTION <<<")
        if self._entry_callback:
            threading.Thread(target=self._entry_callback).start()

    def release_critical_section(self):
        with self._lock:
            self.logger.info("Exiting CS. Replying to deferred.")
            self.state = State.RELEASED
            for target in self.deferred_queue:
                self._send_reply(target)
            self.deferred_queue.clear()

    def _send_reply(self, target_id):
        msg = {
            "type": MessageType.REPLY,
            "sender": self.node_id,
            "ts": self.clock.value
        }
        self.transport.send_to_node(target_id, msg)