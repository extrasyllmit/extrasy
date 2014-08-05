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
 * Copyright 2005,2006,2012 Free Software Foundation, Inc.
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

#ifndef INCLUDED_DIGITAL_LL_FRAMER_SINK_1_H
#define INCLUDED_DIGITAL_LL_FRAMER_SINK_1_H

#include <digital_ll_api.h>
#include <gr_sync_block.h>
#include <gr_msg_queue.h>
#include <digital_ll_timestamp.h>
#include <digital_ll_context_tag_manager.h>
class digital_ll_framer_sink_1;
typedef boost::shared_ptr<digital_ll_framer_sink_1> digital_ll_framer_sink_1_sptr;

DIGITAL_LL_API digital_ll_framer_sink_1_sptr
digital_ll_make_framer_sink_1(gr_msg_queue_sptr packet_queue,
		gr_msg_queue_sptr time_queue,
		gr_msg_queue_sptr chan_queue);

/*!
 * \brief Given a stream of bits and access_code flags, assemble packets.
 * \ingroup sink_blk
 *
 * input: stream of bytes from gr_correlate_access_code_bb
 * output: none. Pushes assembled packet into target queue
 *
 * The framer expects a fixed length header of 2 16-bit shorts
 * containing the payload length, followed by the payload. If the
 * 2 16-bit shorts are not identical, this packet is ignored. Better
 * algs are welcome.
 *
 * The input data consists of bytes that have two bits used.
 * Bit 0, the LSB, contains the data bit.
 * Bit 1 if set, indicates that the corresponding bit is the
 * the first bit of the packet. That is, this bit is the first
 * one after the access code.
 */
class DIGITAL_LL_API digital_ll_framer_sink_1 : public gr_sync_block
{
  friend DIGITAL_LL_API digital_ll_framer_sink_1_sptr
    digital_ll_make_framer_sink_1(gr_msg_queue_sptr packet_queue,
    		gr_msg_queue_sptr time_queue,
    		gr_msg_queue_sptr chan_queue);

 private:

  digital_ll_context_tag_manager d_tag_manager;

  enum state_t {STATE_SYNC_SEARCH, STATE_HAVE_SYNC, STATE_HAVE_HEADER};

  static const int MAX_PKT_LEN    = 4096;
  static const int HEADERBITLEN   = 32;

  gr_msg_queue_sptr  d_packet_queue;		// where to send the packet when received
  gr_msg_queue_sptr  d_time_queue;		// where to send the packet timestamp when received
  gr_msg_queue_sptr  d_chan_queue;		// where to send the packet channel when received
  state_t            d_state;
  unsigned int       d_header;			// header bits
  int		     d_headerbitlen_cnt;	// how many so far

  unsigned char      d_packet[MAX_PKT_LEN];	// assembled payload
  unsigned char	     d_packet_byte;		// byte being assembled
  int		     d_packet_byte_index;	// which bit of d_packet_byte we're working on
  int 		     d_packetlen;		// length of packet
  int                d_packet_whitener_offset;  // offset into whitener string to use
  int		     d_packetlen_cnt;		// how many so far

  int64_t d_sync_ind;
  digital_ll_timestamp d_sync_timestamp;
  int d_sync_channel;

  digital_ll_timestamp d_timestamp;
  int64_t d_timestamp_sample;
  double d_samp_rate;

  std::vector<gr_tag_t> d_tags;
  std::vector<gr_tag_t> d_time_tags;
  std::vector<gr_tag_t> d_rate_tags;

  std::vector<gr_tag_t>::iterator d_time_itr;
  std::vector<gr_tag_t>::iterator d_rate_itr;

 protected:
  digital_ll_framer_sink_1(gr_msg_queue_sptr packet_queue,
			gr_msg_queue_sptr time_queue,
			gr_msg_queue_sptr chan_queue);

  void enter_search();
  void enter_have_sync();
  void enter_have_header(int payload_len, int whitener_offset);

  bool header_ok()
  {
    // confirm that two copies of header info are identical
    return ((d_header >> 16) ^ (d_header & 0xffff)) == 0;
  }

  void header_payload(int *len, int *offset)
  {
    // header consists of two 16-bit shorts in network byte order
    // payload length is lower 12 bits
    // whitener offset is upper 4 bits
    *len = (d_header >> 16) & 0x0fff;
    *offset = (d_header >> 28) & 0x000f;
  }

 public:
  ~digital_ll_framer_sink_1();

  int work(int noutput_items,
	   gr_vector_const_void_star &input_items,
	   gr_vector_void_star &output_items);
};

#endif /* INCLUDED_DIGITAL_LL_FRAMER_SINK_1_H */
