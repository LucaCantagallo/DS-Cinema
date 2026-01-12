import threading
import time
import logging
from src.node.algorithm import RicartAgrawala
from src.common.models import LamportClock

logging.basicConfig(level=logging.INFO, format='%(message)s')

class MockTransport:
    def __init__(self, my_id, network_bus):
        self.my_id = my_id
        self.bus = network_bus 

    def broadcast(self, msg, exclude_self=True):
        targets = []
        for pid, algo in self.bus.items():
            if pid != self.my_id:
                threading.Thread(target=algo.handle_message, args=(msg,)).start()
                targets.append(pid)
        return targets

    def send_to_node(self, target_id, msg):
        if target_id in self.bus:
            threading.Thread(target=self.bus[target_id].handle_message, args=(msg,)).start()

def test_simultaneous_click():
    print("\n--- SIMULAZIONE CLICK SIMULTANEO ---")
    
    network_bus = {}
    results = []
    
    clock1 = LamportClock()
    clock2 = LamportClock()
    
    get_peers = lambda: list(network_bus.keys())
    
    algo_luca = RicartAgrawala("Luca", clock1, get_peers, None)
    algo_marco = RicartAgrawala("Marco", clock2, get_peers, None)
    
    algo_luca.transport = MockTransport("Luca", network_bus)
    algo_marco.transport = MockTransport("Marco", network_bus)
    
    network_bus["Luca"] = algo_luca
    network_bus["Marco"] = algo_marco
    

    def on_luca_win():
        print(f"LUCA è entrato nella Sezione Critica! (Clock: {algo_luca.clock.value})")
        results.append("Luca")
        time.sleep(0.5) 
        algo_luca.release_critical_section()
        
    def on_marco_win():
        print(f"MARCO è entrato nella Sezione Critica! (Clock: {algo_marco.clock.value})")
        results.append("Marco")
        time.sleep(0.5)
        algo_marco.release_critical_section()

    print(">>> CLICK SIMULTANEO SU ENTRAMBI I NODI...")
    t1 = threading.Thread(target=algo_luca.request_critical_section, args=(on_luca_win,))
    t2 = threading.Thread(target=algo_marco.request_critical_section, args=(on_marco_win,))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    time.sleep(2)
    
    print(f"\nOrdine di accesso reale: {results}")
    
    if results == ["Luca", "Marco"]:
        print("TEST SUPERATO: Luca ha vinto per priorità ID (Tie-breaker corretto).")
    else:
        print("TEST FALLITO: Ordine errato.")

if __name__ == "__main__":
    test_simultaneous_click()