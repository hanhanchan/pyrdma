#!/usr/bin/env python
from src.rdma.socket.rdma_socket_client import RdmaSocketClient
import src.config.config as cfg
from src.socket.client import SocketClient
import threading
import  argparse
import time 
#client
def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--port',type=int)
    return vars(arg_parser.parse_args())   
def read_file(file_path):
    c = SocketClient()
 
 
    c.new_pull_file(file_path) 
 
 
threading_list=["t1","t2","t3","t4","t5","t6","t7","t8","t9","t10"]
if __name__ == "__main__":
    # c = RdmaSocketClient(cfg.ADDR_CLIENT, cfg.PORT_STR)
    # c.request()
    # args =  parse_args()

    # count=0
    # start_time = time.perf_counter()
    # while(count<2):
    #     threading_list[count] = threading.Thread(target=read_file, args=("test/test.txt",))
    #     threading_list[count+1]= threading.Thread(target=read_file, args=("test/test2.txt",))
    #     threading_list[count].start()
    #     threading_list[count+1].start()
    #     threading_list[count].join()
    #     threading_list[count+1].join()
    #     count=count+2
 
    #     if count==2:
    #         end_time = time.perf_counter()
    # print(str(count)+" find time", end_time - start_time, "s")
 
 
    
    #c.new_pull_file("test/test.txt") 
 
    # #c.push_file("../test/test.txt")
    # c.pull_file("./test/pull/des/50M.file")
    # c = RdmaSocketClient(ADDR, PORT_STR)
    # c.request()
    c = SocketClient()
 
 
    c.new_pull_file("test/test.txt") 