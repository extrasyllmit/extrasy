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
from cmath import exp
from math import pi
from optparse import OptionParser

# third party library imports
from gnuradio import blks2
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio import window
from gnuradio.eng_option import eng_option
from gnuradio.gr import firdes
from grc_gnuradio import blks2 as grc_blks2
from gruel import pmt

import numpy

# project specific imports
import digital_ll
from digital_ll import pfb_channelizer
from digital_ll import tag_logger
from digital_ll import time_spec_t
from digital_ll.lincolnlog import dict_to_xml

# block port definitions
#SCHEDULE_IN_PORT = pmt.from_python('sched_in')

USE_NEW_TX_CHANNELIZER = True
USE_NEW_RX_CHANNELIZER = True

class tx_channelizer(gr.hier_block2):
    """
    tx_channelizer(options, sample_rate)
    derives from gr.hier_block2
    """
    def __init__(self, options, dev_logger=None, digital_channel_number=0):
        # Constructor
        gr.hier_block2.__init__(self, "rx_channelizer",
        gr.io_signature(1, 1, gr.sizeof_gr_complex), # Input signature
        gr.io_signature(1, 1, gr.sizeof_gr_complex)) # Output signature

        # Add the options as member variables
        self.dev_logger    = dev_logger
        self.num_chan      = options.digital_freq_hop_num_channels
        self.trans_bw      = options.tx_channelizer_transition_bandwidth
        self.att_dB        = options.tx_channelizer_attenuation_db
        self.current_chan  = digital_channel_number
        samp_rate          = 1         # This is only used as a place holder. Sample rate
                                       # dealt with as discrete-time (1 = Fs)

        # # Define the normalized frequencies that specify the center of the channels
        self.define_channel_freqs()

        # Create the poly upsampler's filter
        self.filt = gr.firdes.low_pass_2(1, samp_rate, float(samp_rate)/self.num_chan/2.0, self.trans_bw, attenuation_dB=self.att_dB, window=gr.firdes.WIN_BLACKMAN_hARRIS) 

        # Create the necessary blocks
        self.interpolator = filter.pfb.interpolator_ccf(self.num_chan, (self.filt))
        
        if not USE_NEW_TX_CHANNELIZER:
        	self.modulator_source = gr.sig_source_c(samp_rate, gr.GR_COS_WAVE, self.norm_channel_freq[0], 1, 0)
        	self.multiply         = gr.multiply_vcc(1)
        else:
        	self.modulator    = digital_ll.modulator( self.num_chan, self.current_chan )

        # Connect the blocks
        self.connect(self, (self.interpolator, 0))
        
        if USE_NEW_TX_CHANNELIZER:
        	self.connect((self.interpolator, 0), (self.modulator, 0))
        	self.connect((self.modulator, 0), (self, 0))
        
        else:
        	self.connect((self.interpolator, 0), (self.multiply,0))
        	self.connect((self.modulator_source, 0), (self.multiply,1))
        	self.connect((self.multiply,0), self)

        # Set the modulator to be on the right channel
        self.switch_channels(self.current_chan)

    def define_channel_freqs(self):
        # Return the normalized channel frequencies that correspond to the center
        # of the channels defined by digital_ll/include/pfb_channelizer_ccf.h
        self.norm_channel_freq = [0,]*self.num_chan
        for n in range(0, self.num_chan):
            self.norm_channel_freq[n] = float(n)/self.num_chan

    def switch_channels(self, channel_number):
        # Switch the signal source to have a new frequency given by channel number
        if not USE_NEW_TX_CHANNELIZER:
        	self.modulator_source.set_frequency(self.norm_channel_freq[channel_number])
       	else:
        	self.modulator.switch_channels(channel_number)


    def add_options(parser):
        parser.add_option("","--tx-channelizer-transition-bandwidth", type="float", default=0.01, help="The transition bandwidth of the filter implemented in the Tx Channelizer (cycles/sample)")
        parser.add_option("","--tx-channelizer-attenuation-db", type="float", default=30, help="The stop band attenation in dB of the filter implemented in the Tx Channelizer")
    add_options = staticmethod(add_options)
    
    def log_results(self, indent_level, logger):
        
        section_indent = (indent_level)
        
        logger.info('%s<tx_channelizer>', section_indent*'\t')
        
        params = {  "number_digital_channels":self.num_chan,
                    "channelizer_transition_bandwidth":self.trans_bw,
                    "channelizer_attenuation_dB":self.att_dB,
                    "digital_channel_number":self.current_chan }
        logger.info(dict_to_xml(params, section_indent+1))   
        
        logger.info('%s</tx_channelizer>', section_indent*'\t')

class rx_channelizer(gr.hier_block2):
    """
    rx_channelizer(options, sample_rate)
    derives from gr.hier_block2
    """
    def __init__(self, options, dev_logger=None, digital_channel_number=0):
        # Constructor
        gr.hier_block2.__init__(self, "rx_channelizer",
		    gr.io_signature(1, 1, gr.sizeof_gr_complex), # Input signature
	        gr.io_signature(1, 1, gr.sizeof_gr_complex)) # Output signature        

        # Add the options as member variables
        self.dev_logger     = dev_logger
        self.num_chan       = options.digital_freq_hop_num_channels
        self.trans_bw       = options.rx_channelizer_transition_bandwidth
        self.att_dB         = options.rx_channelizer_attenuation_db
        self.current_chan   = digital_channel_number
        self.beacon_channel = -1
        self.osr            = 1         # Oversampling rate
        samp_rate           = 1         # This is only used as a place holder. Sample rate
                                        # dealt with as discrete-time (1 = Fs)
        
        # Design the channelizer's filter
        self.filt = gr.firdes.low_pass_2(1, samp_rate, float(samp_rate)/self.num_chan/2.0, self.trans_bw, attenuation_dB=self.att_dB, window=gr.firdes.WIN_BLACKMAN_hARRIS)
        
        # Generate the blocks that will be used
        self.channelizer    = pfb_channelizer(self.num_chan, (self.filt), self.osr, 100)
        
        if not USE_NEW_RX_CHANNELIZER:
		    self.mux            = grc_blks2.selector( item_size=gr.sizeof_gr_complex*1,
		                            	num_inputs=self.num_chan, num_outputs=1,
		                            	input_index=self.current_chan, output_index=0)
        else:
        	self.mux = digital_ll.selector( self.num_chan, self.current_chan, 0 )
        
        # Connect the blocks
        for n in range(0, self.num_chan):
            exec 'self.connect( (self.channelizer, ' + str(n) + '), (self.mux, ' + str(n) + ') )'
        
        #self.tagger = heart_beat_tagger(125000,1,"heart_beat_tagger","heart_beat_tagger")
        
        #self.connect(self, (self.tagger, 0))
        #self.connect((self.tagger, 0), (self.channelizer, 0))
        self.connect(self, (self.channelizer, 0))
        self.connect((self.mux, 0), self)
               
        #self.tag1 = tag_logger( gr.sizeof_gr_complex, '/home/g103homes/a/stahlbuhk/Desktop/beforeFB.dat' )
        #self.tag2 = tag_logger( gr.sizeof_gr_complex, '/home/g103homes/a/stahlbuhk/Desktop/afterFB.dat' )
    
        #self.connect(self.tagger, self.tag1)
        #self.connect((self.mux, 0), self.tag2)
    
    
    def switch_channels(self, channel_number):
        # Switch to the channel of interest
        assert(channel_number < self.num_chan)
        self.mux.set_input_index(channel_number)
        self.current_chan = channel_number
    
    def add_options(parser):
        # Add input options to parser
        parser.add_option("","--digital-freq-hop-num-channels", type="int", 
                          default=1, 
                          help="Number of digital channels to use in the channelizer")
        parser.add_option("","--rx-channelizer-transition-bandwidth", type="float", default=0.01, help="The transition bandwidth of the filter implemented in the Rx Channelizer (cycels/sample)")
        parser.add_option("","--rx-channelizer-attenuation-db", type="float", default=30, help="The stop band attenation in dB of the filter implemented in the Rx Channelizer")
    add_options = staticmethod(add_options)
        
    def log_results(self, indent_level, logger):
        
        section_indent = (indent_level)
        
        logger.info('%s<rx_channelizer>', section_indent*'\t')
        
        params = {  "number_digital_channels":self.num_chan,
                    "channelizer_transition_bandwidth":self.trans_bw,
                    "channelizer_attenuation_db":self.att_dB,
                    "digital_channel_number":self.current_chan,
                    "oversampling_rate":self.osr }
        logger.info(dict_to_xml(params, section_indent+1))   
        
        logger.info('%s</rx_channelizer>', section_indent*'\t')
    
    def return_to_beacon_channel(self, blank=0):
        # Record the action with dev_logger
        if not self.dev_logger is None:
            self.dev_logger.debug("Freq Hop: Returning to the beacon channel %s", self.beacon_channel)
        self.mux.return_to_beacon_channel()
    
    def set_beacon_channel(self, beacon_channel):
        self.beacon_channel = beacon_channel
        # Record the action with dev_logger
        if not self.dev_logger is None:
            self.dev_logger.debug("Freq Hop: The beacon channel is being set to %s", self.beacon_channel)
        self.mux.set_beacon_channel( beacon_channel)
    
    def channelizer_command(self, sched):
        '''
        Set the channelizer's schedule:
            The input sched should be a tuple.
                First element tuple of (int, fractional) seconds of beginning
                of frame
                Second element should be the frame length in seconds
                Third element should be a list specifying the number of seconds
                from the start of the frame when each slot begins
                Fourth element should be the channel index of each slot
        '''
    
        # Get the frame starting time
        t0      = sched[0]       # tuple of size 2 (integer sec, fractional sec)
        t0_int  = t0[0]
        t0_frac = t0[1]
        
        # Get the frame length
        frame_length = sched[1]  # frame total length in seconds (double)
        slot_times   = sched[2]  # slot starting times since t0 in seconds (list of doubles)
        slot_freqs   = sched[3]  # each slots desired channel (list of integers)
        
        # Check the channels coming in
        for i,n in enumerate(slot_freqs):
            assert n >= 0 and n < self.num_chan,\
                "Slot %r has channel %r which is greater than the number of channels %r" % (i, n, self.num_chan)
        
        # Record the action with dev_logger
        if not self.dev_logger is None:
            self.dev_logger.debug("Freq Hop: A new schedule starting at time %d + %f set", t0_int, t0_frac)
        
        # Set the schedule in the mux
        self.mux.set_schedule(t0_int, t0_frac, frame_length, slot_times, slot_freqs)
        
    def handle_schedule_update(self, sched):
        """
        This function will be called
        to update the digital_ll_selector's schedule.
        
        It expects a dictionary with the follow keys:data
            'valid': is this a valid field? If true, look at the schedule and
                     pass it to the C++ mux code to create a new channel
                     hopping schedule. If false, return to the desigated
                     beacon channel.
            't0'   : If valid true, this field should indicate the start of
                     the frame in GMT Posix time. This schedule will be
                     automatically replicated in time at multiples of
                     the frame length until a new schedule's t0 time is passed.
            'slots': A list of tuples where each tuple is a new slot assignment
                     description.
                     The tuples elements should have the following position indexed meaning
                        element 0) Do not care
                        element 1) The length of each slot in seconds as double
                        element 2) The time offset from beginning of frame of each slot
                                   should be a double.
                        element 3 & 4) Do not care
                        element 5) The integer index of the digital channel to hop to
                                   for this time slot.
        
        The frame time length is determined by the time offset of the last slot
        plus the time length of that slot.
        
        The mux C++ code will automatically replicate a frame schedule each frame time length
        seconds until it reaches a new frame schedules t0 time.
        """
        
        # sched should be a tuple consisting of double and int for when
        # the channel hopping should begin
        if sched is not None:
            print "The rx channelizer got schedule update. Schedule valid: %s" % sched["valid"]
            
            # If this is a valid message, pass it to the C++ code. Else return to beacon channel
            if sched["valid"]:
                t0_int  = sched["t0"].int_s   # time to begin frame (int seconds)
                t0_frac = sched["t0"].frac_s  # time to begin frame (fractional seconds)
                
                slot_times   = [float(slot[2]) for slot in sched["slots"]] # time to begin slot
                slot_lengths = [float(slot[1]) for slot in sched["slots"]]   # length of each slot
                slot_freqs   = [int(slot[5]) for slot in sched["slots"]]   # freq. of each slot
                
                frame_length = slot_times[-1] + slot_lengths[-1] # length of the frame
                
                slot_times   = tuple(slot_times)
                slot_freqs   = tuple(slot_freqs)
                
                self.mux.set_schedule(t0_int, t0_frac, frame_length, slot_times, slot_freqs)
            else:
                self.mux.return_to_beacon_channel( )


# Define a Tukey Window
# This code below was taken from the following source: http://leohart.wordpress.com/2006/01/29/hello-world/

# Not to be confused with functions to be used on the Windows OS
# These window functions are similar to those found in the Windows toolbox of MATLAB
# Note that numpy has a couple of Window functions already:
# See: hamming, bartlett, blackman, hanning, kaiser
def tukeywin(window_length, alpha=0.5):
    '''
    The Tukey window, also known as the tapered cosine window, can be regarded as a cosine lobe of width \alpha * N / 2
    that is convolved with a rectangle window of width (1 - \alpha / 2). At \alpha = 1 it becomes rectangular, and
    at \alpha = 0 it becomes a Hann window.
 
    We use the same reference as MATLAB to provide the same results in case users compare a MATLAB output to this function
    output
 
    Reference
    ---------
 
    http://www.mathworks.com/access/helpdesk/help/toolbox/signal/tukeywin.html
 
    '''
    # Special cases
    if alpha <= 0:
        return numpy.ones(window_length) #rectangular window
    elif alpha >= 1:
        return numpy.hanning(window_length)
 
    # Normal case
    x = numpy.linspace(0, 1, window_length)
    w = numpy.ones(x.shape)
 
    # first condition 0 <= x < alpha/2
    first_condition = x<alpha/2
    w[first_condition] = 0.5 * (1 + numpy.cos(2*numpy.pi/alpha * (x[first_condition] - alpha/2) ))
 
    # second condition already taken care of
 
    # third condition 1 - alpha / 2 <= x <= 1
    third_condition = x>=(1 - alpha/2)
    w[third_condition] = 0.5 * (1 + numpy.cos(2*numpy.pi/alpha * (x[third_condition] - 1 + alpha/2))) 
 
    return w
        
