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

# standard python library imports
import copy
import math
import os
import random 
import struct
import sys
import time

# third party library imports
from gnuradio import gr, gru
from gnuradio import eng_notation
from gnuradio import digital
from grc_gnuradio import blks2 as grc_blks2

# project specific imports
from digital_ll import lincolnlog
from digital_ll import tag_logger





import digital_ll

from digital_ll.lincolnlog import dict_to_xml

# /////////////////////////////////////////////////////////////////////////////
#                              receive path
# /////////////////////////////////////////////////////////////////////////////

class receive_path_gmsk(gr.hier_block2):
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

        self._use_coding = False
        
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
        self.packet_receiver = \
            digital_ll.pkt2.demod_pkts(self.demodulator, options, #added on 9/28/12
                               access_code=self._access_code,
                               callback=self._rx_callback,
                               threshold=self._threshold,
                               use_coding=self._use_coding,
                               logging=self._logging)

    
        # Display some information about the setup
        if self._verbose:
            self._print_verbage()
    
        # connect block input to channel filter
        self.connect(self, self.channel_filter)
    
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


    
    @staticmethod    
    def add_options(normal, expert):
        """
        Adds receiver-specific options to the Options Parser
        """
        
     
        normal.add_option("","--access-code-threshold",type="int",default=-1,help="access code threshold")

        
        if not normal.has_option("--modulation-bitrate"):
            normal.add_option("-r", "--modulation-bitrate", type="eng_float", default=100e3,
                              help="specify bitrate [default=%default].")
            
        normal.add_option("-v", "--verbose", action="store_true", default=False)
        normal.add_option("", "--rx-access-code", type="string",
                          default="1", 
                          help="set receiver access code 64 1s and 0s [default=%default]")
        expert.add_option("-S", "--modulation-samples-per-symbol", type="float", default=2,
                          help="set samples/symbol [default=%default]")
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
                  "access_code":self._access_code,
                  "coding":self._use_coding,
                  "constellation_points":self._constellation_points,
                  "excess_bw":self._excess_bw,
                  "chbw_factor":self._chbw_factor,
                  "freq_bw":self._freq_bw,
                  "phase_bw":self._phase_bw,
                  "timing_bw":self._timing_bw,
                  }
        
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
       
