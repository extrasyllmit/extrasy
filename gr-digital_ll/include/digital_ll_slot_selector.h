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
#ifndef INCLUDED_DIGITAL_LL_SLOT_SELECTOR_H
#define INCLUDED_DIGITAL_LL_SLOT_SELECTOR_H

#include <digital_ll_api.h>
#include <gr_block.h>
#define BOOST_ICL_USE_STATIC_BOUNDED_INTERVALS
#include <boost/icl/interval_set.hpp>
#include <boost/icl/separate_interval_set.hpp>
#include <boost/icl/continuous_interval.hpp>
#include <boost/tuple/tuple.hpp>
#include <gruel/thread.h>
#include "digital_ll_timestamp.h"
#include "digital_ll_context_tag_manager.h"
#include <deque>
#include <vector>
#include <map>
#include <string>





class digital_ll_slot_selector;
typedef boost::shared_ptr<digital_ll_slot_selector> digital_ll_slot_selector_sptr;

typedef boost::icl::interval_set<double> ts_interval_set;
typedef boost::icl::separate_interval_set<double> ts_separate_interval_set;
DIGITAL_LL_API digital_ll_slot_selector_sptr digital_ll_make_slot_selector
  (size_t item_size, double frame_len,
			std::vector<double> slot_lens, std::vector<double> slot_offsets,
			uint64_t frame_t0_int_s, double frame_t0_frac_s,
			uint64_t stream_t0_int_s, double stream_t0_frac_s, double fs);

struct Schedule{
	double frame_len;
	std::vector<double> slot_lens;
	std::vector<double> slot_offsets;
	digital_ll_timestamp frame_t0;
};






/*!
 * \brief pass samples to output according to some schedule
 */
class DIGITAL_LL_API digital_ll_slot_selector : public gr_block
{
  typedef boost::tuple<uint64_t, digital_ll_timestamp, double> tag_tuple;
  typedef std::vector<tag_tuple>::iterator tag_tuple_it;

  friend DIGITAL_LL_API digital_ll_slot_selector_sptr
  digital_ll_make_slot_selector (size_t item_size, double frame_len,
			std::vector<double> slot_lens, std::vector<double> slot_offsets,
			uint64_t frame_t0_int_s, double frame_t0_frac_s,
			uint64_t stream_t0_int_s, double stream_t0_frac_s, double fs);

  static DIGITAL_LL_API bool compare_tuple_ts(const boost::tuples::tuple<uint64_t, digital_ll_timestamp, double> & t1,
  	  		const boost::tuples::tuple<uint64_t, digital_ll_timestamp, double> & t2);

  static DIGITAL_LL_API bool compare_tuple_offset(const boost::tuples::tuple<uint64_t, digital_ll_timestamp, double> & t1,
  	  		const boost::tuples::tuple<uint64_t, digital_ll_timestamp, double> & t2);


  private:

      digital_ll_context_tag_manager d_tag_manager;

      // time that all other times in a given iteration are referenced to
	  digital_ll_timestamp d_timestamp_gps;
	  int64_t d_timestamp_sample;
	  double d_samp_rate;

	  // store the last time we updated a time tag
	  digital_ll_timestamp d_last_time_tag_update_gps;

	  double d_frame_len;
	  std::vector<double> d_slot_lens;
	  std::vector<double> d_slot_offsets;
	  std::vector<int> d_slot_nums;
	  digital_ll_timestamp d_frame_t0_gps;


	  int   d_itemsize;

	  std::deque<gr_tag_t> d_time_tags;
	  std::deque<gr_tag_t> d_rate_tags;
	  std::deque<gr_tag_t> d_other_tags;
	  std::vector<tag_tuple> d_tag_tuples;

	  std::deque<Schedule> d_next_schedule;


	  // the mutex protects access to the next schedule
	  gruel::mutex				d_mutex;

	  void sort_tags(std::vector<gr_tag_t> tags);

	  ts_interval_set compute_current_blocks(gr_vector_int &ninput_items);

	  ts_separate_interval_set compute_slots_of_interest(
			  ts_interval_set current_blocks);

	  ts_separate_interval_set compute_output_slots(
			  ts_interval_set current_blocks,
			  ts_separate_interval_set slots_of_interest);

	  int limit_output_samples(
	                            int noutput_items,
	                            int ninput_items,
	                            ts_interval_set current_blocks,
	                            ts_separate_interval_set & output_slots);


	  int produce_outputs(
			  ts_interval_set current_blocks,
			  ts_separate_interval_set slots_of_interest,
			  ts_separate_interval_set output_slots,
			  int noutput_items,
			  gr_vector_int &ninput_items,
			  gr_vector_const_void_star &input_items,
			  gr_vector_void_star &output_items);




 protected:
  digital_ll_slot_selector (size_t item_size, double frame_len,
		  std::vector<double> slot_lens, std::vector<double> slot_offsets,
		  uint64_t frame_t0_int_s, double frame_t0_frac_s,
		  uint64_t stream_t0_int_s, double stream_t0_frac_s, double fs);
  void forecast (int noutput_items, gr_vector_int &ninput_items_required);

  gruel::mutex *mutex() { return &d_mutex; }

 public:
  void set_schedule(double frame_len, std::vector<double> slot_lens,
		  std::vector<double> slot_offsets,
		  uint64_t frame_t0_int_s, double frame_t0_frac_s);

  int general_work (int noutput_items,
            gr_vector_int &ninput_items,
		    gr_vector_const_void_star &input_items,
		    gr_vector_void_star &output_items);



};

#endif /* INCLUDED_DIGITAL_LL_SLOT_SELECTOR_H */
