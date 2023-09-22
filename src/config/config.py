import pyverbs.enums as e

ADDR_SERVER = "192.168.56.3" #server bound to where
ADDR_CLIENT = "192.168.56.4" #client bount to where 
PORT_INT = 50008
PORT_STR = "50008"
NAME = "rocep0s8"
TIMEOUT_IN_MS = 500
BUFFER_SIZE = 1024
FILE_SIZE = 10 * BUFFER_SIZE * BUFFER_SIZE  # 10MB
BUFFER_META_SIZE=1024
FILE_NAME="test/test.txt"
OPTIONS = {
    "qp_init": {
        "qp_type": e.IBV_QPT_RC,
        "max_send_wr": 4,
        "max_recv_wr": 4,
        "max_send_sge": 2,
        "max_recv_sge": 2,
    },
    "cq_init": {
        "cqe": 8
    },
    "gid_init": {
        "port_num": 1,
        "gid_index": 1,  # 3 mean to use the RoCE v2 interface
    }
}
