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
#include <digital_ll_selector.h>

static pmt::pmt_t RATE_SYM = pmt::pmt_string_to_symbol("rx_rate");
static pmt::pmt_t TIME_SYM = pmt::pmt_string_to_symbol("rx_time");
static pmt::pmt_t CHAN_SYM = pmt::pmt_string_to_symbol("dig_chan");
static pmt::pmt_t ID_SYM = pmt::pmt_string_to_symbol("digital_ll_selector");

using boost::get;

digital_ll_selector_sptr
digital_ll_make_selector (int numchans, int input_index, int output_index)
{
	return digital_ll_selector_sptr (new digital_ll_selector (numchans, input_index, output_index));
}


digital_ll_selector::digital_ll_selector (int numchans, int input_index, int output_index)
	: gr_sync_block ("selector",
		gr_make_io_signature (numchans, numchans, sizeof (gr_complex)),
		gr_make_io_signature (1, 1, sizeof (gr_complex)))
{
    // Initialize Variables
    d_input_index  = input_index;
    d_output_index = output_index;
    
    d_offset_save      = -1;   // Let's us know that no tag has been found yet
	d_time_full_s_save = 0;
	d_time_frac_s_save = 0.0;
	d_rate_save        = 0.0;
	d_num_chans        = numchans;
	d_ntags_proc      = 0;
	//last_print         = -1000000000;  
}


digital_ll_selector::~digital_ll_selector ()
{
}

void
digital_ll_selector::set_input_index( int input_index )
{
    // Manually change the input index with a Python call.

    assert( input_index < d_num_chans );
    d_input_index = input_index;
}

int
digital_ll_selector::work (int noutput_items,
			gr_vector_const_void_star &input_items,
			gr_vector_void_star &output_items)
{
	const gr_complex *in = (const gr_complex *) input_items[d_input_index];
	gr_complex *out = (gr_complex *) output_items[0];

    // Get the UHD tags that we are interested in
    uint64_t offset;
    offset = get_tags( noutput_items );

    // Find the most recent tag
    int tag_ind;
    tag_ind = find_most_recent_tag( offset );
    
    // Get the time corresponding to the most recent tag and increment it by
    // the offsets progression
    time_tuple gps_time;
    if( tag_ind != -1 )
    {
        gps_time = boost::make_tuple( get<1>(d_tag_tuples[tag_ind]), get<2>(d_tag_tuples[tag_ind]) );
        gps_time = increment_time_tuple( gps_time, offset - get<0>(d_tag_tuples[tag_ind]), get<3>(d_tag_tuples[tag_ind]) );
    }
    
    //if( offset - last_print > 1000000)
    //{
    //    std::cout << "Offset: " << offset << "\tGPS time: " << get<0>(gps_time) << " + " << get<1>(gps_time) << "\n";
    //   last_print = offset;
    //}
    

    // output channel tag for first iteration
	if(this->nitems_written(d_output_index)==0)
	{
		// add channel tag
		gr_tag_t chan_tag;
		chan_tag.key = CHAN_SYM;
		chan_tag.offset = offset;
		chan_tag.srcid = ID_SYM;
		chan_tag.value = pmt::pmt_from_long(d_input_index);
		add_item_tag(d_output_index,chan_tag);
//		fprintf(stderr, "Selector adding channel tag to stream for channel %d at offset %ld, time %lu,%.10f\n",
//				d_input_index, offset, get<0>(gps_time), get<1>(gps_time));

	}


	// =========================   Copy the input to the output   ========================================
	for( int i = 0; i < noutput_items; i++ )
	{
	    out[i] = in[i];
	    
	    //======================= Figuring out the GPS Time for this Offset Sample =======================
	    if( tag_ind != -1 )
	    {
	        // Increment the offset. If we reach a new tag in d_tag_tuples
	        // then set that to be out new tag index
	        offset++;       // increment the offset counter
	        if( tag_ind != d_tag_tuples.size()-1 && offset >= get<0>(d_tag_tuples[tag_ind+1]) )
	        {
	        	//std::cout << "Getting new tag " << tag_ind << "\n";
	            tag_ind++;   // increment the tag index
	            gps_time = boost::make_tuple( get<1>(d_tag_tuples[tag_ind]), get<2>(d_tag_tuples[tag_ind]) );
	            gps_time = increment_time_tuple( gps_time, offset - get<0>(d_tag_tuples[tag_ind]), get<3>(d_tag_tuples[tag_ind]) ); // This is probably unnecessary
	        }
	        else
	        {
	            gps_time = increment_time_tuple( gps_time, 1, get<3>(d_tag_tuples[tag_ind]) );
	        }
	        
	        //===================== Figuring out what slot to be on in frame schedule =========================
	        
	        // If we don't have a frame schedule search for one.
	        if( !d_frame_schedule.size() )
	            get_next_schedule( gps_time );



	        // If we now have a frame schedule determine which slot/channel we should be on.
	        if( d_frame_schedule.size() )
	        {
	            if( compare_time_tuples( gps_time, get<0>(d_frame_schedule[0]) ) == -1 )
	            {

	                //std::cout << "Moving to new slot at sample: " << offset << " and time " << get<0>(gps_time) << " + " << get<1>(gps_time) << " with rate " << get<3>(d_tag_tuples[tag_ind]) << "\n";
	            
	                // If this is not the last element in the schedule (where the last element
	                // indicates the end of the frame) set the channel to the new frequency
	                if( d_frame_schedule.size() != 1 )
	                {

	                	// only add new tag for change in input index
	                	if(d_input_index != get<1>(d_frame_schedule[0]))
	                	{
	                		// add channel tag
							gr_tag_t chan_tag;
							chan_tag.key = CHAN_SYM;
							chan_tag.offset = offset;
							chan_tag.srcid = ID_SYM;
							chan_tag.value = pmt::pmt_from_long(get<1>(d_frame_schedule[0]));
							add_item_tag(d_output_index,chan_tag);
//							fprintf(stderr, "Selector adding channel tag to stream for channel %d at offset %ld, time %lu,%.10f\n",
//									get<1>(d_frame_schedule[0]), offset, get<0>(gps_time), get<1>(gps_time));
	                	}


	                    set_input_index( get<1>(d_frame_schedule[0]) );
	                    if( d_input_index > d_num_chans )
	                    	std::cout << "ERROR: the requested channel number is " << d_input_index
	                    	 	<< " but the channelizer has only " << d_num_chans << "!\n";
	                    in = (const gr_complex *) input_items[d_input_index];


	                }
	                    
	                // Pop the first element off of the list
	                d_frame_schedule.pop_front();
	            }
	        }
	        else if (d_input_index != d_beacon_channel)
	        {
	            // Return to the beacon channel
                set_input_index( d_beacon_channel );

                // add channel tag
				gr_tag_t chan_tag;
				chan_tag.key = CHAN_SYM;
				chan_tag.offset = offset;
				chan_tag.srcid = ID_SYM;
				chan_tag.value = pmt::pmt_from_long(d_beacon_channel);
				add_item_tag(d_output_index,chan_tag);
//				fprintf(stderr, "Selector adding channel tag to stream for channel %d at offset %ld, time %lu,%.10f\n",
//						d_beacon_channel, offset, get<0>(gps_time), get<1>(gps_time));

	        }   
	    }
	}
	// ====================== End for loop ===============================================================

    // Save the last elements of d_rate_tags for next call to work function
    save_last();

	// Tell runtime system how many output items we produced.
	return noutput_items;
}

/*
Get the sorted tags and add them to the d_tag_tuples
*/
uint64_t
digital_ll_selector::get_tags( int noutput_items )
{
    // This function looks for all UHD tags (both time and rate) and sorts
    // them by their sample time offset. It then saves the tag information
    // in a vector of tag tuples which can be used by the other functions.

    // Clear the old tags
    d_time_tags.clear();
    d_rate_tags.clear();
    d_tag_tuples.clear();
    
    // Get the tags from input, so that the GPS time may be matched to the
    // samples streaming in.
    std::vector<gr_tag_t> tags;
    const uint64_t nread = this->nitems_read(d_input_index); //number of items read
    const size_t ninput_items = noutput_items; //assumption for sync block
    this->get_tags_in_range(tags, d_input_index, nread, nread+ninput_items); // read the tags 
    
    // Search for UHD rx_time tags (which have been conveniently defined above)
    std::vector<gr_tag_t>::iterator it;
    for( it = tags.begin(); it != tags.end(); it++ )
    {
        if(it->key == RATE_SYM)
        {
        
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
        else if( it->key == TIME_SYM )
        {
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
    }
    
    // Sort the tags using STL functionality
    std::sort(d_time_tags.begin(), d_time_tags.end(), gr_tag_t::offset_compare);
    std::sort(d_rate_tags.begin(), d_rate_tags.end(), gr_tag_t::offset_compare);
    
    // If the last recorded tuple is recorded before most recent found tag, record it to
    // the tuple vector
    if( d_time_tags.empty() || d_time_tags.begin()->offset >= d_offset_save )
    {
        d_tag_tuples.push_back(boost::make_tuple( d_offset_save, d_time_full_s_save, d_time_frac_s_save, d_rate_save ) );
    }
    
    // Store the rest of the tags as tuples
    int64_t offset;
    int64_t time_full_s;
    double  time_frac_s;
    double  rate;
    
    for( int k = 0; k < d_time_tags.size(); k++ )
    {
        offset      = d_time_tags[k].offset;
        time_full_s = pmt::pmt_to_uint64(pmt::pmt_tuple_ref(d_time_tags[k].value,0));
        time_frac_s = pmt::pmt_to_double(pmt::pmt_tuple_ref(d_time_tags[k].value,1));
        rate        = pmt::pmt_to_double(d_rate_tags[k].value);
        
        //std::cout << "Found a tag for offset " << offset <<  " and time " << time_full_s << " + " << time_frac_s << "\tRate " << rate << "\n";
        
        d_tag_tuples.push_back( boost::make_tuple( offset, time_full_s, time_frac_s, rate ) );
    }
    
    return nread;
}

void
digital_ll_selector::save_last( )
{
    // save the last seen UHD gps (POSIX) time tag for the next time work
    // function is called.
    
    if( !d_tag_tuples.empty() )
    {
        d_offset_save      = get<0>(d_tag_tuples.back());
        d_time_full_s_save = get<1>(d_tag_tuples.back());
        d_time_frac_s_save = get<2>(d_tag_tuples.back());
        d_rate_save        = get<3>(d_tag_tuples.back());
    }
}

int
digital_ll_selector::find_most_recent_tag( uint64_t offset )
{
    // Find the most recent tag based off of offset.
    // This function assumes that d_tag_tuples is sorted by their
    // offset values from low to high.
    int most_recent = -1;
    for( int i = 0; i < d_tag_tuples.size(); i++ )
    {
        if( get<0>(d_tag_tuples[i]) < offset )
            most_recent = i;
    }
    
    return most_recent;
}

time_tuple
digital_ll_selector::increment_time_tuple( time_tuple gps_time, int64_t increment, double rate )
{
    // Increment the time tuple (consisting of integer and fractional components)
    // by increment/rate (seconds). Returns time tuple.
    
    double fractpart, intpart;
    uint64_t carry_over;
    
    // Find out how much we will be incrementing the time by
    // storing it as an integer and fractional part
    fractpart = modf(double(increment)/rate , &intpart);
    
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

time_tuple
digital_ll_selector::advance_time_tuple( time_tuple gps_time, double seconds )
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

int
digital_ll_selector::compare_time_tuples( time_tuple tuple1, time_tuple tuple2 )
{
    // This function will compare two time tuples and tell (in int form)
    // which is the larger. The returned int should be interpretted as follows:
    //   -1 means first tuple is a later time (larger POSIX number)
    //    1 means second tuple is a later time (larger POSIX number)
    //    0 means the two tuples have the same POSIX time
    
    int decision;

    if( get<0>(tuple1) > get<0>(tuple2) )
        decision = -1;
    else if( get<0>(tuple1) < get<0>(tuple2) )
        decision = 1;
    else
    {
        // Integer components are the same. Look at number of fractional
        // seconds.
        if( get<1>(tuple1) > get<1>(tuple2) )
            decision = -1;
        else if( get<1>(tuple1) < get<1>(tuple2) )
            decision = 1;
        else
            decision = 0;
    }
    
    return decision;
}

void
digital_ll_selector::set_schedule( int int_s, double frac_s, double frame_length, const std::vector<double> slot_times, const std::vector<int> slot_chan_nums) 
{

    //std::cout << "Set schedule has been called!\n";
    
    // Create a time tuple for the frame's beginning
    time_tuple frame_start = boost::make_tuple( int_s, frac_s );

    // We have a new schedule. Find out where it begins in the list of frame schedules.
    // Note that this code assumes the d_frame_schedules are always sorted by their
    // frame_start fields (lowest to highest). Which (since we maintatin that order in this
    // function) will always be true.
    int pos = 0;
    for(int i = 0; i < d_frame_schedules.size(); i++ )
    {
        if( compare_time_tuples( frame_start, get<0>(d_frame_schedules[i]) ) == 1 )
            break; // We have found where to insert this frame in the vector
        else
            pos++;
    }
    
    //std::cout << "Inserting the new schedule at position: " << pos << "\n";
    
    // Make a frame schedule tuple and add it to our list of frame schedules
    frame_tuple new_frame = boost::make_tuple( frame_start, frame_length, slot_times, slot_chan_nums );
    if( pos < d_frame_schedules.size() )
        d_frame_schedules.insert( d_frame_schedules.begin() + pos, new_frame );
    else
        d_frame_schedules.push_back( new_frame );
   
   //std::cout << "The new schedule has " << get<2>(d_frame_schedules[pos]).size() << " elements with frame length " << frame_length << "\n";
        
   //std::cout << "Exiting set schedule\n";
}

int
digital_ll_selector::get_next_schedule( time_tuple current_gps_time )
{
    // This function will find which of the schedules in d_frame_schedules to get
    // and will then create a d_frame_schedule with the correct "updated" gps times.
    // This will allow us to continue using the same d_frame_schedule in sync over
    // and over again. (ie, it automatically extends the schedule for multiple frames).
    // We will return 1 if a new schedule is found or zero otherwise.
    
    // First find which schedule in d_frame_schedules is the one to use.
    // Remember that d_frame_schedules are stored in sorted order by gps_time
    int pos = -1;
    for( int i = 0; i < d_frame_schedules.size(); i++ )
    {
        if( compare_time_tuples( current_gps_time, get<0>(d_frame_schedules[i]) ) == 1 )
            break;
        else
            pos++;
    }

    // If pos still is -1, then we do not have a new schedule. Return 0.
    if( pos == -1 )
        return 0;
    else
    {
    
        //std::cout << "I am going to get a new schedule: " << pos << "!\n";
    
        // We have a new schedule to follow. We will need to setup a structure
        // in d_frame_schedule that is capable of being followed by the main code
        // (ie, it needs to have updated GPS times to reflect this in particular frame)
        
        assert( pos < d_frame_schedules.size() );
        
        // First clear out the d_frames_schedules of data that isn't necessary.
        if( pos != 0)
            d_frame_schedules.erase( d_frame_schedules.begin(), d_frame_schedules.begin() + pos );
        
        // Now the first element of d_frames_schedules contains the schedule we want.
        // We want to increment the frame_start field of d_frames_schedules[0] by X times
        // the frame_length field so that the result is the maximum value possible, but
        // still less than current_gps_time.
        time_tuple new_frame_start = get<0>(d_frame_schedules[0]);
        time_tuple candidate_new_frame_start = advance_time_tuple(get<0>(d_frame_schedules[0]), get<1>(d_frame_schedules[0]));
        while( compare_time_tuples( candidate_new_frame_start, current_gps_time ) == 1 )
        {
            new_frame_start = advance_time_tuple( new_frame_start, get<1>(d_frame_schedules[0]) );
            candidate_new_frame_start = advance_time_tuple( candidate_new_frame_start, get<1>(d_frame_schedules[0]) );
        }
        
        //std::cout << "My new frame start time will be: " << get<0>(new_frame_start) << " + " << get<1>(new_frame_start) << "\n";
        
        // At this point new_frame_start should tell us the new frame start that we will
        // want to use. Let's setup a d_frame_schedule deque that will be easy for the
        // main function to work with. This will basically consist of a list of gps
        // times and channels.
        d_frame_schedule.clear();
        time_tuple slot_time;
        for( int i = 0; i < get<2>(d_frame_schedules[0]).size(); i++ )
        {
            slot_time = advance_time_tuple( new_frame_start, get<2>(d_frame_schedules[0])[i] );
            d_frame_schedule.push_back( boost::make_tuple( slot_time, get<3>(d_frame_schedules[0])[i] ) );
        }
        // Don't forget to add a last element which will tell the work function code when it needs to
        // get a new slot schedule.
        slot_time = advance_time_tuple( new_frame_start, get<1>(d_frame_schedules[0]) );
        d_frame_schedule.push_back( boost::make_tuple( slot_time, 0 ) );
        
        //std::cout << "Updated the frame scheduler. Its size is: " << d_frame_schedule.size() << "\n";
        
        return 1;
    }

}

void
digital_ll_selector::set_beacon_channel( int beacon_channel )
{
    // This function sets the beacon channel to be a new provided channel.
    
    d_beacon_channel = beacon_channel;
}

void
digital_ll_selector::return_to_beacon_channel( )
{
    //This function should be called to return the channelizer to the
    // designated beacon channel. It clears out all receive schedules
    // and moves the channelizer to the beacon channel.

    // First clear out the frame schedules
    d_frame_schedules.clear();
    
    // Return to the beacon channel
    set_input_index( d_beacon_channel );
}


