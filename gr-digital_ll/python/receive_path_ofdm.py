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
import time

import copy
import sys
from digital_ll import lincolnlog
from digital_ll import ofdm_demod
from digital_ll.lincolnlog import dict_to_xml

# /////////////////////////////////////////////////////////////////////////////
#                              receive path
# /////////////////////////////////////////////////////////////////////////////

class receive_path_ofdm(gr.hier_block2):
    def __init__(self, rx_callback, options):

	gr.hier_block2.__init__(self, "receive_path",
				gr.io_signature(1, 1, gr.sizeof_gr_complex),
				gr.io_signature(0, 0, 0))


        options = copy.copy(options)    # make a copy so we can destructively modify

        self._verbose     = options.verbose
        self._log         = options.log
        self._pcsthresh   = options.pcsthresh
        self._pcsalpha    = options.pcsalpha
        self._accesstype  = options.channelaccess
        self._rx_callback = rx_callback      # this callback is fired when there's a packet available
        self._n_iter      = options.pcstrain_niter
        self._iter_len    = options.pcstrain_iterlen
        self._pcstrain_flag = options.pcstrain_flag
        self._pcs_waitafter = options.pcs_waitafter

        # receiver
        self.ofdm_rx = ofdm_demod(options, callback=self._rx_callback)

        # Carrier Sensing Blocks
        alpha = self._pcsalpha #default value was 0.001
        thresh = self._pcsthresh   # in dB, will have to adjust (default was 30)
        pcstrain_flag = self._pcstrain_flag
        n_iter = self._n_iter
        iter_len = self._iter_len
        self.probe = digital_ll.probe_avg_mag_sqrd_c(thresh,alpha,pcstrain_flag,n_iter,iter_len)

        self.connect(self, self.ofdm_rx)
        self.connect((self.ofdm_rx, 0), self.probe)
        self.connect((self.ofdm_rx, 1), gr.null_sink(gr.sizeof_float))

        # Display some information about the setup
        if self._verbose:
            self._print_verbage()
        
    def carrier_sensed(self):
        """
        Return True if we think carrier is present.
        """
        # Get the PCS and VCS Flags
        pcsFlag = self.probe.unmuted()
        vcsFlag = self.ofdm_rx.ofdm_recv.preamble_sense_avg.checkFlag()

        # Based upon which type of carrier we are using set the return flag        
        if self._accesstype[0] is 'p':
            grandOldFlag = bool(pcsFlag)
        elif self._accesstype[0] is 'v':
            grandOldFlag = bool(vcsFlag)
        elif self._accesstype[0] is 'a':
            grandOldFlag = bool(pcsFlag or vcsFlag)
        elif self._accesstype[0] is 'n':
            grandOldFlag = False
        else:
            raise Exception('This is not a valid input')
        
        return grandOldFlag

    def check_sample_count(self):
        return self.ofdm_rx.sample_counter.get_sample_count()

    def calibrate_probe( self ):
        """
        Calibrate the PCS (energy detector/probe) to have a threshold learned
        off of the following finite time interval.
        """
        self.probe.signal_begin_calibration( )
        while not self.probe.check_finished_calibration( ):
            pass    #Do nothing. Just wait.

        # Bed-time
        time.sleep(self._pcs_waitafter)

    def carrier_threshold(self):
        """
        Return current setting in dB.
        """
        return self.probe.threshold()

    def set_carrier_threshold(self, threshold_in_db):
        """
        Set carrier threshold.

        @param threshold_in_db: set detection threshold
        @type threshold_in_db:  float (dB)
        """
        self.probe.set_threshold(threshold_in_db)
    
        
    def add_options(normal, expert):
        """
        Adds receiver-specific options to the Options Parser
        """
        normal.add_option("-W", "--bandwidth", type="eng_float",
                          default=500e3,
                          help="set symbol bandwidth [default=%default]")
        normal.add_option("","--coding", type='int', default=None,
                          help="enable FEC coding of the data")
        normal.add_option("","--pcsthresh",default=30, type="eng_float", help="pcs power detection threshold in dB")
        normal.add_option("","--vcsthresh",default=0.15, type="eng_float", help="vcs normalized threshold (1 - alpha)")
        normal.add_option("","--backoff",default=0,type="int", help="Number of samples to backoff when VCS detected (0 causes a default to be set)")
        normal.add_option("","--expected-pkt-size",default=1500,type="int",help="The maximum size (bytes) to expect for packets, used to set backoff when backoff is < 0")
        normal.add_option("","--channelaccess",default="all",help="channel access type to be used [pcs, vcs, all, none]")
        normal.add_option("","--pcsalpha",default=0.001,type="eng_float",help="The alpha parameter used in the single pole filter for the pcs detector")

        normal.add_option("", "--pcstrain_niter",default=5,type="int",help="Number of iterations to run pcs max detection for")
        normal.add_option("", "--pcstrain_iterlen",default=1000000,type="int",help="Number of samples to scan for the max over per iteration")
        normal.add_option("", "--pcstrain_flag", default=0, type="int",help="Use calibration process to learn pcs threshold from noise floor (true). Else use hard threshold")
        normal.add_option("-v", "--verbose", action="store_true", default=False)
        normal.add_option("", "--pcs_waitafter", default=0, type="eng_float", help="Number of seconds to sleep after pcs calibration to allow other nodes time to calibrate")
        expert.add_option("", "--log", action="store_true", default=False,
                          help="Log all parts of flow graph to files (CAUTION: lots of data)")
        
        # adding ofdm_demod options
        ofdm_demod.add_options(normal, expert)

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
    
        # ofdm section start
        logger.info("%s<ofdm>", section_indent*'\t')
        section_indent += 1
        
        # narrowband section param values
        params = {"modulation":self.ofdm_rx._modulation,
                  "coding":self.ofdm_rx._use_coding,
                  "number_of_subcarriers":self.ofdm_rx._fft_length,
                  "number_of_active_subcarriers":self.ofdm_rx._occupied_tones,
                  "cp_length":self.ofdm_rx._cp_length,
                  "channel_access":self._accesstype}
        logger.info(dict_to_xml(params, section_indent))
                
        # channel_sensor section start
        logger.info("%s<channel_sensor>", section_indent*'\t')
        section_indent += 1
        
        # vcs section start
        logger.info("%s<vcs>", section_indent*'\t')
        section_indent += 1
        
        # vcs section param values
        params = {"threshold_norm":self.ofdm_rx._vcsthresh,
                  "backoff_samples":self.ofdm_rx._vcsbackoff,
                  "expected_pkt_size":self.ofdm_rx._expected_pkt_size}
        logger.info(dict_to_xml(params, section_indent))
                
        # vcs section end
        section_indent -= 1
        logger.info("%s</vcs>", section_indent*'\t')

        
        # pcs section start
        logger.info("%s<pcs>", section_indent*'\t')
        section_indent += 1
        
        # pcs section param values
        params = {"pcsthresh":self._pcsthresh,
                  "pcsalpha":self._pcsalpha,
                  "pcstrain_niter":self._n_iter,
                  "pcstrain_iterlen":self._iter_len,
                  "pcstrain_flag":self._pcstrain_flag,
                  "learned_pcs_threshold":self.probe.get_threshold(),}
        logger.info(dict_to_xml(params, section_indent))
                
        # pcs section end
        section_indent -= 1
        logger.info("%s</pcs>", section_indent*'\t')            
        
        # channel_sensor section end
        section_indent -= 1
        logger.info("%s</channel_sensor>", section_indent*'\t')
        
        # ofdm section end
        section_indent -= 1
        logger.info("%s</ofdm>", section_indent*'\t')

        
    def _print_verbage(self):
        """
        Prints information about the receive path
        """
        pass
