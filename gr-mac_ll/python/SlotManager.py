#
# This file is part of ExtRaSy
#
# Copyright (C) 2013-2014 Massachusetts Institute of Technology
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
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
import abc
from bisect import bisect
from bisect import bisect_right
from collections import defaultdict
from collections import namedtuple
from collections import OrderedDict
import copy
from copy import deepcopy
import cPickle
from itertools import chain
from itertools import izip
import logging
from math import floor
from math import ceil
from operator import itemgetter
import random
import struct
import sqlite3
import threading
import time
import os
import sys


# third party library imports
import numpy as np
import numpy.ma as ma

# project specific imports
from dataInt import DataInterface
from digital_ll import beacon_utils
from digital_ll import GridFrameSchedule as grid_sched
from digital_ll import GridUpdateTuple
from digital_ll import lincolnlog
from digital_ll import power_controller
from digital_ll import SimpleFrameSchedule
from digital_ll import time_spec_t
from digital_ll.beacon_utils import TDMA_HEADER_MAX_FIELD_VAL
from digital_ll.beacon_utils import TDMA_HEADER_LEN
from digital_ll.beacon_utils import PHY_HEADER_LEN
from digital_ll.beacon_utils import frame_config_to_xml
from digital_ll.FrameSchedule import SlotParamTuple
from digital_ll.lincolnlog import dict_to_xml
import sm
from sm import SM


#=========================================================================================
# Slot Manager Abstract Base Class
#=========================================================================================
class SlotManager(object):
    ''' 
    Defines the interface for slot manager objects 
    '''
    __metaclass__ = abc.ABCMeta
    
    current_schedule = None

    frame_history = None
    dev_log = None
    types_to_ints = None
    ints_to_types = None
    frame_window = None
    slot_manager_header_names = None
    slot_manager_header_format = None
    SlotManagerHeaderTuple = None
    slot_manager_header_len = None
    
    def __init__(self, types_to_ints, options, tdma_mac):
        '''
        Declare any parameters needed by the slot manager here
        '''
        self.dev_log = logging.getLogger('developer')
        
        self.types_to_ints = dict(types_to_ints)
        self.ints_to_types = dict()
        
        # map from ints back to slot types
        for key in self.types_to_ints:
            self.ints_to_types[self.types_to_ints[key]] = key
        
        self.frame_window = options.frame_validaton_history_depth
        self.frame_history = {}
    
        # append any subclass specific headers here 
        self.slot_manager_header_names = ''
        self.slot_manager_header_format = ''
        
        # make a named tuple for the slot manager header. Subclasses are expected to 
        # overwrite this
        self.SlotManagerHeaderTuple = namedtuple('SlotManagerHeaderTuple', 
                                                 self.slot_manager_header_names)
        
        # finally calculate the length of the class specific header
        self.slot_manager_header_len = struct.calcsize(self.slot_manager_header_format)

        # store off tdma mac object so code can access its member functions
        self.tdma_mac = tdma_mac

        
    def compute_frame(self, frame_num):
        
        if self.current_schedule is None:
            frame_config = None
        else:
            frame_config = self.current_schedule.compute_frame(frame_num)
            self.frame_history[frame_num] = deepcopy(frame_config)
            
        return frame_config        

    #@timeit
    def prune_frame_history(self, frame_num):
        
        for k in self.frame_history.keys():
            if k < frame_num-self.frame_window:
                del self.frame_history[k]  

    def timestamp_to_slot_and_frame(self, timestamp, frame_tuples, frame_times):
        '''
        Find the slot and frame number in which a timestamp occurred
        
        Given the frame_config struct, calculate which slot of which frame
        covers the specified timestamp. Only generate results for frames that you know about
    
        '''
        out_params = (None, None)
    

        ins_point = bisect_right(frame_times, timestamp)
        if ins_point >= 1:
            frame_num = frame_tuples[ins_point-1][0]
            frame = self.frame_history[frame_num]
            
            # now figure out what slot this timestamp is in
            pkt_offset = float(timestamp - frame["t0"])
            
            slot_offsets = [s.offset for s in frame["slots"]]
            
            ins_point = bisect_right(slot_offsets, pkt_offset)
            # check if packet is newer than any frames currently known about
            if pkt_offset > frame["frame_len"]:
                slot_num = -1
                
                print "packet offset %f greater than frame length %f"%(pkt_offset, frame["frame_len"])
                
                out_params = (frame_num, slot_num)
            elif ins_point >= 1:
                slot_num = ins_point-1
                out_params = (frame_num, slot_num)
                

        return out_params
    
    def packets_to_slot_and_frame(self,rf_in, mac_config):
        '''
        Find the slot and frame number in which a packet occurred
        
        Given the frame_config struct, calculate which slot of which frame
        covers the specified packet. Only generate results for frames that you know about
    
        '''
        # find the time offset of the timestamp with respect to the first frame in the 
        # schedule 
        out_params = []
        
        bitrate = mac_config["fs"]/mac_config["samples_per_symbol"]*mac_config["bits_per_symbol"]
        
        pkt_overhead = (self.slot_manager_header_len + 
                        self.tdma_mac.get_tdma_header_len() + 
                        self.tdma_mac.get_phy_header_len())
        
        if len(self.frame_history) > 0:
            
            frame_tuples = [ (key, time_spec_t(val["t0"])) for key,val in self.frame_history.items()]
    
            # sort by timestamp
            frame_tuples.sort( key=itemgetter(1)) 
            frame_times = [el[1] for el in frame_tuples]
    
            # subtract first frame's timestamp from all frames (helps with precision issues)
            
            # figure out what frame this timestamp is in
            for meta, data in rf_in:
                
                if data is None:
                    data_len = 0
                else:
                    data_len = len(data)
                    
                packet_middle = (data_len + pkt_overhead)*8/bitrate/2  
                packet_timestamp = time_spec_t(meta["timestamp"])
                
                frame_num, slot_num = self.timestamp_to_slot_and_frame(packet_timestamp + 
                                                                       packet_middle,
                                                                       frame_tuples, 
                                                                       frame_times)
                if frame_num is not None and slot_num is not None:  
                    out_params.append((meta, data, frame_num, slot_num))
            
        return out_params
    
    
    def pack_slot_manager_header(self, slot_manager_header_tuple, data):
        """
        Concatenates 'header' fields with data to form a payload suitable 
        to pass down to lower layers
        """
        
        packed_header = struct.pack(self.slot_manager_header_format, 
                                    *slot_manager_header_tuple)
    
        # join packet data with the binary packed header
        payload = ''.join( (packed_header, data) )
        return payload
    
    def update_slot_manager_header(self, slot_manager_header_tuple, payload):
        """
        This assumes that the header fields already exist in payload and overwrites those 
        fields with new values
        """
        
        # this assumes the header fields are header_offset bytes from the start of payload
        packed_header = struct.pack(self.slot_manager_header_format, 
                                 *slot_manager_header_tuple)
        return ''.join( (packed_header, payload[self.slot_manager_header_len:]) )   
        
    def unpack_slot_manager_header(self, meta, payload):
        """
        The inverse of pack_slot_manager_header: This pulls the 'header' fields out
        of the provided payload and returns them as a list of tuples
        """
            
        # pull the header fields out of payload using a named tuple
        headerTup = self.SlotManagerHeaderTuple
        headerFields = headerTup._make(struct.unpack(self.slot_manager_header_format, 
                                                     payload[:self.slot_manager_header_len]))
        # cut the header bytes out of the payload     
        payload = payload[self.slot_manager_header_len:]

        # add info from header to metadata
        meta.update(headerFields._asdict())
        
        return meta, payload
    
    
    def fill_slot(self, mac_config, packet_count, slot, slot_num, cur_frame_ts, frame_num, 
                  pkt_in, link_dir, pre_guard, toID, control_packets=[]):
        '''
        Add as many packets to slot as will fit without exceeding the slot length
        
        This function checks the pkt_in queue for a packet, and then verifies the packet will
        fit into what is left of the current slot. This function is also responsible for 
        managing the pkt_in queue, the packet_count counter, and adding timing metadata 
        as necessary to packets in slot_packets
        
        Keyword Arguments:
        
        mac_config            (dict) mac state machine configuration info. Must contain at
                                     minimum the following:
          bits_per_symbol      (int) number of bits in each symbol. Depends on modulation
          bytes_to_samples    (func) converts number of bytes to number of samples
          fs                 (float) sample rate at the output of the modulator
          macCode              (int) MAC code to add to header
          my_id                (int) MAC address of this node
          phyCode              (int) PHY code to add to header
          pkt_overhead         (int) Number of bytes added to each packet as MAC header.
                                     Does not include PHY headers (preamble, pkt len, etc) 
          samples_per_symbol (float) number of samples for each symbol. 
        packet_count           (int) running count of number of packets sent
        slots                 (list) element i corresponds to slot number i. Each element
                                     is a SlotParamTuple
        slot_num               (int) number of the current slot
        cur_frame_ts       (time_spec_t) timestamp of the start of the current frame
        frame_num              (int) current frame number
        pkt_in               (queue) (meta,data) tuples ready to be sent in this slot
        link_dir            (string) "up" for uplinks and "down" for downlinks
        types_to_ints         (dict) maps packet type to packet codes
        pre_guard            (float) time in seconds to reserve at the start of a slot
        toID                   (int) MAC address of the intended receiver
              
        Returns:
        
        slot_packets  (list) (meta,data) tuples to be sent during this slot
        packet_count   (int) updated count of packets sent
        pkt_in       (queue) input queue with packets in slot_packets or dropped_pkts removed
        dropped_pkts  (list) if a packet's duration is larger than the slot, it will be 
                             dropped and recoreded here
        '''
     
        dropped_pkts = []
        fs = mac_config["fs"]
        
        
        slot_packets = []
        slot_dur = slot.len-pre_guard
        slot_offset = slot.offset+pre_guard
        current_dur = 0
        num_slot_bytes = 0
        
        # process control packets first
        for (pktCode, data) in control_packets:
            
#            packet_bytes = len(data) + pkt_overhead
#            packet_samples = bytes_to_samples(packet_bytes, samps_per_sym, bits_per_sym)
#            
#            pkt_dur = float(packet_samples)/fs
            
            # start from scratch on metadata for control packets
            meta={"fromID":mac_config["my_id"],
                  "toID":toID,
                  "sourceID":mac_config["my_id"],
                  "destinationID":toID,
                  "packetid":packet_count,
                  "pktCode":pktCode,
                  "phyCode":mac_config["phyCode"],                    
                  "macCode":mac_config["macCode"],
                  "linkdirection":link_dir,
                  "rfcenterfreq":slot.rf_freq,
                  "frequency":slot.bb_freq, 
                  "bandwidth":slot.bw,
                  "tx_gain": slot.tx_gain,
                  "timeslotID":int(slot_num),
                  "frameID":int(frame_num % TDMA_HEADER_MAX_FIELD_VAL )   
                  }  
            
            # build the class specific header tuple and add it to the payload
            slot_manager_header_tuple = self.make_slot_manager_header_tuple(meta,data)

            payload = self.pack_slot_manager_header(slot_manager_header_tuple, data)
            
            # calculate how many samples this packet will take
            num_packet_samples = self.tdma_mac.num_bytes_to_num_samples(len(payload))
            
            pkt_dur = float(num_packet_samples)/fs
            
            # drop any packets that will never fit any slot
            if pkt_dur > slot_dur:
                
                self.dev_log.warn(("packet code %i packet ID %i cannot fit slot %i in frame % i and " +
                                   "will be dropped. Packet length of %i bytes " + 
                                   "and %f seconds exceeds slot of %f seconds."),
                                  meta["pktCode"], meta["packetid"], meta["timeslotID"], meta["frameID"],
                                  len(payload), pkt_dur, slot_dur)

                # add the drop direction to metadata
                meta["direction"] = "drop"
                    
                packet_count = ( packet_count + 1) % TDMA_HEADER_MAX_FIELD_VAL
                
                dropped_pkts.append((meta,payload))   
          
            else:
                     
                # if another packet will fit, add it to the slot packet list and pop it from
                # app in. Otherwise leave it for the next slot
                if current_dur + pkt_dur <= slot_dur:
                       
                    packet_count = (packet_count+ 1) % TDMA_HEADER_MAX_FIELD_VAL
                    
                    pkt_timestamp = time_spec_t(cur_frame_ts.int_s(), 
                                         round((slot_offset + cur_frame_ts.frac_s())*fs)/fs)     
                                    
                    slot_packets.append( (deepcopy(meta),payload) )
                    num_slot_bytes += len(data)
                    current_dur += pkt_dur
                    
        
        # now try to add in data packets               
        while (len(pkt_in) > 0) and (current_dur < slot_dur):
            
            
            
            meta_in, data = pkt_in[0]
            #meta = deepcopy(meta_in)
            meta = meta_in
#            packet_bytes = len(data) + pkt_overhead
#            packet_samples = bytes_to_samples(packet_bytes, samps_per_sym, bits_per_sym)
#            
#            #print "MAC data len %d packet len %d packet samples %d" % (len(data), packet_bytes, packet_samples)
#            pkt_dur = float(packet_samples)/fs
    
            # destinationID is set by whatever is generating packets in the first place, and 
            # should already be in the packet metadata. 
            # sourceID is set by the handler function that first adds in the packet to an 
            # input queue. 
            h_meta={"fromID":mac_config["my_id"],
                    "toID":toID,
                    "packetid":packet_count,
                    "pktCode":self.types_to_ints["data"],
                    "phyCode":mac_config["phyCode"],
                    "macCode":mac_config["macCode"],
                    "linkdirection":link_dir,
                    "rfcenterfreq":slot.rf_freq,
                    "frequency":slot.bb_freq, 
                    "bandwidth":slot.bw,
                    "tx_gain": slot.tx_gain,
                    "timeslotID":int(slot_num),
                    "frameID":int(frame_num % TDMA_HEADER_MAX_FIELD_VAL )   
                    }       
            # adding new header info to meta
            meta.update(h_meta)
            
            # build the class specific header tuple and add it to the payload
            slot_manager_header_tuple = self.make_slot_manager_header_tuple(meta,data)

            payload = self.pack_slot_manager_header(slot_manager_header_tuple, data)
            
            
            # calculate how many samples this packet will take
            num_packet_samples = self.tdma_mac.num_bytes_to_num_samples(len(payload))
            
            pkt_dur = float(num_packet_samples)/fs
            
            # drop any packets that will never fit any slot
            if pkt_dur > slot_dur:
                pkt_in.popleft()
                self.dev_log.warn(("packet code %i packet ID %i cannot fit slot %i in frame % i and " +
                                   "will be dropped. Packet length of %i bytes " + 
                                   "and %f seconds exceeds slot of %f seconds."),
                                  meta["pktCode"], meta["packetid"], meta["timeslotID"], meta["frameID"],
                                  len(payload), pkt_dur, slot_dur)
                # add the drop direction to metadata
                meta["direction"] = "drop"
                    
                packet_count = ( packet_count + 1) % TDMA_HEADER_MAX_FIELD_VAL
                
                dropped_pkts.append((meta,payload))   
      
            else:
                     
                # if another packet will fit, add it to the slot packet list and pop it from
                # app in. Otherwise leave it for the next slot
                if current_dur + pkt_dur <= slot_dur:
                       
                    packet_count = (packet_count+ 1) % TDMA_HEADER_MAX_FIELD_VAL
                                    
                    slot_packets.append( (meta,payload) )
                    num_slot_bytes += len(data)
    
                    pkt_in.popleft()
                
                current_dur += pkt_dur
            
        
        # add timestamp and tx time fields
        current_dur = 0    
        for k, (meta,payload) in enumerate(slot_packets):
            
            self.dev_log.debug("sending packet number %i in frame %i, slot %i",
                                       meta["packetid"], meta["frameID"], meta["timeslotID"])
            
            
            # calculate how many samples this packet will take
            num_packet_samples = self.tdma_mac.num_bytes_to_num_samples(len(payload))
            
            pkt_dur = float(num_packet_samples)/fs
            
            pkt_timestamp = time_spec_t(cur_frame_ts.int_s(), 
                                        round((slot_offset + 
                                               cur_frame_ts.frac_s() + 
                                               current_dur)*fs)/fs)
                    
           
            # TODO: update header fields for correct timestamp
            slot_packets[k][0]["timestamp"] = pkt_timestamp.to_tuple()
            
            # add a tx_time field to the first packet of every slot
            if current_dur == 0:
                
                slot_packets[k][0]["tx_time"] = pkt_timestamp.to_tuple()
                
            current_dur += pkt_dur         
                    
        if len(slot_packets) >0:
            slot_packets[0][0]["more_pkt_cnt"] = len(slot_packets)-1
                       
        return slot_packets, packet_count, pkt_in, dropped_pkts, num_slot_bytes   
    
    def make_slot_manager_header_tuple(self, meta, data):
        '''
        This should be overloaded in subclasses
        '''
        
        # returning an empty tuple so this won't fail for classes that don't have any
        # class specific header fields
        return ()             
          
    def append_my_settings(self, indent_level, settings_xml):
        
        params = {
                  "pkt_stat_frame_window":self.frame_window}
        
        settings_xml+= "\n" + dict_to_xml(params, indent_level)
        
        return settings_xml
    
    @abc.abstractmethod
    def log_my_settings(self, indent_level,logger):
        pass
        
         
    @staticmethod            
    def add_options(normal, expert):
    
        normal.add_option("--frame-validaton-history-depth", default=10, type="int",
                          help=("Number of frames used to compute packet statistics. " +
                                "In general this set to beacon_timeout*frame_rate " +
                                "[default=%default]"))
        

        
#=========================================================================================
# Base Slot Manager Abstract Base Class
#=========================================================================================
class BaseSlotManager(SlotManager):
    ''' 
    Defines the interface for slot manager objects 
    '''
    __metaclass__ = abc.ABCMeta
    
    initial_time_ref = None
    
    def __init__(self, types_to_ints, options, tdma_mac, initial_time_ref):
        '''
        Declare any parameters needed by the slot manager here
        '''
        super(BaseSlotManager, self).__init__(types_to_ints, options, tdma_mac)
        
        self.initial_time_ref = initial_time_ref
        
      
     
    def track_slot_performance(self, mac_config,
                                    frame_num, rf_in):   
        
        
        
        verified_pkts = self.packets_to_slot_and_frame(rf_in, mac_config)
        
        for meta, data, frame_num, slot_num in verified_pkts:
            if meta["crcpass"] == False:
                self.dev_log.debug("CRC fail in packet arriving in frame %i, slot %i",
                                    frame_num, slot_num)
            elif meta["toID"] != mac_config["my_id"]:
                        self.dev_log.debug("Not adding packet to packet stat list since it is not addressed to me")
     
            elif frame_num != meta["frameID"] or slot_num != meta["timeslotID"]   :
                self.dev_log.warning(("inconsistent packet. Sent in frame %i slot %i, " +
                                      "arrived in frame %i slot %i"),meta["frameID"],
                                     meta["timeslotID"],frame_num, slot_num)   
        
        
        return 
    
    
    def manage_slots(self, mac_config, frame_num, rf_in, mobile_queues):
        '''
        Determine which slots should be assigned to which nodes
        
        This function should track the performance of each node in each slot and reassign
        slots that are not performing well. This should also remove queues for mobiles 
        that are no longer connected to the network. 
        
        Keyword Arguments:
        
        mac_config    (dict) mac state machine configuration info
 
        frame_num     (int)  current frame number
        rf_in         (list) (meta,data) tuples of packets received over the rf interface 
        mobile_queues (dict) keyed by mac address of a mobile node. Each entry is a list
                             of (meta,data) tuples addressed to the same mobile node   
                                              
        Returns:
        
        mobile_queues (dict) keyed by mac address of a mobile node. Each entry is a list
                             of (meta,data) tuples addressed to the same mobile node
        '''
        
        
        next_sched = deepcopy(self.current_schedule)
        
            
        # remove old frame configs from the history
        self.prune_frame_history(frame_num)   
                    
        return next_sched, mobile_queues
    
     
    
    def send_frame(self, mac_config, frame_config, next_sched, 
                        frame_num, packet_count, cur_frame_ts, mobile_queues):
        '''
        Generate a list of packets to send during the next frame
        
        This generates all of the packets to transmit during the next frame. It should
        handle any control packets generated by the slot manager, packets from the
        application layer, beacons, and if necessary, create keepalive packets. 
        It should also keep track of packet and frame numbers. 
        
        Keyword Arguments:
        
        mac_config            (dict) mac state machine configuration info. Must contain at
                                     minimum the following:
          base_id              (int)
          bits_per_symbol      (int) number of bits in each symbol. Depends on modulation
          bytes_to_samples    (func) converts number of bytes to number of samples
          fs                 (float) sample rate at the output of the modulator
          macCode              (int) MAC code to add to header
          my_id                (int) MAC address of this node
          phyCode              (int) PHY code to add to header
          pkt_overhead         (int) Number of bytes added to each packet as MAC header.
                                     Does not include PHY headers (preamble, pkt len, etc) 
          pre_guard          (float) time in seconds to reserve at the start of a slot                          
          samples_per_symbol (float) number of samples for each symbol. 
        frame_config          (dict) frame format defined by the base station. Must 
                                     contain at minimum the following:
            slots             (list) element i corresponds to slot number i. Each element
                                     is a SlotParamTuple  
        active_slots          (dict) keyed by slot number. The contents of this dictionary  
                                     are specific to the slot manager in use
        frame_num              (int) current frame number
        packet_count           (int) number of packets sent so far
        cur_frame_ts       (time_spec_t) timestamp of the start of the current frame
        mobile_queues         (dict) keyed by mac address of a mobile node. Each entry is 
                                     a list of (meta,data) tuples addressed to the same 
                                     mobile node
                                    
        Returns:
        
        active_slots  (dict) an updated version of the active_slots input. These updates
                             are specific to the slot manager
        frame_num     (int)  current frame number   
        packet_count  (int)  number of packets sent so far
        tx_list       (list) packets to send out for this frame
        mobile_queues (dict) keyed by mac address of a mobile node. Each entry is a list
                             of (meta,data) tuples addressed to the same mobile node with
                             packets included in tx_list or dropped_pkts removed
        dropped_pkts  (list) any packets from app_in that were dropped for any reason
        '''
        
        tx_list = []
        dropped_pkts = [] 
        toID = mac_config["my_id"]
        slots = frame_config["slots"]
        pre_guard = mac_config["pre_guard"]
        
        # store this frame to the frame history
        self.frame_history[frame_num] = frame_config
        
        self.dev_log.debug("sending schedule first frame num %i t0 %s in frame num %i at time %s",
                           next_sched.first_frame_num,next_sched.time_ref, frame_num, cur_frame_ts )
        
        # fill any beacon or active downlink slots
        for k, slot in enumerate(slots):
          
            # if this is a beacon slot, make a beacon and add it to the tx packet list
            if slot.type == 'beacon':
                pktCode = self.types_to_ints["beacon"]
                
                slot_pkts, packet_count = make_beacon(mac_config=mac_config, 
                                                      frame_config=frame_config, 
                                                      next_sched=next_sched,
                                                      frame_num=frame_num, 
                                                      packet_count=packet_count, 
                                                      cur_frame_ts=cur_frame_ts, 
                                                      slot_num=k,  
                                                      pktCode=pktCode, 
                                                      toID=toID,
                                                      bytes_to_samples=self.tdma_mac.num_bytes_to_num_samples,
                                                      dev_log=self.dev_log)
                tx_list += slot_pkts
            
            # if this is an active downlink slot, fill it with data packets    
            elif slot.type == 'downlink' and slot.owner > 0:
                toID = slot.owner
                result = self.fill_slot(mac_config, packet_count, slot, k, cur_frame_ts,   
                                        frame_num, mobile_queues[toID], "down", 
                                        pre_guard, slot.owner)
                
                # unpack results
                slot_pkts, packet_count, mobile_queues[toID], dropped, num_slot_bytes = result
                dropped_pkts += dropped
                
                tx_list+= slot_pkts
            
                
            
        frame_num +=1 
        
        return frame_num, packet_count, tx_list, mobile_queues, dropped_pkts
    

#=========================================================================================
# Mobile Slot Manager Abstract Base Class
#=========================================================================================
class MobileSlotManager(SlotManager):
    ''' 
    Defines the interface for slot manager objects 
    '''
    __metaclass__ = abc.ABCMeta
    
    # placeholder for latest beacon packet metadata
    current_meta = None
    
    
    def __init__(self, types_to_ints, options, tdma_mac):
        '''
        Declare any parameters needed by the slot manager here
        '''
        super(MobileSlotManager, self).__init__(types_to_ints, options, tdma_mac)
        
        self.sync_frame_len = options.beacon_sense_block_size
        self._tx_freq = options.rf_tx_freq
        
    def track_slot_performance(self, mac_config, frame_num, rf_in, beacon_feedback):
        '''
        Determine which slots are active and assigned to the mobile node
        
        In general, this function should prune the active_slots struct of slots this 
        node no longer owns, add new downlink slots when they are first assigned to the 
        node, and keep a running tally of any neccessary slot statistics
        
        Keyword Arguments:
        
        mac_config         (dict) mac state machine configuration info
        frame_num          (int)  current frame number
        rf_in              (list) (meta,data) tuples of packets received over the rf 
                                  interface 
                            
        Returns:
        '''
        

        verified_pkts = self.packets_to_slot_and_frame(rf_in, mac_config)
        
        for meta, data, frame_num, slot_num in verified_pkts:
            if meta["crcpass"] == False:
                self.dev_log.debug("CRC fail in packet arriving in frame %i, slot %i",
                                    frame_num, slot_num)

            elif meta["toID"] != mac_config["my_id"]:
                        self.dev_log.debug("Not adding packet to packet stat list since it is not addressed to me")
    
                 
            elif frame_num != meta["frameID"] or slot_num != meta["timeslotID"]   :
                self.dev_log.warning(("inconsistent packet for pkt number %i. Sent in frame %i slot %i, " +
                                      "arrived in frame %i slot %i at time %s"), meta["packetid"],
                                     meta["frameID"], meta["timeslotID"],frame_num, 
                                     slot_num, meta["timestamp"])
                for key, val in self.frame_history.iteritems(): 
                    self.dev_log.debug("frame_num: %i t0: %s", key, val["t0"])   
            
        return  
    
    def manage_slots(self, mac_config, frame_num, current_ts=None):
        '''
        Determine which slots are active and assigned to the mobile node
        
        In general, this function should prune the active_slots struct of slots this 
        node no longer owns, add new downlink slots when they are first assigned to the 
        node, and keep a running tally of any neccessary slot statistics
        
        Keyword Arguments:
        
        mac_config         (dict) mac state machine configuration info 
        slot_stat_history  (dict) keyed by slot number. The contents of this dictionary  
                                  are specific to the slot manager in use
        frame_num          (int)  current frame number
                            
        Returns:
        
        slot_stat_history (dict) an updated version of the slot_stat_history input. 
                                 These updates are specific to the slot manager
        '''
        
        
        # remove old frame configs from the history
        self.prune_frame_history(frame_num)
                 
        return 
    
        
    def send_frame(self, mac_config, frame_config, frame_num, 
                          packet_count, frame_ts, app_in):
        '''
        Generate a list of packets to send during the next frame
        
        This generates all of the packets to transmit during the next frame. It should
        handle any control packets generated by the slot manager, packets from the
        application layer, and if necessary, create keepalive packets. It should also
        keep track of packet and frame numbers. 
        
        Keyword Arguments:
        
        mac_config            (dict) mac state machine configuration info. Must contain at
                                     minimum the following:
          base_id              (int)
          bits_per_symbol      (int) number of bits in each symbol. Depends on modulation
          bytes_to_samples    (func) converts number of bytes to number of samples
          fs                 (float) sample rate at the output of the modulator
          macCode              (int) MAC code to add to header
          my_id                (int) MAC address of this node
          phyCode              (int) PHY code to add to header
          pkt_overhead         (int) Number of bytes added to each packet as MAC header.
                                     Does not include PHY headers (preamble, pkt len, etc) 
          pre_guard          (float) time in seconds to reserve at the start of a slot                          
          samples_per_symbol (float) number of samples for each symbol. 
        frame_config          (dict) frame format defined by the base station. Must 
                                     contain at minimum the following:
            slots             (list) element i corresponds to slot number i. Each element
                                     is a SlotParamTuple  
        active_slots          (dict) keyed by slot number. The contents of this dictionary  
                                     are specific to the slot manager in use
        frame_num              (int) current frame number
        packet_count           (int) number of packets sent so far
        frame_ts       (time_spec_t) timestamp of the start of the current frame
        app_in               (deque) (meta,data) tuples from the application later  
          
                                    
        Returns:
        
        active_slots (dict)  an updated version of the active_slots input. These updates
                             are specific to the slot manager
        frame_num    (int)   current frame number   
        packet_count (int)   number of packets sent so far
        tx_list      (list)  packets to send out for this frame
        app_in       (deque) the input packet queue with the packets in dropped_pkts or 
                             tx_list removed
        dropped_pkts (list)  any packets from app_in that were dropped for any reason
        '''
        
        tx_list = []
        dropped_pkts = [] 
    
        slots = frame_config["slots"]
        pre_guard = mac_config["pre_guard"]
    
        # fill all uplink slots that are assigned to this node
        for k, slot in enumerate(slots):
            
            # mobiles should only transmit data during their uplink slots   
            if slot.type == 'uplink' and slot.owner == mac_config["my_id"]:
                result = self.fill_slot( mac_config, packet_count, slot, k, frame_ts,   
                                        frame_num, app_in, "up",
                                        pre_guard, mac_config["base_id"])
                
                # unpack results
                slot_pkts, packet_count, app_in, dropped, num_slot_bytes = result
                dropped_pkts += dropped
                
                # add packets for the current slot to the list of packets for the frame
                tx_list+= slot_pkts              
            
        frame_num +=1
     
        return frame_num, packet_count, tx_list, app_in, dropped_pkts
    

#    def acquire_sync(self,frame_config, current_ts, mac_config, reset):
#        
#        # this is default behavior. Since no tune list is ever created, the rf_freq
#        # is a don't care. If we start tuning, the rf_freq must be valid
#        beacon_channel = mac_config["beacon_channel"]
#        rf_freq = self._tx_freq
#        
#        new_frame_config = {
#                            "t0":current_ts,
#                            "frame_len":self.sync_frame_len,
#                            "slots":[SlotParamTuple(owner=mac_config["base_id"], 
#                                                    len=self.sync_frame_len, 
#                                                    offset=0,
#                                                    type='beacon',
#                                                    rf_freq=rf_freq,
#                                                    bb_freq=beacon_channel,
#                                                    bw=0,
#                                                    tx_gain=0)]}
#        
#        return new_frame_config, False, None
    
    
            

    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "sync_frame_len":self.sync_frame_len,
                  }
        opts_xml += "\n" + dict_to_xml(params, indent_level)
          
        opts_xml = super(MobileSlotManager, self).append_my_settings(indent_level,
                                                                     opts_xml)
        
        return opts_xml    
    
    @staticmethod            
    def add_options(normal, expert):
    
        SlotManager.add_options(normal, expert)
        
        normal.add_option("--beacon-sense-block-size", type="float", default=0.5, 
                          help="Step size to use when trying to acquire sync " +
                               "[default=%default]")   
    
            
#=========================================================================================
# Database enabled slot manager abstract class
#=========================================================================================
class BaseSlotManagerDb(BaseSlotManager):
    '''
    Database enabled slot manager abstract class. 
    ''' 
    
    __metaclass__ = abc.ABCMeta
    db = None
    db_filename = None
    db_prune_interval = None
    db_frame_limit = None
    
    def __init__(self, types_to_ints, options, tdma_mac, initial_time_ref):
        '''
        Declare any parameters needed by the slot manager here
        '''
        
        super(BaseSlotManagerDb, self).__init__(types_to_ints, options, 
                                                tdma_mac,
                                                initial_time_ref)
        
        self.db_filename = options.db_file
        self.db_prune_interval = options.db_prune_interval
        self.db_frame_limit = options.db_frame_memory_depth
        self.tables_initialized = False
 


    @abc.abstractmethod
    def initialize_database_tables(self, db_name):
        
        # here's an example of initializing the database interface
        # initialize the database and pass it in to the base station state machine.              
        #self.db = DataInterface(flush_db=True, 
        #                        time_ref = self.initial_time_ref, 
        #                        db_name=db_name)
        
        ## you should also set tables_initialized to True when done
        #if self.db is not None:
        #    # if database is available, do other class specific initialization
        #    self.tables_initialized = True
        
        raise NotImplementedError

 
 
    
    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "db_file":self.db_filename,
                  "db_frame_limit":self.db_frame_limit,
                  "db_prune_interval":self.db_prune_interval,
                  }
        opts_xml += "\n" + dict_to_xml(params, indent_level)
        
                   
        opts_xml = super(BaseSlotManagerDb, self).append_my_settings(indent_level,
                                                                                  opts_xml)    
        return opts_xml
    
    
    @staticmethod            
    def add_options(normal, expert):
    
        BaseSlotManager.add_options(normal, expert)
    
        normal.add_option("--db-file", type="string",
                          default="/tmp/ram/performance_history.sqlite", 
                          help=("path to the database file. This should be on a " +
                                "ramdisk, or performance will be very bad" +
                                "[default=%default]"))
         
        normal.add_option("--db-frame-memory-depth", type='int', default=100,
                          help="Number of frames worth of history to keep in the " +
                               "database at any one time [default=%default]")
        
        normal.add_option("--db-prune-interval", type='int', default=1,
                          help="How often to prune the database, in frames" +
                               " [default=%default]")

#=========================================================================================
# Base Station Static Slot Manager
#=========================================================================================
class base_slot_manager_static(BaseSlotManager):
    '''
    Example implementation for static slot assignment.
    
    Static slot assignment assumes that the initial frame configuration never changes. 
    Also, it does not send keepalives. 
    '''
    
    def __init__(self,types_to_ints, options, tdma_mac, initial_schedule):
        '''
        Declare any parameters needed by the slot manager here
        '''
        
        # call base class init
        super(base_slot_manager_static, self).__init__(types_to_ints, options, tdma_mac, 
                                                       initial_schedule["t0"])

  
        # configure schedule class
        self.current_schedule = SimpleFrameSchedule(frame_config=initial_schedule,
                                                    first_frame_num=0,
                                                    frame_num_ref=0,
                                                    valid=True)
        
    def log_my_settings(self, indent_level, logger): 
        
        # slot manager section start
        logger.info("%s<slot_manager>", indent_level*'\t')
        indent_level += 1
        
        params = {"name":self.__class__.__name__}
        opts_xml = dict_to_xml(params, indent_level)
        
        opts_xml = self.append_my_settings(indent_level, opts_xml)
        logger.info(opts_xml)
        
        # slot manager section end
        indent_level -= 1
        logger.info("%s</slot_manager>", indent_level*'\t')
        
            
#=========================================================================================
# Mobile Static Slot Manager
#=========================================================================================
class mobile_slot_manager_static(MobileSlotManager):
    '''
    Example implementation for static slot assignment.
    
    Static slot assignment assumes that the initial frame configuration never changes. 
    Also, it does not send keepalives. 
    '''
    
    def __init__(self,types_to_ints, options, tdma_mac):
        '''
        Declare any parameters needed by the slot manager here
        '''
        
        # call base class init
        super(mobile_slot_manager_static, self).__init__(types_to_ints, options, tdma_mac)

    def log_my_settings(self, indent_level, logger): 
        
        # slot manager section start
        logger.info("%s<slot_manager>", indent_level*'\t')
        indent_level += 1
        
        params = {"name":self.__class__.__name__}
        opts_xml = dict_to_xml(params, indent_level)
        
        opts_xml = self.append_my_settings(indent_level, opts_xml)
        logger.info(opts_xml)
        
        # slot manager section end
        indent_level -= 1
        logger.info("%s</slot_manager>", indent_level*'\t')
        
    def acquire_sync(self,frame_config, current_ts, mac_config, reset):
        
        # this is default behavior. If we start tuning, the rf_freq must be valid
        rf_freq = self._tx_freq
        
        new_frame_config = {
                            "t0":current_ts,
                            "frame_len":self.sync_frame_len,
                            "slots":[SlotParamTuple(owner=mac_config["base_id"], 
                                                    len=self.sync_frame_len, 
                                                    offset=0,
                                                    type='beacon',
                                                    rf_freq=rf_freq,
                                                    bb_freq=0,
                                                    bw=0,
                                                    tx_gain=0)]}
        
        return new_frame_config, False, None
            
       
#=========================================================================================
# Utility class for shared code for Packet Bit Error Rate based slot manager with 
# performance feedback
#=========================================================================================
class shared_slot_manager_ber_feedback(object):
    '''
    Utility class for shared code between the mobile and base. Note that you should
    put this class first in the inheritance list if you want member functions declared 
    in this class to 'win' in name resolution when resolving member functions that exist
    in this class as well as other classes in the inheritance list
    '''
    PacketStatTuple = namedtuple('PacketStatTuple', 'packetid sourceID')
    
    def setup_headers(self, options):

        if options.rf_power_control_enabled:        
            self.slot_manager_header_format = 'IIB'
            self.slot_manager_header_names = 'slot_total_bytes slot_payload_bytes uplink_gain'
        else:
            self.slot_manager_header_format = 'II'
            self.slot_manager_header_names = 'slot_total_bytes slot_payload_bytes'

        # update the named tuple used in unpacking headers
        self.SlotManagerHeaderTuple = namedtuple('SlotManagerHeaderTuple', 
                                                 self.slot_manager_header_names)
        
        # finally calculate the length of the class specific header
        self.slot_manager_header_len = struct.calcsize(self.slot_manager_header_format)
        self.slot_manager_header_num_fields = len(self.SlotManagerHeaderTuple._fields)

    def make_slot_manager_header_tuple(self, meta, data):
        '''
        Return a header tuple initialized with zeros. The header fields will need to
        be filled in after the slot is filled in, so this will be a placeholder
        '''
        
        if self.pwr_control_up:
            new_tup = self.SlotManagerHeaderTuple(slot_total_bytes=0,
                                                  slot_payload_bytes=0,
                                                  uplink_gain=0)
        else:
            new_tup = self.SlotManagerHeaderTuple(slot_total_bytes=0,
                                                  slot_payload_bytes=0,)
        return new_tup
     
#=========================================================================================
# Base Packet Bit Error Rate based slot manager with performance feedback
#=========================================================================================
class base_slot_manager_ber_feedback(shared_slot_manager_ber_feedback, BaseSlotManager):
    '''
    BER based slot manager with feedback. 
    ''' 
    
    
    db = None
    def __init__(self, types_to_ints, initial_schedule, options, tdma_mac):
        '''
        Declare any parameters needed by the slot manager here
        
        Keyword Arguments:
        
        ber_threshold    (float) 
        keepalive_num_bits (int)
        '''
        
        super(base_slot_manager_ber_feedback, self).__init__(types_to_ints, options, 
                                                             tdma_mac,
                                                             initial_schedule["t0"])
        
        self.setup_headers(options)

        
        # change all non-beacon slot owners to -1
        for k, slot in enumerate(initial_schedule["slots"]):
            if slot.type != "beacon":
                initial_schedule["slots"][k] = slot._replace(owner=-1)
        
        self.current_schedule = grid_sched(num_channels=options.digital_freq_hop_num_channels,
                                           frame_config=initial_schedule,
                                           first_frame_num=0,
                                           frame_num_ref=0,
                                           valid=True)
        
        self.slot_performance = {}
        self.state = "initialize"
        self.state_counter = 0
        self.link_ids = None

        self.db_filename = options.db_file
        self.db_prune_interval = options.db_prune_interval
        self.db_frame_limit = options.db_frame_memory_depth
        
        self.schedule_change_delay = options.slot_assignment_leadtime
        self.downlink_packet_timeout = options.downlink_packet_feedback_timeout
        self.uplink_packet_timeout = options.uplink_packet_feedback_timeout
        
        self.pwr_control = options.rf_power_control_enabled
        self.pwr_control_up = options.rf_power_control_enabled
        

        if self.pwr_control:
            self.power_controller = power_controller(options)

        self.link_summary = {}
        self.grid_fig = None
        
        # start up rf hopper state machine
        self.rf_sm = frame_rf_hopper_base(types_to_ints, self.current_schedule.frame_len,
                                          options)
        self.rf_sm.start()
        
        sync_timeout = float('inf')
        
        # if using the rf_hopper, set the sync timeout to coincide with the hopping period
        sync_timeout = min(sync_timeout, self.rf_sm.min_rf_dwell)
            
        self.beacon_channel = options.berf_beacon_channel
        self.beacon_hopping_enabled = options.berf_beacon_hopping_enabled
        
        if self.beacon_hopping_enabled:
            self.beacon_sm = beacon_hopper_base(types_to_ints, 
                                                self.current_schedule.frame_len,
                                                options)
            self.beacon_sm.start()
            
            # if using the beacon hopper, set the sync timeout to coincide with the 
            # hopping period
            sync_timeout = min(sync_timeout, self.beacon_sm.min_beacon_dwell)
        
        self.tables_initialized = False
 
        self.sm = reinforcement_learner(types_to_ints, options=options, plotting=True, 
                                        sync_timeout=sync_timeout) 
        self.sm.start()
        
        # get the ll_logging set of logs so we have access to the state log
        self.ll_logging = lincolnlog.LincolnLog(__name__)
        self.statelog = self.ll_logging._statelog
        
    #@timeit    
    def track_slot_performance(self, mac_config, cur_frame_num, rf_in):
        '''
        Determine which slots should be assigned to which nodes
        
        This function should track the performance of each node in each slot and reassign
        slots that are not performing well. This should also remove queues for mobiles 
        that are no longer connected to the network. 
        
        Keyword Arguments:
        
        mac_config         (dict) mac state machine configuration info. Must contain at
                                  minimum the following:
          base_id           (int) MAC address of this node (the base station)
          my_id             (int) MAC address of this node
          peer_ids         (list) List of MAC addresses of mobile nodes in the network
        frame_config       (dict) frame format defined by the base station. Must 
                                  contain at minimum the following:
          frame_len       (float) length of the frame, in seconds                         
          slots            (list) element i corresponds to slot number i. Each element
                                  is a SlotParamTuple
          t0        (time_spec_t) timestamp associated with t0_frame_num
          t0_frame_num      (int) frame number of the frame starting at t0
        active_slots       (dict) keyed by slot number. Each value is a dict containing:                       
          ber             (float) the cumulative bit error rate for that slot
          in_shutdown      (bool) whether the slot has been shut down due to poor BER
          pkts             (list) PacketStatTuples, one entry per packet
        frame_num           (int) current frame number
        rf_in              (list) (meta, data) tuples of packets coming from the receiver.
                                  Each meta dict must contain at minimum:
          crcpass          (bool) whether or not the packet passed CRC
          messagelength     (int) length of the packet in bytes
          timestamp (time_spec_t) timestamp when the first sample of the packet arrived  
         
        Returns:
        
        active_slots  (dict) updated version of active_slots, keyed by slot num. Each 
                             element is a dict containing:                
          ber        (float) the cumulative bit error rate for that slot
          in_shutdown (bool) whether the slot has been shut down due to poor BER
          pkts        (list) PacketStatTuples, one entry per packet

        '''
        
         
        if len(self.frame_history) > 0:
            # HACK: Just grab the latest frame config for now
            last_frame_num = max(self.frame_history.keys())  
            frame_config = self.frame_history[last_frame_num]
            
            ack_list = []
            feedback_regions = []
            
            # unpack the class specific header info from the rf_packet list
            rf_in = [ (self.unpack_slot_manager_header(meta, data)) for (meta,data) in rf_in
                     if meta["crcpass"] == True and meta["pktCode"] != self.types_to_ints["beacon"] ]
            
            # if using uplink power control, rescale the uplink gain
            for k, (meta, data) in enumerate(rf_in):
                if "uplink_gain" in meta:
                    rf_in[k][0]["uplink_gain"] = meta["uplink_gain"]*.5
                               
            pkt_tups = self.packets_to_slot_and_frame(rf_in, mac_config)
            
            
            valid_pkts = [(pkt[0], pkt[1]) for pkt in pkt_tups 
                             if pkt[0]["crcpass"] == True and 
                             pkt[0]["fromID"] != mac_config["my_id"]]
            
            # add valid packets to the database
            if self.db is not None:
                self.db.add_rx_packets(valid_pkts, 
                                       TDMA_HEADER_LEN + PHY_HEADER_LEN + self.slot_manager_header_len, 
                                       "pass", 
                                       self.types_to_ints)
            
            for meta, data, frame_num, slot_num in pkt_tups:
                try:  
                    # only process packets that pass CRC, otherwise we can't trust any of the data
                    if meta["crcpass"] == False:
                        self.dev_log.debug("CRC fail in packet arriving in frame %i, slot %i",
                                           frame_num, slot_num)
                        
                    elif meta["toID"] != mac_config["my_id"]:
                        self.dev_log.debug("Not adding packet to packet stat list since it is not addressed to me")
    
                      
                    elif frame_num != meta["frameID"] or slot_num != meta["timeslotID"]:
                        self.dev_log.warning(("inconsistent packet. Sent in frame %i slot %i, " +
                                              "arrived in frame %i slot %i"),meta["frameID"],
                                             meta["timeslotID"],frame_num, slot_num)                                                        
    
                    elif meta["pktCode"] == self.types_to_ints["feedback"]:
                        feedback_region, new_acks = self.unpack_feedback(meta, data)
                        feedback_regions.append( (feedback_region, meta["fromID"]))
                        
                        for ack in new_acks:
                            self.dev_log.info("base received ack in frame %i for packet num %i sourceID %i from node %i",
                                       meta["frameID"], ack.packetid, ack.sourceID, meta["fromID"])
                    
                        ack_list.extend(new_acks) 
        
                except KeyError as err:
                    self.dev_log.exception("metadata %s caused Key Error during feedback " +
                                           "packet handling.", meta)            
            
            
            
            if self.db is not None:
                # process ack list
                self.db.update_packet_status(ack_list, "pass")
                
                # fail any pending packets that occur in frames that have at least one
                # acked packet
                self.db.fail_missing_tx_packets(feedback_regions)
                
                # declare tx packets that haven't been acked as failed
                self.db.update_pending_tx_packets(self.downlink_packet_timeout)  
                
                # declare any bits associated with old rx packets as failed
                self.db.update_pending_dummy_packets(self.uplink_packet_timeout, 
                                                     self.types_to_ints)
              
            # compute the bit error rate for each active slot and prune old packets
#            self.store_pkt_bers(mac_config["base_id"])
            

                
        else:
            pass
        
        return   
           
    #@timeit        
    def manage_slots(self, mac_config, frame_num, rf_in, mobile_queues):
        '''
        Determine which slots should be assigned to which nodes
        
        This function should track the performance of each node in each slot and reassign
        slots that are not performing well. This should also remove queues for mobiles 
        that are no longer connected to the network. 
        
        Keyword Arguments:
        
        mac_config         (dict) mac state machine configuration info. Must contain at
                                  minimum the following:
          base_id           (int) MAC address of this node (the base station)
          my_id             (int) MAC address of this node
          peer_ids         (list) List of MAC addresses of mobile nodes in the network
        frame_config       (dict) frame format defined by the base station. Must 
                                  contain at minimum the following:
          frame_len       (float) length of the frame, in seconds                         
          slots            (list) element i corresponds to slot number i. Each element
                                  is a SlotParamTuple
          t0        (time_spec_t) timestamp associated with t0_frame_num
          t0_frame_num      (int) frame number of the frame starting at t0
        active_slots       (dict) keyed by slot number. Each value is a dict containing:                       
          ber             (float) the cumulative bit error rate for that slot
          in_shutdown      (bool) whether the slot has been shut down due to poor BER
          pkts             (list) PacketStatTuples, one entry per packet
        frame_num           (int) current frame number
        rf_in              (list) (meta, data) tuples of packets coming from the receiver.
                                  Each meta dict must contain at minimum:
          crcpass          (bool) whether or not the packet passed CRC
          messagelength     (int) length of the packet in bytes
          timestamp (time_spec_t) timestamp when the first sample of the packet arrived  
        mobile_queues      (dict) keyed by mac address of a mobile node. Each entry is a
                                  list of (meta,data) tuples addressed to the same mobile  
                                  node              
        Returns:
        
        active_slots  (dict) updated version of active_slots, keyed by slot num. Each 
                             element is a dict containing:                
          ber        (float) the cumulative bit error rate for that slot
          in_shutdown (bool) whether the slot has been shut down due to poor BER
          pkts        (list) PacketStatTuples, one entry per packet
        frame_config  (dict) updated frame format with any changes to slot  
                             assignments. Must contain at minimum the following:
          frame_len  (float) length of the frame, in seconds                         
          slots       (list) element i corresponds to slot number i. Each element
                             is a SlotParamTuple
          t0   (time_spec_t) timestamp associated with t0_frame_num
          t0_frame_num (int) frame number of the frame starting at t0
        mobile_queues (dict) keyed by mac address of a mobile node. Each entry is a list
                             of (meta,data) tuples addressed to the same mobile node
        '''

        next_sched = deepcopy(self.current_schedule)
        
        
        if self.tables_initialized == False:
            
            link_ids = [ (peer_id, 0 ) for peer_id in mac_config["peer_ids"]]
            
            self.initialize_database_tables(self.db_filename)
            self.sm.store_link_ids(self.db, link_ids)
            self.sm.store_scen_config(self.db, self.current_schedule.num_freq_slots,
                                      self.current_schedule.num_time_slots )
            
        
        # this should only happen at startup 
        if next_sched.frame_num_ref < 0:
            next_sched.frame_num_ref = frame_num+1
            next_sched.first_frame_num = frame_num+1
            
        
        # store off the new frame number so all the database machinery stays happy.     
        self.db.preload_frame_num(frame_num)    
        
        # set the time for the next schedule to first become valid
        sched_frame_delta = frame_num - self.current_schedule.frame_num_ref + 1
        next_sched.time_ref = self.current_schedule.time_ref + self.current_schedule.frame_len*sched_frame_delta
        next_sched.frame_num_ref = frame_num + 1
        
        beacon_slots = {}
        
        inp = {"database":self.db,
               }
        
        
        if self.beacon_hopping_enabled:
            outp = self.beacon_sm.step((inp, False))
            self.beacon_channel = outp["beacon_chan"]
            self.dev_log.debug("beacon hopper chose channel: %i", self.beacon_channel)
            
        outp = self.rf_sm.step((inp, False))
        rf_freq = outp["rf_freq"]
        
        self.dev_log.debug("frame_hopper chose freq: %f", rf_freq)
        
        for slot_num, slot in enumerate(next_sched.slots):
            # store off beacon channels
            if self.beacon_hopping_enabled:
                bb_freq = self.beacon_channel
            else:
                bb_freq = slot.bb_freq
            
            if slot.type == 'beacon':
                beacon_slots[slot_num] = GridUpdateTuple(owner=slot.owner, 
                                                         type=slot.type, 
                                                         channel_num=bb_freq,
                                                         rf_freq=rf_freq,
                                                         order=len(beacon_slots))
        
        inp = {"base_id":mac_config["base_id"],
               "beacon_slots":beacon_slots,
               "database":self.db,
               "frame_num":frame_num,
               "link_ids":self.link_ids,
               "link_summary":self.link_summary,
               "num_freq_slots":self.current_schedule.num_freq_slots,
               "num_time_slots":self.current_schedule.num_time_slots,
               "peer_ids":mac_config["peer_ids"],
               "rf_freq":rf_freq,
               "state_counter":self.state_counter,
               }
        outp = self.sm.step( (inp, False))    
        
        self.link_ids = outp["link_ids"]
        self.link_summary = outp["link_summary"]
        slot_assignments = outp["slot_assignments"]
        
        for num, assignment in slot_assignments.iteritems():
            self.dev_log.debug("slot %i assignment: %s", num, assignment)
        
        if self.state_counter < outp["state_counter"]:
        
            frame_change = frame_num+ self.schedule_change_delay
            self.dev_log.debug("reset state: commanding new state for frame %i",frame_change)
            next_sched.store_current_config()
            next_sched.replace_grid(slot_assignments, frame_change)
#            next_sched.plot_update(slot_assignments, self.fig_plotter)
            
            # store off the new frame number so all the database machinery stays happy.     
            self.db.preload_frame_num(frame_change)   
            next_sched.store_update(frame_change, slot_assignments, self.db)
            
        
        # do downlink power control (under development) 
        # self.dev_log.debug("checking that power control is %i",self.pwr_control)  
        if self.pwr_control:
            self.dev_log.debug("calling power controller optimization function")
            next_sched = self.power_controller.optimize_power(frame_num,
                                                              next_sched,
                                                              self.db,
                                                              self.dev_log)     
            
        if self.state_counter < outp["state_counter"]:            
            fc = next_sched.compute_frame(frame_change)
            
            fc_xml = frame_config_to_xml(fc, 2)
            
            state_xml = ("<schedule_change>\n" + 
                        "\t<current_frame_num>%i</current_frame_num>\n" + 
                        "\t<new_frame>\n" + 
                        "%s\n" + 
                        "\t</new_frame>\n" + 
                        "</schedule_change>") % (frame_num, fc_xml)
            
            self.statelog.info(state_xml)
            
        self.state_counter = outp["state_counter"]
        
        # remove old frame configs from the history
        self.prune_frame_history(frame_num)
        
        if frame_num % self.db_prune_interval == 0:
            self.db.prune_tables(self.db_frame_limit)
#            self.sm.prune_tables(mac_config["db_prune_interval"]) 

        return next_sched,  mobile_queues 
    
    #@timeit
    def send_frame(self, mac_config, frame_config, next_sched, 
                   frame_num, packet_count, cur_frame_ts, mobile_queues):
        '''
        Generate a list of packets to send during the next frame
        
        This generates all of the packets to transmit during the next frame. It should
        handle packets from the application layer, beacons, and if necessary, create 
        keepalive packets. It should also keep track of packet and frame numbers. 
        
        Keyword Arguments:
        
        mac_config            (dict) mac state machine configuration info. Must contain at
                                     minimum the following:
          base_id              (int)
          bits_per_symbol      (int) number of bits in each symbol. Depends on modulation
          bytes_to_samples    (func) converts number of bytes to number of samples
          fs                 (float) sample rate at the output of the modulator
          macCode              (int) MAC code to add to header
          my_id                (int) MAC address of this node
          phyCode              (int) PHY code to add to header
          pkt_overhead         (int) Number of bytes added to each packet as MAC header.
                                     Does not include PHY headers (preamble, pkt len, etc) 
          pre_guard          (float) time in seconds to reserve at the start of a slot                          
          samples_per_symbol (float) number of samples for each symbol. 
        frame_config          (dict) frame format defined by the base station. Must 
                                     contain at minimum the following:
            slots             (list) element i corresponds to slot number i. Each element
                                     is a SlotParamTuple  
        active_slots          (dict) keyed by slot num. Each element is a dict containing:                
          ber                (float) the cumulative bit error rate for that slot
          in_shutdown         (bool) whether the slot has been shut down due to poor BER
          pkts                (list) PacketStatTuples, one entry per packet
        frame_num              (int) current frame number
        packet_count           (int) number of packets sent so far
        frame_ts       (time_spec_t) timestamp of the start of the current frame
        mobile_queues         (dict) keyed by mac address of a mobile node. Each entry is 
                                     a list of (meta,data) tuples addressed to the same 
                                     mobile node
                                    
        Returns:
        
        active_slots  (dict) keyed by slot num. Not altered by this function in the BER 
                             slot manager. Each element is a dict containing:                
          ber        (float) the cumulative bit error rate for that slot
          in_shutdown (bool) whether the slot has been shut down due to poor BER
          pkts        (list) PacketStatTuples, one entry per packet
        frame_num      (int) current frame number   
        packet_count   (int) number of packets sent so far
        tx_list       (list) packets to send out for this frame
        mobile_queues (dict) keyed by mac address of a mobile node. Each entry is a list
                             of (meta,data) tuples addressed to the same mobile node with
                             packets included in tx_list or dropped_pkts removed
        dropped_pkts  (list) any packets from app_in that were dropped for any reason
        '''    
        
        # get framing parameters
        tdma_header_len = self.tdma_mac.get_tdma_header_len()
        phy_header_len = self.tdma_mac.get_phy_header_len()
        
        # store the current frame to the db if the db's initialized
        if self.db is not None:
            self.db.add_frame_config(frame_config, frame_num)
                
            # add dummy rx packets to the db
            self.db.add_dummy_rx_feedback(frame_config, frame_num, mac_config["base_id"], 
                                          tdma_header_len+phy_header_len+self.slot_manager_header_len, 
                                          self.types_to_ints)    
      
        tx_list = []
        dropped_pkts = [] 
        toID = mac_config["my_id"]
        slots = frame_config["slots"]
        pre_guard = mac_config["pre_guard"]
        
        
        
        # class specific header fields are stored at the front of each packet
        header_offset = 0
        
        
        for k, slot in enumerate(slots):
            if slot.type == 'beacon':
                pktCode = self.types_to_ints["beacon"]
                slot_pkts, packet_count = make_beacon(mac_config=mac_config, 
                                                      frame_config=frame_config, 
                                                      next_sched=next_sched, 
                                                      frame_num=frame_num,  
                                                      packet_count=packet_count, 
                                                      cur_frame_ts=cur_frame_ts, 
                                                      slot_num=k,  
                                                      pktCode=pktCode,
                                                      toID=toID,
                                                      bytes_to_samples=self.tdma_mac.num_bytes_to_num_samples, 
                                                      dev_log=self.dev_log,
                                                      )
    
                tx_list += slot_pkts
                
                
                
            elif slot.type == 'downlink' and slot.owner > 0:
                toID = slot.owner
                result = self.fill_slot( mac_config, packet_count, slot, k, 
                                   cur_frame_ts, frame_num, mobile_queues[toID], 
                                   "down", pre_guard, slot.owner)
                
                # unpack results
                slot_pkts, packet_count, mobile_queues[toID], dropped, num_slot_bytes = result
                dropped_pkts += dropped
                
                if len(slot_pkts) == 0:
                    self.dev_log.debug("No packets being sent to node %i in slot %i for frame %i",
                                       slot.owner, k, frame_num)

                    
                # calculate number of overhead bytes 
                num_overhead_bytes = len(slot_pkts)*(phy_header_len + tdma_header_len + 
                                                     self.slot_manager_header_len)
                
                # build up class specific header field (in this case they are all common
                # for packets in the same slot
                if self.pwr_control_up:
                    uplink_gain = self.current_schedule.get_uplink_gain(slot.owner)
                    
                    if uplink_gain is None:
                        self.dev_log.warning("No uplink slot found for owner %i, assigning uplink gain of 0", slot.owner)
                        uplink_gain = 0
                          
                    header_tup = self.SlotManagerHeaderTuple(slot_total_bytes=num_overhead_bytes+num_slot_bytes,
                                                             slot_payload_bytes=num_slot_bytes,
                                                             uplink_gain=uplink_gain/.5)
                else:
                    header_tup = self.SlotManagerHeaderTuple(slot_total_bytes=num_overhead_bytes+num_slot_bytes,
                                                             slot_payload_bytes=num_slot_bytes)    
                
                # fill in placeholder fields
                for k, (meta, data) in enumerate(slot_pkts):
                    data = self.update_slot_manager_header(header_tup, 
                                                           data)
                    meta.update(header_tup._asdict())
                    slot_pkts[k] = (meta, data) 
                
                tx_list+= slot_pkts
                

        # add transmitted packets to the db if it is initialized
        if self.db is not None:
            self.db.add_tx_packets(tx_list, frame_num,
                                    TDMA_HEADER_LEN + PHY_HEADER_LEN, 
                                    self.types_to_ints)
            
        frame_num +=1     
     
        return frame_num, packet_count, tx_list, mobile_queues, dropped_pkts

    def unpack_feedback(self, meta, data):
        
        self.dev_log.debug("feedback packet len is %i", len(data))
        format_str = 'HHHH'
        feedback_region = struct.unpack(format_str, data[:struct.calcsize(format_str)])
        
        
        # remove feedback region info from data
        data = data[struct.calcsize(format_str):]
        
        if len(data) > 0:
            # assume data is 16 bit unsigned ints
            format_str = 'H'*int(len(data)/2)
            data_seq = struct.unpack(format_str, data)
            
            # assume that data is actually list of PacketStatTuples (curently pairs)
            ack_list = [ self.PacketStatTuple(*a) for a in grouped( list(data_seq), 2)]
            
        else:
            ack_list = []
        
        return feedback_region, ack_list
    


    def initialize_database_tables(self, db_name):
        
        # initialize the database and pass it in to the base station state machine.              
        self.db = DataInterface(flush_db=True, 
                                time_ref = self.initial_time_ref, 
                                db_name=db_name)
        
        
        if self.db is not None:
            grid_sched.initialize_database_table(self.db)
            reinforcement_learner.initialize_database_table(self.db)
            self.tables_initialized = True
    
  
 
    
    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "db_file":self.db_filename,
                  "db_frame_limit":self.db_frame_limit,
                  "db_prune_interval":self.db_prune_interval,
                  "schedule_change_delay":self.schedule_change_delay,
                  "downlink_packet_timeout":self.downlink_packet_timeout,
                  "uplink_packet_timeout":self.uplink_packet_timeout,
                  }
        opts_xml += "\n" + dict_to_xml(params, indent_level)
        
        
        # add components
        opts_xml += "\n%s<learning_algorithm>"%(indent_level*'\t')
        indent_level+=1
        opts_xml = self.sm.append_my_settings(indent_level, opts_xml)
        indent_level-=1
        opts_xml += "\n%s</learning_algorithm>"%(indent_level*'\t')
        
        # add components
        opts_xml += "\n%s<rf_hopper>"%(indent_level*'\t')
        indent_level+=1
        opts_xml = self.rf_sm.append_my_settings(indent_level, opts_xml) 
        indent_level-=1
        opts_xml += "\n%s</rf_hopper>"%(indent_level*'\t')
           
        opts_xml = super(base_slot_manager_ber_feedback, self).append_my_settings(indent_level,
                                                                                  opts_xml)    
        return opts_xml
    
    @staticmethod            
    def add_options(normal, expert):
    
        BaseSlotManager.add_options(normal, expert)
    
        normal.add_option("--db-file", type="string",
                          default="/tmp/ram/performance_history.sqlite", 
                          help=("path to the database file. This should be on a " +
                                "ramdisk, or performance will be very bad" +
                                "[default=%default]"))
         
        normal.add_option("--db-frame-memory-depth", type='int', default=100,
                          help="Number of frames worth of history to keep in the " +
                               "database at any one time [default=%default]")
        
        normal.add_option("--db-prune-interval", type='int', default=1,
                          help="How often to prune the database, in frames" +
                               " [default=%default]")
        
        normal.add_option("--slot-assignment-leadtime", type='int', default=4,
                          help="How many frames in advance to announce a schedule "+ 
                          "change [default=%default]")
        
        normal.add_option("--downlink-packet-feedback-timeout", type='int', default=4,
                          help="How many frames to wait for an ack before marking a " +
                               "packet as failed [default=%default]")
        
        normal.add_option("--uplink-packet-feedback-timeout", type='int', default=3,
                          help="How many frames to wait before declaring that an uplink" +
                               "packet has failed [default=%default]")
        normal.add_option("--berf-beacon-channel", type='int', default=0,
                          help="Channel on which to expect beacons to appear [default=%default]")
        
        reinforcement_learner.add_options(normal, expert)
        frame_rf_hopper_base.add_options(normal, expert)
        beacon_hopper_base.add_options(normal, expert)
        
        
    def log_my_settings(self, indent_level, logger): 
        
        # slot manager section start
        logger.info("%s<slot_manager>", indent_level*'\t')
        indent_level += 1
        
        params = {"name":self.__class__.__name__}
        opts_xml = dict_to_xml(params, indent_level)
        
        opts_xml = self.append_my_settings(indent_level, opts_xml)
        logger.info(opts_xml)
        
        # slot manager section end
        indent_level -= 1
        logger.info("%s</slot_manager>", indent_level*'\t')        

#=========================================================================================
# Mobile Packet Bit Error Rate based slot manager with performance feedback
#=========================================================================================
class mobile_slot_manager_ber_feedback(shared_slot_manager_ber_feedback, MobileSlotManager):
    '''
    BER based slot manager with feedback
    '''
    slot_stat_history = None
    beacon_channel = None
    last_feedback_pair = None
    def __init__(self, types_to_ints, options, tdma_mac):
        '''
        Declare any parameters needed by the slot manager here
        
        Keyword Arguments:
        
        ber_threshold    (float) 
        keepalive_num_bits (int)
        frame_window       (int)
        '''
        
        super(mobile_slot_manager_ber_feedback, self).__init__(types_to_ints, options, 
                                                               tdma_mac)
        
        self.setup_headers(options)
        
        self.slot_stat_history = {}
        self.beacon_channel = options.berf_beacon_channel
        
        
        self.pwr_control_up = options.rf_power_control_enabled
        self.beacon_hopping_enabled = options.berf_beacon_hopping_enabled
        
        self.rf_sm = frame_rf_hopper_mobile(types_to_ints, options)
        self.rf_sm.start()
        
        if self.beacon_hopping_enabled:
            self.beacon_sm = beacon_hopper_mobile(types_to_ints, options)
            self.beacon_sm.start()
        
    def track_slot_performance(self, mac_config, cur_frame_num, rf_in, beacon_feedback):     
        '''
        Keep a tally of the bit error rate associated with each active downlink slot
        
        This function prunes the slot stats structure of slots this node no longer 
        owns, adds new downlink slots when they are first assigned to the node, and keeps  
        a running tally of the bit error rate associated with each active downlink slot
        
        Keyword Arguments:
        
        mac_config         (dict) mac state machine configuration info. Must contain at
                                  minimum the following:
          my_id             (int) MAC address of this node
        frame_history      (dict) keyed by frame number, where each element is a frame 
                                  format defined by the base station. Each element must 
                                  contain at minimum the following:
          frame_len       (float) length of the frame, in seconds                         
          slots            (list) element i corresponds to slot number i. Each element
                                  is a SlotParamTuple
          t0        (time_spec_t) timestamp associated with t0_frame_num
          t0_frame_num      (int) frame number of the frame starting at t0

        slot_stat_history  (dict) pktlist is list of packet numbers to ack in next frame
        frame_num           (int) current frame number
        rf_in              (list) (meta, data) tuples of packets coming from the receiver.
                                  Each meta dict must contain at minimum:
          crcpass          (bool) whether or not the packet passed CRC
          messagelength     (int) length of the packet in bytes
          timestamp (time_spec_t) timestamp when the first sample of the packet arrived 
         
                            
        Returns:
        
        slot_stat_history (dict) updated version of slot_stat_history, keyed by slot num.  
                                 Each element is a dict containing:                
          ber            (float) the cumulative bit error rate for that slot
          in_shutdown     (bool) whether the slot has been shut down due to poor BER
          pkts            (list) PacketStatTuples, one entry per packet
        '''

        # First, ensure that this is tracking all and only the downlink slots assigned to 
        # this node
        
        # HACK: Just grab the latest frame config for now
        if len(self.frame_history) > 0:
        
            last_frame_num = max(self.frame_history.keys())  
            frame_config = self.frame_history[last_frame_num]
        else:
            frame_config = None
            
        # only process if frame_config is defined
        if frame_config is not None:
            
            
            # unpack the class specific header info from the rf_packet list
            rf_in = [ (self.unpack_slot_manager_header(meta, data)) for (meta,data) in rf_in
                     if meta["crcpass"] == True and meta["pktCode"] != self.types_to_ints["beacon"] ]
            
            # if using uplink power control, rescale the uplink gain
            for k, (meta, data) in enumerate(rf_in):
                if "uplink_gain" in meta:
                    rf_in[k][0]["uplink_gain"] = meta["uplink_gain"]*.5
                
                
            verified_pkts = self.packets_to_slot_and_frame(rf_in, mac_config)
        
            for meta, data, frame_num, slot_num in verified_pkts:
                # only process packets that pass CRC, otherwise we can't trust any of the data
                if meta["crcpass"] == False:
                    self.dev_log.debug("CRC fail in packet arriving in frame %i, slot %i",
                                       frame_num, slot_num)
                elif meta["toID"] != mac_config["my_id"]:
                        self.dev_log.debug("Not adding packet to packet stat list since it is not addressed to me")

                elif frame_num != meta["frameID"] or slot_num != meta["timeslotID"]   :
                    self.dev_log.warning(("inconsistent packet. Sent in frame %i slot %i, " +
                                          "arrived in frame %i slot %i at timestamp %s"),meta["frameID"],
                                         meta["timeslotID"],frame_num, slot_num, meta["timestamp"])
                    for hist_frame_num in self.frame_history:
                        self.dev_log.debug("frame num %i has t0 of %s", hist_frame_num, self.frame_history[hist_frame_num]["t0"])
                                
                else:
                    if "pktlist" not in self.slot_stat_history:
                        self.slot_stat_history["pktlist"] = []
                    
                    self.dev_log.debug("storing packet id %i to packet list as good packet",meta["packetid"] )  
                    self.dev_log.info("received packet num %i sent in frame %i, slot %i during frame %i",
                                      meta["packetid"], meta["frameID"], meta["timeslotID"], cur_frame_num)  
                    self.slot_stat_history["pktlist"].append(self.PacketStatTuple(packetid=meta["packetid"], sourceID=meta["sourceID"]))
                     
        else:
            self.slot_stat_history["pktlist"] = [] 
            
        return 

    def manage_slots(self, mac_config, frame_num, current_ts=None):
        '''
        Determine which slots are active and assigned to the mobile node
        
        In general, this function should prune the active_slots struct of slots this 
        node no longer owns, add new downlink slots when they are first assigned to the 
        node, and keep a running tally of any neccessary slot statistics
        
        Keyword Arguments:
        
        mac_config         (dict) mac state machine configuration info 
        slot_stat_history  (dict) keyed by slot number. The contents of this dictionary  
                                  are specific to the slot manager in use
        frame_num          (int)  current frame number
                            
        Returns:
        
        slot_stat_history (dict) an updated version of the slot_stat_history input. 
                                 These updates are specific to the slot manager
        '''
        
        
        
        
        # remove old frame configs from the history
        self.prune_frame_history(frame_num)
                 
        return 

    
    def send_frame(self, mac_config, frame_config, frame_num, packet_count, frame_ts, 
                   app_in):
        '''
        Generate a list of packets for active uplink slots to send during the next frame
        
        This generates all of the packets to transmit during the next frame. It should
        handle packets from the application layer, and if necessary, create keepalive 
        packets. It should also keep track of packet and frame numbers. It should only
        make packets for frames that are not in shutdown
        
        Keyword Arguments:
        
        mac_config            (dict) mac state machine configuration info. Must contain at
                                     minimum the following:
          base_id              (int)
          bits_per_symbol      (int) number of bits in each symbol. Depends on modulation
          bytes_to_samples    (func) converts number of bytes to number of samples
          fs                 (float) sample rate at the output of the modulator
          macCode              (int) MAC code to add to header
          my_id                (int) MAC address of this node
          phyCode              (int) PHY code to add to header
          pkt_overhead         (int) Number of bytes added to each packet as MAC header.
                                     Does not include PHY headers (preamble, pkt len, etc) 
          pre_guard          (float) time in seconds to reserve at the start of a slot                          
          samples_per_symbol (float) number of samples for each symbol. 
        frame_config          (dict) frame format defined by the base station. Must 
                                     contain at minimum the following:
            slots             (list) element i corresponds to slot number i. Each element
                                     is a SlotParamTuple  
        slot_stat_history       (dict) keyed by slot num. Each element is a dict containing:                
          ber             (float) the cumulative bit error rate for that slot
          in_shutdown      (bool) whether the slot has been shut down due to poor BER
          pkts             (list) PacketStatTuples, one entry per packet
        frame_num              (int) current frame number
        packet_count           (int) number of packets sent so far
        frame_ts       (time_spec_t) timestamp of the start of the current frame
        app_in               (queue) (meta,data) tuples from the application later  
          
                                    
        Returns:
        
        slot_stat_history  (dict) keyed by slot num. Not altered by this function in the BER 
                             slot manager. Each element is a dict containing:                
          ber        (float) the cumulative bit error rate for that slot
          in_shutdown (bool) whether the slot has been shut down due to poor BER
          pkts        (list) PacketStatTuples, one entry per packet
        frame_num    (int)   current frame number   
        packet_count (int)   number of packets sent so far
        tx_list      (list)  packets to send out for this frame
        app_in       (queue) the input packet queue with the packets in dropped_pkts or 
                             tx_list removed
        dropped_pkts (list)  any packets from app_in that were dropped for any reason
        '''             
        tx_list = []
        dropped_pkts = [] 
    
        slots = frame_config["slots"]
        pre_guard = mac_config["pre_guard"]
        
        control_tuple = self.make_feedback_payload(mac_config, 
                                                   self.types_to_ints["feedback"],
                                                   frame_ts)
        
        # get framing parameters
        tdma_header_len = self.tdma_mac.get_tdma_header_len()
        phy_header_len = self.tdma_mac.get_phy_header_len()
        
        # class specific header fields are stored at the front of each packet
        header_offset = 0
        
        # now clear out the list
        if "pktlist" in self.slot_stat_history:
            self.slot_stat_history["pktlist"][:] = []
        
        for k, slot in enumerate(slots):
               
            if slot.type == 'uplink' and slot.owner == mac_config["my_id"]:
                result = self.fill_slot( mac_config, packet_count, slot, k, frame_ts, 
                                        frame_num, app_in, "up",
                                        pre_guard, mac_config["base_id"], [control_tuple])
                
                # unpack results
                slot_pkts, packet_count, app_in, dropped, num_slot_bytes = result
                dropped_pkts += dropped
                
                # calculate number of overhead bytes 
                num_overhead_bytes = len(slot_pkts)*(phy_header_len + tdma_header_len + 
                                                     self.slot_manager_header_len)
                
                
                
                # build up class specific header field (in this case they are all common
                # for packets in the same slot
                if self.pwr_control_up:
                          
                    header_tup = self.SlotManagerHeaderTuple(slot_total_bytes=num_overhead_bytes+num_slot_bytes,
                                                             slot_payload_bytes=num_slot_bytes,
                                                             uplink_gain=slot.tx_gain/.5)
                else:  
                    header_tup = self.SlotManagerHeaderTuple(slot_total_bytes=num_overhead_bytes+num_slot_bytes,
                                                             slot_payload_bytes=num_slot_bytes)
                
                # fill in placeholder fields
                for k, (meta, data) in enumerate(slot_pkts):
                    data = self.update_slot_manager_header(header_tup, 
                                                           data)
                    meta.update(header_tup._asdict())
                    slot_pkts[k] =  (meta, data) 
                
                tx_list+= slot_pkts 
                    
            
        frame_num +=1
     
        
        return frame_num, packet_count, tx_list, app_in, dropped_pkts
    
    def make_feedback_payload(self, mac_config, pktCode, frame_ts): 
        '''
        Generate the (meta,data) tuple for a single keepalive packet
        
        This combines the input parameters into the metadata and packet payload required
        for a valid keepalive packet. 
        
        Keyword Arguments:
        
        mac_config      (dict) mac state machine configuration info. Must contain at
                               minimum the following:
          fs           (float) sample rate at the output of the modulator
          macCode        (int) MAC code to add to header
          my_id          (int) MAC address of this node
          phyCode        (int) PHY code to add to header
          pre_guard    (float) time in seconds to reserve at the start of a slot                          
        pktCode          (int) packet type code to add to header
                                    
        Returns:
        (pktCode, payload)
        pktCode is as described above
        payload is a binary packing of the following format:
            a series of 16 bit pairs, one pair for each packet received in the
            previous frame. The first element is the packetID of the received packet. The
            second element is the sourceID of the received packet. 
            
        '''  
        
        frame_tuples = [ (key, time_spec_t(val["t0"])) for key,val in self.frame_history.items()]
    
        # sort by timestamp
        frame_tuples.sort( key=itemgetter(1)) 
        frame_times = [el[1] for el in frame_tuples]
        
        # get the current timestamp, but subtract off 10 samples worth of time to ensure
        # precision issues don't cause us to dither at slot boundaries
        
        timestamp = frame_ts - mac_config["lead_limit"] - 10.0/mac_config["fs"]
        # find frame num and slot num for the current real time
        end_frame_num, slot_num = self.timestamp_to_slot_and_frame(timestamp,
                                                                   frame_tuples, 
                                                                   frame_times)
        
        # hard limit parameters to 0 to prevent crashes when the timestamp doesn't occur 
        # in a frame the state machine knows about
        if end_frame_num is not None:         
            start_frame_num = max(end_frame_num-1,0)
            end_frame_num = max(end_frame_num, 0)
            slot_num = max(slot_num, 0)
        else:
            start_frame_num = 0
            end_frame_num = 0
            slot_num = 0
            
        format_str = 'HHHH'
        
        # add header to describe what time period this feedback packet covers
        feedback_region_str = struct.pack(format_str, start_frame_num, slot_num, 
                                          end_frame_num, slot_num)
        
             
        if "pktlist" in self.slot_stat_history and len(self.slot_stat_history["pktlist"]) > 0:
            # pack the list of tuples as a series of 16 bit unsigned ints
            for stat in self.slot_stat_history["pktlist"]:
                self.dev_log.info("acking packet number %i from node %i",stat.packetid, stat.sourceID )
            
            
            format_str = 'HH'* len(self.slot_stat_history["pktlist"])
            
            payload = struct.pack(format_str, *chain(*self.slot_stat_history["pktlist"]))
            
            self.dev_log.debug("made feedback payload for slot stat history %s",self.slot_stat_history["pktlist"] )

        else:
            # if no packets to report, payload is empty
            payload = ''
        
#        # preallocate space in the payload for the class specific header fields
#        default_fields = (0,)*self.slot_manager_header_num_fields
#        payload = self.pack_slot_manager_header(self.SlotManagerHeaderTuple(*default_fields), 
#                                                payload)
        
        return (pktCode, feedback_region_str + payload)
    
    
    
    def acquire_sync(self,frame_config, current_ts, mac_config, reset):
        
        
        inp = {"current_ts":current_ts,
               "reset":reset,
               }
        last_beacon_chan = self.beacon_channel
        
        if self.beacon_hopping_enabled:
            outp = self.beacon_sm.step( (inp, False) )
        
            self.beacon_channel = outp["beacon_chan"]
            
        outp = self.rf_sm.step( (inp,False) )
        rf_freq = outp["rf_freq"]
        
        new_frame_config = {
                            "t0":current_ts,
                            "frame_len":self.sync_frame_len,
                            "slots":[SlotParamTuple(owner=mac_config["base_id"], 
                                                    len=self.sync_frame_len, 
                                                    offset=0,
                                                    type='beacon',
                                                    rf_freq=rf_freq,
                                                    bb_freq=self.beacon_channel,
                                                    bw=0,
                                                    tx_gain=0)]}
        
        is_updated =  ((frame_config is None) or 
                       (frame_config["slots"][0].rf_freq != rf_freq) or
                       (last_beacon_chan != self.beacon_channel))
        
        if is_updated and frame_config is not None:
            self.dev_log.info("New Sync schedule: rf freq is %f, beacon_chan is %i", 
                              frame_config["slots"][0].rf_freq,
                              self.beacon_channel)

        uhd_cmd_tuple_list = [(current_ts, rf_freq, "txrx_tune")]
        
        return new_frame_config, is_updated, uhd_cmd_tuple_list
 
    def compute_frame(self, frame_num):
        '''
        Overload compute_frame for beacon hopper
        '''
        if self.current_schedule is None:
            frame_config = None
        else:
            frame_config = self.current_schedule.compute_frame(frame_num)
            self.frame_history[frame_num] = deepcopy(frame_config)
            
        if self.beacon_hopping_enabled:    
            for k, slot in enumerate(frame_config["slots"]):    
                if slot.type == "beacon":
                    frame_config["slots"][k] = slot._replace(bb_freq=self.beacon_channel)
            
        return frame_config            

    def append_my_settings(self, indent_level, opts_xml):
        
        # add components
        opts_xml += "%s<rf_hopper>\n"%(indent_level*'\t')
        indent_level+=1
        opts_xml = self.rf_sm.append_my_settings(indent_level, opts_xml) 
        indent_level-=1
        opts_xml += "%s</rf_hopper>\n"%(indent_level*'\t')
           
        opts_xml = super(mobile_slot_manager_ber_feedback, self).append_my_settings(indent_level,
                                                                                    opts_xml)  
    
        return opts_xml
    
    @staticmethod     
    def add_options(normal, expert):
        
        MobileSlotManager.add_options(normal, expert)
        
        frame_rf_hopper_mobile.add_options(normal, expert)
        beacon_hopper_mobile.add_options(normal, expert)
        
        
    def log_my_settings(self, indent_level, logger): 
        
        # slot manager section start
        logger.info("%s<slot_manager>", indent_level*'\t')
        indent_level += 1
        
        params = {"name":self.__class__.__name__}
        opts_xml = dict_to_xml(params, indent_level)
        
        opts_xml = self.append_my_settings(indent_level, opts_xml)
        logger.info(opts_xml)
        
        # slot manager section end
        indent_level -= 1
        logger.info("%s</slot_manager>", indent_level*'\t')        

#=========================================================================================
# Utility class for shared code for agent wrapper protocol manager 
#=========================================================================================
class shared_agent_protocol_manager(object):
    '''
    Utility class for shared code between the mobile and base. Note that you should
    put this class first in the inheritance list if you want member functions declared 
    in this class to 'win' in name resolution when resolving member functions that exist
    in this class as well as other classes in the inheritance list
    '''
    PacketStatTuple = namedtuple('PacketStatTuple', 'packetid sourceID')
    
    def setup_headers(self, options):
        
        self.slot_manager_header_format = 'II'
        self.slot_manager_header_names = 'slot_total_bytes slot_payload_bytes'

        # update the named tuple used in unpacking headers
        self.SlotManagerHeaderTuple = namedtuple('SlotManagerHeaderTuple', 
                                                 self.slot_manager_header_names)
        
        # finally calculate the length of the class specific header
        self.slot_manager_header_len = struct.calcsize(self.slot_manager_header_format)
        self.slot_manager_header_num_fields = len(self.SlotManagerHeaderTuple._fields)

    def make_slot_manager_header_tuple(self, meta, data):
        '''
        Return a header tuple initialized with zeros. The header fields will need to
        be filled in after the slot is filled in, so this will be a placeholder
        '''
       
        new_tup = self.SlotManagerHeaderTuple(slot_total_bytes=0,
                                              slot_payload_bytes=0,)
        return new_tup

    @staticmethod
    def configure_action_space(options,fs):
        
        all_addresses = options.agent_mac_address_mapping
        options.agent_mac_address_mapping = [int(x) for x in all_addresses.split(',')]
        
        #TODO: stop hard coding directory, file, and set names
        # set up actions
        pfs = pat_sched()
#        pattern_set = pfs.load_pattern_set_from_file(pattern_dir="./test_import", 
#                                                     pattern_file="pattern_group1", 
#                                                     set_name="SET_01", 
#                                                     fs=self.fs)

        pattern_set = pfs.load_pattern_set_from_file(pattern_file=options.agent_pattern_file, 
                                                     set_name=options.agent_pattern_set, 
                                                     )        
        if len(options.rf_frequency_list) > 0:
            rf_freq = [float(x) + float(options.rf_tx_freq) for x in options.rf_frequency_list.split(',')]
        else:
            rf_freq = list(set([options.rf_tx_freq, options.rf_rx_freq]))
            
        # store action space to class variable
        pfs.store_action_space(pattern_set=pattern_set, 
                               owner_ids=options.agent_mac_address_mapping,
                               rf_freqs=rf_freq)        
         
      
#=========================================================================================
# higher level control state machines
#=========================================================================================
class reinforcement_learner(SM):
    """
    Simple implementation of state machine that decides between exploring a space and 
    exploiting what it already knows about the space
    """
    startState = None
    dev_log = None
    _db = None
    def __init__(self, types_to_ints, options, link_ids = None, plotting=False, fig_plotter=None, 
                 sync_timeout=float('inf')):
        self.startState = 'init'
        self.plotting = plotting
        self.dev_log = logging.getLogger('developer')
    
        self.slot_learning_window = options.berf_stats_sense_window
        self.initial_explore_frames = options.berf_initial_explore_duration
        self.learning_state_duration = options.berf_epoch_duration
        self.learning_epsilon = options.greedy_epsilon
        self.learning_rate = options.learning_rate
    
        self.slot_exploration_alg = options.berf_exploration_protocol
        self.types_to_ints = types_to_ints
        
        # if this is not inf, the reinforment learner should verify that it has
        # received at least one packet from any mobile over the last sync_timeout_frames  
        # before storing results for learning
        self.sync_timeout_frames = sync_timeout
        
        # take valid frequency list from rf_frequency list if using hopping
        self.rf_frequency_list = [float(x) + float(options.rf_tx_freq) for x in options.rf_frequency_list.split(',')]
        
        if len(options.digital_freq_hop_guard_channels) > 0:
            self.guard_channels = [ int(x) for x in options.digital_freq_hop_guard_channels.split(',')]
        else:
            self.guard_channels = []
            
        # get the ll_logging set of logs so we have access to the state log
        self.ll_logging = lincolnlog.LincolnLog(__name__)
        self.statelog = self.ll_logging._statelog    
    
    @staticmethod
    def initialize_database_table(db_int):
        
        drop_tables_sql = """
        DROP TABLE IF EXISTS link_decisions;
        DROP TABLE IF EXISTS link_masks;
        DROP TABLE IF EXISTS link_ids;
        DROP TABLE IF EXISTS scenario_config;
        """
        
        link_decisions_table_sql = """
        CREATE TABLE IF NOT EXISTS link_decisions(
            frame_num INTEGER NOT NULL,
            owner INTEGER NOT NULL,
            link_num INTEGER NOT NULL,
            link_type TEXT NOT NULL,
            task TEXT NOT NULL,
            decision_order INTEGER NOT NULL,
            slot_num INTEGER NOT NULL,
            channel_num INTEGER NOT NULL,
            rf_freq REAL NOT NULL,
            data TEXT NOT NULL,
            PRIMARY KEY (frame_num, owner, link_num, link_type),
            -- FOREIGN KEY(frame_num, owner, link_num, link_type) REFERENCES 
            --     link_masks(frame_num, owner, link_num, link_type),
            FOREIGN KEY (frame_num) REFERENCES frame_nums(frame_num) ON DELETE CASCADE
            );
        """
        
        link_masks_table_sql = """
        CREATE TABLE IF NOT EXISTS link_masks(
            frame_num INTEGER NOT NULL,
            owner INTEGER NOT NULL,
            link_num INTEGER NOT NULL,
            link_type TEXT NOT NULL,
            data TEXT NOT NULL,
            PRIMARY KEY (frame_num, owner, link_num, link_type),
            FOREIGN KEY (frame_num) REFERENCES frame_nums(frame_num) ON DELETE CASCADE
            );   
        """
        
        link_ids_sql = """
        CREATE TABLE IF NOT EXISTS link_ids(
            owner INTEGER NOT NULL,
            link_num INTEGER NOT NULL,
            PRIMARY KEY (owner, link_num)
        );
        """
        
        scen_config_sql = """
        CREATE TABLE IF NOT EXISTS scenario_config(
            scen_id INTEGER PRIMARY KEY NOT NULL,
            num_freq_slots INTEGER NOT NULL,
            num_time_slots INTEGER NOT NULL
            );
        """
        
        with db_int.con as c:
            c.executescript(drop_tables_sql)
            c.executescript(link_decisions_table_sql)
            c.executescript(link_masks_table_sql)        
            c.executescript(link_ids_sql)
            c.executescript(scen_config_sql)  
    
    
    @staticmethod
    def store_link_ids(db_int, link_ids):
        
        with db_int.con as c:
            c.executemany("""
            INSERT INTO link_ids
                (owner, link_num) values
                (?,?)
            """, link_ids)
        
    
    @staticmethod
    def store_scen_config(db_int, num_freq_slots, num_time_slots):
        
        with db_int.con as c:
            c.execute("""
            INSERT INTO scenario_config
                (num_freq_slots, num_time_slots) values
                (?,?)
            """, (num_freq_slots, num_time_slots))
            
        pass
        
    @staticmethod    
    def initialize_figures(link_ids, num_freq_slots, num_time_slots):
        fig = plt.figure()
        ax_handles = {}
        mesh_handles = {}
        
        
        # TODO: pull relevant info from database

        num_links = len(link_ids) 
        mask_vals = np.zeros((num_freq_slots, num_time_slots))
        
        for k, (peer_id, link_num) in enumerate(link_ids):
            key = (peer_id, link_num, 'upmask')
            ind = np.ravel_multi_index( (0,k), (4,num_links)) +1 # +1 for matlab
            ax_handles[key] = fig.add_subplot(4,num_links,ind)
            mesh_handles[key] = ax_handles[key].pcolormesh(mask_vals, edgecolors="black")
            mesh_handles[key].set_clim(0,1)
            
            ax_handles[key].set_xlabel('slots')
            ax_handles[key].set_ylabel('channels')
            ax_handles[key].set_title('id %i:%i uplink mask'%(peer_id, link_num))
                   
            # force labels to integers
            ya = ax_handles[key].get_yaxis()
            ya.set_major_locator(MaxNLocator(integer=True))
            locs = ax_handles[key].get_yticks()
            ax_handles[key].set_yticks(locs, map(lambda x: "%i" % x, locs))

            
            key = (peer_id, link_num, 'uplink')
            ind = np.ravel_multi_index( (1,k), (4,num_links)) +1 # +1 for matlab
            ax_handles[key] = fig.add_subplot(4,num_links, ind )
            mesh_handles[key] = ax_handles[key].pcolormesh(mask_vals, edgecolors="black")
            mesh_handles[key].set_clim(0,1)
            ax_handles[key].set_xlabel('slots')
            ax_handles[key].set_ylabel('channels')
            ax_handles[key].set_title('id %i:%i uplink'%(peer_id, link_num))
            
            # force labels to integers
            ya = ax_handles[key].get_yaxis()
            ya.set_major_locator(MaxNLocator(integer=True))
            locs = ax_handles[key].get_yticks()
            ax_handles[key].set_yticks(locs, map(lambda x: "%i" % x, locs))
            
            key = (peer_id, link_num, 'downmask')
            ind = np.ravel_multi_index( (2,k), (4,num_links)) +1 # +1 for matlab
            ax_handles[key] = fig.add_subplot(4,num_links,ind)
            mesh_handles[key] = ax_handles[key].pcolormesh(mask_vals, edgecolors="black")
            mesh_handles[key].set_clim(0,1)
            ax_handles[key].set_xlabel('slots')
            ax_handles[key].set_ylabel('channels')
            ax_handles[key].set_title('id %i:%i downlink mask'%(peer_id, link_num))
            
            # force labels to integers
            ya = ax_handles[key].get_yaxis()
            ya.set_major_locator(MaxNLocator(integer=True))
            locs = ax_handles[key].get_yticks()
            ax_handles[key].set_yticks(locs, map(lambda x: "%i" % x, locs))
            
            key = (peer_id, link_num, 'downlink')
            ind = np.ravel_multi_index( (3,k), (4,num_links)) +1 # +1 for matlab
            ax_handles[key] = fig.add_subplot(4,num_links,ind)
            mesh_handles[key] = ax_handles[key].pcolormesh(mask_vals, edgecolors="black")
            mesh_handles[key].set_clim(0,1)
            ax_handles[key].set_xlabel('slots')
            ax_handles[key].set_ylabel('channels')
            ax_handles[key].set_title('id %i:%i downlink'%(peer_id, link_num))
            
            # force labels to integers
            ya = ax_handles[key].get_yaxis()
            ya.set_major_locator(MaxNLocator(integer=True))
            locs = ax_handles[key].get_yticks()
            ax_handles[key].set_yticks(locs, map(lambda x: "%i" % x, locs))
    
        fig.tight_layout()
               
        return fig, ax_handles, mesh_handles
    
    def getNextValues(self, state, inp):
        """
        handle inputs and determine next value of outputs
        """
        next_state = self.getNextState(state, inp)
        
        link_ids = inp["link_ids"]
        
        state_counter = inp["state_counter"]
        
        num_freq_slots = inp["num_freq_slots"]
        num_time_slots = inp["num_time_slots"]
        beacon_assignments = inp["beacon_slots"]
        old_link_summary=inp["link_summary"]
        slot_assignments = beacon_assignments
        rf_freq = inp["rf_freq"]
        

        # handle first state machine iteration
        if state == "init":
            self._db = inp["database"]
            state_counter = self.initial_explore_frames-1
            
            if link_ids is None:
                # initialize link ids based on one uplink and one downlink per peer id
                link_ids = [ (peer_id, 0 ) for peer_id in inp["peer_ids"]]
                
            # initialize possible link directions assuming bidirectional comms to each 
            # node
            self.link_dirs = []
            self.link_dirs.extend([ (peer_id, "uplink") for peer_id in inp["peer_ids"]])
            self.link_dirs.extend([ (peer_id, "downlink") for peer_id in inp["peer_ids"]]) 
            new_link_summary = {}
            
            
            for (peer_id, link_dir) in self.link_dirs:
                for freq in self.rf_frequency_list:
                    
                    link = (peer_id, link_dir, freq)
                    self.dev_log.debug("adding link %s", link)
                    # initialize link summaries
                    new_link_summary[link] = ma.array(ma.empty( (num_freq_slots, 
                                                                 num_time_slots) ),
                                                                 mask=True) 
                
            downlink_states = OrderedDict()
            uplink_states = OrderedDict()
            for link_id in link_ids:
                downlink_states[link_id] = "explore"
                uplink_states[link_id] = "explore"
            
            # make a masked array view to track what slots are available for assignment
            valid_slots = ma.masked_array(np.ones((num_freq_slots, num_time_slots)))  
            
            # mask the beacon slots
            valid_slots[self.guard_channels,:] = ma.masked
                
            
            # mask the beacon slots
            for slot_num in slot_assignments:
                valid_slots[:,slot_num] = ma.masked  
                
            dl_explorers = [ (key, "downlink") for key, value in downlink_states.iteritems() 
                             if value == "explore"]
            ul_explorers = [ (key, "uplink") for key, value in uplink_states.iteritems() 
                             if value == "explore"] 
            
            # now assign random slots to explorers.
            valid_slots, slot_assignments = self.assign_random_slots(inp["frame_num"],
                                                                     ul_explorers,
                                                                     new_link_summary, 
                                                                     valid_slots, 
                                                                     slot_assignments,
                                                                     rf_freq,
                                                                     'explore')
            
            valid_slots, slot_assignments = self.assign_random_slots(inp["frame_num"],
                                                                     dl_explorers,
                                                                     new_link_summary, 
                                                                     valid_slots, 
                                                                     slot_assignments,
                                                                     rf_freq,
                                                                     'explore')
            
        
        # if in the middle of a state duration, keep counting
        elif state == "countdown":
            state_counter -=1
            new_link_summary = deepcopy(old_link_summary)
        # if the state duration is over, choose what to do for each link    
        elif state == "reset":
            
            state_counter = self.learning_state_duration-1
            
            downlink_states = OrderedDict()
            uplink_states = OrderedDict()
            
            
            # make a masked array view to track what slots are available for assignment
            valid_slots = ma.masked_array(np.ones((num_freq_slots, num_time_slots)))
            
            # mask the beacon slots
            valid_slots[self.guard_channels,:] = ma.masked
            
            # mask the beacon slots
            for slot_num in slot_assignments:
                valid_slots[:,slot_num] = ma.masked  
          
            # if supposed to be checking whether there are mobiles recently communicating,
            # check for recent comms and set a flag accordingly  
            if self.sync_timeout_frames < float('inf'):
                num_packets = self._db.count_recent_rx_packets(self.sync_timeout_frames, 
                                                               self.types_to_ints)
                had_recent_traffic = num_packets > 0
            else:
                had_recent_traffic = None
                
                
            # decide who is exploring and who is exploiting
            for link_id in link_ids:
                downlink_states[link_id] = self.choose_explore_or_exploit(had_recent_traffic)
                uplink_states[link_id] = self.choose_explore_or_exploit(had_recent_traffic)
                
            # sort out into explorers and exploiters so we can service the exploit nodes
            # first
            dl_exploiters = [ (key, "downlink") for key, value in downlink_states.iteritems() 
                             if value == "exploit"]
            ul_exploiters = [ (key, "uplink") for key, value in uplink_states.iteritems() 
                             if value == "exploit"]
            dl_explorers = [ (key, "downlink") for key, value in downlink_states.iteritems() 
                             if value == "explore"]
            ul_explorers = [ (key, "uplink") for key, value in uplink_states.iteritems() 
                             if value == "explore"]
              
            # compute new link state summary unless we're hopping without sync
            if had_recent_traffic is None or had_recent_traffic:
                new_link_summary = self.update_summary(old_link_summary, 
                                                       inp["peer_ids"], 
                                                       inp["base_id"], 
                                                       num_freq_slots,
                                                       num_time_slots,
                                                       rf_freq)
            else:
                new_link_summary=old_link_summary
                
            # uplink exploiters get first dibs since the uplink slots are most critical to
            # algorithm performance
            valid_slots, slot_assignments = self.assign_optimal_slots(inp["frame_num"],
                                                                      ul_exploiters,
                                                                      new_link_summary, 
                                                                      valid_slots, 
                                                                      slot_assignments,
                                                                      rf_freq,
                                                                      'exploit')
            # downlink exploiters get to go next
            valid_slots, slot_assignments = self.assign_optimal_slots(inp["frame_num"],
                                                                      dl_exploiters,
                                                                      new_link_summary, 
                                                                      valid_slots, 
                                                                      slot_assignments,
                                                                      rf_freq,
                                                                      'exploit')
            
            
            # TODO: Come up with a reasonable and general way to assign slots randomly
            # when the number of slots requested by the network exceeds the number of 
            # slots we actually have to give. Ie, how do we make sure nodes have an 
            # uplink for each downlink? 
            
            # now assign random slots to explorers.
            valid_slots, slot_assignments = self.assign_random_slots(inp["frame_num"],
                                                                     ul_explorers,
                                                                     new_link_summary, 
                                                                     valid_slots, 
                                                                     slot_assignments,
                                                                     rf_freq,
                                                                     'explore')
            
            valid_slots, slot_assignments = self.assign_random_slots(inp["frame_num"],
                                                                     dl_explorers,
                                                                     new_link_summary, 
                                                                     valid_slots, 
                                                                     slot_assignments,
                                                                     rf_freq,
                                                                     'explore')
            
             
        outp = {"link_ids":link_ids,
                "link_summary":new_link_summary,
                "slot_assignments":slot_assignments,
                "state_counter":state_counter,}
        
        return (next_state, outp)
            
    def getNextState(self, state, inp):
        """
        Pick the next state whenever the state counter expires
        """
        
        state_counter = inp["state_counter"]
        
        # is this the first iteration? If so, switch to the initial exploration state.
        if state == "init":
            next_state = "countdown"

        elif state == "countdown":
            if state_counter-1 > 0:
                next_state = state
            else:
                next_state = "reset"
        # this is in reset, go back to countdown
        else:
            next_state = "countdown"
             
        return next_state
                
    def update_summary(self, old_summary, peer_ids, base_id, num_freq_slots, 
                       num_time_slots, rf_freq):
        """
        update the performance summary of the node. alpha is the forgetting factor applied
        to old data
        """        
        
        # copy the old summary into the new sumamry. The relevant part of new_summary
        # will be overwritten in the following loops        
        new_summary = deepcopy(old_summary)
        
        for (peer_id, direction) in self.link_dirs:
            
            # make new empty masked array for peer_id, direction combo
            new_summary[(peer_id, direction, rf_freq)] = ma.array(ma.empty((num_freq_slots, 
                                                                            num_time_slots)),
                                                                  mask=True)
            
            if direction == "uplink":
                from_id = peer_id
                to_id = base_id
            else:
                from_id = base_id
                to_id = peer_id
                
            results = self._db.get_slot_sums(to_id, from_id, self.slot_learning_window,
                                             rf_freq)
            pass_fails = {}
            for r in results:
                self.dev_log.debug("Processing result set: %s", tuple(r))
                # initialize storage for intermediate results for each slot and channel
                # number in the results
                if (r["channel_num"],r["slot_num"]) not in pass_fails:
                    pass_fails[ (r["channel_num"],r["slot_num"])] = {'pass':0, 'fail':0}  
                # store intermediate result
                pass_fails[ (r["channel_num"],r["slot_num"])][r["status"]] = float(
                  r["slot_total_bits"])    
            
            # compute BER for each channel and slot in results (This also sets mask in 
            # the new_summary slot appropriately)
            for (row,col), bits in pass_fails.iteritems():
                #self.dev_log.debug("updating chan %i, timeslot %i for slot_perf:\n%s",
                #                   row, col, slot_perf)
                if bits["fail"]+bits["pass"]>0:
                    new_summary[ (peer_id, direction, rf_freq)][row,col] = bits["fail"]/(bits["fail"]+bits["pass"])    
            
            
            for num, key in enumerate(old_summary.keys()):
                self.dev_log.debug("old summary key %i:  %s",num, key)
                self.dev_log.debug("old summary val %s", old_summary[key])
            for num, key in enumerate(new_summary.keys()):
                self.dev_log.debug("new summary key %i:  %s",num, key)
                self.dev_log.debug("new summary val %s", new_summary[key])    
             
            new_summary[ (peer_id, direction,rf_freq)] = self.combine_arrays(old_summary[ (peer_id, direction, rf_freq)], 
                                                                new_summary[ (peer_id, direction, rf_freq)],
                                                                self.learning_rate)
            
            for num, key in enumerate(new_summary.keys()):
                self.dev_log.debug("combined summary key %i:  %s",num, key)
                self.dev_log.debug("combined summary val %s", new_summary[key])  
    
        return new_summary
    
    @staticmethod
    def combine_arrays(a,b,alpha):
        """
        Where elements exist in both a and b, apply the forgetting factor to the sum. 
        
        ie, (1-alpha)*a + alpha*b
        Where an element exists in only one array, use the unweighted value
        """
        c = (1-alpha)*a + alpha*b
        ab_xor_vals = ma.array(np.zeros(ma.shape(a)), mask=True)
        
        # assign the elements from b that are not masked in b but masked in a into ab_xor_vals
        ab_xor_vals = ma.where(ma.getmask(a) & ~ma.getmask(b), b, ab_xor_vals )
        
        # assign the elements from a that are not masked in a but masked in b into ab_xor_vals
        ab_xor_vals = ma.where(ma.getmask(b) & ~ma.getmask(a), a, ab_xor_vals )
        
        c = reinforcement_learner.masked_sum( c, ab_xor_vals)
        
        return c
    
    @staticmethod     
    def masked_sum(a,b):
        """
        Compute the sum of two masked arrays, where elements in the exlusive OR of the
        two masks are assumed to be zero
        """
        return ma.masked_array(a.filled(0)+b.filled(0), (ma.getmask(a) & ma.getmask(b)))   
         
    def choose_explore_or_exploit(self, had_recent_traffic=None):
        """
        Decide whether to explore the space or exploit what we know
        """
        
        # if we care about recent traffic and there's been no recent traffic
        if had_recent_traffic is not None and (not had_recent_traffic):
            # just explore
            return "explore"
        else: 
            throw = random.random()
             
            if throw > self.learning_epsilon:
                return "exploit"
            else:
                return "explore"
        
    def assign_optimal_slots(self, frame_num, link_list, link_summary, valid_slots, 
                             slot_assignments, rf_freq, task):
        """
        pick an available slot that has the lowest ber
        """
        
        # shuffle order of elements so there's no cyclical behavior
        random.shuffle(link_list)
        
        for ( (peer_id, link_num), link_dir) in link_list:
            ber_table = link_summary[(peer_id, link_dir, rf_freq) ]
            masked_bers = valid_slots*ber_table
            
            # plot the mask if plotting is on
            if self.plotting:
                self.store_mask(frame_num, peer_id, link_num, link_dir, valid_slots)
#                self.plot_mask(peer_id, link_num, link_dir, valid_slots)
            
            # check if all the valid ber values are already masked
            if ma.getmask(masked_bers).all():
                # if all valid bers are masked, see if there are any unmasked slots at all
                if ma.getmask(valid_slots).all():
                    # if everything is masked, we can't do anything. 
                    pass
                # if there are unmasked slots, pick a tile at random from an unmasked slot
                else:
                    channel_num, slot_num = self.pick_random_slot(peer_id, link_dir, 
                                                                  valid_slots, 
                                                                  slot_assignments)
                    
                    # store the new slot assignment
                    slot_assignments[slot_num] = GridUpdateTuple(owner=peer_id, 
                                                                 type=link_dir, 
                                                                 channel_num=channel_num,
                                                                 rf_freq=rf_freq,
                                                                 order=len(slot_assignments))
                    # update the valid slots mask
                    valid_slots[:,slot_num] = ma.masked
                    
                    if self.plotting:
                        self.store_bers(frame_num, peer_id, link_num, link_dir, 
                                        link_summary[(peer_id, link_dir, rf_freq) ], 
                                        slot_assignments[slot_num], slot_num, task)
                        
                        self.log_bers(frame_num, peer_id, link_num, link_dir, 
                                        link_summary[(peer_id, link_dir, rf_freq) ], 
                                        slot_assignments[slot_num], slot_num, task) 
                 
            # if there are unmasked ber values, pick the optimal value        
            else:
                flat_ind = ma.argmin(masked_bers)
                (channel_num, slot_num) = np.unravel_index(flat_ind, 
                                                           ma.shape(valid_slots))
                
                # store the new slot assignment
                slot_assignments[slot_num] = GridUpdateTuple(owner=peer_id, 
                                                             type=link_dir, 
                                                             channel_num=channel_num,
                                                             rf_freq=rf_freq,
                                                             order=len(slot_assignments))
                
                # update the valid slots mask
                valid_slots[:,slot_num] = ma.masked
                
                if self.plotting:
                    self.store_bers(frame_num, peer_id, link_num, link_dir, 
                                    link_summary[(peer_id, link_dir, rf_freq) ], 
                                    slot_assignments[slot_num], slot_num, task)
                    
                    self.log_bers(frame_num, peer_id, link_num, link_dir, 
                                        link_summary[(peer_id, link_dir, rf_freq) ], 
                                        slot_assignments[slot_num], slot_num, task)                    
          
    
        return valid_slots, slot_assignments
    
    def assign_random_slots(self, frame_num, link_list, link_summary, valid_slots, 
                            slot_assignments, rf_freq, task):
        """
        pick an available slot at random
        """
        
        
        if self.slot_exploration_alg == "random":
            # shuffle order of elements so there's no cyclical behavior
            random.shuffle(link_list)
            
        
        for ((peer_id, link_num), link_dir) in link_list:
            
            # plot the mask if plotting is on
            if self.plotting:
                self.store_mask(frame_num, peer_id, link_num, link_dir, valid_slots)
#                self.plot_mask(peer_id, link_num, link_dir, valid_slots)
            
            if self.slot_exploration_alg == "random":
                channel_num, slot_num = self.pick_random_slot(peer_id, link_dir, 
                                                              valid_slots, 
                                                              slot_assignments)
            elif self.slot_exploration_alg == "increment":
                channel_num, slot_num = self.pick_increment_slot(peer_id, link_dir, 
                                                                 valid_slots, 
                                                                 slot_assignments)
            
            # store the new slot assignment
            slot_assignments[slot_num] = GridUpdateTuple(owner=peer_id, 
                                                         type=link_dir, 
                                                         channel_num=channel_num,
                                                         rf_freq=rf_freq,
                                                         order=len(slot_assignments))
        
            # update the valid slots mask
            valid_slots[:,slot_num] = ma.masked
            
            if self.plotting:
                self.store_bers(frame_num, peer_id, link_num, link_dir, 
                                link_summary[(peer_id, link_dir, rf_freq) ], 
                                slot_assignments[slot_num], slot_num, task)
                
                self.log_bers(frame_num, peer_id, link_num, link_dir, 
                                        link_summary[(peer_id, link_dir, rf_freq) ], 
                                        slot_assignments[slot_num], slot_num, task)  
                
    
        return valid_slots, slot_assignments   

        
    def pick_random_slot(self,peer_id, link_dir, valid_slots, slot_assignments):
        
        # get a list of all the valid row,column combinations as two lists of length N    
        (channel_nums, slot_nums) = valid_slots.nonzero()
        
        # pick one at random
        rand_ind = random.randrange(len(channel_nums))
        

        return channel_nums[rand_ind], slot_nums[rand_ind]


    def pick_increment_slot(self,peer_id, link_dir, valid_slots, slot_assignments):
        
        # get a list of all the valid row,column combinations as two lists of length N    
        (channel_nums, slot_nums) = valid_slots.nonzero()
        
        # pick the first available slot and base the channel number off of that
        slot_num = slot_nums[0]
        unique_chans = sorted(set(channel_nums))
        channel_num = unique_chans[ slot_num % len(unique_chans) ]
        
        

        return channel_num, slot_num    
    
    #@timeit
    def store_mask(self, frame_num, peer_id, link_num, link_dir, valid_slots):
           
        with self._db.con as c:
            try:
                # store this grid update to database    
                c.execute("""
                insert into link_masks
                (frame_num, owner, link_num, link_type, data) values
                (?,?,?,?,?)""",
                (frame_num, peer_id, link_num, link_dir, cPickle.dumps(valid_slots)))
                
            except sqlite3.IntegrityError as err:
                self.dev_log.exception("Integrity error inserting mask for frame %i", frame_num)


    
    #@timeit
    def store_bers(self, frame_num, peer_id, link_num, link_dir, ber_table, slot_assignment, slot_num, task):
        
        # store this grid update to database
        with self._db.con as c:    
            c.execute("""
            insert into link_decisions
            (frame_num, owner, link_num, link_type, task, decision_order, 
             slot_num, channel_num, rf_freq, data) values
            (?,?,?,?,?,?,?,?,?,?)
            """,
            (frame_num, peer_id, link_num, link_dir, task, slot_assignment.order, 
             int(slot_num), int(slot_assignment.channel_num), slot_assignment.rf_freq, 
             cPickle.dumps(ber_table)))
            
    def log_bers(self, frame_num, peer_id, link_num, link_dir, ber_table, slot_assignment, slot_num, task):
        
        # store this grid update to the state log
        params = {"frame_num":frame_num,
                  "peer_id":peer_id, 
                  "link_num":link_num, 
                  "link_dir":link_dir, 
                  "task":task, 
                  "order":slot_assignment.order, 
                  "slot_num":int(slot_num), 
                  "channel_num":int(slot_assignment.channel_num), 
                  "rf_freq":slot_assignment.rf_freq, 
                  "ber_table":ber_table.tolist(),
                  }
        
        param_xml = dict_to_xml(params, 1)
        
        ber_log_xml = ("<ber_update>\n" + 
                       "%s\n" + 
                       "</ber_update>") % param_xml
                       
        self.statelog.info(ber_log_xml)
                    

    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "slot_learning_window":self.slot_learning_window,
                  "initial_explore_frames":self.initial_explore_frames,
                  "learning_state_duration":self.learning_state_duration,
                  "learning_epsilon":self.learning_epsilon,
                  "learning_rate":self.learning_rate,
                  "rf_frequency_list":self.rf_frequency_list,
                  "slot_exploration_alg":self.slot_exploration_alg}
        opts_xml += "\n" + dict_to_xml(params, indent_level)
        
        
        return opts_xml

    @staticmethod            
    def add_options(normal, expert):
        
        normal.add_option("--berf-stats-sense-window", type="int", default=10, 
                          help="Frames used to compute stats for the next decision " +
                               "[default=%default]")
        
        normal.add_option("--berf-initial-explore-duration", type="int", default=4, 
                          help="Frames to explore on the first iteration " +
                               "[default=%default]")
        
        normal.add_option("--berf-epoch-duration", type="int", default=4, 
                          help="Frames between new decisions " +
                               "[default=%default]")
        
        normal.add_option("--greedy-epsilon", type="float", default=0.1, 
                          help="Probablility of chosing a random location to explore " +
                               "instead of using the available location with lowest BER" +
                               " [default=%default]")
        
        normal.add_option("--learning-rate", type="float", default=.9, 
                          help="Weight on new data. Old data will be weighted by "
                               "(1 - learning-rate) [default=%default]")
        
        normal.add_option("--rf-frequency-list", type="string", 
                          default="720e6, 725e6",
                          help="list of valid rf frequencies the front end can tune to" +
                                " [default=%default]")
        
        
        normal.add_option("--berf-exploration-protocol", type="choice", 
                          choices=["random", "increment"], default="random",
                          help="Algorithm for assigning slots while exploring " + 
                               "[default=%default]")
        
        normal.add_option("--digital-freq-hop-guard-channels", type="string", 
                          default="",
                          help="list of channels the algorithm is forbidden from using" +
                                " [default=%default]")
        
class frame_rf_hopper_base(SM):
    """
    Simple implementation of state machine that hops the network when no mobile nodes are 
    detected for some number of frames
    """
    
    startState = None
    dev_log = None
    _db = None
    types_to_ints = None
    
    HopperState = namedtuple('HopperState', 'name rf_chan counter')
    
    def __init__(self, types_to_ints, frame_len, options):
        self.startState = self.HopperState(name="init", rf_chan=0, counter=0)
        
        self.dev_log = logging.getLogger('developer')
        self.types_to_ints = deepcopy(types_to_ints)
        
        
        # take valid frequency list from rf_frequency list if using hopping.
        self.rf_frequency_list = [float(x) + float(options.rf_tx_freq) for x in options.rf_frequency_list.split(',')]
  
        
        self.berf_base_rf_hop_rendezvous_frames = options.berf_base_rf_hop_rendezvous_frames
        
        self.min_rf_dwell = self.berf_base_rf_hop_rendezvous_frames

    def getNextValues(self, state, inp):
        """
        handle inputs and determine next value of outputs
        """
        
        # is this the first iteration? 
            
        
        if state.name == "init":
            self._db = inp["database"]
            next_state = self.HopperState(name="countdown", 
                                          rf_chan=0, 
                                          counter=self.min_rf_dwell-1)

        elif state.name == "countdown":
            if state.counter-1 > 0:
                next_state = state._replace(counter=state.counter-1)
            else:
                next_state = state._replace(name="switch_if_idle",
                                            counter=state.counter-1)
                
        # this is in reset, go back to countdown
        elif state.name == "switch_if_idle":
            
            num_packets = self._db.count_recent_rx_packets(self.min_rf_dwell, 
                                                           self.types_to_ints)
            
            if num_packets > 0:
                next_state = state
            else:
                num_rf_chans = len(self.rf_frequency_list)
                next_state = self.HopperState(name="countdown", 
                                              rf_chan=(state.rf_chan+1)%num_rf_chans, 
                                              counter=self.min_rf_dwell-1)
                
            
        outp = {
                "rf_freq":self.rf_frequency_list[next_state.rf_chan]
                }
        
        return (next_state, outp)
    

    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "berf_base_rf_hop_rendezvous_frames":self.berf_base_rf_hop_rendezvous_frames,
                  "rf_frequency_list":self.rf_frequency_list,
                  }
        opts_xml += "\n" + dict_to_xml(params, indent_level)
        
        
        return opts_xml
    
    @staticmethod
    def add_options(normal, expert):
        normal.add_option("--berf-base-rf-hop-rendezvous-frames", type='float', 
                          default=2.0,
                          help="The number of frames a base should wait " +
                               "before switching to the next rf frequency " +
                               "[default=%default]")
 
        normal.add_option("--rf-frequency-list", type="string", 
                          default="720e6, 725e6",
                          help="list of valid rf frequencies the front end can tune to" +
                                " [default=%default]")
        
    
    
class frame_rf_hopper_mobile(SM):
    """
    Simple implementation of state machine that hops the mobile when it can't get sync for
    some number of seconds
    """
    
    startState = None
    dev_log = None
    types_to_ints = None
    
    HopperState = namedtuple('HopperState', 'name rf_chan deadline')
    
    def __init__(self, types_to_ints, options):
        self.startState = self.HopperState(name="init", rf_chan=0, deadline=0)
        
        self.dev_log = logging.getLogger('developer')
        self.types_to_ints = deepcopy(types_to_ints)
        
        self.berf_mobile_rf_hop_rendezvous_interval = options.berf_mobile_rf_hop_rendezvous_interval
        
        # take valid frequency list from rf_frequency list if using hopping
        self.rf_frequency_list = [float(x) + float(options.rf_tx_freq) for x in options.rf_frequency_list.split(',')]
                
    def getNextValues(self, state, inp):
        """
        handle inputs and determine next value of outputs
        """
        
        current_ts = inp["current_ts"]
        timeout = self.berf_mobile_rf_hop_rendezvous_interval
        reset = inp["reset"]
        # is this the first iteration? 
        if state.name == "init":
            
            next_state = self.HopperState(name="countdown", 
                                          rf_chan=0, 
                                          deadline=current_ts+timeout)
        
        # else handle when not previously in sync
        elif state.name == "countdown":
            # is the state machine being reset?
            if reset == True:
                next_state = state._replace(deadline=current_ts+timeout)
                
            # is this past the sync deadline?    
            elif state.deadline <= inp["current_ts"]:
                # if so, set up a retune and reset the sync deadline
                num_rf_chans = len(self.rf_frequency_list)
                next_state = state._replace(rf_chan=(state.rf_chan+1)%num_rf_chans,
                                            deadline=current_ts+timeout)
            # otherwise keep waiting
            else:
                next_state = state
        
        
        outp = {
                "rf_freq":self.rf_frequency_list[next_state.rf_chan]
                }
        
        return (next_state, outp)
    
    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "berf_mobile_rf_hop_rendezvous_interval":self.berf_mobile_rf_hop_rendezvous_interval,
                  "rf_frequency_list":self.rf_frequency_list,
                  }
        opts_xml += "\n" + dict_to_xml(params, indent_level)
        
        
        return opts_xml    
    
    @staticmethod
    def add_options(normal, expert):

        normal.add_option("--berf-mobile-rf-hop-rendezvous-interval", type='float', 
                          default=2.0,
                          help="How long, in seconds, a mobile should dwell at a given " +
                               "rf frequency when it cannot detect beacons")
        
        normal.add_option("--rf-frequency-list", type="string", 
                          default="720e6, 725e6",
                          help="list of valid rf frequencies the front end can tune to" +
                                " [default=%default]")
               


class beacon_hopper_base(SM):
    """
    Simple implementation of state machine that hops the network when no mobile nodes are 
    detected for some number of frames
    """
    
    startState = None
    dev_log = None
    _db = None
    types_to_ints = None
    
    HopperState = namedtuple('HopperState', 'name beacon_chan counter')
    
    def __init__(self, types_to_ints, frame_len, options):
        self.startState = self.HopperState(name="init", beacon_chan=0, counter=0)
        
        self.dev_log = logging.getLogger('developer')
        self.types_to_ints = deepcopy(types_to_ints)
        
        self.beacon_hopping_enabled = options.berf_beacon_hopping_enabled
        
        if len(options.digital_freq_hop_guard_channels) > 0:
            self.guard_channels = [ int(x) for x in options.digital_freq_hop_guard_channels.split(',')]
        else:
            self.guard_channels = []
        
        # take valid frequency list from number_digital_channels list if using hopping. Otherwise,
        # use options.beacon_channel
        if options.berf_beacon_hopping_enabled:
            self.beacon_channel_list = range(options.digital_freq_hop_num_channels)
            self.beacon_channel_list = [c for c in self.beacon_channel_list 
                                        if c not in self.guard_channels]
        else:
            self.beacon_channel_list = [options.berf_beacon_channel]
        
        self.berf_base_beacon_hop_rendezvous_frames = options.berf_base_beacon_hop_rendezvous_frames
        self.berf_mobile_beacon_hop_rendezvous_interval = options.berf_mobile_beacon_hop_rendezvous_interval
        
        self.min_beacon_dwell = self.berf_base_beacon_hop_rendezvous_frames

    def getNextValues(self, state, inp):
        """
        handle inputs and determine next value of outputs
        """
        
        # is this the first iteration? 
            
        
        if state.name == "init":
            self._db = inp["database"]
            next_state = self.HopperState(name="countdown", 
                                          beacon_chan=0, 
                                          counter=self.min_beacon_dwell-1)

        elif state.name == "countdown":
            if state.counter-1 > 0:
                next_state = state._replace(counter=state.counter-1)
            else:
                next_state = state._replace(name="switch_if_idle",
                                            counter=state.counter-1)
                
        # this is in reset, go back to countdown
        elif state.name == "switch_if_idle":
            
            num_packets = self._db.count_recent_rx_packets(self.min_beacon_dwell, 
                                                           self.types_to_ints)
            
            if num_packets > 0:
                next_state = state
            else:
                num_beacon_chans = len(self.beacon_channel_list)
                next_state = self.HopperState(name="countdown", 
                                              beacon_chan=(state.beacon_chan+1)%num_beacon_chans, 
                                              counter=self.min_beacon_dwell-1)
                self.dev_log.info("base switching from beacon channel %i to channel %i",
                                  state.beacon_chan, next_state.beacon_chan)
                
        # if hopping is disabled, override the frequency channel choice
        if self.beacon_hopping_enabled == False:        
            next_state = next_state._replace(beacon_chan = 0)
            
        outp = {
                "beacon_chan":self.beacon_channel_list[next_state.beacon_chan]
                }
        
        return (next_state, outp)
    

    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "berf_base_beacon_hop_rendezvous_frames":self.berf_base_beacon_hop_rendezvous_frames,
                  "berf_mobile_beacon_hop_rendezvous_interval":self.berf_mobile_beacon_hop_rendezvous_interval,
                  "beacon_hopping_enabled":self.beacon_hopping_enabled,
                  }
        opts_xml += "\n" + dict_to_xml(params, indent_level)
        
        
        return opts_xml
    
    @staticmethod
    def add_options(normal, expert):
        normal.add_option("--berf-base-beacon-hop-rendezvous-frames", type='float', default=2.0,
                          help="The number of frames a base should wait " +
                               "before switching to the next beacon channel " +
                               "[default=%default]")
       
        normal.add_option("--berf-mobile-beacon-hop-rendezvous-interval", type='float', default=2.0,
                          help="How long, in seconds, a mobile should dwell at a given " +
                               "beacon channel when it cannot detect beacons")
        
        normal.add_option("--berf-beacon-hopping-enabled", type='int', default=0,
                          help="Enable or disable digital beacon hopping [default=%default]")
    
    
class beacon_hopper_mobile(SM):
    """
    Simple implementation of state machine that digitally hops the mobile when it can't 
    get sync for some number of seconds
    """
    
    startState = None
    dev_log = None
    types_to_ints = None
    
    HopperState = namedtuple('HopperState', 'name beacon_chan deadline')
    
    def __init__(self, types_to_ints, options):
        self.startState = self.HopperState(name="init", beacon_chan=0, deadline=0)
        
        self.dev_log = logging.getLogger('developer')
        self.types_to_ints = deepcopy(types_to_ints)
        
        self.berf_mobile_beacon_hop_rendezvous_interval = options.berf_mobile_beacon_hop_rendezvous_interval
        self.beacon_hopping_enabled = options.berf_beacon_hopping_enabled
        
        if len(options.digital_freq_hop_guard_channels) > 0:
            self.guard_channels = [ int(x) for x in options.digital_freq_hop_guard_channels.split(',')]
        else:
            self.guard_channels = []
        
        # take valid frequency list from number_digital_channels list if using hopping. Otherwise,
        # use options.beacon_channel
        if options.berf_beacon_hopping_enabled:
            self.beacon_channel_list = range(options.digital_freq_hop_num_channels)
            self.beacon_channel_list = [c for c in self.beacon_channel_list 
                                        if c not in self.guard_channels]
        else:
            self.beacon_channel_list = [options.berf_beacon_channel]
        
    def getNextValues(self, state, inp):
        """
        handle inputs and determine next value of outputs
        """
        
        current_ts = inp["current_ts"]
        timeout = self.berf_mobile_beacon_hop_rendezvous_interval
        reset = inp["reset"]
        # is this the first iteration? 
        if state.name == "init":
            
            next_state = self.HopperState(name="countdown", 
                                          beacon_chan=0, 
                                          deadline=current_ts+timeout)
        
        # else handle when not previously in sync
        elif state.name == "countdown":
            # is the state machine being reset?
            if reset == True:
                next_state = state._replace(deadline=current_ts+timeout)
                
            # is this past the sync deadline?    
            elif state.deadline <= inp["current_ts"]:
                # if so, set up a retune and reset the sync deadline
                num_beacon_chans = len(self.beacon_channel_list)
                next_state = state._replace(beacon_chan=(state.beacon_chan+1)%num_beacon_chans,
                                            deadline=current_ts+timeout)
                
                self.dev_log.info("mobile switching from beacon channel %i to channel %i",
                                  state.beacon_chan, next_state.beacon_chan)
            # otherwise keep waiting
            else:
                next_state = state
        
        
        # if hopping is disabled, override the frequency channel choice
        if self.beacon_hopping_enabled == False:        
            next_state = next_state._replace(beacon_chan = 0)
                
        outp = {
                "beacon_chan":self.beacon_channel_list[next_state.beacon_chan]
                }
        
        return (next_state, outp)
    
    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "berf_mobile_beacon_hop_rendezvous_interval":self.berf_mobile_beacon_hop_rendezvous_interval,
                  "beacon_hopping_enabled":self.beacon_hopping_enabled,
                  }
        opts_xml += "\n" + dict_to_xml(params, indent_level)
        
        
        return opts_xml    
    
    @staticmethod
    def add_options(normal, expert):

        normal.add_option("--berf-mobile-beacon-hop-rendezvous-interval", type='float', default=2.0,
                          help="How long, in seconds, a mobile should dwell at a given " +
                               "beacon channel when it cannot detect beacons")
        
        normal.add_option("--berf-beacon-hopping-enabled", type='int', default=0,
                          help="Enable or disable digital beacon hopping [default=%default]")          


                    
##=========================================================================================
## common functions
##=========================================================================================
def make_beacon(mac_config, frame_config, next_sched, frame_num, packet_count,  
                cur_frame_ts, slot_num, pktCode, toID, bytes_to_samples, dev_log=None, 
                pkt_overhead=PHY_HEADER_LEN+TDMA_HEADER_LEN): 
    '''
    Generate the (meta,data) tuple for a single beacon packet
    
    This combines the input parameters into the metadata and packet payload required
    for a valid beacon packet. 
    
    Keyword Arguments:
    
    mac_config        (dict) mac state machine configuration info. Must contain at
                             minimum the following:
      fs             (float) sample rate at the output of the modulator
      macCode          (int) MAC code to add to header
      my_id            (int) MAC address of this node
      phyCode          (int) PHY code to add to header
      pre_guard      (float) time in seconds to reserve at the start of a slot                          
    frame_config  (dict) current frame format defined by the base station. This is
                             used to set up the beacon packet header info. Must 
                             contain at minimum the following:                  
      slots           (list) element i corresponds to slot number i. Each element
                             is a SlotParamTuple
    next_frame_config (dict) frame format for the next frame as defined by the base 
                             station. This is used for the actual beacon packet data as 
                             any changes in the frame format contained in the beacon of 
                             frame N can only synchronously take effect for frame N+1. 
                             Must contain at minimum the following:                  
      slots           (list) element i corresponds to slot number i. Each element
                             is a SlotParamTuple                               
    frame_num          (int) current frame number
    packet_count       (int) number of packets sent so far
    cur_frame_ts (time_spec_t) timestamp of the start of the current frame
    frame_latch_num    (int) frame number when the mobiles should start using the schedule 
                             contained in this beacon
    slot_num           (int) number of the current slot
    pktCode            (int) packet type code to add to header
    toID               (int) MAC address of the intended receiver

                                
    Returns:
    slot_pkts   (list) list containing a single element: A (meta,data) tuple describing
                       a beacon  packet
    packet_count (int) number of packets sent so far
    
    '''         
    pre_guard = mac_config["pre_guard"]
    fromID = mac_config["my_id"]
    fs = mac_config["fs"]
    # get the slot info for this beacon
    slot = frame_config["slots"][slot_num]
    cur_frame_len = frame_config["frame_len"]
    
    beacon = deepcopy(next_sched)
    t0 = beacon.time_ref
        
    # compute the offset to the start of the schedule
    frame_offset = float(t0 - cur_frame_ts)-slot.offset - pre_guard

    packet_offset = slot.offset + pre_guard

    # round beacon packet tx timestamp to nearest sample
    pkt_timestamp = time_spec_t(cur_frame_ts.int_s(), 
                                round((packet_offset + cur_frame_ts.frac_s())*fs)/fs)
    
       
    
    
    
    # remove t0 field since that's populated on the receive side
    beacon.time_ref = time_spec_t(0)
    
    # add tx time and frame offset so receive side can compute t0
    beacon.tx_time = pkt_timestamp.to_tuple()
    beacon.frame_offset = frame_offset

    
    beacon.compact()         
#    # convert the named tuple slots to plain slots to shrink the beacon packet
#    for index, slot_i in enumerate(beacon["slots"]):
#        beacon["slots"][index] = tuple(slot_i)
    
    data = beacon_utils.dump_beacon(beacon)
    
    fs = mac_config["fs"]

    
    slot_dur = slot.len-pre_guard
    
    
    # Note that bytes_to_samples should account for PHY layer header already so 
    # subtract that out so it is not doublecounted        
    packet_bytes = len(data) + pkt_overhead
    packet_samples = bytes_to_samples(packet_bytes - PHY_HEADER_LEN)
    
#    dev_log.info("beacon packet len is %i bytes",packet_bytes)
#    dev_log.info("beacon vars are %s", vars(beacon)) 
#    dev_log.info("beacon dump is %s", cPickle.dumps(beacon))        
    pkt_dur = float(packet_samples)/fs
    
    if pkt_dur > slot_dur and dev_log is not None:
        dev_log.warning("Beacon packet duration of %f seconds is greater than beacon slot length of %f seconds",
                        pkt_dur,slot_dur)        
    
    # prevent frame_num from overflowing a 2 byte int. packet_count is managed
    # by other code to prevent this, but internal logic requires frame_num to be
    # monotonically increasing, so only limit frame_num when sending packets
    meta = {"sourceID": fromID,
           "fromID": fromID,
           "destinationID": toID,
           "toID": toID,
           "packetid": packet_count,
           "pktCode": pktCode,
           "phyCode": mac_config["phyCode"],
           "macCode": mac_config["macCode"],
           "linkdirection": "down",
           "rfcenterfreq": slot.rf_freq,
           "frequency": slot.bb_freq, 
           "bandwidth": slot.bw,
           "tx_gain": slot.tx_gain,
           "timeslotID": int(slot_num),
           "frameID": int(frame_num % TDMA_HEADER_MAX_FIELD_VAL),
           "tx_time": pkt_timestamp.to_tuple(), #only needed for packet framer
           "timestamp": pkt_timestamp.to_tuple(),
           "more_pkt_cnt": 0, # only needed for packet framer
           "slot_total_bytes": 0, # placeholder
           "slot_payload_bytes": 0 # placeholder
           }
    
    packet_count = (packet_count + 1) % TDMA_HEADER_MAX_FIELD_VAL
    slot_pkts = [(meta,data)]
    
    return slot_pkts, packet_count
     
#def make_keepalive(mac_config, frame_num, packet_count, cur_frame_ts, slot_num, slot, 
#                   pktCode,toID, link_dir): 
#    '''
#    Generate the (meta,data) tuple for a single keepalive packet
#    
#    This combines the input parameters into the metadata and packet payload required
#    for a valid keepalive packet. 
#    
#    Keyword Arguments:
#    
#    mac_config      (dict) mac state machine configuration info. Must contain at
#                           minimum the following:
#      fs           (float) sample rate at the output of the modulator
#      macCode        (int) MAC code to add to header
#      my_id          (int) MAC address of this node
#      phyCode        (int) PHY code to add to header
#      pre_guard    (float) time in seconds to reserve at the start of a slot                          
#    frame_num        (int) current frame number
#    packet_count     (int) number of packets sent so far
#    cur_frame_ts (time_spec_t) timestamp of the start of the current frame
#    slot_num         (int) number of the current slot
#    slot  (SlotParamTuple) the current slot
#    pktCode          (int) packet type code to add to header
#    toID             (int) MAC address of the intended receiver
#    link_dir      (string) "up" for uplinks and "down" for downlinks
#                                
#    Returns:
#    slot_pkts   (list) list containing a single element: A (meta,data) tuple describing
#                       a keepalive packet
#    packet_count (int) number of packets sent so far
#    
#    '''           
#    pre_guard = mac_config["pre_guard"]
#    fromID = mac_config["my_id"]
#    fs = mac_config["fs"]
#    frame_offset = slot.offset + pre_guard
#      
#    pkt_timestamp = time_spec_t(cur_frame_ts.int_s(), 
#                                round((frame_offset + cur_frame_ts.frac_s())*fs)/fs)
#    
#    data = []
#    
#    # prevent frame_num from overflowing a 2 byte int. packet_count is managed
#    # by other code to prevent this, but internal logic requires frame_num to be
#    # monotonically increasing, so only limit frame_num when sending packets
#    meta = {"sourceID": fromID,
#           "fromID": fromID,
#           "destinationID": toID,
#           "toID": toID,
#           "packetid": packet_count,
#           "pktCode": pktCode,
#           "phyCode": mac_config["phyCode"],
#           "macCode": mac_config["macCode"],
#           "linkdirection": link_dir,
#           "rfcenterfreq": slot.rf_freq,
#           "frequency": slot.bb_freq, 
#           "bandwidth": slot.bw,
#           "tx_gain": slot.tx_gain, 
#           "timeslotID": int(slot_num),
#           "frameID": int(frame_num % TDMA_HEADER_MAX_FIELD_VAL),
#           "tx_time": pkt_timestamp.to_tuple(), #only needed for packet framer
#           "timestamp": pkt_timestamp.to_tuple(),
#           "more_pkt_cnt": 0, # only needed for packet framer
#           "slot_total_bytes": 0, # placeholder
#           "slot_payload_bytes": 0 # placeholder
#           }
#  
#    
#    packet_count = (packet_count + 1) % TDMA_HEADER_MAX_FIELD_VAL
#    slot_pkts = [(meta,data)]
#    
#    return slot_pkts, packet_count
#
#
#
#
def grouped(iterable, n):
    "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
    return izip(*[iter(iterable)]*n)
        
