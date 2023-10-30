#!/usr/bin/env python
#!/usr/bin/env python
# 17:04
from src.rdma.socket.rdma_socket_client import RdmaSocketClient
import src.config.config as cfg
from src.socket.client import SocketClient
from src.socket.server import SocketServer
from src.rdma.socket.rdma_socket_server import RdmaSocketServer
import argparse
serverforclient_node=[]
#server
 
def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--port',type=int)
    return vars(arg_parser.parse_args())    
if __name__ == "__main__":
    #or multiple clients?
    # args =  parse_args()
    s = SocketServer()
    s.serve()  
 
 
    # s = RdmaServer(ADDR, PORT_STR, OPTIONS)
    # s.run()
    # s.close()
 
    # s = SocketServer()
    # s.serve() 
    # s = RdmaSocketServer(cfg.ADDR_SERVER, cfg.PORT_STR, cfg.OPTIONS)
    # s.serve()
