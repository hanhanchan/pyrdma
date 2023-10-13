
#ifndef _HEADERS_
#define _HEADERS_
typedef bit<9>  egressSpec_t;
typedef bit<16> ether_type_t;
typedef bit<48> mac_addr_t;
typedef bit<8> ip_protocol_t;
typedef bit<32> ipv4_addr_t;
typedef bit<16> udp_port_t;

typedef bit<3> max_concurrent_t;
typedef bit<3> max_reply_chunk_t;
typedef bit<1> mtye_t;
typedef bit<32> program_t;
typedef bit<2> rver_t;
typedef bit<2> programv_t;
typedef bit<1> ver_t;
typedef bit<8> flow_ctrl_t;
typedef bit<4> server_offload_t;
typedef bit<32> xid_t;
typedef bit<8> ib_opcode_t;
const ip_protocol_t IP_PROTOCOLS_UDP = 0x11;
const ether_type_t ETHERTYPE_IPV4   = 16w0x0800;
const ether_type_t ETHERTYPE_ARP    = 16w0x0806;
const ether_type_t ETHERTYPE_ROCEv1 = 16w0x8915;
const bit<16> UDP_PORT_ROCEV2  =   4791;
const ib_opcode_t RC_RDMA_WRITE_FIRST = 00000110;
const ib_opcode_t RC_RDMA_WRITE_MIDDLE = 8w0b00000111;
const ib_opcode_t RC_RDMA_WRITE_LAST = 8w0b00001000;
const ib_opcode_t UC_RDMA_WRITE_FIRST = 00100110;
const ib_opcode_t UC_RDMA_WRITE_MIDDLE = 00100111;
const ib_opcode_t UC_RDMA_WRITE_LAST = 00101000;
typedef bit<16> rhandle_t;
typedef bit<8> dma_len_t;
typedef bit<64> roffset_t;
enum bit<8> ip_type_t {
    ICMP = 1,
    UDP  = 17
}

// for ib 
// IB/RoCE-specific types:
typedef bit<128> ib_gid_t;
typedef bit<24> sequence_number_t;
typedef bit<24> queue_pair_t;
typedef bit<16> rkey_t;
typedef bit<32> addr_t;

//rpc related type
const ver_t RPC_RDMA_VERSION=1;
const flow_ctrl_t RPC_FLOW_CONTROL=128;
enum bit<2> rpc_rdma_type_t {
    RDMA_MSG = 0,
    RDMA_NOMSG = 1 
}
const mtye_t MSG_TYPE=0; //call 
const rver_t RPC_VERSION=2;
const program_t RPC_PROGRAM=100003;
const programv_t RPC_PROGRAMV=3;

enum bit<8> rpc_type_t {
    // todo: remedy other procedure type 
    VOID=0 ,
    GETATTR=1 ,
    ACCESS=4 ,
    READDIRPLUS=17
}
 
// RDMA MTU (packet size). Matches ibv_mtu enum in verbs.h
enum bit<3> packet_size_t {
    IBV_MTU_128  = 0, // not actually defined in IB, but useful for no recirculation tests
    IBV_MTU_256  = 1,
    IBV_MTU_512  = 2,
    IBV_MTU_1024 = 3
}

// Drop probability between 0 and 32767
typedef bit<16> drop_probability_t;

 
// Port metadata, used for drop simulation
struct port_metadata_t {
    drop_probability_t ingress_drop_probability;
    drop_probability_t egress_drop_probability;
}

 
header ethernet_h {
    bit<48> mst_addr;
    bit<48> msrc_addr;
    bit<16>    ether_type;
}

header ipv4_h {
    bit<4>        version;
    bit<4>        ihl;
    bit<8>        diffserv;
    bit<16>       total_len;
    bit<16>       identification;
    bit<3>        flags;
    bit<13>       frag_offset;
    bit<8>        ttl;
    ip_protocol_t protocol;
    bit<16>       hdr_checksum;
    ipv4_addr_t   src_addr;
    ipv4_addr_t   dst_addr;
}
 
header udp_h {
    udp_port_t src_port;
    udp_port_t dst_port;
    bit<16> length;
    bit<16> checksum;
}
 
// InfiniBand-RoCE Base Transport Header
header ib_bth_h {
    ib_opcode_t       opcode;
    bit<1>            se;
    bit<1>            migration_req;
    bit<2>            pad_count;
    bit<4>            transport_version;
    bit<16>           partition_key;
    bit<1>            f_res1;
    bit<1>            b_res1;
    bit<6>            reserved;
    queue_pair_t      dst_qp;
    bit<1>            ack_req;
    bit<7>            reserved2;
    sequence_number_t psn;
}

header ib_aeth_h {
    addr_t raddr;
    rkey_t r_key;
    bit<32> len;
} 

// InfiniBand-RoCE RDMA Extended Transport Header
header ib_reth_h {
    addr_t raddr;
    rkey_t r_key;
    bit<32> len;
}

// InfiniBand-RoCE Immediate Header
header ib_immediate_h {
    bit<32> immediate;
}

// InfiniBand-RoCE ICRC Header
header ib_icrc_h {
    bit<32> icrc;
}

header rpc_rdma_h{
    bit<32> xid;
    bit<32> ver;
    bit<32> flow_ctrl;
    bit<32> rmsg_type; 
    bit<32> rlist;  
}

header reply_chunk1_h{
    bit<32> wcount;
    bit<32> rhandle;
    bit<32> dma_len;
    bit<64> roffset;
}
header reply_chunk2_h{
    rhandle_t rhandle;
    dma_len_t dma_len;
    roffset_t roffset;
}

header rpc_h{
    xid_t xid;
    mtye_t mtype;
    rver_t rver;
    program_t program;
    programv_t programv;
    rpc_type_t rproc;
}
// Full header stack
struct headers {
    ethernet_h     ethernet;
    ipv4_h         ipv4;
    udp_h          udp;
    ib_bth_h       ib_bth;
    ib_reth_h      ib_reth;
    //ib_immediate_h ib_immediate;
   //ib_icrc_h      ib_icrc;
    //rpc_h          rpc;
    //reply_chunk1_h reply_chunk1;
   // reply_chunk2_h  reply_chunk2;
    //rpc_rdma_h     rpc_rdma;
  
}
struct metadata {
}
 
#endif /* _HEADERS_ */
