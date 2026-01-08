import pytest
import json
import struct
from src.common.protocol import PacketProtocol

def test_serialize_message():
    """Verifica che un dizionario venga convertito in bytes con header di 4 byte"""
    message = {"type": "TEST", "value": 123}
    data = PacketProtocol.serialize(message)
    
    # Controllo lunghezza minima (4 byte header + qualcosa di payload)
    assert len(data) > 4
    
    # Decodifica manuale per verificare la correttezza
    header = data[:4]
    payload = data[4:]
    
    expected_length = len(json.dumps(message).encode('utf-8'))
    unpacked_length = struct.unpack('>I', header)[0]
    
    assert unpacked_length == expected_length
    assert json.loads(payload.decode('utf-8')) == message

def test_deserialize_complete_packet():
    """Verifica la deserializzazione di un pacchetto intero"""
    message = {"key": "value"}
    json_bytes = json.dumps(message).encode('utf-8')
    header = struct.pack('>I', len(json_bytes))
    data = header + json_bytes
    
    result, remainder = PacketProtocol.deserialize(data)
    
    assert result == message
    assert remainder == b""

def test_deserialize_partial_packet():
    """Verifica che se i dati sono incompleti restituisca None e il buffer originale"""
    message = {"key": "value"}
    json_bytes = json.dumps(message).encode('utf-8')
    header = struct.pack('>I', len(json_bytes))
    data = header + json_bytes
    
    # Tagliamo gli ultimi 2 byte per simulare un pacchetto spezzato dal TCP
    partial_data = data[:-2]
    
    result, remainder = PacketProtocol.deserialize(partial_data)
    
    assert result is None
    assert remainder == partial_data

def test_deserialize_multiple_packets():
    """Verifica la gestione di due pacchetti attaccati (sticky packets)"""
    msg1 = {"id": 1}
    msg2 = {"id": 2}
    
    data1 = PacketProtocol.serialize(msg1)
    data2 = PacketProtocol.serialize(msg2)
    stream = data1 + data2 # TCP li ha incollati insieme
    
    # Prima chiamata: deve estrarre il primo e lasciare il secondo
    result1, remainder1 = PacketProtocol.deserialize(stream)
    assert result1 == msg1
    assert remainder1 == data2
    
    # Seconda chiamata: deve estrarre il secondo
    result2, remainder2 = PacketProtocol.deserialize(remainder1)
    assert result2 == msg2
    assert remainder2 == b""