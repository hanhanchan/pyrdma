# const
import pyverbs.enums as e
# config
from pyverbs.cq import CQ
from pyverbs.qp import QPCap, QPInitAttr, QPAttr, QP
from pyverbs.addr import GID, GlobalRoute, AHAttr
from pyverbs.wr import SGE, SendWR, RecvWR

import src.config.config as c
import src.common.msg as m
# common
from src.common.buffer_attr import BufferAttr, BufferBasic, BufferKey
import src.common.utils as utils
from src.common.file_attr import FileAttr
# pyverbs
from pyverbs.device import Context
from pyverbs.mr import MR
from pyverbs.pd import PD
from src.common.buffer_attr import deserialize, serialize

class SocketNode:
    def __init__(self, name, options=c.OPTIONS):
        self.name = name
        self.options = options
        self.rdma_ctx = Context(name=self.name)
        self.pd = PD(self.rdma_ctx)
        self.msg_mr = MR(self.pd, c.BUFFER_SIZE,
                         e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        self.read_mr = MR(self.pd, c.BUFFER_SIZE,
                          e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        self.recv_mr = MR(self.pd, c.BUFFER_SIZE,
                          e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        self.file_mr = MR(self.pd, c.FILE_SIZE,
                          e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        # gid
        gid_options = self.options["gid_init"]
        self.gid = self.rdma_ctx.query_gid(gid_options["port_num"], gid_options["gid_index"])
        # cq
        self.cq = self.init_cq()
        # qp
        self.qp = self.init_qp()
        self.buffer_attr,self.buffer_basic_attr,self.buffer_key_attr = self.init_buffer_attr(self.file_mr, c.FILE_SIZE)
        self.remote_metadata = None
        # file attr
        self.file_attr = FileAttr()

    def init_buffer_attr(self, mr: MR, buffer_len=c.BUFFER_SIZE):
        # send the metadata to other
        # return BufferAttr(mr.buf, buffer_len,
        #                   mr.lkey, mr.rkey,
        #                   str(self.gid), self.qp.qp_num)
        return BufferAttr(mr.buf, buffer_len,mr.lkey, mr.rkey,str(self.gid), self.qp.qp_num),BufferBasic(str(self.gid), self.qp.qp_num),BufferKey(mr.buf, buffer_len,mr.lkey,mr.rkey)

    def init_cq(self):
        cqe = self.options["cq_init"]["cqe"]
        cq = CQ(self.rdma_ctx, cqe, None, None, 0)
        cq.req_notify()
        return cq

    def init_qp(self):
        qp_options = self.options["qp_init"]
        cap = QPCap(max_send_wr=qp_options["max_send_wr"], max_recv_wr=qp_options["max_recv_wr"],
                    max_send_sge=qp_options["max_send_sge"], max_recv_sge=qp_options["max_recv_sge"])
        qp_init_attr = QPInitAttr(qp_type=qp_options["qp_type"], qp_context=self.rdma_ctx,
                                  cap=cap, scq=self.cq, rcq=self.cq)
        return QP(self.pd, qp_init_attr)

    def qp2init(self):
        qp_attr = QPAttr(qp_state=e.IBV_QPS_INIT, cur_qp_state=e.IBV_QPS_RESET)
        qp_attr.qp_access_flags = e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE
        self.qp.to_init(qp_attr)
        return self

    def qp2rtr(self, metadata_attr: BufferAttr):
        self.remote_metadata = metadata_attr
        gid_options = self.options["gid_init"]
        qp_attr = QPAttr(qp_state=e.IBV_QPS_RTR, cur_qp_state=e.IBV_QPS_INIT)
        qp_attr.qp_access_flags = e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE
        port_num = gid_options["port_num"]
        remote_gid = GID(metadata_attr.gid)
        gr = GlobalRoute(dgid=remote_gid, sgid_index=gid_options["gid_index"])
        ah_attr = AHAttr(gr=gr, is_global=1, port_num=port_num)
        qp_attr.ah_attr = ah_attr
        qp_attr.dest_qp_num = metadata_attr.qp_num
        self.qp.to_rtr(qp_attr)
        return self

    def qp2rts(self):
        qp_attr = QPAttr(qp_state=e.IBV_QPS_RTS, cur_qp_state=e.IBV_QPS_RTR)
        qp_attr.qp_access_flags = e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE
        # TODO: for bug read test
        qp_attr.timeout = 18
        qp_attr.retry_cnt = 6
        qp_attr.max_rd_atomic = 1
        self.qp.to_rts(qp_attr)
        return self

    # poll cq
    def poll_cq(self, poll_count=1, debug=True):
        self.cq.req_notify()
        npolled = 0
        wc_list = []
        while npolled < poll_count:
            (one_poll_count, wcs) = self.cq.poll(num_entries=poll_count)
            if one_poll_count > 0:
                npolled += one_poll_count
                self.cq.ack_events(one_poll_count)
                if debug:
                    for wc in wcs:
                        # check the wc status, if not success, log the result or die
                        utils.check_wc_status(wc)
                wc_list += wcs
        return wc_list

    def post_write(self, mr: MR, data, length, rkey, remote_addr, opcode=e.IBV_WR_RDMA_WRITE, imm_data=0):
        mr.write(data, length)
        sge = SGE(addr=mr.buf, length=length, lkey=mr.lkey)
        wr = SendWR(opcode=opcode, num_sge=1, sg=[sge, ])
        wr.set_wr_rdma(rkey=rkey, addr=remote_addr)
        if imm_data != 0:
            wr.imm_data = imm_data
        self.qp.post_send(wr)

    # TODO: bug: post read can not poll cq?
    def post_read(self, mr: MR, length, rkey, remote_addr):
        sge = SGE(addr=mr.buf, length=length, lkey=mr.lkey)
        wr = SendWR(opcode=e.IBV_WR_RDMA_READ, num_sge=1, sg=[sge, ])
        wr.set_wr_rdma(rkey=rkey, addr=remote_addr)
        self.qp.post_send(wr)

    def post_send(self, mr: MR, data, length=0):
        if length == 0:
            length = len(data)
        mr.write(data, length)
        sge = SGE(addr=mr.buf, length=length, lkey=mr.lkey)
        wr = SendWR(opcode=e.IBV_WR_SEND, num_sge=1, sg=[sge, ])
        self.qp.post_send(wr)

    def post_recv(self, mr: MR):
        sge = SGE(addr=mr.buf, length=c.BUFFER_SIZE, lkey=mr.lkey)
        wr = RecvWR(num_sge=1, sg=[sge, ])
        self.qp.post_recv(wr)

        
    # initiative push file
    def c_push_file(self, file_path):
        self.post_recv(self.recv_mr)
        self.poll_cq()
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            try:
                self.file_attr.open(file_path)
            except OSError as err:
                err_str = str(err)
                self.post_send(self.msg_mr, err_str)
                return
            # FH+local buffer 
            self.file_attr.file_name = file_path
            # write file name
            self.post_write(self.file_mr, file_path, len(file_path),
                            self.remote_metadata.remote_stag, self.remote_metadata.addr,
                            opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=len(file_path))
            self.post_recv(self.recv_mr)
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
                if wc.opcode & e.IBV_WC_RECV:
                    msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                    self.post_recv(self.recv_mr)
                    if utils.check_msg(msg, m.FILE_READY_MSG):
                        # send next chunk
                        file_stream = self.file_attr.fd.read(c.FILE_SIZE)
                        size = len(file_stream)
                        self.post_write(self.file_mr, file_stream, size,
                                        self.remote_metadata.remote_stag, self.remote_metadata.addr,
                                        opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=size)
                        print("send next chunk", size)
                    elif utils.check_msg(msg, m.FILE_DONE_MSG):
                        print("file done")
                        # done
                        self.file_attr.done()
            self.file_attr.close()

    # passive save file
    def s_save_file(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        while not self.file_attr.is_done():
            wc = self.poll_cq()[0]
            if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
                # initiative save file
                size = wc.imm_data
                if size == 0:
                    print("file done")
                    self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                    self.file_attr.done()
                elif self.file_attr.file_name:
                    print("recv file body", size)
                    self.post_recv(self.file_mr)
                    file_stream = self.file_mr.read(size, 0)
                    self.file_attr.fd.write(file_stream)
                    self.post_send(self.msg_mr, m.FILE_READY_MSG)
                else:
                    self.post_recv(self.file_mr)
                    # file_name = self.file_mr.read(size, 0)
                    file_name = "./test/push/des/test.file"  # test
                    self.file_attr.file_name = file_name
                    self.file_attr.fd = utils.create_file(file_name)
                    self.post_send(self.msg_mr, m.FILE_READY_MSG)
            elif wc.opcode & e.IBV_WC_RECV:
                msg = self.file_mr.read(c.BUFFER_SIZE, 0)
                if utils.check_msg(msg, m.FILE_ERR_MSG):
                    break
        if self.file_attr.fd:
            self.post_send(self.msg_mr, m.FILE_DONE_MSG)
            self.poll_cq()
        self.file_attr.close()

    def c_init_send(self,file_path):
        self.file_attr.file_name = file_path
        # self.post_recv(self.recv_mr)
        self.poll_cq()  # post recv
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        print("receive begin")
        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            self.file_attr.fd = utils.create_file("./test/pull/src/pull.txt")
            # self.file_attr.fd = utils.create_file(file_path)
            loacal_meta= serialize(self.buffer_key_attr)
            self.post_send(self.msg_mr, loacal_meta)
            # self.post_write(self.msg_mr, file_path, len(file_path),
            #                 self.remote_metadata.remote_stag, self.remote_metadata.addr,
            #                 e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=len(file_path))
            self.post_recv(self.file_mr)
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
                if wc.opcode == e.IBV_WC_RDMA_WRITE:
                    file_stream =self.file_mr.read(c.FILE_SIZE,0)
                    self.file_attr.fd.write(file_stream)
                    self.post_send(self.msg_mr, m.FILE_DONE_MSG) 
                    # size = wc.imm_data
                    # if size == 0:
                    #     print("file done")
                    #     self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                    #     self.file_attr.done()
                    # else:
                    #     print("recv file body", size)
                    #     self.post_recv(self.file_mr)
                    #     file_stream = self.file_mr.read(size, 0)
                    #     self.file_attr.fd.write(file_stream)
                    #     self.post_send(self.msg_mr, m.FILE_READY_MSG)
                elif wc.opcode & e.IBV_WC_RECV:
                    msg = self.file_mr.read(c.BUFFER_SIZE, 0)
                    if utils.check_msg(msg, m.FILE_ERR_MSG):
                        print("server file error")
                        break
            self.file_attr.close()
        else:
            print("server file error")
    def p_receive_send(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
        wc = self.poll_cq()[0]  # post recv
        print("receive opcode ="+str(wc.opcode))
        
        if wc.opcode == e.IBV_WC_RECV:
            # passive push file
            # size = wc.imm_data
            file_name=c.FILE_NAME
            remote_meta = deserialize(self.file_mr.read(c.BUFFER_META_SIZE, 0))
            print(remote_meta)
            loacal_meta= serialize(self.buffer_key_attr) #file 
            self.post_send(self.msg_mr, loacal_meta)
            self.post_recv(self.file_mr)
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
                if wc.opcode == e.IBV_WR_RDMA_WRITE:
                    file_stream =self.file_mr.read(c.FILE_SIZE,0)
                    size = len(file_stream)
                    self.post_write(self.file_mr, file_stream, size,
                            remote_meta.rkey, remote_meta.addr,
                            opcode=e.IBV_WR_RDMA_WRITE)
                    self.file_attr.done()
            self.post_recv(self.recv_mr)


            try:
                self.file_attr.open(file_name)
            except OSError as err:
                self.post_send(self.msg_mr, m.FILE_ERR_MSG)
                return
            self.file_attr.file_name = file_name
            file_stream = self.file_attr.fd.read(c.FILE_SIZE)
            size = len(file_stream)
            #def post_write(self, mr: MR, data, length, rkey, remote_addr, opcode=e.IBV_WR_RDMA_WRITE, imm_data=0)
            self.post_write(self.file_mr, file_stream, size,
                            remote_meta.remote_stag, remote_meta.addr,
                            opcode=e.IBV_WR_RDMA_WRITE)
            print("write to client")
        self.post_recv(self.recv_mr)
        while not self.file_attr.is_done():
            wc = self.poll_cq()[0]
            if wc.opcode & e.IBV_WC_RECV:
                # self.post_recv(self.recv_mr)
                msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                if utils.check_msg(msg, m.FILE_DONE_MSG):
                    print("file done")
                    # done
                    self.file_attr.done()
        self.file_attr.close()

    def s_receive_send(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
        wc = self.poll_cq()[0]  # post recv
        print("receive opcode ="+str(wc.opcode))
        if wc.opcode == e.IBV_WC_RECV:
            # passive push file
            # size = wc.imm_data
            file_name=c.FILE_NAME
            remote_meta = deserialize(self.file_mr.read(c.BUFFER_META_SIZE, 0))
            print(remote_meta)
            try:
                self.file_attr.open(file_name)
            except OSError as err:
                self.post_send(self.msg_mr, m.FILE_ERR_MSG)
                return
            self.file_attr.file_name = file_name
            file_stream = self.file_attr.fd.read(c.FILE_SIZE)
            size = len(file_stream)
            #def post_write(self, mr: MR, data, length, rkey, remote_addr, opcode=e.IBV_WR_RDMA_WRITE, imm_data=0)
            self.post_write(self.file_mr, file_stream, size,
                            remote_meta.remote_stag, remote_meta.addr,
                            opcode=e.IBV_WR_RDMA_WRITE)
            print("write to client")
        self.post_recv(self.recv_mr)
        while not self.file_attr.is_done():
            wc = self.poll_cq()[0]
            if wc.opcode & e.IBV_WC_RECV:
                # self.post_recv(self.recv_mr)
                msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                if utils.check_msg(msg, m.FILE_DONE_MSG):
                    print("file done")
                    # done
                    self.file_attr.done()
        self.file_attr.close()
        '''
        file mr 用msg mr send 出去
        self.post_recv(self.file_mr)
        msg替换为file mr metadata 
        self.post_send(file metadata)
        check file msg opcode:
        done 
    def p_receive_send(self):
        self.post_recv(msg_mr)
        check msg_mr opcode=send
        self.post_recv(file_mr)
        self.post_send(file metadata)
        check file msg opcode:
        write to c file mr
    def s_receive_send(self):
        self.post_recv(msg_mr)
        read file content to file_mr
        write(file_mr to p.file_mr)

    '''
    def c_pull_file(self, file_path):
        self.file_attr.file_name = file_path
        # self.post_recv(self.recv_mr)
        self.poll_cq()  # post recv
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            self.file_attr.fd = utils.create_file("./test/pull/src/pull.txt")
            # self.file_attr.fd = utils.create_file(file_path)
            self.post_write(self.msg_mr, file_path, len(file_path),
                            self.remote_metadata.remote_stag, self.remote_metadata.addr,
                            e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=len(file_path))
            self.post_recv(self.file_mr)
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
                if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
                    size = wc.imm_data
                    if size == 0:
                        print("file done")
                        self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                        self.file_attr.done()
                    else:
                        print("recv file body", size)
                        self.post_recv(self.file_mr)
                        file_stream = self.file_mr.read(size, 0)
                        self.file_attr.fd.write(file_stream)
                        self.post_send(self.msg_mr, m.FILE_READY_MSG)
                elif wc.opcode & e.IBV_WC_RECV:
                    msg = self.file_mr.read(c.BUFFER_SIZE, 0)
                    if utils.check_msg(msg, m.FILE_ERR_MSG):
                        print("server file error")
                        break
            self.file_attr.close()
        else:
            print("server file error")

    def s_push_file(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
        wc = self.poll_cq()[0]  # post recv
        if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
            # passive push file
            size = wc.imm_data
            file_name = self.file_mr.read(size, 0)
            try:
                self.file_attr.open(file_name)
            except OSError as err:
                self.post_send(self.msg_mr, m.FILE_ERR_MSG)
                return
            self.file_attr.file_name = file_name
            file_stream = self.file_attr.fd.read(c.FILE_SIZE)
            size = len(file_stream)
            self.post_write(self.file_mr, file_stream, size,
                            self.remote_metadata.remote_stag, self.remote_metadata.addr,
                            opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=size)
        self.post_recv(self.recv_mr)
        while not self.file_attr.is_done():
            wc = self.poll_cq()[0]
            if wc.opcode & e.IBV_WC_RECV:
                self.post_recv(self.recv_mr)
                msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                if utils.check_msg(msg, m.FILE_READY_MSG):
                    # send next chunk
                    file_stream = self.file_attr.fd.read(c.FILE_SIZE)
                    size = len(file_stream)
                    self.post_write(self.file_mr, file_stream, size,
                                    self.remote_metadata.remote_stag, self.remote_metadata.addr,
                                    opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=size)
                elif utils.check_msg(msg, m.FILE_DONE_MSG):
                    print("file done")
                    # done
                    self.file_attr.done()
        self.file_attr.close()

    def close(self):
        self.rdma_ctx.close()
        self.pd.close()
        self.msg_mr.close()
        self.recv_mr.close()
        self.file_mr.close()
        self.read_mr.close()
        self.cq.close()
        self.qp.close()
        self.file_attr.close()
