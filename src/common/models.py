class LamportClock:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1
        return self.value

    def update(self, received_timestamp: int):
        self.value = max(self.value, received_timestamp) + 1
        return self.value
    
class MessageType:
    REQUEST = "REQUEST"
    REPLY = "REPLY"
    RELEASE = "RELEASE"
    SYNC = "SYNC"       
    SEAT_TAKEN = "SEAT_TAKEN"
    STATE_REQUEST = "STATE_REQUEST" 
    STATE_REPLY = "STATE_REPLY"      