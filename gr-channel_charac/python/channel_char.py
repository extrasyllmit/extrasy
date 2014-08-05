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

from gnuradio import eng_notation
from gnuradio import fft
from gnuradio import gr
from gnuradio import uhd
from gnuradio import window
from gnuradio.eng_option import eng_option
from gnuradio.gr import firdes
from grc_gnuradio import wxgui as grc_wxgui
from optparse import OptionParser
import wx
import channel_charac
from math import log10
from math import floor
from math import ceil
from math import sqrt
import random
import numpy as np
import time
from digital_ll.lincolnlog import dict_to_xml


class channel_char_run(gr.top_block):
    
    def __init__(self, options):
        gr.top_block.__init__(self)
        
        ##################################################
        # Variables
        ##################################################
        self.samp_rate      = options.samp_rate
        self.nfft           = options.num_tx_tones
        self.cf             = options.rf_cf
        self.K              = options.num_rx_tones
        self.Lt             = options.num_nodes
        self.n_avg          = options.num_averages
        self.wait_noise     = options.noise_delay
        self.wait_sig       = options.rx_delay
        self.tx_gain        = options.rf_tx_gain
        self.rx_gain        = options.rf_rx_gain
        self.digital_scale  = options.signal_scale
        self.from_file      = options.from_file
        self.id             = options.node_id
        self.search_size    = options.search_size
        self.wait_quit      = options.run_duration
        self.wait_tx        = options.tx_delay
        self.to_file        = options.to_file
        
        ###################################################
        # Get a channel_char block
        ###################################################
        self.cc = channel_char(options)
        
        ###################################################
        # Rx Chain
        ###################################################
        if self.to_file == -1:
            if self.from_file == -1:
                self.uhd_usrp_source_0 = uhd.usrp_source(
                	device_addr=options.usrp,
                	stream_args=uhd.stream_args(
                		cpu_format="fc32",
                		channels=range(1),
                	),
                )
                self.uhd_usrp_source_0.set_clock_source("external", 0)
                self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)
                self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(self.cf,10e6), 0)
                self.uhd_usrp_source_0.set_gain(self.rx_gain, 0)
                self.uhd_usrp_source_0.set_antenna("RX2", 0)
            else:
                self.gr_file_source_0 = gr.file_source(gr.sizeof_gr_complex*1, self.from_file, True)
                
            if self.from_file == -1:
                self.connect((self.uhd_usrp_source_0, 0), (self.cc, 0))
            else:
                self.gr_null_sink_0 = gr.null_sink(gr.sizeof_gr_complex*1)
                self.connect((self.cc, 0), (self.gr_null_sink_0, 0))
                self.connect((self.gr_file_source_0, 0), (self.cc, 0))
                
        
        ###################################################
        # Tx Chain
        ###################################################
        if self.from_file == -1:
            if self.to_file == -1:
                self.tx_sink = uhd.usrp_sink(device_addr=options.usrp,stream_args=uhd.stream_args(cpu_format="fc32",channels=range(1),),)
                self.tx_sink.set_clock_source("external", 0)
                self.tx_sink.set_samp_rate(self.samp_rate)
                self.tx_sink.set_center_freq(uhd.tune_request(self.cf,10e6), 0)
                self.tx_sink.set_gain(self.tx_gain, 0)
            else:
                self.tx_sink = gr.file_sink(gr.sizeof_gr_complex*1, self.to_file)
                self.gr_null_source_0 = gr.null_source(gr.sizeof_gr_complex*1)
                self.connect((self.gr_null_source_0, 0), (self.cc))
            
            self.connect((self.cc, 0), (self.tx_sink, 0))
    
    def print_result(self):
        if self.to_file == -1:
            self.cc.print_result()
        
    def wait_until_finished(self):
        if self.from_file == -1:
            self.cc.wait_until_finished()
    
    def poke(self):
        self.cc.poke()
        
    def add_options_run(parser):
        parser.add_option("","--usrp",type="string",default="addr=192.168.10.2",help="Channel Sounding Stand-Alone: The address of the USRP to use (Must be in format 'addr=XXX.XXX.XX.X')")
        parser.add_option("","--samp-rate",default=1e6,type="float",help="Channel Sounding Stand-Alone: The sample frequency to use (SPS)")
        parser.add_option("","--from-file",type="string",default=-1,help="Channel Sounding Stand-Alone: Name of file to read in and run")
        parser.add_option("","--to-file",type="string",default=-1,help="Channel Sounding Stand-Alone: Name of file to write generated samples to")
        parser.add_option("","--rf-cf",default=1111e6,type="float",help="Channel Sounding Stand-Alone: The center frequency to use (Hz).")
    add_options_run = staticmethod(add_options_run) 

class channel_char(gr.hier_block2):
    """
    channel_char
    derives from gr.hier_block2
    
    This class returns an object that is able to both generate a sounding
    waveform and receive a sounding waveform to generate the appropriate
    statistics. The input is a gr_complex stream to process and the output
    is a gr_complex stream to transmit. Putting null_source/sink on the I/O
    will cause the channel_char to only do actions in one direction.
    
    The required options list is very extensive. See the __init__ code to 
    find out what everything means.
    """

    def __init__(self, options, use_sounding = True):

        gr.hier_block2.__init__(self, "channel_char",
			gr.io_signature(1, 1, gr.sizeof_gr_complex), # Input signature
			gr.io_signature(1, 1, gr.sizeof_gr_complex)) # Output signature

        ##################################################
        # Variables
        ##################################################
        self.samp_rate      = options.samp_rate
        self.nfft           = options.num_tx_tones
        self.cf             = options.rf_cf
        self.K              = options.num_rx_tones
        self.Lt             = options.num_nodes
        self.n_avg          = options.num_averages
        self.wait_noise     = options.noise_delay
        self.wait_sig       = options.rx_delay
        self.tx_gain        = options.rf_tx_gain
        self.rx_gain        = options.rf_rx_gain
        self.digital_scale  = options.signal_scale
        self.id             = options.node_id
        self.search_size    = options.search_size
        self.wait_quit      = options.run_duration
        self.wait_tx        = options.tx_delay

        ##################################################
        # Set Default K and Lt
        ##################################################
        if self.K == -1:
            usable = self.nfft/2 - 2
            self.K = int(self.Lt*floor(usable/self.Lt))

        ##################################################
        # Simple Checks
        ##################################################
        if use_sounding:
            assert self.K % self.Lt == 0, 'K must be divisible by Lt for channel souding technique'
            assert self.nfft >= 2*(self.K+1), 'nfft must be >= 2*(K + 1) for channel sounding technique'
            assert self.id != -1, 'The id must be specified for channel sounding technique'
            assert self.Lt != -1, 'The number of nodes in the test must be specified for channel sound technique'
        else:
            self.id = 1
            self.Lt = 1

        ##################################################
        # Set default wait times if signalled to
        ##################################################
        if self.wait_noise == -1:
            self.wait_noise = int(round(0.5*self.samp_rate))
        
        if self.wait_tx   == -1:
            self.wait_tx = int(round(self.wait_noise + 6*self.samp_rate + self.n_avg*self.nfft))
        
        if self.wait_sig == -1:
            self.wait_sig = int(round(self.wait_tx + 6*self.samp_rate))
        
        if self.wait_quit == -1:
            self.wait_quit = int(round(self.wait_sig + 6*self.samp_rate + self.n_avg*self.nfft))


        ##################################################
        # Blocks for Rx Chain
        ##################################################
        self.gr_stream_to_vector_0 = gr.stream_to_vector(gr.sizeof_gr_complex*1, self.nfft)
        self.fft_vxx_0 = fft.fft_vcc(self.nfft, True, ([1,]*self.nfft), True, 1)
        self.post_fft_analysis = channel_charac.test( self.nfft, self.K, self.Lt, self.n_avg, self.wait_sig, self.wait_noise )

        ##################################################
        # Connections for Rx Chain
        ##################################################
        self.connect(self, self.gr_stream_to_vector_0)
        self.connect((self.gr_stream_to_vector_0, 0), (self.fft_vxx_0, 0))
        self.connect((self.fft_vxx_0, 0), (self.post_fft_analysis, 0))
  
        ##################################################
        # Tx Chain
        ##################################################
        upsample_factor = 2;
        min_papr        = float('inf');
        
        # Average power for a digital tx signal with digital scale = 1
        self.avgpwr = 0.5
        
        # Search for a low PAPR signal
        for n in range(0, self.search_size):
            X   = [0,]*self.nfft
            Xup = [0,]*(self.nfft*upsample_factor)
        
            # Populate upper band
            for k in range(0, int(ceil(self.K/2.0/self.Lt))):
                r = random.sample([-1, 1], 1)
                X[2*self.id + 2*self.Lt*k] = r[0]   
            
            # Populate lower band
            for k in range(0, int(floor(self.K/2.0/self.Lt))):
                r = random.sample([-1.0,1.0], 1)
                offset = int(floor(k/float(self.Lt)))
                X[self.nfft - 2*(self.Lt-self.id+1) - 2*self.Lt*k] = r[0]
            
            # Create the upsampled signal to calculate the PAPR
            X_shift = np.fft.ifftshift(X)
            pos     = int(ceil((upsample_factor-1)*self.nfft/2.0))
            Xup[pos:pos+self.nfft] = X_shift
            Xup     = np.fft.fftshift(Xup)
            Xup     = np.array(Xup)
            xup     = abs(np.fft.ifft(Xup))
            
            # Calculate the PAPR
            xmax    = max(abs(xup)**2)                       # Maximum value
            xvar    = np.sum(np.square(xup))/xup.size   # Power
            papr    = xmax/xvar
            
            # If this is the minimum PAPR save off the transmit signal
            if papr < min_papr:
                min_papr = papr
                X        = np.array(X)
                x        = np.fft.ifft(X)
                pwrx     = (self.K/self.Lt)/float(self.nfft**2) # Power before normalizing
                for k in range(0, len(x)):
                    x[k] = sqrt(self.avgpwr/pwrx)*x[k] # Normalize power to default amount
                    x[k] = self.digital_scale*x[k]     # Apply the digital scaling
                self.maxv = max(abs(x))
                x_save   = x.tolist()
        
        self.papr = min_papr
        
        # Generate the blocks to transmit the waveform
        self.siggen = channel_charac.signal_gen( x_save, self.wait_tx, self.wait_quit )
        self.connect(self.siggen, self)


    def get_log_results( self, indent_level ):
        '''
        Return the results as an XML formatted string.
        '''
    
        section_indent = (indent_level)
        string = ""
        string = string + "%s<channel_sounding>" % (section_indent*"\t")
        
        # Log the test parameters
        string = string + "%s<sounding_parameters>" % ((section_indent+1)*"\t")
        test_params = { "id":self.id,
                        "tx_papr":self.papr,
                        "tx_maximum_sample":self.maxv,
                        "center_frequency_Hz":self.cf,
                        "bandwidth_Hz":self.samp_rate,
                        "tx_gain_dB":self.tx_gain,
                        "rx_gain_dB":self.rx_gain,
                        "digital_scaling":self.digital_scale,
                        "K_bins_occupied":self.K,
                        "nfft_bins":self.nfft,
                        "number_fft_avg":self.n_avg,
                        "wait_noise":self.wait_noise,
                        "wait_tx":self.wait_tx,
                        "wait_sig":self.wait_sig,
                        "wait_quit":self.wait_quit }
        string = string + dict_to_xml(test_params, section_indent+2)       
        string = string + "%s</sounding_parameters>\n" % ((section_indent+1)*"\t")
        
        # Wait until we are done observing the channel
        done = False
        while not done:
            time.sleep(0.01)
            done = self.post_fft_analysis.SNR_calculation_ready()
        
        # Get the various measurements and write to file
        tx_dpwr    = (self.digital_scale**2)*self.avgpwr
        tx_pwr_eq, rx_pwr_eq = get_pwr_equations( self.cf, self.tx_gain, self.rx_gain ) # returned in dB
        
        snr = [0,]*self.nfft
        sinr= [0,]*self.nfft
        pwr = [0,]*self.nfft
        Np  = [0,]*self.nfft
        Ip  = [0,]*self.nfft
        for n in range(1, self.Lt+1):
            # Get the results
            snr[n] = self.post_fft_analysis.return_SNR_2step(n)
            pwr[n] = self.post_fft_analysis.return_sig_power(n)
            Np[n]   = self.post_fft_analysis.return_noise_power(n)
            Ip[n]   = self.post_fft_analysis.return_odd_bin_power(n)
            sinr[n]= self.post_fft_analysis.return_SNR(n)
            
            string = string + "%s<results>" % ((section_indent+1)*"\t")
            test_params = { "other_node_id":n,
                            "tx_discrete_sig_pwr_dB":(10*log10(tx_dpwr)), 
                            "rx_discrete_sig_pwr_dB":(10*log10(pwr[n])),
                            "rx_discrete_noise_pwr_dB":(10*log10(Np[n])),
                            "rx_discrete_txfloor_pwr_dB":(10*log10(Ip[n])),
                            "tx_analog_sig_pwr_dB":(tx_pwr_eq + 10*log10(tx_dpwr)),
                            "rx_analog_sig_pwr_dB":(rx_pwr_eq + 10*log10(pwr[n])),
                            "rx_analog_noise_pwr_dB":(rx_pwr_eq + 10*log10(Np[n])),
                            "rx_analog_txfloor_pwr_dB":(rx_pwr_eq + 10*log10(Ip[n])),
                            "pathloss_dB":(tx_pwr_eq + 10*log10(tx_dpwr) - (rx_pwr_eq + 10*log10(pwr[n]))),
                            "snr_dB":(10*log10(snr[n])),
                            "signal_to_txfloor_pwr_dB":(10*log10(sinr[n])) }
            string = string + dict_to_xml(test_params, section_indent+2)
            string = string + "%s</results>\n" % ((section_indent+1)*"\t")
            
        string = string + "%s</channel_sounding>\n" % (section_indent*"\t")
        return string
        
        
    def log_results(self, indent_level, logger):
    
        section_indent = (indent_level)
        
        logger.info("%s<channel_sounding>", section_indent*"\t")
        
        # Log the test parameters
        logger.info("%s<sounding_parameters>", (section_indent+1)*"\t")
        test_params = { "id":self.id,
                        "tx_papr":self.papr,
                        "tx_maximum_sample":self.maxv,
                        "center_frequency_Hz":self.cf,
                        "bandwidth_Hz":self.samp_rate,
                        "tx_gain_dB":self.tx_gain,
                        "rx_gain_dB":self.rx_gain,
                        "digital_scaling":self.digital_scale,
                        "K_bins_occupied":self.K,
                        "nfft_bins":self.nfft,
                        "number_fft_avg":self.n_avg,
                        "wait_noise":self.wait_noise,
                        "wait_tx":self.wait_tx,
                        "wait_sig":self.wait_sig,
                        "wait_quit":self.wait_quit }
        logger.info(dict_to_xml(test_params, section_indent+2))        
        
        logger.info("%s</sounding_parameters>", (section_indent+1)*"\t")
        
        # Wait until we are done observing the channel
        done = False
        while not done:
            time.sleep(0.01)
            done = self.post_fft_analysis.SNR_calculation_ready()
        
        # Get the various measurements and write to file
        tx_dpwr    = (self.digital_scale**2)*self.avgpwr
        tx_pwr_eq, rx_pwr_eq = get_pwr_equations( self.cf, self.tx_gain, self.rx_gain ) # returned in dB
        
        snr = [0,]*self.nfft
        sinr= [0,]*self.nfft
        pwr = [0,]*self.nfft
        Np  = [0,]*self.nfft
        Ip  = [0,]*self.nfft
        for n in range(1, self.Lt+1):
            # Get the results
            snr[n] = self.post_fft_analysis.return_SNR_2step(n)
            pwr[n] = self.post_fft_analysis.return_sig_power(n)
            Np[n]   = self.post_fft_analysis.return_noise_power(n)
            Ip[n]   = self.post_fft_analysis.return_odd_bin_power(n)
            sinr[n]= self.post_fft_analysis.return_SNR(n)
            
            logger.info("%s<results>", (section_indent+1)*"\t")
            
            test_params = { "other_node_id":n,
                            "tx_discrete_sig_pwr_dB":(10*log10(tx_dpwr)), 
                            "rx_discrete_sig_pwr_dB":(10*log10(pwr[n])),
                            "rx_discrete_noise_pwr_dB":(10*log10(Np[n])),
                            "rx_discrete_txfloor_pwr_dB":(10*log10(Ip[n])),
                            "tx_analog_sig_pwr_dB":(tx_pwr_eq + 10*log10(tx_dpwr)),
                            "rx_analog_sig_pwr_dB":(rx_pwr_eq + 10*log10(pwr[n])),
                            "rx_analog_noise_pwr_dB":(rx_pwr_eq + 10*log10(Np[n])),
                            "rx_analog_txfloor_pwr_dB":(rx_pwr_eq + 10*log10(Ip[n])),
                            "pathloss_dB":(tx_pwr_eq + 10*log10(tx_dpwr) - (rx_pwr_eq + 10*log10(pwr[n]))),
                            "snr_dB":(10*log10(snr[n])),
                            "signal_to_txfloor_pwr_dB":(10*log10(sinr[n])) }
            logger.info(dict_to_xml(test_params, section_indent+2)) 
            
            logger.info("%s</results>", (section_indent+1)*"\t")
            
        logger.info("%s</channel_sounding>", section_indent*"\t")
    
    def print_result(self):
        done = False
        while not done:
            time.sleep(0.01)
            done = self.post_fft_analysis.SNR_calculation_ready()
        
        print '************************************************************'
        print 'Reporting for Node', self.id
        print '    My Tx signal PAPR =', self.papr
        if self.maxv <= 1:
            print '    Maximum scaled sample =', self.maxv
        else:
            print '    Maximum scaled sample =', self.maxv, '(Warning: Clipping!)'
        print '    Center Freq =', self.cf/1.0e6, 'MHz'
        print '    Bandwidth  =', self.samp_rate/1.0e3, 'kHz'
        print '    Tx Gain =', self.tx_gain, 'dB'
        print '    Rx Gain = ', self.rx_gain, 'dB'
        print '    Digital Scaling =', self.digital_scale
        print '    K =', self.K, '(bins occupied)'
        print '    NFFT =', self.nfft, '(bins total)'
        print '-------------------------'
        print 'Pathloss and SNR Results:'
        
        # Calculate the transmitted digital power
        tx_dpwr    = (self.digital_scale**2)*self.avgpwr
        tx_pwr_eq, rx_pwr_eq = get_pwr_equations( self.cf, self.tx_gain, self.rx_gain ) # returned in dB
        
        snr = [0,]*self.nfft
        sinr= [0,]*self.nfft
        pwr = [0,]*self.nfft
        Np  = [0,]*self.nfft
        Ip  = [0,]*self.nfft
        for n in range(1, self.Lt+1):
            # Get the results
            snr[n] = self.post_fft_analysis.return_SNR_2step(n)
            pwr[n] = self.post_fft_analysis.return_sig_power(n)
            Np[n]   = self.post_fft_analysis.return_noise_power(n)
            Ip[n]   = self.post_fft_analysis.return_odd_bin_power(n)
            sinr[n]= self.post_fft_analysis.return_SNR(n)
            
            # Print the results to screen
            if n == self.id:
                print 'From Tx No.', n, '(ie, Me!)'
            else:
                print 'From Tx No.', n
            print '    Transmitted Discrete Signal Power: %0.7f' % (10*log10(tx_dpwr)), 'dB/samp'
            print '    Received Discretized Signal Power: %0.7f' % (10*log10(pwr[n])), 'dB/samp'
            print '    Received Discretized Noise Power:  %0.7f' % (10*log10(Np[n])), 'dB/samp'
            print '    Received Tx Floor Power:           %0.7f' % (10*log10(Ip[n])), 'dB/samp'
            print '    Estimated Transmitted Power at Tx: %0.7f' % (tx_pwr_eq + 10*log10(tx_dpwr)), 'dBm'
            print '    Estimated Received Power at Rx:    %0.7f' % (rx_pwr_eq + 10*log10(pwr[n])), 'dBm'
            print '    Estimated Noise Power at Rx:       %0.7f' % (rx_pwr_eq + 10*log10(Np[n])), 'dBm'
            print '    Estimated Power of Tx Floor at Rx: %0.7f' % (rx_pwr_eq + 10*log10(Ip[n])), 'dBm'
            print '    Estimated Path Loss between Tx/Rx: %0.7f' % (tx_pwr_eq + 10*log10(tx_dpwr) - (rx_pwr_eq + 10*log10(pwr[n]))), 'dB'
            print '    Signal to Noise Ratio:             %0.7f' % (10*log10(snr[n])), 'dB'
            print '    Signal to Tx Floor Ratio:          %0.7f' % (10*log10(sinr[n])), 'dB'
            
        print '************************************************************'

    def poke(self):
        self.post_fft_analysis.poke()
        self.siggen.poke()

    def wait_until_finished(self):
        done = False
        while not done:
            time.sleep(0.01)
            nsamps = self.siggen.get_samples_processed()
            done   = nsamps > self.wait_quit

    def get_nfft(self):
        return self.nfft

    def set_nfft(self, nfft):
        self.nfft = nfft
        
    def add_options(parser):
        parser.add_option("","--num-nodes",type="int",default=-1,help="Channel Sounding: The number of nodes participating in test (Note: K should be divisible by Lt)")
        parser.add_option("","--node-id",type=int,default=-1,help="Channel Sounding: The id number of this node. All nodes in a test should have a unique ID from the set {1:Lt}")
        parser.add_option("","--num-tx-tones",default=64,type="int",help="Channel Sounding: The size of the FFT to use. Default value chosen if not specified.")
        parser.add_option("","--num-rx-tones",default=-1,type="int",help="Channel Sounding: The number of bins to use. Default value chosen if not specified.")
        
        parser.add_option("","--num-averages",type="int",default=10,help="Channel Sounding: The number of averages to take the measurements over (ie, tests last nfft*n_avg*fs)")
        parser.add_option("","--noise-delay",type="int",default=-1,help="Channel Sounding: The amount of time in samples to wait before measuring noise")
        parser.add_option("","--tx-delay",type="int",default=-1,help="Channel Sounding: The amount of time in samples to wait before beginning to transmit sounding symbols")
        parser.add_option("","--rx-delay",type="int",default=-1,help="Channel Sounding: The amount of time to wait in samples before measuring signal")
        parser.add_option("","--run-duration",type="int",default=-1,help="Channel Sounding: The amount of time in samples to wait before finishing all transmissions and shutting down")
        
        parser.add_option("","--rf-tx-gain",type="float",default=10,help="Channel Sounding: The USRP front-end adjustable transmitter gain used during channel sounding technique")
        parser.add_option("","--rf-rx-gain",type="float",default=10,help="Channel Sounding: The USRP front-end adjustable receiver gain used during channel sounding technique")
        
        parser.add_option("","--search-size",type="int",default=20000,help="Channel Sounding: The number of tx signals to generate to find the one with the lowest PAPR")
        parser.add_option("","--signal-scale",type="float",default=1,help="Channel Sounding: Scaling to apply to the discrete signal to transmit")
    # Make a static method to call before instantiation
    add_options = staticmethod(add_options) 

def get_pwr_equations( cf, tx_gain, rx_gain ):
    tx_pwr_eq  = -0.0056706*cf/1.0e6 +  6.176 + tx_gain # already in dB
    rx_pwr_eq  =  0.0028850*cf/1.0e6 + -7.84  - rx_gain # already in dB
    return tx_pwr_eq, rx_pwr_eq
        
def main():
    # Take care of the inputs assigning defaults if necessary
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    channel_char.add_options(parser)
    channel_char_run.add_options_run(parser)
    (options, args) = parser.parse_args()
    
    # Tora, tora, tora
    tb = channel_char_run(options)
    tb.start()
    tb.poke()
    tb.print_result()
    tb.wait_until_finished()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

