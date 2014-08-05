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

#ifndef INCLUDED_DIGITAL_LL_MODULATOR_H
#define INCLUDED_DIGITAL_LL_MODULATOR_H

#include <digital_ll_api.h>
#include <gr_sync_block.h>
#define BOOST_ICL_USE_STATIC_BOUNDED_INTERVALS
#include <boost/icl/interval_set.hpp>
#include <boost/icl/separate_interval_set.hpp>
#include <boost/icl/continuous_interval.hpp>
#include <boost/tuple/tuple.hpp>
#include <deque>
#include <vector>
#include <iostream>
#include <math.h>
#include <assert.h>
#include <bitset>

typedef boost::tuple<uint64_t, uint64_t> channel_tuple; // (offset, new_channel)
typedef boost::tuple<uint64_t, pmt::pmt_t> scaling_tuple; // (offset, pmt object of vector of float)

class digital_ll_modulator;
typedef boost::shared_ptr<digital_ll_modulator> digital_ll_modulator_sptr;

DIGITAL_LL_API digital_ll_modulator_sptr digital_ll_make_modulator (int num_chan, int current_chan);

/*!
 * Tx Modulator with Synchronization
 *
 */
class DIGITAL_LL_API digital_ll_modulator : public gr_sync_block
{
	friend DIGITAL_LL_API digital_ll_modulator_sptr digital_ll_make_modulator (int num_chan, int current_chan);

	digital_ll_modulator (int num_chan, int current_chan);
	
	void get_channel_tags( int noutput_items ); // Get the channel switching tags
	
    int d_current_chan;                         // The current channel we are on
    int d_num_chan;                             // The number of channels
    

    
    std::vector<channel_tuple> d_channel_tags;  // channel tags
    std::vector<uint64_t> d_sob_offsets;
    std::deque<gr_tag_t> d_tags;                // Intial holding deque for tags

 public:
	~digital_ll_modulator ();

    void switch_channels( int new_chan ); // Public function to set the new channel

	int work (int noutput_items,
		gr_vector_const_void_star &input_items,
		gr_vector_void_star &output_items);
};

#endif /* INCLUDED_DIGITAL_LL_MODULATOR_H */

