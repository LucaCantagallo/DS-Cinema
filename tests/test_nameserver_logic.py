import pytest
from src.nameserver.server import NameServerLogic

def test_register_new_peer():
    """Verifica che un nuovo peer venga aggiunto correttamente"""
    ns = NameServerLogic()
    ns.register_peer("node_1", "127.0.0.1", 5001)
    
    peers = ns.get_peers()
    assert "node_1" in peers
    assert peers["node_1"] == {"host": "127.0.0.1", "port": 5001}

def test_register_update_peer():
    """Se un peer si registra di nuovo, aggiorna i dati"""
    ns = NameServerLogic()
    ns.register_peer("node_1", "127.0.0.1", 5001)
    ns.register_peer("node_1", "192.168.1.5", 6000)
    
    peers = ns.get_peers()
    assert peers["node_1"]["host"] == "192.168.1.5"
    assert peers["node_1"]["port"] == 6000

def test_remove_peer():
    """Verifica la rimozione di un peer"""
    ns = NameServerLogic()
    ns.register_peer("node_1", "127.0.0.1", 5001)
    ns.remove_peer("node_1")
    
    assert "node_1" not in ns.get_peers()