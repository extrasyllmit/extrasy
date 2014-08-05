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
import math
from pprint import pprint
import sys
import threading
import time
# third party library imports

# project specific imports
from digital_ll import time_spec_t



class power_controller():

    def __init__(self, options):

        self.max_tx_gain  = max(min(options.rf_power_control_max_tx_gain,31.5),1.0)
        self.min_tx_gain  = min(max(options.rf_power_control_min_tx_gain,0.0),31.5)
        self.init_tx_gain = max(min(options.rf_tx_gain,31.5),0.0)

        options.rf_power_control_stepsizes = [float(x) for x in options.rf_power_control_stepsizes.split(',')]
        self.gain_steps = options.rf_power_control_stepsizes

        options.rf_power_control_thresholds = [float(x) for x in options.rf_power_control_thresholds.split(',')]
        self.ber_thresholds = options.rf_power_control_thresholds

        self.agc_N_frames = options.rf_power_control_sense_window

        self.beacon_gain = options.rf_tx_gain
        self.beacon_step = 1.0
        self.beacon_margin = 6.0 

        self.num_mobiles = len(options.sink_mac_addresses)
        self.downlink_owner_gain_dict = {}
        
        #uplink power control parameters
        self.pwr_control_up = options.rf_power_control_enabled
        self.init_uplink_tx_gain = self.init_tx_gain        
        self.uplink_owner_gain_dict = {}
        
    def optimize_power(self, frame_count, next_sched, link_database, dev_log):    
        time_gain_tuple_list = []
            
        def adjust_downlink_gain(owner, total_bits, fail_bits, recent_frame_num):
            if owner in self.downlink_owner_gain_dict:
                (previous_gain, previous_total_bits, previous_fail_bits, previous_frame_num, last_updated_frame) = self.downlink_owner_gain_dict[owner]
                if previous_total_bits == 0:
                    previous_ber = 1.0
                else:
                    previous_ber = float(previous_fail_bits)/float(previous_total_bits)
                    
                if (total_bits == 0):
                    #ber = 1.0
                    #increase gain slowly when no feedbacks
                    ber = self.ber_thresholds[3]
                else:
                    ber = float(fail_bits)/float(total_bits) 
                                                           
                dev_log.debug("downlink owner %i, total bits %i, fail bits %i, recent frame num %i", owner, total_bits, fail_bits, recent_frame_num)

                if (((previous_ber <= self.ber_thresholds[2]) and (ber > self.ber_thresholds[2])) or (recent_frame_num == -1) or
                    (recent_frame_num > last_updated_frame + self.agc_N_frames)):

                    #dev_log.debug("Previous BER: %f. Current BER: %f", previous_ber, ber)
                    #dev_log.debug("Previous gain : %.1f", previous_gain)
                    
                    if ber > self.ber_thresholds[3]:
                        new_gain = min(previous_gain + self.gain_steps[3], self.max_tx_gain)
                    elif ber > self.ber_thresholds[2]:
                        new_gain = min(previous_gain + self.gain_steps[2], self.max_tx_gain)
                    elif ber > self.ber_thresholds[1]:
                        new_gain = min(previous_gain + self.gain_steps[1], self.max_tx_gain)
                    else:
                        new_gain = max(previous_gain + self.gain_steps[0], self.min_tx_gain)

                    #dev_log.debug("New gain : %0.1f", new_gain)                        
                    updated_frame = recent_frame_num                                
                else:
                    new_gain = previous_gain
                    updated_frame = last_updated_frame
                                        
                self.downlink_owner_gain_dict[owner] = (new_gain, total_bits, fail_bits, recent_frame_num, updated_frame)            
            else:
                #register owner first time, don't know anything, just use default gain
                self.downlink_owner_gain_dict[owner] = (self.init_tx_gain, total_bits, fail_bits, recent_frame_num, 0)
            
            return self.downlink_owner_gain_dict[owner][0]
           
        def adjust_uplink_gain(owner, total_bits, fail_bits, recent_frame_num):
            if owner in self.uplink_owner_gain_dict:
                (previous_gain, previous_total_bits, previous_fail_bits, previous_frame_num, last_updated_frame) = self.uplink_owner_gain_dict[owner]
                if previous_total_bits == 0:
                    previous_ber = 1.0
                else:
                    previous_ber = float(previous_fail_bits)/float(previous_total_bits)
                    
                if (total_bits == 0):
                    ber = 1.0
                else:
                    ber = float(fail_bits)/float(total_bits) 
                
                dev_log.debug("uplink owner %i, total bits %i, fail bits %i, recent frame num %i", owner, total_bits, fail_bits, recent_frame_num)
                                                           
                if (((previous_ber <= self.ber_thresholds[2]) and (ber > self.ber_thresholds[2])) or (recent_frame_num == -1) or
                    (recent_frame_num > last_updated_frame + self.agc_N_frames)):

                    #dev_log.debug("Previous BER: %f. Current BER: %f", previous_ber, ber)
                    #dev_log.debug("Previous gain : %.1f", previous_gain)
                    
                    if ber > self.ber_thresholds[3]:
                        new_gain = min(previous_gain + self.gain_steps[3], self.max_tx_gain)
                    elif ber > self.ber_thresholds[2]:
                        new_gain = min(previous_gain + self.gain_steps[2], self.max_tx_gain)
                    elif ber > self.ber_thresholds[1]:
                        new_gain = min(previous_gain + self.gain_steps[1], self.max_tx_gain)
                    else:
                        new_gain = max(previous_gain + self.gain_steps[0], self.min_tx_gain)

                    #dev_log.debug("New gain : %0.1f", new_gain)                        
                    updated_frame = recent_frame_num                                
                else:
                    new_gain = previous_gain
                    updated_frame = last_updated_frame
                                        
                self.uplink_owner_gain_dict[owner] = (new_gain, total_bits, fail_bits, recent_frame_num, updated_frame)            
            else:
                #register owner first time, don't know anything, just use default gain
                self.uplink_owner_gain_dict[owner] = (self.init_uplink_tx_gain, total_bits, fail_bits, recent_frame_num, 0)
            
            return self.uplink_owner_gain_dict[owner][0]
           

        ##################################################################
        unique_links = next_sched.get_unique_links()
        for (owner,linktype) in unique_links:
            if (linktype == 'downlink') and (owner > 0):                
                packet_list = link_database.get_total_bits_to_user(owner, self.agc_N_frames)
                total_bits = 0
                fail_bits = 0
                recent_frame_num = -1                    
                if len(packet_list) > 0:
                    total_bits = sum([p[1] for p in packet_list])
                    fail_bits = sum([p[1] for p in packet_list if p[0] == 'fail'])
                    recent_frame_num = max([p[2] for p in packet_list])
                
                downlink_tx_gain = adjust_downlink_gain(owner, total_bits, fail_bits, recent_frame_num)
                next_sched.store_tx_gain(owner, linktype, downlink_tx_gain)
                              
            elif (linktype == 'beacon'):
                #case when not all downlink gains are established yet
                if len(self.downlink_owner_gain_dict) < self.num_mobiles:
                    self.beacon_gain = self.beacon_gain + self.beacon_step
                #case when all downlink gains are available
                else:
                    self.beacon_gain = max([mobile_tuple[0] for mobile_tuple in self.downlink_owner_gain_dict.itervalues()]) + self.beacon_margin
                
                self.beacon_gain = min(self.beacon_gain, self.max_tx_gain)
                next_sched.store_tx_gain(owner, linktype, self.beacon_gain)
                
            elif (linktype == 'uplink') and (owner > 0):
                if self.pwr_control_up:
                    packet_list = link_database.get_total_bits_from_user(owner, self.agc_N_frames)
                    total_bits = 0
                    fail_bits = 0
                    recent_frame_num = -1                    
                    if len(packet_list) > 0:
                        total_bits = sum([p[1] for p in packet_list])
                        fail_bits = sum([p[1] for p in packet_list if p[0] == 'fail'])
                        recent_frame_num = max([p[2] for p in packet_list])
                
                    uplink_tx_gain = adjust_uplink_gain(owner, total_bits, fail_bits, recent_frame_num)
                    next_sched.store_tx_gain(owner, linktype, uplink_tx_gain)
                else:
                    next_sched.store_tx_gain(owner, linktype, self.init_uplink_tx_gain)            

        return next_sched
        

