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
# Copyright 2011 Free Software Foundation, Inc.
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

########################################################################
# Include python install macros
########################################################################
include(GrPython)
if(NOT PYTHONINTERP_FOUND)
    return()
endif()

INCLUDE(LL_Version)   #setup version num

set_source_files_properties( ${CMAKE_BINARY_DIR}/python/version.py 
	PROPERTIES GENERATED true)

########################################################################
# Add version info
########################################################################
CONFIGURE_FILE(
    ${CMAKE_CURRENT_SOURCE_DIR}/version.py
    ${CMAKE_BINARY_DIR}/python/version.py
@ONLY)

########################################################################
# Install python sources
########################################################################
GR_PYTHON_INSTALL(
    FILES
    __init__.py
    channelizer.py
#    ofdm.py
#    ofdm_receiver.py
#    ofdm_sync_pn.py
#    ofdm_packet_util.py
#    payload_utils.py
#    pkt.py
    pkt2.py
#    packet_utils.py
#    generic_mod_demod.py
#    sync_watcher.py
#    transmit_path_narrowband.py
    receive_path_narrowband.py
    receive_path_gmsk.py
#    transmit_path_ofdm.py
#    receive_path_ofdm.py
    lincolnlog.py
#    bpsk.py
#    psk.py
#    qam.py
#    qpsk.py
    gmsk.py
    modulation_utils.py
#    heart_beat_tagger.py
    time_spec.py
    beacon_utils.py
    packet_framer.py
    scheduled_mux.py
    pmt_to_python.py
    pmt_rpc.py
    packet_utils2.py
    tdma_logger.py
#    burst_gate.py
    eob_shifter.py
    FrameSchedule.py
    command_queue_manager.py
    power_control.py
    tune_manager.py
    SortedCollection.py
	uhd_interface.py
	pfb_channelizer.py
    ${CMAKE_BINARY_DIR}/python/version.py
    DESTINATION ${GR_PYTHON_DIR}/digital_ll
)

########################################################################
# Handle the unit tests
########################################################################
include(GrTest)

set(GR_TEST_TARGET_DEPS gnuradio-digital_ll)
set(GR_TEST_PYTHON_DIRS ${CMAKE_BINARY_DIR}/swig)
GR_ADD_TEST(qa_peak_detector_robust_fb ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_digital_ll_peak_detector_robust_fb.py)
GR_ADD_TEST(qa_slot_selector ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_digital_ll_slot_selector.py)
