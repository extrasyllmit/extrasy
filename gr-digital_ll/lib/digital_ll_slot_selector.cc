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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <digital_ll_slot_selector.h>
#include <gr_io_signature.h>
#include <digital_ll_timestamp.h>
#include <boost/numeric/interval.hpp>
#include <string.h>
#include <stdio.h>
#include <limits.h>

//used with d_tag_tuple
#define SAMP_IND 0
#define GPS_TIME_IND 1
#define RATE_IND 2

#define DEBUG false


static pmt::pmt_t RATE_SYM = pmt::pmt_string_to_symbol("rx_rate");
static pmt::pmt_t TIME_SYM = pmt::pmt_string_to_symbol("rx_time");
static pmt::pmt_t ID_SYM = pmt::pmt_string_to_symbol("digital_ll_slot_selector");

namespace icl = boost::icl;
using boost::get;
using boost::icl::continuous_interval;
using boost::icl::interval;
using std::min;

bool digital_ll_slot_selector::compare_tuple_ts(const boost::tuples::tuple<uint64_t, digital_ll_timestamp, double> & t1,
		const boost::tuples::tuple<uint64_t, digital_ll_timestamp, double> & t2)
{
	bool result = get<GPS_TIME_IND>(t1) <  get<GPS_TIME_IND>(t2);
	return result;
}

bool digital_ll_slot_selector::compare_tuple_offset(const boost::tuples::tuple<uint64_t, digital_ll_timestamp, double> & t1,
		const boost::tuples::tuple<uint64_t, digital_ll_timestamp, double> & t2)
{
	bool result = get<SAMP_IND>(t1) <  get<SAMP_IND>(t2);
	return result;
}


digital_ll_slot_selector_sptr
digital_ll_make_slot_selector(size_t item_size, double frame_len,
		std::vector<double> slot_lens, std::vector<double> slot_offsets,
		uint64_t frame_t0_int_s, double frame_t0_frac_s,
		uint64_t stream_t0_int_s, double stream_t0_frac_s, double fs)
{
  return digital_ll_slot_selector_sptr(new digital_ll_slot_selector(item_size, frame_len,
			slot_lens, slot_offsets, frame_t0_int_s, frame_t0_frac_s,
			stream_t0_int_s, stream_t0_frac_s, fs));
}


/*
*
* offset = 0, starts with 0th item
* offset = 1, starts with 1st item, etc...
*
* we take m items out of each n
*/
digital_ll_slot_selector::digital_ll_slot_selector(size_t item_size, double frame_len,
		std::vector<double> slot_lens, std::vector<double> slot_offsets,
		uint64_t frame_t0_int_s, double frame_t0_frac_s,
		uint64_t stream_t0_int_s, double stream_t0_frac_s, double fs)
  : gr_block("slot_selector",
	     gr_make_io_signature(1, 1, item_size),
	     gr_make_io_signature(1, 1, item_size)),
    d_frame_len(frame_len),
    d_slot_lens(slot_lens),
    d_slot_offsets(slot_offsets),
    d_frame_t0_gps(frame_t0_int_s, frame_t0_frac_s),
    d_itemsize(item_size),
    d_timestamp_gps(stream_t0_int_s, stream_t0_frac_s),
    d_timestamp_sample(0),
    d_samp_rate(fs),
    d_last_time_tag_update_gps(0,0)
{

    set_tag_propagation_policy(TPP_DONT);
    set_output_multiple(1);
    std::vector<std::string> context_keys;
    context_keys.push_back("dig_chan");
    d_tag_manager = digital_ll_context_tag_manager(context_keys);
}


void
digital_ll_slot_selector::forecast(int noutput_items, gr_vector_int &ninput_items_required)
{
  ninput_items_required[0] = noutput_items;
}

// sort incoming stream tags into lists of rate tags, time tags, and all other tags,
// each list sorted by offset
void
digital_ll_slot_selector::sort_tags(std::vector<gr_tag_t> tags)
{
	//fprintf(stderr, "sort tags start\n");
  //clear stored tag vectors
  d_time_tags.clear();
  d_rate_tags.clear();
  d_other_tags.clear();
  d_tag_tuples.clear();

  digital_ll_timestamp ts;
  double rate;
  uint64_t offset;


  //sort current tags into time tags, rate tags, and all other tags
  std::vector<gr_tag_t>::iterator it;

  for( it= tags.begin(); it != tags.end(); it++ )
  {
	  if(it->key == RATE_SYM)
	  {
		  if(DEBUG) { fprintf(stdout, "Found rate tag\n"); }
		  //check for duplicate keys at offset. Keep the last tag in case of dups
		  if(!d_rate_tags.empty() && d_rate_tags.back().offset == it->offset)
		  {
			  d_rate_tags.pop_back();
			  d_rate_tags.push_back(*it);
		  }
		  else
		  {
			  d_rate_tags.push_back(*it);
		  }

		  offset = d_rate_tags.back().offset;
		  rate = pmt::pmt_to_double(d_rate_tags.back().value);
		  //fprintf(stderr,"found rate tag of %f Hz at offset %lu\n", rate, offset);
	  }
	  else if(it->key == TIME_SYM)
	  {
		  if(DEBUG) { fprintf(stdout, "Found time tag\n");}
		  //check for duplicate keys at offset. Keep the last tag in case of dups
		  if(!d_time_tags.empty() && d_time_tags.back().offset == it->offset)
		  {
			  d_time_tags.pop_back();
			  d_time_tags.push_back(*it);
		  }
		  else
		  {
			  d_time_tags.push_back(*it);
		  }
		  offset = d_time_tags.back().offset;
		  ts = digital_ll_timestamp(
		  		  			pmt::pmt_to_uint64(pmt::pmt_tuple_ref(d_time_tags.back().value,0)),
		  		  			pmt::pmt_to_double(pmt::pmt_tuple_ref(d_time_tags.back().value,1)));
		  //fprintf(stderr,"found time tag of %lu, %f s at offset %lu\n", ts.int_s(), ts.frac_s(), offset);
	  }
	  else
	  {
		  d_tag_manager.add_context_tag(*it);
		  // ignore other non-context tags for now
		  d_other_tags.push_back(*it);
	  }
  }

  // sort each list by offset
  std::sort(d_rate_tags.begin(), d_rate_tags.end(), gr_tag_t::offset_compare);
  std::sort(d_time_tags.begin(), d_time_tags.end(), gr_tag_t::offset_compare);
  std::sort(d_other_tags.begin(), d_other_tags.end(), gr_tag_t::offset_compare);



	// convert time and rate tags into offset, time, rate tuple

	// if the first time tag appears later than the time tag saved from the previous
	// iteration, or there are no tags in the current sample set,
	// add the previous iterations time tag so timestamps can be computed for
	// any sample in the current sample block
	if ( (d_time_tags.empty()) ||
		 (d_time_tags.begin()->offset > d_timestamp_sample))
	{
		d_tag_tuples.push_back(boost::make_tuple(d_timestamp_sample,d_timestamp_gps,d_samp_rate));
	}

	// store the rest of the tags as tuples
	for(int k=0; k<d_time_tags.size(); k++)
	{
		offset = d_time_tags[k].offset;
		ts = digital_ll_timestamp(
			pmt::pmt_to_uint64(pmt::pmt_tuple_ref(d_time_tags[k].value,0)),
			pmt::pmt_to_double(pmt::pmt_tuple_ref(d_time_tags[k].value,1)));

		//round timestamp to be integer number of samples
		ts = digital_ll_timestamp(ts.int_s(),
						round(ts.frac_s()*d_samp_rate)/d_samp_rate);

		rate = pmt::pmt_to_double(d_rate_tags[k].value);

		d_tag_tuples.push_back(boost::make_tuple(offset,ts,rate ));
	}
//
//	if(d_tag_tuples.size() > 1)
//	{
//		for (tag_tuple_it ii=d_tag_tuples.begin(); ii !=d_tag_tuples.end(); ii++ )
//		{
//			fprintf(stderr,"initial offset is %lu, delta from d_gps is %f\n",
//					get<SAMP_IND>(*ii), double(get<GPS_TIME_IND>(*ii)-d_timestamp_gps));
//		}
//	}

	//fprintf(stderr, "sort tags complete\n");
}

ts_interval_set
digital_ll_slot_selector::compute_current_blocks(gr_vector_int &ninput_items)
{
	//fprintf(stderr, "compute_current_blocks\n");
	ts_interval_set block_ints;

	digital_ll_timestamp t_start_gps;
	digital_ll_timestamp t_end_gps;
	int64_t reference_sample;
	double samp_rate;


	samp_rate = get<RATE_IND>(d_tag_tuples[0]);
	reference_sample= get<SAMP_IND>(d_tag_tuples[0]);


	// handle special case of tag occurring at the first sample of this block
	if(reference_sample == nitems_read(0))
	{
		
		d_timestamp_gps = get<GPS_TIME_IND>(d_tag_tuples[0]);
		d_timestamp_sample = reference_sample;
		d_samp_rate = samp_rate;
		d_frame_t0_gps = d_timestamp_gps;

		if(DEBUG) {fprintf(stdout, "special case: d_timestamp_gps is %lu,%f\n",
		d_timestamp_gps.int_s(), d_timestamp_gps.frac_s());}
	}


	uint64_t current_offset, next_offset;

	current_offset = nitems_read(0);
	t_start_gps = get<GPS_TIME_IND>(d_tag_tuples[0]) + (current_offset-reference_sample)/samp_rate;



//	fprintf(stderr, "d_timestamp_gps is %lu,%f\n",
//			d_timestamp_gps.int_s(), d_timestamp_gps.frac_s());
//	fprintf(stderr, "samp rate is is %f, reference sample is %ld \n", d_samp_rate, d_timestamp_sample);


	// loop through all rate/time tag pairs in the lists, using the offset of the current
	// tag to compute the endpoint of the previous interval
	for( int k=1; k<d_tag_tuples.size(); k++)
	{
		next_offset = get<SAMP_IND>(d_tag_tuples[k]);
		t_end_gps = t_start_gps + (next_offset - current_offset)/samp_rate;

		interval<double>::type current_int(double(t_start_gps-d_timestamp_gps), double(t_end_gps-d_timestamp_gps));


		// update variables for next iteration
		current_offset = get<SAMP_IND>(d_tag_tuples[k]);
		samp_rate = get<RATE_IND>(d_tag_tuples[k]);
		t_start_gps = get<GPS_TIME_IND>(d_tag_tuples[k]);

		block_ints.insert(current_int );



	}

	// add final endpoint
	next_offset = nitems_read(0) + ninput_items[0];
	t_end_gps = get<GPS_TIME_IND>(d_tag_tuples.back()) + double(next_offset - get<SAMP_IND>(d_tag_tuples.back()))/samp_rate;

//	fprintf(stdout, "last generated block starts at %lu,%f and ends at %lu,%f\n",
//				t_start.int_s(), t_start.frac_s(),t_end.int_s(),t_end.frac_s());

	// add in last interval
	interval<double>::type current_int(double(t_start_gps-d_timestamp_gps), double(t_end_gps-d_timestamp_gps));
	block_ints.insert(current_int );
//	fprintf(stdout, "generated %i current blocks\n",interval_count(block_ints));
	//fprintf(stderr, "compute_current_blocks complete\n");
	return block_ints;

}

ts_separate_interval_set
digital_ll_slot_selector::compute_slots_of_interest(
		  ts_interval_set current_blocks)
{
	//fprintf(stderr, "compute_slots_of_interest\n");

	//slots of interest must be a separate interval type, otherwise adjacent slots of
	//interest will be joined into one large slot. This is a problem for the default case
	//of passing all samples (ie frame length = 1, slot length = 1)
	ts_separate_interval_set slot_ints;

	// get lower and upper time bounds of current blocks

	double t_start = lower(current_blocks);
	double t_end = upper(current_blocks);

	// check if there's a new schedule set to start during the current blocks
    // note that a scoped lock isn't acquired unless there's something already
	// in the schedule queue. This makes the assumption that new schedules will show up
	// at least one work function call ahead of time. This prevents locking and unlocking
	// the mutex all the time when in the common case it won't be needed

	if(!d_next_schedule.empty() )
	{
		gruel::scoped_lock guard(*mutex());

		struct Schedule sched;

		//use this as a sentinel value to make sure something was actually assigned in
		// the following loop
		sched.frame_len = -1;
		std::deque<Schedule>::iterator it;

		for(it=d_next_schedule.begin(); it != d_next_schedule.end(); it++)
		{
//			fprintf(stdout, "schedule change at front is timestamped %lu,%f, for block starting %lu,%f and ending %lu,%f\n",
//					it->frame_t0.int_s(), it->frame_t0.frac_s(),
//									t_start.int_s(), t_start.frac_s(),t_end.int_s(),t_end.frac_s());
			// if this schedule change starts in the current block set
			if ( double(it->frame_t0 - d_timestamp_gps) < t_end)
			{
				sched = *it;
//				fprintf(stdout, "schedule change for %lu,%12.10f found in block starting %lu,%.10f and ending %lu,%12.10f\n",
//						sched.frame_t0.int_s(), sched.frame_t0.frac_s(),
//						t_start.int_s(), t_start.frac_s(),t_end.int_s(),t_end.frac_s());

				d_next_schedule.pop_front();

			}
			// otherwise break out of the loop
			else
			{
				break;
			}
		}

		// clear out any elements that are no longer needed
		d_next_schedule.erase(d_next_schedule.begin(), it);
		// assign the new schedule if the frame length has been replaced by something
		// valid
		if(sched.frame_len >0)
		{
			d_frame_len = sched.frame_len;
			d_slot_lens = sched.slot_lens;
			d_slot_offsets = sched.slot_offsets;
			d_frame_t0_gps = sched.frame_t0;

//			fprintf(stdout, "schedule changed. New schedule t0: %lu,%f, for block starting %lu,%f and ending %lu,%f\n",
//					sched.frame_t0.int_s(), sched.frame_t0.frac_s(),
//					(d_timestamp_gps + t_start).int_s(),
//					(d_timestamp_gps + t_start).frac_s(),
//					(d_timestamp_gps + t_end).int_s(),
//					(d_timestamp_gps + t_end).frac_s());

		}
	}



//	fprintf(stdout, "block starts at %lu,%f and ends at %lu,%f\n",
//			t_start.int_s(), t_start.frac_s(),t_end.int_s(),t_end.frac_s());

	//find the first frame that begins before t_start and the last frame that ends
	// after t_end

	int64_t first_frame_num = ceil( double(d_timestamp_gps - d_frame_t0_gps + t_start)/d_frame_len)-1;
	int64_t last_frame_num = floor( double(d_timestamp_gps - d_frame_t0_gps + t_end)/d_frame_len)+1;

//	fprintf(stdout, "first frame num is %ld, last frame num is %ld\n", first_frame_num,
//			last_frame_num);

	//compute the intervals of each slot in our slot list from the first to the last
	//frame number

	digital_ll_timestamp slot_start_gps, slot_end_gps;
	for(int64_t m=first_frame_num; m<=last_frame_num; m++)
	{
		for(int n=0; n< d_slot_lens.size(); n++)
		{
			slot_start_gps = d_frame_t0_gps + (double(m)*d_frame_len + d_slot_offsets[n]);
			slot_end_gps = d_frame_t0_gps + (double(m)*d_frame_len + d_slot_offsets[n] + d_slot_lens[n]);

//			fprintf(stdout, "slot starts at %lu,%f and ends at %lu,%f\n",
//					slot_start_gps.int_s(), slot_start_gps.frac_s(),slot_end_gps.int_s(),slot_end_gps.frac_s());


			interval<double>::type current_slot(double(slot_start_gps-d_timestamp_gps), double(slot_end_gps-d_timestamp_gps));

			slot_ints.insert(current_slot);
		}
	}
//	fprintf(stdout, "generated %i slots of interest\n",interval_count(slot_ints));
	//fprintf(stderr, "compute_slots_of_interest complete\n");
	return slot_ints;

}

ts_separate_interval_set
digital_ll_slot_selector::compute_output_slots(
		  ts_interval_set current_blocks,
		  ts_separate_interval_set slots_of_interest)
{
  // compute the intersection of the slots of interest with current blocks
  return current_blocks & slots_of_interest;
}


int digital_ll_slot_selector::limit_output_samples(
                          int noutput_items,
                          int ninput_items,
                          ts_interval_set current_blocks,
                          ts_separate_interval_set & output_slots)
{
  // handle special case where there's nothing to output. In this case,
  // none of the slots of any of the frames of interest overlap with the
  // samples we have access to in input_items. Therefore, we should consume
  // all the input samples
  if(output_slots.iterative_size() == 0)
  {
    return ninput_items;
  }
  // handle case where all the samples in output slots will fit in
  // the output buffer. This means that we're starved for input samples, so
  // consume all the input samples we have access to
  else if( round(length(output_slots)*d_samp_rate) <= noutput_items)
  {
    return ninput_items;
  }
  // We need to limit the number of samples produced to noutput items.
  // Find the time associated with the last sample that will fit in the output
  // buffer and limit the output slots to those samples that occur before that
  // time
  else
  {
    int block_samples=0;
    int total_samples=0;
    ts_separate_interval_set::iterator it = output_slots.begin();
    ts_interval_set blocks_consumed;

    for(it; it!=output_slots.end(); it++)
    {
      block_samples = round(length(*it)*d_samp_rate);

      if(total_samples+block_samples<noutput_items)
      {
        total_samples+=block_samples;
      }
      else
      {
        // find the number of samples from the last block that can still
        // fit in what's left of the output buffer
        double last_block_samples = (noutput_items - total_samples);

        // find the time associated with the last of the samples that will
        // fit in the output buffer
        double last_block_end = last_block_samples/d_samp_rate + lower(*it);

        // set up an interval we can use to limit the samples that show up in
        // output_slots, as well as to calculate how many input samples to
        // consume
        ts_interval_set sample_mask;
        sample_mask.insert(interval<double>::type(last_block_end, std::numeric_limits<double>::infinity()));

        // limit the output samples
        output_slots -= sample_mask;

        blocks_consumed = current_blocks - sample_mask;
        break;
      }
    }
    return round(length(blocks_consumed)*d_samp_rate);
  }
}


int
digital_ll_slot_selector::produce_outputs(
		  ts_interval_set current_blocks,
		  ts_separate_interval_set slots_of_interest,
		  ts_separate_interval_set output_slots,
		  int noutput_items,
		  gr_vector_int &ninput_items,
		  gr_vector_const_void_star &input_items,
		  gr_vector_void_star &output_items)
{
	//fprintf(stderr, "produce_outputs\n");
	//fprintf(stderr, "noutputs: %i ninputs: %i nitems_read: %lu nitems_written %lu\n",
	//		  noutput_items, ninput_items[0], nitems_read(0), nitems_written(0));
//	fprintf(stdout, "generated %i output slots\n",interval_count(output_slots));
	std::deque<gr_tag_t> out_tags;


	double slot_ts; // timestamp of the start of the current output
	digital_ll_timestamp time_tag_ts_gps; // timestamp of the current time tag
	digital_ll_timestamp ref_ts_gps; // timestamp of the time tag used as a reference
	double ref_rate; // sample rate of the rate tag used as a reference
	double ref_offset; // offset of the time/rate tag used as reference


	//Loop over the slots of interest and generate rx_time and rx_rate tags
	// for each block with a starting point contained in the current set of sample blocks

	tag_tuple_it ref_it;

	gr_tag_t time_tag, rate_tag;
	int input_offset, output_offset;
	boost::tuple<uint64_t, digital_ll_timestamp, double> dummy_tuple;



	double tag_ts;
	//add any "other" tags that intersect with an output slot
	for(std::deque<gr_tag_t>::iterator it=d_other_tags.begin(); it!=d_other_tags.end(); it++)
	{
		//create dummy tuple with tag offset to use in the upper_bound function
		dummy_tuple = boost::make_tuple(it->offset,0,0 );
		// find the last offset less than or equal to the offset of the
		// current tag. We need this to compute the correct timestamp for the given
		// tag

		// get an iterator to the first element greater than the offset of the
		// current tag
		ref_it = std::upper_bound(d_tag_tuples.begin(), d_tag_tuples.end(),
							 dummy_tuple,compare_tuple_ts);

		// the last element less than or equal to the starting point will be one
		// element before the first element greater than the starting point.
		// as long as the first element greater than or equal to the starting point
		// is not the first element in the vector, move the reference iterator down
		// one. If the test fails, something is wrong, so don't try to add the other
		// tag
		if( ref_it != d_tag_tuples.begin() )
		{
			ref_it--;
			ref_ts_gps = get<GPS_TIME_IND>(*ref_it);
			ref_rate = get<RATE_IND>(*ref_it);
			ref_offset = get<SAMP_IND>(*ref_it);

			// compute tag timestamp with respect to the current block frame of reference
			tag_ts = double(ref_ts_gps-d_timestamp_gps) + (it->offset-ref_offset)/ref_rate;

			if(contains(output_slots,tag_ts))
			{
				out_tags.push_back(*it);
			}
		}
	}

	//sort the output tags by offset
	std::sort(out_tags.begin(), out_tags.end(), gr_tag_t::offset_compare);

	// set up input and output pointers
	uint8_t* out = (uint8_t*)output_items[0];
	const uint8_t* in = (const uint8_t*)input_items[0];
	output_offset = 0;
	double slot_len_s;
	uint64_t slot_len_samps;
	std::deque<gr_tag_t>::iterator out_it = out_tags.begin();
	std::vector<gr_tag_t> context_tags;
	std::vector<gr_tag_t>::iterator tag_it;

	// now loop over the set of output blocks, copying input samples to outputs and adding
	// tags as needed

	for( ts_interval_set::iterator it = output_slots.begin();
				it != output_slots.end(); it++)
	{
		// get starting timestamp of output slot
		slot_ts = it->lower();

//		fprintf(stdout, "d_timestamp_gps is %lu,%f\n",
//				d_timestamp_gps.int_s(), d_timestamp_gps.frac_s());
//		fprintf(stdout, "samp rate is is %f, reference sample is %ld \n", d_samp_rate, d_timestamp_sample);
//


		//create dummy tuple with slot_ts to use in the upper_bound function
		digital_ll_timestamp dummy_ts = d_timestamp_gps + slot_ts;

		//round fractional seconds to be integer number of samples
		dummy_ts = digital_ll_timestamp(dummy_ts.int_s(),
				round(dummy_ts.frac_s()*d_samp_rate)/d_samp_rate);

		dummy_tuple = boost::make_tuple(0,dummy_ts,0 );


		// find the last timestamp less than or equal to the starting point of the
		// current slot. We need this to compute the correct offset for the given
		// timestamp of the slot

		// get an iterator to the first element greater than the starting point of the
		// current slot
		ref_it = std::upper_bound(d_tag_tuples.begin(), d_tag_tuples.end(),
				dummy_tuple,compare_tuple_ts);

		if( ref_it != d_tag_tuples.begin() )
		{
			ref_it--;

			ref_ts_gps = get<GPS_TIME_IND>(*ref_it);
			ref_rate = get<RATE_IND>(*ref_it);
			ref_offset = get<SAMP_IND>(*ref_it);

			input_offset = round( (slot_ts + double(d_timestamp_gps-ref_ts_gps)) * ref_rate)
					+ ref_offset-nitems_read(0);

			if( input_offset > ninput_items[0])
			{


				ref_it++;
				fprintf(stderr,"input offset %d exceeds number of input items %d\n", input_offset, ninput_items[0]);


				for (tag_tuple_it ii=d_tag_tuples.begin(); ii !=d_tag_tuples.end(); ii++ )
				{
					fprintf(stderr,"ref offset is %lu, delta from d_gps is %f\n",
							get<SAMP_IND>(*ii), double(d_timestamp_gps - get<GPS_TIME_IND>(*ii)));
				}

				for (ts_interval_set::iterator ii = current_blocks.begin();
					  ii!=current_blocks.end(); ii++)
				{
				   fprintf(stdout, "current block begins at %f and ends at %f\n",
						 ii->lower(), ii->upper());
				}

				for (ts_separate_interval_set::iterator ii = slots_of_interest.begin();
									  ii!=slots_of_interest.end(); ii++)
				{
				   fprintf(stdout, "slot of interest block begins at %f and ends at %f\n",
										 ii->lower(), ii->upper());
				}

				for (ts_interval_set::iterator ii = output_slots.begin();
									  ii!=output_slots.end(); ii++)
				{
				   fprintf(stdout, "output_slot block begins at %f and ends at %f\n",
						 ii->lower(), ii->upper());
				}

			}

			const uint8_t* iptr = &in[input_offset*d_itemsize];
			uint8_t* optr = &out[output_offset*d_itemsize];

			// get length of current slot

			slot_len_s = length(*it);
			slot_len_samps = round(slot_len_s*ref_rate);

			//fprintf(stderr, "slot is %i samples long\n", slot_len_samps);
			//perform copy
			memcpy(optr,iptr, slot_len_samps*d_itemsize);

			//find the current slot of interest
			ts_separate_interval_set::iterator current_slot_it;
			current_slot_it = find(slots_of_interest,slot_ts);

			// add time and rate tags to this slot if no tags have previously been added
			// for this slot
			if( contains( (*it),current_slot_it->lower()) | ((slot_ts + d_timestamp_gps) > d_last_time_tag_update_gps) )
			{

				time_tag_ts_gps = d_timestamp_gps+ digital_ll_timestamp(slot_ts);


				time_tag.key = TIME_SYM;
				time_tag.offset = output_offset+nitems_written(0);
				time_tag.value = pmt::pmt_make_tuple(
					pmt::pmt_from_uint64(time_tag_ts_gps.int_s()),
					pmt::pmt_from_double(time_tag_ts_gps.frac_s()) );
				time_tag.srcid = ID_SYM;

				rate_tag.key = RATE_SYM;
				rate_tag.offset = output_offset+nitems_written(0);
				rate_tag.value = pmt::pmt_from_double(ref_rate);
				rate_tag.srcid = ID_SYM;

				add_item_tag(0,time_tag);
				add_item_tag(0,rate_tag);

				d_last_time_tag_update_gps = time_tag_ts_gps + length(*current_slot_it);

				int64_t tag_start_offset = int64_t(input_offset) + int64_t(nitems_read(0));
				int64_t tag_end_offset = tag_start_offset + slot_len_samps;
				context_tags = d_tag_manager.get_latest_context_tags(tag_start_offset,
						tag_end_offset);

//				fprintf(stderr, "slot selector searched for latest tag at offset %ld, time %lu,%.10f\n",
//						tag_start_offset,time_tag_ts_gps.int_s(), time_tag_ts_gps.frac_s());



				// add context tags to output as needed
				for( tag_it=context_tags.begin(); tag_it != context_tags.end(); tag_it++)
				{
					int64_t old_offset = tag_it->offset;


					// compute the tag offset with respect to the start of the current block
					int64_t tag_block_offset = tag_it->offset - (input_offset + nitems_read(0));

					// if the tag occurs before the start of the block, move the offset to
					// the first sample of the block
					if( tag_block_offset < 0)
					{
						tag_it->offset = output_offset+nitems_written(0);
					}
					// otherwise shift it within the block appropriately
					else
					{
						tag_it->offset = tag_block_offset + output_offset+nitems_written(0);
					}

					add_item_tag(0, *tag_it);

					digital_ll_timestamp old_ts = d_timestamp_gps + double(old_offset-nitems_read(0)-input_offset-d_timestamp_sample)/ref_rate;
					digital_ll_timestamp new_ts = d_timestamp_gps + slot_ts + (tag_it->offset - output_offset - nitems_written(0))/ref_rate;
//					fprintf(stderr, "slot selector moving offset for dig chan tag value %ld from offset %ld, time %lu,%.10f to %ld, time %lu,%.10f\n",
//							pmt::pmt_to_long(tag_it->value),
//							old_offset, old_ts.int_s(), old_ts.frac_s(),
//							tag_it->offset, new_ts.int_s(), new_ts.frac_s());

				}

				if (DEBUG) {

				for (ts_interval_set::iterator ii = current_blocks.begin();
					  ii!=current_blocks.end(); ii++)
				{
				   fprintf(stdout, "current block begins at %f and ends at %f\n",
						 ii->lower(), ii->upper());
				}

				for (ts_separate_interval_set::iterator ii = slots_of_interest.begin();
									  ii!=slots_of_interest.end(); ii++)
				{
				   fprintf(stdout, "slot of interest block begins at %f and ends at %f\n",
										 ii->lower(), ii->upper());
				}

				for (ts_interval_set::iterator ii = output_slots.begin();
									  ii!=output_slots.end(); ii++)
				{
				   fprintf(stdout, "output_slot block begins at %f and ends at %f\n",
						 ii->lower(), ii->upper());
				}


				fprintf(stdout, "slot ts was %.10f seconds relative to timestamp %lu,%.10f\n",
						slot_ts, d_timestamp_gps.int_s(), d_timestamp_gps.frac_s());

				fprintf(stdout, "time tag gps was  %lu,%.10f\n",
										time_tag_ts_gps.int_s(), time_tag_ts_gps.frac_s());

				fprintf(stdout, "current slot was %.10f seconds long\n", length(*current_slot_it));

				}
//				fprintf(stdout, "adding time tag ts of %lu,%f at output sample %lu\n",
//						time_tag_ts_gps.int_s(), time_tag_ts_gps.frac_s(), output_offset+nitems_written(0));
			}

			//fprintf(stderr, "copy complete\n");
			//propogate tags to output
			if(out_it != out_tags.end())
			{

//				fprintf(stdout, "slot starts at %f and ends at %f\n",
//						it->lower(),
//						it->upper());

				tag_ts = digital_ll_timestamp(ref_ts_gps + (out_it->offset-ref_offset)/ref_rate -d_timestamp_gps );
//				fprintf(stdout, "tag ts is %f\n", tag_ts);
			}
			while((out_it != out_tags.end()) && (contains((*it),tag_ts)) )
			{
//				fprintf(stdout, "tag offset: %lu input offset: %lu output_offset: %lu nitems_read %lu nitems_written %lu\n",
//						out_it->offset, input_offset, output_offset, nitems_written(0), nitems_read(0));

				//shift tag offset to be in terms of output offset
				out_it->offset = out_it->offset - input_offset - nitems_read(0) +
						output_offset + nitems_written(0);

//				fprintf(stderr, "adding tag to output at offset %lu\n", out_it->offset);
				add_item_tag(0,*out_it);
				out_it++;
				if(out_it != out_tags.end())
				{
					tag_ts = digital_ll_timestamp(ref_ts_gps-d_timestamp_gps + (out_it->offset-ref_offset)/ref_rate);
				}
			}

			//update output_offset
			output_offset +=slot_len_samps;
		}
	}
	//fprintf(stderr, "produce_outputs complete, returning %i samples\n", output_offset);
	return output_offset;
}

// set schedule will store a new schedule to take effect at frame_t0. If there's already
// an older schedule queued up, it will be overwritten
void
digital_ll_slot_selector::set_schedule(double frame_len, std::vector<double> slot_lens,
		  std::vector<double> slot_offsets,
		  uint64_t frame_t0_int_s, double frame_t0_frac_s)
{
	// declare and initialize schedule struct
	struct Schedule sched;
	sched.frame_len = frame_len;
	sched.slot_lens = slot_lens;
	sched.slot_offsets = slot_offsets;
	sched.frame_t0 = digital_ll_timestamp(frame_t0_int_s, frame_t0_frac_s);

	// lock the mutex so we don't mess with the schedule queue while the work function
	// is in the middle of accessing it
	gruel::scoped_lock guard(*mutex());

	// check the last element of the schedule queue. If the new schedule has a timestamp
	// earlier than the oldest element of the schedule queue, erase the last element and
	// check the next oldest element. Once the new schedule has the oldest timestamp in
	// the queue, assign it to the queue

	while(!d_next_schedule.empty())
	{
		if(d_next_schedule.back().frame_t0 >= sched.frame_t0)
		{
			d_next_schedule.pop_back();
		}
		else
		{
			break;
		}
	}
	if(DEBUG){fprintf(stdout, "schedule change for %lu,%12.10f stored\n",
							sched.frame_t0.int_s(), sched.frame_t0.frac_s());}

	d_next_schedule.push_back(sched);
	if(DEBUG){
		fprintf(stdout, "schedule queue now has %lu schedules\n",d_next_schedule.size());}
}

int
digital_ll_slot_selector::general_work(int noutput_items,
			     gr_vector_int &ninput_items,
			     gr_vector_const_void_star &input_items,
			     gr_vector_void_star &output_items)
{

  //fprintf(stderr, "work: noutputs: %i ninputs: %i nitems_read: %lu nitems_written %lu\n",
  //		  noutput_items, ninput_items[0], nitems_read(0), nitems_written(0));
  std::vector<gr_tag_t> tags;
  int samps_made;
  // get the tags for the current block

  get_tags_in_range(tags, 0, nitems_read(0), nitems_read(0) + ninput_items[0]);

  // sort the tags out into d_time_tags, d_rate_tags, and d_other_tags
  sort_tags(tags);

  // get the set of continuous sample blocks in the current sample range
  ts_interval_set current_blocks = compute_current_blocks(ninput_items);

  // compute the ranges of slots potentially intersecting the current sample range
  ts_separate_interval_set slots_of_interest = compute_slots_of_interest(current_blocks);

  // get the intersection of the slots of interest with the input continuous sample blocks
  ts_separate_interval_set output_slots = compute_output_slots(current_blocks, slots_of_interest);

  int samples_consumed = limit_output_samples(noutput_items, ninput_items[0],
                                              current_blocks, output_slots);
  // generate outputs and propagate tags
  samps_made = produce_outputs(current_blocks, slots_of_interest, output_slots,
		  noutput_items, ninput_items, input_items, output_items);

  //store last time tag and rate tag for reference

  if (!d_tag_tuples.empty())
  {
	  d_timestamp_gps = get<GPS_TIME_IND>(d_tag_tuples.back());
	  d_timestamp_sample = get<SAMP_IND>(d_tag_tuples.back());
	  d_samp_rate = get<RATE_IND>(d_tag_tuples.back());
  }
  //fprintf(stderr, "work complete: returning %i samples\n", samps_made);

  consume_each(samples_consumed);
//  fprintf(stderr,"ninputs: %d noutputs: %d samples consumed: %d samples made:%d\n",
//		  ninput_items[0], noutput_items, samples_consumed, samps_made);
  // tell gnuradio how many samples we made
  return samps_made;
}
