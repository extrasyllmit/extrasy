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
from collections import defaultdict
from collections import deque
from copy import deepcopy
import cPickle
import logging
import math
from math import floor
from math import pi
from operator import itemgetter
import Queue
import time

# third party library imports
from gnuradio import gr
from gruel import pmt

import numpy

# project specific imports
import digital_ll
from digital_ll import beacon_utils
from digital_ll import lincolnlog
from digital_ll import packet_utils2
from digital_ll import SimpleFrameSchedule
from digital_ll import SlotParamTuple
from digital_ll import time_spec_t
from digital_ll.beacon_utils import TDMA_HEADER_MAX_FIELD_VAL
from digital_ll.lincolnlog import dict_to_xml

from mac_ll import tdma_mobile_sm





#block port definitions - inputs
FROM_APP_PORT = pmt.from_python('from_app') # packets coming from the application layer
INCOMING_PKT_PORT = pmt.from_python('incoming_pkt') # packets arriving from the rf interface
SCHEDULE_IN_PORT = pmt.from_python('sched_in')

#block port definitions - outputs
OUTGOING_PKT_PORT = pmt.from_python('outgoing_pkt') # packets being sent out the rf interface
TO_APP_PORT = pmt.from_python('to_app') # packets being forwarded out to the application layer
COMMAND_OUT_PORT = pmt.from_python('command_out')

#Time state machine
LOOKING_FOR_TIME = 0 
HAVE_TIME = 0


# /////////////////////////////////////////////////////////////////////////////
#                   TDMA MAC
# /////////////////////////////////////////////////////////////////////////////

class tdma_controller(gr.sync_block):
    """
    TDMA controller implementation. This class is meant to be a framework
    for a TDMA state machine to use to interact with the outside world.
    
    This class will primarily take care of timing and message handling
    """
    def __init__(
        self, options, mac_sm, manage_slots, fs, mux_name, rx_channelizer_name, 
        fhss_flag=0, start_time=None, plot_lock=None
    ):
        """
        Inputs: complex stream from USRP, app_in, pkt in
        Outputs: pkt out, app_out
        """
        gr.sync_block.__init__(
            self,
            name = "tdma_controller",
            in_sig = [numpy.complex64],
            out_sig = None
        )
          
        # set up loggers
        self.ll_logging  = lincolnlog.LincolnLog(__name__)
        self.dev_logger = logging.getLogger('developer')
        
        self.dev_logger.debug("tdma controller init")
        
      
        self.plot_lock = plot_lock
        # TODO: get these from mac/phy?
        macCode = 1
        phyCode = 0
        
        # store off any inputs we'll need later
        self.fs = float(fs)
        self.mac_sm = mac_sm
        self.mux_name = mux_name
        self.rx_channelizer_name = rx_channelizer_name
        self.start_time = start_time
        
        self.monitor_timing = True
        if self.monitor_timing == True:
            self.state_time_deltas = 0
            self.wall_time_deltas = 0
            self.poll_interval = 5

        if fhss_flag:
            self.number_digital_channels = options.digital_freq_hop_num_channels
        else:
            self.number_digital_channels = 1

        # round pre_guard to nearest sample: probably ok if we do this at upsampled
        # sample rate, but doing this at the rate given in the fs param for now
        self.pre_guard = round(options.slot_pre_guard*self.fs)/self.fs
        
        if self.pre_guard != options.slot_pre_guard:
            self.dev_logger.warn("Rounding pre_guard from %.15f to %.15f", self.pre_guard,
                                 options.slot_pre_guard)

                
        # store off option parameters that will be needed later
        self.frame_file = options.frame_file
        self.max_app_in_q_size = options.mac_tx_packet_q_depth
        self.max_incoming_q_size = options.phy_rx_packet_q_depth
                
        # Queue to hold packets coming from application layer prior to processing
        self.app_in_q = deque([],self.max_app_in_q_size)
        # Queue to hold packets coming from rf interface prior to processing
        self.raw_incoming_q = Queue.Queue()
        # queue to hold incoming packets after initial processing
        self.incoming_q = deque([],self.max_incoming_q_size)
        # Queue for schedule updates from the beacon consumer
        self.in_sched_update_q = deque()


        # dictionary mapping between node ID and the queue holding packets addressed to
        # that ID. Using defaultdict so that deques for new toIDs are automatically
        # created as needed. In general, mobiles will only have one queue, since they
        # only communicate directly with the base, but bases will have one queue per 
        # associated mobile
        self.pkt_switch_queues = defaultdict(deque)
    
        
        if start_time is None:
            self.start_time = ceil(time.time())
        else:
            self.start_time = start_time
        
        
        # reference timestamp used with time_offset and fs to compute the current time 
        # based on the number of samples received
        self.ref_timestamp = time_spec_t(0)
        self.ref_time_offset = 0
        

        self.current_timestamp = time_spec_t(0)
        
        # used for adding a packet id field to packets
        self.packet_count = 0
        self.frame_count = 0
        
        self.found_time = False
        self.found_rate = False
        self.know_time = False
        
        self.time_cal_complete = False
        self.do_time_cal = False
        self.num_cal_beacons = 0
        self.beacon_channel = options.gpsbug_cal_channel

        # don't propagate any tags
        self.set_tag_propagation_policy(gr.gr_block.TPP_DONT)
      
        # register output message ports
        self.message_port_register_out(OUTGOING_PKT_PORT)
        self.message_port_register_out(TO_APP_PORT)
        self.message_port_register_out(COMMAND_OUT_PORT)
        
        # register input message ports
        self.message_port_register_in(FROM_APP_PORT)
#        self.message_port_register_in(INCOMING_PKT_PORT)
        self.message_port_register_in(SCHEDULE_IN_PORT)
        
        # register message handlers for input ports
        self.set_msg_handler(FROM_APP_PORT, self.handle_app_pkt)
#        self.set_msg_handler(INCOMING_PKT_PORT, self.handle_incoming_pkt)
        self.set_msg_handler(SCHEDULE_IN_PORT, self.handle_schedule_update)
        

        
        #state machine should only be started by top level node once calibration is complete
#        self.mac_sm.start()
        
        # define the link direction to assign to received packets
        if self.mac_sm.is_base():
            self.rx_pkt_dir = "up"
            
            # decide which packet stat tracking function to use
            self.manage_slots = manage_slots
            
        else:
            self.rx_pkt_dir = "down"
            
            
            
            
            
            # decide which packet stat tracking function to use
            self.manage_slots = manage_slots
        
        # list for the current set of schedules the state machine is operating on
        self.sched_seq = []
        self.frame_config = None
        self.current_sched = None
        self.last_frame_slots = None 
        # TODO: LOG THESE    

        
        self.mac_config = {
                           "app_in_q_size":self.max_app_in_q_size,
                           "base_id":options.base_station_mac_address,
                           "bits_per_symbol":1, # TODO: Always true for GMSK...will have to fix later
                           "fhss_flag":fhss_flag,
                           "fs":self.fs,
                           "lead_limit":options.frame_lead_limit,
                           "macCode":macCode,
                           "mux_command":self.mux_name + ".set_schedules",
                           "my_id":options.source_mac_address,
                           "number_digital_channels":options.digital_freq_hop_num_channels,
                           "beacon_channel":options.gpsbug_cal_channel,
                           "peer_ids":options.sink_mac_addresses,
                           "phyCode":phyCode,
                           "pre_guard":self.pre_guard,
                           "rx_channelizer_command":self.rx_channelizer_name + ".channelizer_command",
                           "rx_channelizer_return_to_beacon":self.rx_channelizer_name + ".return_to_beacon_channel",
                           "samples_per_symbol":options.modulation_samples_per_symbol,
                           "slot_manager":self.manage_slots,
                           }    
        
        self.dev_logger.debug("tdma controller init complete")
    
    @staticmethod    
    def add_options(normal, expert):
        """
        Adds tdma controller options to the Options Parser
        """
        normal.add_option("--mac-tx-packet-q-depth", default=50, type="int",
                          help=("Max size of the application layer packet queue " +
                                "[default=%default]"))
        normal.add_option("--phy-rx-packet-q-depth", default=50, type="int",
                          help=("Max size of the phy layer packet queue " +
                                "[default=%default]"))
        
        normal.add_option("--frame-file", type='string', default="frame.xml",
                          help=("Base station only option " 
                          + "to specify where to load the frame parameters from"))
        
        normal.add_option("--gpsbug-cal-channel", type='int', 
                          help=("Channel to find the beacon on during gpsbug time calibration"),
                          default=0)

    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''
        section_indent = indent_level
        
        # top level tdma controller params
        params = {
                  "app_in_q_size":self.max_app_in_q_size,
                  "incoming_q_size":self.max_incoming_q_size,
                  "mux_name":self.mux_name,
                  "rx_channelizer_name":self.rx_channelizer_name,
                  "first_frame_time":self.start_time,
                  "frame_file":self.frame_file,
                 }
        
        #logger.info(dict_to_xml(params, section_indent))
        logger.info(dict_to_xml(params, section_indent))
    
        # tdma state machine section start
        #logger.info("%s<tdma_mac>", section_indent*'\t')
        logger.info("%s<tdma_controller>", (section_indent*'\t'))
        section_indent += 1
        
        # mac section param values
        params = {
                  "node_source_address":self.mac_config["my_id"],
                  "base_id":self.mac_config["base_id"],
                  "node_sink_address_list":self.mac_config["peer_ids"],
                  "fs":self.mac_config["fs"],
                  "lead_limit":self.mac_config["lead_limit"],
                  "pre_guard":self.mac_config["pre_guard"],
                  "fhss_flag":self.mac_config["fhss_flag"],        
                  }                                 
        #logger.info(dict_to_xml(params, section_indent))
        logger.info(dict_to_xml(params, section_indent))
        
        
        self.manage_slots.log_my_settings(section_indent,logger)
        
               
        # csma section end
        section_indent -= 1
        #logger.info("%s</tdma_mac>", section_indent*'\t')
        logger.info("%s</tdma_controller>", (section_indent*'\t'))

    def set_bytes_to_samples_converter(self, bytes_to_samples):
        '''
        Store the function to use to calculate how many complex samples it will take to 
        transmit a given number of bytes
        '''
        self.mac_config["bytes_to_samples"] = bytes_to_samples
        
    def handle_app_pkt(self, pdu):
        '''
        Try to put another packet on to the app_in_q. If the queue is full, don't block,
        just drop the packet, catch the Full exception, and continue on
        
        This function is also responsible for tagging packets with the ID of this node.
        The fromID and toID are added by the MAC, but since this is where packets external
        to the network are first added, they will need an accurate sourceID. 
        '''

        #print "handle_app_pkt: queue length is %d" % len(self.app_in_q)
        # make sure the pdu is a pmt pair
        if pmt.pmt_is_pair(pdu):
            #print "pmt is a pair"
            # get the first and last elements of the pair
            meta = pmt.to_python(pmt.pmt_car(pdu))
            vect = pmt.to_python(pmt.pmt_cdr(pdu))
            
            # make sure there's some metadata associated with the packet, otherwise 
            # drop it
            if not (meta is None):
                #print "meta is not none"
                if len(self.app_in_q) < self.app_in_q.maxlen:
                    
                    # stamp each app packet with a source ID
                    meta["sourceID"]=self.mac_config["my_id"]
                    self.app_in_q.append((meta, vect))
                else:
                    # TODO: Include warning about dropping packet due to full queue
                    pass
        

    def incoming_packet_callback(self, ok, payload, timestamp, channel):
        # trying to address exception seen in long runs where a packet's metadata
        # dictionary is changing size while processing. Assuming this is a multithreaded 
        # issue so moving to this approach
        self.raw_incoming_q.put( (ok, payload, timestamp, channel))
    
    def process_raw_incoming_queue(self):
        
        while not self.raw_incoming_q.empty():
            
            (ok, payload, timestamp, channel) = self.raw_incoming_q.get()
            # if packet passed CRC
            if ok:
                meta, data = self.mac_sm.unpack_tdma_header(payload = payload)
                
                self.dev_logger.info("Packet %i metadata says channel %i and was received on channel %i",
                          meta["packetid"],meta["frequency"], channel)
                if meta is None:
                    meta = {}
            
                meta["crcpass"] = True
                meta["timestamp"] = (time_spec_t(timestamp))
                meta["messagelength"] = len(payload)
                
                # hack to work around frame number wrap around in packet headers
                if self.frame_count - meta["frameID"] > TDMA_HEADER_MAX_FIELD_VAL/2:
                    # compute how many times the frame count has overflowed the packet frame
                    # num field
                    num_wraps = floor(self.frame_count/TDMA_HEADER_MAX_FIELD_VAL)
                    
                    # update the packet metadata what its actual value likely was
                    meta["frameID"] = int(num_wraps*(TDMA_HEADER_MAX_FIELD_VAL) 
                                          + meta["frameID"])
                    
                    # make sure we didn't go one wrap too far
                    if meta["frameID"] > self.frame_count:
                        meta["frameID"] = meta["frameID"] - TDMA_HEADER_MAX_FIELD_VAL;
                        
                        
    #            self.dev_logger.debug("pktID: %d code: %d slot: %d",meta["packetid"],
    #                                  meta["pktCode"], meta["timeslotID"])
                
                if ("toID" in meta) and ("packetid" in meta) and ("pktCode" in meta):
                    if meta["toID"] != self.mac_config["my_id"]:
                        self.dev_logger.warning("received packet number %d, type %d, in slot %d, frame %d, addressed to %d at timestamp %s",
                                                meta["packetid"], meta["pktCode"], 
                                                meta["timeslotID"], meta["frameID"], 
                                                meta["toID"], meta["timestamp"])
                        
                    else:
    #                    self.dev_logger.debug("received packet number %d, type %d, in slot %d",
    #                                          meta["packetid"], meta["pktCode"],
    #                                          meta["timeslotID"])            
                        pass
                    
                if len(self.incoming_q) < self.incoming_q.maxlen:
                
                    self.incoming_q.append((meta, data))
                else:   
                    # if dropping the packet, also log it as a drop
                    meta["direction"] = "drop"
                    #if "frequency" in meta.keys():
                    #    meta["frequency"] = self.convert_channel_to_hz(meta["frequency"])
                    meta_copy = deepcopy(meta)
                    self.ll_logging.packet(meta_copy)
                    
                
            # crc failed        
            else:    
                meta = {"crcpass":False}
                meta["timestamp"] = (time_spec_t(timestamp))
                meta["messagelength"] = len(payload)
                data = None
                
                # add in packet so we can get a more accurate BER estimate 
                self.incoming_q.append((meta, data))
            # add other metadata not in the over the air packet    
            
            meta["linkdirection"] = self.rx_pkt_dir
            meta["direction"] = "receive"    
            
             
                    
            # always log that we received the packet
            #if "frequency" in meta.keys():
            #    meta["frequency"] = self.convert_channel_to_hz(meta["frequency"])
            meta_copy = deepcopy(meta)
            self.ll_logging.packet(meta_copy)

    def handle_schedule_update(self, sched_pmt):
        '''
        Add the new schedule to the schedule update queue
        '''
        pickled_sched = pmt.to_python(sched_pmt)
        
        # make sure there's something in the schedule, otherwise 
        # drop it
        if not (pickled_sched is None):
            
            self.dev_logger.debug("controller got schedule update")
            self.in_sched_update_q.append(cPickle.loads(pickled_sched))

    def send_commands(self, command_list, **kwargs):
        '''
        Send out commands to other components
        '''
        # note using the double splat operator to take in a dictionary but only 
        # pick out the keyword arguments relevant to this function
        
        #if len(command_list):
        #    print command_list
        
        for command, params in command_list:
        #for i in range(0, len(command_list), 2):
        #    command = command_list[i]
        #    params  = command_list[i+1]
            self.dev_logger.debug("params is %s",params)
            if len(params)>0:
                key = pmt.from_python(command)
                vals = pmt.from_python(([params], {})) 
                self.message_port_pub(COMMAND_OUT_PORT, pmt.pmt_cons(key,vals)) 
            
    def send_app_pkts(self, app_out_list, **kwargs):
        '''
        Forward packets to application layer
        '''
        frame_nums = set()
        # note using the double splat operator to take in a dictionary but only 
        # pick out the keyword arguments relevant to this function
        
        for pkt in app_out_list:
            
            try:
                meta,data = pkt
            except ValueError:
                self.dev_logger.error("Value error for pkt: %s", pkt)
                raise ValueError
            
            self.message_port_pub(TO_APP_PORT, pmt.from_python(data))   
            frame_nums.add(meta["frameID"])
         
        if len(app_out_list) > 0:
            self.dev_logger.info("sending %d packets from frames %s to app layer", 
                                 len(app_out_list), list(frame_nums))            

    def tx_frames(self, tx_list, **kwargs):
        '''
        Send out all the packets in the tx_list
        '''
        if len(tx_list) > 0:
            self.dev_logger.debug("sending %d packets to framer",len(tx_list))
        
        # note using the double splat operator to take in a dictionary but only 
        # pick out the keyword arguments relevant to this function
        for meta, data in tx_list:
            if "tx_time" in meta:
#                self.dev_logger.debug("commanding slot start of %s,%s at current time %s,%s", 
#                                      time.strftime("%H:%M:%S", time.localtime(meta["tx_time"][0])),
#                                           meta["tx_time"][1], 
#                                      time.strftime("%H:%M:%S", time.localtime(self.current_timestamp.int_s())),
#                                           self.current_timestamp.frac_s(),)
                self.dev_logger.debug("commanding slot start of %s at current time %s", 
                                      meta["tx_time"],self.current_timestamp)
            #print "sending packet with metadata %s" % meta
            msg = pmt.pmt_cons(pmt.from_python(meta), pmt.from_python(data))
            self.message_port_pub(OUTGOING_PKT_PORT, msg)
            
    def log_dropped_pkts(self, dropped_pkts, **kwargs):
        '''
        Log any packets the MAC drops
        '''
        
        # note using the double splat operator to take in a dictionary but only 
        # pick out the keyword arguments relevant to this function
        for meta, data in dropped_pkts:
            meta["frequency"] = self.convert_channel_to_hz(meta["frequency"])
            self.ll_logging.packet(deepcopy(meta))    
        

    def convert_channel_to_hz( self, index ):
        if self.number_digital_channels > 1:
            freq = self.fs*index/float(self.number_digital_channels)
            if freq >= self.fs/2.0:
                freq = freq - self.fs
        else:
            freq = 0
        return freq

    def app_queue_size(self):
        '''
        For base station nodes, return the min of the approximate number of items in the 
        packet output queues. 
        For mobile nodes, return the size of the app_in queue
        Useful to allow traffic generator blocks to back off how quickly they are 
        adding data to the app in queue
        '''
        if self.mac_sm.is_base():
            if len(self.pkt_switch_queues.keys()) > 0:
                queue_lens = [len(q) for q in self.pkt_switch_queues.values()]
#                self.dev_logger.debug("pkt queue keys: %s",self.pkt_switch_queues.keys() )
#                self.dev_logger.debug("reported min of pkt queue len is %d", min(queue_lens))
                return min(queue_lens)
            else:
#                self.dev_logger.debug("pkt queue dict is empty")
                return 0
        else:
#            self.dev_logger.debug("pkt queue len %d", len(self.app_in_q))
            return len(self.app_in_q)
        
    def log_mac_behavior(self,inp,outp):

        if self.mac_sm.is_base() :
            # handle init
            if self.last_frame_slots is None:
                self.last_frame_slots = deepcopy(inp["frame_config"]["slots"])
                
            elif inp["frame_config"]["slots"] !=self.last_frame_slots:
             
                in_slots = self.last_frame_slots
                out_slots = inp["frame_config"]["slots"]
            
                for k in range(min([ len(in_slots), len(out_slots)] )):
                    if in_slots[k].owner != out_slots[k].owner:
                        self.dev_logger.info("Owner of %s slot %d changed from %d to %d",
                                             in_slots[k].type, k, in_slots[k].owner,
                                             out_slots[k].owner  )
                self.last_frame_slots = deepcopy(out_slots)
        else:
            pass
        
        pass
    
    def set_time_calibration_complete(self):
        self.time_cal_complete = True
        
    def send_time_calibration_beacons(self, cal_time):
        '''
        It's assumed that only base nodes will have this function called
        '''
        
        # set up cal frame
        compute_frame = self.mac_config["slot_manager"].compute_frame
        self.cal_frame_config = compute_frame(0)
        self.cal_frame_config["t0_frame_num"] = 0
        self.cal_frame_config["first_frame_num"]=0
        # compute number of beacons to send
        
        for k,slot in enumerate(self.cal_frame_config["slots"]):
            if (slot.type == "beacon"):
                self.cal_frame_config["slots"][k] = slot._replace(bb_freq=self.beacon_channel)
                    
        # compute number of beacons to send
        
        frame_len = self.cal_frame_config["frame_len"]
        
        self.cal_schedule = SimpleFrameSchedule(frame_config=self.cal_frame_config,
                                                first_frame_num=0,
                                                frame_num_ref=0,
                                                valid=True)
        
        num_beacons = int(math.floor(cal_time/frame_len))
        
        
        if (num_beacons < 2) and ( cal_time > 0):
            
            self.dev_logger.warning(("Sending %d beacons when minimum number of " + 
                                     "beacons is 2. This will likely fail. frame " +
                                     "length is %f and time cal duration is %f"), 
                                    num_beacons, frame_len, cal_time)
            
            self.dev_logger.info("starting time calibration with %d beacons over %f seconds",
                                 num_beacons, cal_time)    
        
        self.do_time_cal = True
        self.num_cal_beacons = num_beacons
        
        
        

    def work(self, input_items, output_items):
        #print "tdma controller work"       
        #process streaming samples and tags here
        in0 = input_items[0]
        nread = self.nitems_read(0) #number of items read on port 0
        ninput_items = len(input_items[0])
        
        # update the starting timestamp for this block
        start_timestamp =  self.ref_timestamp + (nread - self.ref_time_offset)/self.fs

        #read all tags associated with port 0 for items in this work function
        tags = self.get_tags_in_range(0, nread, nread+ninput_items)

        #print "tdma controller start of tag loop"   
        #lets find all of our tags, making the appropriate adjustments to our timing
        for tag in tags:
            key_string = pmt.pmt_symbol_to_string(tag.key)
            
            if key_string == "rx_time":
                self.ref_time_offset = tag.offset
                self.ref_timestamp = time_spec_t(pmt.to_python(tag.value))
                
                # only set host offset at the start
                if not self.found_time:
                    current_time = time.time()
                    current_time_ahead = time_spec_t(current_time) - self.ref_timestamp
                    self.mac_sm.cq_manager.set_current_time_ahead(float(current_time_ahead))
                
                    self.dev_logger.debug("for rx time %s and host time %s, setting time ahead to %s",
                                          self.ref_timestamp, current_time, current_time_ahead)
                
                
                self.found_time = True
                
                self.dev_logger.debug("tdma_controller found new rx time of %s at offset %ld",
                                      self.ref_timestamp, self.ref_time_offset)
                
                
                
                
                #print "mobile controller found rate"   
                # if this tag occurs at the start of the sample block, update the 
                # starting timestamp
                if tag.offset == nread:
                    start_timestamp =  self.ref_timestamp + (nread - 
                                           self.ref_time_offset)/self.fs
                    
            elif key_string == "rx_rate":
                self.fs = pmt.to_python(tag.value)
                self.found_rate = True
                
                #print "mobile controller found time"   
                # if this tag occurs at the start of the sample block, update the 
                # starting timestamp
                if tag.offset == nread:
                    start_timestamp =  self.ref_timestamp + float(nread - 
                                           self.ref_time_offset)/self.fs
#        self.dev_logger.debug("tag processing complete")
        
        if not (self.current_sched is None):
            start_timestamp = start_timestamp.round_to_sample(self.fs, self.current_sched["t0"])
        #determine first transmit slot when we learn the time
        if not self.know_time:
            if self.found_time and self.found_rate:
                #print "mobile controller knows time"   
                self.know_time = True
                
                # if the state machine has a command queue manager, send out a time cal
                # message
                if hasattr(self.mac_sm, "cq_manager"):
                    # calibrate the command queue to uhd timing errors
                    cal_ts = self.ref_timestamp  + float(nread + ninput_items - 
                                                         self.ref_time_offset)/self.fs
                    self.mac_sm.cq_manager.add_command_to_queue([(cal_ts, 0, "time_cal")])
                    
         
        if self.know_time:
            # set the mac to generate packets if the start of the frame occurs at any
            # point between now and the end of the current block plus the lead limit. 
            # This should guarantee that packets are always submitted at least one lead
            # limit ahead of their transmit time
            end_timestamp = self.ref_timestamp + self.mac_config["lead_limit"] + float(nread + 
                                ninput_items - self.ref_time_offset)/self.fs 
                                           
        else:
            end_timestamp = start_timestamp
        
        if not (self.current_sched is None):
            end_timestamp = end_timestamp.round_to_sample(self.fs, self.current_sched["t0"])
        
        # only update the current timestamp if it is further along than the state machine
        if self.current_timestamp < start_timestamp:
            self.current_timestamp = start_timestamp
        
        
        # use this to detect endless loops 
        loop_counter = 0
        loop_max = 100
        last_ts = self.current_timestamp
        
        # grab the latest schedule updates from the thread safe data struct
        num_scheds = len(self.in_sched_update_q)

#        self.dev_logger.debug("processing schedule updates")
        for k in range(num_scheds):
            self.sched_seq.append(self.in_sched_update_q.popleft())
        
#        self.dev_logger.debug("schedule updates all appended to schedule sequence")        
        # run the state machine if time cal is complete
        if self.time_cal_complete:
#        if self.current_sched is not None:
#            self.last_frame = deepcopy(self.current_sched)

            # handle any incoming packets
            self.process_raw_incoming_queue()

            # start timers
            if self.monitor_timing == True:
                wall_start_ts = time.time()
                state_start_ts = self.current_timestamp
        
            outp = None
            #print "mobile controller state machine loop"   
            # iterate state machine until the current timestamp exceeds the ending timestamp
            
            while self.current_timestamp < end_timestamp:
#                self.dev_logger.debug("iterating state machine")
                last_ts = self.current_timestamp
                rf_in = []
                
                
                
                while( len(self.incoming_q) > 0): 
                    rf_in.append(self.incoming_q.popleft())
                
                inp = {
                       "app_in":self.app_in_q,
                       "current_ts":self.current_timestamp,
                       "end_ts":end_timestamp,  
                       "frame_config":self.frame_config,
                       "frame_count":self.frame_count,
                       "mac_config":self.mac_config,
                       "packet_count":self.packet_count, 
                       "pkt_switch_queues":self.pkt_switch_queues, 
                       "plot_lock":self.plot_lock,
                       "rf_in":rf_in, 
                       "sched_seq":self.sched_seq, 
                       } 
                
                #print "current timestamp is %s, end timestamp is %s" %(self.current_timestamp, end_timestamp)
                #print "iterating state machine"   
                outp = self.mac_sm.step( (inp, False) )
                # handle outputs
                #print "sending tx frames"                   
                self.tx_frames(**outp)
                #print "sending commands"
                self.send_commands(**outp)
                #print "sending application packets"
                self.send_app_pkts(**outp)
                self.log_dropped_pkts(**outp)
                
                self.log_mac_behavior(inp,outp)
                #print "output handling complete"
                
                # update node state with results
                self.current_timestamp = time_spec_t(outp["current_ts"])
                self.packet_count = outp["packet_count"]
                self.pkt_switch_queues = outp["pkt_switch_queues"]
                self.frame_count = outp["frame_count"]
                self.frame_config = outp["frame_config"] 
                self.sched_seq = outp["sched_seq"]
    #            self.schedule_valid = outp["schedule_valid"]
                #bers = [self.active_rx_slots[num]["ber"] for num in self.active_rx_slots]
                #self.dev_logger.debug("active slot bers are %s", bers) 
            
                if last_ts == self.current_timestamp:
                    loop_counter+=1
                else:
                    loop_counter = 0
                    
                if loop_counter > loop_max:
                    
                    self.dev_logger.warn("INFINITE (PROBABLY) LOOP DETECTED - breaking out after %d loops",loop_counter)
                    self.dev_logger.warn("current timestamp is: %s  end timestamp is %s",self.current_timestamp, end_timestamp)
                    break
            #print "tdma controller work complete"  
#                self.dev_logger.debug("iteration complete")
            # do timer calcs at end of work function
            if self.monitor_timing == True:
                wall_end_ts = time.time()
                
                # if state machine wasn't executed at least once, outp won't be defined,
                # so assign something reasonable to state_end_ts
                if not (outp is None):
                    state_end_ts = time_spec_t(outp["current_ts"])
                else:
                    state_end_ts = state_start_ts
                    
                wall_delta_ts = wall_end_ts - wall_start_ts
                state_delta_ts = float(state_end_ts - state_start_ts)
                
                self.state_time_deltas += state_delta_ts
                self.wall_time_deltas += wall_delta_ts
                
                if self.state_time_deltas >= self.poll_interval:
                    
                    self.dev_logger.info("runtime ratio was %f wall seconds per state second",self.wall_time_deltas/self.state_time_deltas)
                    self.state_time_deltas = 0
                    self.wall_time_deltas = 0
                    
        # we're still in time cal       
        elif self.do_time_cal: 
            
            if not self.know_time:
                self.dev_logger.error(("The base station does not know it's own time. " +
                                       "Cannot calibrate"))
            elif not self.mac_sm.is_base():
                self.dev_logger.error("Only base nodes can send time calibration beacons")
            
        
            else:
                
                # send out cal beacon frames
                for k in range(self.num_cal_beacons):
                    
                    
                    
                    
                    packet_count = self.packet_count
                    frame_count = 0 
                    frame_ts = (self.current_timestamp + self.mac_config["lead_limit"] + 
                                k*self.cal_frame_config["frame_len"])
                    
                    # round fractional part to an integer sample so we don't break the 
                    # slot selector
                    frame_ts = time_spec_t(frame_ts.int_s(), round(frame_ts.frac_s()*self.fs)/self.fs )
                    
                    config = self.mac_config
                    mobile_queues=defaultdict(deque)
                    
                    # make mac beacon frames 
                    outs = self.manage_slots.send_frame(self.mac_config, 
                                                             self.cal_frame_config,
                                                             self.cal_schedule,
                                                             frame_count, 
                                                             packet_count, 
                                                             frame_ts, 
                                                             mobile_queues, )
                    
                    frame_count, packet_count, tx_list, mobile_queues, dropped_pkts = outs
                    
                    # handle outputs
                    self.packet_count = packet_count
                    # filter out anything that's not a beacon
                    tx_list = [x for x in tx_list if 
                               x[0]["pktCode"] == self.mac_sm._types_to_ints["beacon"]]
                    
                    # add tdma headers to all the packets in the tx list
                    tx_list = [ (meta, self.mac_sm.pack_tdma_header(data, **meta)) 
                               for meta, data in tx_list  ]

                    
                    # send packets
                    self.tx_frames(tx_list) 
                    
                self.current_timestamp = (end_timestamp + self.mac_config["lead_limit"] + 
                                self.num_cal_beacons*self.cal_frame_config["frame_len"])
                self.do_time_cal = False
               
        return ninput_items
    
       
