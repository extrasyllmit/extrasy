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
#include <channel_charac_signal_gen.h>
#include <assert.h>
#include <iostream>


channel_charac_signal_gen_sptr
channel_charac_make_signal_gen (const std::vector<gr_complex> &signal, int delay, int quit)
{
	return channel_charac_signal_gen_sptr (new channel_charac_signal_gen (signal, delay, quit));
}


channel_charac_signal_gen::channel_charac_signal_gen (const std::vector<gr_complex> &in_signal, int delay, int quit)
	: gr_sync_block ("signal_gen",
		gr_make_io_signature (0, 0, 0),
		gr_make_io_signature (1, 1, sizeof (gr_complex)))
{
    assert(in_signal.size() != 0);
    this->pos    = 0;
    this->nsamps = 0;
    this->delay  = delay;
    this->size   = in_signal.size();
    this->signal = new gr_complex[this->size];
    this->quit   = quit;
    for( int i = 0; i < in_signal.size(); i++ )
    {
        this->signal[i] = in_signal[i];
    }
}


channel_charac_signal_gen::~channel_charac_signal_gen ()
{
    delete [] signal;
}


int
channel_charac_signal_gen::work (int noutput_items,
			gr_vector_const_void_star &input_items,
			gr_vector_void_star &output_items)
{
	gr_complex *out = (gr_complex *) output_items[0];

	// Output the Signal
	
    if(nsamps <= delay)
    {
        for( int i = 0; i < noutput_items; i++ )
        {
            out[i] = 0;
        }
    }
    else if( nsamps > delay && nsamps < quit )
    {
        for( int i = 0; i < noutput_items; i++ )
        {
            out[i] = signal[pos++];
            if( pos >= size )
            {
                pos = 0;
            }
        }
    }
    else if( nsamps >= quit)
    {
        for( int i = 0; i < noutput_items; i++ )
        {
            out[i] = 0;
        }
    }
    
    nsamps = nsamps + noutput_items;

	// Tell runtime system how many output items we produced.
	return noutput_items;
}

int
channel_charac_signal_gen::get_samples_processed()
{
    return nsamps;
}

int
channel_charac_signal_gen::done()
{
    int done;
    if( nsamps > quit )
        done = 1;
    else
        done = 0;
        
    return done;
}

void
channel_charac_signal_gen::poke()
{
    nsamps = 0;
}

