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
 * Copyright 2004,2006,2010,2012 Free Software Foundation, Inc.
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

#include <digital_ll_framer_sink_1.h>
#include <gr_io_signature.h>
#include <cstdio>
#include <stdexcept>
#include <string.h>
#include <digital_ll_context_tag_manager.h>



#define VERBOSE 0


inline void
digital_ll_framer_sink_1::enter_search()
{
  if (VERBOSE)
    fprintf(stderr, "@ enter_search\n");

  d_state = STATE_SYNC_SEARCH;
  d_sync_ind = -1;
}

inline void
digital_ll_framer_sink_1::enter_have_sync()
{
  if (VERBOSE)
    fprintf(stderr, "@ enter_have_sync\n");

  while((d_time_itr != d_time_tags.end()) && (d_sync_ind >= d_time_itr->offset))
  {
	  d_timestamp_sample = d_time_itr->offset;
	  d_timestamp = digital_ll_timestamp( pmt::pmt_to_uint64(pmt::pmt_tuple_ref(d_time_itr->value,0)),
	    pmt::pmt_to_double(pmt::pmt_tuple_ref(d_time_itr->value,1)));
      d_time_itr++;
  }
  while((d_rate_itr != d_rate_tags.end()) && (d_sync_ind >= d_rate_itr->offset))
  {
	  //fprintf(stderr, "assigning sample rate at offset: %ld\n", d_rate_itr->offset);
	  if(pmt::pmt_is_tuple(d_rate_itr->value))
	  {
		  d_samp_rate = pmt::pmt_to_double(pmt::pmt_tuple_ref(d_rate_itr->value,0));
	  }
	  else
	  {
		  d_samp_rate = pmt::pmt_to_double(d_rate_itr->value);
	  }
//	  fprintf(stderr, "samp rate now set to %f at offset %lu\n",d_samp_rate, d_rate_itr->offset);
	  d_rate_itr++;
  }

  // store timestamp associated with sync
  d_sync_timestamp = d_timestamp + (d_sync_ind-d_timestamp_sample)/d_samp_rate;
  std::vector<gr_tag_t> context_tags;
  context_tags = d_tag_manager.get_latest_context_tags(d_sync_ind);

  if( !(context_tags.empty()))
  {
	  d_sync_channel = pmt::pmt_to_long(context_tags[0].value);
//	  fprintf(stderr, "framer sink found tag offset %ld, channel %ld  for sync ind %ld\n",
//	  			  context_tags[0].offset, d_sync_channel, d_sync_ind);
  }
  else
  {
	  d_sync_channel = 0;
  }

  if (VERBOSE)
  {
	  fprintf(stdout, "sync found at ind %ld\n", d_sync_ind);
	  fprintf(stdout, "timestamp reference offset: %ld, time %lu + %f\n",
			  d_timestamp_sample,d_timestamp.int_s(),d_timestamp.frac_s());
	  fprintf(stdout, "samp_rate is %f\n", d_samp_rate);
	  fprintf(stdout, "timestamp is %lu + %f \n",
			  d_sync_timestamp.int_s(), d_sync_timestamp.frac_s());
  }
  d_state = STATE_HAVE_SYNC;
  d_header = 0;
  d_headerbitlen_cnt = 0;
}

inline void
digital_ll_framer_sink_1::enter_have_header(int payload_len,
					 int whitener_offset)
{
  if (VERBOSE)
    fprintf(stderr, "@ enter_have_header (payload_len = %d) (offset = %d)\n",
	    payload_len, whitener_offset);

  d_state = STATE_HAVE_HEADER;
  d_packetlen = payload_len;
  d_packet_whitener_offset = whitener_offset;
  d_packetlen_cnt = 0;
  d_packet_byte = 0;
  d_packet_byte_index = 0;
}

digital_ll_framer_sink_1_sptr
digital_ll_make_framer_sink_1(gr_msg_queue_sptr packet_queue,
		gr_msg_queue_sptr time_queue,
		gr_msg_queue_sptr chan_queue)
{
  return gnuradio::get_initial_sptr(new digital_ll_framer_sink_1(packet_queue, time_queue, chan_queue));
}


digital_ll_framer_sink_1::digital_ll_framer_sink_1(gr_msg_queue_sptr packet_queue,
		gr_msg_queue_sptr time_queue,
		gr_msg_queue_sptr chan_queue)
  : gr_sync_block ("framer_sink_1",
		   gr_make_io_signature (1, 1, sizeof(unsigned char)),
		   gr_make_io_signature (0, 0, 0)),
    d_packet_queue(packet_queue),
    d_time_queue(time_queue),
    d_chan_queue(chan_queue)
{
  enter_search();

  // initialize timestamp and timestamp sample
  d_timestamp_sample = 0;
  d_timestamp = digital_ll_timestamp(0.0);

  std::vector<std::string> context_keys;
  context_keys.push_back("dig_chan");
  d_tag_manager = digital_ll_context_tag_manager(context_keys);

}

digital_ll_framer_sink_1::~digital_ll_framer_sink_1 ()
{
}

int
digital_ll_framer_sink_1::work (int noutput_items,
			     gr_vector_const_void_star &input_items,
			     gr_vector_void_star &output_items)
{
  const unsigned char *in = (const unsigned char *) input_items[0];
  int count=0;

  // check for new timestamp updates
  std::vector<gr_tag_t> rtags;
  pmt::pmt_t val;

  uint64_t abs_N, end_N;
  abs_N = nitems_read(0);
  end_N = abs_N + (uint64_t)(noutput_items);

  d_tags.clear();
  d_time_tags.clear();
  d_rate_tags.clear();
//  d_chan_tags.clear();

  std::vector<gr_tag_t>::iterator t;

  get_tags_in_range(d_tags, 0, abs_N, end_N);

  for(t = d_tags.begin(); t != d_tags.end(); t++) {

		if ( pmt::pmt_symbol_to_string(t->key).compare("rx_time") ==0)
		{
			d_time_tags.push_back(*t);
//	    	fprintf(stderr,"found rx_time tag at offset %lu, time %lu + %f\n",t->offset,
//	          pmt::pmt_to_uint64(pmt::pmt_tuple_ref(t->value,0)), pmt::pmt_to_double(pmt::pmt_tuple_ref(t->value,1)));
	//    	d_timestamp_sample = t->offset;
	//
	//    	d_timestamp_int_secs = pmt::pmt_to_uint64(pmt::pmt_tuple_ref(t->value,0));
	//    	d_timestamp_frac_secs = pmt::pmt_to_double(pmt::pmt_tuple_ref(t->value,1));

		 }

		if ( pmt::pmt_symbol_to_string(t->key).compare("rx_rate") ==0)
		{
			d_rate_tags.push_back(*t);
//	    	fprintf(stderr,"found rx_rate tag at offset %lu, value %f\n",t->offset,pmt::pmt_to_double(t->value));

	//    	d_timestamp_sample = t->offset;
	//    	d_samp_rate = pmt::pmt_to_double(t->value);
		 }

		if ( pmt::pmt_symbol_to_string(t->key).compare("dig_chan") ==0)
		{
			d_tag_manager.add_context_tag(*t);
//			fprintf(stderr,"framer sink found dig_chan tag at offset %lu, value %ld\n",t->offset,pmt::pmt_to_long(t->value));
		}

	}

  d_time_itr = d_time_tags.begin();
  d_rate_itr = d_rate_tags.begin();


  if (VERBOSE)
    fprintf(stderr,">>> Entering state machine\n");

  while (count < noutput_items){
    switch(d_state) {

    case STATE_SYNC_SEARCH:    // Look for flag indicating beginning of pkt
      if (VERBOSE)
	fprintf(stderr,"SYNC Search, noutput=%d\n", noutput_items);

      while (count < noutput_items) {
	if (in[count] & 0x2){  // Found it, set up for header decode
		d_sync_ind = count + this->nitems_read(0);
	  enter_have_sync();
	  break;
	}
	count++;
      }
      break;

    case STATE_HAVE_SYNC:
      if (VERBOSE)
	fprintf(stderr,"Header Search bitcnt=%d, header=0x%08x\n",
		d_headerbitlen_cnt, d_header);

      while (count < noutput_items) {	// Shift bits one at a time into header
	d_header = (d_header << 1) | (in[count++] & 0x1);
	if (++d_headerbitlen_cnt == HEADERBITLEN) {

	  if (VERBOSE)
	    fprintf(stderr, "got header: 0x%08x\n", d_header);

	  // we have a full header, check to see if it has been received properly
	  if (header_ok()){
	    int payload_len;
	    int whitener_offset;
	    header_payload(&payload_len, &whitener_offset);
	    enter_have_header(payload_len, whitener_offset);

	    if (d_packetlen == 0){	    // check for zero-length payload
	      // build a zero-length message
	      // NOTE: passing header field as arg1 is not scalable
	      gr_message_sptr msg =
		gr_make_message(0, d_packet_whitener_offset, 0, 0);

	      d_packet_queue->insert_tail(msg);		// send it
	      msg.reset();  				// free it up

	      // pass up timestamp
	      msg = gr_make_message(0,d_sync_timestamp.int_s(),d_sync_timestamp.frac_s(),0);
	      d_time_queue->insert_tail(msg);		// send it
		  msg.reset();  				// free it up

		  // pass up channel
		  msg = gr_make_message(0,d_sync_channel,0,0);
		  d_chan_queue->insert_tail(msg);		// send it
		  msg.reset();  				// free it up
//		  fprintf(stderr,"framer sink found packet at offset %ld, channel %ld\n",
//				  d_sync_ind,d_sync_channel);

	      enter_search();
	    }
	  }
	  else
	    enter_search();				// bad header
	  break;					// we're in a new state
	}
      }
      break;

    case STATE_HAVE_HEADER:
      if (VERBOSE)
	fprintf(stderr,"Packet Build\n");

      while (count < noutput_items) {   // shift bits into bytes of packet one at a time
	d_packet_byte = (d_packet_byte << 1) | (in[count++] & 0x1);
	if (d_packet_byte_index++ == 7) {	  	// byte is full so move to next byte
	  d_packet[d_packetlen_cnt++] = d_packet_byte;
	  d_packet_byte_index = 0;

	  if (d_packetlen_cnt == d_packetlen){		// packet is filled

	    // build a message
	    // NOTE: passing header field as arg1 is not scalable
	    gr_message_sptr msg =
	      gr_make_message(0, d_packet_whitener_offset, 0, d_packetlen_cnt);
	    memcpy(msg->msg(), d_packet, d_packetlen_cnt);

	    d_packet_queue->insert_tail(msg);		// send it
	    msg.reset();  				// free it up

	      // pass up timestamp
	    msg = gr_make_message(0,d_sync_timestamp.int_s(),d_sync_timestamp.frac_s(),0);
	    d_time_queue->insert_tail(msg);		// send it
	    msg.reset();  				// free it up

//	    fprintf(stderr,"framer sink found packet at offset %ld, channel %ld\n",
//	    				  d_sync_ind,d_sync_channel);

        // pass up channel
		msg = gr_make_message(0,d_sync_channel,0,0);
		d_chan_queue->insert_tail(msg);		// send it
		msg.reset();  				// free it up

	    enter_search();
	    break;
	  }
	}
      }
      break;

    default:
      assert(0);

    } // switch

  }

  if(d_time_tags.size() > 0)
  {
	  for( int k=0; k< d_time_tags.size(); k++)
	  {
		  //store off the latest value of time tag for which the associated sample has
		  //been consumed
		  if (noutput_items + nitems_read(0) > d_time_tags[k].offset)
		  {
			  d_timestamp_sample = d_time_tags[k].offset;
			  d_timestamp = digital_ll_timestamp( pmt::pmt_to_uint64(pmt::pmt_tuple_ref(d_time_tags[k].value,0)),
			  	    pmt::pmt_to_double(pmt::pmt_tuple_ref(d_time_tags[k].value,1)));
		  }
	  }

//    fprintf(stderr, "assigning timestamp reference at offset: %ld, time %lu + %f\n",
//    		d_timestamp_sample,d_timestamp_int_secs,d_timestamp_frac_secs);
  } 
  if(d_rate_tags.size() > 0)
  {
	  for( int k=0; k< d_rate_tags.size(); k++)
	  {
		  if (noutput_items + nitems_read(0) > d_rate_tags[k].offset)
		  {
			  d_samp_rate = pmt::pmt_to_double(d_rate_tags[k].value);
		  }
	  }
    //fprintf(stderr, "assigning sample rate %f at offset: %ld\n", d_samp_rate, d_timestamp_sample);

  } 
      
  return noutput_items;
}
