import sys
import threading
from src.node.gui import CinemaGUI
from src.node.peer import Peer

def on_network_message(msg, sender_ip):
    print(f"Network message from {sender_ip}: {msg}")

def on_gui_click(seat_id):
    print(f"User clicked seat {seat_id}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m src.node.main <node_id> <port>")
        return

    node_id = sys.argv[1]
    port = int(sys.argv[2])
    
    peer = Peer("127.0.0.1", port, on_network_message)
    peer.start()
    
    try:
        gui = CinemaGUI(node_id=node_id, on_seat_click=on_gui_click)
        gui.log(f"System started on port {port}")
        gui.start()
    finally:
        peer.stop()

if __name__ == "__main__":
    main()