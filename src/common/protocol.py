import json
import struct
from typing import Tuple, Optional

class PacketProtocol:
    
    @staticmethod
    def serialize(message: dict) -> bytes:
        json_bytes = json.dumps(message).encode('utf-8')
        header = struct.pack('>I', len(json_bytes))
        return header + json_bytes

    @staticmethod
    def deserialize(buffer: bytes) -> Tuple[Optional[dict], bytes]:
        if len(buffer) < 4:
            return None, buffer
        
        msg_length = struct.unpack('>I', buffer[:4])[0]
        total_length = 4 + msg_length
        
        if len(buffer) < total_length:
            return None, buffer
        
        payload = buffer[4:total_length]
        remainder = buffer[total_length:]
        
        try:
            message = json.loads(payload.decode('utf-8'))
            return message, remainder
        except json.JSONDecodeError:
            return None, buffer