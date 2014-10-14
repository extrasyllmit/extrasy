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
#
# 
# This file incorporates work covered by the following copyright:
#
#
# Copyright 2010,2011 Free Software Foundation, Inc.
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
from optparse import OptionParser
import sys

# third party library imports
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import uhd
from gnuradio.eng_option import eng_option

# project specific imports
from digital_ll.lincolnlog import dict_to_xml



uhd_error_codes = {0x00:'ERROR_CODE_NONE',             
                   0x01:'EVENT_CODE_BURST_ACK: A burst was successfully transmitted',       
                   0x02:'EVENT_CODE_UNDERFLOW: An internal send buffer has emptied',       
                   0x04:'EVENT_CODE_SEQ_ERROR: Packet loss between host and device',
                   0x08:'EVENT_CODE_TIME_ERROR: Packet had time that was late',
                   0x10:'EVENT_CODE_UNDERFLOW_IN_PACKET: Underflow occurred inside a packet',
                   0x20:'EVENT_CODE_SEQ_ERROR_IN_BURST: Packet loss within a burst',
                   0x40:'EVENT_CODE_USER_PAYLOAD: Some kind of custom user payload',
                   } 

#def add_freq_option(parser):
#    """
#    Hackery that has the -f / --freq option set both tx_freq and rx_freq
#    """
#    def freq_callback(option, opt_str, value, parser):
#        parser.values.rx_freq = value
#        parser.values.tx_freq = value
#
#    if not parser.has_option('--freq'):
#        parser.add_option('-f', '--freq', type="eng_float",
#                          action="callback", callback=freq_callback,
#                          help="set Tx and/or Rx frequency to FREQ [default=%default]",
#                          metavar="FREQ")

class uhd_interface:
    def __init__(self, istx, args, sym_rate, sps, freq=None,
                 gain=None, spec=None, antenna=None):
        
        if(istx):
            self.u = uhd.usrp_sink(device_addr=args, stream_args=uhd.stream_args('fc32'))
        else:
            self.u = uhd.usrp_source(device_addr=args, stream_args=uhd.stream_args('fc32'))

#        self.u.set_clock_source("external", 0)
#        self.u.set_time_source("external", 0)
        
        # Set the subdevice spec
        if(spec):
            self.u.set_subdev_spec(spec, 0)

        # Set the antenna
        if(antenna):
            self.u.set_antenna(antenna, 0)
        
        self._args = args
        self._ant  = antenna
        self._spec = spec
        self._gain = self.set_gain(gain)
        self._freq = self.set_freq(freq)

        self._rate, self._sps = self.set_sample_rate(sym_rate, sps)
        print "RF front end sensor names are: "
        print self.u.get_sensor_names(0)
        print "Motherboard sensor names are: "
        print self.u.get_mboard_sensor_names(0)
        print "Ref locked: "
        print self.u.get_mboard_sensor("ref_locked",0)
        #print "ref locked is: "
        #print self.u.get_sensor("ref_locked",0)

    def set_sample_rate(self, sym_rate, req_sps):
        start_sps = req_sps
        while(True):
            asked_samp_rate = sym_rate * req_sps
            self.u.set_samp_rate(asked_samp_rate)
            actual_samp_rate = self.u.get_samp_rate()

            sps = actual_samp_rate/sym_rate
            if(sps < 2):
                req_sps +=1
            else:
                actual_sps = sps
                break
        
        if(sps != req_sps):
            print "\nSymbol Rate:         %f" % (sym_rate)
            print "Requested sps:       %f" % (start_sps)
            print "Given sample rate:   %f" % (actual_samp_rate)
            print "Actual sps for rate: %f" % (actual_sps)

        if(actual_samp_rate != asked_samp_rate):
            print "\nRequested sample rate: %f" % (asked_samp_rate)
            print "Actual sample rate: %f" % (actual_samp_rate)

        return (actual_samp_rate, actual_sps)

    def get_sample_rate(self):
        return self.u.get_samp_rate()
    
    def set_gain(self, gain=None):
        if gain is None:
            # if no gain was specified, use the mid-point in dB
            g = self.u.get_gain_range()
            gain = float(g.start()+g.stop())/2
            print "\nNo gain specified."
            print "Setting gain to %f (from [%f, %f])" % \
                (gain, g.start(), g.stop())
        
        self.u.set_gain(gain, 0)
        return gain

    def set_freq(self, freq=None):
        if(freq is None):
            sys.stderr.write("You must specify -f FREQ or --freq FREQ\n")
            sys.exit(1)
        
        #r = self.u.set_center_freq(freq, 0)
	r = self.u.set_center_freq(uhd.tune_request(freq,10e6), 0)
        if r:
            return freq
        else:
            frange = self.u.get_freq_range()
            sys.stderr.write(("\nRequested frequency (%f) out or range [%f, %f]\n") % \
                                 (freq, frange.start(), frange.stop()))
            sys.exit(1)

#-------------------------------------------------------------------#
#   TRANSMITTER
#-------------------------------------------------------------------#

class uhd_transmitter(uhd_interface, gr.hier_block2):
    def __init__(self, args, sym_rate, sps, freq=None, gain=None,
                 spec=None, antenna=None, verbose=False):
        gr.hier_block2.__init__(self, "uhd_transmitter",
                                gr.io_signature(1,1,gr.sizeof_gr_complex),
                                gr.io_signature(0,0,0))

        # Set up the UHD interface as a transmitter
        uhd_interface.__init__(self, True, args, sym_rate, sps,
                               freq, gain, spec, antenna)

        self.connect(self, self.u)

        if(verbose):
            self._print_verbage()
            
    def add_options(parser):
#        add_freq_option(parser)
        parser.add_option("", "--usrp-args", type="string", default="",
                          help="UHD device address args [default=%default]",
                          )
        parser.add_option("", "--usrp-spec", type="string", default=None,
                          help="Subdevice of UHD device where appropriate",
                          )
        parser.add_option("", "--usrp-antenna", type="string", default=None,
                          help="select Rx Antenna where appropriate",
                          )
        parser.add_option("", "--rf-tx-freq", type="eng_float", default=None,
                          help="set transmit frequency to FREQ [default=%default]",
                          metavar="FREQ")
        parser.add_option("", "--rf-tx-gain", type="eng_float", default=None,
                          help="set transmit gain in dB (default is midpoint)",
                          )
        parser.add_option("-v", "--verbose", action="store_true", default=False)

    # Make a static method to call before instantiation
    add_options = staticmethod(add_options)

    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''
                
        section_indent = indent_level
        
        # tx front end section start
        logger.info("%s<tx_frontend>", section_indent*'\t')
        section_indent += 1
        
        # tx front end section param values
        params = {"args":self._args,
                  "rf_frequency":self._freq,
                  "tx_gain":self._gain,
                  "sample_rate":self._rate,
                  "antenna":self._ant,    
                  "spec":self._spec}
        logger.info(dict_to_xml(params, section_indent))
        
        # tx front end section end
        section_indent -= 1
        logger.info("%s</tx_frontend>", section_indent*'\t')
        
    def _print_verbage(self):
        """
        Prints information about the UHD transmitter
        """
        print "\nUHD Transmitter:"
        print "Args:     %s"    % (self._args)
        print "Freq:        %sHz"  % (eng_notation.num_to_str(self._freq))
        print "Gain:        %f dB" % (self._gain)
        print "Sample Rate: %ssps" % (eng_notation.num_to_str(self._rate))
        print "Antenna:     %s"    % (self._ant)
        print "Subdev Sec:  %s"    % (self._spec)


#-------------------------------------------------------------------#
#   RECEIVER
#-------------------------------------------------------------------#


class uhd_receiver(uhd_interface, gr.hier_block2):
    def __init__(self, args, sym_rate, sps, freq=None, gain=None,
                 spec=None, antenna=None, verbose=False):
        gr.hier_block2.__init__(self, "uhd_receiver",
                                gr.io_signature(0,0,0),
                                gr.io_signature(1,1,gr.sizeof_gr_complex))
      
        # Set up the UHD interface as a receiver
        uhd_interface.__init__(self, False, args, sym_rate, sps,
                               freq, gain, spec, antenna)

        self.connect(self.u, self)

        if(verbose):
            self._print_verbage()

    def add_options(parser):
#        add_freq_option(parser)
        parser.add_option("", "--usrp-args", type="string", default="",
                          help="UHD device address args [default=%default]")
        parser.add_option("", "--usrp-spec", type="string", default=None,
                          help="Subdevice of UHD device where appropriate")
        parser.add_option("", "--usrp-antenna", type="string", default=None,
                          help="select Rx Antenna where appropriate")
        parser.add_option("", "--rf-rx-freq", type="eng_float", default=None,
                          help="set receive frequency to FREQ [default=%default]",
                          metavar="FREQ")
        parser.add_option("", "--rf-rx-gain", type="eng_float", default=None,
                          help="set receive gain in dB (default is midpoint)",
                          )
        if not parser.has_option("--verbose"):
            parser.add_option("-v", "--verbose", action="store_true", default=False)

    # Make a static method to call before instantiation
    add_options = staticmethod(add_options)

    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''
                
        section_indent = indent_level
        
        # rx front end section start
        logger.info("%s<rx_frontend>", section_indent*'\t')
        section_indent += 1
        
        # rx front end section param values
        params = {"args":self._args,
                  "rf_frequency":self._freq,
                  "rx_gain":self._gain,
                  "sample_rate":self._rate,
                  "antenna":self._ant,    
                  "spec":self._spec}
        logger.info(dict_to_xml(params, section_indent))
        
        # rx front end section end
        section_indent -= 1
        logger.info("%s</rx_frontend>", section_indent*'\t')

    def _print_verbage(self):
        """
        Prints information about the UHD transmitter
        """
        print "\nUHD Receiver:"
        print "UHD Args:    %s"    % (self._args)
        print "Freq:        %sHz"  % (eng_notation.num_to_str(self._freq))
        print "Gain:        %f dB" % (self._gain)
        print "Sample Rate: %ssps" % (eng_notation.num_to_str(self._rate))
        print "Antenna:     %s"    % (self._ant)
        print "Spec:        %s"    % (self._spec)
