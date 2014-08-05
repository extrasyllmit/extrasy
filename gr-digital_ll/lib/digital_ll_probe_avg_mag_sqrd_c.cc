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
 *
 *
 * This file incorporates work covered by the following copyright:
 *
 *
 * Copyright 2005,2010 Free Software Foundation, Inc.
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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
#include <digital_ll_probe_avg_mag_sqrd_c.h>
#include <gr_io_signature.h>
#include <cmath>

#include <cstdio>
#include <stdexcept>
#include <iostream>
#include <string.h>

#include <algorithm>

# define VERBOSE 0
# define DEBUG 0

digital_ll_probe_avg_mag_sqrd_c_sptr
digital_ll_make_probe_avg_mag_sqrd_c(double threshold_db, double alpha, int use_calibration, int n_iter, int iter_len)
{
  return gnuradio::get_initial_sptr(new digital_ll_probe_avg_mag_sqrd_c(threshold_db, alpha, use_calibration, n_iter, iter_len));
}

digital_ll_probe_avg_mag_sqrd_c::digital_ll_probe_avg_mag_sqrd_c (double threshold_db, double alpha, int use_calibration, int n_iter, int iter_len)
  : gr_sync_block ("probe_avg_mag_sqrd_c",
		   gr_make_io_signature(1, 1, sizeof(gr_complex)),
		   gr_make_io_signature(0, 0, 0)),
    d_iir(alpha), d_unmuted(false), d_level(0)
{
  set_threshold (threshold_db);
  
  // Setup the parameters for generating the test statistic
  this->test_iter = 0;
  this->inner_iter = 0;
  this->use_calibration = use_calibration;
  this->n_iter = n_iter;
  this->iter_len = iter_len;
  this->test_max = new float[n_iter];
  
  this->begin_calibration = 0;
}

digital_ll_probe_avg_mag_sqrd_c::~digital_ll_probe_avg_mag_sqrd_c()
{
    delete [] test_max;
}

int
digital_ll_probe_avg_mag_sqrd_c::work(int noutput_items,
			   gr_vector_const_void_star &input_items,
			   gr_vector_void_star &output_items)
{
  const gr_complex *in = (const gr_complex *) input_items[0];


  for (int i = 0; i < noutput_items; i++){
    double mag_sqrd = in[i].real()*in[i].real() + in[i].imag()*in[i].imag();
    d_iir.filter(mag_sqrd);	// computed for side effect: prev_output()
    
    
    //Gather the test statistics
    if (use_calibration && begin_calibration){
    
        // See if this is a new max for this iteration
        if ((float) d_iir.prev_output() >= test_max[test_iter])
            test_max[test_iter] = (float) d_iir.prev_output();
        
        inner_iter++;
        
        // See if we need to move on to the next test iteration
        if ( inner_iter >= iter_len ){
            test_iter++;
            inner_iter = 0;
        }
        
        // If we've moved past all of the iterations we need to find the
        // median of all the max's.  That will become out d_threshold
        if ( test_iter >= n_iter ){
            std::sort(test_max, test_max + n_iter);
            d_threshold = test_max[(int)n_iter/2];
            begin_calibration = 0;
            
            //For Debugging
            if( DEBUG ){
                for( int i = 0; i < n_iter; i++ )
                    std::cout << test_max[i] << "\t";
                std::cout << "\n";
                
                std::cout << "The threshold is now " << d_threshold << "\n";
            }
            
            
        }
        
    }
    
    // Debugging stuff
    if( VERBOSE ){
      if( test_iter >= n_iter ){
        fprintf(stderr, "output: %+.20f \n", d_iir.prev_output());
        fprintf(stderr, "thresh: %i \n", d_iir.prev_output() >= d_threshold);
      }
    }
    
  }

  d_unmuted = d_iir.prev_output() >= d_threshold;
  d_level = d_iir.prev_output();
  return noutput_items;
}

double
digital_ll_probe_avg_mag_sqrd_c::threshold() const
{
  return 10 * std::log10(d_threshold);
}

void
digital_ll_probe_avg_mag_sqrd_c::signal_begin_calibration( )
{
  if( use_calibration ){
    begin_calibration = 1;
  }
}

int
digital_ll_probe_avg_mag_sqrd_c::check_finished_calibration() const
{
  return !begin_calibration;
}

void
digital_ll_probe_avg_mag_sqrd_c::set_threshold(double decibels)
{
  // convert to absolute threshold (mag squared)
  d_threshold = std::pow(10.0, decibels/10);
}

void
digital_ll_probe_avg_mag_sqrd_c::set_alpha(double alpha)
{
  d_iir.set_taps(alpha);
}


