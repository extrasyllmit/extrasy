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


#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gr_io_signature.h>
#include <digital_ll_time_tag_shifter.h>
#include <stdio.h>

static pmt::pmt_t RATE_SYM    = pmt::pmt_string_to_symbol("rx_rate");
static pmt::pmt_t FREQ_SYM    = pmt::pmt_string_to_symbol("rx_freq");
static pmt::pmt_t RX_TIME_SYM = pmt::pmt_string_to_symbol("rx_time");
static pmt::pmt_t TX_TIME_SYM = pmt::pmt_string_to_symbol("tx_time");

//used with d_tag_tuple
#define SAMP_IND 0
#define GPS_TIME_IND 1
#define RATE_IND 2
#define SRCID_IND 3
#define FREQ_IND 4



using boost::get;

digital_ll_time_tag_shifter_sptr
digital_ll_make_time_tag_shifter (int is_receive_side, int input_size)
{
	return digital_ll_time_tag_shifter_sptr (new digital_ll_time_tag_shifter (is_receive_side, input_size));
}


digital_ll_time_tag_shifter::digital_ll_time_tag_shifter (int is_receive_side, int input_size)
	: gr_block ("time_tag_shifter",
		gr_make_io_signature (1, 1, input_size),
		gr_make_io_signature (1, 1, input_size))
{

    // Create the message passing interface and handle function
    message_port_register_in(pmt::pmt_string_to_symbol("time_tag_shift"));
    set_msg_handler(pmt::mp("time_tag_shift"), boost::bind(&digital_ll_time_tag_shifter::handle_update, this, _1));

    // Set the propagation policy so that we do not propagate
    // any tags around this block. It will generate the necessary tags
    set_tag_propagation_policy( TPP_DONT );

    // Initialize the member variables
    d_input_size = input_size;
    d_integer_time_offset = 0; // at startup we assume correct GPS time
    d_generate_time_tag = false;
    d_is_receive_side   = (bool) is_receive_side;

    d_drop_1_second = false;
    d_drop_count = 0;
    d_offset_shift = 0;

}


digital_ll_time_tag_shifter::~digital_ll_time_tag_shifter ()
{
}

void
digital_ll_time_tag_shifter::handle_update(pmt::pmt_t msg)
{
    d_integer_time_offset = pmt::pmt_to_long(msg);
    d_generate_time_tag = true;

    if( (d_is_receive_side) and (d_integer_time_offset<0))
    {
    	fprintf(stderr,"---------Negative time offset found. Dropping 1 second of samples\n");
    	d_drop_1_second = true;
    	d_drop_count = 0;
    }
}

void
digital_ll_time_tag_shifter::forecast(int noutput_items, gr_vector_int &ninput_items_required)
{
  ninput_items_required[0] = noutput_items;
}


int
digital_ll_time_tag_shifter::general_work (int noutput_items,
        gr_vector_int &ninput_items,
	    gr_vector_const_void_star &input_items,
	    gr_vector_void_star &output_items)
{
	const char *in = (const char *) input_items[0];
	char *out = (char *) output_items[0];
	int samples_made;
	int samples_consumed;
	int samples_to_skip = 0;


	// if the offset was negative, drop 1 second of data on the floor so we don't
	// have to verify the downstream blocks are comfortable time traveling to the past
	if(d_drop_1_second)
	{
		// if we're within the region of only dropping samples, drop everything
		// and tell gnuradio we used all our inputs
		if(d_drop_count + ninput_items[0] < int(d_rate_save))
		{
			samples_made = 0;
			samples_consumed = ninput_items[0];

			d_drop_count+=ninput_items[0];
		}
		// if we're exactly at the boundary to stop dropping, do same as above, but also
		// set up status vars to show that we're done
		else if(d_drop_count + ninput_items[0] == int(d_rate_save))
		{
			samples_made = 0;
			samples_consumed = ninput_items[0];

			d_drop_count+=ninput_items[0];

			d_drop_1_second = false;
			d_offset_shift = d_rate_save;
		}
		else
		{
			// this is how many samples to skip over in the mem copy
			samples_to_skip = d_rate_save-d_drop_count;

			// compute how many samples to generate
			samples_made = std::min(ninput_items[0] - samples_to_skip, noutput_items);

			samples_consumed = samples_to_skip + samples_made;

			const uint8_t* in = (const uint8_t*)input_items[0];
			// shift pointer to skip required number of samples
			const uint8_t* iptr = &in[samples_to_skip*d_input_size];

			memcpy(out, iptr, (size_t)(d_input_size*samples_made));

			d_drop_1_second = false;
			d_offset_shift = d_rate_save;

		}
	}
	// if not in the middle of dropping samples, copy out samples as normal
	else
	{
		// Copy the input to the output
		samples_consumed = std::min(noutput_items,ninput_items[0]);
		samples_made = samples_consumed;
		memcpy(out, in, (size_t)(d_input_size*samples_consumed));
	}




	// The receive side must keep track of what gps time we think
	// we are at. This is because, if a change is requested we need to
	// generate a new tag so that all down wind SP blocks are aware of the
	// "new" gps time. Note that this save time will be the raw, uncorrected
	// gps time from the USRP/UHD.
	if( d_is_receive_side )
	{
        // Look for time stream tags and add the appropriate offset
        d_offset = get_tags( samples_consumed);

        if( d_generate_time_tag )
        {
            // Find the most recent tag
            int tag_ind;
            tag_ind = find_most_recent_tag( d_offset );
            
            if( tag_ind >= 0 )
            {   

            
                // Get the gps time
                d_gps_time = get<GPS_TIME_IND>(d_tag_tuples[tag_ind]);
                
                // Increment the gps time by how much we've advanced since
                // the last tag we saw.
                // TODO: By passing in progression as double instead of most
                // accurate <uint64_t, double> we lose precision over time.
                // Could hurt in some cases, but is probably safe for current
                // intended use.
                d_gps_time = advance_time_tuple(
                    d_gps_time,
                    ((double) (d_offset - get<SAMP_IND>(d_tag_tuples[tag_ind])) )/get<RATE_IND>(d_tag_tuples[tag_ind])
                    );
                
                // Advance the gps time to correct possible error
                d_gps_time = advance_time_tuple( d_gps_time, (double) d_integer_time_offset );
                
                // only do this if we aren't in the middle of dropping samples
                if(!d_drop_1_second)
                {
//                	fprintf(stderr, "adding new time tag of %lu,%f at output offset %lu from input offset %lu\n",
//                			get<0>(d_gps_time), get<1>(d_gps_time), d_offset-d_offset_shift, d_offset);

                	// Create the tag
					pmt::pmt_t value = pmt::pmt_make_tuple(
										pmt::pmt_from_uint64(get<0>(d_gps_time)),
										pmt::pmt_from_double(get<1>(d_gps_time))
										);
					add_item_tag( 0, d_offset-d_offset_shift, RX_TIME_SYM, value, get<SRCID_IND>(d_tag_tuples[tag_ind]) );
					add_item_tag( 0, d_offset-d_offset_shift, RATE_SYM, pmt::pmt_from_double(get<RATE_IND>(d_tag_tuples[tag_ind])), get<SRCID_IND>(d_tag_tuples[tag_ind]) );
					add_item_tag( 0, d_offset-d_offset_shift, FREQ_SYM, get<FREQ_IND>(d_tag_tuples[tag_ind]), get<SRCID_IND>(d_tag_tuples[tag_ind]) );

					// Lower flag
					d_generate_time_tag = false;
                }
            }
        }

        // Save the last elements for next call to work function
        save_last();
    }

    // Correct all the tags we see passing by us
    augment_reality(samples_to_skip, samples_consumed );

	// Tell runtime system how many output items we produced.
    consume_each(samples_consumed);
	return samples_made;
}

/*
Get the sorted tags and add them to the d_tag_tuples
*/
uint64_t
digital_ll_time_tag_shifter::get_tags( int ninput_items )
{


    // This function looks for all UHD tags (both time and rate) and sorts
    // them by their sample time offset. It then saves the tag information
    // in a vector of tag tuples which can be used by the other functions.

    // Clear the old tags
    d_time_tags.clear();
    d_rate_tags.clear();
    d_freq_tags.clear();
    d_tag_tuples.clear();
    
    // Get the tags from input, so that the GPS time may be matched to the
    // samples streaming in.
    std::vector<gr_tag_t> tags;
    const uint64_t nread = this->nitems_read(0); //number of items read
    //fprintf(stderr,"looking for tags from offset %lu to offset %lu\n", nread, nread+ninput_items);
    this->get_tags_in_range(tags, 0, nread, nread+ninput_items); // read the tags 
    
    // Search for UHD rx_time tags (which have been conveniently defined above)
    std::vector<gr_tag_t>::iterator it;
    for( it = tags.begin(); it != tags.end(); it++ )
    {
 //   	fprintf(stderr,"time tag shift input found tag\n");
        if(it->key == RATE_SYM)
        {
//        	fprintf(stderr,"time tag shift found rate tag at %lu\n",it->offset);
        	//std::cout << "Got a new rate tag. Total tags found = " << d_ntags_proc++ << "\n";
            //check for duplicate keys at offset. Keep the last tag in case of dups
            if(!d_rate_tags.empty() && d_rate_tags.back().offset == it->offset)
            {
	            d_rate_tags.back() = *it;
            }
            else
            {
	            d_rate_tags.push_back(*it);
            }
        }
        else if( it->key == RX_TIME_SYM )
        {
//        	fprintf(stderr,"time tag shift found rx time tag at %lu\n",it->offset);
            //std::cout << "Got a new time tag. Total tags found = " << d_ntags_proc++ << "\n";
            //check for duplicate keys at offset. Keep the last tag in case of dups
		    if(!d_time_tags.empty() && d_time_tags.back().offset == it->offset)
		    {
		        d_time_tags.back() = *it;
		    }
		    else
		    {
			    d_time_tags.push_back(*it);
		    }
        }
        else if(it->key == FREQ_SYM )
        {
//        	fprintf(stderr,"time tag shift found freq tag at %lu\n",it->offset);
            if(!d_freq_tags.empty() && d_freq_tags.back().offset == it->offset)
            {
                d_freq_tags.back() = *it;
            }
            else
            {
                d_freq_tags.push_back(*it);
            }
        }
    }
    
    // Sort the tags using STL functionality
    std::sort(d_time_tags.begin(), d_time_tags.end(), gr_tag_t::offset_compare);
    std::sort(d_rate_tags.begin(), d_rate_tags.end(), gr_tag_t::offset_compare);
    std::sort(d_freq_tags.begin(), d_freq_tags.end(), gr_tag_t::offset_compare);
    
    // If the last recorded tuple is recorded before most recent found tag, record it to
    // the tuple vector
    if( d_time_tags.empty() || d_time_tags.begin()->offset > d_offset_save )
    {
        d_tag_tuples.push_back(boost::make_tuple( d_offset_save, d_time_save, d_rate_save, d_src_id_save, d_freq_save ) );
    }
    
    // Store the rest of the tags as tuples
    int64_t    offset;
    int64_t    time_full_s;
    double     time_frac_s;
    double     rate;
    pmt::pmt_t freq;
    pmt::pmt_t src_id;
    tag_shifter::time_tuple time;
    
    for( int k = 0; k < d_time_tags.size(); k++ )
    {
        offset      = d_time_tags[k].offset;
        time_full_s = pmt::pmt_to_uint64(pmt::pmt_tuple_ref(d_time_tags[k].value,0));
        time_frac_s = pmt::pmt_to_double(pmt::pmt_tuple_ref(d_time_tags[k].value,1));
        rate        = pmt::pmt_to_double(d_rate_tags[k].value);
        src_id      = d_time_tags[k].srcid;
        freq        = d_freq_tags[k].value;
        
        time = boost::make_tuple( time_full_s, time_frac_s );
        d_tag_tuples.push_back( boost::make_tuple( offset, time, rate, src_id, freq ) );
    }
    
    return nread;
}

int
digital_ll_time_tag_shifter::find_most_recent_tag( uint64_t offset )
{
    // Find the most recent tag based off of offset.
    // This function assumes that d_tag_tuples is sorted by their
    // offset values from low to high.
    int most_recent = -1;
    for( int i = 0; i < d_tag_tuples.size(); i++ )
    {
        if( get<SAMP_IND>(d_tag_tuples[i]) < offset )
            most_recent = i;
    }
    
    return most_recent;
}

tag_shifter::time_tuple
digital_ll_time_tag_shifter::advance_time_tuple( tag_shifter::time_tuple gps_time, double seconds )
{
    // Increment the time tuple (consisting of integer and fractional components)
    // by seconds provided as a double. Returns time tuple.
    
    double fractpart, intpart;
    uint64_t carry_over;
    
    // Find out how much we will be incrementing the time by
    // storing it as an integer and fractional part
    fractpart = modf(seconds , &intpart);
    
    // Increment the fractional part. If the sum is > 1 then we want to 
    // subtract that from the fraction and add it to the integer part
    get<1>(gps_time)   = fractpart + get<1>(gps_time);
    if( get<1>(gps_time) >= 1.0 )
    {
        get<1>(gps_time) = get<1>(gps_time) - 1.0;
        carry_over = 1;
    }
    else
    {
        carry_over = 0;
    }
    
    // Increment the integer part and return
    get<0>(gps_time) = int64_t( intpart ) + get<0>(gps_time) + carry_over;
    return gps_time;   
}

void
digital_ll_time_tag_shifter::save_last()
{
    d_offset_save      = get<SAMP_IND>(d_tag_tuples.back());
    d_time_save        = get<GPS_TIME_IND>(d_tag_tuples.back());
    d_rate_save        = get<RATE_IND>(d_tag_tuples.back());
    d_src_id_save      = get<SRCID_IND>(d_tag_tuples.back());
    d_freq_save        = get<FREQ_IND>(d_tag_tuples.back());
}

/*
Thus function goes through the tags we've seen during this work function
and changes the rx time tags and tx time tags to reflect the discovered
gps inaccuracies.
*/
void
digital_ll_time_tag_shifter::augment_reality( int samples_to_skip, int noutput_items )
{
    // Get the tags from input, so that the GPS time may be matched to the
    // samples streaming in.
    std::vector<gr_tag_t> tags;
    const uint64_t nread = this->nitems_read(0); //number of items read
    const size_t ninput_items = noutput_items; //assumption for sync block
    this->get_tags_in_range(tags, 0, nread+samples_to_skip, nread+ninput_items); // read the tags
    
    // Loop over the tags. Generating output tags
    std::vector<gr_tag_t>::iterator it;
    pmt::pmt_t value;    // The value of the new tag
    int64_t time_full_s; // Full time in seconds (for time tags)
    double  time_frac_s; // Fractional time in seconds (for time tags)
    tag_shifter::time_tuple time_tuple; // time tuple

    for( it = tags.begin(); it != tags.end(); it++ )
    {
    
        if(it->key == RX_TIME_SYM || it->key == TX_TIME_SYM)
        {
//        	fprintf(stderr,"outputting time tag at offset %lu\n",it->offset-d_offset_shift);
            // Get int and fractional times
            time_full_s = pmt::pmt_to_uint64(pmt::pmt_tuple_ref(it->value,0));
            time_frac_s = pmt::pmt_to_double(pmt::pmt_tuple_ref(it->value,1));
            
            // Make time tuple
            time_tuple  = boost::make_tuple( time_full_s, time_frac_s );
            
            // Increment time tuple
            if( it->key == RX_TIME_SYM )
                time_tuple  = advance_time_tuple( time_tuple, (double) d_integer_time_offset );
            else
                time_tuple  = advance_time_tuple( time_tuple, -1.0*d_integer_time_offset );
                
            // Create a pmt tuple
            value = pmt::pmt_make_tuple(pmt::pmt_from_uint64(get<SAMP_IND>(time_tuple)), pmt::pmt_from_double(get<GPS_TIME_IND>(time_tuple)));
        }
        else
        {
            // Just propagate the value unchanged
            value = it->value;
        }
        
        add_item_tag( 0, it->offset-d_offset_shift, it->key, value, it->srcid );
    }
}

