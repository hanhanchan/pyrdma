#!/usr/bin/env python
from src.rdma.socket.rdma_socket_server import RdmaSocketServer
from src.config.config import PORT_STR, OPTIONS
from src.socket.server import SocketServer
from src.rdma.socket.rdma_socket_client import RdmaSocketClient
from src.config.config import PORT_STR
from src.socket.client import SocketClient
import threading
#server
if __name__ == "__main__":
    # s = RdmaServer(ADDR, PORT_STR, OPTIONS)
    # s.run()
    # s.close()
 
    s = SocketServer()
    s.serve() 
    # s = RdmaSocketServer(ADDR, PORT_STR, OPTIONS)
    # s.serve()
