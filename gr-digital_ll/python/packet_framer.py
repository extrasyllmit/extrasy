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
from collections import deque
import logging
from math import pi
from Queue import Queue
import time

# third party library imports
from gnuradio import gr
import gnuradio.digital as gr_digital
from gruel import pmt

import numpy

# project specific imports
from beacon_utils import generate_packet
from digital_ll import packet_utils2


#import gnuradio.extras as gr_extras

# /////////////////////////////////////////////////////////////////////////////
#                   mod/demod with packets as i/o
# /////////////////////////////////////////////////////////////////////////////

class packet_framer(gr.sync_block):
    """
    The input is a pmt message blob.
    Non-blob messages will be ignored.
    The output is a byte stream for the modulator
    """

    def __init__(
        self,
        fs,
        samples_per_symbol,
        bits_per_symbol,
        access_code=None,
        pad_for_usrp=True,
        use_whitener_offset=False,
        use_coding=0,
        packet_format='tdma',
        number_digital_channels=1
    ):
        """
        Create a new packet framer.
        @param access_code: AKA sync vector
        @type access_code: string of 1's and 0's between 1 and 64 long
        @param use_whitener_offset: If true, start of whitener XOR string is incremented each packet
        """

        

        gr.sync_block.__init__(
            self,
            name = "framer",
            in_sig = None,
            out_sig = [numpy.uint8]
        )
        
        self.IN_PORT = pmt.from_python('in')
        
#        self.in_packets = Queue()
        self.in_packets = deque()
        
        self.message_port_register_in(self.IN_PORT)
        self.set_msg_handler(self.IN_PORT, self.handle_pdu)
        
        self._bits_per_symbol = bits_per_symbol
        self._samples_per_symbol = samples_per_symbol
        self._pad_for_usrp = pad_for_usrp
        self._use_whitener_offset = use_whitener_offset
        self._whitener_offset = 0
        self._use_coding = use_coding
        self._packet_format = packet_format
        self._fs = fs
        self._number_digital_channels=number_digital_channels
        
        self._dev_logger = logging.getLogger('developer')

        if not access_code:
            access_code = packet_utils2.default_access_code
        if not packet_utils2.is_1_0_string(access_code):
            raise ValueError, "Invalid access_code %r. Must be string of 1's and 0's" % (access_code,)
        self._access_code = access_code
        
        print "access code: %s" % self._access_code
        
        self._pkt = []
        self.more_frame_cnt = 0
        self.keep = False
        
        


    def handle_pdu(self,pdu):
#        print "handle pdu"
        # make sure the pdu is a pmt pair
        if pmt.pmt_is_pair(pdu):
        
            # get the first and last elements of the pair
            meta = pmt.to_python(pmt.pmt_car(pdu))
            vect = pmt.to_python(pmt.pmt_cdr(pdu))
            
            # make sure there's some metadata associated with the packet, otherwise 
            # drop it
            if meta is not None:
#                self.in_packets.put( (meta,vect) )
                self.in_packets.append( (meta,vect) )
#                print "appended packets"
                    

    def convert_channel_to_hz( self, index ):
        if self._number_digital_channels > 1:
            if index >= self._number_digital_channels:
                assert False, 'The scheduled channel is %d which is not a valid channel when %d channels are specified'\
                    % (index, self._number_digital_channels)
            freq = self._fs*index/float(self._number_digital_channels)
            if freq >= self._fs/2.0:
                freq = freq - self._fs
        else:
            freq = 0
        return freq
    

    def work(self, input_items, output_items):
        #print "in work"
        
        offset = self.nitems_written(0)
        item_index = 0
        
        while not len(self._pkt):
#            try: meta, payload = self.in_packets.get(True,.1)
            try: 
                meta, payload = self.in_packets.popleft()
                if len(payload) == 0:
                    payload = ""
            
            # FIXME meta["frequency"] will be baseband frequency. 
            except IndexError: 
                #print "can't pop yet"
                return 0
            
            if "tx_time" in meta: 
                self.tx_time = meta["tx_time"]
                self.more_frame_cnt = meta["more_pkt_cnt"]
                self.has_tx_time = True
                
                # clear tx_time and more_pkt_count from the packet metadata, since
                # they shouldn't go in the logs
                del meta["tx_time"]
                del meta["more_pkt_cnt"]
                
                #print payload
                #print tx_time
                #print payload.tostring()
            else:

                #print payload
                self.has_tx_time = False
            
            pkt = packet_utils2.make_packet(payload, 
                                            self._samples_per_symbol, 
                                            self._bits_per_symbol,
                                            None, # options
                                            self._access_code,
                                            False, #pad_for_usrp 
                                            self._use_coding,
                                            None, # logging
                                            self._whitener_offset)   

            # add any metadata params that don't belong in the over the air packet
            meta["direction"] = "transmit" # packet framer is always in transmit direction
            meta["messagelength"] = len(pkt)
             
            self._pkt = numpy.fromstring(pkt, numpy.uint8)
            if self._use_whitener_offset:
                self._whitener_offset = (self._whitener_offset + 1) % 16

            #shouldn't really need to send start of burst
            #only need to do sob if looking for timed transactions
            
            num_items = min(len(self._pkt), len(output_items[0]))
            output_items[0][item_index:item_index+num_items] = self._pkt[:num_items]
            self._pkt = self._pkt[num_items:] #residue for next work()
#            print "num items: %d  length _pkt: %d" %(num_items, len(self._pkt))
            if len(self._pkt) == 0 :
                 #which output item gets the tag?
                
                source = pmt.pmt_string_to_symbol("framer")
                
                # add tx rate tag if this is the first packet in the run
                if offset + item_index == 0:
                    key = pmt.pmt_string_to_symbol("tx_rate")
                    val = pmt.from_python(self._fs)
                    self.add_item_tag(0, offset+item_index, key, val, source)
                
                if self.has_tx_time:
                    key = pmt.pmt_string_to_symbol("tx_sob")
                    self.add_item_tag(0, offset+item_index, key, pmt.PMT_T, source)
                    key = pmt.pmt_string_to_symbol("tx_time")
                    self.add_item_tag(0, offset+item_index, key, pmt.from_python(self.tx_time), source)
                    # FIXME Add tx_new_channel tag which specifies the channel
                    key = pmt.pmt_string_to_symbol("tx_new_channel")
                    #if "frequency" in meta.keys():
                    #    meta["frequency"] = self.convert_channel_to_hz(meta["frequency"])
                    self.add_item_tag(0, offset+item_index, key, pmt.from_python(meta["frequency"]), source)
                    

                    self._dev_logger.debug("adding tx_sob with time %s at offset %ld", 
                                           self.tx_time,offset+item_index)
                    #if self.keep:
                    #    print 'bad order'
                    #self.keep = True

                 # add packet metadata tag
                key = pmt.pmt_string_to_symbol("packetlog")
                val = pmt.from_python(meta)
                #print "sending packet %d bytes" % meta["messagelength"]
#                print "adding packet log tag at offset %ld" %( offset+item_index)
                self.add_item_tag(0, offset+item_index, key, val, source)    
                
                # add length of current packet to item index
                item_index+=num_items
                
                if self.more_frame_cnt == 0:
#                    print "adding tx_eob tag at offset %ld" %( offset+item_index)
                    key = pmt.pmt_string_to_symbol("tx_eob")
                    self.add_item_tag(0, offset + item_index-1, key, pmt.PMT_T, source)
                    self._dev_logger.debug("adding tx_eob at offset %ld", 
                                           offset + item_index-1)
                    #if self.keep:
                    #    print 'good order'
                    #self.keep = False
                    
               
                else:
                    self.more_frame_cnt -= 1
            
            return item_index            
        else:
            #print "self._pkt had residue"
            num_items = min(len(self._pkt), len(output_items[0]))
            output_items[0][:num_items] = self._pkt[:num_items]
            self._pkt = self._pkt[num_items:] #residue for next work()
            return item_index + num_items
    
    
    def num_bytes_to_num_samples(self, payload_len): 
        '''
        Compute the number of samples a packet will occupy based on the length of the
        packet payload, which includes any mac or higher layer headers
        '''
        return packet_utils2.ncomplex_samples(payload_len, 
                                               self._samples_per_symbol, 
                                               self._bits_per_symbol, 
                                               self._use_coding)
        
class packet_deframer(gr.hier_block2):
    """
    Hierarchical block for demodulating and deframing packets.

    The input is a byte stream from the demodulator.
    The output is a pmt message blob.
    """

    def __init__(self, access_code=None, threshold=-1):
        """
        Create a new packet deframer.
        @param access_code: AKA sync vector
        @type access_code: string of 1's and 0's
        @param threshold: detect access_code with up to threshold bits wrong (-1 -> use default)
        @type threshold: int
        """

        gr.hier_block2.__init__(
            self,
            "demod_pkts2",
            gr.io_signature(1, 1, 1),
            gr.io_signature(1, 1, 1),
        )

        if not access_code:
            access_code = packet_utils2.default_access_code
        if not packet_utils2.is_1_0_string(access_code):
            raise ValueError, "Invalid access_code %r. Must be string of 1's and 0's" % (access_code,)

        if threshold == -1:
            threshold = 12              # FIXME raise exception

        msgq = gr.msg_queue(4)          # holds packets from the PHY
        self.correlator = gr_digital.correlate_access_code_bb(access_code, threshold)

        self.framer_sink = gr.framer_sink_1(msgq)
        self.connect(self, self.correlator, self.framer_sink)
        self._queue_to_blob = _queue_to_blob(msgq)
        self.connect(self._queue_to_blob, self)





class _queue_to_blob(gr.basic_block):
    """
    Helper for the deframer, reads queue, unpacks packets, posts.
    It would be nicer if the framer_sink output'd messages.
    """
    def __init__(self, msgq):
        gr.block.__init__(
            self, name = "_queue_to_blob",
            in_sig = None, out_sig = None,
            num_msg_outputs = 1
        )
        self._msgq = msgq
        self._mgr = pmt.pmt_mgr()
        for i in range(64):
            self._mgr.set(pmt.pmt_make_blob(10000))

    def work(self, input_items, output_items):
        while True:
            try: msg = self._msgq.delete_head()
            except: return -1
            ok, payload = packet_utils2.unmake_packet(msg.to_string(), int(msg.arg1()))
            if ok:
                payload = numpy.fromstring(payload, numpy.uint8)
                try: blob = self._mgr.acquire(True) #block
                except: return -1
                pmt.pmt_blob_resize(blob, len(payload))
                pmt.pmt_blob_rw_data(blob)[:] = payload
                self.post_msg(0, pmt.pmt_string_to_symbol("ok"), blob)
            else:
                a = 0

