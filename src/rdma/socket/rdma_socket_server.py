# const
import pyverbs.cm_enums as ce
import pyverbs.enums as e
# config
import src.config.config as c
# pyverbs
from pyverbs.cmid import CMID, AddrInfo
from pyverbs.mr import MR
from pyverbs.pd import PD
from pyverbs.qp import QPInitAttr, QPCap

from src.common.buffer_attr import BufferAttr, deserialize, serialize
from src.common.common import die, check_wc_status, print_info


def process_wc_send_events(cmid, poll_count=1):
    npolled = 0
    wcs = []
    while npolled < poll_count:
        wc = cmid.get_send_comp()
        if wc is not None:
            npolled += 1
            wcs.append(wc)
    for wc in wcs:
        check_wc_status(wc)


def process_wc_recv_events(cmid, poll_count=1):
    npolled = 0
    wcs = []
    while npolled < poll_count:
        wc = cmid.get_recv_comp()
        if wc is not None:
            npolled += 1
            wcs.append(wc)
    for wc in wcs:
        check_wc_status(wc)


class RdmaSocketServer:
    def __init__(self, addr, port, options=c.OPTIONS):
        addr_info = AddrInfo(src=addr, src_service=port, port_space=ce.RDMA_PS_TCP, flags=ce.RAI_PASSIVE)
        qp_options = options["qp_init"]
        cap = QPCap(max_send_wr=qp_options["max_send_wr"], max_recv_wr=qp_options["max_recv_wr"],
                    max_send_sge=qp_options["max_send_sge"], max_recv_sge=qp_options["max_recv_sge"])
        qp_init_attr = QPInitAttr(qp_type=qp_options["qp_type"], cap=cap)
        self.sid = CMID(creator=addr_info, qp_init_attr=qp_init_attr)

    def serve(self):
        self.sid.listen()
        print("rdma socket listening")
        while True:
            new_id = self.sid.get_request()
            new_id.accept()
            while True:
                try:
                    print("a connect come")
                    pd = PD(new_id)
                    metadata_recv_mr = MR(pd, c.BUFFER_SIZE, e.IBV_ACCESS_LOCAL_WRITE)
                    new_id.post_recv(metadata_recv_mr)
                    process_wc_recv_events(new_id)
                    client_metadata_attr = deserialize(metadata_recv_mr.read(c.BUFFER_SIZE, 0))
                    print_info("client metadata attr:\n" + str(client_metadata_attr))
                    resource_send_mr = MR(pd, c.BUFFER_SIZE,
                                          e.IBV_ACCESS_LOCAL_WRITE |
                                          e.IBV_ACCESS_REMOTE_READ |
                                          e.IBV_ACCESS_REMOTE_WRITE)
                    # metadata_send_mr: client send the resource_send_mr attr to server
                    buffer_attr = BufferAttr(addr=resource_send_mr.buf, length=c.BUFFER_SIZE,
                                             local_stag=resource_send_mr.lkey,
                                             remote_stag=resource_send_mr.rkey)
                    buffer_attr_bytes = serialize(buffer_attr)
                    # metadata_send_mr: node send the resource_send_mr attr to others
                    metadata_send_mr = MR(pd, c.BUFFER_SIZE, e.IBV_ACCESS_LOCAL_WRITE)
                    metadata_send_mr.write(buffer_attr_bytes, len(buffer_attr_bytes))

                    new_id.post_send(metadata_send_mr)
                    process_wc_send_events(new_id)

                except Exception as err:
                    print("error:", err)
                    break
            new_id.close()
