#!/usr/bin/env python
from src.rdma.socket.rdma_socket_client import RdmaSocketClient
import src.config.config as cfg
# from src.socket.client import SocketClient
# from src.socket.server import SocketServer
from src.socket.proxy import SocketClient
from src.socket.proxy import SocketServer
from src.rdma.socket.rdma_socket_server import RdmaSocketServer
import threading
import src.common.msg as m
import  argparse
# def client(cc):
#     cc.request()
# def server(ss):
#     ss.serve()  
def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--port',type=int)
    return vars(arg_parser.parse_args())   
def main():
    # args =  parse_args()
    s = SocketServer()    #port=args['port'])
    s.serve()
    # c = SocketClient()
    # s = SocketServer()
    # thread = threading.Thread(target=server,args=s)
    # thread.start()
    # client(c)
    # while True:
    #     try:
    #         msg = s.conn.recv(c.BUFFER_SIZE)
    #         if msg == m.BEGIN_MSG:
    #             print("begin, exchange the metadata")
    #             s.conn.sendall(m.READY_MSG)
    #             # exchange the metadata
    #             # use socket to exchange the metadata of server
    #             client_metadata_attr_bytes = s.conn.recv(c.BUFFER_SIZE)
    #             s.client_metadata_attr = deserialize(client_metadata_attr_bytes)
    #             print_info("the client metadata attr is:\n" + str(self.client_metadata_attr))
    #             # qp_attr
    #             s.node.qp2init().qp2rtr(s.client_metadata_attr).qp2rts()
    #             # node.post_recv(node.recv_mr)
    #             # send its buffer attr to client
    #             buffer_attr_bytes = serialize(node.buffer_attr)
    #             s.conn.sendall(buffer_attr_bytes)
    #             # exchange metadata done
    #             # node.poll_cq()

    #         elif msg == m.SEND_FILE_MSG:
    #             s.node.p_receive_send(s.node,s.client_metadata_attr,c.node,c.server_metadata_attr)
    #             print("success write file to client")
    #         elif msg == m.DONE_MSG:
    #             print("done")
    #             s.node.close()
    #             break
    #     except Exception as err:
    #         print(err)
    #         s.node.close()
    #         break
    # print("---------------------------- A CONNECT DONE  --------------------------------")

if __name__ == '__main__':
    main()
 
