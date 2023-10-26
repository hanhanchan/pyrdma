/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>
#include "headers.p4"
#define MAX_CONCURRENT 16
//time1121
parser MyParser(packet_in pkt,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4 : parse_ipv4;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            IP_PROTOCOLS_UDP : parse_udp;
        }
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        transition select(hdr.udp.dst_port) {
            UDP_PORT_ROCEV2 : parse_bth;
        }
    }
    state parse_bth {
        pkt.extract(hdr.ib_bth);
        transition select(hdr.ib_bth.opcode) {
            default: parse_reth;
        }
        
    }
    state parse_reth {
        pkt.extract(hdr.ib_reth);
        transition accept;
    }
}


/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    action drop() {
        mark_to_drop(standard_metadata);
    }
    register<bit<16>>(MAX_CONCURRENT) switch_src_port;
 
    action record_switch_port(bit <32> index){
        switch_src_port.write((bit <32> )index,hdr.udp.src_port);
    }

    action ipv4_forward(ipv4_addr_t switch_ip, ipv4_addr_t host_ip, bit<48> switch_mac,  bit<48> host_mac, bit<24> client_qp, bit<16> port_index,egressSpec_t port) {
        standard_metadata.egress_spec = port;
        bit<16> switch_src_p;    
        hdr.ethernet.msrc_addr = switch_mac;
        hdr.ethernet.mst_addr = host_mac;
        hdr.ipv4.src_addr=switch_ip;
        hdr.ipv4.dst_addr=host_ip;
        switch_src_port.read(switch_src_p, (bit <32> )port_index);
        hdr.udp.src_port=switch_src_p;
        hdr.ib_bth.dst_qp=client_qp;
    }

    table ipv4_lpm {
        key = {
  
            hdr.ipv4.src_addr: lpm;
            hdr.ib_bth.dst_qp: exact;
            hdr.ib_bth.opcode:exact; 
        }
        actions = {
            ipv4_forward;
            drop;
            NoAction;
        }
        size = 1024;
        default_action = NoAction;
    }
    table record_port {
        key={
            hdr.ipv4.dst_addr:lpm;
            hdr.ib_bth.dst_qp: exact;
            hdr.ib_bth.opcode:exact;           
        }
        actions={
        record_switch_port;

        }
    }

    apply{
            if(hdr.ib_bth.isValid()){
                ipv4_lpm.apply();
                record_port.apply();
            }
         }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action translate(addr_t mount_raddr, rkey_t mount_rkey) {
        hdr.ib_reth.setValid();
        hdr.ib_reth.r_key = mount_rkey;
        hdr.ib_reth.raddr=mount_raddr;
    }

    table rdma_translate {
        key = {
            hdr.ipv4.dst_addr       : lpm;
            hdr.ib_bth.dst_qp: exact; 
        }
        actions = {
            translate;
            NoAction;
        }
        size = 512;
        default_action = NoAction;
    }    
    apply{
        if(hdr.ib_reth.isValid())
        {
            rdma_translate.apply();
        }

    }
                    
}
/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
     apply {

    }
}


/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out pkt, in headers hdr) {
    apply {
        pkt.emit(hdr.ethernet);
        pkt.emit(hdr.ipv4);
        pkt.emit(hdr.udp);
        pkt.emit(hdr.ib_bth);
        pkt.emit(hdr.ib_reth);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;
