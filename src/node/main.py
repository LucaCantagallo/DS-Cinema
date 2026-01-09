import sys
import threading
import time
import logging
from src.node.gui import CinemaGUI
from src.node.peer import Peer
from src.node.algorithm import RicartAgrawala
from src.common.models import LamportClock, MessageType
from src.common.protocol import PacketProtocol

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("Main")

NAMESERVER_HOST = "127.0.0.1"
NAMESERVER_PORT = 5000

class CinemaNode:
    def __init__(self, node_id, port):
        self.node_id = node_id
        self.port = port
        self.seats = [False] * 25 
        
        self.clock = LamportClock()
        self.peer = Peer(node_id, "127.0.0.1", port, self.on_network_message)
        
        self.algo = RicartAgrawala(
            node_id=node_id,
            clock=self.clock,
            peers_list_func=self.peer.get_known_peers,
            peer_transport=self.peer
        )
        
        self.gui = CinemaGUI(node_id, total_seats=25, on_seat_click=self.handle_gui_click)

    def start(self):
        self.peer.start()
        
        self.register_to_nameserver()
        
        self.gui.log(f"Node started on port {self.port}")
        self.gui.start()

    def stop(self):
        self.peer.stop()

    def register_to_nameserver(self):
        msg = {
            "type": "REGISTER",
            "node_id": self.node_id,
            "listening_port": self.port
        }
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((NAMESERVER_HOST, NAMESERVER_PORT))
                s.sendall(PacketProtocol.serialize(msg))
            logger.info("Registered to NameServer")
        except Exception as e:
            logger.error(f"Could not connect to NameServer: {e}")
            self.gui.log("ERROR: NameServer unreachable!")

    def on_network_message(self, msg, sender_ip=None):
        m_type = msg.get("type")
        
        if m_type == "SYNC":
            peers = msg.get("peers", {})
            self.peer.update_directory(peers)
            logger.info(f"Peers updated: {list(peers.keys())}")
            self.gui.log(f"Peers connected: {len(peers)}")
            return

        if m_type == "SEAT_TAKEN":
            seat_id = msg.get("seat_id")
            sender = msg.get("sender")
            self.seats[seat_id] = True
            self.gui.update_seat_color(seat_id, "#FF6347") 
            self.gui.log(f"Seat {seat_id} taken by {sender}")
            self.clock.update(msg.get("ts", 0))
            return

        if m_type in [MessageType.REQUEST, MessageType.REPLY]:
            self.algo.handle_message(msg)

    def handle_gui_click(self, seat_id):
        if self.seats[seat_id]:
            self.gui.log(f"Seat {seat_id} already taken!")
            return

        success = self.algo.request_critical_section(lambda: self._on_enter_cs(seat_id))
        
        if success:
            self.gui.log(f"Requesting seat {seat_id}...")
            self.gui.update_seat_color(seat_id, "#FFD700") 
        else:
            self.gui.log("System busy. Please wait.")

    def _on_enter_cs(self, seat_id):
        if not self.seats[seat_id]:
            self.seats[seat_id] = True
            self.gui.update_seat_color(seat_id, "#32CD32") 
            self.gui.log(f"SUCCESS: Seat {seat_id} booked!")
            
            update_msg = {
                "type": "SEAT_TAKEN",
                "seat_id": seat_id,
                "ts": self.clock.value
            }
            self.peer.broadcast(update_msg)
        else:
            self.gui.log(f"FAIL: Seat {seat_id} was stolen!")
            self.gui.update_seat_color(seat_id, "#FF6347")

        time.sleep(1) 
        self.algo.release_critical_section()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m src.node.main <node_id> <port>")
    else:
        node = CinemaNode(sys.argv[1], int(sys.argv[2]))
        try:
            node.start()
        except KeyboardInterrupt:
            node.stop()