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
# Copyright 1980-2012 Free Software Foundation, Inc.
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
import logging
from math import ceil
from math import pi
import Queue
import time

# third party library imports
from gnuradio import gr
import gnuradio.digital as gr_digital
from gnuradio.digital import packet_utils
from gruel import pmt

import numpy

# project specific imports
import digital_ll

# /////////////////////////////////////////////////////////////////////////////
#                  EOB Shifter
# /////////////////////////////////////////////////////////////////////////////

class eob_shifter(gr.sync_block):
    """
    This block corrects for the offset in end of burst tags caused by
    upsampling. It assumes that all eob tags have already had their 
    offsets scaled by the upsampling ratio N. It will then shift
    the tags by N-1 samples to push them to the end of the set of upsampled
    samples they are associated with
    """
    def __init__(
        self,upsamp_factor
    ):
        """
        The input is an integer upsampling factor

        """


        gr.sync_block.__init__(
            self,
            name = "eob_shifter",
            in_sig = [numpy.complex64],
            out_sig = [numpy.complex64]
        )
    
        self.dev_logger = logging.getLogger('developer')
    
        self.upsamp_factor = int(upsamp_factor)
        self.set_tag_propagation_policy(gr.gr_block.TPP_DONT)
        self.eob_key = "tx_eob"
        self.tag_residues = []
        
    def work(self, input_items, output_items):

                           
        in0 = input_items[0]
        out = output_items[0]
        
        
        
        nread = self.nitems_read(0) #number of items read on port 0
        ninput_items = len(input_items[0])
        noutput_items = len(output_items[0])

        nitems_to_consume = min(ninput_items, noutput_items)

        out[:nitems_to_consume] = in0[:nitems_to_consume]
        
        # output any tags left over from the last iteration if they're ready
        ready_tags = [x for x in self.tag_residues if x[0] < self.nitems_written(0) + ninput_items]
        
        # test if we're writing past what we're allowed
        for tag in ready_tags:
            if tag[0] >= self.nitems_written(0) + nitems_to_consume:
                self.dev_logger.error("writing tags out of range. bad idea")
        
        
        for offset, key, value, srcid in ready_tags:
#            self.dev_logger.debug("adding key %s value %s source %s at offset %s",
#                                  key,value,srcid, offset)
            self.add_item_tag(0,offset, pmt.from_python(key), pmt.from_python(value), pmt.from_python(srcid))  
        
        
        # keep tags in residues that aren't ready yet
        self.tag_residues = [x for x in self.tag_residues if x[0] >= self.nitems_written(0) + ninput_items]
        
        #read all tags associated with port 0 for items in this work function
        tags = self.get_tags_in_range(0, nread, nread+nitems_to_consume)
        
        for tag in tags:
            
            if pmt.pmt_symbol_to_string(tag.key) == self.eob_key:
                new_offset = tag.offset + self.upsamp_factor-1
                
                # if the new offset is still in this work block, shift the tag. 
                # Otherwise store the tag tuple for the next call
                if new_offset < self.nitems_written(0) + ninput_items:
#                    self.dev_logger.debug("adding key %s value %s source %s at offset %s",
#                                  pmt.to_python(tag.key),pmt.to_python(tag.value),pmt.to_python(tag.srcid), new_offset)
                    self.add_item_tag(0,new_offset, tag.key, tag.value, tag.srcid)
                else:
                    # turning into native python types in case seg fault issue is due to memory management
                    self.tag_residues.append( (new_offset, pmt.to_python(tag.key), pmt.to_python(tag.value), pmt.to_python(tag.srcid)) )
            else:
#                self.dev_logger.debug("adding key %s value %s source %s at offset %s",
#                                  pmt.to_python(tag.key),pmt.to_python(tag.value),pmt.to_python(tag.srcid), tag.offset)
                self.add_item_tag(0,tag.offset, tag.key, tag.value, tag.srcid)
        
        
        
        return nitems_to_consume			
