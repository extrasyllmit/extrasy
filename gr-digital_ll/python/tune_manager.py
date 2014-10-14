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
import logging
from operator import itemgetter

# third party library imports

# project specific imports

class tune_manager(object):
    '''
    classdocs
    '''

    last_freq = None
    
    def __init__(self, tune_delay=2e-3):
        '''
        Constructor
        '''
        self.last_freq = 0
        self.tune_delay = tune_delay
        self.dev_log = logging.getLogger('developer')
        
    def add_tune_commands(self, frame_config, cmd_list):
        
        new_rf_freq = frame_config["slots"][0].rf_freq
        
        if new_rf_freq != self.last_freq:
            
            self.dev_log.info("Tuning to %f at t0: %f", new_rf_freq, frame_config["t0"])
            
            cmd_list.append( (frame_config["t0"], new_rf_freq, 'txrx_tune') ) 
#            cmd_list.append( (frame_config["t0"], new_rf_freq, 'rx_tune') )
            
            self.last_freq = new_rf_freq
            # sort command list by timestamp
            cmd_list.sort(key=itemgetter(0))
            
            # tweak the first slot to allow for tuning latency
            slot = frame_config["slots"][0]
            new_offset = slot.offset+self.tune_delay
            new_len = slot.len-self.tune_delay
            
            frame_config["slots"][0] = slot._replace(offset=new_offset,
                                                     len=new_len)
            
        return cmd_list, frame_config
        
        