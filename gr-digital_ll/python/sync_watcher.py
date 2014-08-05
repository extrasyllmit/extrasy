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
###################################################
# Gnuradio Python Flow Graph
# Title: Sync Watcher
# Author: Craig Pomeroy
# Description: Meant to watch the output of digital_correlate_access_code_bb and provide status on 
# when packets are found 
# Generated: Wed Aug 29 16:58:53 2012
##################################################

from gnuradio import gr
from gnuradio.gr import firdes
import digital_ll

class sync_watcher(gr.hier_block2):
    """sync watcher monitors the flag bit output from digital_correlate_access_code_bb and extends
       any peaks for self.pkt_size bits """
    def __init__(self, pkt_size=32032):
        gr.hier_block2.__init__(
            self, "Sync Watcher",
            gr.io_signature(1, 1, gr.sizeof_char * 1),
            gr.io_signature(0, 0, 0),
        )

        ##################################################
        # Variables
        ##################################################
        crc_size = 32; # size of crc, in bits
        preamble_size = 16;
        access_code_size = 64;
        # size of packet, including crc, but not including preamble or access_code
        # This is (probably) the number of bits left in the packet once an access_code flag is seen
        # TODO: verify timing of access_code flag with respect to the rest of the packet
        self.pkt_size = pkt_size #use to be: 4000*8 + crc_size 

        # number of bits we're interested in from the input byte stream
        self.significant_bits = 2 
        
        ##################################################
        # Blocks
        ##################################################
        
        # unpack bits takes one byte in and splits it into k bytes out. 
        # bit 0 from input is placed in bit 0 of output byte 0
        # bit 1 from input is placed in bit 0 of output byte 1
        # ... and so on up to k
        self.unpack_bits = gr.unpack_k_bits_bb(self.significant_bits)
        
        # deinterleave splits single stream of bytes at rate of N bytes/sec into two separate 
        # streams of bytes, each at a rate of N/2 bytes/sec
        self.deinterleave = gr.deinterleave(gr.sizeof_char * 1)
        
        self.char_to_float = gr.char_to_float(1)
        
        # Setup the downcounter that will raise the flag for max iterations upon high input
        self.downcounter = digital_ll.downcounter( self.pkt_size )
        
        # Null sinks 1 and 2 for tieing off lose ends
        self.null_sink_1 = gr.null_sink(gr.sizeof_char * 1)
        self.null_sink_2 = gr.null_sink(gr.sizeof_float * 1)

        #self.file_sink = gr.file_sink(gr.sizeof_short * 1, "/home/interlaken/a/cr22845/SDR/generalized-sdr-comms/demos/csma_month2/flag_out.dat")

        ##################################################
        # Connections
        ##################################################
        # unpack byte with bit 0 = data bit and bit 1 = flag bit into two bytes, byte 0 has bit
        # 0 = data bit and byte 1 has bit 0 = flag bit
        self.connect((self, 0), (self.unpack_bits, 0))
        
        # deinterleave to get two streams. One byte stream has only data bits, on stream has only 
        # flag bits
        self.connect((self.unpack_bits, 0), (self.deinterleave, 0))
        
        # send data bytes to null
        self.connect((self.deinterleave, 1), (self.null_sink_1, 0))
        
        # convert flag bytes to floats for use with downcounter
        self.connect((self.deinterleave, 0), (self.char_to_float, 0))
        
        
        # connect the float output to the downcounter block
        self.connect((self.char_to_float, 0), (self.downcounter, 0))
        
        # finally tie it off with a null sink
        self.connect((self.downcounter, 0), (self.null_sink_2, 0))
        

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

    # if probe is unmuted, return channel_busy = True
    def channel_busy(self):
        return self.downcounter.checkFlag( )
    
    def set_pkt_size(self, pkt_size):
        self.pkt_size = pkt_size
        return self.downcounter.setMaxCount( self.pkt_size )
        
