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
 */

#ifndef INCLUDED_DIGITAL_LL_SELECTOR_H
#define INCLUDED_DIGITAL_LL_SELECTOR_H

#include <digital_ll_api.h>
#include <gr_sync_block.h>
#define BOOST_ICL_USE_STATIC_BOUNDED_INTERVALS
#include <boost/icl/interval_set.hpp>
#include <boost/icl/separate_interval_set.hpp>
#include <boost/icl/continuous_interval.hpp>
#include <boost/tuple/tuple.hpp>
#include <gruel/thread.h>
#include <deque>
#include <vector>
#include <stdint.h>
#include <math.h>
#include <iostream>
#include <assert.h>

class digital_ll_selector;
typedef boost::shared_ptr<digital_ll_selector> digital_ll_selector_sptr;

typedef boost::tuple<uint64_t, uint64_t, double, double> tag_tuple; //(offset, int_time, frac_time, rate)
typedef boost::tuple<uint64_t, double> time_tuple;                  //(int_time, frac_time)
typedef boost::tuple< time_tuple, double, std::vector<double>, std::vector<int> > frame_tuple;  //(frame_time, frame_length, slot_times, slot_channels)
typedef boost::tuple< time_tuple, int > slot_tuple; // (slot time, int channel)

DIGITAL_LL_API digital_ll_selector_sptr digital_ll_make_selector (int numchans, int input_index, int output_index);

/*!
 * digital_ll_selector
 * The selector is a sync block that chooses from one of its N inputs to send
 * to output. It has the ability to schedule a GPS time when switch should occur.
 *
 */
class DIGITAL_LL_API digital_ll_selector : public gr_sync_block
{

	friend DIGITAL_LL_API digital_ll_selector_sptr digital_ll_make_selector (int numchans, int input_index, int output_index);

	digital_ll_selector (int numchans, int input_index, int output_index);
	
 private:
 
    // Number of tags processed
    int d_ntags_proc;
 
    // The input and output index to use
	int d_input_index;
	int d_output_index;
	int d_num_chans;
	//int last_print;
	
	// The tag handling functionality
	std::deque<gr_tag_t> d_time_tags;
	std::deque<gr_tag_t> d_rate_tags;
	uint64_t get_tags( int noutput_items ); // returns number of read items
	
	// Fuctions to store the data in the tags
	std::vector<tag_tuple> d_tag_tuples;
	int find_most_recent_tag( uint64_t offset );
	time_tuple increment_time_tuple( time_tuple gps_time, int64_t increment, double rate );
	
	// Variables to save the UHD data between calls to work function
	int64_t d_offset_save;
	int64_t d_time_full_s_save;
	double  d_time_frac_s_save;
	double  d_rate_save;
    void save_last();
    
    // Private functions for handling rx schedules and beacons
    std::vector<frame_tuple> d_frame_schedules;
    std::deque<slot_tuple> d_frame_schedule;
    int d_beacon_channel;
    time_tuple advance_time_tuple( time_tuple gps_time, double seconds );
    int compare_time_tuples( time_tuple tuple1, time_tuple tuple2 );
    int get_next_schedule( time_tuple current_gps_time );

 public:
	~digital_ll_selector ();

    // Public functions for handdling rx schedules and beacons
    void set_schedule(int int_s, double frac_s, double frame_length, const std::vector<double> slot_times, const std::vector<int> slot_chan_nums); 
    void set_beacon_channel( int beacon_channel );
    void return_to_beacon_channel( );

    void set_input_index( int input_index );

	int work (int noutput_items,
		gr_vector_const_void_star &input_items,
		gr_vector_void_star &output_items);
};

#endif /* INCLUDED_DIGITAL_LL_SELECTOR_H */

