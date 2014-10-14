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
 * Copyright 2004,2010,2011 Free Software Foundation, Inc.
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

#include <gr_io_signature.h>
#include <digital_ll_clock_recovery_mm_ff.h>
#include <gri_mmse_fir_interpolator.h>
#include <stdexcept>
#include <set>

#define DEBUG_CR_MM_FF	0		// must be defined as 0 or 1

// Public constructor

static pmt::pmt_t RATE_SYM = pmt::pmt_string_to_symbol("rx_rate");
static pmt::pmt_t TIME_SYM = pmt::pmt_string_to_symbol("rx_time");
static pmt::pmt_t ID_SYM = pmt::pmt_string_to_symbol("digital_ll_clock_recovery_mm");

digital_ll_clock_recovery_mm_ff_sptr
digital_ll_make_clock_recovery_mm_ff(float omega, float gain_omega,
				  float mu, float gain_mu,
				  float omega_relative_limit)
{
  return gnuradio::get_initial_sptr(new digital_ll_clock_recovery_mm_ff (omega,
								      gain_omega, 
								      mu,
								      gain_mu,
								      omega_relative_limit));
}

digital_ll_clock_recovery_mm_ff::digital_ll_clock_recovery_mm_ff (float omega, float gain_omega,
							    float mu, float gain_mu,
							    float omega_relative_limit)
  : gr_block ("clock_recovery_mm_ff",
	      gr_make_io_signature (1, 1, sizeof (float)),
	      gr_make_io_signature (1, 1, sizeof (float))),
    d_mu (mu), d_gain_omega(gain_omega), d_gain_mu(gain_mu),
    d_last_sample(0), d_interp(new gri_mmse_fir_interpolator()),
    d_logfile(0), d_omega_relative_limit(omega_relative_limit)
{
  if (omega <  1)
    throw std::out_of_range ("clock rate must be > 0");
  if (gain_mu <  0  || gain_omega < 0)
    throw std::out_of_range ("Gains must be non-negative");

  set_omega(omega);			// also sets min and max omega
  set_relative_rate (1.0 / omega);
  set_tag_propagation_policy(TPP_DONT);
  d_sample_offset = 0;

  d_timestamp_int_secs=0;
  d_timestamp_sample=0;
  d_timestamp_frac_secs=0;
  d_nom_samp_rate=1;

  if (DEBUG_CR_MM_FF)
    d_logfile = fopen("cr_mm_ff.dat", "wb");
}

digital_ll_clock_recovery_mm_ff::~digital_ll_clock_recovery_mm_ff ()
{
  delete d_interp;

  if (DEBUG_CR_MM_FF && d_logfile){
    fclose(d_logfile);
    d_logfile = 0;
  }
}

void
digital_ll_clock_recovery_mm_ff::forecast(int noutput_items, gr_vector_int &ninput_items_required)
{
  unsigned ninputs = ninput_items_required.size();
  for (unsigned i=0; i < ninputs; i++)
    ninput_items_required[i] =
      (int) ceil((noutput_items * d_omega) + d_interp->ntaps());
}

static inline float
slice(float x)
{
  return x < 0 ? -1.0F : 1.0F;
}




/*
 * This implements the Mueller and Müller (M&M) discrete-time error-tracking synchronizer.
 *
 * See "Digital Communication Receivers: Synchronization, Channel
 * Estimation and Signal Processing" by Heinrich Meyr, Marc Moeneclaey, & Stefan Fechtel.
 * ISBN 0-471-50275-8.
 */
int
digital_ll_clock_recovery_mm_ff::general_work (int noutput_items,
					    gr_vector_int &ninput_items,
					    gr_vector_const_void_star &input_items,
					    gr_vector_void_star &output_items)
{
  const float *in = (const float *) input_items[0];
  float *out = (float *) output_items[0];

  int 	ii = 0;				// input index
  int   final_ii=0;
  int  	oo = 0;				// output index
  int   final_oo=0;
  int   ni = ninput_items[0] - d_interp->ntaps(); // don't use more input than this
  float mm_val;

  std::vector<gr_tag_t> d_tags;
  std::vector<gr_tag_t>::iterator d_tags_itr;
  std::vector<uint64_t> offset_vec;
  std::vector<uint64_t> oo_vec, ii_vec;

  uint64_t abs_N, end_N;

  abs_N = nitems_read(0);
  end_N = abs_N + ni;

  // clear out old tags
  d_time_tags.clear();
  d_rate_tags.clear();
  d_other_tags.clear();

  //get the tags from input stream
  get_tags_in_range(d_tags, 0, abs_N, end_N);

//  for(int k=0; k< d_time_tags.size(); k++)
//  {
//	  if(!d_tags.empty() and (d_time_tags.back().offset != d_tags[0].offset))
//		  d_tags.push_back(d_time_tags.back());
//	  	  d_tags.push_back(d_rate_tags.back());
//	  	  d_time_tags.pop_back();
//	  	  d_rate_tags.pop_back();
//  }

  //fprintf(stderr,"%d tags found over %d samples\n", d_tags.size(),ni);
  //fprintf(stderr,"relative rate is %f\n", relative_rate());
  //fprintf(stderr,"sample offset is %f\n", d_sample_offset);

  //insert starting offset
  offset_vec.push_back(abs_N);
  oo_vec.push_back(0);
  ii_vec.push_back(0);

  // sort tags by offset
  std::sort(d_tags.begin(), d_tags.end(), gr_tag_t::offset_compare);

  d_sample_offset = nitems_written(0) -nitems_read(0)*relative_rate();

  int current_offset=0;
  d_tags_itr = d_tags.begin();

  while (oo < noutput_items && ii < ni ){

    // produce output sample
    out[oo] = d_interp->interpolate (&in[ii], d_mu);
    mm_val = slice(d_last_sample) * out[oo] - slice(out[oo]) * d_last_sample;
    d_last_sample = out[oo];

    d_omega = d_omega + d_gain_omega * mm_val;
    d_omega = d_omega_mid + gr_branchless_clip(d_omega-d_omega_mid, d_omega_relative_limit);   // make sure we don't walk away
    d_mu = d_mu + d_omega + d_gain_mu * mm_val;



	  while ((d_tags_itr != d_tags.end()) && ((ii + abs_N) >= d_tags_itr->offset))
	  {
		  current_offset = oo-ii*relative_rate();
		  gr_tag_t new_tag = *d_tags_itr;


		  //compute new corrected offset
		  new_tag.offset = new_tag.offset*relative_rate()+d_sample_offset+current_offset;

		  // store unique offsets and associated ii and oo index values for later
		  if(offset_vec.back() != d_tags_itr->offset)
		  {
			  offset_vec.push_back(d_tags_itr->offset);
			  oo_vec.push_back(oo);
			  ii_vec.push_back(ii);
		  }


		  // if this is a time update tag, store original tag for later processing
		  if(d_tags_itr->key == TIME_SYM)
		  {
//			  fprintf(stderr,"storing tag key %s and is tuple %d\n",
//					  pmt::pmt_symbol_to_string(d_tags_itr->key).c_str(),
//					  pmt::pmt_is_tuple(d_tags_itr->value));
			  d_time_tags.push_back(*d_tags_itr);
		  }
		  // if this is a rate update tag, store original tag for later processing
		  else if (d_tags_itr->key == RATE_SYM)
		  {
//			  fprintf(stderr,"storing tag key %s\n",
//			  					  pmt::pmt_symbol_to_string(d_tags_itr->key).c_str());
			  d_rate_tags.push_back(*d_tags_itr);
		  }
		  //otherwise pass it along to the generic tag list
		  else
		  {
			  d_other_tags.push_back(*d_tags_itr);
			  //add_item_tag(0,new_tag);
		  }

		  d_tags_itr++;
	  }

	final_ii = ii;
	final_oo = oo;

    ii += (int) floor(d_mu);
    d_mu = d_mu - floor(d_mu);
    oo++;

    if (DEBUG_CR_MM_FF && d_logfile){
      fwrite(&d_omega, sizeof(d_omega), 1, d_logfile);
    }
  }

  //insert ending offset
  offset_vec.push_back(abs_N+final_ii);
  oo_vec.push_back(final_oo);
  ii_vec.push_back(final_ii);

  if( final_oo > 0)
   {
	  // generate corrected rx_rate and rx_time tags
	  std::vector<uint64_t>::iterator offset_itr;
	  std::vector<gr_tag_t>::iterator time_itr;
	  std::vector<gr_tag_t>::iterator rate_itr;
	  std::vector<gr_tag_t>::iterator other_itr;

	  time_itr = d_time_tags.begin();
	  rate_itr = d_rate_tags.begin();
	  other_itr = d_other_tags.begin();

	  double inst_rel_rate;
	  uint64_t out_offset;
	  uint64_t out_timestamp_int_secs;
	  double out_timestamp_frac_secs;
	  double timestamp_frac_secs_delta;
	  double out_rate;

	  // for vector of length N, iterate only N-1 times
	  for(int i = 0; i<offset_vec.size()-1;i++)
	  {
		  while((time_itr != d_time_tags.end()) && (offset_vec[i] >= time_itr->offset))
		  {
			  d_timestamp_sample = time_itr->offset;
			  d_timestamp_int_secs = pmt::pmt_to_uint64(pmt::pmt_tuple_ref(time_itr->value,0));
			  d_timestamp_frac_secs = pmt::pmt_to_double(pmt::pmt_tuple_ref(time_itr->value,1));
			  time_itr++;
		  }
		  while((rate_itr != d_rate_tags.end()) && (offset_vec[i] >= rate_itr->offset))
		  {
			  if(pmt::pmt_is_tuple(rate_itr->value))
			  {
				  d_nom_samp_rate = pmt::pmt_to_double(pmt::pmt_tuple_ref(rate_itr->value,0));
			  }
			  else
			  {
				  d_nom_samp_rate = pmt::pmt_to_double(rate_itr->value);
			  }

			  rate_itr++;
		  }

		  // compute the instantaneous sample rate
		  if( (oo_vec[i+1] == oo_vec[i]) || ii_vec[i+1]==ii_vec[i])
		  {
			  // go to a safe rate
			  out_rate = d_nom_samp_rate;
		  }
		  else
		  {
			  inst_rel_rate = (oo_vec[i+1]-oo_vec[i])/double(ii_vec[i+1]-ii_vec[i]);
			  out_rate = d_nom_samp_rate*inst_rel_rate;
		  }
		  // get the current sample error
		  current_offset = oo_vec[i]-ii_vec[i]*relative_rate();

		  // compute the sample offset to store the current tag
		  out_offset = offset_vec[i]*relative_rate()+d_sample_offset+current_offset;

		  // get the time difference between the current sample and the last timestamp update
		  timestamp_frac_secs_delta = (ii_vec[i] + abs_N - d_timestamp_sample)/d_nom_samp_rate;

//		  fprintf(stderr,"input offset: %d, number items read: %lu, timestamp sample %ld, frac_delta: %f\n",
//				  ii_vec[i], abs_N, d_timestamp_sample, timestamp_frac_secs_delta);

		  out_timestamp_frac_secs = d_timestamp_frac_secs + timestamp_frac_secs_delta;

		  out_timestamp_int_secs = d_timestamp_int_secs + floor(out_timestamp_frac_secs);

		  out_timestamp_frac_secs = out_timestamp_frac_secs - floor(out_timestamp_frac_secs);

		  // process all other tags
		  int64_t tag_sample;
		  while((other_itr != d_other_tags.end()) && (offset_vec[i] >= other_itr->offset))
		  {
			  tag_sample = (other_itr->offset)*relative_rate()+d_sample_offset+current_offset;
			  other_itr->offset = tag_sample;
			  add_item_tag(0,*other_itr);
			  fprintf(stderr,"moving dig_chan tag to offset %lu\n",other_itr->offset);
			  other_itr++;
		  }

		  if(d_time_tags.size() > 0)
		  {

//			  fprintf(stderr,"offset_vec:%lu rel_rate:%f d_sample_offset:%f current_offset: %d\n", offset_vec[i], relative_rate(), d_sample_offset, current_offset);
//			  fprintf(stderr,"current input timestamp: %lu, %f at input sample %lu, \n", d_timestamp_int_secs, d_timestamp_frac_secs, d_timestamp_sample);
//			  fprintf(stderr,"output timestamp: %lu, %f at output sample %lu\n", out_timestamp_int_secs, out_timestamp_frac_secs, out_offset);
		  }

//		  fprintf(stderr,"out timestamp: %lu, %f\n", out_timestamp_int_secs, out_timestamp_frac_secs);
		  //build the rx_rate and rx_time tags
		  const pmt::pmt_t time_val = pmt::pmt_make_tuple(
		                      pmt::pmt_from_uint64(out_timestamp_int_secs),
		                      pmt::pmt_from_double(out_timestamp_frac_secs)
		                  );
		  const pmt::pmt_t rate_val = pmt::pmt_from_double(out_rate);

		  add_item_tag(0, out_offset, TIME_SYM, time_val, ID_SYM);
		  add_item_tag(0, out_offset, RATE_SYM, rate_val, ID_SYM);

	  }


//	  fprintf(stderr,"n inputs: %lu  n outputs: %lu relative rate is %f, sample offset is %f\n", final_ii, final_oo, relative_rate(), d_sample_offset);
	  d_sample_offset = (final_oo+nitems_written(0)) -(final_ii+nitems_read(0))*relative_rate();
  }
//    fprintf(stderr,"cumulative sample offset is %f\n", d_sample_offset);
  //fprintf(stderr,"unique offsets: %lu\n", offset_list.size());


  // store off any unused time tags
  while (d_tags_itr != d_tags.end())
  {
	  if(d_tags_itr->key == TIME_SYM)
	  {
		  d_timestamp_sample = d_tags_itr->offset;
		  d_timestamp_int_secs = pmt::pmt_to_uint64(pmt::pmt_tuple_ref(d_tags_itr->value,0));
		  d_timestamp_frac_secs = pmt::pmt_to_double(pmt::pmt_tuple_ref(d_tags_itr->value,1));

	  }
	  else if(d_tags_itr->key == RATE_SYM)
	  {
		  d_nom_samp_rate = pmt::pmt_to_double(d_tags_itr->value);
	  }
	  d_tags_itr++;
  }

  consume_each (ii);

  return oo;
}
