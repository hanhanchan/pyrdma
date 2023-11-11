import socket
# config
# common
import socketserver

# Import P4Runtime lib from parent utils dir
# Probably there's a better way of doing this.
import p4runtime_lib.bmv2
import p4runtime_lib.helper
import src.common.msg as m
# config
import src.config.config as c
from src.common.buffer_attr import serialize, deserialize
from src.common.utils import print_info
from src.socket.socket_node import SocketNode

p4info_file_path = 'src/socket/simple-version-modify-header.p4.p4info.txt'
bmv2_file_path = 'src/socket/simple-version-modify-header.json'
threading_index = -1
port = 50051
UC_SEND = 36
UC_WRITE_FIRST = 38
UC_WRITE_MIDDLE = 39
UC_WRITE_LAST = 41

egress_port = 1


class SocketClient:
    def __init__(self, name=c.NAME, addr=c.ADDR_CLIENT, port=c.PORT_INT, options=c.OPTIONS):
        self.name = name
        self.addr = addr
        self.port = port
        self.options = options
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.node = None
        self.server_metadata_attr = None

    def request(self):
        msg = self._connect_recv_msg()

        if msg == m.READY_MSG:
            # use socket to exchange metadata of client
            self.node = SocketNode(name=self.name)
            server_metadata_attr = self._exchange_metadata(self.node)
            # qp
            self.node.qp2init().qp2rtr(server_metadata_attr).qp2rts()
            # exchange done, write message or push file to buffer
        # done
        # node.close()
        # self._close()
        return server_metadata_attr

    def _exchange_metadata(self, node: SocketNode):
        buffer_attr_bytes = serialize(node.buffer_attr)
        self.socket.sendall(buffer_attr_bytes)
        # get the metadata from server
        server_metadata_attr_bytes = self.socket.recv(c.BUFFER_SIZE)
        self.server_metadata_attr = deserialize(server_metadata_attr_bytes)
        print_info("server metadata attr:\n" + str(self.server_metadata_attr))
        return self.server_metadata_attr

    def _connect_recv_msg(self):
        print("connect in", self.addr, self.port)
        self.socket.connect((self.addr, self.port))
        self.socket.sendall(m.BEGIN_MSG)
        msg = self.socket.recv(c.BUFFER_SIZE)
        return msg

    def _close(self):
        self.socket.sendall(m.DONE_MSG)
        self.socket.close()


class CreateControl():
    def __init__(self):
        if c.is_control_plane != True:
            global threading_index
            self.p4info_helper = p4runtime_lib.helper.P4InfoHelper(p4info_file_path)
            self.s1 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
                name='s1',
                address='192.168.56.10:50051',
                device_id=1,
                proto_dump_file='logs/s1-p4runtime-requests.txt')
            self.s1.MasterArbitrationUpdate()
            self.s1.SetForwardingPipelineConfig(p4info=self.p4info_helper.p4info,
                                                bmv2_json_file_path=bmv2_file_path)
            print("Installed P4 Program using SetForwardingPipelineConfig on s1")

    def writeQPrules(self, client_ip, to_client_qp, index):
        # 1) match server B, rewrite dst from server A to client
        table_entry = self.p4info_helper.buildTableEntry(
            table_name="MyIngress.record_port",
            match_fields={

                "hdr.ipv4.dst_addr": (client_ip, 32),
                "hdr.ib_bth.dst_qp": to_client_qp,
                # "hdr.ib_bth.opcode": opcode,
            },
            action_name="MyIngress.record_switch_port",
            action_params={
                "index": index,
            }
        )
        self.s1.WriteTableEntry(table_entry)
        print("Installed ingress QP rule on %s" % self.s1.name)

    def writeIPRules(self, rfile_ip_addr, rproxy_ip_addr, rclient_ip_addr, rproxy_mac, rclient_mac, to_proxy_qp,
                     to_client_qp, index, eport):
        # 1) match server B, rewrite dst from server A to client
        table_entry = self.p4info_helper.buildTableEntry(
            table_name="MyIngress.ipv4_lpm",
            match_fields={
                "hdr.ipv4.src_addr": (rfile_ip_addr, 32),
                "hdr.ib_bth.dst_qp": to_proxy_qp,
                # "hdr.ib_bth.opcode": opcode,
            },
            action_name="MyIngress.ipv4_forward",
            action_params={
                "switch_ip": rproxy_ip_addr,
                "host_ip": rclient_ip_addr,
                "switch_mac": rproxy_mac,
                "host_mac": rclient_mac,
                "client_qp": to_client_qp,
                "port_index": index,
                "port": eport,
            })
        self.s1.WriteTableEntry(table_entry)
        print("Installed ingress tunnel rule on %s" % self.s1.name)

    def writeTunnelRules(self, rclient_address, rclient_qp, rkey, raddr):
        # 1) match server B, rewrite dst from server A to client
        table_entry = self.p4info_helper.buildTableEntry(
            table_name="MyEgress.rdma_translate",
            match_fields={
                "hdr.ipv4.dst_addr": (rclient_address, 32),
                "hdr.ib_bth.dst_qp": rclient_qp,
            },
            action_name="MyEgress.translate",
            action_params={
                "mount_raddr": raddr,
                "mount_rkey": rkey
            })
        self.s1.WriteTableEntry(table_entry)
        print("Installed egress translate rule on %s" % self.s1.name)


p4control = CreateControl()


class HandleServer(socketserver.BaseRequestHandler):

    def handle(self) -> None:
        global threading_index
        global p4control
        threading_index = threading_index + 1
        print("now threading index is " + str(threading_index))
        print("\n---------------------------- A CONNECT ACCEPT  --------------------------------")
        self.client = SocketClient()
        self.client.request()
        conn = self.request
        # # TODO: here, how to bring the name into the handle func
        node = SocketNode(c.NAME)

        while True:
            try:
                # conn = self.request
                # self.client=SocketClient()
                # self.client.request()
                # # TODO: here, how to bring the name into the handle func
                # node = SocketNode(c.NAME)
                msg = conn.recv(c.BUFFER_SIZE)
                if msg == m.BEGIN_MSG:
                    print("begin, exchange the metadata")
                    conn.sendall(m.READY_MSG)
                    # exchange the metadata
                    # use socket to exchange the metadata of server
                    client_metadata_attr_bytes = conn.recv(c.BUFFER_SIZE)
                    self.client_metadata_attr = deserialize(client_metadata_attr_bytes)
                    print_info("the client metadata attr is:\n" + str(self.client_metadata_attr))
                    # qp_attr
                    node.qp2init().qp2rtr(self.client_metadata_attr).qp2rts()
                    # node.post_recv(node.recv_mr)
                    # send its buffer attr to client
                    buffer_attr_bytes = serialize(node.buffer_attr)
                    conn.sendall(buffer_attr_bytes)
                    # exchange metadata done
                    # node.poll_cq()
                    if c.is_control_plane != True:
                        # from switch to client
                        proxy_ip_addr = "192.168.56.3"
                        client_ip_addr = "192.168.56.2"
                        file_ip_addr = "192.168.56.4"
                        proxy_mac = "08:00:27:d1:20:9a"
                        client_mac = "08:00:27:4f:de:53"

                        # convert pairs

                        to_client_qp = self.client_metadata_attr.qp_num  # from file node

                        to_proxy_qp = self.client.node.buffer_attr.qp_num  # from proxy
                        print("file_proxy_qp " + str(to_proxy_qp))
                        print("proxy_client_qp " + str(to_client_qp))
                        p4control.writeQPrules(client_ip_addr, to_client_qp, threading_index)

                        p4control.writeIPRules(file_ip_addr, proxy_ip_addr, client_ip_addr,
                                               proxy_mac, client_mac, to_proxy_qp, to_client_qp, threading_index,
                                               egress_port)

                        # modify port qp and port

                        p4control.writeTunnelRules(client_ip_addr, to_client_qp, self.client_metadata_attr.remote_stag,
                                                   self.client_metadata_attr.addr)  # remote_info[i]['rkey'], remote_info[i]['addr'])
                        print("write switch rules ok!")

                elif msg == m.SEND_FILE_MSG:
                    content = node.p_receive_send()
                    print("-----------receive from client-------")
                    self.client.node.post_recv(self.client.node.recv_mr)
                    self.client.socket.sendall(m.SEND_FILE_MSG)
                    print("-----------send to servers--------")
                    file_stream = self.client.node.p_trans_write(self.client.server_metadata_attr, content)
                    # print(file_stream)
                    # node.p_return_write(file_stream,self.client_metadata_attr)
                    # s.node,s.client_metadata_attr,c.node,c.server_metadata_attr
                    # print("success write file to client")
                elif msg == m.DONE_MSG:
                    print("done")
                    node.close()
                    break
            except Exception as err:
                print(err)
                node.close()
                break
        print("---------------------------- A CONNECT DONE  --------------------------------")


# connection establish use socket, then use ibv to rdma
class SocketServer:
    def __init__(self, name=c.NAME, addr=c.ADDR_SERVER, port=c.PORT_INT, options=c.OPTIONS):
        self.server = socketserver.ThreadingTCPServer((addr, port,), HandleServer)

        print("listening in", addr, port)
        self.name = name
        self.options = options

    def serve(self):
        self.server.serve_forever()

