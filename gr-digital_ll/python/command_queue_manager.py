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
import logging
import math
from pprint import pprint
import sys
import threading
import time

# third party library imports
from gnuradio import gr
from gnuradio import uhd
from gruel import pmt

# project specific imports
from digital_ll import lincolnlog
from digital_ll import time_spec_t
from digital_ll import uhd_time_spec_t_builder
from digital_ll.lincolnlog import dict_to_xml

class command_queue_manager(gr.basic_block):

    def __init__(self, uhd_sink, uhd_source=None):
        gr.basic_block.__init__(
              self,
              name = "Command Queue Manager Block",
              in_sig = None,
              out_sig = None)
        
        self.dev_log = logging.getLogger('developer')

        self.uhd_sink = uhd_sink
        self.uhd_source = uhd_source
        
        self.current_gain = 0.0
              
        self.reservation = threading.BoundedSemaphore(1)
        
        #example : [(time_spec_t(1367432337,0.276619),10, 'tx_gain'), (time_spec_t(1367432338,0.276619),12, 'tx_freq')]
        self.time_gain_tuple_list = []
        #pick maximum uhd lead time and minimum processing time in the for loop below
        self.period = 0.1 #make this about or less than the frame set up time
        self.queue_size_limit = 100
        self.max_drops = 20 #reset entire queue if there are too many drops
        
        self.time_sync_done = False        
        
        self.gps_offset = 0
        
        self.current_time_ahead = 0
        
        # set up and register input ports
        self.TIME_CAL_IN_PORT = pmt.from_python('time_tag_shift')
        self.message_port_register_in(self.TIME_CAL_IN_PORT)
        self.set_msg_handler(self.TIME_CAL_IN_PORT, self.store_gps_offset)
        
        # get the ll_logging set of logs so we have access to the state log
        self.ll_logging = lincolnlog.LincolnLog(__name__)
        self.statelog = self.ll_logging._statelog  

        
        def _fulltime_manager():
            while True:
                self.process_command_queue()                            
                time.sleep(0.01)    #make this timer x number slots/second << 16                
                                           
        _manager_thread = threading.Thread(target=_fulltime_manager)
        _manager_thread.daemon = True
        _manager_thread.start()

    def store_gps_offset(self, msg):
        
        self.gps_offset = pmt.pmt_to_long(msg)

    def process_command_queue(self):
        self.reservation.acquire()      
        if len(self.time_gain_tuple_list) > 0:                        
            #need to rewrite code to avoid calling get_time_now()
            #current_uhd_time = self.uhd_sink.u.get_time_now()
            #current_real_uhd_time = current_uhd_time.get_real_secs()
            #current_frac_uhd_time = current_uhd_time.get_frac_secs() #type double
            #current_time_spec_t_uhd_time = time_spec_t( math.floor(current_real_uhd_time), current_frac_uhd_time)
            
            #alternative to keep calling uhd time
            t1 = time.time() - self.current_time_ahead
            current_time_spec_t_uhd_time = time_spec_t(t1)
            
            #print "current uhd time is                      %s" % current_time_spec_t_uhd_time
            #pprint(self.time_gain_tuple_list)
            
            pop_list = []
            m = 0
            n = 0
            #self.u.set_center_freq(uhd.tune_request(freq,10e6), 0)
            for idx, (cmd_time, cmd_value, cmd_type) in enumerate(self.time_gain_tuple_list):
                if cmd_type == "time_cal":
#                    self.dev_log.info("received calibration command at uhd time %s with command time %s and value %s. Delta is %f",
#                                      current_time_spec_t_uhd_time, cmd_time, cmd_value,
#                                      cmd_time-current_time_spec_t_uhd_time)
                    
#                    command_time_delta = cmd_time-current_time_spec_t_uhd_time
#                    # the time cal command should come in very close to the current time.
#                    # if it's more than a half a second off in either direction, the uhd 
#                    # time is probably off by a second. 
#                    if command_time_delta < -.5:
#                        self.dev_log.info("Time cal command is more than half a second " +
#                                           "in the past. Adjusting current time ahead " +
#                                           "from %f to %f",self.current_time_ahead,
#                                           self.current_time_ahead+1 )
#                        
#                        self.current_time_ahead+=1
#                    elif command_time_delta > .5:
#                        self.dev_log.info("Time cal command is more than half a second " +
#                                           "in the future. Adjusting current time ahead " +
#                                           "from %f to %f",self.current_time_ahead,
#                                           self.current_time_ahead-1 )
#                        
#                        self.current_time_ahead-=1    

                    
                    pop_list.append(idx)
                    n = n + 1
                
                elif cmd_time <= current_time_spec_t_uhd_time:
                    #print "stale time %s, remove invalid command" % str(cmd_time)
                    pop_list.append(idx)
            
                    m = m + 1
                    
                    if cmd_type =="txrx_tune":
                        self.dev_log.warn("Tune command time of %s is stale. Current time is %s",
                                          cmd_time, current_time_spec_t_uhd_time)   
                        
                        self.log_tune_command(cmd_time, cmd_value, True) 
                    
                elif (cmd_time - current_time_spec_t_uhd_time) <= self.period:
                    #print "submit command with time %s to UHD queue" % str(cmd_time)
                    uhd_cmd_time_builder = uhd_time_spec_t_builder(cmd_time.int_s(), 
                                                                   cmd_time.frac_s())
                    uhd_cmd_time = uhd_cmd_time_builder.time_spec_t()

                    if cmd_type == 'tx_gain':
                        
                        self.uhd_sink.u.set_command_time(uhd_cmd_time)    
                        self.uhd_sink.u.set_gain(cmd_value,0)
                        self.uhd_sink.u.clear_command_time()
                        
                    elif cmd_type =="txrx_tune":
                        self.dev_log.debug("Tuning tx and rx to %f at command time %s, current time %s", 
                                           cmd_value, cmd_time, current_time_spec_t_uhd_time)
                        
                        self.uhd_sink.u.set_command_time(uhd_cmd_time)
                        self.uhd_sink.u.set_center_freq(uhd.tune_request(cmd_value,10e6), 0)
                        self.uhd_sink.u.clear_command_time()
                        
                        
                        self.uhd_source.u.set_command_time(uhd_cmd_time)
                        self.uhd_source.u.set_center_freq(uhd.tune_request(cmd_value,10e6), 0)
                        self.uhd_source.u.clear_command_time()
                        
                        self.log_tune_command(cmd_time, cmd_value, False)
                        
                    
                    pop_list.append(idx)
                    n = n + 1
                else:
                    #assume command time list is in increasing order
                    break
                    
            #need to sort pop_list in reverse, otherwise won't pop correctly
            for idx in sorted(pop_list, reverse=True):
                self.time_gain_tuple_list.pop(idx)
                                                    
            #print "Drop %i stale commands and submit %i commands to UHD queue" % (m,n)
            if m > 0:
                self.dev_log.debug("Dropped %i stale commands to UHD queue", m)
                #if too many drops, reset entire queue so there's a chance to recover
                if m >= self.max_drops:
                    self.time_gain_tuple_list = []
            
        self.reservation.release()
            
        
    def add_command_to_queue(self,time_gain_tuple_list):
        self.reservation.acquire() 

             
        if len(self.time_gain_tuple_list) < self.queue_size_limit:
                            
            corrected_tuple_list = [ (t[0]-self.gps_offset,) + t[1:] for t in time_gain_tuple_list ]
            
            for (cmd_time, cmd_value, cmd_type) in time_gain_tuple_list:
                self.dev_log.debug("processing command type %s, value %s for raw time %s, corrected time %s",
                                   cmd_type, cmd_value, cmd_time, cmd_time-self.gps_offset )

            
            self.time_gain_tuple_list += corrected_tuple_list
            #self.process_command_queue()
        self.reservation.release()

    def log_tune_command(self, cmd_time, freq, dropped):
        
        params = {
                  "timestamp":str(cmd_time),
                  "freq":freq,
                  "dropped":dropped
                  }
        
        param_xml = dict_to_xml(params, 1)
        
        tune_log_xml = ("<rf_tune>\n" + 
                        "%s\n" + 
                        "</rf_tune>") % param_xml
                        
        self.statelog.info(tune_log_xml)
    
    def set_current_time_ahead(self, time_ahead):
        self.current_time_ahead = time_ahead     
