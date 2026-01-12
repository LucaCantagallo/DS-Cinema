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

        self.seats = [None] * 25 
        
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
        sender = msg.get("sender")

        if m_type == "SYNC":
            peers = msg.get("peers", {})
            old_peers_count = len(self.peer.get_known_peers())
            self.peer.update_directory(peers)
            
            known = self.peer.get_known_peers()
            if old_peers_count == 0 and len(known) > 0:
                others = [pid for pid in known if pid != self.node_id]
                if others:
                    target = others[0]
                    self.gui.log(f"Syncing state from {target}...")
                    self._request_state_from_peer(target)
            return

        if m_type == MessageType.STATE_REQUEST:
            response = {
                "type": MessageType.STATE_REPLY,
                "seats": self.seats, 
                "sender": self.node_id
            }
            self.peer.send_to_node(sender, response)
            return

        if m_type == MessageType.STATE_REPLY:
            new_seats = msg.get("seats")
            self.seats = new_seats
            self._refresh_gui()
            self.gui.log(f"State synced from {sender}!")
            return

        if m_type == "SEAT_TAKEN":
            seat_id = msg.get("seat_id")
            owner = msg.get("seat_owner") 
            self.seats[seat_id] = owner
            self._update_single_seat(seat_id)
            self.gui.log(f"Seat {seat_id} taken by {owner}")
            self.clock.update(msg.get("ts", 0))
            return

        if m_type == "SEAT_FREED":
            seat_id = msg.get("seat_id")
            prev_owner = msg.get("sender")
            self.seats[seat_id] = None
            self._update_single_seat(seat_id)
            self.gui.log(f"Seat {seat_id} freed by {prev_owner}")
            self.clock.update(msg.get("ts", 0))
            return

        if m_type in [MessageType.REQUEST, MessageType.REPLY]:
            self.algo.handle_message(msg)

    def _refresh_gui(self):
        """Ricolora tutta la griglia in base ai proprietari"""
        for i in range(25):
            self._update_single_seat(i)

    def _update_single_seat(self, seat_id):
        owner = self.seats[seat_id]
        if owner is None:
            self.gui.update_seat_color(seat_id, "#90EE90")
        elif owner == self.node_id:
            self.gui.update_seat_color(seat_id, "#32CD32")
        else:
            self.gui.update_seat_color(seat_id, "#FF6347") 

    def _request_state_from_peer(self, target_id):
        msg = {"type": MessageType.STATE_REQUEST, "sender": self.node_id}
        self.peer.send_to_node(target_id, msg)

    def handle_gui_click(self, seat_id):
        current_owner = self.seats[seat_id]

        if current_owner is not None and current_owner != self.node_id:
            self.gui.log(f"Seat {seat_id} is owned by {current_owner}!")
            return

        if current_owner == self.node_id:
            self.gui.log(f"Releasing seat {seat_id}...")
            self.gui.update_seat_color(seat_id, "#FFD700") 
            self.gui.root.update_idletasks()
            
            success = self.algo.request_critical_section(lambda: self._on_release_cs(seat_id))
            if not success:
                self.gui.log("System busy. Keep clicking.")
                self._update_single_seat(seat_id)
            return

        self.gui.log(f"Requesting seat {seat_id} (Current T={self.clock.value})...")
        self.gui.update_seat_color(seat_id, "#FFD700") 
        self.gui.root.update_idletasks()

        success = self.algo.request_critical_section(lambda: self._on_acquire_cs(seat_id))
        if not success:
            self.gui.log("System busy.")
            self._update_single_seat(seat_id)

    def _on_acquire_cs(self, seat_id):
        if self.seats[seat_id] is None:
            self.seats[seat_id] = self.node_id
            self._update_single_seat(seat_id)
            self.gui.log(f"SUCCESS: Booked seat {seat_id} @ Time {self.clock.value}")
            
            self.peer.broadcast({
                "type": "SEAT_TAKEN",
                "seat_id": seat_id,
                "seat_owner": self.node_id,
                "ts": self.clock.value
            })
        else:
            self.gui.log(f"FAIL: Seat {seat_id} taken by {self.seats[seat_id]}!")
            self._update_single_seat(seat_id)

        time.sleep(0.5) 
        self.algo.release_critical_section()

    def _on_release_cs(self, seat_id):
        if self.seats[seat_id] == self.node_id:
            self.seats[seat_id] = None
            self._update_single_seat(seat_id)
            self.gui.log(f"RELEASED: Seat {seat_id} is now free.")
            
            self.peer.broadcast({
                "type": "SEAT_FREED",
                "seat_id": seat_id,
                "sender": self.node_id,
                "ts": self.clock.value
            })
        
        time.sleep(0.5)
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