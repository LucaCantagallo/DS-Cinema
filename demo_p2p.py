import time
import logging
from src.node.peer import Peer

logging.basicConfig(level=logging.INFO, format='%(message)s')

def print_msg_node_1(msg, ip):
    print(f"NODE 1 received from {ip}: {msg}")

def print_msg_node_2(msg, ip):
    print(f"NODE 2 received from {ip}: {msg}")

if __name__ == "__main__":
    print("--- AVVIO TEST P2P ---")

    p1 = Peer("127.0.0.1", 5001, print_msg_node_1)
    p2 = Peer("127.0.0.1", 5002, print_msg_node_2)

    p1.start()
    p2.start()
    print("Nodes started on ports 5001 and 5002")
    time.sleep(1) 

    print(">>> Sending Hello from 1 to 2...")
    p1.send_packet("127.0.0.1", 5002, {"content": "Hello Node 2!", "sender": "Node 1"})


    print(">>> Sending Ciao from 2 to 1...")
    p2.send_packet("127.0.0.1", 5001, {"content": "Ciao Node 1!", "sender": "Node 2"})

    time.sleep(2)

    p1.stop()
    p2.stop()
    print("--- TEST COMPLETED ---")