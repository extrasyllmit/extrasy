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
#
# 
# This file incorporates work covered by the following copyright:
#
#
# Copyright 2005-2007,2011 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr, gru
from gnuradio import eng_notation
from gnuradio import digital
from grc_gnuradio import blks2 as grc_blks2
from digital_ll import lincolnlog
from digital_ll import tag_logger
import time

import copy
import os, sys
import random, time, struct
import math
import digital_ll

from digital_ll.lincolnlog import dict_to_xml

# /////////////////////////////////////////////////////////////////////////////
#                              receive path
# /////////////////////////////////////////////////////////////////////////////

class receive_path_narrowband(gr.hier_block2):
    def __init__(self, demod_class, rx_callback, options, log_index=-1, use_new_pkt=False):
        gr.hier_block2.__init__(self, "receive_path",
    			gr.io_signature(1, 1, gr.sizeof_gr_complex),
    			gr.io_signature(0, 0, 0))
        
        options = copy.copy(options)    # make a copy so we can destructively modify
    
        self._verbose     = options.verbose
        self._bitrate     = options.modulation_bitrate  # desired bit rate
    
        self._rx_callback = rx_callback  # this callback is fired when a packet arrives
        self._demod_class = demod_class  # the demodulator_class we're using
    
        self._chbw_factor = options.chbw_factor # channel filter bandwidth factor
    
        self._access_code   = options.rx_access_code
        self._threshold     = options.access_code_threshold
        
        self._accesstype    = options.channelaccess
        
        self._pcsthresh  = options.pcsthresh
        self._pcsalpha   = options.pcsalpha
        self._n_iter      = options.pcstrain_niter
        self._iter_len    = options.pcstrain_iterlen
        self._pcstrain_flag = options.pcstrain_flag
        self._pcs_waitafter = options.pcs_waitafter
        
        
        if  self._access_code == '0':
            self._access_code = None
        elif self._access_code == '1':
            self._access_code = '0000010000110001010011110100011100100101101110110011010101111110'
            print 'rx access code: %s' % self._access_code
        elif self._access_code == '2':
            self._access_code = '1110001100101100010110110001110101100000110001011101000100001110'
    
        # Get demod_kwargs
        demod_kwargs = self._demod_class.extract_kwargs_from_options(options)
    
        # Build the demodulator
        self.demodulator = self._demod_class(**demod_kwargs)
        print self.demodulator

        self._use_coding = options.coding
        
        self._rfcenterfreq = options.rf_rx_freq
        
        # make sure option exists before adding member variable
        if hasattr(options, 'my_bandwidth'):
            self._bandwidth  = options.my_bandwidth
            
        self._logging    = lincolnlog.LincolnLog(__name__)
        #if options.pcktlog != -1:
        #    self._logging    = lincolnlog.LincolnLog(__name__)
        #else:
        #    self._logging = -1
    
        # Make sure the channel BW factor is between 1 and sps/2
        # or the filter won't work.
        if(self._chbw_factor < 1.0 or self._chbw_factor > self.samples_per_symbol()/2):
            sys.stderr.write("Channel bandwidth factor ({0}) must be within the range [1.0, {1}].\n".format(self._chbw_factor, self.samples_per_symbol()/2))
            sys.exit(1)
        
        # Design filter to get actual channel we want
        sw_decim = 1
        chan_coeffs = gr.firdes.low_pass (1.0,                  # gain
                                          sw_decim * self.samples_per_symbol(), # sampling rate
                                          self._chbw_factor,    # midpoint of trans. band
                                          0.5,                  # width of trans. band
                                          gr.firdes.WIN_HANN)   # filter type
        self.channel_filter = gr.fft_filter_ccc(sw_decim, chan_coeffs)
        
        # receiver
        if use_new_pkt:
            self.packet_receiver = \
                digital_ll.pkt2.demod_pkts(self.demodulator, options, #added on 9/28/12
                                   access_code=self._access_code,
                                   callback=self._rx_callback,
                                   threshold=self._threshold,
                                   use_coding=self._use_coding,
                                   logging=self._logging)
        else:
            self.packet_receiver = \
                digital_ll.pkt.demod_pkts(self.demodulator, options, #added on 9/28/12
                                   access_code=self._access_code,
                                   callback=self._rx_callback,
                                   threshold=self._threshold,
                                   use_coding=self._use_coding,
                                   rfcenterfreq=self._rfcenterfreq, bandwidth=self._bandwidth,
                                   logging=self._logging)
                    
    
        # Carrier Sensing Blocks
        alpha = self._pcsalpha #default was 0.1
        thresh = self._pcsthresh   # in dB, will have to adjust
        pcstrain_flag = self._pcstrain_flag
        n_iter = self._n_iter  # number of iterations of the configuration process
        iter_len = self._iter_len # the length of each iteration of the configuration process
        self.probe = digital_ll.probe_avg_mag_sqrd_c(thresh,alpha,pcstrain_flag,n_iter,iter_len)
    
        # Display some information about the setup
        if self._verbose:
            self._print_verbage()
    
        # connect block input to channel filter
        self.connect(self, self.channel_filter)

        # connect the channel input filter to the carrier power detector
        self.connect(self.channel_filter, self.probe)
    
        # connect channel filter to the packet receiver
        self.connect(self.channel_filter, self.packet_receiver)
        
       
            
        # added to make logging easier
        self._modulation = options.modulation 
        
        if "_constellation" in vars(self.demodulator):
            self._constellation_points = len(self.demodulator._constellation.points())
        else:
            self._constellation_points = None
            
        if "_excess_bw" in vars(self.demodulator):
            self._excess_bw = self.demodulator._excess_bw
        else:
            self._excess_bw = None
        
        if "_freq_bw" in vars(self.demodulator):
            self._freq_bw = self.demodulator._freq_bw
        else:
            self._freq_bw = None
            
        if "_phase_bw" in vars(self.demodulator):
            self._phase_bw = self.demodulator._phase_bw
        else:
            self._phase_bw = None
            
        if "_timing_bw" in vars(self.demodulator):
            self._timing_bw = self.demodulator._timing_bw
        else:
            self._timing_bw = None             
            

    def bitrate(self):
        return self._bitrate

    def samples_per_symbol(self):
        return self.demodulator._samples_per_symbol

    def differential(self):
        return self.demodulator._differential

    def carrier_sensed(self):
        """
        Return True if we think carrier is present.
        """
        # Get the PCS and VCS Flags
        pcsFlag = self.probe.unmuted()
        vcsFlag = self.packet_receiver.channel_busy()

        # Based upon which type of carrier we are using set the return flag        
        if self._accesstype[0] is 'p':
            grandOldFlag = bool(pcsFlag)
        elif self._accesstype[0] is 'v':
            grandOldFlag = bool(vcsFlag)
        elif self._accesstype[0] is 'a':
            grandOldFlag = bool(pcsFlag or vcsFlag)
        elif self._accesstype[0] is 'n':
            grandOldFlag = False
        else:
            raise Exception('This is not a valid input')
            
        return grandOldFlag

    def calibrate_probe( self ):
        """
        Calibrate the PCS (energy detector/probe) to have a threshold learned
        off of the following finite time interval.
        """
        self.probe.signal_begin_calibration( )
        while not self.probe.check_finished_calibration( ):
            pass    #Do nothing. Just wait.
            
        # Bed-time
        time.sleep(self._pcs_waitafter)

    def carrier_threshold(self):
        """
        Return current setting in dB.
        """
        return self.probe.threshold()

    def set_carrier_threshold(self, threshold_in_db):
        """
        Set carrier threshold.

        @param threshold_in_db: set detection threshold
        @type threshold_in_db:  float (dB)
        """
        self.probe.set_threshold(threshold_in_db)
    
    @staticmethod    
    def add_options(normal, expert):
        """
        Adds receiver-specific options to the Options Parser
        """
        
        normal.add_option("","--coding",type="int", default=0,
                      help="enable FEC coding of the data")        
        normal.add_option("","--threshold",type="int",default=-1,help="access code threshold")
        normal.add_option("","--channelaccess",default="all",help="channel access type to be used [pcs, vcs, all, none]")
        normal.add_option("","--pcsthresh",default=40,type="eng_float",help="pcs power detection threshold in dB")
        normal.add_option("","--pcsalpha",default=0.1,type="eng_float",help="The alpha parameter used in the single pole filter for the pcs detector")
        normal.add_option("","--backoff",default=4000*8+32,type="int",help="The number of BITS to backoff when a packets access code is detected")
        normal.add_option("","--expected-pkt-size",default=1500,type="int",help="The maximum size (bytes) to expect for packets, used to set backoff when backoff is < 0")
        normal.add_option("", "--pcstrain_niter",default=5,type="int",help="Number of iterations to run pcs max detection for")
        normal.add_option("", "--pcstrain_iterlen",default=1000000,type="int",help="Number of samples to scan for the max over per iteration")
        normal.add_option("", "--pcstrain_flag", default=0, type="int",help="Use calibration process to learn pcs threshold from noise floor (true). Else use hard threshold")
        normal.add_option("", "--pcs_waitafter", default=0, type="eng_float", help="Number of seconds to sleep after pcs calibration to allow other nodes time to calibrate")

        
        if not normal.has_option("--modulation-bitrate"):
            normal.add_option("-r", "--modulation-bitrate", type="eng_float", default=100e3,
                              help="specify bitrate [default=%default].")
        if not normal.has_option('--coding'):
            normal.add_option("","--coding",type="int", default=0,
                              help="enable FEC coding of the data")
            
        normal.add_option("-v", "--verbose", action="store_true", default=False)
        normal.add_option("", "--rx-access-code", type="string",
                          default="1", 
                          help="set receiver access code 64 1s and 0s [default=%default]")
        expert.add_option("-S", "--modulation-samples-per-symbol", type="float", default=2,
                          help="set samples/symbol [default=%default]")
        expert.add_option("", "--log", action="store_true", default=False,
                          help="Log all parts of flow graph to files (CAUTION: lots of data)")
        expert.add_option("", "--chbw-factor", type="float", default=1.0,
                          help="Channel bandwidth = chbw_factor x signal bandwidth [defaut=%default]")

    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''
                
        section_indent = indent_level
        
        # top level transmit section param values
        params = {"multiplexing":"narrowband"}
        logger.info(dict_to_xml(params, section_indent))
    
        # narrowband section start
        logger.info("%s<narrowband>", section_indent*'\t')
        section_indent += 1
        
        # narrowband section param values
        params = {"modulation":self._modulation,
                  "bitrate":self._bitrate,
                  "samples_per_symbol":self.samples_per_symbol(),
                  "differential":self.differential(),
                  "access_code":self._access_code,
                  "coding":self._use_coding,
                  "constellation_points":self._constellation_points,
                  "excess_bw":self._excess_bw,
                  "chbw_factor":self._chbw_factor,
                  "freq_bw":self._freq_bw,
                  "phase_bw":self._phase_bw,
                  "timing_bw":self._timing_bw,
                  "channel_access":self._accesstype}
        
        # add optional params if they exist 
        
        # check for mod code (currently in psk and qam only)
        if "_mod_code" in vars(self.demodulator):
            params["mod_code"] = self.demodulator._mod_code
        
        # check for gain_mu (currently in gmsk only)
        if "_gain_mu" in vars(self.demodulator):
            params["gain_mu"] = self.demodulator._gain_mu
        
        # check for mu (currently in gmsk only)    
        if "_mu" in vars(self.demodulator):
            params["mu"] = self.demodulator._mu
        
        # check for omega_relative_limit (currently in gmsk only)    
        if "_omega_relative_limit" in vars(self.demodulator):
            params["omega_relative_limit"] = self.demodulator._omega_relative_limit
        
        # check for freq_error (currently in gmsk only)    
        if "_freq_error" in vars(self.demodulator):
            params["freq_error"] = self.demodulator._freq_error                                            
                          
        logger.info(dict_to_xml(params, section_indent))
        
        # channel_sensor section start
        logger.info("%s<channel_sensor>", section_indent*'\t')
        section_indent += 1
        
        # vcs section start
        logger.info("%s<vcs>", section_indent*'\t')
        section_indent += 1
        
        # vcs section param values
        params = {"threshold_bits":self.packet_receiver._threshold,
                  "backoff_bits":self.packet_receiver._backoff,
                  "expected_pkt_size":self.packet_receiver._expected_pkt_size}
        logger.info(dict_to_xml(params, section_indent))
                
        # vcs section end
        section_indent -= 1
        logger.info("%s</vcs>", section_indent*'\t')

        
        # pcs section start
        logger.info("%s<pcs>", section_indent*'\t')
        section_indent += 1
        
        # pcs section param values
        params = {"pcsthresh":self._pcsthresh,
                  "pcsalpha":self._pcsalpha,
                  "pcstrain_niter":self._n_iter,
                  "pcstrain_iterlen":self._iter_len,
                  "pcstrain_flag":self._pcstrain_flag,
                  "learned_pcs_threshold":self.probe.get_threshold(),}
        logger.info(dict_to_xml(params, section_indent))
                
        # pcs section end
        section_indent -= 1
        logger.info("%s</pcs>", section_indent*'\t')            
        
        # channel_sensor section end
        section_indent -= 1
        logger.info("%s</channel_sensor>", section_indent*'\t')
        
        
        if self._use_coding == True:
            # Forward error correction section start
            logger.info("%s<forward_error_correction>", section_indent*'\t')
            section_indent += 1
            
            # TODO: change the way coding is implemented so a coding module can be
            # checked for this information, instead of hard coding it
            # Forward error correction section param values
            params = {"scheme":"reed_solomon",
                "code_rate":(4.0/8.0)}
            logger.info(dict_to_xml(params, section_indent))
            
            # Forward error correction section end
            section_indent -= 1
            logger.info("%s</forward_error_correction>", section_indent*'\t') 
               
        # narrowband section end
        section_indent -= 1
        logger.info("%s</narrowband>", section_indent*'\t')

    def _print_verbage(self):
        """
        Prints information about the receive path
        """
        print "\nReceive Path:"
        print "modulation:      %s"    % (self._demod_class.__name__)
        print "bitrate:         %sb/s" % (eng_notation.num_to_str(self._bitrate))
        print "samples/symbol:  %.4f"    % (self.samples_per_symbol())
        print "Differential:    %s"    % (self.differential())
        
    def set_window_size(self, win_size):
        self.packet_receiver.set_window_size(win_size)
