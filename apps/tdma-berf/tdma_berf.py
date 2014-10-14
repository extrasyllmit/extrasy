#!/usr/bin/env python
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
from argparse import ArgumentParser
import commands
from ConfigParser import SafeConfigParser
from copy import deepcopy
import logging.config
from math import ceil
from optparse import OptionParser
import re
import sys
import time

# third party library imports
from gnuradio.eng_option import eng_option
from gnuradio import gr
from gnuradio import gru
from gnuradio import uhd

import numpy

# project specific imports
import digital_ll
from digital_ll import beacon_consumer
from digital_ll import channelizer
from digital_ll import lincolnlog
from digital_ll.lincolnlog import dict_to_xml
from digital_ll.lincolnlog import log_levels
from digital_ll import modulation_utils
from digital_ll import parse_frame_file
from digital_ll import receive_path_gmsk
from digital_ll import tdma_types_to_ints
from digital_ll import tdma_logger
from digital_ll import time_tag_shifter
from digital_ll import PatternFrameSchedule
from digital_ll import uhd_error_codes
from digital_ll import uhd_receiver
from digital_ll import uhd_transmitter

import mac_ll
from mac_ll import Infinite_Backlog_PDU_Streamer
from mac_ll import Tunnel_Handler_PDU_Streamer
from mac_ll import base_slot_manager_ber_feedback
from mac_ll import mobile_slot_manager_ber_feedback

from mac_ll import tdma_base_sm
from mac_ll import tdma_controller
from mac_ll import tdma_mobile_sm



class my_top_block(gr.top_block):
    def __init__(self, modulator, demodulator, options, ll_logging, dev_log, start_tb_time, time_cal_timeout, start_controller_time):
        gr.top_block.__init__(self)
        
        # Get the modulation's bits_per_symbol
        args = modulator.extract_kwargs_from_options(options)
        symbol_rate = options.modulation_bitrate / modulator(**args).bits_per_symbol()
        
        # all subsequent code expects list of ints, so convert from 
        # comma separated string
        sink_addresses = options.sink_mac_addresses
        options.sink_mac_addresses = [int(x) for x in sink_addresses.split(',')]

        # Direct asynchronous notifications to callback function
        if True:#self.options.show_async_msg:
            self.async_msgq = gr.msg_queue(0)
            self.async_src = uhd.amsg_source("", self.async_msgq)
            self.async_rcv = gru.msgq_runner(self.async_msgq, self.async_callback)

        self.dev_log = dev_log
        
        # how much time should be spent calibrating time sync?
        self.cal_time = time_cal_timeout
      
        self.rx_channelizer = channelizer.rx_channelizer(options, dev_log)
        self.tx_channelizer = channelizer.tx_channelizer(options, dev_log)
        self.rx_channelizer.set_beacon_channel(options.gpsbug_cal_channel)
        upsampled_symbol_rate = symbol_rate*options.digital_freq_hop_num_channels
        upsample_factor_usrp = options.digital_freq_hop_num_channels

        #setting up USRP RX
        self.source = uhd_receiver(options.usrp_args, upsampled_symbol_rate,
                                       options.modulation_samples_per_symbol,
                                       options.rf_rx_freq, options.rf_rx_gain,
                                       options.usrp_spec, "RX2",
                                       options.verbose)
            
        #setting up USRP TX
        self.sink = uhd_transmitter(options.usrp_args, upsampled_symbol_rate,
                                        options.modulation_samples_per_symbol,
                                        options.rf_tx_freq, options.rf_tx_gain,
                                        options.usrp_spec, "TX/RX",
                                        options.verbose)

        if self.source._sps != options.modulation_samples_per_symbol:
            self.dev_log.warning("The USRP does not support the requested sample rate of %f. Using %f instead",
                                    options.modulation_samples_per_symbol*upsampled_symbol_rate,
                                    self.source._sps*upsampled_symbol_rate)

        options.modulation_samples_per_symbol = self.source._sps
        
        self.digital_scaling = gr.multiply_const_vcc((options.digital_scale_factor,))
        
        # moved down here (after reassignment of self.source._sps so we can use
        # the actual sample rate the UHD is using
        self.fs = options.modulation_samples_per_symbol*upsampled_symbol_rate/upsample_factor_usrp
        
        self.pmt_rpc = digital_ll.pmt_rpc(obj=self,result_msg=False)
        
        self.start_tb_time = start_tb_time
        self.start_controller_time = start_controller_time
        
        # this helps control dc tone problem (Use to be burst_gate now eob_shifter)
        # TODO: Only programmed for GMSK. Other modulations will need additional work.
        upsample_factor = 8*options.modulation_samples_per_symbol*options.digital_freq_hop_num_channels
        self.eob        = digital_ll.eob_shifter(upsample_factor)

        num_d_chans = options.digital_freq_hop_num_channels
      
        if  options.tx_access_code == '0':
            tx_access_code = None
        elif options.tx_access_code == '1':
            tx_access_code = '0000010000110001010011110100011100100101101110110011010101111110'
        elif options.tx_access_code == '2':
            tx_access_code = '1110001100101100010110110001110101100000110001011101000100001110'   
        else:
            tx_access_code = options.tx_access_code
            
        print 'tx access code: %s' % tx_access_code   
   
        self.packet_framer = digital_ll.packet_framer(
            fs=self.fs,
            samples_per_symbol=options.modulation_samples_per_symbol,
            bits_per_symbol=1,
            access_code=tx_access_code,
            number_digital_channels=num_d_chans
        )
        
        if options.node_role == "tdma_base":
            self.tdma_mac_sm = tdma_base_sm(options, self.sink, self.source, 
                                            self.packet_framer.num_bytes_to_num_samples)
            
            self.frame_sched = parse_frame_file(options.frame_file,start_controller_time, self.fs)
            
            for k, slot in enumerate(self.frame_sched["slots"]):
                self.frame_sched["slots"][k] = slot._replace()
                
                # replace the rf_freq field with the value of tx_freq from the ini or 
                # command line for the slots transmitted by the base
                if (slot.type == "downlink") or (slot.type == "beacon"):
                    self.frame_sched["slots"][k] = slot._replace(rf_freq=options.rf_tx_freq,
                                                                 tx_gain=options.rf_tx_gain,
                                                                 bw=self.fs)
                    
                # replace the rf_freq field with the value of rx_freq from the ini or 
                # command line for the slots received by the base
                elif slot.type == "uplink":
                    self.frame_sched["slots"][k] = slot._replace(rf_freq=options.rf_rx_freq,
                                                                 tx_gain=options.rf_tx_gain,
                                                                 bw=self.fs)
                    

                
                
        else:
            self.tdma_mac_sm = tdma_mobile_sm(options, self.sink, self.source,
                                              self.packet_framer.num_bytes_to_num_samples)
            self.frame_sched = None
        
                
        if self.tdma_mac_sm.is_base():
                
            manage_slots = base_slot_manager_ber_feedback(tdma_types_to_ints, 
                                                          initial_schedule=self.frame_sched,
                                                          options=options,
                                                          tdma_mac = self.tdma_mac_sm,)
            
            
        else:
                
            manage_slots = mobile_slot_manager_ber_feedback(tdma_types_to_ints, 
                                                            options=options,
                                                            tdma_mac = self.tdma_mac_sm,)

            
        self.dev_log.info("starting at time %s", start_tb_time)
        self.tdma_controller = tdma_controller(options=options, 
                                               mac_sm=self.tdma_mac_sm,
                                               manage_slots=manage_slots, 
                                               fs=self.fs, 
                                               mux_name="scheduled_mux",
                                               rx_channelizer_name="rx_channelizer",
                                               fhss_flag=1, 
                                               start_time=start_controller_time,
                                               )
        
        
        if options.traffic_generation == "infinite": 
            self.traffic = Infinite_Backlog_PDU_Streamer( options, 
                                                 self.tdma_controller.app_queue_size )
            self.msg_connect(self.traffic, "out_pkt_port", self.tdma_controller,'from_app')
        
        elif options.traffic_generation == "tunnel":
            self.traffic = Tunnel_Handler_PDU_Streamer(options)
            self.msg_connect(self.traffic, "out_pkt_port", self.tdma_controller,'from_app')
            self.msg_connect(self.tdma_controller,'to_app', self.traffic, "in_pkt_port")

        else:
            self.traffic = None

        
        self.tdma_logger = tdma_logger(ll_logging, upsample_factor_usrp)
        
        # set up receive path
        packet_rx_callback = self.tdma_controller.incoming_packet_callback
        self.rx_path = receive_path_gmsk(demodulator, packet_rx_callback, options, 
                                               log_index=-2, use_new_pkt=True)
   

   
        self.gmsk_mod = digital_ll.gmsk_mod(
            samples_per_symbol=options.modulation_samples_per_symbol,
            bt=options.bt,
            verbose=False,
            log=False,
        )
   
        # declare time tag shifters
        is_receive = True
        self.rx_time_tag_shifter = time_tag_shifter(is_receive, gr.sizeof_gr_complex)
        self.tx_time_tag_shifter = time_tag_shifter(not is_receive, gr.sizeof_gr_complex)
   
   
        # handle base node specific setup
        if self.tdma_mac_sm.is_base():
            t0 = time.time()
            t0_int = int(t0)-10
            t0_frac = t0-t0_int
            beacon_sched = (1,1,0,(t0_int, t0_frac),(t0_int, t0_frac))
            
            self.scheduled_mux = digital_ll.scheduled_mux(gr.sizeof_gr_complex,1,
                                                          self.fs, [beacon_sched])
 
            self.connect(self.source, self.rx_time_tag_shifter, self.rx_channelizer,self.scheduled_mux,self.rx_path) 
            
        # handle mobile node specific setup    
        else:
            t0 = time.time()
            t0_int = int(t0)-10
            t0_frac = t0-t0_int
            beacon_sched = (2.0,2.0,0,(t0_int, t0_frac),(t0_int, t0_frac))

            self.scheduled_mux = digital_ll.scheduled_mux(gr.sizeof_gr_complex,2,self.fs)
            self.rx_channelizer.switch_channels(options.gpsbug_cal_channel)
            # Set up receive path for beacon
            
            # set up beacon consumer
            self.beacon_consumer = beacon_consumer(options, overwrite_metadata=True)
            
            beacon_rx_callback = self.beacon_consumer.beacon_callback
            self.beacon_rx_path = receive_path_gmsk(demodulator, beacon_rx_callback, options,log_index=-1,use_new_pkt=True)
         
            self.connect(self.source, self.rx_time_tag_shifter,self.rx_channelizer,self.scheduled_mux,self.beacon_consumer)
            self.connect(self.scheduled_mux,self.beacon_rx_path)
            self.connect((self.scheduled_mux,1),self.rx_path)

            
            self.msg_connect(self.beacon_consumer, "sched_out", self.tdma_controller, "sched_in")
                    
                    
            # add in time tag shifter block message connections
            self.msg_connect(self.beacon_consumer, 'time_cal_out', self.rx_time_tag_shifter, 'time_tag_shift')
            self.msg_connect(self.beacon_consumer, 'time_cal_out', self.tx_time_tag_shifter, 'time_tag_shift')
            self.msg_connect(self.beacon_consumer, 'time_cal_out', self.tdma_mac_sm.cq_manager, 'time_tag_shift')
            

        self.connect(self.rx_channelizer,self.tdma_controller)
        self.connect(self.packet_framer, self.gmsk_mod, self.digital_scaling,
                     self.tx_channelizer, self.tx_time_tag_shifter, self.eob, self.sink)
            
            

            
        #self.connect(self.gmsk_mod, self.tdma_logger)
        self.connect(self.eob, self.tdma_logger)


        self.msg_connect(self.tdma_controller, "command_out", self.pmt_rpc, "in")
        self.msg_connect(self.tdma_controller, "outgoing_pkt", self.packet_framer, "in")   
        
        # store off params for logging 
        self.get_usrp_params(options)
             
    def async_callback(self, msg):
        md = self.async_src.msg_to_async_metadata_t(msg)
        if md.event_code != 1:
            self.dev_log.warn("Channel: %i Time: %f Event: %s", md.channel, 
                                 md.time_spec.get_real_secs(), 
                                 uhd_error_codes[md.event_code])
 
    def do_time_calibration(self):
        
        current_time = time.time()
        
        if self.tdma_mac_sm.is_base():

            # send time cal beacons
            self.tdma_controller.send_time_calibration_beacons(self.cal_time)
            while(time.time() - current_time < self.cal_time):
                time.sleep(.1)
        else:
            # do mobile time cal stuff
            self.dev_log.info("starting time calibration on channel %i over %f seconds",
                                 self.rx_channelizer.current_chan, self.cal_time)    

            while( time.time() - current_time < self.cal_time ):
                time.sleep(.1)
            
            if not self.beacon_consumer.time_cal_is_successful():
                self.dev_log.error("Time calibration failed")
            
            self.beacon_consumer.set_time_calibration_complete()
            self.beacon_consumer.reset()    
           
        
        self.dev_log.info("time calibration complete")    
            
        self.tdma_mac_sm.start()
        # tell the controller that time cal is done    
        self.tdma_controller.set_time_calibration_complete()
        
        
    def get_usrp_params(self,options):
    
        #uhd_find_devices is a binary that is in installed in the path,
        #reports the details about the usrp connected including 
        #serial number and ip address
        
        #(status, usrp_str)= commands.getstatusoutput("uhd_find_devices --args=" + options.usrp_args )
        usrp_str = commands.getstatusoutput("uhd_find_devices --args=" + options.usrp_args )[1]
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
        
# //////////////////////////////////////////////////////////////////////////////
#                           initial configuration
# //////////////////////////////////////////////////////////////////////////////

def initial_config():

    traffic_models = ["infinite", "none", "tunnel"]
    

    # Dictionary of default variables
    node_defaults = dict()

    # Get the arg parser and add config file as an option
    arg_parser = ArgumentParser(add_help=False)
    arg_parser.add_argument("-c", "--config-file", help="set config-file name")
    
    #(known, args)=arg_parser.parse_known_args()
    known=arg_parser.parse_known_args()[0]
    
    # Setup dev logger
    # import log config template from lincolnlogs
    log_config = deepcopy(digital_ll.log_config)
    # set the log level
#    log_config["loggers"]["developer"]["level"] = known.log_level

    logging.config.dictConfig(log_config)
    dev_log = logging.getLogger('developer')

    f = digital_ll.ContextFilter()
    dev_log.addFilter(f)
    
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

    # Create Options Parser:
    parser = OptionParser (option_class=eng_option, conflict_handler="resolve")
    expert_grp = parser.add_option_group("Expert")

    parser.add_option("--show-gpl", action="store_true", default=False,
                      help="display the full GPL license for this program")

    # note this option is actually handled by the argparse module. This is only included 
    # so the config file option shows up in the help file
    parser.add_option("-c", "--config-file", help="set config-file name")    
    parser.add_option("--log-level", default="INFO", 
                      help="verbosity of debug log. options are %s" % log_levels)
    parser.add_option("-m", "--modulation", type="choice", choices=demods.keys(), 
                      default='gmsk',
                      help="Select modulation from: %s [default=%%default]"
                            % (', '.join(demods.keys()),))
    parser.add_option("","--pcktlog", default="./tdma_packetlog.xml", help="file to save packet log to")
    parser.add_option("","--statelog",default="./tdma_statelog.xml",help="file to save state log to")
    
    
    #related to power control settings
    
                      
                     
    parser.add_option("","--rf-power-control-enabled", type="int", default=0,
                      help=("Set to 1 to enable base power control.  Irrelavant otherwise. " +
                            "[default=%default]"))
    parser.add_option("","--rf-power-control-max-tx-gain", type="float", default=31.5,
                      help=("Set max transmit gain up to 31.5 at 0.5 increment when base power control is enabled." +
                            "[default=%default]"))
    parser.add_option("","--rf-power-control-min-tx-gain", type="float", default=0.0,
                      help=("Set min transmit gain down to 0.0 at 0.5 increment when base power control is enabled." +
                            "[default=%default]"))
    parser.add_option("","--rf-power-control-thresholds", type="string", default="0, 0.03, 0.08, 0.50",
                      help=("Set power control BER thresholds where gain change decision is made, " +
                            "applicable when base power control is enabled." +
                            "[default=%default]"))
    parser.add_option("","--rf-power-control-stepsizes", type="string", default="-2,    0,    3,    9",
                      help=("Set power control gain change sizes for corresponding thesholds, " +
                            "applicable when base power control is enabled." +
                            "[default=%default]"))
    parser.add_option("","--rf-power-control-sense-window", type="int", default=5,
                      help=("Number of frames used in computing link quality for power control purpose." +
                            "[default=%default]"))

   
    parser.add_option("--start-time", type="float", default=float(0), 
                      help=("Start time of the test, in seconds since 1970. " + 
                             "Starts immediately if start time is in the past. " +
                             "[default=%default]  " + 
                             "Hint: Use date +%s to get the current epoch time."))
    parser.add_option("--run-duration", type="float", default=float(0), 
                      help=("Run time duration of the test in seconds. " + 
                             "Run forever until control-C if run time is 0. " +
                             "[default=%default]"))
    parser.add_option("", "--node-role", type="choice", choices=["tdma_base", "tdma_mobile"], 
                      default='tdma_mobile',
                      help="Select mac from: %s [default=%%default]"
                            % (', '.join(["tdma_base", "tdma_mobile"])))
    
    parser.add_option("", "--gpsbug-cal-duration", type="float", default=10.0, 
                      help="Duration to run time calibration")
        
    # TODO: clean up this option. Store available traffic generation schemes somehow
    parser.add_option("--traffic-generation", type="choice", choices=traffic_models,
                      default="none",
                      help="Select traffic generation method: %s [default=%%default]" % (", ".join(traffic_models)))

    receive_path_gmsk.add_options(parser, expert_grp)


#    normally this would be in transmit path add option
    parser.add_option("", "--tx-access-code", type="string",
                      default="1", 
                      help="set transmitter access code 64 1s and 0s [default=%default]")
    
    parser.add_option("", "--digital-scale-factor", type="float", default=0.5, 
                      help="digital amplitude control for transmit, between 0.0 and 1.0")    

    uhd_receiver.add_options(parser)
    uhd_transmitter.add_options(parser)
    
    for mod in mods.values():
        mod.add_options(expert_grp)

    for mod in demods.values():
        mod.add_options(expert_grp)


    channelizer.rx_channelizer.add_options(parser)
    channelizer.tx_channelizer.add_options(parser)
    
    base_slot_manager_ber_feedback.add_options(parser,expert_grp)
    mobile_slot_manager_ber_feedback.add_options(parser,expert_grp)

    tdma_base_sm.add_options(parser,expert_grp)
    tdma_mobile_sm.add_options(parser,expert_grp)
    tdma_controller.add_options(parser,expert_grp)
    Infinite_Backlog_PDU_Streamer.add_options(parser,expert_grp)
    Tunnel_Handler_PDU_Streamer.add_options(parser,expert_grp)
    beacon_consumer.add_options(parser,expert_grp)
    
    # get list of all option defaults in the current option list
    opt_list = parser.defaults
    
    # update defaults for node-options modules
    # iterate through each entry in node_defaults
    for key in node_defaults:
        #dev_log.debug('Searching opt_list for option: %s', key)
        # if there's a match to an entry in opt_list
        if key in opt_list:
            # update default options from the value in gr_defaults
            #dev_log.debug('Updating option default: %s from node_defaults', key)
            parser.set_default(key, node_defaults[key])
        else:
#            print "Ini file option ", key, "doesn't have a field in parser"
#            assert False
            dev_log.warning('Option %s from ini file not present in parser',key)

    for key in opt_list:
        if key not in node_defaults:
            dev_log.warning('Option %s from parser not in ini file',key)
        
    
#    for key in opt_list:
#        dev_log.info("option key: %s", key)

    
    (options, args) = parser.parse_args ()
    
    # update log level
    dev_log.info("new log level is %s", options.log_level)
    log_config["loggers"]["developer"]["level"] = options.log_level
    logging.config.dictConfig(log_config)
    dev_log = logging.getLogger('developer')
    
    dev_log.debug("hi")
        
    #if options.pcktlog != -1:
    #    lincolnlog.LincolnLogLayout('debug', -1, options.pcktlog , -1, -1)
    #else:
    #    lincolnlog.LincolnLogLayout('debug', -1, -1, -1, -1)
    lincolnlog.LincolnLogLayout('debug', -1, options.pcktlog , options.statelog, -1)      

    ll_logging     = lincolnlog.LincolnLog(__name__)

    if len(args) != 0:
        parser.print_help(sys.stderr)
        sys.exit(1)
            
    # parse rest of command line args
    if len(args) != 0:
        parser.print_help(sys.stderr)
        sys.exit(1)
            
        # cannot proceed without a config file, so exit
    if known.config_file is None:
        print "No config file provided, exiting"
        sys.exit(1)
        
    

    return(mods, demods, options, ll_logging, dev_log)



# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////


def main():
    
#    import os
#    print os.getpid()
#    raw_input('Attach and press enter: ')

    #traffic_models = ["infinite", "none"]
    
                   
    try:
        (mods, demods, options, ll_logging, dev_log) = initial_config()
        
        if options.show_gpl:
            show_full_gpl()
            return
        else:
            show_short_gpl()        
        #variables = vars( options )
        #for key in variables:
        #    print key, ' = ', variables[key]    
        #assert False, 'Exiting for debugging'
                
        # wait for start time
        current_time = time.time()
        if options.start_time-current_time > 0.0:
            dev_log.info("Waiting %s seconds for start time of %s", options.start_time-current_time, 
                        options.start_time)
            start_time = options.start_time
        else:
            dev_log.info("Current time is past start time. Starting immediately")
            start_time = ceil(current_time)

        print "current time is", current_time
        print "start time is", start_time
        
        while current_time < options.start_time:
            time.sleep(.1)
            current_time = time.time()
        

        expected_setup_time = 7
        #expected_cs_time = 30
        #expected_cal_time = 10
        #num_cal_beacons = 5

      
        
        start_tb_time = start_time + expected_setup_time
            

        # schedule start_controller_time
        
        
            
        start_controller_time = start_tb_time + options.gpsbug_cal_duration
        print "start controller time is", start_controller_time    
        
        
        # build the graph
        tb = my_top_block(mods["gmsk"],demods["gmsk"], options, 
                          ll_logging, dev_log, start_tb_time, options.gpsbug_cal_duration, start_controller_time)
        
        # Log to state.xml
        log_my_settings(options, tb, ll_logging._statelog)
        
        print "sample rate is: %f" % tb.fs
        print "samples per symbol %f" % options.modulation_samples_per_symbol
        
        print "started flow graph at time ", time.time()        
        tb.start()        # start flow graph        
        tb.do_time_calibration()        
        dev_log.info("after calibration time is %s", time.time())        
        dev_log.info("scheduled start controller time (after cal) is %s", tb.start_controller_time)
        
        if not numpy.isinf(options.run_duration) and options.run_duration > 0.0 :
            dev_log.info("test will run for run-time of %s seconds", options.run_duration)
            
            while( time.time() - tb.start_controller_time < options.run_duration ):
                
                
                
                
                time.sleep(.1)
            dev_log.info("run time exceeded.")    
            shut_down(tb, dev_log )
        else:
            dev_log.info("test will run forever until control-C")
            
            while True:
                
                time.sleep(.5)
            
            tb.wait()
            
    
    except KeyboardInterrupt:
        shut_down(tb, dev_log )
        pass

def show_short_gpl():
    print """
    ExtRaSy Copyright (C) 2013-2014  Massachusetts Institute of Technology

    This program comes with ABSOLUTELY NO WARRANTY; for details run this program
    with '--show-gpl'
    This is free software, and you are welcome to redistribute it under certain
    conditions; run this program with '--show-gpl' for details.
    """

def show_full_gpl():
    print """
    ExtRaSy
    
    Copyright (C) 2013-2014 Massachusetts Institute of Technology
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    """


def log_my_settings( options, tb, logger ):
    print 'logging'

    # get current timestamp
    epoch_time = time.time()
    indent_level = 0
    
    section_indent = (indent_level)
    
    # node state section start
    logger.info("%s<node_state>", section_indent*'\t')
    section_indent += 1
     
    # get current repo branch and version
    #(status, branch) = commands.getstatusoutput("git rev-parse --symbolic-full-name --abbrev-ref HEAD")
    #(status, commit) = commands.getstatusoutput("git describe --always --dirty")
    branch = commands.getstatusoutput("git rev-parse --symbolic-full-name --abbrev-ref HEAD")[1]
    commit = commands.getstatusoutput("git describe --always --dirty")[1]
    node_version = branch + '-' + commit
    
    # get machine name    
    #(status, hostname) =  commands.getstatusoutput("uname -n")
    hostname = commands.getstatusoutput("uname -n")[1]
    # node state section param values
    params = {"timestamp":epoch_time,
              "traffic_generation_type":options.traffic_generation,
              "node_version":node_version,
              "mac_ll_version":mac_ll.__version__,
              "digital_ll_version":digital_ll.__version__,
              "hostname":hostname,
              "pckt_log":options.pcktlog,
              "statelog":options.statelog,
              "node_config":options.config_file,
              "frame_file":options.frame_file,
              "mac_type":options.node_role,
              "power_control_enabled":options.rf_power_control_enabled,
              "calibration_time":tb.cal_time,
              }

    logger.info(dict_to_xml(params, section_indent))

    if tb.traffic is not None:

        # traffic_generatione section start
        logger.info("%s<traffic_generation>", section_indent*'\t')
        section_indent += 1
         
        tb.traffic.log_my_settings(section_indent, logger)
            
        # traffic_generation section end
        section_indent -= 1
        logger.info("%s</traffic_generation>", section_indent*'\t')
    
    
    # radio section start
    logger.info("%s<radio>", section_indent*'\t')
    section_indent += 1           
    
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
    
    # receive section start
    logger.info("%s<receive>", section_indent*'\t')
    section_indent += 1 
    
    # call receive path's logger
    tb.rx_path.log_my_settings(section_indent,logger)
   
    # receive section end
    section_indent -= 1
    logger.info("%s</receive>", section_indent*'\t')
    
    

    # digital hopper section start
    logger.info("%s<digital_hopper>", section_indent*'\t')
    section_indent += 1 
    
    tb.rx_channelizer.log_results(section_indent,logger)
    tb.tx_channelizer.log_results(section_indent,logger)
    
    # digital hopper section section end
    section_indent -= 1
    logger.info("%s</digital_hopper>", section_indent*'\t')
    
    
    
    # phy section end
    section_indent -= 1
    logger.info("%s</phy>", section_indent*'\t')
    
    # mac section start
    logger.info("%s<mac>", section_indent*'\t')
    section_indent += 1 
    
    tb.tdma_controller.log_my_settings(section_indent, logger)
    
    
    # mac section end
    section_indent -= 1
    logger.info("%s</mac>", section_indent*'\t')  

    

    # node state section end
    section_indent -= 1
    logger.info("%s</node_state>", section_indent*'\t')
    
    # catchall for options
    ops = vars(options)
    
    logger.info('%s<options>',section_indent*'\t')
    section_indent += 1 
    logger.info(dict_to_xml( ops, section_indent ))
    section_indent -= 1
    logger.info('%s</options>',section_indent*'\t')
    
def shut_down(tb, dev_log ):
    print "shut down process begins at ", time.time()

    dev_log.debug("telling top block to stop")
    tb.stop()
    
    dev_log.debug("waiting for top block thread to complete")
    tb.wait()
    dev_log.debug("top block has shut down")
    
    if tb.traffic is not None:
        dev_log.debug("shutting down traffic generator")
        tb.traffic.shut_down()
        dev_log.debug("traffic shutdown complete")
    
    print "shut down process finishes at ", time.time()        
        
if __name__ == '__main__':
    main()


