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
# Install public header files
########################################################################
install(FILES
    digital_ll_api.h
#    digital_ll_peak_detector_robust_fb.h
#    digital_ll_digital_ll_ofdm_frame_acquisition.h
#    digital_ll_ofdm_frame_sink.h
    digital_ll_downcounter.h
#    digital_ll_peak_detector_simple.h
#    digital_ll_sample_counter.h
    digital_ll_probe_avg_mag_sqrd_c.h 
    digital_ll_tag_logger.h 
    digital_ll_framer_sink_1.h
    digital_ll_slot_selector.h 
    digital_ll_timestamp.h
	digital_ll_selector.h
    digital_ll_modulator.h
#    digital_ll_synchronized_recorder.h
    digital_ll_time_tag_shifter.h
    digital_ll_uhd_time_spec_t_builder.h
    digital_ll_context_tag_manager.h
    digital_ll_clock_recovery_mm_ff.h
    digital_ll_pfb_channelizer_ccf.h
    DESTINATION include/digital_ll
    )

