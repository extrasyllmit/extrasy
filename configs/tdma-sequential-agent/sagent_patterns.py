'''
Pattern File for ExtRaSy example sagents
'''
from collections import namedtuple

PatternTuple = namedtuple("PatternTuple", 'owner len offset type bb_freq')

slot_init = PatternTuple

FRAME_LEN_N0 = 0.22000000
SET_N0 = [
    # pattern 0
    {"frame_len":FRAME_LEN_N0,
     "rf_freq_ind":0,
     "slots":[slot_init(owner=0, len=0.04000000, offset=0.00000000, type=  "beacon", bb_freq=6),
              slot_init(owner=1, len=0.04000000, offset=0.04000000, type="downlink", bb_freq=6),
              slot_init(owner=2, len=0.04000000, offset=0.08000000, type="downlink", bb_freq=7),
              slot_init(owner=1, len=0.05000000, offset=0.12000000, type=  "uplink", bb_freq=0),
              slot_init(owner=2, len=0.05000000, offset=0.17000000, type=  "uplink", bb_freq=1),
              ]
     },
    # pattern 1
    {"frame_len":FRAME_LEN_N0,
     "rf_freq_ind":0,
     "slots":[slot_init(owner=0, len=0.04000000, offset=0.00000000, type=  "beacon", bb_freq=2),
              slot_init(owner=1, len=0.04000000, offset=0.04000000, type="downlink", bb_freq=6),
              slot_init(owner=2, len=0.04000000, offset=0.08000000, type="downlink", bb_freq=2),
              slot_init(owner=1, len=0.05000000, offset=0.12000000, type=  "uplink", bb_freq=6),
              slot_init(owner=2, len=0.05000000, offset=0.17000000, type=  "uplink", bb_freq=2),
              ]
     },
    # pattern 2
    {"frame_len":FRAME_LEN_N0,
     "rf_freq_ind":0,
     "slots":[slot_init(owner=0, len=0.04000000, offset=0.00000000, type=  "beacon", bb_freq=0),
              slot_init(owner=1, len=0.04000000, offset=0.04000000, type="downlink", bb_freq=0),
              slot_init(owner=2, len=0.04000000, offset=0.08000000, type="downlink", bb_freq=0),
              slot_init(owner=1, len=0.05000000, offset=0.12000000, type=  "uplink", bb_freq=0),
              slot_init(owner=2, len=0.05000000, offset=0.17000000, type=  "uplink", bb_freq=0),
              ]
     },
	 ]