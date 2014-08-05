#!/usr/bin/env python
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

from gnuradio import gr
from gnuradio import eng_notation
from gnuradio import gru
from digital_ll import modulation_utils 
from gnuradio.eng_option import eng_option
from gruel import pmt
from optparse import OptionParser
from gnuradio.gr import firdes
from argparse import Namespace
from argparse import ArgumentParser
from gnuradio import uhd
from mac_ll import csma
from mac_ll import csma_pkt_converter

from threading import Semaphore
from threading import Timer
from threading import Event
from collections import deque


from digital_ll import receive_path_narrowband
from digital_ll import transmit_path_narrowband
from digital_ll import receive_path_ofdm
from digital_ll import transmit_path_ofdm
from uhd_interface import uhd_transmitter
from uhd_interface import uhd_receiver

import mac_ll
import digital_ll

import os, sys
import random 
import time
from time import sleep

# logging stuff

import logging.config
from digital_ll.lincolnlog import dict_to_xml
from digital_ll import sample_counter

from collections import deque
import digital_ll
from digital_ll import Payload_Packet
from digital_ll import packet_utils 

# config file parsing
from ConfigParser import SafeConfigParser


from gruel import pmt;
import numpy;

from digital_ll import lincolnlog


# traffic generation
#from mac_ll import Passive_Traffic
#from mac_ll import Queue_Filler
#from mac_ll import Tunnel_Handler
from mac_ll import Infinite_Backlog_PDU_Streamer
from mac_ll import Tunnel_Handler_PDU_Streamer
from mac_ll import csma_msg_queue_adapter

import commands
import re

SNR_db = 30
sig_amp = 1.0
noise_amp = 10**(-SNR_db/20)
print sig_amp, noise_amp
key_sym = pmt.pmt_intern("key")

#def num_samps_from_chars(num_inputs, samples_per_symbol, bits_per_symbol):
#    chunkSize = 512
#    # hack to guarantee our event size is large enough
#    num_chunks = ceil( (num_inputs*20+50)/512.0)
#    return int(num_chunks*chunkSize) 


# ////////////////////////////////////////////////////////////////////
#                     the flow graph
# ////////////////////////////////////////////////////////////////////

class my_top_block(gr.top_block):

    def __init__(self, mod_class, demod_class,
                 rx_callback, options):

        gr.top_block.__init__(self)
        
        print "using rx tap: %s" % options.use_rx_tap
        
        # Get the modulation's bits_per_symbol
        args = mod_class.extract_kwargs_from_options(options)
        if options.phy_type == "narrowband":
            symbol_rate = options.bitrate / mod_class(**args).bits_per_symbol()
        elif options.phy_type == "ofdm":
            symbol_rate = float(options.bandwidth)/options.samples_per_symbol  # spoof symbol rate to get desired bandwidth
        else:
            assert False, options.phy_type + " is not a valid phy_type input"
        
        self.fs = options.samples_per_symbol*symbol_rate
        
        # These fields ultimately get passed down to packet_utils for logging with each packet
        # tx/rx event
#        options.my_rfcenterfreq = options.tx_freq
        options.my_bandwidth    = self.fs
        
        print "fs = %s" % self.fs
        
        # if using the rx tap, declare and connect a udp sink to forward all received samples    
        if options.use_rx_tap == True:
            print "starting rx tap at address %s and port %s" %(options.rx_tap_addr, options.rx_tap_port )
            self.udpSink = gr.udp_sink(gr.sizeof_gr_complex*1, options.rx_tap_addr, options.rx_tap_port, 1472, True)
            self.udpSink2 = gr.udp_sink(gr.sizeof_gr_complex*1, options.rx_tap_addr, options.rx_tap_port+1, 1472, True)
        else:
            print "rx tap disabled"   
        
        self.phy_type = options.phy_type
        
        if options.phy_type == "narrowband":
            self.txpath = transmit_path_narrowband(mod_class, options)
            self.rxpath = receive_path_narrowband(demod_class, rx_callback, options)
        

        elif options.phy_type == "ofdm":
            self.txpath = transmit_path_ofdm(options)
            self.rxpath = receive_path_ofdm(rx_callback, options)
        else:
            # TODO: how do we handle this case? Throw an error? 
            pass
        
        self.tx_sample_counter = sample_counter()
        self.rx_sample_counter = sample_counter()
        
        

        
        self.get_usrp_params(options)
    
        #setting up USRP RX
        self.source = uhd_receiver(options.args, symbol_rate,
                                       options.samples_per_symbol,
                                       options.rx_freq, options.rx_gain,
                                       options.spec, "RX2",
                                       options.verbose)
        #this tells it to use the external clock reference
        self.source.u.set_clock_source("external", 0)
            
        #setting up USRP TX
        self.sink = uhd_transmitter(options.args, symbol_rate,
                                        options.samples_per_symbol,
                                        options.tx_freq, options.tx_gain,
                                        options.spec, options.antenna,
                                        options.verbose)
    
        #this tells it to use the external clock reference
        self.sink.u.set_clock_source("external", 0)
        options.samples_per_symbol = self.source._sps
    
        self.connect(self.txpath, self.sink)
        self.connect(self.txpath, self.tx_sample_counter)
        
        if options.use_rx_tap == True:
            # connect udp sinks
            self.connect(self.source, self.udpSink)
            self.connect(self.txpath, self.udpSink2)    
            
       
        # this is only connected if options.use_tx_squelch is true 
        self.amp = gr.multiply_const_vcc((1.0,))

        
        # connect rx path with or without tx squelch support
        if options.use_tx_squelch == True:
            self.connect(self.source, self.amp, self.rxpath)
            self.connect(self.amp, self.rx_sample_counter)
        else:      
            self.connect(self.source, self.rxpath)
            self.connect(self.source, self.rx_sample_counter)

        self.traffic_adapter = csma_msg_queue_adapter(options.app_in_q_size,
                                                      options.node_source_address)

        if options.traffic_generation == "infinite": 
            self.traffic = Infinite_Backlog_PDU_Streamer( options, 
                                                 self.traffic_adapter.queue_size )
            self.msg_connect(self.traffic, "out_pkt_port", self.traffic_adapter,'in_port')
        
        elif options.traffic_generation == "tunnel":
            self.traffic = Tunnel_Handler_PDU_Streamer(options)
            self.msg_connect(self.traffic, "out_pkt_port", self.traffic_adapter,'in_port')
            self.msg_connect(self.traffic_adapter, "out_port", self.traffic,'in_pkt_port')
        else:
            self.traffic = None


#    max_pkt_size = tb.txpath.max_pkt_size()
#    
#    if options.traffic_generation == "infinite":
#    
#        # spawn a thread to fill the tx queue with an infinite backlog of packets
#        traffic_generator = Queue_Filler(tb.tx_pkt_queue,source_addr, 
#                                sink_addr_list, max_pkt_size, .001 )
#    elif options.traffic_generation == "tunnel":
#        
#        # start up the tunnel interface to the tx queue
#        traffic_generator = Tunnel_Handler(tb.tx_pkt_queue, source_addr,sink_addr_list,
#                                           max_pkt_size, options)
#        mac.set_network_interface(traffic_generator)
#    
#    elif options.traffic_generation == "none":
#        # declare a dummy object that has all the same methods defined as "real" traffic models
#        traffic_generator = Passive_Traffic()


               
        self.tx_pkt_queue = self.traffic_adapter.pkt_queue
        self.packer = Payload_Packet()
        
    
        self.options = options
        self.keep_going = True
    def set_rx_chain(self, on):
        """
        Sets the whether to turn of RX chain or not
        """
        self.amp.set_k(on)

    def send_pkt(self, payload='', eof=False):
        print "calling send_pkt for packet of size %d bytes" % len(payload)
        
        
        self.set_rx_chain((0,))
        return self.txpath.send_pkt(payload, eof)
    


    def send_packet(self, from_id, to_id, pktno, pad_bytes, pkt_code_str, phy_code, mac_code, 
                more_data, data):
        #print "sending payload %s" % data 
        
        #self.mute_rx_path(True)
        
        payload = self.packer.pack_payload(from_id, to_id, pktno, pad_bytes, pkt_code_str, 
                                           phy_code, mac_code, more_data, data)
        
        
#        if (pkt_type == "CTS") | (pkt_type == "ACK"):
#        for m in range(5):
#            self.send_pkt(payload)
    
        # add padding (should work for both OFDM and narrowband. Doing it this way for 
        # now, but this should really be done by the PHY since this could be PHY specific
        # behavior
        payload = self.packer.pad_payload(payload)
        
        
#        if self.phy_type == "ofdm":
#            padding = len(payload) % 4
#            payload = payload + '0'*padding  
        
        if (pkt_code_str == "ACK"):
            for m in range(4):
                self.send_pkt(payload)

        self.send_pkt(payload)
        time.sleep(0.010)
        self.set_rx_chain((1.0,))
        return #self.mute_rx_path(False)
        
    
    def channel_free(self):
        """
        Return True if the receive path thinks the channel is available
        """
        return not self.rxpath.carrier_sensed()
        #return random.randint(0,1)

    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.
        """
        self.sink.set_freq(target_freq)
        self.source.set_freq(target_freq)
        
    #def mute_rx_path(self, mute_enable):
        #if mute_enable ==True:
            #self.amp.set_k((0,))
        #else:
            #self.amp.set_k((1,))
            
    def get_usrp_params(self,options):
    
        #uhd_find_devices is a binary that is in installed in the path,
        #reports the details about the usrp connected including 
        #serial number and ip address
        (status, usrp_str)= commands.getstatusoutput("uhd_find_devices --args=" + options.args )
        
        # split result into lines
        usrp_lines = usrp_str.split('\n')
        
        # make regex that matches with whitespace, followed by 'addr:' followed by 
        # whitespace, the string containing the addr, and the end of the line
        addr_regex = re.compile(r"^\s*(addr):\s*(.*)$")
        
        # make regex that matches with whitespace, followed by 'serial:' followed by 
        # whitespace, the string containing the serial number, and the end of the line
        serial_regex = re.compile(r"^\s*(serial):\s*(.*)$")
        
        addr_match = None
        serial_match = None
        
        # search the lines returned by uhd_find_devices using regular expressions
        for line in usrp_lines:
            addr_matches = addr_regex.search(line)
            serial_matches = serial_regex.search(line)
            
            if addr_matches:
                addr_match = addr_matches.groups()
            if serial_matches:
                serial_match = serial_matches.groups()
        
        if addr_match:
            usrp_ip = addr_match[1]
        else:
            usrp_ip = 'unknown'
            
        if serial_match:
            usrp_serial = serial_match[1]
        else:
            usrp_serial = 'unknown'          
        
        self.usrp_ip = usrp_ip
        self.usrp_serial = usrp_serial

def initial_config(logger):
    # Step 1: Get name of config file. If config file exists, set command line defaults from 
    #         config file. ArgParser can do this, optParser can't. This is why we're using both
    # Step 2: Parse remaining args with optParser for compatibility with node-options
    
    # note that the config file option names for node_options objects must exactly match the 
    # destination name of the corresponding OptionParser name  
    
    node_defaults = dict()

    arg_parser = ArgumentParser(add_help=False)
    arg_parser.add_argument("-c", "--config-file", dest="config_file", help="set config-file name")
    
    arg_parser.add_argument("--debuglog", dest="debuglog", default="debug.txt", help="file to save debug output to, [default=%default]")
    
    (known, args)=arg_parser.parse_known_args()
    
    # define a basic formatter for use with xml files
    formatter_debug = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(lineno)s - { "%(message)s" }')
    
    # create file handler for writing all debug messages
    fh_debug = logging.FileHandler(known.debuglog, mode='w')
    
    fh_debug.setFormatter(formatter_debug)
    logger.addHandler(fh_debug)
    
    # declare config parser
    conf_parser = SafeConfigParser(allow_no_value=True)
    
    # if given a config file, try to parse it, otherwise, skip that step
    if known.config_file is not None:
        # load config file
        file_list = conf_parser.read(known.config_file)
        
        if len(file_list) == 0:
            print "File '%s' not found" % known.config_file
            sys.exit(1)
        
        sections = conf_parser.sections()    
        # config file read successfully: Update command line defaults as needed
        for section in sections:
            # get list of all items in each section 
            section_entries = conf_parser.options(section)
            
            # update defaults for any matching variable names
            # iterate through each entry in each section
            for key in section_entries:
                
                logger.debug('Initializing %s option: %s from config file', section, key)
                # update defaults from the value in the config file
                node_defaults[key] = conf_parser.get(section, key)
                
                # handle special case of converting string representation of bools to bools
                if (node_defaults[key] == "True") | (node_defaults[key] == "False"):
                    node_defaults[key] = (node_defaults[key] == "True")

    # store values from arg parser into defaults of config parser, 
    # so everything is on the same page
    known_dict = vars(known)
    for key in known_dict:
        node_defaults[key] = known_dict[key]  

    mods = modulation_utils.type_1_mods()
    demods = modulation_utils.type_1_demods()
    ofdmmods = {"8psk": mods['bpsk'], "qam8": mods['bpsk'], "qam16": mods['bpsk'], "qam64": mods['bpsk'], "qam256": mods['bpsk']}
    mods.update(ofdmmods)
    demods.update(ofdmmods)

    # declare command line argument parser groups
    opt_parser = OptionParser (option_class=eng_option, conflict_handler="resolve")
    expert_grp = opt_parser.add_option_group("Expert")
        
    # note this option is actually handled by the argparse module. This is only included 
    # so the config file option shows up in the help file
    opt_parser.add_option("-c", "--config-file", dest="config_file", help="set config-file name")    
    
    # add debug options    
    expert_grp.add_option("--use-rx-tap", dest="use_rx_tap", 
                          help="if set, forward all received samples out through a udp sink for debug",
                          action="store_true", default=False)
        
    expert_grp.add_option("--rx-tap-addr", dest="rx_tap_addr", 
                          help="if using the rx-tap, forward all rx samples to this address [default=%default]",
                          default="127.0.0.1")
    
    expert_grp.add_option("--rx-tap-port", dest="rx_tap_port", 
                          help="if using the rx-tap, forward all rx samples to this port [default=%default]",
                          type="int", default=9088) 
     
    # TODO: clean up this option. Store available phy types somehow
    opt_parser.add_option("--phy-type", type="choice", choices=("narrowband","ofdm"),
                          help="Select phy type from: %s [default=%%default}" % (", ".join(("narrowband","ofdm"))))
    
    expert_grp.add_option("--use-tx-squelch", dest="use_tx_squelch", 
                          help="if set, zero out samples from receive path while transmitting",
                          action="store_true", default=False)
    
    opt_parser.add_option("-m", "--modulation", type="choice", choices=mods.keys(),
                      help="Select modulation from: %s [default=%%default]"
                            % (', '.join(mods.keys()),))
    opt_parser.add_option("-v","--verbose", action="store_true")

    opt_parser.add_option("","--pcktlog",default=-1, help="file to save packet log to")
    
    opt_parser.add_option("--nodelog", default="node_state.xml", help="file to save the inital node state to, [default=%default]")
        
    # note this option is actually handled by the argparse module. This is only included 
    # so the config file option shows up in the help file
    opt_parser.add_option("--debuglog", default="debug.txt", help="file to save debug output to, [default=%default]")
    
    # TODO: clean up this option. Store available traffic generation schemes somehow
    opt_parser.add_option("--traffic-generation", type="choice", choices=("infinite","tunnel", "none"),
                          help="Select traffic generation method: %s [default=%%default]" % (", ".join(("infinite","tunnel", "none"))))

#    expert_grp.add_option("--tx-queue-size", type="int", default = 20, 
#                          help="The maxmimum size of the transmit queue [default=%default]")
#    
    opt_parser.add_option("--start-time", type="float", default=float(0), 
                          help=("Start time of the test, in seconds since 1970. " + 
                                 "Starts immediately if start time is in the past. " +
                                 "[default=%default]  " + 
                                 "Hint: Use date +%s to get the current epoch time."))
    
    opt_parser.add_option("--run-time", type="float", default=float('inf'), 
                          help="Run time of the test, in seconds. [default=%default]")
                          
    opt_parser.add_option("--bandwidth", type="float", default=1e6, help="Variable for setting the bandwidth that the OFDM FFT spans over")

    # add other options to parser
    transmit_path_narrowband.add_options(opt_parser, expert_grp)
    receive_path_narrowband.add_options(opt_parser, expert_grp)
    transmit_path_ofdm.add_options(opt_parser, expert_grp)
    receive_path_ofdm.add_options(opt_parser, expert_grp)
    uhd_receiver.add_options(opt_parser)
    uhd_transmitter.add_options(opt_parser)
    Infinite_Backlog_PDU_Streamer.add_options(opt_parser, expert_grp)
    Tunnel_Handler_PDU_Streamer.add_options(opt_parser, expert_grp)

    csma.add_options(opt_parser)
    
    # for now, add csma options directly. When there are more types available, follow
    # style of mod/demod class and add using the mac_types registry in sm.py
    

    
    # TODO: add csma options, and continue converting mac_sm to use a common top
    # level node

    for mod in mods.values():
        mod.add_options(expert_grp)

    for demod in demods.values():
        demod.add_options(expert_grp)
    
    
    opt_parser.add_option("--node-sink-address-list", type="string", help="set node sink address list")
        

    # store updated default values to opt_parser
    
    # get list of all option defaults in the current option list
    opt_list = opt_parser.defaults
    
    # update defaults for node-options modules
    # iterate through each entry in node_defaults
    for key in node_defaults:
        logger.debug('Searching opt_list for option: %s', key)
        # if there's a match to an entry in opt_list
        if key in opt_list:
            # update default options from the value in gr_defaults
            logger.debug('Updating option default: %s from node_defaults', key)
            opt_parser.set_default(key, node_defaults[key])
        else:
            logger.warning('Option %s from node_defaults not present in opt_parser',key)
    
    # update defaults for mac-options entries
        
    
    # parse rest of command line args
    (options, args) = opt_parser.parse_args (args)
    if len(args) != 0:
        opt_parser.print_help(sys.stderr)
        sys.exit(1)

    # update config parser object with parsing result
    opt_dict = vars(options)
    
    for section in conf_parser.sections():
        for key in opt_dict:
            if conf_parser.has_option(section, key):
                conf_parser.set(section,key, str(opt_dict[key]))
            
        # cannot proceed without a config file, so exit
    if known.config_file is None:
        print "No config file provided, exiting"
        sys.exit(1)

    return (conf_parser, options)
   
def packet_checker(pkt):
    return True


# /////////////////////////////////////////////////////////////////////////////
#                    PHY <-> MAC State Machine Interface
# /////////////////////////////////////////////////////////////////////////////
class mac_harness:

    def __init__(self, mac_options, packet_options, options, logger, verbose=False):
        '''
        Constructor
        '''      
        self.verbose = verbose
        self.tb = None             # top block (access to PHY)
        
        # create logger
        self.logger = logger 
        
        
        # define timer initial values
        self.backoff_min_time = mac_options.getfloat('mac-options', 'backoff_min_time')
        self.backoff_max_time = mac_options.getfloat('mac-options', 'backoff_max_time')
        self.backoff_time = mac_options.getfloat('mac-options', 'backoff_time')
        self.tx_session_time = mac_options.getfloat('mac-options', 'tx_session_time')
        self.rx_session_time = mac_options.getfloat('mac-options', 'rx_session_time')
        self.cts_time = mac_options.getfloat('mac-options', 'cts_time')
        self.ack_time = mac_options.getfloat('mac-options', 'ack_time')
        
        # define timer status variables
        self.backoff_timer_expired = False
        self.tx_session_timer_expired = False
        self.rx_session_timer_expired = False
        self.cts_timer_expired = False
        self.ack_timer_expired = False
        
        # define timer objects
        self.backoff_timer = Timer(self.backoff_time, self.backoff_timer_callback)
        self.tx_session_timer = Timer(self.tx_session_time, self.tx_session_timer_callback)
        self.rx_session_timer = Timer(self.rx_session_time, self.rx_session_timer_callback)
        self.cts_timer = Timer(self.cts_time, self.cts_timer_callback)
        self.ack_timer = Timer(self.ack_time, self.ack_timer_callback)
        
        self.timer_lock = Semaphore()
        
        
        # define event variable to control state machine iteration rate
        self.run_event = Event()
        
        # define rx packet queue and set maximum size
        self.rx_pkt_queue = deque(maxlen=mac_options.getint('mac-options', 'rx_queue_size') )       
        
        
        # store packet parser callback
        self.packet_parser = packet_options['packet_parser']
        
        # store packet checker callback
        self.packet_checker = packet_options['packet_checker']
        
        # store node address
        self.address = int(mac_options.getfloat('mac-options', 'node_source_address') )
        
        # initialize rts packet counter
        self.rts_num = 0;
        self.rts_num_max = 65535
        
        # store network interface
        self.network_interface = None

        # declare the state machine
        self.mac_sm = csma(options.mac)
        
        self.packet_count = 0.0
        self.packet_avg = 0

        self.run_time = options.run_time
        
        # declare the number of state machine iterations to run before checking in on the
        # transmit and receive paths
        self.num_path_stall_iterations = 100
    
    def set_top_block(self, tb):
        self.tb = tb
        
        # store reference to tx packet queue
        self.tx_pkt_queue = self.tb.tx_pkt_queue
        
    def set_network_interface(self, network_interface):
        '''
        network_interface variable must have a write_to_network(payload) method
        '''
        self.network_interface = network_interface

    def backoff_timer_callback(self):
        self.timer_lock.acquire()
        # set timer expired flag
        self.backoff_timer_expired = True
        self.logger.debug("backoff_timer_expired")
        # notify the state machine it should run again
        self.run_event.set()
        self.timer_lock.release()
    
    def tx_session_timer_callback(self):
        self.timer_lock.acquire()
        # set timer expired flag
        self.tx_session_timer_expired = True
        self.logger.debug("tx_session_timer_expired")
        # notify the state machine it should run again
        self.run_event.set()
        self.timer_lock.release()
    
    def rx_session_timer_callback(self):
        self.timer_lock.acquire()
        # set timer expired flag
        self.rx_session_timer_expired = True
        self.logger.debug("rx_session_timer_expired")
        # notify the state machine it should run again
        self.run_event.set()  
        self.timer_lock.release() 
        
    def cts_timer_callback(self):
        self.timer_lock.acquire()
        # set timer expired flag
        self.cts_timer_expired = True
        self.logger.debug("cts_timer_expired")
        # notify the state machine it should run again
        self.run_event.set()  
        self.timer_lock.release()    
    
    def ack_timer_callback(self):
        self.timer_lock.acquire()
        # set timer expired flag
        self.ack_timer_expired = True
        self.logger.debug("ack_timer_expired")
        # notify the state machine it should run again
        self.run_event.set()  
        self.timer_lock.release()      

    def phy_rx_callback(self, ok, packet_bytes):
        """
        Invoked by thread associated with PHY to pass received packet up.
    
        This is where packets get put into a packet processing queue

        @param ok: bool indicating whether payload CRC was OK
        @param payload: contents of the packet (string)
        """
        
        # TODO: This currently does a packet CRC, I don't know how to turn this off
        if ok:
#            self.logger.info("phy_rx_callback")
            if len(self.rx_pkt_queue) < self.rx_pkt_queue.maxlen:
                outs = self.packet_parser(packet_bytes)
                crc_result = True
                pkt = csma_pkt_converter(self.address, crc_result,*outs)
                self.logger.debug("received packet")
                self.rx_pkt_queue.append(pkt)
                self.run_event.set()
            else:
                # drop a log statement that queue was full
                self.logger.debug("Queue-Event:Queue Full, dropping packet")
        else:
            self.logger.info("crc fail")
    
    def set_success_counters( self, use_adaptive_coding, adaptive_coding_memory_length, success_arq_counter, adaptive_coding_upper_thresh, adaptive_coding_lower_thresh, adaptive_coding_block_lengths, logger ):
        # Success_arq_counter is a dictionary (indexed by the id of each
        # sink address as a string) that will keep count of our successes
        # and failures.
        self.use_adaptive_coding = use_adaptive_coding
        self.adaptive_coding_memory_length = adaptive_coding_memory_length
        self.success_arq_counter = dict(success_arq_counter)
        self.adaptive_coding_upper_thresh = adaptive_coding_upper_thresh
        self.adaptive_coding_lower_thresh = adaptive_coding_lower_thresh
        self.adaptive_coding_block_lengths = adaptive_coding_block_lengths
        self.success_logger = logger   # Success logger will log the adaptation results to file.
        assert adaptive_coding_upper_thresh > adaptive_coding_lower_thresh, \
            "The adaptive_coding_lower_thresh must be less than the adaptive_coding_upper_thresh. Check test parameter input."
        
    def process_arq_counters( self ):
        # Process the success_arq_counter's to see if we need to adapt our coding rates.
        for node in self.success_arq_counter:
            counter      = self.success_arq_counter[node]
            if len(counter) > 0:
                success_rate = float(sum(counter))/len(counter)
            else:
                success_rate = float('nan')
            
            # Act upon the information
            if success_rate > self.adaptive_coding_upper_thresh and len(counter) >= self.adaptive_coding_memory_length:
                current_block_length = self.tb.txpath.packet_tx.get_coding_block_size(node)
                ind = self.adaptive_coding_block_lengths.index(current_block_length)
                if ind > 0:
                    new_block_length = self.adaptive_coding_block_lengths[ind-1]
                else:
                    new_block_length = current_block_length
                print 'Decreasing block length from', current_block_length, 'to', new_block_length
                self.tb.txpath.packet_tx.set_coding_block_size( new_block_length, node )
                self.success_arq_counter[node] = []
            elif success_rate < self.adaptive_coding_lower_thresh and len(counter) >= self.adaptive_coding_memory_length:
                current_block_length = self.tb.txpath.packet_tx.get_coding_block_size(node)
                ind = self.adaptive_coding_block_lengths.index(current_block_length)
                if ind+1 < len(self.adaptive_coding_block_lengths):
                    new_block_length = self.adaptive_coding_block_lengths[ind+1]
                else:
                    new_block_length = current_block_length
                print 'Increasing block length from', current_block_length, 'to', new_block_length
                self.tb.txpath.packet_tx.set_coding_block_size( new_block_length, node )
                self.success_arq_counter[node] = []
        
            # Record the results to file
            if self.success_arq_counter_updates[node]:
                # The metric has changed. Record the results to the MAC file.
                section_indent = 0
                self.success_logger.info("%s<FEC_rate_adaptation>", section_indent*'\t')
                section_indent += 1
                coding_rate_event_time = time.time()
                params = {  "timestamp":coding_rate_event_time,
                            "affected_receiving_node":node,
                            "code_block_size":self.tb.txpath.packet_tx.get_coding_block_size(node),
                            "success_rate_metric":success_rate}
                self.success_logger.info(dict_to_xml(params, section_indent))
                section_indent -= 1
                self.success_logger.info("%s</FEC_rate_adaptation>", section_indent*'\t')
        
    def main_loop(self):
        """
        Main loop for MAC.
        """
        start_time = time.time()
        tic = time.time()        

        # initialize backoff to min time
        self.backoff_time = self.backoff_min_time
        
        self.logger.debug("starting main loop")
        # start the backoff timer
        self.backoff_timer = Timer(self.backoff_time, self.backoff_timer_callback)
        self.backoff_timer.start()
        
        # initialize session done variable
        session_done = []
        
        # start the state machine
        self.mac_sm.start()
        
        channel_sensor = self.tb
        
        # initialize path stall checking variables
        loop_counter = 0
        last_rx_count = self.tb.rx_sample_counter.get_sample_count()
        last_tx_count = self.tb.tx_sample_counter.get_sample_count()
        
        # this is the state machine
        while self.tb.keep_going:        
        
            new_in = dict()
        
            # wait until there's a new event to handle
            self.logger.debug("waiting for next event")

            
            if len(self.rx_pkt_queue) > 0:
                self.run_event.set()           
            if not self.backoff_timer_expired:
                self.run_event.wait()
            
            if (loop_counter >= self.num_path_stall_iterations):
                loop_counter = 0
                current_rx_count = self.tb.rx_sample_counter.get_sample_count()
                current_tx_count = self.tb.tx_sample_counter.get_sample_count()
                
                if current_rx_count - last_rx_count == 0:
                    msg = "RX stalled: no samples processed in last %s state machine iterations" % self.num_path_stall_iterations
                    self.logger.warning(msg)
                    
                if current_tx_count - last_tx_count == 0:
                    msg = "TX stalled: no samples processed in last %s state machine iterations" % self.num_path_stall_iterations
                    self.logger.warning(msg)
                
            else:
                loop_counter +=1
            current_time = time.time()

            # if time to quit, break out of loop

            
            if current_time - start_time > self.run_time:
                self.tb.keep_going = False
                self.logger.info("Run time has expired, shutting down")
                break
            

            #self.logger.info("rx_queue len is %s",len(self.rx_pkt_queue))

            self.timer_lock.acquire()
            # get the current state machine inputs
            
            rx_pkt_available = False
            
            # remove any packets that I've received from myself from the front of the queue
            while len(self.rx_pkt_queue) > 0 and self.rx_pkt_queue[0].from_id == self.address:
                temp_rx_pkt = self.rx_pkt_queue.popleft()
                self.logger.info("received packet type %s num %s len %i from %s", 
                                 temp_rx_pkt.type, temp_rx_pkt.pktno, 
                                 len(temp_rx_pkt.data), temp_rx_pkt.from_id)
                
            # if there are any other packets in the rx queue
            if (len(self.rx_pkt_queue) > 0):
                
                # pop the current rx packet
                #new_in["rx_pkt"] = self.rx_pkt_queue.popleft()
                new_in["rx_pkt"] = self.rx_pkt_queue[0]
                rx_pkt_available = True
                self.logger.info("received packet type %s num %s len %i from %s", new_in["rx_pkt"].type, new_in["rx_pkt"].pktno, len(new_in["rx_pkt"].data), new_in["rx_pkt"].from_id)
                
#                if (rx_pkt.type == "ack_to_me") | (rx_pkt.type == "data_to_me"):
                     
                
                # TODO: add a real CRC check to packets
                # for now assume all payload crc's check out ok
                new_in["rx_pkt"].set_crc_result(True)
                
                if (new_in["rx_pkt"].type == "rts_to_me"):
                    # if the current rx packet was an rts addressed to me, set the rx_request
                    # flag high
                    new_in["rx_request"] = True
                    
            else:
                # initialize a dummy placeholder packet
                new_in["rx_pkt"] = csma_pkt_converter(self.address)
            
            # populate the current data packet
            if (len(self.tx_pkt_queue) > 0):
                new_in["data_pkt"] = self.tx_pkt_queue[0]
            else:
                
                new_in["data_pkt"] = csma_pkt_converter(self.address)
                
            # populate the next data packet (needed for MACs that support streaming)
            if (len(self.tx_pkt_queue) > 1):
                new_in["next_data_pkt"] = self.tx_pkt_queue[1]
            else:
                new_in["next_data_pkt"] = csma_pkt_converter(self.address) 
                
            # do dumb way of setting expired timers: could probably have the timer callbacks
            # do this directly, but this should be good enough for now
            
            new_in["expired_timers"] = []
            
            if self.ack_timer_expired:
                new_in["expired_timers"].append("ack")
            
            if self.backoff_timer_expired:
                new_in["expired_timers"].append("backoff")

            if self.cts_timer_expired:
                new_in["expired_timers"].append("cts")
              
            if self.rx_session_timer_expired:
                new_in["expired_timers"].append("rx_session")  

            if self.tx_session_timer_expired:
                new_in["expired_timers"].append("tx_session")  
            
            if len(new_in["expired_timers"]) > 0:
                self.logger.debug("expired timers: %s", new_in["expired_timers"])
            
            new_in["channel_free"] = channel_sensor.channel_free()
            new_in["session_done"] = session_done
            
            # Adaptive Coding Variables
            new_in["use_adaptive_coding"] = self.use_adaptive_coding
            new_in["success_arq_counter_size"] = self.adaptive_coding_memory_length
            new_in["success_arq_counter"] = dict(self.success_arq_counter)
            
            # collect inputs
            inp = (new_in )
            
            self.run_event.clear()
            self.timer_lock.release()
            
            # iterate state machine  
            self.logger.debug("running state machine")
            outp = self.mac_sm.step( (inp, False) )
            
            new_state = self.mac_sm.state
            
            self.logger.debug("new state: manager: %s tx: %s rx: %s", 
                              new_state[0], new_state[1][0], new_state[1][1])
            
            # expand outputs
            (path_outs) = outp
            (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
             backoff_control, new_data_received, success_arq_counter, pop_rx_pkt) = path_outs
            
            # Process Adaptive Coding Results
            # We need to extract the csma_arq_success and save it to self
            # for the next iteration of the loop.
            self.success_arq_counter_updates = dict()
            for other_node in success_arq_counter:
                self.success_arq_counter_updates[other_node] = not(success_arq_counter == self.success_arq_counter)
            self.success_arq_counter = dict(success_arq_counter)
            # Next we process the results and set the rates if they are above 
            # or below the described thresholds.
            if self.use_adaptive_coding:
                self.process_arq_counters()
            else:
                for node in self.success_arq_counter:
                    self.success_arq_counter[node] = []
             
            # handle outputs
            
            # store packet number for successfully received data packets
            if new_data_received:
                self.logger.info("new data packet %s received successfully", new_in["rx_pkt"].pktno)
                self.packet_count +=1

                if self.network_interface is not None:
                    self.tb.traffic_adapter.send_pkt(new_in["rx_pkt"].data)

                # HACK: Cancel backoff timer and set backoff to min
                clearing_timers.append('backoff')
                starting_timers.append('backoff')
                self.backoff_time = self.backoff_min_time
    
                if( self.packet_count % 10) == 0:
                    now = time.time()
                    delta_t = now - tic
                    
                    packets_per_sec = float(self.packet_count) / float(delta_t)
                    alpha = .25
                    if self.packet_avg > 0:
                        self.packet_avg = self.packet_avg*(1-alpha) + packets_per_sec*alpha
                    else:
                        self.packet_avg = packets_per_sec
                    print "received %s packets per second" % packets_per_sec
                    print "average %s packets per second" % self.packet_avg
                    self.packet_count = 0
                    tic = now
                

            
            if len(clearing_timers) > 0:
                self.logger.debug("clearing timers: %s", clearing_timers)
            
            if len(starting_timers) > 0:
                self.logger.debug("starting timers: %s", starting_timers)
            
            # handle backoff timeout controls
            
            # if backoff timeout increase is requested
            #print 'Sample Count: ', self.tb.rxpath.check_sample_count() # uncomment to debug
            if backoff_control > 0:
                new_backoff_time = 2*self.backoff_time
               
                if new_backoff_time > self.backoff_max_time:
                    new_backoff_time = self.backoff_max_time
                 
                self.logger.info("increasing backoff to %s", new_backoff_time)     
                self.backoff_time = new_backoff_time
            
            # if backoff timeout decrease is requested    
            elif backoff_control < 0:
                self.backoff_time = self.backoff_min_time + 0.5*random.random()*self.backoff_min_time
                self.logger.info("decreasing backoff to %s", self.backoff_time)
                
            
            # send out any requested packets 
            for pkt in tx_pkts:
                more_data = 0
                data=''
                to_id = pkt["to_id"]
                pktno = pkt["pktno"]
                
                if (pkt["type"] == "rts"):
                    pkt_type = "RTS"
                    
                elif (pkt["type"] == "cts"):
                    pkt_type = "CTS"
                    sleep(0.01)

                elif (pkt["type"] == "data"):
                    if len(self.tx_pkt_queue) > 0:
                        pkt_type = "DATA"
                        data = self.tx_pkt_queue[0].data
                        more_data = self.tx_pkt_queue[0].more_data
                        sleep(.01)
                    else:
                        # state machine is starved for data. Send nothing
                        pkt_type = "NONE"
                              
                elif (pkt["type"] == "ack"):
                    pkt_type = "ACK"
                    sleep(.01)
                        
                self.logger.debug("pkt type is: %s",pkt_type)        
                
                # send out a packet if the packet request is valid
                if (pkt_type != "NONE"):
                    self.logger.info("sending %s num %s len %i to node %s", pkt_type, pktno, len(data), to_id)
                    
                    pad_bytes = 0
                    phy_code = 0
                    mac_code = 0
                    self.tb.send_packet( self.address, to_id, pktno, pad_bytes, pkt_type, phy_code, mac_code, more_data, data)
                    
            self.timer_lock.acquire()

            # only pop tx queue if not empty    
            if pop_tx_pkt:
                if len(self.tx_pkt_queue) > 0:
                    self.logger.info(" popping data packet %s from queue", self.tx_pkt_queue[0].pktno)
                    
                    if len(self.tx_pkt_queue) > 1:
                        self.logger.info("next data packet is %s", self.tx_pkt_queue[1].pktno)
                    else:
                        self.logger.info("tx queue is now empty")
                        
                    self.tx_pkt_queue.popleft()
                    
            

            if pop_rx_pkt and rx_pkt_available:
                if len(self.rx_pkt_queue) > 0:
                    self.logger.info("popping packet from rx queue")
                    self.rx_pkt_queue.popleft()

            
            # cancel timers as requested    
            for timer_name in clearing_timers:
                if (timer_name == "ack"):
                    self.ack_timer.cancel()
                    self.ack_timer_expired = False
                elif (timer_name == "backoff"):
                    self.backoff_timer.cancel()
                    self.backoff_timer_expired = False
                elif (timer_name == "cts"):
                    self.cts_timer.cancel()
                    self.cts_timer_expired = False
                elif (timer_name == "rx_session"):
                    self.rx_session_timer.cancel()
                    self.rx_session_timer_expired = False
                elif (timer_name == "tx_session"):
                    self.tx_session_timer.cancel()
                    self.tx_session_timer_expired = False
                    
                self.logger.debug("clearing %s timer", timer_name)
            
            # restart timers as requested    
            for timer_name in starting_timers:
                if (timer_name == "ack"):
                    self.ack_timer = Timer(self.ack_time, self.ack_timer_callback)
                    self.ack_timer.start()
                elif (timer_name == "backoff"):
                    self.backoff_timer = Timer(self.backoff_time + self.backoff_time*random.random(), self.backoff_timer_callback)
                    self.backoff_timer.start()
                elif (timer_name == "cts"):
                    self.cts_timer = Timer(self.cts_time, self.cts_timer_callback)
                    self.cts_timer.start()
                elif (timer_name == "rx_session"):
                    self.rx_session_timer = Timer(self.rx_session_time, self.rx_session_timer_callback)
                    self.rx_session_timer.start()
                elif (timer_name == "tx_session"):
                    self.tx_session_timer = Timer(self.tx_session_time, self.tx_session_timer_callback)
                    self.tx_session_timer.start()
                
                self.logger.debug("starting %s timer", timer_name)
            
            self.timer_lock.release()
                
            # copy session done out into session_done    
            session_done = list(session_done_out)

            
            # if a session completed, the state machine should iterate again 
            # immediately
            if len(session_done) > 0:
                
                self.logger.debug("running immediately since %s session is done", session_done)
                self.run_event.set()
       
        self.logger.debug("Mac main loop has shut down")
        
    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''
                
        section_indent = indent_level
        
        # top level mac section param values
        params = {"source_mac_address":self.address,
                  "type":self.mac_sm.type,
                  "run_time":self.run_time}
        
        logger.info(dict_to_xml(params, section_indent))
    
        # csma section start
        logger.info("%s<csma>", section_indent*'\t')
        section_indent += 1
        
        # csma section param values
        params = {"collision_avoidance":self.mac_sm.collision_avoidance,
                  "automatic_repeat_request":self.mac_sm.automatic_repeat_request,
                  "backoff_min_time":self.backoff_min_time,
                  "backoff_max_time":self.backoff_max_time,
                  "tx_session_time":self.tx_session_time,
                  "rx_session_time":self.rx_session_time,
                  "cts_time":self.cts_time,
                  "ack_time":self.ack_time,
                  "rx_queue_max_size":self.rx_pkt_queue.maxlen,}                                   
        logger.info(dict_to_xml(params, section_indent))
               
        # csma section end
        section_indent -= 1
        logger.info("%s</csma>", section_indent*'\t')
                              
# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():  
    # set up logging
    logging.config.fileConfig('logging.conf')
    
    print "MAC_LL Version:     " + mac_ll.__version__
    print "DIGITAL_LL Version: " + digital_ll.__version__

    # create logger
    logger = logging.getLogger('default')
    
    # merge command line options and config file into something consistent
    (conf_parser, options) = initial_config(logger)
    
    if options.pcktlog != -1:
        lincolnlog.LincolnLogLayout('debug', -1, options.pcktlog , -1, -1)
    else:
        lincolnlog.LincolnLogLayout('debug', -1, -1, -1, -1)    
    
    # wait for start time
    current_time = time.time()
    
    if options.start_time-current_time > 0:
        logger.info("Waiting %s seconds for start time of %s", options.start_time-current_time, 
                    options.start_time)
    else:
        logger.info("Current time is past start time. Starting immediately")
    
    while current_time < options.start_time:
        sleep(.1)
        current_time = time.time()
        
    logger.info("Started test at time %s",current_time)

    # define a basic formatter for use with xml files
    formatter_bare = logging.Formatter('%(message)s')
        
    # set up state logger
    state_log = logging.getLogger('node_state')
    
    # create file handler for writing out the node state, and then add it to the state logger
    fh_node_state = logging.FileHandler(options.nodelog, mode='w')
    
    fh_node_state.setFormatter(formatter_bare)
    state_log.addHandler(fh_node_state)
    
    mods = modulation_utils.type_1_mods()
    demods = modulation_utils.type_1_demods()

    # Attempt to enable realtime scheduling
    r = gr.enable_realtime_scheduling()
    if r == gr.RT_OK:
        realtime = True
    else:
        realtime = False
        print "Note: failed to enable realtime scheduling"

#    # pull MAC specific options from config file
#    mac_options = conf_parser.items('mac-options')


#    # define tx packet queue and set maximum size
#    tx_pkt_queue = deque(maxlen=conf_parser.getint('mac-options', 'tx_queue_size') )
        
    payload_parser_obj = Payload_Packet()
    payload_parser = payload_parser_obj.unpack_payload
    packet_options = dict()
#    packet_options['tx_pkt_queue'] = tx_pkt_queue 
    packet_options['packet_checker'] = packet_checker 
    packet_options['packet_parser'] = payload_parser
    
    source_addr = int(conf_parser.getfloat('mac-options', 'node_source_address'))
    # get list of valid sink addresses from config file
    sink_addr_list_str = conf_parser.get('mac-options', 'node_sink_address_list')
    
    # convert list from comma separated string to list of integers
    sink_addr_list = [int(x) for x in sink_addr_list_str.split(',')]
    options.node_sink_address_list = sink_addr_list
    
    # instantiate the MAC
    mac = mac_harness(conf_parser, packet_options, options, logger, verbose=True)

    # build the graph (PHY)
#    tb = my_top_block(mods[options.modulation],
#                      demods[options.modulation],
#                      mac.phy_rx_callback, tx_pkt_queue,
#                      options)

    tb = my_top_block(mods[options.modulation],
                      demods[options.modulation],
                      mac.phy_rx_callback,
                      options)

    mac.set_top_block(tb)    # give the MAC a handle for the PHY
    


    # Construct a success_arq_counter for each sink address.
    # This will be used to count success and failures.
    success_arq_counter = dict()
    for sink_addr in sink_addr_list:
        success_arq_counter[str(sink_addr)] = []
        
    # Get adaptive coding block lengths, convert it to a list, and sort it.
    exec 'adaptive_coding_block_lengths = ' + options.adaptive_coding_block_lengths
    adaptive_coding_block_lengths = list(adaptive_coding_block_lengths)
    adaptive_coding_block_lengths.sort()
    
    # Setup the default parameters for adaptive coding.
    mac.set_success_counters( options.adaptive_coding, options.adaptive_coding_memory_length, success_arq_counter,\
                 options.adaptive_coding_upper_thresh, options.adaptive_coding_lower_thresh, adaptive_coding_block_lengths, state_log )
    # Initialize the coding rates
    if options.adaptive_coding:
        tb.txpath.packet_tx.initialize_coding_block_size( adaptive_coding_block_lengths[0], sink_addr_list )

#    max_pkt_size = tb.txpath.max_pkt_size()
#    
#    if options.traffic_generation == "infinite":
#    
#        # spawn a thread to fill the tx queue with an infinite backlog of packets
#        traffic_generator = Queue_Filler(tb.tx_pkt_queue,source_addr, 
#                                sink_addr_list, max_pkt_size, .001 )
#    elif options.traffic_generation == "tunnel":
#        
#        # start up the tunnel interface to the tx queue
#        traffic_generator = Tunnel_Handler(tb.tx_pkt_queue, source_addr,sink_addr_list,
#                                           max_pkt_size, options)
#        mac.set_network_interface(traffic_generator)
#    
#    elif options.traffic_generation == "none":
#        # declare a dummy object that has all the same methods defined as "real" traffic models
#        traffic_generator = Passive_Traffic()
        

    if options.traffic_generation == "tunnel":
        
        # hook up mac to the tunnel network interface
        mac.set_network_interface(tb.traffic)
    
    
    try:
#        print "starting traffic generator"
#        traffic_generator.start()    # start adding packets to the transmit queue
        
       
        print "starting flowgraph"
        tb.start()    # Start executing the flow graph (runs in separate threads)
    
        if options.pcstrain_flag ==1:
            print "calibrating pcs sensor"
            tb.rxpath.calibrate_probe()

        # log current state
        print "Logging current state"
#        log_my_settings(options, mac, tb, traffic_generator, 0, state_log)
        log_my_settings(options, mac, tb, 0, state_log)

        print "starting state machine"
    
        mac.main_loop()  
        
#        shut_down( traffic_generator, mac, tb, logger ) 
        shut_down( mac, tb, logger ) 
        
        logger.debug("shut down complete")
    except KeyboardInterrupt:
#        shut_down( traffic_generator, mac, tb, logger )  
        shut_down(mac, tb, logger )  
        logger.debug("shut down complete")
        
#def shut_down( traffic_generator, mac, tb, logger ):
#
#    traffic_generator.shut_down()
#    logger.debug("traffic generator has shut down")
#    
#    mac.keep_going = False
#    tb.keep_going = False
#
#    logger.debug("telling top block to stop")
#    tb.stop()
#    
#    logger.debug("waiting for top block thread to complete")
#    tb.wait()
#    logger.debug("top block has shut down")

def shut_down( mac, tb, logger ):
    
    mac.keep_going = False
    tb.keep_going = False

    logger.debug("telling top block to stop")
    tb.stop()
    
    logger.debug("waiting for top block thread to complete")
    tb.wait()
    logger.debug("top block has shut down")          
                
def log_my_settings(options, mac, tb, indent_level, logger):
    '''
    Write out all initial parameter values to XML formatted file
    '''
    # get current timestamp
    epoch_time = time.time()
    
    section_indent = (indent_level)
    
    # node state section start
    logger.info("%s<node_state>", section_indent*'\t')
    section_indent += 1
     
    # get current repo branch and version
    (status, branch) = commands.getstatusoutput("git rev-parse --symbolic-full-name --abbrev-ref HEAD")
    (status, commit) = commands.getstatusoutput("git describe --always --dirty")
    node_version = branch + '-' + commit
    
    # get machine name    
    (status, hostname) =  commands.getstatusoutput("uname -n")
     
    # node state section param values
    params = {"timestamp":epoch_time,
              "use_debug_tap":options.use_rx_tap,
              "traffic_generation_type":options.traffic_generation,
              "tx_squelch_enabled":options.use_tx_squelch,
              "node_version":node_version,
              "mac_ll_version":mac_ll.__version__,
              "digital_ll_version":digital_ll.__version__,
              "hostname":hostname,
              "debug_log":options.debuglog,
              "pckt_log":options.pcktlog,
              "node_config":options.config_file}

    logger.info(dict_to_xml(params, section_indent))
    
    # traffic_generatione section start
    logger.info("%s<traffic_generation>", section_indent*'\t')
    section_indent += 1
     
    tb.traffic.log_my_settings(section_indent, logger)
        
    # traffic_generation section end
    section_indent -= 1
    logger.info("%s</traffic_generation>", section_indent*'\t')      
    
    if options.use_rx_tap == True:
    
        # debug tap section start
        logger.info("%s<debug_tap>", section_indent*'\t')
        section_indent += 1
        
        # debug tap section param values
        params = {"debug_tap_addr":options.rx_tap_addr,
                  "debug_tap_port":options.rx_tap_port}
        logger.info(dict_to_xml(params, section_indent))          
    
        # debug tap section end
        section_indent -= 1
        logger.info("%s</debug_tap>", section_indent*'\t')
   
    
        
    # radio section start
    logger.info("%s<radio>", section_indent*'\t')
    section_indent += 1 
    
                  
    
    # debug tap section param values
    params = {"usrp_serial":tb.usrp_serial,
              "usrp_ip":tb.usrp_ip}
    logger.info(dict_to_xml(params, section_indent)) 
    
    # call transmitter's logger
    tb.sink.log_my_settings(section_indent,logger)
    
    # call receiver's logger
    tb.source.log_my_settings(section_indent,logger)
   
    # radio section end
    section_indent -= 1
    logger.info("%s</radio>", section_indent*'\t') 
        
    # phy section start
    logger.info("%s<phy>", section_indent*'\t')
    section_indent += 1 
    
    # transmit section start
    logger.info("%s<transmit>", section_indent*'\t')
    section_indent += 1 
    
    # call transmit path's logger
    tb.txpath.log_my_settings(section_indent,logger)
    
    # transmit section end
    section_indent -= 1
    logger.info("%s</transmit>", section_indent*'\t')
    
    # receive section start
    logger.info("%s<receive>", section_indent*'\t')
    section_indent += 1 
    
    # call receive path's logger
    tb.rxpath.log_my_settings(section_indent,logger)
   
    # receive section end
    section_indent -= 1
    logger.info("%s</receive>", section_indent*'\t')
   
    # phy section end
    section_indent -= 1
    logger.info("%s</phy>", section_indent*'\t')
    
    # mac section start
    logger.info("%s<mac>", section_indent*'\t')
    section_indent += 1 
    
    # call mac's logger
    mac.log_my_settings(section_indent,logger)
   
    # mac section end
    section_indent -= 1
    logger.info("%s</mac>", section_indent*'\t')  
    
    # log the coding and adaptive parameters
    section_indent += 1
    logger.info("%s<coding>", section_indent*'\t')
    params = { "use_coding":options.coding,
               "block_length":options.block_length,
               "adaptive_coding":options.adaptive_coding,
               "adaptive_coding_memory_length":options.adaptive_coding_memory_length,
               "adaptive_coding_upper_thresh":options.adaptive_coding_upper_thresh,
               "adaptive_coding_lower_thresh":options.adaptive_coding_lower_thresh,
               "adaptive_coding_block_lengths":options.adaptive_coding_block_lengths,
             }
    section_indent += 1
    logger.info(dict_to_xml(params, section_indent))
    section_indent -= 1
    logger.info("%s</coding>", section_indent*'\t')
    section_indent -= 1
    
    # node state section end
    section_indent -= 1
    logger.info("%s</node_state>", section_indent*'\t')

if __name__ == '__main__':
        main()
