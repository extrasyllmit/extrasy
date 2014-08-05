#
# This file is part of ExtRaSy
#
# Copyright (C) 2013-2014 Massachusetts Institute of Technology
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# standard python library imports
from collections import deque
from fcntl import ioctl
import logging
from math import ceil
from math import floor
import os
import pwd
import random
import socket
import struct
import sys
import threading
from threading import Thread
import time

# third party library imports
from gnuradio import gr
from gruel import pmt

# project specific imports
import digital_ll
from digital_ll.lincolnlog import dict_to_xml



class Passive_Traffic():
    '''
    This class exists only so that function calls expecting other traffic models don't fail
    '''
    def __init__(self):
        self.keep_going = True
        
    
    def run(self):
        pass
    
    def start(self):
        pass      
        
    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''    
        pass
    
    def shut_down(self):
        pass



class Infinite_Backlog_PDU_Streamer(gr.basic_block):
    
    '''
    Keep another block's packet queue full. The other block must have a way to query
    the current queue size. This query function is passed in as query_queue_size.
    When the queue size drops below the fill threshold, this block will send out
    enough packets to fill the queue.
    '''
    def __init__(self, options, query_queue_size=None):
        
        gr.basic_block.__init__(
              self,
              name = "infinite_backlog_pdu",
              in_sig = None,
              out_sig = None)
        
        
        self.q_size = query_queue_size
        
        # pull parameters out of options
        self.max_queue_size = options.mac_tx_packet_q_depth
        self.fill_thresh = options.infinite_backlog_refill_threshold
        self.destination_id_list = options.sink_mac_addresses
        self.payload_size = options.infinite_backlog_payload_size
        
        # note: this is 1000 chars long
        self.data = ("GNU Radio is a free & open-source software development toolkit that "
            "provides signal processing blocks to implement software radios. It can be " 
            "used with readily-available low-cost external RF hardware to create "
            "software-defined radios, or without hardware in a simulation-like "
            "environment. It is widely used in hobbyist, academic and commercial "
            "environments to support both wireless communications research and real-world "
            "radio systems.   GNU Radio applications are primarily written using the "
            "Python programming language, while the supplied performance-critical signal "
            "processing path is implemented in C++ using processor floating-point "
            "extensions, where available. Thus, the developer is able to implement "
            "real-time, high-throughput radio systems in a simple-to-use, "
            "rapid-application-development environment.    While not primarily a "
            "simulation tool, GNU Radio does support development of signal processing "
            "algorithms using pre-recorded or generated data, avoiding the need for "
            "actual RF hardware.")
        
        # make as many copies of data as needed to exceed the desired payload size
        self.payload = self.data*int(ceil(float(self.payload_size)/float(len(self.data))))
        
        # slice payload down to desired payload size
        self.payload = self.payload[:self.payload_size]
        
        # convert payload to pmt
        self.payload = pmt.from_python(self.payload)
        self.OUT_PKT_PORT = pmt.from_python("out_pkt_port")
        
        # register outgoing packet port
        self.message_port_register_out(self.OUT_PKT_PORT)
        
        self._traffic_trigger_thread = threading.Thread(target=self._traffic_trigger_probe)
        self._traffic_trigger_thread.daemon = True
        self._traffic_trigger_thread.start()
        
        sys.stderr.write("init complete\n")
        
    def do_burst(self):
        #sys.stderr.write("traffic gen do_burst called\n")
        
        if (self.q_size is not None) and hasattr(self.q_size, '__call__') :
            current_q_size = self.q_size();
        else:
            sys.stderr.write("queue size not callable\n")
            current_q_size = 0
        
        if current_q_size < self.fill_thresh:
            num_calls = max(0,self.max_queue_size - current_q_size )
            #sys.stderr.write("adding %d packets to queue \n" % num_calls)
            for k in range(num_calls):
                meta= {"destinationID":random.choice(self.destination_id_list)}
                self.message_port_pub(self.OUT_PKT_PORT, 
                                      pmt.pmt_cons(pmt.from_python(meta), self.payload))
        
        return True
    
    def _traffic_trigger_probe(self):
        while True:
            val = self.do_burst()
            try: self.set_traffic_trigger(val)
            except AttributeError, e: pass
            time.sleep(1.0/(10.0))
            
    def shut_down(self):
        '''
        Just a placeholder so all traffic models have similar interface
        '''
        pass
        

    
    @staticmethod       
    def add_options(normal, expert):
        """
        Adds Infinite_Backlog_PDU_Streamer specific options to the Options Parser
        """
        
        normal.add_option("--sink-mac-addresses", type="string", 
                      help=("List of destination mac IDs in the network" ))
        normal.add_option("--infinite-backlog-refill-threshold", default=50, type="int",
                          help=("Generate more packets once the number of packets " +
                                "in the app layer input queue drops below this number " +
                                "[default=%default]"))
        normal.add_option("--mac-tx-packet-q-depth", default=50, type="int",
                          help=("Max size of the application layer packet queue " +
                                "[default=%default]"))
        normal.add_option("--infinite-backlog-payload-size", default=140, type="int",
                          help=("Number of bytes in a data packet payload " +
                                "[default=%default]"))
        
    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''    
        section_indent = indent_level
        
        # infinite backlog section start
        logger.info("%s<infinite>", section_indent*'\t')
        section_indent += 1
        
        # infinite backlog section param values
        params = {
                  "node_sink_address_list":self.destination_id_list,
                  "max_queue_size":self.max_queue_size,
                  "fill_threshold":self.fill_thresh,
                  "payload_size":self.payload_size
                  }
        logger.info(dict_to_xml(params, section_indent))
        
        # infinite backlog section end
        section_indent -= 1
        logger.info("%s</infinite>", section_indent*'\t')   
        
        
        
        
        
        
class Tunnel_Handler_PDU_Streamer(gr.basic_block):
    '''
    This class interfaces between the MAC and network layers using a Tunnel object. 
    Any packets it gets from the network layer are encapsulated in a MAC layer header and placed
    into a queue for transmission by the MAC layer. Any valid data packets the MAC layer gets from
    a remote node are passed out to the network layer
    
    See /usr/src/linux/Documentation/networking/tuntap.txt 
    '''

        
    def __init__(self, options):
        
        gr.basic_block.__init__(
              self,
              name = "tunnel_handler_pdu",
              in_sig = None,
              out_sig = None)
        
        # store initial vars from constructor
        self.tun_device_filename = options.tuntap_device_filename
        self.tun_device_name = options.tuntap_device_name
        
        self.max_pkt_size = int(options.tuntap_mtu)
        
        # TODO: Don't set up interface if options are wrong
        
        # process the mac and IP address lists from strings to lists
        self.mac_id = options.source_mac_address
        self.mac_id_list = options.sink_mac_addresses
        self.ip_string_list = options.tuntap_sink_ip_addresses.split(',')
            
        self.mac_high_bytes = 0xc6ffffff
        
        # get this node's mac address in hex
        hex_str = '%12x' % ( (self.mac_high_bytes<<16) + self.mac_id)
        self.mac_hex = ':'.join( [ hex_str[0:2], hex_str[2:4], hex_str[4:6],
                                   hex_str[6:8], hex_str[8:10], hex_str[10:12] ] )
        
        self.ip_address = options.tuntap_source_ip_address
               
        self.use_persistent_tunnel = options.tuntap_use_persistent_device
        self.logger = logging.getLogger('developer')
           
        # define initial values for tun_fd and self.tun_ifname in case the node source
        # address is invalid
        self.tun_fd = -1; 
        self.tun_ifname = "error"
        self.keep_going = False
        #self.ip_address = "0.0.0.0"
        

        self.keep_going = True
        
        
        
        self.OUT_PKT_PORT = pmt.from_python("out_pkt_port")
        self.IN_PKT_PORT = pmt.from_python("in_pkt_port")
        # register outgoing packet port
        self.message_port_register_out(self.OUT_PKT_PORT)
        
        # register incoming packet port
        self.message_port_register_in(self.IN_PKT_PORT)
        
        # register message handler for input port
        self.set_msg_handler(self.IN_PKT_PORT, self.write_to_network)
        
        # open the TUN/TAP interface
        (self.tun_fd, self.tun_ifname) = self.open_tun_interface()
    
        # set up the mac and ip address for the tunnel device
        self.configure_tun_device()
         
        # set up the arp cache
        self.add_arp_entries() 
         
        self._network_read_thread = threading.Thread(target=self.read_from_network)
        
        # mark this thread as a daemon so the program doesn't wait for it when
        # closing
        self._network_read_thread.daemon = True
        
        # don't start the thread until you're ready to deal with traffic
        self._network_read_thread.start()
        

        

    def open_tun_interface(self):
        '''
        Initialize the TUN/TAP interface
        '''
        
        # get current user name 
        user = pwd.getpwuid( os.getuid() )[0]
        
        # TODO: Add try catch statement with description of common fixes to problems if
        # 'ip tuntap add dev' command fails
        
        if self.use_persistent_tunnel == False:
            cmd= 'sudo ip tuntap add dev ' + self.tun_device_name + ' mode tap user ' + user
            os.system(cmd)
        
        
        IFF_TUN        = 0x0001   # tunnel IP packets
        IFF_TAP        = 0x0002   # tunnel ethernet frames
        IFF_NO_PI    = 0x1000   # don't pass extra packet info
        IFF_ONE_QUEUE    = 0x2000   # beats me ;)

        # using TAP mode with no Packet Information so read calls will return at packet
        # boundaries and the kernel won't add extra packet information
        mode = IFF_TAP | IFF_NO_PI
        TUNSETIFF = 0x400454ca

        try:
            tun = os.open(self.tun_device_filename, os.O_RDWR)
            ifs = ioctl(tun, TUNSETIFF, struct.pack("16sH", self.tun_device_name, mode))
        except IOError:
            print
            print "----------------------------------------------------------------------"
            print "-"
            print "- Unable to open tunnel device name %s" % (self.tun_device_name)
            print "- If using a persistent device for debug, verify the current user"
            print "- is the owner of the device. Otherwise verify permissions are"
            print "- set to allow rw access on /dev/net/tun. Suggested command for "
            print "- opening a persistent device is:"
            print "-"
            print "- user@host:~$ sudo ip tuntap add dev gr0 mode tap user username"
            print "-"
            print "- where gr0 is the device name and username is the current username"
            print "-"
            print "----------------------------------------------------------------------"
            print
            raise
        
        ifname = ifs[:16].strip("\x00")
        return (tun, ifname)

    def configure_tun_device(self):
        self.logger.debug("configuring tun/tap device")
        # configure the mac address and IP address of the virtual interface
        # take the device down or we can't reset the mac address
        cmd = 'sudo ifconfig %s down' % self.tun_ifname
        self.logger.debug("%s",cmd)
        os.system(cmd)
        
        # set the mac address
        cmd = 'sudo ifconfig %s hw ether %s' % (self.tun_ifname, self.mac_hex)
        self.logger.debug("%s",cmd)
        os.system(cmd)
        
        # set the ip address
        cmd= 'sudo ifconfig %s %s' % (self.tun_ifname, self.ip_address)
        self.logger.debug("%s",cmd)
        os.system(cmd)
        
        # set the MTU
        cmd= 'sudo ifconfig %s mtu %i' % (self.tun_ifname, self.max_pkt_size)
        self.logger.debug("%s",cmd)
        os.system(cmd)
        
        # bring the interface back up
        cmd = 'sudo ifconfig %s up' % self.tun_ifname
        self.logger.debug("%s",cmd)
        os.system(cmd)
        
        
        print "Allocated virtual ethernet interface: %s" % (self.tun_ifname,)
        print
        print "  $ IP address of device %s is %s" % (self.tun_ifname, self.ip_address)
        print  
        
    def add_arp_entries(self):
        # add entries to ARP cache so ARP broadcasts aren't necessary
        for ind, mac_id in enumerate(self.mac_id_list):
            mac_hex_str = '%04x' % mac_id
            mac_hex = 'c6:ff:ff:ff:%s:%s' %( mac_hex_str[0:2], mac_hex_str[2:4])
            ip_addr = self.ip_string_list[ind]
            self.logger.debug("adding arp entry ip: %s, mac: %s", ip_addr, mac_hex)
            
            cmd = 'sudo arp -s %s %s' % (ip_addr, mac_hex)
            os.system(cmd)
    
    def remove_arp_entries(self): 
        # remove the entries you just added in the arp cache
        
        for ip_addr in self.ip_string_list:
            self.logger.debug("removing arp entry ip: %s", ip_addr)
            cmd = 'sudo arp -d %s' % ip_addr
            os.system(cmd)  
    
    def read_mac_dest(self, data):
        
        # each hex char encodes 4 bits, and mac destination is first 6 bytes, so 
        # read out the first 12 characters
        all_bytes = (struct.unpack_from('<cccccc',data) )
        #self.logger.debug("full mac dest hex is %s",all_bytes)
        high_bytes, low_bytes = struct.unpack_from('!LH',data)
        #self.logger.debug("high bytes %x, low_bytes %x",high_bytes, low_bytes)
        
        # verify that this is a mac address we actually want to talk to
        if high_bytes == self.mac_high_bytes:
            # only return back the lowest 16 bits of the mac address since that's 
            # all that fits into our header
            return low_bytes
        # this is a broadcast
        elif (high_bytes == 0xffffffff) and (low_bytes == 0xffff):
            return -1
        else:
            return -2
        
        
        return  low_bytes       
          
    def read_from_network(self):
        '''
        This function reads packets from the network layer and puts them in a queue for the MAC
        layer to handle.
        '''
        
        self.logger.debug("starting tuntap read from network")
        
        while self.keep_going:  
           
            data = os.read(self.tun_fd, 10*1024)
            
            #print data.encode('hex')
            # if there's an error with the tunnel interface
            if not data:
                self.logger.error("Error reading from tunnel device")
                break
            
            # only add packet to queue if it is under the maximum allowed size
            
#            if len(data) < self.max_pkt_size:  
            # map ip destination address to appropriate mac address
            to_id = self.read_mac_dest(data)
            self.logger.debug("read returned. len data is %d", len(data))
#                self.logger.debug("data is %s", data)
            if to_id >0:    
                self.logger.debug("sending message to mac id %d", to_id)
                meta= {"destinationID":to_id}
                self.message_port_pub(self.OUT_PKT_PORT, 
                              pmt.pmt_cons(pmt.from_python(meta), 
                                           pmt.from_python(data)))
            # handle broadcast case
            elif to_id == -1:
                for mac_id in self.mac_id_list:
                    if mac_id != self.mac_id:
                        self.logger.debug("sending broadcast message to mac id %d", mac_id)
                        meta= {"destinationID":mac_id} 
                        self.message_port_pub(self.OUT_PKT_PORT, 
                                              pmt.pmt_cons(pmt.from_python(meta), 
                                                           pmt.from_python(data)))
#            else:
#                self.logger.debug("type of len(data) is %s. Type of max_pkt_size is %s", type(len(data)), type(self.max_pkt_size))
#                msg = ()
#                self.logger.warning("provided packet length of %s exceeds maximum " + 
#                                    "allowed packet length of %s. Dropping this packet",
#                                    len(data), self.max_pkt_size)

             
        
        
        try: 
            os.close(self.tun_fd)
        except OSError as e:
            if e.errno == os.errno.EBADF:
                self.logger.warning("Tunnel file descriptor is bad");
            else:
                self.logger.error("unexpected error when closing tunnel file descriptor")
                raise    
            
        self.logger.debug("tunnel interface read from network complete")
            
    def write_to_network(self,payload):
        '''
        This function accepts packets from the MAC layer and forwards them up to the network layer
        '''
        data = str(pmt.to_python(payload))
        #self.logger.debug("Write to network called. Keep going is %s", self.keep_going)
        # only forward packets while tunned is active
        if self.keep_going:
            self.logger.debug("sending packet to app layer, length %i", 
                              len(data))
            os.write(self.tun_fd, data)
    
    def shut_down(self):
        '''
        This function makes the traffic generator break out of any infinite loops and shut down
        '''
        self.logger.info("Shutting down tunnel interface")
        self.keep_going = False
        
        
        ip_split = self.ip_address.split('.')
        # send a ping to the current interface to break out of the blocking read on the 
        # tunnel device
        
        ping_address = '.'.join(ip_split[:3]) + '.0'

        # send a ping out the broadcast address and wait for 1 second before
        # exiting. This will force the read_from_network out of it's 
        # blocking read call
        cmd = 'ping -c 1 -b -w 1 %s' % ping_address
        os.system(cmd)
        
        
        # sleep to make sure all traffic finishes
        time.sleep(.1)
        # TODO: Add try catch statement with description of common fixes to problems if
        # 'ip tuntap del dev' command fails
        
        if self.use_persistent_tunnel == False:
            # remove tunnel
            self.logger.debug("taking down interface")
            cmd= 'sudo ifconfig ' + self.tun_device_name + ' down'
            os.system(cmd)
            
            self.logger.debug("removing tuntap device")
            cmd= 'sudo ip tuntap del dev ' + self.tun_device_name + ' mode tap'
            os.system(cmd)
            
            self.remove_arp_entries()
        else:
            print
            print "----------------------------------------------------------------------"
            print "- As use_persistent_tunnel==True, not removing tuntap device %s " % self.tun_device_name
            print "- If you want to remove the device, try the following command:"
            print "-"
            print "- user@host:~$ sudo ip tuntap del dev " + self.tun_device_name + " mode tap"
            print "-"
            print "----------------------------------------------------------------------"  
            print
            
        
                
        self.logger.info("Tunnel interface shutdown complete")     
        
                    
    @staticmethod       
    def add_options(normal, expert):
        """
        Adds Tunnel_Listener specific options to the Options Parser
        """
        
        normal.add_option("--source-mac-address", default=1, type="int",
                      help=("Source ID of this node " +
                            "[default=%default]"))
        
        expert.add_option("--tuntap-device-filename", default="/dev/net/tun",
                          help="path to tun device file [default=%default]")
        
        expert.add_option("--tuntap-device-name", default="gr0",
                          help="name of tunnel device [default=%default]")
        
        expert.add_option("--tuntap-use-persistent-device",
                          help="Use a tunnel device that's already allocated, such as when debugging with wireshark",
                          action="store_true", default=False)
        
        normal.add_option("--tuntap-source-ip-address", default='192.168.200.1',
                      help=("Source ID of this node " +
                            "[default=%default]"))
        
        expert.add_option("--tuntap-sink-ip-addresses", default="192.168.200.1, 192.168.200.2, 192.168.200.3",
                          help="List of IP addresses of nodes in the network. Only needed if using tun/tap")
        expert.add_option("--sink-mac-addresses", default="1, 2, 3",
                          help="List of mac IDs in the network in the same order as ip-list")
        
        expert.add_option("--tuntap-mtu", default="1500",
                          help="Max packet size for tuntap device [default=%default]")
        # TODO: Am I missing any options? How do you pick your IP?
       
        
            
    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''    
        section_indent = indent_level
        
        # infinite backlog section start
        logger.info("%s<tunnel>", section_indent*'\t')
        section_indent += 1
        
        # tunnel section param values
        params = {"tun_device_filename":self.tun_device_filename,
                  "tun_ifname":self.tun_ifname}
        
                
        # TODO: Am I missing any interesting parameters?
        
        logger.info(dict_to_xml(params, section_indent))
        
        # infinite backlog section end
        section_indent -= 1
        logger.info("%s</tunnel>", section_indent*'\t')

class csma_msg_queue_adapter(gr.basic_block):
    '''
    classdocs
    '''

    
    pkt_queue = None
    my_id = None
    packet_id = None
    max_packet_id = None
    
    crc_result = None
    pad_bytes = None
    pkt_code = None
    phy_code = None
    mac_code = None
    more_data = None
    
    IN_PORT = None
    
    def __init__(self, queue_size, from_id):
        '''
        Constructor
        '''
        
        gr.basic_block.__init__(
              self,
              name = "msg_queue_adapter",
              in_sig = None,
              out_sig = None)
        
        self.pkt_queue = deque(maxlen=queue_size)
        self.my_id = int(from_id)
        
        self.packet_id = 0
        self.max_packet_id = 65535
        
        # set up constants for packet headers
        self.crc_result = True
        self.pad_bytes = 0 
        self.pkt_code = 'DATA'
        self.phy_code = 0
        self.mac_code = 0
        self.more_data = 0
        
        
        # set up message port
        self.IN_PORT = pmt.from_python("in_port")
        self.message_port_register_in(self.IN_PORT)
        
        # set up message port
        self.OUT_PORT = pmt.from_python("out_port")
        self.message_port_register_out(self.OUT_PORT)        
        
        # register message handler for input port
        self.set_msg_handler(self.IN_PORT, self.store_pkt)
         
    def store_pkt(self, pdu):
        '''
        Try to put another packet on to the pkt_queue. If the queue is full, don't block,
        just drop the packet, catch the Full exception, and continue on
        '''
        
        # make sure the pdu is a pmt pair before handling it 
        if pmt.pmt_is_pair(pdu):
            #print "pmt is a pair"
            # get the first and last elements of the pair
            meta = pmt.to_python(pmt.pmt_car(pdu))
            data = pmt.to_python(pmt.pmt_cdr(pdu))
            
            # make sure there's some metadata associated with the packet, otherwise 
            # drop it
            if not (meta is None) and ("destinationID" in meta):
                
                # if there's any room left in the queue
                if len(self.pkt_queue) < self.pkt_queue.maxlen:
                    
                    pkt = csma_pkt_converter(my_id = self.my_id, 
                                             crc_result = self.crc_result, 
                                             from_id = self.my_id, 
                                             to_id = int(meta["destinationID"]), 
                                             pktno = self.packet_id, 
                                             pad_bytes = self.pad_bytes, 
                                             pkt_code = self.pkt_code, 
                                             phy_code = self.phy_code, 
                                             mac_code = self.mac_code, 
                                             more_data = self.more_data, 
                                             data = data)
                    
                    self.packet_id = (self.packet_id +1) % self.max_packet_id
                    
                    # add packaged packet to pkt queue
                    self.pkt_queue.append(pkt)
                    
                    
    def queue_size(self): 
        return len(self.pkt_queue)
    
    def send_pkt(self, data):
        self.message_port_pub(self.OUT_PORT, pmt.from_python(data))     