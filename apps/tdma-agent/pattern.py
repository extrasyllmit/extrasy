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

'''
Example Pattern File. Works for 5 digital channels and up
'''
from collections import namedtuple

PatternTuple = namedtuple("PatternTuple", 'owner len offset type bb_freq')

slot_init = PatternTuple



FRAME_LEN_01 = 0.60000 

SET_01 = [
    {"frame_len":FRAME_LEN_01,
     "rf_freq_ind":0,
     "slots":[slot_init(owner=0, len=0.1, offset=0.0, type=  "beacon", bb_freq=0),
              slot_init(owner=1, len=0.1, offset=0.1, type="downlink", bb_freq=1),
              slot_init(owner=2, len=0.1, offset=0.2, type=  "uplink", bb_freq=4),
              slot_init(owner=0, len=0.1, offset=0.3, type=  "beacon", bb_freq=0),
              slot_init(owner=2, len=0.1, offset=0.4, type="downlink", bb_freq=1),
              slot_init(owner=1, len=0.1, offset=0.5, type=  "uplink", bb_freq=4),
              ]
     },
    {"frame_len":FRAME_LEN_01,
     "rf_freq_ind":1,
     "slots":[slot_init(owner=0, len=0.1, offset=0.0, type=  "beacon", bb_freq=0),
              slot_init(owner=1, len=0.1, offset=0.1, type="downlink", bb_freq=1),
              slot_init(owner=2, len=0.1, offset=0.2, type=  "uplink", bb_freq=4),
              slot_init(owner=0, len=0.1, offset=0.3, type=  "beacon", bb_freq=0),
              slot_init(owner=2, len=0.1, offset=0.4, type="downlink", bb_freq=1),
              slot_init(owner=1, len=0.1, offset=0.5, type=  "uplink", bb_freq=4),
              ]
    },
    {"frame_len":FRAME_LEN_01,
     "rf_freq_ind":0,
     "slots":[slot_init(owner=0, len=0.1, offset=0.0, type=  "beacon", bb_freq=1),
              slot_init(owner=1, len=0.1, offset=0.1, type="downlink", bb_freq=0),
              slot_init(owner=2, len=0.1, offset=0.2, type=  "uplink", bb_freq=4),
              slot_init(owner=0, len=0.1, offset=0.3, type=  "beacon", bb_freq=1),
              slot_init(owner=2, len=0.1, offset=0.4, type="downlink", bb_freq=4),
              slot_init(owner=1, len=0.1, offset=0.5, type=  "uplink", bb_freq=0),
              ]
     },
    {"frame_len":FRAME_LEN_01,
     "rf_freq_ind":1,
     "slots":[slot_init(owner=0, len=0.1, offset=0.0, type=  "beacon", bb_freq=1),
              slot_init(owner=1, len=0.1, offset=0.1, type="downlink", bb_freq=0),
              slot_init(owner=2, len=0.1, offset=0.2, type=  "uplink", bb_freq=4),
              slot_init(owner=0, len=0.1, offset=0.3, type=  "beacon", bb_freq=1),
              slot_init(owner=2, len=0.1, offset=0.4, type="downlink", bb_freq=4),
              slot_init(owner=1, len=0.1, offset=0.5, type=  "uplink", bb_freq=0),
              ]
    },    
    ]

	


          
