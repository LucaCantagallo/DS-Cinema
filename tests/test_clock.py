import pytest
from src.common.models import LamportClock

def test_initial_value():
    """Un nuovo clock deve partire da 0"""
    clock = LamportClock()
    assert clock.value == 0

def test_increment():
    """L'evento locale deve incrementare il clock di 1"""
    clock = LamportClock()
    clock.increment()
    assert clock.value == 1

def test_update():
    """Ricezione msg: clock = max(local, remote) + 1"""
    clock = LamportClock()
    clock.value = 1
    remote_time = 5
    clock.update(remote_time)
    assert clock.value == 6