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

from gnuradio import gr
from gnuradio import eng_notation
from gnuradio import digital
import digital_ll
from digital_ll import lincolnlog
from digital_ll.lincolnlog import dict_to_xml

import copy
import sys

# /////////////////////////////////////////////////////////////////////////////
#                              transmit path
# /////////////////////////////////////////////////////////////////////////////

class transmit_path_narrowband(gr.hier_block2):
    def __init__(self, modulator_class, options):
        '''
        See below for what options should hold
        '''
        gr.hier_block2.__init__(self, "transmit_path",
				gr.io_signature(1,1,gr.sizeof_char),
				gr.io_signature(1,1,gr.sizeof_gr_complex))
        
        options = copy.copy(options)    # make a copy so we can destructively modify

        self._verbose      = options.verbose
        self._tx_amplitude = options.tx_amplitude   # digital amplitude sent to USRP
        self._bitrate      = options.bitrate        # desired bit rate
        self._modulator_class = modulator_class     # the modulator_class we are using
        self._access_code   = options.tx_access_code



        self._use_coding = options.coding
        self._rfcenterfreq = options.tx_freq
        self._bandwidth = options.my_bandwidth
        self._logging    = lincolnlog.LincolnLog(__name__)
        #if options.pcktlog != -1:
        #    self._logging    = lincolnlog.LincolnLog(__name__)
        #else:
        #    self._logging = -1
        
        if  self._access_code == 0:
            self._access_code = None
        elif self._access_code == 1:
            self._access_code = '0000010000110001010011110100011100100101101110110011010101111110'
            print 'tx access code: %s' % self._access_code
        elif self._access_code == 2:
            self._access_code = '1110001100101100010110110001110101100000110001011101000100001110'

        # Get mod_kwargs
        mod_kwargs = self._modulator_class.extract_kwargs_from_options(options)
        
        # transmitter
        self.modulator = self._modulator_class(**mod_kwargs)
        
        self.packet_tx = \
            digital_ll.mod_pkts(self.modulator,
                             options, #added on 9/28/12
                             access_code=self._access_code,
                             msgq_limit=4,
                             pad_for_usrp=True,
                             use_whitener_offset=False,
                             modulate=True,
                             use_coding=self._use_coding,
                             rfcenterfreq=self._rfcenterfreq, bandwidth=self._bandwidth,
                             logging=self._logging 
                             )

        self.amp = gr.multiply_const_cc(1)
        self.set_tx_amplitude(self._tx_amplitude)
        self.null_sink = gr.null_sink(gr.sizeof_char)
        
        # Display some information about the setup
        if self._verbose:
            self._print_verbage()

        # Connect components in the flowgraph
        self.connect(self.packet_tx, self.amp, self)
        self.connect(self,self.null_sink)
        
        # added to make logging easier
        self._modulation = options.modulation
        
        if "_constellation" in vars(self.modulator):
            self._constellation_points = len(self.modulator._constellation.points())
        else:
            self._constellation_points = None
            
        if "_excess_bw" in vars(self.modulator):
            self._excess_bw = self.modulator._excess_bw
        else:
            self._excess_bw = None
                  
    
    def num_complex_samples(self, num_bytes):
        return int(self.packet_tx.num_complex_samples(num_bytes))
        
    def set_tx_amplitude(self, ampl):
        """
        Sets the transmit amplitude sent to the USRP in volts
        @param: ampl 0 <= ampl < 1.
        """
        self._tx_amplitude = max(0.0, min(ampl, 1))
        self.amp.set_k(self._tx_amplitude)
        
    def send_pkt(self, payload='', eof=False):
        """
        Calls the transmitter method to send a packet
        """
        print "calling send_pkt for packet of size %d bytes" % len(payload)
        return self.packet_tx.send_pkt(payload, eof)
        
    def bitrate(self):
        return self._bitrate

    def samples_per_symbol(self):
        return self.modulator._samples_per_symbol

    def differential(self):
        return self.modulator._differential
    
    def use_streaming_inputs(self, stream_enable=True):
        # prepare to reconfigure
#        self.lock()

        # wire hier block input to packet transmitter 
        if stream_enable == True:
            
            self.disconnect(self,self.null_sink)
            self.connect(self, self.packet_tx)
        
        # disconnect hier block input from packet transmitter
        else:
            self.disconnect(self, self.packet_tx)
            self.connect(self,self.null_sink)
#        self.unlock()
        
        return self.packet_tx.use_streaming_inputs(stream_enable)

    def max_pkt_size(self):
        return self.packet_tx.max_pkt_size()
    
    def add_options(normal, expert):
        """
        Adds transmitter-specific options to the Options Parser
        """
        if not normal.has_option('--bitrate'):
            normal.add_option("-r", "--bitrate", type="eng_float",
                default=100e3,
                help="specify bitrate [default=%default].")
        normal.add_option("", "--tx-amplitude", type="eng_float",
            default=0.25, metavar="AMPL",
            help="set transmitter digital amplitude: 0 <= AMPL < 1 [default=%default]")

        normal.add_option("", "--tx-access-code", type="float",
            default=1, 
            help="set transmitter access code 64 1s and 0s [default=%default]")

        if not normal.has_option('--coding'):
            normal.add_option("","--coding",type="int", default=0,
                              help="enable FEC coding of the data")

        normal.add_option("-v", "--verbose", action="store_true",
                          default=False)

        expert.add_option("-S", "--samples-per-symbol", type="float",
                          default=2,
                          help="set samples/symbol [default=%default]")
        expert.add_option("", "--log", action="store_true",
                          default=False,
                          help="Log all parts of flow graph to file (CAUTION: lots of data)")
        normal.add_option("", "--block-length", type="int", default=8, help="Reed-Solomon code block length [default=%default]")
        normal.add_option("", "--adaptive-coding", type="int", default=False, help="Enable adaptive FEC coding.")
        normal.add_option("", "--adaptive-coding-block-lengths", type="string", default = "6,8,10,12", help="The block lengths adaptive coding will vary over. Should be comma separated list.")
        normal.add_option("", "--adaptive-coding-memory-length", type="int", default=10, help="The number of previous atomic events (data Tx attempts) used to make rate adaptation decisions")
        normal.add_option("", "--adaptive-coding-upper-thresh", type = "eng_float", default=0.9, help="The fraction of successful packets needed to trigger a move to lower rate coding")
        normal.add_option("", "--adaptive-coding-lower_thresh", type = "eng_float", default=0.8, help="The fraction of successful packets needed to trigger a move to a higher rate coding")
        expert.add_option("", "--log", action="store_true",
                          default=False,
                          help="Log all parts of flow graph to file (CAUTION: lots of data)")
        
        normal.add_option("", "--percent-bw-occupied", type="float", default=0.0,
                          help="value used for packet logs in percent_bw_occupied field [default=%default]")     

    # Make a static method to call before instantiation
    add_options = staticmethod(add_options)

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
        params = {"tx_amplitude":self._tx_amplitude,
                  "modulation":self._modulation,
                  "bitrate":self._bitrate,
                  "samples_per_symbol":self.samples_per_symbol(),
                  "differential":self.differential(),
                  "access_code":self._access_code,
                  "coding":self._use_coding,
                  "constellation_points":self._constellation_points,
                  "excess_bw":self._excess_bw}
        
        # add optional params if they exist 
        
        # check for mod code (currently in psk and qam only)
        if "_mod_code" in vars(self.modulator):
            params["mod_code"] =  self.modulator._mod_code
        
        # check for bt (currently in gmsk and cpm only)
        if "_bt" in vars(self.modulator):
            params["bt"] =  self.modulator._bt
                    
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
        Prints information about the transmit path
        """
        print "Tx amplitude     %s"    % (self._tx_amplitude)
        print "modulation:      %s"    % (self._modulator_class.__name__)
        print "bitrate:         %sb/s" % (eng_notation.num_to_str(self._bitrate))
        print "samples/symbol:  %.4f"  % (self.samples_per_symbol())
        print "Differential:    %s"    % (self.differential())
