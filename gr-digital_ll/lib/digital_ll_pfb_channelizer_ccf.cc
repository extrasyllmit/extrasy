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
 * Copyright 2009,2010 Free Software Foundation, Inc.
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

#include <digital_ll_pfb_channelizer_ccf.h>
#include <gr_fir_ccf.h>
#include <gr_fir_util.h>
#include <gri_fft.h>
#include <gr_io_signature.h>
#include <cstdio>
#include <cstring>

digital_ll_pfb_channelizer_ccf_sptr digital_ll_make_pfb_channelizer_ccf (unsigned int numchans,
							 const std::vector<float> &taps,
							 float oversample_rate)
{
  return gnuradio::get_initial_sptr(new digital_ll_pfb_channelizer_ccf (numchans, taps,
								  oversample_rate));
}


digital_ll_pfb_channelizer_ccf::digital_ll_pfb_channelizer_ccf (unsigned int numchans,
						const std::vector<float> &taps,
						float oversample_rate)
  : gr_block ("pfb_channelizer_ccf",
	      gr_make_io_signature (numchans, numchans, sizeof(gr_complex)),
	      gr_make_io_signature (1, numchans, sizeof(gr_complex))),
    d_updated (false), d_numchans(numchans), d_oversample_rate(oversample_rate)
{
  // The over sampling rate must be rationally related to the number of channels
  // in that it must be N/i for i in [1,N], which gives an outputsample rate
  // of [fs/N, fs] where fs is the input sample rate.
  // This tests the specified input sample rate to see if it conforms to this
  // requirement within a few significant figures.
  double intp = 0;
  double fltp = modf(numchans / oversample_rate, &intp);
  if(fltp != 0.0)
    throw std::invalid_argument("digital_ll_pfb_channelizer: oversample rate must be N/i for i in [1, N]");

  // ==== Code Modified by Thomas Stahlbuhk - MIT Lincoln Laboratory in February 2013 ======
  // The following code changes have been instigated to fix an observed
  // all-to-all tag propagation problem in gr_block_executor.cc by which
  // the offset and (Craig's implemented) UHD rate downcoversion editor
  // are executed twice from input to output propagation around this block.
  // The code will comment out setting the relative rate and will instead
  // elect to not propagate tags automatically but instead generate tags
  // at the right offset and (for UHD rate tags) rate anew.
  
  // set_relative_rate(1.0/intp);  // Code commented out by Thomas Feb 14, 2012
                                   // All other code is new and has been added by Thomas
  
  set_tag_propagation_policy( TPP_DONT );

  // ==== End Code Modifications by Thomas Stahlbuhk =======================================
  
  d_filters = std::vector<gr_fir_ccf*>(d_numchans);
  d_channel_map.resize(d_numchans);

  // Create an FIR filter for each channel and zero out the taps
  std::vector<float> vtaps(0, d_numchans);
  for(unsigned int i = 0; i < d_numchans; i++) {
    d_filters[i] = gr_fir_util::create_gr_fir_ccf(vtaps);
    d_channel_map[i] = i;
  }

  // Now, actually set the filters' taps
  set_taps(taps);

  // Create the FFT to handle the output de-spinning of the channels
  d_fft = new gri_fft_complex (d_numchans, false);

  // Although the filters change, we use this look up table
  // to set the index of the FFT input buffer, which equivalently
  // performs the FFT shift operation on every other turn.
  d_rate_ratio = (int)rintf(d_numchans / d_oversample_rate);
  d_idxlut = new int[d_numchans];
  for(unsigned int i = 0; i < d_numchans; i++) {
    d_idxlut[i] = d_numchans - ((i + d_rate_ratio) % d_numchans) - 1;
  }

  // Calculate the number of filtering rounds to do to evenly
  // align the input vectors with the output channels
  d_output_multiple = 1;
  while((d_output_multiple * d_rate_ratio) % d_numchans != 0)
    d_output_multiple++;
  set_output_multiple(d_output_multiple);
}

digital_ll_pfb_channelizer_ccf::~digital_ll_pfb_channelizer_ccf ()
{
  delete d_fft;
  delete [] d_idxlut;

  for(unsigned int i = 0; i < d_numchans; i++) {
    delete d_filters[i];
  }
}

void
digital_ll_pfb_channelizer_ccf::set_taps (const std::vector<float> &taps)
{
  gruel::scoped_lock guard(d_mutex);
  unsigned int i,j;

  unsigned int ntaps = taps.size();
  d_taps_per_filter = (unsigned int)ceil((double)ntaps/(double)d_numchans);

  // Create d_numchan vectors to store each channel's taps
  d_taps.resize(d_numchans);

  // Make a vector of the taps plus fill it out with 0's to fill
  // each polyphase filter with exactly d_taps_per_filter
  std::vector<float> tmp_taps;
  tmp_taps = taps;
  while((float)(tmp_taps.size()) < d_numchans*d_taps_per_filter) {
    tmp_taps.push_back(0.0);
  }

  // Partition the filter
  for(i = 0; i < d_numchans; i++) {
    // Each channel uses all d_taps_per_filter with 0's if not enough taps to fill out
    d_taps[i] = std::vector<float>(d_taps_per_filter, 0);
    for(j = 0; j < d_taps_per_filter; j++) {
      d_taps[i][j] = tmp_taps[i + j*d_numchans];  // add taps to channels in reverse order
    }

    // Build a filter for each channel and add it's taps to it
    d_filters[i]->set_taps(d_taps[i]);
  }

  // Set the history to ensure enough input items for each filter
  set_history (d_taps_per_filter+1);

  d_updated = true;
}

void
digital_ll_pfb_channelizer_ccf::print_taps()
{
  unsigned int i, j;
  for(i = 0; i < d_numchans; i++) {
    printf("filter[%d]: [", i);
    for(j = 0; j < d_taps_per_filter; j++) {
      printf(" %.4e", d_taps[i][j]);
    }
    printf("]\n\n");
  }
}

std::vector< std::vector<float> >
digital_ll_pfb_channelizer_ccf::taps() const
{
  return d_taps;
}

void
digital_ll_pfb_channelizer_ccf::set_channel_map(const std::vector<int> &map)
{
  gruel::scoped_lock guard(d_mutex);

  if(map.size() > 0) {
    unsigned int max = (unsigned int)*std::max_element(map.begin(), map.end());
    unsigned int min = (unsigned int)*std::min_element(map.begin(), map.end());
    if((max >= d_numchans) || (min < 0)) {
      throw std::invalid_argument("digital_ll_pfb_channelizer_ccf::set_channel_map: map range out of bounds.\n");
    }
    d_channel_map = map;
  }
}

std::vector<int>
digital_ll_pfb_channelizer_ccf::channel_map() const
{
  return d_channel_map;
}


int
digital_ll_pfb_channelizer_ccf::general_work (int noutput_items,
				      gr_vector_int &ninput_items,
				      gr_vector_const_void_star &input_items,
				      gr_vector_void_star &output_items)
{
  gruel::scoped_lock guard(d_mutex);

  gr_complex *in = (gr_complex *) input_items[0];
  gr_complex *out = (gr_complex *) output_items[0];

  if (d_updated) {
    d_updated = false;
    return 0;		     // history requirements may have changed.
  }

  size_t noutputs = output_items.size();

  int n=1, i=-1, j=0, oo=0, last;
  int toconsume = (int)rintf(noutput_items/d_oversample_rate);
  while(n <= toconsume) {
    j = 0;
    i = (i + d_rate_ratio) % d_numchans;
    last = i;
    while(i >= 0) {
      in = (gr_complex*)input_items[j];
      d_fft->get_inbuf()[d_idxlut[j]] = d_filters[i]->filter(&in[n]);
      j++;
      i--;
    }

    i = d_numchans-1;
    while(i > last) {
      in = (gr_complex*)input_items[j];
      d_fft->get_inbuf()[d_idxlut[j]] = d_filters[i]->filter(&in[n-1]);
      j++;
      i--;
    }

    n += (i+d_rate_ratio) >= (int)d_numchans;

    // despin through FFT
    d_fft->execute();

    // Send to output channels
    for(unsigned int nn = 0; nn < noutputs; nn++) {
      out = (gr_complex*)output_items[nn];
      out[oo] = d_fft->get_outbuf()[d_channel_map[nn]];
    }
    oo++;
  }

  // ==== Code Modified by Thomas Stahlbuhk - MIT Lincoln Laboratory in February 2013 ======
    
  double rrate = 1.0/d_numchans;   // the sample rate conversion from input to output
  rrate = 1.0; // This is to fix a bug that exists in how GNU Radio propagates tags
               // for some reason something before this general_work function handles
               // rate conversion before us. So all we'll do is send input to outputs
               // FIXME - fix me - broken
  
  // Get the input tags.
  std::vector<gr_tag_t> tags;
  const uint64_t nread = this->nitems_read(0);                    // number of items read
  const size_t ninput_items0 = toconsume;                         // Number of input we'll consume
  this->get_tags_in_range(tags, 0, nread, nread + ninput_items0); // read the tags
  
  // Loop over the tags changing their offset by 1.0/d_numchans. If we encounter a rate
  // tag from the UHD, multiply the rate by 1.0/d_numchans as well.
  std::vector<gr_tag_t>::iterator it;
  pmt::pmt_t key;      // The key of the new tag
  pmt::pmt_t value;    // The value of the new tag
  uint64_t   offset;   // The offset of the new tag
  double     old_rate; // The rate of the old tag
  
  for( it = tags.begin(); it != tags.end(); it++ )
  {
    // Set the key/offset/values of the new tag
    offset = it->offset * rrate;
    key    = it->key;
    if( pmt::pmt_symbol_to_string(it->key).compare("rx_rate") == 0 )
    {
      old_rate = pmt::pmt_to_double(it->value);
      value    = pmt::pmt_from_double(old_rate*rrate);
    }
    else
      value = it->value;
    
    // Propagate our new tag to ALL of the outputs
    // Create a tag id
    pmt::pmt_t srcid = it->srcid;
    for( uint64_t i = 0; i < d_numchans; i++ )
      add_item_tag( i, offset, key, value, srcid );
  }
  
  // ==== End Code Modifications by Thomas Stahlbuhk =======================================

  consume_each(toconsume);
  return noutput_items;
}
