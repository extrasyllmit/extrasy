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
from bisect import bisect_right
from collections import namedtuple
from copy import deepcopy
import logging
from math import ceil
from math import floor
from operator import itemgetter
from operator import attrgetter
from pprint import pprint
import struct
import threading
import time
# third party library imports

# project specific imports
from digital_ll import beacon_utils
from digital_ll import command_queue_manager
from digital_ll import time_spec_t
from digital_ll import tune_manager
from digital_ll.beacon_utils import PHY_HEADER_LEN
from digital_ll.beacon_utils import TdmaHeaderTuple
from digital_ll.beacon_utils import TDMA_HEADER_FORMAT
from digital_ll.beacon_utils import TDMA_HEADER_LEN
from digital_ll.beacon_utils import TDMA_HEADER_MAX_FIELD_VAL
from digital_ll.FrameSchedule import SlotParamTuple

import sm
from sm import SM














#=========================================================================================
# shared tdma code
#=========================================================================================
class tdma_shared(object):
    
    def get_tdma_header_len(self):
        return TDMA_HEADER_LEN    
    
    def get_phy_header_len(self):
        return PHY_HEADER_LEN           
    
    def num_bytes_to_num_samples(self, payload_len):
        return self.num_phy_bytes_to_num_samples(payload_len+TDMA_HEADER_LEN)
    
    @staticmethod
    def add_options(normal, expert):
    
        normal.add_option("--source-mac-address", default=1, type="int",
                          help=("Source ID of this node " +
                                "[default=%default]"))
        normal.add_option("--base-station-mac-address", default=1, type="int",
                          help=("ID of the network's base station " +
                                "[default=%default]"))
        normal.add_option("--sink-mac-addresses", type="string", 
                          help=("List of node IDs in the network." ))
        normal.add_option("--frame-lead-limit", default=.2, type="eng_float",
                          help=("How in advance to schedule transmissions, in seconds " +
                                "[default=%default]"))
        normal.add_option("--slot-pre-guard", default=0, type="eng_float",
                          help=("Quiet time at the start of each slot reserved as a " +
                                "work around for transients or settling times " +
                                "[default=%default]"))
    @staticmethod    
    def pack_tdma_header(data, fromID, toID, packetid, pktCode, phyCode, macCode,
                         sourceID, destinationID, rfcenterfreq, frequency,
                         bandwidth, timeslotID, frameID, linkdirection, **kwargs):
        """
        Concatenates 'header' fields with data to form a payload suitable 
        to pass into either the narrowband or ofdm packet structs
        
        """
        #TODO: padding bytes should be moved into phy level header
        
        # get the length of our header
        
        #hardcoded K from configuration of RS coding in packet_utils.py
        RS_K = 4  #this number is in bytes
    
        pad_tmp = (len(data) + TDMA_HEADER_LEN +4) % RS_K  #+4 for crc since crc is performed before RS coding
        if pad_tmp == 0:
            pad_bytes =0
        else:
            pad_bytes = RS_K - pad_tmp
        
        
        packed_header = struct.pack(TDMA_HEADER_FORMAT, packetid, pad_bytes, fromID, toID, 
                                    pktCode, phyCode, macCode, sourceID, destinationID, 
                                    rfcenterfreq, frequency, bandwidth, timeslotID, frameID, 
                                    linkdirection)
    
        # add padding
        #payload = ''.join( (packed_header, pickle_payload,'0'*pad_bytes) )
        payload = ''.join( (packed_header, data,'0'*pad_bytes) )
        return payload
    
    @staticmethod
    def unpack_tdma_header(meta=None, payload=''):
        """
        The inverse of pack_tdma_header: This pulls the 'header' fields out
        of the provided payload and returns them as a list of tuples
        """
        
        # provide metadata from phy layer if available
        if meta is None:
            meta = dict()
            
        # pull the header fields out of payload using a named tuple
        headerFields = TdmaHeaderTuple._make(struct.unpack(TDMA_HEADER_FORMAT, 
                                                           payload[:TDMA_HEADER_LEN]))
        
        
        # get the metadata and data out of the packet
        if headerFields.pad_bytes > 0: 
            data = payload[TDMA_HEADER_LEN:-headerFields.pad_bytes]
        else:
            data = payload[TDMA_HEADER_LEN:]
                   
        # add info from header to metadata
        meta.update(headerFields._asdict())
        
        # remove the pad_bytes field from metadata since no one needs it
        del meta['pad_bytes']
        
        return meta, data
        #return ( fromID, toID, packet_id, packet_code_str, more_data_follows, data)
    
#=========================================================================================
# tdma mobile MAC implementation
#=========================================================================================
class tdma_mobile_sm(tdma_shared,SM):
    """ 
    This is the implementation for a basic tdma mobile state machine  
    """
    
    startState = None
    
    def __init__(self, options, uhd_sink, uhd_source, num_bytes_to_num_samples):
        self.startState = ("init", {"sched_valid":False,
                                       "next_frame_ts":time_spec_t(0),
                                       "next_frame_num":0})
        
        self._types_to_ints = dict(beacon_utils.tdma_types_to_ints)
        self._ints_to_types = dict()
        self.dev_log = logging.getLogger('developer')
        
        self.cq_manager = command_queue_manager(uhd_sink, uhd_source) 
        
        self.tuner = tune_manager()
        
        # map from ints back to slot types
        for key in self._types_to_ints:
            self._ints_to_types[self._types_to_ints[key]] = key
            
        # store off bytes to samples conversion function
        self.num_phy_bytes_to_num_samples = num_bytes_to_num_samples  
        
#        #related to power control
#        if options.pwr_control_up:                 
#            self.pwr_control_up = 1            
#            self.dev_log.info("power control is enabled")
#        else:
#            self.pwr_control_up = 0
#            self.dev_log.info("power control is disabled")    
#     
        # hack to disable power control while going through simplification
        self.pwr_control_up = 0
        self.dev_log.info("power control is disabled")  
        
        
    def is_base(self):
        '''
        Is this MAC a base station type?
        '''
        return False
    
    def getNextValues(self, state, inp):
        """ This gets the next values of outputs and the next state
        
        """
        if inp == 'undefined':
            return (state, None)

        # unpack inputs
        app_in = inp['app_in']
        rf_in = inp['rf_in']
        mac_config = inp['mac_config']
        current_ts = inp['current_ts']
        packet_count = inp['packet_count']
        cur_frame_config = inp['frame_config']
        
        lead_lim = inp['mac_config']['lead_limit']
        
        manager = mac_config["slot_manager"]
        
        # process schedule updates from base
        sched_outs = self.process_schedule_seq(inp["sched_seq"], 
                                               current_ts, 
                                               lead_lim,
                                               manager.current_meta, 
                                               manager.current_schedule)
        
        sched_seq, sched_meta, next_sched, beacon_feedback = sched_outs
        
        inp["next_sched"] = next_sched
        
        manager.current_schedule = next_sched
        manager.current_meta = sched_meta
        
        state_name = state[0]
        state_params = state[1]
        
        command_list = []  
        
        if state_name == "init":
            

            outs = manager.acquire_sync(frame_config=None,
                                        current_ts=inp["end_ts"]+lead_lim,
                                        mac_config=mac_config,
                                        reset = True)
            
            # TODO: remove cmd tuple calcs from manager
            next_frame_config, is_updated, uhd_cmd_tuple_list = outs
            inp['frame_config'] = next_frame_config
            
            uhd_cmd_tuple_list = []
            uhd_cmd_tuple_list, next_frame_config = self.tuner.add_tune_commands(next_frame_config,
                                                                                uhd_cmd_tuple_list)    
            self.cq_manager.add_command_to_queue(uhd_cmd_tuple_list)
            
            if uhd_cmd_tuple_list is not None:
                self.dev_log.info("New Sync schedule: rf freq is %f", 
                              next_frame_config["slots"][0].rf_freq)
                
#                # calibrate the command queue to uhd timing errors
#                self.cq_manager.add_command_to_queue([(current_ts, lead_lim, "time_cal")])
#                self.cq_manager.add_command_to_queue(uhd_cmd_tuple_list)
            
            # advance time to the end of the current sample block
            current_ts = inp['end_ts']
            
            command_list.append(self.make_mux_commands(mac_config, 
                                                       next_frame_config, 
                                                       current_ts))
                
            # FIXME Add return to beacon channel command to command list
            if mac_config["fhss_flag"]:
                command_list.append( self.make_rx_channelizer_commands(mac_config, 
                                                                       next_frame_config, 
                                                                       current_ts) )
                
                
        
        next_state = self.getNextState(state, inp )
        
        next_state_name = next_state[0]
        next_state_params = next_state[1]
        this_frame_count = next_state_params["next_frame_num"]
        
        
        state_sched = state[1]

        tx_list = []
        dropped_pkts = []
              
        
        # deal with any packets coming from rf interface
        app_out_list = self.handle_rf_pkts(mac_config, rf_in)
        
         # track slot performance
        if next_state_params["sched_valid"]:
            manager.track_slot_performance(mac_config, this_frame_count-1, rf_in, beacon_feedback)       

        if state_name == "no_sync":
            # staying in "no_sync"
            if next_state_name == "no_sync":
                # advance time to the end of the current sample block
                current_ts = inp['end_ts']
                
                outs = manager.acquire_sync(frame_config=cur_frame_config,
                                            current_ts=inp["end_ts"]+lead_lim,
                                            mac_config=mac_config,
                                            reset = False)
                
                next_frame_config, is_updated, uhd_cmd_tuple_list = outs
                
                uhd_cmd_tuple_list = []
                uhd_cmd_tuple_list, next_frame_config = self.tuner.add_tune_commands(next_frame_config,
                                                                                     uhd_cmd_tuple_list)    
            
                # if there's a non-timing change in the schedule, update all schedule
                # dependent components
                if is_updated:
                    
                    if uhd_cmd_tuple_list is not None:
                        self.cq_manager.add_command_to_queue(uhd_cmd_tuple_list)
                    
                    new_commands = self.make_mux_commands(mac_config, 
                                                          next_frame_config, 
                                                          current_ts)
                    command_list.append(new_commands)
                    
                    # FIXME Add return to beacon channel command to command list
                    if mac_config["fhss_flag"]:
                        new_commands = self.make_rx_channelizer_commands(mac_config, 
                                                                         next_frame_config, 
                                                                         current_ts) 
                        command_list.append(new_commands)
                            
            # transition to wait
            elif next_state_name == "wait":
    
                next_frame_config = manager.compute_frame(this_frame_count)
                
            # switch from no_sync to output
            elif next_state_name == "output_frame": 
                # don't advance time during this transition
                manager.manage_slots(mac_config, this_frame_count, current_ts)
                    
                next_frame_config = manager.compute_frame(this_frame_count)
                uhd_cmd_tuple_list = []
                uhd_cmd_tuple_list, next_frame_config = self.tuner.add_tune_commands(next_frame_config,
                                                                                     uhd_cmd_tuple_list)    
                self.cq_manager.add_command_to_queue(uhd_cmd_tuple_list)
                
                self.dev_log.debug( ("storing frame t0=%s with t0 frame num=%i to history as " + 
                                "frame num %i"), next_frame_config['t0'], 
                                next_frame_config['t0_frame_num'], this_frame_count)
                
                               
                    
            # should never get here        
            else: 
                self.dev_log.error("next state name: %s is not known", next_state_name)

                
        elif state_name == "wait":
            if next_state_name == "no_sync":
                
                outs = manager.acquire_sync(frame_config=cur_frame_config,
                                            current_ts=inp["end_ts"]+lead_lim,
                                            mac_config=mac_config,
                                            reset = True)
                
                next_frame_config, is_updated, uhd_cmd_tuple_list = outs
                self.dev_log.info("New Sync schedule: rf freq is %f", 
                                  next_frame_config["slots"][0].rf_freq)
                
                uhd_cmd_tuple_list = []
                uhd_cmd_tuple_list, next_frame_config = self.tuner.add_tune_commands(next_frame_config,
                                                                                uhd_cmd_tuple_list)    
           
            
                if uhd_cmd_tuple_list is not None:
                    self.cq_manager.add_command_to_queue(uhd_cmd_tuple_list)
                
                # always update timing dependent components for this transition
                new_commands = self.make_mux_commands(mac_config, 
                                                      next_frame_config, 
                                                      current_ts)
                command_list.append(new_commands)
                
                # FIXME Add return to beacon channel command to command list
                if mac_config["fhss_flag"]:
                    new_commands = self.make_rx_channelizer_commands(mac_config, 
                                                                     next_frame_config, 
                                                                     current_ts) 
                    command_list.append(new_commands)
         
            # stay in wait
            elif next_state_name == "wait":
                # advance time to the start of the next frame
                current_ts = next_state_params["next_frame_ts"]-1/mac_config["fs"]
                next_frame_config = cur_frame_config
                        
            # switch from wait to output
            elif next_state_name == "output_frame": 
                # don't advance time during this transition
                next_frame_config = cur_frame_config
                pass
                
            # should never get here        
            else: 
                self.dev_log.error("next state name: %s is not known", next_state_name)
                
                
        elif state_name == "output_frame":
            # if going out of sync
            if next_state_name == "no_sync":
                
                outs = manager.acquire_sync(frame_config=cur_frame_config,
                                            current_ts=inp["end_ts"]+lead_lim,
                                            mac_config=mac_config,
                                            reset = True)
                
                next_frame_config, is_updated, uhd_cmd_tuple_list = outs
                
                uhd_cmd_tuple_list = []
                uhd_cmd_tuple_list, next_frame_config = self.tuner.add_tune_commands(next_frame_config,
                                                                                     uhd_cmd_tuple_list)    

                self.dev_log.info("New Sync schedule: rf freq is %f", 
                                  next_frame_config["slots"][0].rf_freq)
                
                if uhd_cmd_tuple_list is not None:
                    self.cq_manager.add_command_to_queue(uhd_cmd_tuple_list)
                
                # always update timing dependent components for this transition
                new_commands = self.make_mux_commands(mac_config, 
                                                      next_frame_config, 
                                                      current_ts)
                command_list.append(new_commands)
                
                # FIXME Add return to beacon channel command to command list
                if mac_config["fhss_flag"]:
                    new_commands = self.make_rx_channelizer_commands(mac_config, 
                                                                     next_frame_config, 
                                                                     current_ts) 
                    command_list.append(new_commands)
            
            # transition to wait
            elif next_state_name == "wait":
                # advance time to the start of the next frame
                current_ts = next_state_params["next_frame_ts"]-1/mac_config["fs"]
#                next_frame_config = current_frame_config
                next_frame_config = manager.compute_frame(this_frame_count)
                        
            elif next_state_name == "output_frame":
                
                manager.manage_slots(mac_config, this_frame_count)
                
                next_frame_config = manager.compute_frame(this_frame_count)
                self.dev_log.debug( ("storing frame t0=%s with t0 frame num=%i to history as " + 
                                "frame num %i"), next_frame_config['t0'], 
                                next_frame_config['t0_frame_num'], this_frame_count)
                
                
                current_ts = ( next_state_params["next_frame_ts"] + 
                               next_frame_config["frame_len"]-1/mac_config["fs"])
                
                
                if self.pwr_control_up:
                    # do uplink power control
                    uhd_cmd_tuple_list = self.make_gain_commands(mac_config, 
                                                                 next_frame_config)
                else:
                    uhd_cmd_tuple_list = []
                            
                uhd_cmd_tuple_list, next_frame_config = self.tuner.add_tune_commands(next_frame_config,
                                                                                     uhd_cmd_tuple_list)    
                self.cq_manager.add_command_to_queue(uhd_cmd_tuple_list)
                    
                # compute the list of packets to send and any schedule updates necessary
                # for the next frame
                send_frame = manager.send_frame
                result = send_frame(mac_config, next_frame_config, 
                                    next_state_params["next_frame_num"], packet_count,  
                                    next_state_params["next_frame_ts"],  app_in )
            
                old_packet_count = packet_count
                # unpack results
                frame_count, packet_count, tx_list, app_in, dropped_pkts = result
                
                self.dev_log.info("sending %i packets in frame num %i at time %s",
                                  packet_count-old_packet_count,this_frame_count,
                                  next_state_params["next_frame_ts"] )
                command_list.append(self.make_mux_commands(mac_config, 
                                                           next_frame_config, 
                                                           next_state_params["next_frame_ts"]))
            

                # FIXME Add rx channelizer schedule set to command list
                if mac_config["fhss_flag"]:
                    command_list.append( self.make_rx_channelizer_commands(mac_config, 
                                                                           next_frame_config, 
                                                                           next_state_params["next_frame_ts"]) )

            # should never get here        
            else: 
                self.dev_log.error("next state name: %s is not known", next_state_name)
        
        manager.current_schedule = next_sched
        

        
        # add tdma headers to all the packets in the tx list
        tx_list = [ (meta, self.pack_tdma_header(data, **meta)) for meta, data in tx_list  ]
               
        outputs = {
                   "app_in":app_in,
                   "app_out_list":app_out_list,
                   "command_list":command_list,
                   "current_ts":current_ts,
                   "dropped_pkts":dropped_pkts,
                   "frame_config":next_frame_config,
                   "frame_count":this_frame_count,
                   "packet_count":packet_count,
                   "pkt_switch_queues":None,
                   "sched_seq":sched_seq,
                   "tx_list":tx_list, 
                    }
        
        return  (next_state, outputs)

    def getNextState(self, state, inp):
                
        frame_config = inp['frame_config']
        next_sched = inp['next_sched']
        current_ts = inp['current_ts']
        end_ts = inp['end_ts']
        lead_lim = inp['mac_config']['lead_limit']
        state_name = state[0]
        state_params = state[1]
        fs = inp["mac_config"]["fs"]            
        
        # handle one time initialization tasks
        if state_name == "init":
            
            
            
            
            next_state_name = "no_sync"
            next_state_params=dict(state_params)
            next_state_params["next_frame_ts"]=frame_config["t0"] + frame_config["frame_len"]
            next_state_params["next_frame_num"]=0
            
        elif next_sched is None or next_sched.valid == False:
            
                    
            # if the schedule isn't valid, always go back to no_sync
            next_state_name = "no_sync"
            next_state_params=dict(state_params)
            next_state_params["sched_valid"] = False 
            next_state_params["next_frame_num"] = 0
            next_state_params["next_frame_ts"]=frame_config["t0"] + frame_config["frame_len"]
            
        # otherwise handle valid schedules
        else:
            if state_name == "no_sync":
                
                next_state_name = "wait"
                next_state_params=dict(state_params)
                next_state_params["sched_valid"] = True
                        
            elif state_name == "output_frame":
                # if the next frame timestamp is in the current set of 
                # samples ( plus the lead limit so the transmitter has time to react)
                # then stay in output frame
                
                next_frame_ts, next_frame_num  = self.find_next_frame_start(current_ts, 
                                                                       frame_config, fs)
                
                if next_frame_ts < end_ts + lead_lim:
                    next_state_name = "output_frame"
                else:
                    next_state_name = "wait" 
                    
                next_state_params = {"sched_valid":True,
                                     "next_frame_ts":next_frame_ts,
                                     "next_frame_num":next_frame_num}  
                
            elif state_name == "wait":
                # if the next frame timestamp is in the current set of 
                # samples ( plus the lead limit so the transmitter has time to react)
                # then stay in output frame
                
                next_frame_ts, next_frame_num  = self.find_next_frame_start(current_ts, 
                                                                       frame_config, fs)
                
                if next_frame_ts < end_ts + lead_lim:
                    next_state_name = "output_frame"
                else:
                    next_state_name = "wait"
                    
                next_state_params = {"sched_valid":True,
                                     "next_frame_ts":next_frame_ts,
                                     "next_frame_num":next_frame_num}      
                
            else:
                print "Unrecognized state name:" + state_name                

                
#        self.dev_log.debug("state transition: %s => %s. next_frame_ts: %s next_frame_num %i", 
#                           state_name, next_state_name, next_state_params["next_frame_ts"],
#                           next_state_params["next_frame_num"])   
        return (next_state_name, next_state_params)
    
    def process_schedule_seq(self, sched_seq, current_ts, lead_lim, current_meta, current_sched):
        '''
        This function manages the sequence of new schedules and pulls out the right most 
        schedule with a timestamp less than or equal to the current timestamp. It also 
        detects schedules that signal a loss of sync. 
        '''
        # sched_seq_in is a sequence of schedules that haven't yet been interpreted by 
        # the node into a frame_config. Currently implemented as a deque to take care of
        # producer/consumer data structure access
       
        # do a first pass on sequence looking for any schedules marked as not valid. This 
        # indicates a loss of sync, so all the schedules up to the newest schedule marked  
        # not valid should be purged from the list
        sched_valids = [s.valid for (m,s) in sched_seq]
        
        # pull out the beacon packet ids for each schedule in the current schedule 
        # sequence
        try:
            beacon_feedback = list(set((m["packetid"], m["sourceID"]) for (m,s) in sched_seq
                                       if m))
        except KeyError as err:
            self.dev_log.error("Key Error: %s   Dict contents: %s", err.message, m)
        
        if not all(sched_valids):
            # if there's at least one false, find the last one
            sched_valids.reverse()
            rind = sched_valids.index(False)
            ind = len(sched_valids)-1-rind
            
            # now clear out all schedules up to this index
            sched_seq[:] = sched_seq[ind:]
        
        # now sort the garbage collected list by time

        sched_seq.sort(key=lambda element: element[1].time_ref)

        # now determine what the next schedule should be
        # pull out the starting times for the current set of schedules
        sched_times = [s.time_ref for (m,s) in sched_seq]
        
        # find the rightmost schedule with a timestamp less than or equal to the 
        # current timestamp. To ensure there's time to react to new schedules,
        # look at these new schedules at least lead_limit ahead of time
        # Note that the returned value from bisect_right is one index 
        # to the right of what we're looking for
        ins_point = bisect_right(sched_times, current_ts+lead_lim)
        
        if ins_point >= 1:
                                
            (sched_meta, next_sched) = sched_seq[ins_point-1]
            
            if next_sched.valid:
                self.dev_log.debug("new schedule with t0 %s becoming active at current time %s",
                                   next_sched.time_ref, current_ts)
                self.dev_log.debug("sched_times was %s", sched_times)
                #self.dev_log.debug("new schedule is %s", next_sched["slots"])
                # cull the next schedule and old schedules no longer needed 
            sched_seq[:] = sched_seq[ins_point:]
         
        # if all the schedules are in the future, but the first one is not valid       
        elif len(sched_seq) > 0 and sched_seq[0][1].valid==False:
            # assign the first schedule to next_schedule so the invalid schedule event is
            # propagated immediately
            (sched_meta, next_sched) = sched_seq[0]
         
        # handle the case of no new schedules
        else: 
            next_sched = current_sched  
            sched_meta = current_meta
#            self.dev_log.debug("no new schedules at current time %s", current_ts)
           
        return sched_seq, sched_meta, next_sched, beacon_feedback
                
    
    def handle_rf_pkts(self, mac_config, rf_in):
        '''
        Handle packets coming to the MAC from the RF interface 
        '''
        app_out_list = []
        manager = mac_config["slot_manager"]
        # filter out any invalid packets
        valid_pkts = [(meta, data) for meta, data in rf_in if meta["crcpass"] == True]
            
        for meta, data in valid_pkts:    
#            print "received incoming packet with metadata %s" %meta
            
            if (meta["pktCode"] == self._types_to_ints["data"]) and (meta["toID"] == mac_config["my_id"]):
                meta, payload = manager.unpack_slot_manager_header(meta, data)
                app_out_list.append( (meta, payload) )
        
        return app_out_list
    
    
    def make_mux_commands(self,mac_config, frame_config, frame_ts): 
        '''
        This creates commands to send to the mux that tell it to pass along
        the samples associated with the slots we want to receive
        
        The parameters for the mux command are a list of tuples, one tuple per 
        mux output. 
        [ (frame_len, slot_lens, slot_offsets, frame_t0)]
        '''
        default_frame_len = 1.333
        default_offset = 0
        my_id = mac_config["my_id"]
        base_id = mac_config["base_id"]
        
        if frame_config is not None:
        
            # pull out the receive slots
            rx_slots = [x for x in frame_config["slots"] if (x.type == "downlink") and 
                        (x.owner==my_id)]
            
            beacon_slots = [x for x in frame_config["slots"] if (x.type == "beacon") and 
                        (x.owner==base_id)]
            
            
            # build up the parameters to tell the schedule mux which samples to forward
            # to the receiver
            rx_sched = (frame_config["frame_len"],
                        [x.len for x in rx_slots],
                        [x.offset for x in rx_slots],
                        frame_ts.to_tuple())
        
            beacon_sched = (frame_config["frame_len"],
                            [x.len for x in beacon_slots],
                            [x.offset for x in beacon_slots],
                            frame_ts.to_tuple())
        else:
            # TODO: handle frequency rendezvous when there's no sync
            rx_sched = (default_frame_len,
                        [0],
                        [default_offset],
                        frame_ts.to_tuple())
        
            beacon_sched = (default_frame_len,
                            [default_frame_len],
                            [default_offset],
                            frame_ts.to_tuple())
        
#        print "making new mux commands"

                    
        #return [ (mac_config["mux_command"], [beacon_sched, rx_sched]) ]
        
        self.dev_log.debug("beacon schedule: %s",beacon_sched)
        self.dev_log.debug("rx schedule: %s",rx_sched)
        return (mac_config["mux_command"], [beacon_sched, rx_sched])
    
    def make_rx_channelizer_commands(self, mac_config, frame_config, frame_ts):
        '''
        This creates commands to send to the rx channelizer that tell it to
        tune to various channels associated with the slots we want to receive.
        
        The parameters for the channelizer command is
        (t0, frame length, slot times, slot frequencies)
        '''
        
        default_frame_len = 1.333
        default_offset = 0
        
        if frame_config is not None:
            slot_times       = [x.offset for x in frame_config["slots"]]
            slot_frequencies = [x.bb_freq for x in frame_config["slots"]]
            t0               = frame_ts.to_tuple()
            frame_length     = frame_config["frame_len"]
        else:
            slot_times       = [0]
            slot_frequencies = [0]
            t0               = frame_ts.to_tuple()
            frame_length     = default_frame_len
            
        self.dev_log.debug("rx channelizer commands: %s",[t0, frame_length, slot_times, slot_frequencies])
        
        #return [ (mac_config["rx_channelizer_command"], [t0, frame_length, slot_times, slot_frequencies]) ]
        return (mac_config["rx_channelizer_command"], [t0, frame_length, slot_times, slot_frequencies])
    
    def find_next_frame_start(self, current_time, frame_config, fs):
        '''
        This is used by mobiles to derive the next frame start time
        '''
        
        t0 = time_spec_t(frame_config['t0'])
        frame_len = frame_config['frame_len'] 
        
        time_delta = float(current_time - t0)
        
    
        frame_delta = ceil(time_delta/frame_len)
        next_frame_num = frame_config["t0_frame_num"] + frame_delta
        
        # find the lowest frame start time greater than or equal to the current time
        next_frame_ts = t0 + frame_delta*frame_len
        next_frame_ts = next_frame_ts.round_to_sample(fs, t0)
        self.dev_log.debug("find_next_frame: sched t0: %s current_ts: %s sched t0 frame num: %i",
                           t0, current_time, frame_config["t0_frame_num"] )
        
        return next_frame_ts, next_frame_num
    
    def make_gain_commands(self, mac_config, frame_config):
        '''
        Build up a list of time-gain tuples for uplink slots based on the 
        current frame config
        '''
        t0 = frame_config['t0']
        
        # build up a list of time-gain tuple commands for downlink and beacon slots
        tuple_list = [ (t0+s.offset, s.tx_gain, 'tx_gain') for s in frame_config["slots"]
                       if s.owner == mac_config["my_id"] and s.type == 'uplink']
        
        
        tuple_list = remove_redundancy(tuple_list)
        
        return tuple_list    

#=========================================================================================
# tdma base MAC implementation
#=========================================================================================
class tdma_base_sm(tdma_shared, SM):
    """ 
    This is the implementation for a basic tdma base state machine  
    """
    
    startState = None
    
    def __init__(self, options, uhd_sink, uhd_source, num_bytes_to_num_samples):
        self.startState = "init",time_spec_t(0)
        
        self._types_to_ints = dict(beacon_utils.tdma_types_to_ints)
        self._ints_to_types = dict()
        self.dev_log = logging.getLogger('developer')
        # map from ints back to slot types
        for key in self._types_to_ints:
            self._ints_to_types[self._types_to_ints[key]] = key
            
        self.tuner = tune_manager()    
        self.cq_manager = command_queue_manager(uhd_sink, uhd_source)    

#        #related to downlink power control
#        if options.pwr_control:                            
#            self.pwr_control = 1            
#            self.dev_log.info("downlink power control is enabled")
#        else:
#            self.pwr_control = 0
#            self.dev_log.info("downlink power control is disabled")  
#
#        #related to uplink power control
#        if options.pwr_control_up:                 
#            self.pwr_control_up = 1            
#            self.dev_log.info("uplink power control is enabled")
#        else:
#            self.pwr_control_up = 0
#            self.dev_log.info("uplink power control is disabled")    

        # Hack to disable power control while going through code simplification
        self.pwr_control = 0
        self.dev_log.info("downlink power control is disabled")  
        self.pwr_control_up = 0
        self.dev_log.info("uplink power control is disabled")   

        self.num_phy_bytes_to_num_samples = num_bytes_to_num_samples
        
    def is_base(self):
        '''
        Is this MAC a base station type?
        '''
        return True
    
    def getNextValues(self, state, inp):
        """ This gets the next values of outputs and the next state
        
        """
        if inp == 'undefined':
            return (state, None)

        
        # unpack inputs
        app_in = inp['app_in']
        rf_in = inp['rf_in']
        mobile_queues = inp['pkt_switch_queues']
        mac_config = inp['mac_config']
        current_ts = inp['current_ts']
        packet_count = inp['packet_count']
        frame_count = inp['frame_count']
        
        
        manager = mac_config["slot_manager"]
        
        
        cur_frame_config = manager.compute_frame(frame_count)
        inp['frame_config'] = cur_frame_config
                    
        state_name = state[0]
                        
        # fan out input packets to destination queues
        mobile_queues = self.switch_packets(mac_config, app_in, mobile_queues)      

        tx_list = []
        dropped_pkts = []
        command_list = []
        
        
        # deal with any packets coming from rf interface
        result = self.handle_rf_pkts(mac_config, rf_in)
        
        # unpack results
        app_out_list, routing_pkts = result
        
        # route one hop packets
        mobile_queues = self.route_packets(mac_config, routing_pkts, mobile_queues)
        
        
        # update the error statistics for each active slot
        manager.track_slot_performance(mac_config, frame_count, rf_in)        
        


        next_state = self.getNextState(state, inp )
        
        
        
        next_state_name = next_state[0]
        next_frame_ts = next_state[1] 
        
            
        if next_state_name == "init":
            # advance time to the end of the current sample block, or one sample
            # ahead of the first frame minus the lead limit, whichever is bigger.
            # this prevents busy waits at the start or precision issues in 
            # comparison against the start time, but still gives enough time
            # to send out the first frame
            first_frame_time_with_lead = cur_frame_config['t0'] - mac_config["lead_limit"] + 1/mac_config['fs']
            current_ts = max(inp['end_ts'], first_frame_time_with_lead )
            
            
        elif next_state_name == "output_frame":
 
            
                        
            outs = manager.manage_slots(mac_config, frame_count, rf_in, mobile_queues)
        
            next_sched, mobile_queues = outs
            cur_frame_config = next_sched.compute_frame(frame_count)
            
            command_list.append(self.make_mux_commands(mac_config, cur_frame_config, next_frame_ts))


            #FIXME Add command list to schedule
            if mac_config["fhss_flag"]:
                command_list.append( self.make_rx_channelizer_commands(mac_config, cur_frame_config, next_frame_ts) )

                            
            # advance time to the end of the current frame
            current_ts = next_frame_ts + cur_frame_config["frame_len"] - mac_config["lead_limit"]
            

#           insert power control function call before compute next frame config            
#           print "Everything about next frame is printed here"
#           pprint(cur_frame_config)

#            pprint("Before ...")
#            pprint(cur_frame_config["slots"])
            #related to power control, enabled by options.pwr_control
            if self.pwr_control and hasattr(manager, 'db'):
#                uhd_cmd_tuple_list, cur_frame_config = self.tx_power_controller.optimize_power(frame_count,
#                                                                                               cur_frame_config,
#                                                                                               manager.db,
#                                                                                               self.dev_log)
                uhd_cmd_tuple_list = self.make_gain_commands(cur_frame_config)
            else:
                uhd_cmd_tuple_list = []
                
            
            uhd_cmd_tuple_list, cur_frame_config = self.tuner.add_tune_commands(cur_frame_config,
                                                                                uhd_cmd_tuple_list)    
#                print time_gain_tuple_list
            self.cq_manager.add_command_to_queue(uhd_cmd_tuple_list)
                        
            self.dev_log.info("sending frame num %i at time %s",frame_count,
                              next_frame_ts )
            send_frame = mac_config["slot_manager"].send_frame
            result = send_frame( mac_config, cur_frame_config, next_sched, 
                                 frame_count, packet_count, next_frame_ts, 
                                 mobile_queues)
                        
            # unpack results
            frame_count, packet_count, tx_list, mobile_queues, dropped_pkts = result
            
            
            
            
            
#            compute_frame_config = mac_config["slot_manager"].base_compute_frame_config
#        
#            cur_frame_config = compute_frame_config(manager.current_schedule, frame_count)
            
            cur_frame_config = manager.compute_frame(frame_count)
            
            manager.current_schedule = next_sched
    
            
            
        elif next_state_name == "wait":
            
            # output the mux command on the first state transition to output_frame
            if state_name == "init":
                command_list.append(self.make_mux_commands(mac_config, cur_frame_config,next_frame_ts))
#                # calibrate the command queue to uhd timing errors
#                self.cq_manager.add_command_to_queue([(current_ts, mac_config["lead_limit"], "time_cal")])
                
                #FIXME Add command list to schedule
                if mac_config["fhss_flag"]:
                    command_list.append( self.make_rx_channelizer_commands(mac_config, cur_frame_config, next_frame_ts) )
                
                    
            current_ts = max( next_frame_ts - mac_config["lead_limit"], inp['end_ts'])   
           
        else: # should never get here
                pass
                    
        
        current_ts = current_ts.round_to_sample(mac_config["fs"], cur_frame_config["t0"])
        
        # add tdma headers to all the packets in the tx list
        tx_list = [ (meta, self.pack_tdma_header(data, **meta)) for meta, data in tx_list  ]
        
        #self.dev_log.debug("outgoing slot_stat_history: %s", slot_stat_history)          
        outputs = {
                   "app_in":app_in,
                   "app_out_list":app_out_list, 
                   "command_list":command_list,
                   "current_ts":current_ts, 
                   "dropped_pkts":dropped_pkts,
                   "frame_config":cur_frame_config,
                   "frame_count":frame_count,
                   "packet_count":packet_count,
                   "pkt_switch_queues":mobile_queues,
                   "sched_seq":inp['sched_seq'],
                   "tx_list":tx_list, 
                    }
        
        return  (next_state, outputs)

    
    def getNextState(self, state, inp):
                
        frame_config = inp['frame_config']
        current_ts = inp['current_ts']
        end_ts = inp['end_ts']
        frame_count = inp['frame_count']
        lead_lim = inp['mac_config']['lead_limit']
        state_name = state[0]
        fs = inp["mac_config"]["fs"]
        
        current_ts = current_ts.round_to_sample(fs, frame_config["t0"])
        next_frame_ts = compute_next_frame_start(current_ts, frame_count, frame_config, fs)
        
#        self.dev_log.debug("t0 is %s, current_time is %s, next_frame_ts is %s",
#                          frame_config["t0"], current_ts, next_frame_ts)
        
        if state_name == "init":
            # check if it's too soon to start 
            if (current_ts + lead_lim  < frame_config["t0"]):
                next_state_name = "wait"
            else:
                # check whether it's time to output the next frame
                if (current_ts <= next_frame_ts + lead_lim ):
                    next_state_name = "output_frame"
                    
                else:
                    next_state_name = "wait"

        # if not in init, the next state only depends on the timestamp            
        else:
            # check whether it's time to output the next frame
            if (current_ts <= next_frame_ts + lead_lim ):
                next_state_name = "output_frame"
            else:
                next_state_name = "wait"
                           
#        self.dev_log.debug("current state %s, next state %s",
#                           state_name, next_state_name)       
        return next_state_name, next_frame_ts
    
    def switch_packets(self,mac_config, app_in, mobile_queues):
        '''
        Store packets in output queues by toID. This is distinct from routing, which
        operates on destinationID. 
        '''
        
        app_in_len = len(app_in)
        
        # TODO: Verify that this doesn't need to be a copy operation
        for k in range(app_in_len):
            
            
            
            meta, data = app_in.popleft()
            
            # if the packet was submitted without a toID specified, assume it's toID
            # is the same as it's destinationID
            if "toID" not in meta:
                meta["toID"] = meta["destinationID"]
            
            if( (meta["toID"] != mac_config["my_id"]) and (meta["toID"] > 0) and
              (len(mobile_queues[meta["toID"]]) < mac_config["app_in_q_size"]) ):
                mobile_queues[meta["toID"]].append( (meta,data) )
        
        return mobile_queues
    
    def handle_rf_pkts(self, mac_config, rf_in):
        '''
        Handle packets coming to the MAC from the RF interface
        '''
        app_out_list = []
        routing_pkts = []
        manager = mac_config["slot_manager"]
        
        # filter out any invalid packets
        valid_pkts = [(meta, data) for meta, data in rf_in if meta["crcpass"] == True]
        
        for meta, data in valid_pkts:
            
            # check if this is a data packet addressed to me
            if (meta["destinationID"] == mac_config["my_id"]):
                if (meta["pktCode"] == self._types_to_ints["data"]):
                    meta, payload = manager.unpack_slot_manager_header(meta, data)
#                    print "packet was data addressed to me"
                    app_out_list.append( (meta, payload) )
            
            # if the packet wasn't addressed to me, and wasn't from me, try to route it        
            elif meta["fromID"] != mac_config["my_id"]:
                routing_pkts.append( (meta, data) ) 
                
        return app_out_list, routing_pkts
    
    def route_packets(self, mac_config, routing_pkts, mobile_queues):
        '''
        Inspect the destination ID of each packet to route the packet out the correct port
        Modify the fromID,toID as needed
        '''
        for meta, data in routing_pkts:
            
            # do not route our own packets
            if meta['fromID'] != mac_config["my_id"]:
                new_meta = deepcopy(meta)
                new_meta['toID'] = meta['destinationID']
                new_meta['fromID'] = mac_config["my_id"]
                new_meta['timestamp'] = meta['timestamp'].to_tuple()
            
                mobile_queues[meta["destinationID"]].append( (new_meta, data) )
            
        return mobile_queues
    
    
    def make_mux_commands(self,mac_config, frame_config, frame_ts): 
        '''
        This creates commands to send to the mux that tell it to pass along
        the samples associated with the slots we want to receive
        
        The parameters for the mux command are a list of tuples, one tuple per 
        mux output. 
        [ (frame_len, slot_lens, slot_offsets, frame_t0)]
        '''
        # pull out the receive slots
        rx_slots = [x for x in frame_config["slots"] if x.type == "uplink" and x.owner > 0]
#        print "making new mux commands"
        # build up the parameters to tell the schedule mux which samples to forward
        # to the receiver
        rx_sched = (frame_config["frame_len"],
                    [x.len for x in rx_slots],
                    [x.offset for x in rx_slots],
                    frame_ts.to_tuple())
                    
        
        self.dev_log.debug("rx schedule: %s",rx_sched)          
        #return [ (mac_config["mux_command"], [rx_sched]) ]
        return (mac_config["mux_command"], [rx_sched])
    
    def make_rx_channelizer_commands(self, mac_config, frame_config, frame_ts):
        '''
        This creates commands to send to the rx channelizer that tell it to
        tune to various channels associated with the slots we want to receive.
        
        The parameters for the channelizer command is
        (t0, frame length, slot times, slot frequencies)
        '''
        
        slot_times       = [x.offset for x in frame_config["slots"]]
        slot_frequencies = [x.bb_freq for x in frame_config["slots"]]
        t0               = frame_ts.to_tuple()
        frame_length     = frame_config["frame_len"]
            
        self.dev_log.debug("rx_channelizer_command: %s", [t0, frame_length, slot_times, slot_frequencies])    
        #return [ (mac_config["rx_channelizer_command"], [t0, frame_length, slot_times, slot_frequencies]) ]
        return (mac_config["rx_channelizer_command"], [t0, frame_length, slot_times, slot_frequencies])
    
    def make_gain_commands(self, frame_config):
        '''
        Build up a list of time-gain tuples for beacon and downlink slots based on the 
        current frame config
        '''
        t0 = frame_config['t0']
        
        # build up a list of time-gain tuple commands for downlink and beacon slots
        tuple_list = [ (t0+s.offset, s.tx_gain, 'tx_gain') for s in frame_config["slots"]
                       if s.owner > 0 and (s.type == 'downlink' or s.type == 'beacon')]
        
        
        tuple_list = remove_redundancy(tuple_list)
        
        return tuple_list

#=========================================================================================
# common functions
#=========================================================================================

def compute_next_frame_start(current_time, frame_num, schedule, fs):
    '''
    This is used by base stations to compute the next frame start time
    '''
    
    t0 = time_spec_t(schedule['t0'])
    frame_len = schedule['frame_len'] 
    
    # find the lowest frame start time greater than or equal to the current time
    next_frame_ts = float(frame_num-schedule['t0_frame_num'])*frame_len + t0
    next_frame_ts = next_frame_ts.round_to_sample(fs, t0)
    
    
    return next_frame_ts
                      
def remove_redundancy(time_gain_tuple_list):
    
    for k in reversed(range(len(time_gain_tuple_list))):
        if k>0 and time_gain_tuple_list[k][1]==time_gain_tuple_list[k-1][1]:
            time_gain_tuple_list.pop(k)
            
    return time_gain_tuple_list



#
# Add the tdma family of macs to the mac registry
#
sm.add_mac_type('tdma_mobile', tdma_mobile_sm)
sm.add_mac_type('tdma_base', tdma_base_sm)
