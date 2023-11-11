#!/usr/bin/env python
import argparse

from src.socket.client import SocketClient
from src.socket.proxy import SocketProxy
from src.socket.server import SocketServer

serverforclient_node = []


def read_file(file_path):
    c = SocketClient()

    c.new_pull_file(file_path)


threading_list = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10"]
def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-s', '--server type', type=int)
    arg_parser.add_argument('-c', '--client number', type=int)
    return vars(arg_parser.parse_args())


if __name__ == "__main__":
    # or multiple clients?
    args = parse_args()
    if args.c == 0:
        if args.s == 1:
            s = SocketServer()
            s.serve()
        if args.s == 2:
            s = SocketProxy()
            s.serve()
    else:
        c = SocketClient()
        c.new_pull_file("test/test.txt")

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

    # s = RdmaServer(ADDR, PORT_STR, OPTIONS)
    # s.run()
    # s.close()

    # s = RdmaSocketServer(cfg.ADDR_SERVER, cfg.PORT_STR, cfg.OPTIONS)
    # s.serve()
