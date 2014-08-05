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
# Copyright 2005,2006,2011 Free Software Foundation, Inc.
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

import copy
import sys
from digital_ll import lincolnlog
from digital_ll.lincolnlog import dict_to_xml
from digital_ll import ofdm_mod

# /////////////////////////////////////////////////////////////////////////////
#                              transmit path
# /////////////////////////////////////////////////////////////////////////////

class transmit_path_ofdm(gr.hier_block2): 
    def __init__(self, options):
        '''
        See below for what options should hold
        '''

        gr.hier_block2.__init__(self, "transmit_path",
				gr.io_signature(1,1,gr.sizeof_char),
				gr.io_signature(1, 1, gr.sizeof_gr_complex))

        options = copy.copy(options)    # make a copy so we can destructively modify

        self._verbose      = options.verbose      # turn verbose mode on/off
        self._tx_amplitude = options.tx_amplitude # digital amp sent to radio

        self.packet_tx = ofdm_mod(options,
                                        msgq_limit=4,
                                        pad_for_usrp=False)

        self.amp = gr.multiply_const_cc(1)
        self.set_tx_amplitude(self._tx_amplitude)
        self.null_sink = gr.null_sink(gr.sizeof_char)
        self.coding_block_length = options.block_length

        # Display some information about the setup
        if self._verbose:
            self._print_verbage()

        # Create and setup transmit path flow graph
        self.connect(self.packet_tx, self.amp, self)
        # connect hier block input to null when not using streaming inputs
        self.connect(self,self.null_sink)
        
    def num_complex_samples(self, num_bytes):
        return int(self.packet_tx.num_complex_samples(num_bytes) )   
        
    def set_tx_amplitude(self, ampl):
        """
        Sets the transmit amplitude sent to the USRP
        @param: ampl 0 <= ampl < 1.0.  Try 0.10
        """
        self._tx_amplitude = max(0.0, min(ampl, 1))
        self.amp.set_k(self._tx_amplitude)
        
    def send_pkt(self, payload='', eof=False):
        """
        Calls the transmitter method to send a packet
        """
        return self.packet_tx.send_pkt(payload, eof)
    
    def use_streaming_inputs(self, stream_enable=True):
        """
        Enables or disables streaming input for debug
        """
        # wire hier block input to packet transmitter 
        if stream_enable == True:
            
            self.disconnect(self,self.null_sink)
            self.connect(self, self.packet_tx)
        
        # disconnect hier block input from packet transmitter
        else:
            self.disconnect(self, self.packet_tx)
            self.connect(self,self.null_sink) 
            
        self.packet_tx.use_streaming_inputs(stream_enable)  
        
    def max_pkt_size(self):
        return self.packet_tx.max_pkt_size()
        
    def add_options(normal, expert):
        """
        Adds transmitter-specific options to the Options Parser
        """
        normal.add_option("","--coding",type="int", default=False,
                          help="enable FEC coding of the data")
        
        normal.add_option("", "--tx-amplitude", type="eng_float",
                          default=0.1, metavar="AMPL",
                          help="set transmitter digital amplitude: 0 <= AMPL < 1.0 [default=%default]")
        normal.add_option("-W", "--bandwidth", type="eng_float",
                          default=500e3,
                          help="set symbol bandwidth [default=%default]")
        normal.add_option("-v", "--verbose", action="store_true",
                          default=False)
        normal.add_option("", "--block-length", type="int", default=8, help="Reed-Solomon code block length [default=%default]")
        normal.add_option("", "--adaptive-coding", type="int", default=False, help="Enable adaptive FEC coding.")
        normal.add_option("", "--adaptive-coding-block-lengths", type="string", default = "6,8,10,12", help="The block lengths adaptive coding will vary over. Should be comma separated list.")
        normal.add_option("", "--adaptive-coding-memory-length", type="int", default=10, help="The number of previous atomic events (data Tx attempts) used to make rate adaptation decisions")
        normal.add_option("", "--adaptive-coding-upper-thresh", type = "eng_float", default=0.9, help="The fraction of successful packets needed to trigger a move to lower rate coding")
        normal.add_option("", "--adaptive-coding-lower-thresh", type = "eng_float", default=0.8, help="The fraction of successful packets needed to trigger a move to a higher rate coding")
        expert.add_option("", "--log", action="store_true",
                          default=False,
                          help="Log all parts of flow graph to file (CAUTION: lots of data)")
             
        # add ofdm_mod options
        ofdm_mod.add_options(normal, expert)
    # Make a static method to call before instantiation
    add_options = staticmethod(add_options)

    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''
                
        section_indent = indent_level
        
        # top level transmit section param values
        params = {"multiplexing":"ofdm"}
        logger.info(dict_to_xml(params, section_indent))
    
        # ofdm section start
        logger.info("%s<ofdm>", section_indent*'\t')
        section_indent += 1
        
        # ofdm section param values
        params = {"tx_amplitude":self._tx_amplitude,
                  "modulation":self.packet_tx._modulation,
                  "coding":self.packet_tx._use_coding,
                  "number_of_subcarriers":self.packet_tx._fft_length,
                  "number_of_active_subcarriers":self.packet_tx._occupied_tones,
                  "cp_length":self.packet_tx._cp_length}
        logger.info(dict_to_xml(params, section_indent))
        
            
        if self.packet_tx._use_coding == True:
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
               
        # ofdm section end
        section_indent -= 1
        logger.info("%s</ofdm>", section_indent*'\t')


    def _print_verbage(self):
        """
        Prints information about the transmit path
        """
        print "Tx amplitude     %s" % (self._tx_amplitude)
        
