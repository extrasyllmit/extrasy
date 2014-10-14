/* -*- c++ -*- */
/*
 * This file is part of ExtRaSy
 *
 * Copyright (C) 2013-2014 Massachusetts Institute of Technology
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *
 * This file incorporates work covered by the following copyright:
 *
 *
 * Copyright 2005,2006 Free Software Foundation, Inc.
 *
 * This file is part of GNU Radio
 *
 * GNU Radio is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * GNU Radio is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GNU Radio; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */
#ifndef INCLUDED_digital_ll_PROBE_AVG_MAG_SQRD_C_H
#define INCLUDED_digital_ll_PROBE_AVG_MAG_SQRD_C_H

#include <gr_core_api.h>
#include <gr_sync_block.h>
#include <gr_single_pole_iir.h>
#include <cmath>

class digital_ll_probe_avg_mag_sqrd_c;
typedef boost::shared_ptr<digital_ll_probe_avg_mag_sqrd_c> digital_ll_probe_avg_mag_sqrd_c_sptr;

GR_CORE_API digital_ll_probe_avg_mag_sqrd_c_sptr
digital_ll_make_probe_avg_mag_sqrd_c (double threshold_db, double alpha = 0.0001, int use_calibration=0, int n_iter = 5, int iter_len = 1e6);

/*!
 * \brief compute avg magnitude squared.
 * \ingroup sink_blk
 *
 * input: gr_complex
 *
 * Compute a running average of the magnitude squared of the the input.
 * The level and indication as to whether the level exceeds threshold
 * can be retrieved with the level and unmuted accessors.
 */
class GR_CORE_API digital_ll_probe_avg_mag_sqrd_c : public gr_sync_block
{
  double					d_threshold;
  gr_single_pole_iir<double,double,double>	d_iir;
  bool						d_unmuted;
  double					d_level;

  // Test Statistic Fields
  int test_iter;
  int inner_iter;
  int use_calibration;
  int n_iter;
  int iter_len;
  float *test_max;
  int begin_calibration;

  friend GR_CORE_API digital_ll_probe_avg_mag_sqrd_c_sptr
  digital_ll_make_probe_avg_mag_sqrd_c (double threshold_db, double alpha, int use_calibration, int n_iter, int iter_len);

  digital_ll_probe_avg_mag_sqrd_c (double threshold_db, double alpha, int use_calibration, int n_iter, int iter_len);

public:
  ~digital_ll_probe_avg_mag_sqrd_c ();

  int work (int noutput_items,
	    gr_vector_const_void_star &input_items,
	    gr_vector_void_star &output_items);

  // ACCESSORS
  bool unmuted () const { return d_unmuted; }
  double level () const { return d_level; }
  double get_threshold() const { return d_threshold; }

  void signal_begin_calibration();
  int check_finished_calibration() const;

  double threshold() const;

  // SETTERS
  void set_alpha (double alpha);
  void set_threshold (double decibels);
};

#endif /* INCLUDED_GR_PROBE_AVG_MAG_SQRD_C_H */
