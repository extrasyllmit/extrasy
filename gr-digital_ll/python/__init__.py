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
# The presence of this file turns this directory into a Python package

'''
This is the GNU Radio DIGITAL_LL module. Place your Python package
description here (python/__init__.py).
'''

# ----------------------------------------------------------------
# Temporary workaround for ticket:181 (swig+python problem)
import sys
_RTLD_GLOBAL = 0
try:
    from dl import RTLD_GLOBAL as _RTLD_GLOBAL
except ImportError:
    try:
        from DLFCN import RTLD_GLOBAL as _RTLD_GLOBAL
    except ImportError:
        pass
    
if _RTLD_GLOBAL != 0:
    _dlopenflags = sys.getdlopenflags()
    sys.setdlopenflags(_dlopenflags|_RTLD_GLOBAL)
# ----------------------------------------------------------------


# import swig generated symbols into the digital_ll namespace
from digital_ll_swig import *

# import any pure python here
from uhd_interface import *
#from ofdm import *
#from ofdm_receiver import *
#from ofdm_sync_pn import *
#from pkt import *
import pkt2
#from payload_utils import *
#from generic_mod_demod import *
#from packet_utils import *
#from sync_watcher import *
#from transmit_path_narrowband import *
from receive_path_narrowband import *
from receive_path_gmsk import *
#from transmit_path_ofdm import *
#from receive_path_ofdm import *
from lincolnlog import *
#from bpsk import *
#from psk import *
#from qam import *
#from qpsk import *
from gmsk import *
from modulation_utils import *
#from heart_beat_tagger import *
from time_spec import *
from FrameSchedule import *
from beacon_utils import *
from packet_framer import *
from scheduled_mux import *
import pmt_to_python # injects into pmt 
from pmt_rpc import pmt_rpc
import packet_utils2
from tdma_logger import *
#from burst_gate import *
from eob_shifter import *
from version import __version__
from command_queue_manager import *
from power_control import *
from tune_manager import *
from SortedCollection import *
from pfb_channelizer import *

# ----------------------------------------------------------------
# Tail of workaround
if _RTLD_GLOBAL != 0:
    sys.setdlopenflags(_dlopenflags)      # Restore original flags
# ----------------------------------------------------------------
