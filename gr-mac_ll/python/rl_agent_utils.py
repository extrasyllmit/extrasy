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
from collections import namedtuple
from copy import deepcopy
from itertools import chain
import json
import logging
import logging.config
import math
from math import floor
from operator import itemgetter
import os
import pickle
import random
import struct
import sqlite3
import sys
import time   

# third party library imports
import numpy as np

# project specific imports
from digital_ll import lincolnlog
from digital_ll import PatternFrameSchedule
from digital_ll import SortedCollection
from digital_ll import time_spec_t

from digital_ll.beacon_utils import TDMA_HEADER_MAX_FIELD_VAL
from digital_ll.beacon_utils import TDMA_HEADER_LEN
from digital_ll.beacon_utils import PHY_HEADER_LEN
from digital_ll.FrameSchedule import SlotParamTuple
from digital_ll.lincolnlog import dict_to_xml
from node_agents import Agent_Wrapper
from SlotManager import BaseSlotManagerDb
from SlotManager import grouped
from SlotManager import make_beacon
from SlotManager import MobileSlotManager
from sm import SM

                                             

def timeit(method):

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print 'TIMER: %r:  %2.6f sec' % \
              (method.__name__, te-ts)
        return result

    return timed


#=========================================================================================
# Agent wrapper class for drop 4 alpha
#=========================================================================================
class RL_Agent_Wrapper(Agent_Wrapper, SM):
    '''
    This class wraps a bare agent algorithm to interface with a protocol manager
    '''
    
    def __init__(self, agent, epoch_len, num_stochastic_states, num_action_states, 
                 change_delay, mobile_ids, types_to_ints, 
                 reward_lookup_states, reward_lookup_vals,
                 initial_state=None, num_channels=1, do_episodic_learning=False,
                 lock_buffer_len=10, lock_policy=0):
    
        super(RL_Agent_Wrapper, self).__init__(agent)
        
        # this can't be initialized in init since the database must be created in the same
        # thread from which it will be used. 
        self.db = None
        
        self.startState = "init"
        
        self.epoch_len = epoch_len
        self._num_stochastic_states = num_stochastic_states
        self._num_action_states = num_action_states
        self._num_states = num_stochastic_states*num_action_states
        
        self._initial_state = initial_state
        
        self._last_action = None
        self._last_state = None

        self._change_delay = change_delay
        self._mobile_ids = mobile_ids
        
        
        self.types_to_ints = types_to_ints
        
        # parse reward state and values from comma separated list to lists of ints and floats
        reward_states = [int(i) for i in reward_lookup_states.split(',')]
        reward_vals = [float(i) for i in reward_lookup_vals.split(',')]
        
        # zip the reward lists up into a single dictionary
        self._reward_lookup=dict(zip(reward_states, reward_vals))
        self._optimal_reward = max(reward_vals)
        self._do_lock_policy = bool(lock_policy)
        # set up a buffer to track the recent rewards
        self._recent_rewards_ind = 0
        self._recent_rewards = np.nan*np.ones( (lock_buffer_len, 1))
        
        
        
        # only really needed for logging
        self._num_channels = num_channels
        
        self.epoch_num = 0
        self.frame_num = 0
    
        self.agent_log = logging.getLogger('agent')
        self.dev_log = logging.getLogger('developer')
        self.db_log = logging.getLogger('database')
        
        self.dev_log.info("using agent_log location %s",self.agent_log.handlers[0].baseFilename)
        self.dev_log.info("using db_log location %s",self.db_log.handlers[0].baseFilename)
        
    def getNextValues(self, state, inp):
        """
        Handle inputs and determine next value of outputs.
        
        Once every epoch_len frames, tell the agent to pick the next action
        """        
        next_state = self.getNextState(state, inp)
        state_counter = inp["state_counter"]
        self.epoch_num = inp["epoch_num"]
        self.frame_num = inp["frame_num"]
        
        # sched_params defaults to None if the agent didn't supply a new action
        sched_params = None
        
        # handle any first run setup
        if state == "init":
            
            # get the state_counter running
            state_counter = self.epoch_len-1
            
            # set the agent's first state
            if self._initial_state is None: 
                initial_agent_state = random.randrange(self._num_states)
            else:
                initial_agent_state = self._initial_state
            
            # do initial iteration of the agent
            action = self._agent.start(initial_agent_state)
            
            
             
            # get internal agent variables for logging
            agent_vars = self._agent.log_vars()
            agent_vars["state"]=int(initial_agent_state)
            agent_vars["action"]=int(action)
            # assume log is for the end of an epoch, so the first entry will be at -1
            agent_vars["epoch_num"]=int(self.epoch_num)-1
            agent_vars["frame_num"]=int(inp["frame_num"])
            
            pfs = PatternFrameSchedule()
            action_space = pfs.get_action_space()
            pattern_fields = pfs.PatternTuple._fields
            # store off action space and fields from action space pattern named tuple
            # to make log parsing easier
            agent_vars["action_space"] = action_space
            agent_vars["action_space_pattern_fields"]=pattern_fields
            agent_vars["number_digital_channels"] = self._num_channels
            self.agent_log.info("%s", json.dumps(agent_vars))
            
            # store off the results of the first run to be used in subsequent iterations
            self._last_action = action
            self._last_state = initial_agent_state
            
            # record when the action will first take effect and the frame number that the
            # current epoch began. Also record when the action is supposed to end and when
            # the current epoch will end. This is all needed for doing state estimation 
            # and computing the reward from the most recent agent action
            self._action_start = inp["frame_num"] + self._change_delay 
            self._epoch_start = inp["frame_num"]
            
            self._action_end = inp["frame_num"] + self._change_delay + self.epoch_len -1
            self._epoch_end = inp["frame_num"] + self.epoch_len -1
            
            sched_params = (action, self._action_start)
            
        # if in countdown, decrement the counter    
        elif state == "countdown":
            state_counter -=1
            
        # if the state duration is over, run the agent    
        elif state == "reset":
            state_counter = self.epoch_len-1
            
            # get a new state estimate 
            new_state = self.estimate_state()
            # compute the reward accrued during the most recent epoch
            reward = self.compute_reward()
            
            # update reward history and increment associated index
            self._recent_rewards[self._recent_rewards_ind] = reward
            self._recent_rewards_ind = (self._recent_rewards_ind +1)%self._recent_rewards.shape[0]
            
            # decide whether policy and exploration are frozen
            if all( self._recent_rewards == self._optimal_reward) & self._do_lock_policy:
                self.dev_log.info("recent rewards all equal to optimal reward, freezing policy")
                self._agent.freeze_policy(True)
                self._agent.freeze_exploring(True)
            
            # choose a new action
            action = self._agent.step(reward, new_state)
            
            self._last_action = action
            self._last_state = new_state
            
            # update start of action and epoch periods for next iteration
            self._action_start = inp["frame_num"] + self._change_delay
            self._epoch_start = inp["frame_num"]
            
            # update end of action and epoch periods for next iteration
            self._action_end = inp["frame_num"] + self._change_delay + self.epoch_len -1
            self._epoch_end = inp["frame_num"] + self.epoch_len -1
        
            sched_params = (action, self._action_start)
            
            # get internal agent variables for logging
            agent_vars = self._agent.log_vars()
            agent_vars["state"]=int(new_state)
            agent_vars["action"]=int(action)
            agent_vars["epoch_num"]=int(self.epoch_num)
            agent_vars["frame_num"]=int(inp["frame_num"])
            agent_vars["reward"]=float(reward)

            
            self.epoch_num = 1 + self.epoch_num
            
            
                        
            # log out agent vars
            self.agent_log.info("%s", json.dumps(agent_vars))
            
        outp = {"state_counter":state_counter,
                "sched_params":sched_params,
                "epoch_num":self.epoch_num}
        
        return (next_state, outp)     
            
    def getNextState(self, state, inp):
        """
        Manage a counter to trigger every epoch_len frames
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

    
    def estimate_state(self):
        '''
        This state estimator 
        '''
        
        # initialize link estimate variables
        
        
        dl_pkts_total = {} # dp_tx
        dl_pkts_good = {} # dp_fx_g
        dl_pkts_known = {} # dp_fx_a
        
        fb_pkts_good = {} # fp_rx
        #fb_pkts_total = {} # fp_tx 
        
        ul_pkts_total = {} # up_tx_a + fp_tx
        ul_pkts_good = {} # up_rx

        b_pkts_good = {} # bp_fx_g   
        b_pkts_known = {} # bp_fx_a   
                
        ul_pkts_first = {} # intermediate variable
        ul_pkts_last = {} # intermediate variable    
        
        with self.db.con as c:
            
            # pull out info for the specified epoch 
            rows = c.execute(
            """
            SELECT mobile_id, first_epoch_packet
            FROM epochs
            WHERE epoch_num == ?
            """, (self.epoch_num,))
            
            for r in rows:
#                self.db_log.debug("Epoch Query Result Row: %s",json.dumps(dict(r)))
                ul_pkts_first[r["mobile_id"]]= r["first_epoch_packet"] 
            
            # find the max packet numbers from each mobile
            rows = c.execute(
            """
            SELECT from_id, MAX(packet_num) as max_packet_num
            FROM packets 
            WHERE frame_num >= ? AND frame_num <= ? AND link_direction == 'up' 
                AND status == 'pass'
            GROUP BY from_id
            """, ( self._action_start, self._epoch_end))
            
            for r in rows:
#                self.db_log.debug("Packet Number Query from %i to %i Result Row: %s",
#                                  self._action_start, self._epoch_end,
#                                  json.dumps(dict(r)))
                
                ul_pkts_last[r["from_id"]]= r["max_packet_num"] 
            
            # estimate the total number of packets a given mobile has sent. If there's 
            # no feedback, store -1 as a sentinel value
            for mobile_id in self._mobile_ids:
                if mobile_id in ul_pkts_last and mobile_id in ul_pkts_first:
                    ul_pkts_total[mobile_id] = ul_pkts_last[mobile_id]-ul_pkts_first[mobile_id]+1
                else:
                    ul_pkts_total[mobile_id] = -1
               
            
            rows = c.execute(
            """
            SELECT link_direction, from_id, to_id, status, packet_code, COUNT(packet_guid) as num_packets
            FROM packets 
            WHERE frame_num >= ? AND frame_num <= ?
            GROUP BY link_direction, from_id, to_id, status, packet_code
            """, ( self._action_start, self._epoch_end))
            self.dev_log.info("running query on frames from %i to %i",
                              self._action_start, self._epoch_end)
            for r in rows:
#                self.db_log.debug("Packet Count Query from %i to %i Result Row: %s",
#                                  self._action_start, self._epoch_end,
#                                  json.dumps(dict(r)))
                
                if r["link_direction"] == 'up':
                    from_id = r["from_id"]
                    status = r["status"]
                    count = r["num_packets"]
                    packet_code = r["packet_code"]
                    
                    # sum up the good non-feedback packets
                    if status == "pass" and packet_code != self.types_to_ints["feedback"]:
                        ul_pkts_good[from_id] = ul_pkts_good.get(from_id,0) + count
                    
                    # sum up the good feedback packets
                    if status == "pass" and packet_code == self.types_to_ints["feedback"]:
                        fb_pkts_good[from_id] = fb_pkts_good.get(from_id,0) + count
                        
                elif r["link_direction"] == 'down':
                    to_id = r["to_id"]
                    count = r["num_packets"]
                    packet_code = r["packet_code"]
                    status = r["status"]
                    
                    # sum up all non-beacon downlink packets
                    if packet_code != self.types_to_ints["beacon"]:
                        dl_pkts_total[to_id] = dl_pkts_total.get(to_id,0) + count
                        
                    # sum up the good non-beacon packets
                    if status == "pass" and packet_code != self.types_to_ints["beacon"]:
                        dl_pkts_good[to_id] = dl_pkts_good.get(to_id,0) + count
                    
                    # sum up the non-beacon packets with known status
                    if (status == "pass" or status == "fail") and packet_code != self.types_to_ints["beacon"]:
                        dl_pkts_known[to_id] = dl_pkts_known.get(to_id,0) + count
                    
                    # sum up the good beacon packets 
                    if status == "pass" and packet_code == self.types_to_ints["beacon"]:
                        b_pkts_good[to_id] = b_pkts_good.get(to_id,0) + count
                        
                    # sum up the beacon packets with known status
                    if (status == "pass" or status == "fail") and packet_code == self.types_to_ints["beacon"]:
                        b_pkts_known[to_id] = b_pkts_known.get(to_id,0) + count
                

                               
        # now map packet counts to observable states per mobile
        dl_states = {}
        ul_states = {}
        b_states = {}
        mobile_states = {}
        
        for mobile_id in self._mobile_ids:
            # compute downlink state per mobile
            if dl_pkts_total.get(mobile_id,0) == 0 or fb_pkts_good.get(mobile_id,0) == 0:
                dl_states[mobile_id] = np.nan
            else:
                # assume default value of 0 good packets
                good_pkts = float(dl_pkts_good.get(mobile_id,0))
                if mobile_id not in dl_pkts_known:
                    self.dev_log.warning("inconsistent results: fb_pkts good is %i but mobile id %i not in dl_pkts_known",
                                         fb_pkts_good[mobile_id], mobile_id)
                    dl_states[mobile_id] = np.nan
                else:
                    dl_states[mobile_id] = (good_pkts/dl_pkts_known[mobile_id])>0
    
            # compute uplink state per mobile
            # assume default values of 0 good packets for feedback and uplink
            if ul_pkts_total[mobile_id] > 0:
                good_pkts = float(ul_pkts_good.get(mobile_id,0) + fb_pkts_good.get(mobile_id,0))
                ul_states[mobile_id] = (good_pkts/float(ul_pkts_total[mobile_id]))>0
            else:
                ul_states[mobile_id]=False
            # now compute beacon state
            if fb_pkts_good.get(mobile_id,0) == 0: 
                b_states[mobile_id]=False
            else:
                good_pkts = float(b_pkts_good.get(mobile_id,0))
                known_pkts = float(b_pkts_known.get(mobile_id,0))
                
                if known_pkts > 0:
                    b_states[mobile_id] = good_pkts/known_pkts>0
                    
                else:
                    b_states[mobile_id] = False
                    
            # map observable link states to mobile states
            mobile_states[mobile_id] = b_states[mobile_id] and ul_states[mobile_id] and dl_states[mobile_id]
                 
        # only need the values of mobile states, so pull them out into an array for easier
        # manipulation
        m_state_vals = np.array(mobile_states.values())
        
        # now compute the max possible bidirectional links given the mobile state values
        self.network_state = np.count_nonzero(m_state_vals==1) + np.count_nonzero(np.isnan(m_state_vals))
        
        # zero fill intermediate variables for easier log parsing
        for mobile_id in self._mobile_ids:
            dl_pkts_total[mobile_id] = dl_pkts_total.get(mobile_id,0)
            dl_pkts_good[mobile_id] = dl_pkts_good.get(mobile_id,0)
            dl_pkts_known[mobile_id] = dl_pkts_known.get(mobile_id,0)
            fb_pkts_good[mobile_id] = fb_pkts_good.get(mobile_id,0)
            ul_pkts_total[mobile_id] = ul_pkts_total.get(mobile_id,0)
            ul_pkts_good[mobile_id] = ul_pkts_good.get(mobile_id,0)
            b_pkts_good[mobile_id] = b_pkts_good.get(mobile_id,0)
            b_pkts_known[mobile_id] = b_pkts_known.get(mobile_id,0)
                         
        log_estimates = {"epoch_num":int(self.epoch_num),
                         "frame_num":int(self.frame_num),
                         "network_state":float(self.network_state),
                         "verbose_network_state":mobile_states,
                         "verbose_link_state":{"Ob":b_states,
                                               "Ou":ul_states,
                                               "Od":dl_states},
                         "dl_pkts_total":dl_pkts_total,
                         "dl_pkts_good":dl_pkts_good,
                         "dl_pkts_known":dl_pkts_known,
                         "fb_pkts_good":fb_pkts_good,
                         "ul_pkts_total":ul_pkts_total,
                         "ul_pkts_good":ul_pkts_good,
                         "b_pkts_good":b_pkts_good,
                         "b_pkts_known":b_pkts_known,
                         }
        
        self.db_log.info("%s", json.dumps(log_estimates))
         
        
        agent_state = np.ravel_multi_index((self.network_state, self._last_action), 
                                           dims=(self._num_stochastic_states,self._num_action_states))
        
        return agent_state
           
    def compute_reward(self):
        reward = self._reward_lookup[self.network_state]
        return reward 

    @staticmethod            
    def add_options(normal, expert):
        
                
        normal.add_option("", "--agent-reward-states", type="string", default="0, 1, 2", 
                          help="comma separated list of integers enumerating the possible states used in the reward lookup table of the 'lookup' reward estimation algorithm")

        normal.add_option("", "--agent-lock-buffer-len", type="int", default="10", 
                          help="number of consecutive times an agent must get the optimal reward before it locks policy and exploration")

        normal.add_option("", "--agent-lock-policy", type="int", default=0, 
                          help="If 1, lock policy after agent-lock-buffer-len consecutive optimal rewards")


        normal.add_option("", "--agent-reward-vals", type="string", default="-100, -10, 10", 
                          help="comma separated list of floats of the rewards corresponding to each element in reward_lookup_states")




        
#=========================================================================================
# Utility class for shared code for agent wrapper protocol manager 
#=========================================================================================
class shared_rl_agent_protocol_manager(object):
    '''
    Utility class for shared code between the mobile and base. Note that you should
    put this class first in the inheritance list if you want member functions declared 
    in this class to 'win' in name resolution when resolving member functions that exist
    in this class as well as other classes in the inheritance list
    '''
    PacketStatTuple = namedtuple('PacketStatTuple', 'packetid sourceID')
    BasePacketStatTuple = namedtuple('PacketStatTuple', 'packetid sourceID mobileID')
    def setup_headers(self, options):
        
        self.slot_manager_header_format = 'HH'
        self.slot_manager_header_names = 'first_epoch_packet epoch_num'

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
       
        new_tup = self.SlotManagerHeaderTuple(first_epoch_packet=0,
                                              epoch_num=0,)
        return new_tup

    @staticmethod
    def configure_action_space(options,fs):
        
        all_addresses = options.agent_mac_address_mapping
        options.agent_mac_address_mapping = [int(x) for x in all_addresses.split(',')]
        
        #TODO: stop hard coding directory, file, and set names
        # set up actions
        pfs = PatternFrameSchedule()
#        pattern_set = pfs.load_pattern_set_from_file(pattern_file="pattern_group1", 
#                                                     set_name="SET_01", 
#                                                     fs=self.fs)

        pattern_set = pfs.load_pattern_set_from_file(pattern_file=options.agent_pattern_file, 
                                                     set_name=options.agent_pattern_set, 
                                                     fs=fs)        
        if len(options.rf_frequency_list) > 0:
            rf_freq = [float(x) + float(options.rf_tx_freq) for x in options.rf_frequency_list.split(',')]
        else:
            rf_freq = list(set([options.rf_tx_freq, options.rf_rx_freq]))
            
        # store action space to class variable
        pfs.store_action_space(pattern_set=pattern_set, 
                               owner_ids=options.agent_mac_address_mapping,
                               rf_freqs=rf_freq)
        
        if len(options.agent_rendezvous_rf_band_list) > 0 and len(options.agent_rendezvous_dig_chan_list) > 0:
            
            # convert from comma separated strings to list of floats or ints
            sync_dig_chan_list = [int(x) for x in options.agent_rendezvous_dig_chan_list.split(',')]
            sync_rf_band_list = [float(x) + float(options.rf_tx_freq) in options.agent_rendezvous_rf_band_list.split(',')]
            
            if len(sync_dig_chan_list) == len(sync_rf_band_list):

                action_tuples = zip(sync_dig_chan_list, sync_rf_band_list)
                pfs.set_sync_space(['beacon_chan', 'rf_freq'], action_tuples)
                
            else:
                print "CANNOT SET BEACON SYNC PROPERLY - sync rf band list and sync dig chan list are not the same length"
                    
                   
         
#=========================================================================================
# Agent wrapper slot manager
#=========================================================================================
class base_rl_agent_protocol_manager(shared_rl_agent_protocol_manager, BaseSlotManagerDb):
    '''
    Manages the over the air protocol for agents. 
    ''' 
    

    def __init__(self, types_to_ints, options, tdma_mac, initial_time_ref, agent_wrapper):
        '''
        Declare any parameters needed by the slot manager here
        
        Keyword Arguments:
        
        ber_threshold    (float) 
        keepalive_num_bits (int)
        '''
        
        super(base_rl_agent_protocol_manager, self).__init__(types_to_ints, options, 
                                                            tdma_mac, initial_time_ref)
        
        self.setup_headers(options)
        
        self.current_schedule = PatternFrameSchedule(valid=True,
                                                     tx_gain=options.rf_tx_gain, # TODO: Plumb default tx gain
                                                     slot_bw=0, # TODO: Plumb slot bandwidth
                                                     )
        
        self.current_schedule.add_schedule(time_ref=initial_time_ref, 
                                           frame_num_ref=0, 
                                           first_frame_num=0, 
                                           action_ind=0,
                                           epoch_num=0)
        self.state_counter = 0


        self.schedule_change_delay = options.slot_assignment_leadtime
        self.downlink_packet_timeout = options.downlink_packet_feedback_timeout
        self.uplink_packet_timeout = options.uplink_packet_feedback_timeout

        sync_timeout = float('inf')
        
        self.is_first_iteration = True
        self.epoch_num = 0
        
        # start up agent here
        self._agent_wrapper = agent_wrapper
        self._agent_wrapper.start() 
        
        # store off the epoch length here
        self.epoch_len = self._agent_wrapper.epoch_len
    
        # get the ll_logging set of logs so we have access to the state log
        self.ll_logging = lincolnlog.LincolnLog(__name__)
#        self.statelog = self.ll_logging._statelog
        
        
    #@timeit    
    def track_slot_performance(self, mac_config, cur_frame_num, rf_in):
        '''
        Determine which slots should be assigned to which nodes
        
        This function should track the performance of each node in each slot and reassign
        slots that are not performing well. This should also remove queues for mobiles 
        that are no longer connected to the network. 
        
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
                       
            
            # sort out the packets addressed to me and not from me
            valid_pkts = [(meta, data) for meta, data in rf_in 
                          if meta["fromID"] != mac_config["my_id"] and
                          meta["toID"] ==  mac_config["my_id"]]
            
            # add valid packets to the database
            if self.db is not None:
                self.db.add_rx_packets(valid_pkts, TDMA_HEADER_LEN + PHY_HEADER_LEN + self.slot_manager_header_len, 
                                       "pass", 
                                       self.types_to_ints)
            
            # get the actual arrival slot and frame for each packet
            pkt_tups = self.packets_to_slot_and_frame(valid_pkts, mac_config)
            
            # find ack packets that arrived in the correct slot and frame
            for meta, data, frame_num, slot_num in pkt_tups:
                try:
                    
                    if "epoch_num" in meta and "first_epoch_packet" in meta:
                        self.dev_log.info("received packet num %i from epoch %i first packet num %i from mobile %i",
                                          meta["packetid"], meta["epoch_num"], 
                                          meta["first_epoch_packet"], meta["fromID"])
                      
                    if frame_num != meta["frameID"] or slot_num != meta["timeslotID"]:
                        self.dev_log.warning(("inconsistent packet. Sent in frame %i slot %i, " +
                                              "arrived in frame %i slot %i"),meta["frameID"],
                                             meta["timeslotID"],frame_num, slot_num)                                                        
    
                    if meta["pktCode"] == self.types_to_ints["feedback"]:
                        feedback_region, new_acks = self.unpack_feedback(meta, data, frame_num)
                        feedback_regions.append( (feedback_region, meta["fromID"]))
                        
                        for ack in new_acks:
                            self.dev_log.info("base received ack in frame %i for packet num %i sourceID %i from node %i",
                                       meta["frameID"], ack.packetid, ack.sourceID, ack.mobileID)
                    
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
        
        '''

        if self.is_first_iteration:
            # this can't be done in __init__ since it creates a database connection object
            # that can't be shared between threads
            self.initialize_database_tables(self.db_filename)
            
            # add a default schedule to start
            self.current_schedule.add_schedule(time_ref=self.initial_time_ref,
                                               frame_num_ref=frame_num,
                                               first_frame_num=frame_num,
                                               action_ind=0,
                                               epoch_num=self.epoch_num)
            # TODO: do any first run config of the agent here
            self._agent_wrapper.db = self.db
            
            self.is_first_iteration = False
            
                        
        next_sched = deepcopy(self.current_schedule)   
        
        # store off the new frame number so all the database machinery stays happy.     
        self.db.preload_frame_num(frame_num)    
        
        
        # iterate agent here
        inp = {"frame_num":frame_num,
               "state_counter":self.state_counter,
               "epoch_num":self.epoch_num}
        
        outp = self._agent_wrapper.step( (inp,False) )
        
        self.epoch_num = outp["epoch_num"]
        
        if outp["sched_params"] is not None:
            (action_ind, first_frame_num) = outp["sched_params"]
            
            # pull out info needed to compute the next schedule
            cur_time_ref = next_sched.time_ref
            cur_frame_num_ref = next_sched.schedule_seq[-1][1]
            cur_action_ind = next_sched.schedule_seq[-1][3]
            frame_len = next_sched._action_space[cur_action_ind]["frame_len"]
            
            # set the time and frame number references for the next schedule
            sched_frame_delta = frame_num - cur_frame_num_ref + 1
            
            next_time_ref = (cur_time_ref + frame_len*sched_frame_delta)
            
            next_frame_num_ref = frame_num + 1
            
            
            self.dev_log.info("Sending new schedule with epoch num %i to start at frame %i",
                              self.epoch_num, first_frame_num)
            
            next_sched.add_schedule(time_ref=next_time_ref,
                                    frame_num_ref=next_frame_num_ref,
                                    first_frame_num=first_frame_num,
                                    action_ind=action_ind,
                                    epoch_num=self.epoch_num)
            
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
        '''    
        
        # get framing parameters
        tdma_header_len = self.tdma_mac.get_tdma_header_len()
        phy_header_len = self.tdma_mac.get_phy_header_len()
        
        # store the current frame to the db if the db's initialized
        if self.db is not None:
            self.db.add_frame_config(frame_config, frame_num)
                
                
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

                    
                
                # build up class specific header field (in this case they are all common
                # for packets in the same slot  

                header_tup = self.SlotManagerHeaderTuple(first_epoch_packet=0,
                                                         epoch_num=self.epoch_num,)    
                
                # fill in placeholder fields
                for k, (meta, data) in enumerate(slot_pkts):
                    data = self.update_slot_manager_header(header_tup, 
                                                           data)
                    meta.update(header_tup._asdict())
                    slot_pkts[k] =  (meta, data) 
                
                                                
                
                tx_list+= slot_pkts
        
        # get the unique mobile ids for this frame        
        mobile_ids = set(s.owner for s in slots if s.type !="beacon" and s.owner > 0)
        
        # add transmitted packets to the db if it is initialized
        if self.db is not None:
            self.db.add_tx_packets(tx_list, frame_num,
                                    TDMA_HEADER_LEN + PHY_HEADER_LEN, 
                                    self.types_to_ints, mobile_ids)
            
        frame_num +=1     
     
        return frame_num, packet_count, tx_list, mobile_queues, dropped_pkts
    
    def unwrap_frame_num(self, wrapped_num, frame_count):
        
        if frame_count - wrapped_num > TDMA_HEADER_MAX_FIELD_VAL/2:
            # compute how many times the frame count has overflowed the packet frame
            # num field
            num_wraps = floor(frame_count/TDMA_HEADER_MAX_FIELD_VAL)
            
            # update the packet metadata what its actual value likely was
            unwrapped_num = int(num_wraps*(TDMA_HEADER_MAX_FIELD_VAL) 
                                  + wrapped_num)
            
            # make sure we didn't go one wrap too far
            if unwrapped_num > frame_count:
                unwrapped_num = unwrapped_num - TDMA_HEADER_MAX_FIELD_VAL; 
        else:
            unwrapped_num = wrapped_num
        
        return unwrapped_num     
                    
                
    def unpack_feedback(self, meta, data, frame_count):
        
        self.dev_log.debug("feedback packet len is %i", len(data))
        format_str = 'HHHH'
        feedback_region = struct.unpack(format_str, data[:struct.calcsize(format_str)])
        
        # hack to work around frame number wrap around in packet headers
        start_frame_num = feedback_region[0]
        
        start_frame_num = self.unwrap_frame_num(start_frame_num, frame_count)
        
        end_frame_num = feedback_region[2] 
        end_frame_num= self.unwrap_frame_num(end_frame_num, frame_count)        
        
        feedback_region = (start_frame_num, feedback_region[1], end_frame_num, feedback_region[3])
        
        # remove feedback region info from data
        data = data[struct.calcsize(format_str):]
        
        if len(data) > 0:
            # assume data is 16 bit unsigned ints
            format_str = 'H'*int(len(data)/2)
            data_seq = struct.unpack(format_str, data)
            
            # assume that data is actually list of PacketStatTuples (curently pairs)
            ack_list = [ self.BasePacketStatTuple(*a, mobileID=meta["fromID"]) 
                        for a in grouped( list(data_seq), 2)]
            
            
        else:
            ack_list = []
        
        return feedback_region, ack_list
    


    def initialize_database_tables(self, db_name):
        
        # initialize the database and pass it in to the base station state machine.              
        self.db = AgentDataInterface(flush_db=True, 
                                     time_ref = self.initial_time_ref, 
                                     db_name=db_name)
        
        
        if self.db is not None:
            
            self.tables_initialized = True
           
 
    
    def append_my_settings(self, indent_level, opts_xml):
        
        params = {
                  "schedule_change_delay":self.schedule_change_delay,
                  "downlink_packet_timeout":self.downlink_packet_timeout,
                  "uplink_packet_timeout":self.uplink_packet_timeout,
                  }
        opts_xml += "\n" + dict_to_xml(params, indent_level)
        
        
                   
        opts_xml = super(base_rl_agent_protocol_manager, self).append_my_settings(indent_level,
                                                                                   opts_xml)    
        return opts_xml
    
    @staticmethod            
    def add_options(normal, expert):
    
        BaseSlotManagerDb.add_options(normal, expert)
    

        normal.add_option("--slot-assignment-leadtime", type='int', default=4,
                          help="How many frames in advance to announce a schedule "+ 
                          "change [default=%default]")
        
        normal.add_option("--downlink-packet-feedback-timeout", type='int', default=4,
                          help="How many frames to wait for an ack before marking a " +
                               "packet as failed [default=%default]")
        
        normal.add_option("--uplink-packet-feedback-timeout", type='int', default=3,
                          help="How many frames to wait before declaring that an uplink" +
                               "packet has failed [default=%default]")
        
        normal.add_option("--agent-mac-address-mapping", type="string", 
                          help=("List of all node MAC addresses in the network, including self." ))
        
        normal.add_option("--rf-frequency-list", type="string", 
                          default="720e6, 725e6",
                          help="list of valid rf frequencies the front end can tune to" +
                                " [default=%default]")

        normal.add_option("--agent-pattern-file", type="string", 
                          default="pattern_group1",
                          help="frame pattern file to use with an agent" +
                                " [default=%default]")   

        normal.add_option("--agent-pattern-set", type="string", 
                          default="SET_01",
                          help="name of the set of frame patterns to use with an agent" +
                                " [default=%default]")           

        normal.add_option("--agent-rendezvous-rf-band-list", type="string", 
                          default="",
                          help="list of rf frequencies to search for beacons, should be 1-to-1 with agent-rendezvous-dig-chan-list")

        normal.add_option("--agent-rendezvous-dig-chan-list", type="string", 
                          default="",
                          help="list of digital channels to search for beacons, should be 1-to-1 with agent-rendezvous-rf-band-list")

        
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
# Mobile Agent wrapper slot manager
#=========================================================================================
class mobile_rl_agent_protocol_manager(shared_rl_agent_protocol_manager, MobileSlotManager):
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
        
        super(mobile_rl_agent_protocol_manager, self).__init__(types_to_ints, options, 
                                                               tdma_mac)
        
        self.setup_headers(options)
        
        self.slot_stat_history = {}
        
        self.last_action_ind = 0
        self.sync_deadline = None
        self.sync_timeout = options.agent_rendezvous_interval
        self.beacon_channel = 0
        
        self.first_epoch_packet = 0
        self.epoch_num = None
        

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
        
        # make sure pkt list exists so appends don't fail
        if "pktlist" not in self.slot_stat_history:
                        self.slot_stat_history["pktlist"] = []
        
        # add received beacon feedback to slot stat history
        for beacon_id, base_id in beacon_feedback:
            self.dev_log.info("storing beacon packet num %i to feedback history",beacon_id)
              
            self.slot_stat_history["pktlist"].append(self.PacketStatTuple(packetid=beacon_id, 
                                                                          sourceID=base_id))
            
        # only process if frame_config is defined
        if frame_config is not None:
                
            # unpack the class specific header info from the rf_packet list
            rf_in = [ (self.unpack_slot_manager_header(meta, data)) for (meta,data) in rf_in
                     if meta["crcpass"] == True and meta["pktCode"] != self.types_to_ints["beacon"] ]
                
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
                    
                    
                    self.dev_log.debug("storing packet id %i to packet list as good packet",meta["packetid"] )  
                    self.dev_log.info("received packet num %i sent in frame %i, slot %i during frame %i",
                                      meta["packetid"], meta["frameID"], meta["timeslotID"], cur_frame_num)  
                    self.slot_stat_history["pktlist"].append(self.PacketStatTuple(packetid=meta["packetid"], sourceID=meta["sourceID"]))
                     
        
            
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
        
                    
            
        # check if this is a new epoch
        if self.epoch_num != frame_config["epoch_num"]:
            # if this is a new epoch, update epoch tracking metadata
            self.first_epoch_packet = packet_count
            self.epoch_num = frame_config["epoch_num"]
            self.dev_log.info("starting epoch %i in frame %i. first packet is %i", 
                              self.epoch_num, frame_num, packet_count)
        
        
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
 
                header_tup = self.SlotManagerHeaderTuple(epoch_num=self.epoch_num,
                                                         first_epoch_packet=self.first_epoch_packet)
                
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
        
        # Safety check to make sure start and end frame nums don't overflow
        start_frame_num = start_frame_num%TDMA_HEADER_MAX_FIELD_VAL
        end_frame_num = end_frame_num%TDMA_HEADER_MAX_FIELD_VAL
        
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
    
    
    
    def acquire_sync(self, frame_config, current_ts, mac_config, reset):
        
        
        # handle first run
        if self.sync_deadline is None:
            self.sync_deadline = self.sync_timeout+current_ts
            self.last_action_ind = 0
            is_updated = True
            
        elif self.sync_deadline < current_ts:
            self.sync_deadline = self.sync_timeout + current_ts
            self.last_action_ind = (self.last_action_ind +1)%len(PatternFrameSchedule.sync_space)
            
            is_updated = True
        else:
            is_updated = False
        
        
        sync_action = PatternFrameSchedule.sync_space[self.last_action_ind]
        frame_len = PatternFrameSchedule._action_space[0]["frame_len"]
        new_frame_config = {
                        "t0":current_ts,
                        "frame_len":frame_len,
                        "slots":[SlotParamTuple(owner=mac_config["base_id"], 
                                                len=frame_len, 
                                                offset=0,
                                                type='beacon',
                                                rf_freq=sync_action["rf_freq"],
                                                bb_freq=sync_action["beacon_chan"],
                                                bw=0,
                                                tx_gain=0)]}
        
        if is_updated:

            self.dev_log.info("New Sync schedule: rf freq is %f, beacon chan is %s", 
                              sync_action["rf_freq"],
                              sync_action["beacon_chan"])
            
        uhd_cmd_tuple_list = [(current_ts, sync_action["rf_freq"], "txrx_tune")]
                        
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
            
            
        return frame_config            

    def append_my_settings(self, indent_level, opts_xml):
        
        # add components
        
           
        opts_xml = super(mobile_rl_agent_protocol_manager, self).append_my_settings(indent_level,
                                                                                    opts_xml)  
    
        return opts_xml
    
    @staticmethod     
    def add_options(normal, expert):
        
        MobileSlotManager.add_options(normal, expert)
        
        normal.add_option("--agent-rendezvous-interval", type='float', default=2.0,
                          help="How long, in seconds, a mobile should dwell at a given " +
                               "action index when it cannot detect beacons")
        
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
# Agent Specific Database
#=========================================================================================

class DataInterfaceError(Exception):
    def __init__(self, args):
        super(DataInterfaceError,self).__init__(args)
        
class TimeRefError(DataInterfaceError):
    def __init__(self):
        args = ("No time reference defined. Try calling load_time_ref() " + 
                "after the database is initialized")
        
        super(TimeRefError,self).__init__(args)

class AgentDataInterface(object):
    """
    Database interface object. 
    
    If you want acceptable performance, make sure the database is stored on a ramdisk.
    Use
    mkdir -p /tmp/ram
    sudo mount -t tmpfs -o size=512M tmpfs /tmp/ram
    
    to set up the ramdisk, where 512M is larger than the largest you expect your database to grow.
    """
    def __init__(self, flush_db=False, time_ref=None, db_name="/tmp/ram/performance_history.sqlite"):
        
        # fire up logging service
        self.dev_log = logging.getLogger('developer')
        self.x_log = logging.getLogger('exceptions')
        
        if time_ref is not None:
            self.time_ref = time_spec_t(math.floor(time_ref))
            self.dev_log.debug("setting database time reference to %s", self.time_ref)
        else:
            self.time_ref = None
            self.dev_log.debug("not setting database time at init. This must be done after " + 
                               " the database has been initialized by calling load_time_ref()")
            
        
        # open database file
        try:
            self.dev_log.debug("connecting to database file %s", db_name)
            self.con = sqlite3.connect(db_name)
            self.dev_log.debug("database connection successful")
        except sqlite3.OperationalError as err:
            self.dev_log.exception("Could not open database file named %s.\n" + 
                                   "If using a file on a ramdisk, try using:\n" + 
                                   "mkdir -p /tmp/ram\n" + 
                                   "sudo mount -t tmpfs -o size=512M tmpfs /tmp/ram\n", db_name)
            quit()
        
        db_expanded_name = os.path.expandvars(os.path.expanduser(db_name))
        self._db_path = os.path.dirname(os.path.abspath(db_expanded_name))
        self._db_basename = os.path.basename(os.path.abspath(db_expanded_name))
        
        # use Row wrapper so you can get at rows using field names and/or indexes
        self.con.row_factory = sqlite3.Row

        # make all text ascii only
        self.con.text_factory = str
        
        if flush_db:
            try:
                
                
                self.dev_log.debug("initializing database")
                self.init_database()
                self.dev_log.debug("database initialization complete")
            except Exception as error:
                self.dev_log.exception("Could not initialize the database: Exception %s", error)
                quit()
        
    def init_database(self):
        '''
        Flush out any existing data in the database and build all the tables from scratch
        '''
        
        
        foreign_keys_on_sql = """
        PRAGMA foreign_keys = ON;
        """
        
        foreign_keys_off_sql = """
        PRAGMA foreign_keys = OFF;
        """
        
        drop_tables_sql = """
        DROP TABLE IF EXISTS time_ref;
        DROP TABLE IF EXISTS packets;
        DROP TABLE IF EXISTS slots;
        DROP TABLE IF EXISTS frames;
        DROP TABLE IF EXISTS frame_nums;
        DROP TABLE IF EXISTS epochs;
        """
        
        time_ref_table_sql = """
        CREATE TABLE IF NOT EXISTS time_ref(
            id INTEGER PRIMARY KEY NOT NULL,
            t0 BLOB NOT NULL);
        """
        
        frame_num_table_sql = """
        CREATE TABLE IF NOT EXISTS frame_nums(
            frame_num INTEGER PRIMARY KEY NOT NULL
            );
        """        
        
        frame_table_sql = """
        CREATE TABLE IF NOT EXISTS frames(
            frame_num INTEGER PRIMARY KEY NOT NULL,
            frame_timestamp REAL NOT NULL,
            first_frame_num INTEGER NOT NULL,
            frame_len REAL NOT NULL,
            FOREIGN KEY(frame_num) REFERENCES frame_nums(frame_num) ON DELETE CASCADE
            );
        """
        
        slot_table_sql = """
        CREATE TABLE IF NOT EXISTS slots(
           frame_num INTEGER NOT NULL,
           slot_num INTEGER NOT NULL,
           channel_num INTEGER NOT NULL,
           rf_freq REAL NOT NULL,
           owner INTEGER NOT NULL,
           slot_len REAL NOT NULL,
           slot_offset REAL NOT NULL,
           slot_type TEXT NOT NULL,
           PRIMARY KEY (frame_num, slot_num, channel_num),
           FOREIGN KEY(frame_num) REFERENCES frame_nums(frame_num) ON DELETE CASCADE
           );
        """
        
        packet_table_sql = """
        CREATE TABLE IF NOT EXISTS packets(
            packet_guid INTEGER PRIMARY KEY NOT NULL,
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            destination_id INTEGER NOT NULL,
            packet_num INTEGER NOT NULL,
            packet_code INTEGER NOT NULL,
            link_direction TEXT NOT NULL,
            channel_num INTEGER NOT NULL,
            slot_num INTEGER NOT NULL,
            frame_num INTEGER NOT NULL,
            packet_timestamp REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY(frame_num) 
                REFERENCES frame_nums(frame_num) ON DELETE CASCADE
            -- FOREIGN KEY(frame_num, slot_num, channel_num) 
            --     REFERENCES slots(frame_num, slot_num, channel_num) 
            );           
        """
                
        epoch_table_sql = """
        CREATE TABLE IF NOT EXISTS epochs(
            epoch_num INTEGER NOT NULL,
            mobile_id INTEGER NOT NULL,
            first_epoch_packet INTEGER NOT NULL,
            PRIMARY KEY (epoch_num, mobile_id)
            );           
        """
                   
        with self.con as c:
            
            c.executescript(foreign_keys_off_sql)
            
            rows = c.execute("""
            SELECT name FROM sqlite_master WHERE type = 'table'
            """
            )
            table_names = [row["name"] for row in rows]
            
            for name in table_names:
                c.execute("DROP TABLE IF EXISTS %s"%name)
            
            
                
            c.executescript(foreign_keys_on_sql)
            c.executescript(frame_num_table_sql)
            c.executescript(time_ref_table_sql)
            c.executescript(frame_table_sql)
            c.executescript(slot_table_sql)
            c.executescript(packet_table_sql)
            c.executescript(epoch_table_sql)
            
            # insert the time reference into the database so other connections can access it
            c.execute("insert into time_ref(t0) values (?)", 
                      [pickle.dumps(self.time_ref)])

    def load_time_ref(self):
        '''
        Try to load in the database's time reference if this database interface didn't set it itself
        '''
        try:
            with self.con as c:
                for row in c.execute("SELECT t0 FROM time_ref ORDER BY ID ASC LIMIT 1"):
                
                    self.time_ref = pickle.loads(row["t0"])
                    self.dev_log.debug("setting database time reference to %s", self.time_ref)
                
            if self.time_ref is None:
                raise TimeRefError
            
        except DataInterfaceError as err:
            self.dev_log.exception("%s.%s: %s", err.__module__, err.__class__.__name__, 
                                   err.message)
            quit()
            
        except sqlite3.Error as err:
            
            self.dev_log.error("The database hasn't been properly initialized yet: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
    
    def preload_frame_num(self, frame_num):
        '''
        Get a frame number reference into the database first so all the foreign key checks
        don't fail
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
                 
        try:
            
            with self.con as c:
                #add to the frame table
                c.execute("""
                INSERT OR IGNORE INTO frame_nums(frame_num) values (?)
                """, (frame_num,))      
        
        except sqlite3.Error as err:
            
            self.dev_log.exception("error inserting frame number %i: %s.%s: %s", 
                                 frame_num, err.__module__, err.__class__.__name__, 
                                 err.message)            
                
    #@timeit         
    def add_frame_config(self, frame_config, frame_num):
        '''
        Add a new frame config file to the database, populating the frame and slots tables
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
                 
        try:
                
        
            first_frame_num = frame_config["first_frame_num"]
            frame_len = frame_config["frame_len"]
            frame_time_delta = (frame_num-frame_config["t0_frame_num"])*frame_len
            
            # compute the frame timestamp with respect to the database's reference time
            frame_timestamp = float(frame_config["t0"] - self.time_ref) + frame_time_delta
            
            # pull out the slot parameters we need for the database
            # store number of bits in slot as 0 for temporary placeholders
            slot_params = [(frame_num, k, s.owner, s.len, s.offset, s.type, s.bb_freq, 
                            s.rf_freq) 
                           for k,s in enumerate(frame_config["slots"])]
        
        
        
            with self.con as c:
                #add to the frame table
                c.execute("insert into frames" + 
                  "(frame_num, frame_timestamp, first_frame_num, frame_len) values " + 
                  "(?,?,?,?)", (frame_num, frame_timestamp, first_frame_num, frame_len))
                # add to the slot table
                c.executemany("insert into slots" + 
                  "(frame_num, slot_num, owner, slot_len, slot_offset, slot_type," +
                  " channel_num, rf_freq) " +
                  "values (?, ?, ?, ?, ?, ?, ?, ?)", slot_params)
        
        
        
        except sqlite3.Error as err:
            
            self.dev_log.exception("error inserting frame number %i: %s.%s: %s", 
                                 frame_num, err.__module__, err.__class__.__name__, 
                                 err.message)
    
    #@timeit        
    def add_tx_packets(self, packet_list, frame_num, packet_overhead, types_to_ints, mobile_ids):
        '''
        Add a list of packets to the database. Packet list items are tuples of (meta, data)
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
        
        
        if self.time_ref is None:
            self.dev_log.warning("Could not load time reference from database, so cannot store packets")
            return

        
        try:
            
            # add packets to database
            with self.con as c:
                
                for (meta, data) in packet_list:
                    
                    
                    
                    # get packet timestamp to be in respect to the database time reference
                    packet_timestamp = float(time_spec_t(meta["timestamp"])-self.time_ref)
                    

                    # make a placeholder beacon record for each mobile
                    if meta["pktCode"] == types_to_ints["beacon"]:
                        for mobile_id in mobile_ids:
                            packet_params= (meta["fromID"], mobile_id, meta["sourceID"],
                                               mobile_id, meta["packetid"], 
                                               meta["pktCode"], meta["linkdirection"],
                                               meta["frequency"],meta["timeslotID"],
                                               frame_num, packet_timestamp, "pending") 
                            
                            # add to the slot table
                            c.execute("insert into packets" + 
                              "(from_id, to_id, source_id, destination_id, packet_num," +
                              " packet_code, link_direction, channel_num, slot_num," + 
                              " frame_num, packet_timestamp, status) " +  
                              "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", packet_params)
                            
                    # otherwise just add the single packet        
                    else:
                        packet_params= (meta["fromID"], meta["toID"], meta["sourceID"],
                                               meta["destinationID"], meta["packetid"], 
                                               meta["pktCode"], meta["linkdirection"],
                                               meta["frequency"],meta["timeslotID"],
                                               frame_num, packet_timestamp, "pending") 
                      
            
                
                        # add to the slot table
                        c.execute("insert into packets" + 
                          "(from_id, to_id, source_id, destination_id, packet_num," +
                          " packet_code, link_direction, channel_num, slot_num," + 
                          " frame_num, packet_timestamp, status) " +  
                          "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", packet_params)
                
#                c.execute("UPDATE slots SET payload_bits=( SUM(payload_bits)  )

        except sqlite3.Error as err:
        
            self.dev_log.exception("error inserting tx packet:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
            
        except KeyError as err:
            self.dev_log.exception("key error: meta contents: %s ", meta)
            raise KeyError
            
    #@timeit
    def add_rx_packets(self, packet_list, packet_overhead, status, types_to_ints):
        '''
        Add a list of packets to the database. Packet list items are tuples of (meta, data)
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
        
        
        if self.time_ref is None:
            self.dev_log.warning("Could not load time reference from database, so cannot store packets")
            return

        
        try:
            
            # add packets to database
            with self.con as c:
                
                
                epoch_data = set()
                
                for (meta, data) in packet_list:
                    epoch_data= ( (meta["epoch_num"], meta["fromID"], 
                                     meta["first_epoch_packet"]) )
                    
                    # get packet timestamp to be in respect to the database time reference
                    packet_timestamp = float(time_spec_t(meta["timestamp"])-self.time_ref)
                    
                    
                    
                    packet_params= (meta["fromID"], meta["toID"], meta["sourceID"],
                                           meta["destinationID"], meta["packetid"], 
                                           meta["pktCode"], meta["linkdirection"],
                                           meta["frequency"],meta["timeslotID"],
                                           meta["frameID"],packet_timestamp, status) 
                    

                    
                    # add to the slot table
                    c.execute("insert into packets" + 
                      "(from_id, to_id, source_id, destination_id, packet_num," +
                      " packet_code, link_direction, channel_num, slot_num," + 
                      " frame_num, packet_timestamp, status) " +  
                      "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", packet_params)
                
            
                    c.execute("""
                    INSERT OR IGNORE INTO epochs
                    (epoch_num, mobile_id, first_epoch_packet)
                    values (?, ?, ?) 
                    """, epoch_data) 
                    
        except sqlite3.Error as err:
        
            self.dev_log.exception("error inserting rx packet: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)

#    @timeit        
    def update_packet_status(self, packet_list, status):
        """Update the packets in packet list to have a status given by the status param
        
        packet_list is a list of (packet_num, source_id) tuples. 
        status is a string containing either "pass" or "fail"
        """
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            update_params = [ (status, packet_num, source_id, mobile_id) 
                             for (packet_num, source_id, mobile_id) in packet_list]
            
            # update packets
            with self.con as c:
                c.executemany("UPDATE packets SET status=? " + 
                              "WHERE packet_num=? AND source_id=? AND to_id=?", update_params)    
        
        except sqlite3.Error as err:
        
            self.dev_log.exception("error updating packet status:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
    
#    @timeit
    def update_pending_tx_packets(self, num_frames):
        """
        Change the status of all pending packets that are at least num_frames old to "unknown"
        """
        
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            with self.con as c:
                
                # TODO: Consider choosing tx packets only by joining on slots and 
                # selecting packets from slots based on the slot type
                c.execute("UPDATE packets SET status='unknown' " + 
                          "WHERE frame_num NOT IN(SELECT frame_num FROM frames " + 
                          "ORDER BY rowid DESC LIMIT ?) " +
                          "AND status='pending' AND link_direction='down'",
                          (num_frames,))
                
        except sqlite3.Error as err:
        
            self.dev_log.exception("error updating pending tx packets:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
    
            
    def fail_missing_tx_packets(self, feedback_regions):
        """
        Find packets that occurred in a feedback region that were in a downlink slot 
        assigned to the node in the feedback_region's 'fromID' field
        change the status fields for any of those packets that have not been acked
        to 'fail' 
        """
        
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            with self.con as c:
                for (start_frame, start_slot, end_frame, end_slot), to_id in feedback_regions:
                    
                    c.execute("""
                    UPDATE packets SET status='imminentfail'
                    WHERE packet_guid IN
                        (SELECT packet_guid 
                         FROM packets
                         WHERE packet_timestamp >= 
                            (SELECT frame_timestamp + slot_offset
                             FROM frames, slots 
                             WHERE frames.frame_num=? AND slots.frame_num=? AND slot_num=?
                            ) 
                            AND packet_timestamp < 
                            (SELECT frame_timestamp + slot_offset + slot_len - .000000001
                            FROM frames, slots 
                            WHERE frames.frame_num=? AND slots.frame_num=? AND slot_num=?
                            )
                            AND status='pending' AND link_direction='down' AND to_id=?
                    )""",(start_frame, start_frame, start_slot,
                          end_frame, end_frame, end_slot, to_id) )
                    
                    c.execute("""
                    UPDATE packets SET status='fail'
                    WHERE packet_guid IN
                        (SELECT packet_guid 
                         FROM packets
                         WHERE status='imminentfail' AND link_direction='down' AND to_id=? 
                         AND packet_timestamp < 
                            (SELECT frame_timestamp + slot_offset
                             FROM frames, slots 
                             WHERE frames.frame_num=? AND slots.frame_num=? AND slot_num=?
                            )
                        )
                    """, (to_id, start_frame, start_frame, start_slot))
                    
                    
                
        except sqlite3.Error as err:
        
            self.dev_log.exception("error failing missing tx packets:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)                
    
#    @timeit    
    def prune_tables(self, frame_window):
        """
        keep only the most recent frame_window frames
        """
        
        disk_stats = os.statvfs(self._db_path) 
        db_size = float(os.path.getsize(os.path.join(self._db_path, self._db_basename)))
        disk_free_space = float(disk_stats.f_bavail*disk_stats.f_frsize)
        #disk_total_space = float(disk_stats.f_blocks*disk_stats.f_frsize)
        
        percent_free_use = db_size/(db_size+disk_free_space)*100
        
        if percent_free_use > 50:
            self.dev_log.warning("Database size of %f MB is using %f %% of available space on mount point.",
                                 db_size/(2**20), percent_free_use)
        self.dev_log.debug("Database size before pruning: %f MB", db_size/(2**20))
        try:
            with self.con as c:
                c.execute("DELETE FROM frame_nums " + 
                          "WHERE rowid NOT IN(SELECT rowid FROM frame_nums " + 
                          "ORDER BY rowid DESC LIMIT ?)", (frame_window,))
        
                c.execute("DELETE FROM epochs " + 
                          "WHERE rowid NOT IN(SELECT rowid FROM epochs " + 
                          "ORDER BY rowid DESC LIMIT ?)", (frame_window,))
                
        except sqlite3.Error as err:
        
            self.dev_log.exception("error pruning tables", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
            
      
    
#    @timeit        
    def count_recent_rx_packets(self, num_frames, types_to_ints):
        """
        Count the number of packets received in the last frame_window frames
        """
        
        num_packets = 0
        
        try:
            with self.con as c:
                # count the number of non-dummy uplink packets in the last n frames 
                rows = c.execute("""
                SELECT COUNT(*) as num_packets
                FROM packets
                WHERE packet_code<>? AND link_direction = 'up' AND 
                packets.frame_num IN(
                    SELECT frame_num FROM frames 
                    ORDER BY rowid DESC LIMIT ?
                    )
                """, (types_to_ints["dummy"], num_frames))
                
                for row in rows:
                    num_packets = row["num_packets"]
                    
            return num_packets

        except sqlite3.Error as err:
        
            self.dev_log.exception("error retrieving number of received packets: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
            return num_packets                      
   
