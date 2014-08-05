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

#include <gr_io_signature.h>
#include <digital_ll_downcounter.h>
#include <iostream>

#define DEBUG_VERBOSE 0

digital_ll_downcounter_sptr
digital_ll_make_downcounter (int number)
{
	return digital_ll_downcounter_sptr (new digital_ll_downcounter (number));
}


digital_ll_downcounter::digital_ll_downcounter (int number)
	: gr_sync_block ("downcounter",
		gr_make_io_signature (1, 1, sizeof (float)),
		gr_make_io_signature (1, 1, sizeof (float)))
{
    if( number < 0 ){
        // Check that the number was positive
        std::cout << "Error: The reset count down (" << number << ") is less than zero!\n";
        throw 20;
    }
        
    reset_number = number;
    counter = 0;
    nprocsamps = 0;
}


digital_ll_downcounter::~digital_ll_downcounter ()
{
}

void
digital_ll_downcounter::setMaxCount( int number )
{
    this->reset_number = number;
}

int
digital_ll_downcounter::checkFlag( )
{
    int flag;  // flag is returned high when the counter is greater than 0
    
    if( DEBUG_VERBOSE )
        std::cout << "Checking Flag\n";
    
    if( this->counter ){
        flag = 1;
    }
    else{
        flag = 0;
    }
        
    return flag;
        
}

int
digital_ll_downcounter::work (int noutput_items,
			gr_vector_const_void_star &input_items,
			gr_vector_void_star &output_items)
{
    /*
    Basically all this block does is look for an input sample that is non-zero.
    If it finds a non-zero input than it will hold its output high for some
    determined amount of time. 
    */
    if( DEBUG_VERBOSE )
        std::cout << "Running downcounter\n";
    
	const float *in = (const float *) input_items[0];
	float *out = (float *) output_items[0];

	// Do Signal Processing
	memset(out, 0, noutput_items*sizeof(float));
	
	float eps = 0.0001;  // eps is the precision required to declare input 0
	
	for( int i = 0; i < noutput_items; i++ ){
	    if( in[i] > eps || in[i] < -eps ){
	        // We have a non-zero input set counter to reset_number
	        counter = reset_number;
	    }
	    
	    if( counter > 0 ){
	        // We need to raise the output
	        out[i] = 1.0;
	        
	        //decrement counter
	        counter--;
	    }
	    else{
	        // We need to not raise the output
	        out[i] = 0.0;
	    }
	    
	}
	
	// Increment the total number of processed samps if we are using debug
	if( DEBUG_VERBOSE ){
	    nprocsamps = nprocsamps + noutput_items;
	    std::cout << "Number of Processed Samples = " << nprocsamps << "\n";
	}
	
	// Tell runtime system how many output items we produced.
	return noutput_items;
}

