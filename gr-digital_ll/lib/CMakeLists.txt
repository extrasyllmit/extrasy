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
# Setup library

########################################################################
include(GrPlatform) #define LIB_SUFFIX

find_package(UHD)

add_library(gnuradio-digital_ll SHARED 
#			digital_ll_peak_detector_robust_fb.cc 
#			digital_ll_digital_ll_ofdm_frame_acquisition.cc 
#			digital_ll_ofdm_frame_sink.cc 
			digital_ll_downcounter.cc 
#			digital_ll_peak_detector_simple.cc 
			digital_ll_probe_avg_mag_sqrd_c.cc 
#			digital_ll_sample_counter.cc 
			digital_ll_tag_logger.cc
			digital_ll_framer_sink_1.cc
			digital_ll_slot_selector.cc
			digital_ll_timestamp.cc
			digital_ll_selector.cc 
           digital_ll_modulator.cc 
#			digital_ll_synchronized_recorder.cc 
			digital_ll_time_tag_shifter.cc
			digital_ll_uhd_time_spec_t_builder.cc
			digital_ll_context_tag_manager.cc
			digital_ll_clock_recovery_mm_ff.cc
			digital_ll_pfb_channelizer_ccf.cc
)
target_link_libraries(gnuradio-digital_ll ${Boost_LIBRARIES} ${GRUEL_LIBRARIES} ${GNURADIO_CORE_LIBRARIES} ${UHD_LIBRARIES})
set_target_properties(gnuradio-digital_ll PROPERTIES DEFINE_SYMBOL "gnuradio_digital_ll_EXPORTS")

########################################################################
# Install built library files
########################################################################
install(TARGETS gnuradio-digital_ll
    LIBRARY DESTINATION lib${LIB_SUFFIX} # .so/.dylib file
    ARCHIVE DESTINATION lib${LIB_SUFFIX} # .lib file
    RUNTIME DESTINATION bin              # .dll file
)

########################################################################
# Build and register unit test
########################################################################
find_package(Boost COMPONENTS unit_test_framework)

include(GrTest)
set(GR_TEST_TARGET_DEPS gnuradio-digital_ll)
#turn each test cpp file into an executable with an int main() function
add_definitions(-DBOOST_TEST_DYN_LINK -DBOOST_TEST_MAIN)

#add_executable(qa_digital_ll_peak_detector_robust_fb qa_digital_ll_peak_detector_robust_fb.cc)
#target_link_libraries(qa_digital_ll_peak_detector_robust_fb gnuradio-digital_ll ${Boost_LIBRARIES})
#GR_ADD_TEST(qa_digital_ll_peak_detector_robust_fb qa_digital_ll_peak_detector_robust_fb)
