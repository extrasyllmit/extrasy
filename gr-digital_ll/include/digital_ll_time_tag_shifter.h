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

#ifndef INCLUDED_DIGITAL_LL_TIME_TAG_SHIFTER_H
#define INCLUDED_DIGITAL_LL_TIME_TAG_SHIFTER_H

#include <digital_ll_api.h>
#include <gr_sync_block.h>
#include <deque>
#include <boost/tuple/tuple.hpp>
#include <boost/bind.hpp>
#include <gruel/thread.h>
#include <stdint.h>

class digital_ll_time_tag_shifter;
typedef boost::shared_ptr<digital_ll_time_tag_shifter> digital_ll_time_tag_shifter_sptr;

DIGITAL_LL_API digital_ll_time_tag_shifter_sptr digital_ll_make_time_tag_shifter (int is_receive_side, int input_size = sizeof (gr_complex));

// Type definitions
namespace tag_shifter
{
    typedef boost::tuple<uint64_t, double> time_tuple;    //(intger gps time, fractional gps time)
    typedef boost::tuple<uint64_t, time_tuple, double, pmt::pmt_t, pmt::pmt_t> tag_tuple;    //(offset, gps time, rate, source id, freq)
}

/*!
 * \brief <+description+>
 *
 */
class DIGITAL_LL_API digital_ll_time_tag_shifter : public gr_block
{
	friend DIGITAL_LL_API digital_ll_time_tag_shifter_sptr digital_ll_make_time_tag_shifter (int is_receive_side, int input_size);

	digital_ll_time_tag_shifter (int is_receive_side, int input_size);
 
 private:
 
    // *** Member Functions ***
    uint64_t    get_tags( int noutput_items );
    int         find_most_recent_tag( uint64_t offset );
    void        save_last();
    tag_shifter::time_tuple  advance_time_tuple( tag_shifter::time_tuple gps_time, double seconds );
    void        augment_reality( int samples_to_skip, int noutput_items );
    void        handle_update(pmt::pmt_t msg);
 
    void forecast (int noutput_items, gr_vector_int &ninput_items_required);
    // *** Member Variables ***
    
    // Control
    bool        d_is_receive_side;
    int         d_input_size;
    int         d_integer_time_offset;
    bool        d_generate_time_tag;
    bool		d_drop_1_second;
    
    // Timing
    uint64_t    d_offset;
    tag_shifter::time_tuple  d_gps_time;
    
    uint64_t    d_drop_count;
    int64_t    d_offset_shift;

    // Handling Tags
    std::deque<gr_tag_t> d_time_tags;
	std::deque<gr_tag_t> d_rate_tags;
	std::deque<gr_tag_t> d_freq_tags;
	std::vector<tag_shifter::tag_tuple> d_tag_tuples;
	
	// Save variables
	int64_t                 d_offset_save;
	tag_shifter::time_tuple d_time_save;
	double                  d_rate_save;
	pmt::pmt_t              d_src_id_save;
	pmt::pmt_t              d_freq_save;

 public:
	~digital_ll_time_tag_shifter ();


	  int general_work (int noutput_items,
	            gr_vector_int &ninput_items,
			    gr_vector_const_void_star &input_items,
			    gr_vector_void_star &output_items);

};

#endif /* INCLUDED_DIGITAL_LL_TIME_TAG_SHIFTER_H */

