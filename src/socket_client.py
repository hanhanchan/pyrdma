import socket
# const
import pyverbs.enums as e
import pyverbs.cmid
# config
import src.config.config as c
# common
from src.common.common import print_info
from src.common.socket_node import SocketNode
from src.common.buffer_attr import serialize, deserialize
# pyverbs
from pyverbs.addr import AHAttr, GlobalRoute, GID
from pyverbs.mr import MR
from pyverbs.qp import QPAttr
from pyverbs.wr import SGE, SendWR


class SocketClient:
    def __init__(self, name=c.NAME, addr=c.ADDR, port=c.PORT_INT, options=c.OPTIONS):
        self.name = name
        self.addr = addr
        self.port = port
        self.options = options
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def request(self):
        print("connect in", self.addr, self.port)
        self.socket.connect((self.addr, self.port))
        # use socket to exchange metadata of client
        node = SocketNode(name=self.name)
        node.prepare_resource()
        buffer_attr_bytes = serialize(node.buffer_attr)
        self.socket.sendall(buffer_attr_bytes)
        # get the metadata from server
        server_metadata_attr_bytes = self.socket.recv(c.BUFFER_SIZE)
        server_metadata_attr = deserialize(server_metadata_attr_bytes)
        print_info("server metadata attr:\n"+str(server_metadata_attr))
        # qp
        qp_attr = QPAttr(qp_state=e.IBV_QPS_RTS, cur_qp_state=node.qp.qp_state)
        gid_options = self.options["gid_init"]
        s_gid = GID(server_metadata_attr.gid)
        gr = GlobalRoute(dgid=s_gid, sgid_index=gid_options["gid_index"])
        ah_attr = AHAttr(gr=gr, is_global=1, port_num=gid_options["port_num"])
        qp_attr.ah_attr = ah_attr
        qp_attr.dest_qp_num = server_metadata_attr.qp_num
        node.qp.to_rts(qp_attr)
        # exchange done, write message to buffer
        message = "a message from client"
        me_len = len(message)
        node.resource_mr.write(message, me_len)
        sge = SGE(addr=node.resource_mr.buf, length=me_len, lkey=node.resource_mr.lkey)
        wr = SendWR(num_sge=1, sg=[sge, ], opcode=e.IBV_WR_RDMA_WRITE)
        wr.set_wr_rdma(rkey=server_metadata_attr.remote_stag, addr=server_metadata_attr.addr)
        node.qp.post_send(wr)
        node.process_work_completion_events()
        # read the message
        self.read_mr = MR(node.pd, c.BUFFER_SIZE,
                          e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        sge = SGE(addr=self.read_mr.buf, length=me_len, lkey=self.read_mr.lkey)
        wr = SendWR(num_sge=1, sg=[sge, ], opcode=e.IBV_WC_RDMA_READ)
        wr.set_wr_rdma(rkey=server_metadata_attr.remote_stag, addr=server_metadata_attr.addr)
        node.qp.post_send(wr)
        read_message = self.read_mr.read(me_len, 0)
        print_info("read from sever\n"+str(read_message))
        node.process_work_completion_events()
        self.socket.close()  # 关闭连接
