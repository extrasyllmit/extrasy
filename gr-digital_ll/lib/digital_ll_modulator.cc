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
#include <digital_ll_modulator.h>
#include <iostream>

static pmt::pmt_t MODULATOR_SOB    = pmt::pmt_string_to_symbol("tx_new_channel");
static pmt::pmt_t NEW_CHANNEL_FLAG = pmt::pmt_string_to_symbol("tx_new_channel");


#define MAI_PAI 3.141592653589793116

using boost::get;

digital_ll_modulator_sptr
digital_ll_make_modulator (int num_chan, int current_chan)
{
	return digital_ll_modulator_sptr (new digital_ll_modulator (num_chan, current_chan));
}


digital_ll_modulator::digital_ll_modulator (int num_chan, int current_chan)
	: gr_sync_block ("modulator",
		gr_make_io_signature (1, 1, sizeof (gr_complex)),
		gr_make_io_signature (1, 1, sizeof (gr_complex)))
{
    d_num_chan = num_chan;
    switch_channels( current_chan );

}


digital_ll_modulator::~digital_ll_modulator ()
{
}


int
digital_ll_modulator::work (int noutput_items,
			gr_vector_const_void_star &input_items,
			gr_vector_void_star &output_items)
{
	const gr_complex *in = (const gr_complex *) input_items[0];
	gr_complex *out = (gr_complex *) output_items[0];
    
    // Get the offset
    uint64_t offset = this->nitems_read(0); //number of items read

    // Get the possible channel switching flags
	get_channel_tags( noutput_items );
    gr_complex mod;

    uint64_t channel_tags_pos = 0; // position in the channel tags
    uint64_t sob_tags_pos = 0;


    float current_val;
    float scalar=0.0;
    
    for( int i = 0; i < noutput_items; i++ )
    {
    
        // ===== Hanndle Tags ===================================
        // Check if we need to switch channels
        if( channel_tags_pos < d_channel_tags.size() && offset == get<0>(d_channel_tags[channel_tags_pos]) )
            switch_channels( get<1>(d_channel_tags[channel_tags_pos++]) );

        
        // ===== Hanndle Tags Complete ============================
        
        // Create the new modulation coefficient
        mod = gr_complex(
            cos( 2.0*MAI_PAI*offset*d_current_chan/d_num_chan ),   // real
            sin( 2.0*MAI_PAI*offset*d_current_chan/d_num_chan ) ); // imaginary
        
        // Perform the complex multiply and send it to output
        out[i] = in[i]*mod;
                
        // Increment the offset
        offset++;
        
    }

	// Tell runtime system how many output items we produced.
	return noutput_items;
}

void
digital_ll_modulator::get_channel_tags( int noutput_items )
{
    //Clear the channel tags
    d_channel_tags.clear();

    d_sob_offsets.clear();
    d_tags.clear();

    // Get the tags from input, so that the GPS time may be matched to the
    // samples streaming in.
    std::vector<gr_tag_t> tags;
    const uint64_t nread = this->nitems_read(0); //number of items read
    const size_t ninput_items = noutput_items; //assumption for sync block
    this->get_tags_in_range(tags, 0, nread, nread+ninput_items); // read the tags
    
    // Loop over the tags searching for those with keys "tx_new_channel"
    std::vector<gr_tag_t>::iterator it;
    std::vector<channel_tuple>* current_vec;

    for( it = tags.begin(); it != tags.end(); it++ )
    {
        if(it->key == NEW_CHANNEL_FLAG)
        {
            if( it->key == NEW_CHANNEL_FLAG )
            	current_vec = &d_channel_tags;
            else if( it->key == MODULATOR_SOB )
                d_sob_offsets.push_back(it->offset);

            //check for duplicate keys at offset. Keep the last tag in case of dups
            if(!current_vec->empty() && get<0>(current_vec->back()) == it->offset)
            {
            	current_vec->back() = boost::make_tuple( it->offset,
            						                    pmt::pmt_to_uint64(it->value) );
            }
            else
            {
            	current_vec->push_back(boost::make_tuple( it->offset,
	                    								 pmt::pmt_to_uint64(it->value) ));
            }
        }
    }
}

void
digital_ll_modulator::switch_channels( int new_chan )
{
    if( new_chan > d_num_chan )
        std::cout << "!!! WARNING: New channel is " << new_chan << " which is greater than "
            << "the number of channels (" << d_num_chan << ")\n";
    d_current_chan = new_chan;
}
