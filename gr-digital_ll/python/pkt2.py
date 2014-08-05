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
# Copyright 2005, 2006, 2007 Free Software Foundation, Inc.
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
from math import pi

# third party library imports
from gnuradio import digital
from gnuradio import gr
import gnuradio.gr.gr_threading as _threading
from grc_gnuradio import blks2 as grc_blks2

# project specific imports
from digital_ll import framer_sink_1
from digital_ll import lincolnlog
from digital_ll import tag_logger
import packet_utils2 as packet_utils 


# /////////////////////////////////////////////////////////////////////////////
#                   custom subclass of pkt
# /////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////
#                   mod/demod with packets as i/o
# /////////////////////////////////////////////////////////////////////////////

class mod_pkts(gr.hier_block2):
    """
    Wrap an arbitrary digital modulator in our packet handling framework.

    Send packets by calling send_pkt
    """
    def __init__(self, modulator, options, access_code=None, msgq_limit=2, pad_for_usrp=True,
                 use_whitener_offset=False, modulate=True, use_coding=0, logging=-1):
        """
    Hierarchical block for sending packets

        Packets to be sent are enqueued by calling send_pkt.
        The output is the complex modulated signal at baseband.

        @param modulator: instance of modulator class (gr_block or hier_block2)
        @type modulator: complex baseband out
        @param access_code: AKA sync vector
        @type access_code: string of 1's and 0's between 1 and 64 long
        @param msgq_limit: maximum number of messages in message queue
        @type msgq_limit: int
        @param pad_for_usrp: If true, packets are padded such that they end up a multiple of 128 samples
        @param use_whitener_offset: If true, start of whitener XOR string is incremented each packet
        
        See gmsk_mod for remaining parameters
        """

        gr.hier_block2.__init__(self, "mod_pkts",
                gr.io_signature(1, 1, gr.sizeof_char),                    # Input signature
                gr.io_signature(1, 1, gr.sizeof_gr_complex)) # Output signature

        self._modulator = modulator
        self._pad_for_usrp = pad_for_usrp
        self._use_whitener_offset = use_whitener_offset
        self._whitener_offset = 0
        
        #just added to take coding from benchmark_tx
        self._use_coding = use_coding
        self._logging = logging
        self._options = options

        if access_code is None:
            access_code = packet_utils.default_access_code
        if not packet_utils.is_1_0_string(access_code):
            raise ValueError, "Invalid access_code %r. Must be string of 1's and 0's" % (access_code,)
        self._access_code = access_code
        
        # accepts messages from the outside world
        self._pkt_input = gr.message_source(gr.sizeof_char, msgq_limit)
        self.null_sink = gr.null_sink(gr.sizeof_char)
        
        self.connect(self._pkt_input, self._modulator, self)
        self.connect(self,self.null_sink)

    def send_pkt(self, payload='', eof=False):
        """
        Send the payload.

        @param payload: data to send
        @type payload: string
        """
        if eof:
            msg = gr.message(1) # tell self._pkt_input we're not sending any more packets
        else:
            # print "original_payload =", string_to_hex_list(payload)
            pkt = packet_utils.make_packet(payload,
                                           self._modulator.samples_per_symbol(),
                                           self._modulator.bits_per_symbol(),
                                           self._options,
                                           self._access_code,
                                           self._pad_for_usrp,
                                           self._use_coding, #added on 09/20/2012
                                           self._logging,    #added on 09/24/2012
                                           self._whitener_offset)
            #print "pkt =", string_to_hex_list(pkt)
            msg = gr.message_from_string(pkt)
            if self._use_whitener_offset is True:
                self._whitener_offset = (self._whitener_offset + 1) % 16
        
            print 'modulating %f bytes' % len(pkt)
                
        self._pkt_input.msgq().insert_tail(msg)

    def use_streaming_inputs(self, stream_enable=True):
        
        # prepare to reconfigure
#        self.lock()

        # wire block input directly to modulator
        if stream_enable == True:
            self.disconnect((self._pkt_input,0), (self._modulator, 0))
            self.disconnect(self,self.null_sink)
            self.connect(self, self._modulator)
        
        # wire pkt_input to modulator
        else:
            self.disconnect((self,0), (self._modulator, 0))
            self.connect(self._pkt_input, self._modulator)
            self.connect(self,self.null_sink)
#        self.unlock() 
        
        return 

    def num_complex_samples(self, payloadlen=0):
        return packet_utils._ncomplex_samples(payloadlen,
                                              self._modulator.samples_per_symbol(),
                                              self._modulator.bits_per_symbol())
           
    def max_pkt_size(self):
    # TODO: Get refined packet size from Tri    
        if self._use_coding:
            return 2000-17
        else:
            return 4000-17   
    
class demod_pkts(gr.hier_block2):
    """
    Wrap an arbitrary digital demodulator in our packet handling framework.

    The input is complex baseband.  When packets are demodulated, they are passed to the
    app via the callback.
    """

    def __init__(self, demodulator, options, access_code=None, callback=None, threshold=-1, use_coding=0, logging=-1):
        """
	Hierarchical block for demodulating and deframing packets.

	The input is the complex modulated signal at baseband.
        Demodulated packets are sent to the handler.

        @param demodulator: instance of demodulator class (gr_block or hier_block2)
        @type demodulator: complex baseband in
        @param access_code: AKA sync vector
        @type access_code: string of 1's and 0's
        @param callback:  function of two args: ok, payload
        @type callback: ok: bool; payload: string
        @param threshold: detect access_code with up to threshold bits wrong (-1 -> use default)
        @type threshold: int
	"""

	gr.hier_block2.__init__(self, "demod_pkts",
				gr.io_signature(1, 1, gr.sizeof_gr_complex), # Input signature
				gr.io_signature(0, 0, 0))                    # Output signature

        self._demodulator = demodulator
        if access_code is None:
            access_code = packet_utils.default_access_code
        if not packet_utils.is_1_0_string(access_code):
            raise ValueError, "Invalid access_code %r. Must be string of 1's and 0's" % (access_code,)
        self._access_code = access_code

        #just added to take coding from benchmark_rx
        self._use_coding = use_coding
        self._logging = logging
        self._options = options
        
        
            
        
        # added to simplify logging
        self._threshold = options.access_code_threshold


        if threshold == -1:
            threshold = 4              # FIXME raise exception

        self._rcvd_pktq = gr.msg_queue()          # holds packets from the PHY
        self._time_pktq = gr.msg_queue()          # holds packet timestamps from the PHY
        self._chan_pktq = gr.msg_queue()          # holds packet channels from the PHY
        
        self.correlator = digital.correlate_access_code_bb(access_code, threshold)

        self.framer_sink = framer_sink_1(self._rcvd_pktq, self._time_pktq, self._chan_pktq)
        self.connect(self, self._demodulator, self.correlator, self.framer_sink)
        
        self._watcher = _queue_watcher_thread(self._rcvd_pktq, self._time_pktq, self._chan_pktq, callback, self._use_coding, self._logging, self._options)


    
        # declare tag loggers
#        self.logger_0 = tag_logger(gr.sizeof_char*1, "demodTags.txt")
#        self.logger_1 = tag_logger(gr.sizeof_char*1, "corrTags.txt")    
        
        # connect tag loggers
#        self.connect(self._demodulator, self.logger_0)
#        self.connect(self.correlator, self.logger_1)   
    
    # make channel_busy flag from sync watcher available at the demod_pkts object level    


class _queue_watcher_thread(_threading.Thread):
    def __init__(self, rcvd_pktq, time_pktq, chan_pktq, callback, use_coding, logging, options):
        _threading.Thread.__init__(self)
        self.setDaemon(1)
        self.rcvd_pktq = rcvd_pktq
        self.time_pktq = time_pktq
        self.chan_pktq = chan_pktq
        self.callback = callback
        self.keep_running = True
        self.start()
        self._use_coding = use_coding
        self._logging = logging
        self._options = options

    def run(self):
        while self.keep_running:
            msg = self.rcvd_pktq.delete_head()
            timestamp = self.time_pktq.delete_head()
            channel = self.chan_pktq.delete_head()
            #channel = 0
            ok, payload = packet_utils.unmake_packet(msg.to_string(),
                                                     self._options,    #added on 9/28/12
                                                     self._use_coding, #added on 09/20/2012
                                                     self._logging,    #added on 09/24/2012
                                                     int(msg.arg1()))
            if self.callback:
                #print "found packet"
                self.callback(ok, payload, (long(timestamp.arg1()), float(timestamp.arg2())), long(channel.arg1()) )
