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
from digital_ll import lincolnlog
from time_spec import time_spec_t

class tdma_logger(gr.sync_block):
    """
    TDMA logger to pull out stream tags and send to lincolnlog
    """
    def __init__(self,logging, upsample_factor=1.):
        gr.sync_block.__init__(
            self,
            name = "tdma_logger",
            in_sig = [numpy.complex64],
            out_sig = None
        )
        
        self._logging = logging
        self._sob_found = False
        self._tx_time_offset = 0.0
        self._tx_rate_value = 1.0
        #self._tx_time_value = 0.0
        self._tx_time_spec_t = time_spec_t(0.0)
        self._upsample_factor = upsample_factor
    
    def work(self, input_items, output_items):
                    
        #process streaming samples and tags here
        in0 = input_items[0]
        nread = self.nitems_read(0) #number of items read on port 0
        ninput_items = len(input_items[0])

        #print "nread in logger is " + str(nread)
        #print "ninput_items is " + str(ninput_items)

        #out = output_items[0]        
        #out[:] = in0[:]

        #read all tags associated with port 0 for items in this work function
        tags = self.get_tags_in_range(0, nread, nread+ninput_items)

        #sort by key first so that this order is preserved for same offset when sorting by offset
        tags = sorted(tags, key=lambda tag : pmt.pmt_symbol_to_string(tag.key), reverse=True)        
        
        #sort by tag.offset
        tags = sorted(tags, key=lambda tag : tag.offset)

        #call lincoln log
        if self._logging != -1:

            #lets find all of our tags, making the appropriate adjustments to our timing
            for tag in tags:
                key_string = pmt.pmt_symbol_to_string(tag.key)
                
                #print "found key : " + key_string + " at offset " + str(tag.offset) 
            
                if key_string == 'tx_sob':
                    self._sob_found = True
            
                if key_string == 'tx_time':
                    tx_time_offset = tag.offset
                    tx_time_tuple  = pmt.to_python(tag.value)
                    tx_time_spec_t = time_spec_t(tx_time_tuple[0],tx_time_tuple[1])
                    #tx_time_value = tx_time_spec_t.__float__()
                    self._tx_time_offset = tx_time_offset
                    #self._tx_time_value = tx_time_value
                    self._tx_time_spec_t = tx_time_spec_t
                    #print "tx_time_value is " + str(tx_time_value)

                if key_string == 'tx_rate':
                    tx_rate_offset = tag.offset
                    tx_rate_value  = float(pmt.to_python(tag.value))
                    self._tx_rate_value = tx_rate_value*self._upsample_factor


                if key_string == 'packetlog':
                    packetlog_offset = tag.offset
                    packetlog_value  = pmt.to_python(tag.value)
                    
                    if self._sob_found:
                        offset_from_sob = packetlog_offset - self._tx_time_offset
                        time_from_sob   = offset_from_sob / float(self._tx_rate_value)
                        #packetlog_time  = self._tx_time_value + time_from_sob
                        packetlog_time_spec_t  = self._tx_time_spec_t + time_spec_t(time_from_sob)
                        
                        #packetlog_value['timestamp'] = packetlog_time
                        packetlog_value['timestamp'] = str(packetlog_time_spec_t)
                        
                        #print packetlog_value                                        
                        self._logging.packet(packetlog_value)
            
            #print "--------------logger------------------------"
                    
                    
        return ninput_items

                    

