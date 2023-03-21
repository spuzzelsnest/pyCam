#!/usr/bin/python3

from psutil import process_iter
from signal import SIGTERM # or SIGKILL

for proc in process_iter():
    for conns in proc.connections(kind='inet'):
        if conns.laddr.port == 8081:
            proc.send_signal(SIGTERM) # or SIGKILL
