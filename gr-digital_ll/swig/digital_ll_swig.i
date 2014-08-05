/* -*- c++ -*- */
/*
 * This file is part of ExtRaSy
 *
 * Copyright (C) 2013-2014 Massachusetts Institute of Technology
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
 
#define DIGITAL_LL_API

%include "gnuradio.i"			// the common stuff

//load generated python docstrings
//%include "digital_ll_swig_doc.i"

%{
//#include "digital_ll_peak_detector_robust_fb.h"
//#include "digital_ll_digital_ll_ofdm_frame_acquisition.h"
//#include "digital_ll_ofdm_frame_sink.h"
#include "digital_ll_downcounter.h"
//#include "digital_ll_peak_detector_simple.h"
#include "digital_ll_probe_avg_mag_sqrd_c.h"
//#include "digital_ll_sample_counter.h"
#include "digital_ll_tag_logger.h"
#include "digital_ll_framer_sink_1.h"
#include "digital_ll_slot_selector.h"
#include "digital_ll_timestamp.h"
#include "digital_ll_selector.h"
#include "digital_ll_modulator.h"
//#include "digital_ll_synchronized_recorder.h"
#include "digital_ll_time_tag_shifter.h"
#include "digital_ll_uhd_time_spec_t_builder.h"
#include "digital_ll_clock_recovery_mm_ff.h"
#include "digital_ll_pfb_channelizer_ccf.h"
%}

%include "digital_ll_uhd_time_spec_t_builder.h"


//GR_SWIG_BLOCK_MAGIC(digital_ll,peak_detector_robust_fb);
//%include "digital_ll_peak_detector_robust_fb.h"

#if SWIGGUILE
%scheme %{
(load-extension-global "libguile-gnuradio-digital_ll_swig" "scm_init_gnuradio_digital_ll_swig_module")
%}

%goops %{
(use-modules (gnuradio gnuradio_core_runtime))
%}
#endif

//GR_SWIG_BLOCK_MAGIC(digital_ll,digital_ll_ofdm_frame_acquisition);
//%include "digital_ll_digital_ll_ofdm_frame_acquisition.h"

//GR_SWIG_BLOCK_MAGIC(digital_ll,ofdm_frame_sink);
//%include "digital_ll_ofdm_frame_sink.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,downcounter);
%include "digital_ll_downcounter.h"

//GR_SWIG_BLOCK_MAGIC(digital_ll,peak_detector_simple);
//%include "digital_ll_peak_detector_simple.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,probe_avg_mag_sqrd_c);
%include "digital_ll_probe_avg_mag_sqrd_c.h"

//GR_SWIG_BLOCK_MAGIC(digital_ll,sample_counter);
//%include "digital_ll_sample_counter.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,tag_logger);
%include "digital_ll_tag_logger.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,framer_sink_1);
%include "digital_ll_framer_sink_1.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,slot_selector);
%include "digital_ll_slot_selector.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,selector);
%include "digital_ll_selector.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,modulator);
%include "digital_ll_modulator.h"

//GR_SWIG_BLOCK_MAGIC(digital_ll,synchronized_recorder);
//%include "digital_ll_synchronized_recorder.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,time_tag_shifter);
%include "digital_ll_time_tag_shifter.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,clock_recovery_mm_ff);
%include "digital_ll_clock_recovery_mm_ff.h"

GR_SWIG_BLOCK_MAGIC(digital_ll,pfb_channelizer_ccf);
%include "digital_ll_pfb_channelizer_ccf.h"