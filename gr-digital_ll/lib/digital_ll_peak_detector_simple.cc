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
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gr_io_signature.h>
#include <digital_ll_peak_detector_simple.h>
#include <iostream>


digital_ll_peak_detector_simple_sptr
digital_ll_make_peak_detector_simple (float threshold)
{
	return digital_ll_peak_detector_simple_sptr (new digital_ll_peak_detector_simple (threshold));
}


digital_ll_peak_detector_simple::digital_ll_peak_detector_simple (float threshold)
	: gr_sync_block ("peak_detector_simple",
		gr_make_io_signature (1, 1, sizeof (float)),
		gr_make_io_signature (1, 1, sizeof (char)))
{
    this->threshold = threshold;
    this->extra_search = 500;
    //std::cout << "Peak Detector Threshold: " << threshold << "\n";
}


digital_ll_peak_detector_simple::~digital_ll_peak_detector_simple ()
{
}


int
digital_ll_peak_detector_simple::work (int noutput_items,
			gr_vector_const_void_star &input_items,
			gr_vector_void_star &output_items)
{
	const float *iptr = (const float *) input_items[0];
	char *optr = (char *) output_items[0];
	
	memset(optr, 0, noutput_items*sizeof(char));

	// Signal Processing
	float peak_val = -(float)INFINITY;
    int peak_ind = 0;
    unsigned char state = 0;
    int i = 0;
    int counter = 0;
    
    
    while(i < noutput_items) {   
        if( state == 0 ){
            // We are still looking for the signal to rise above threshold.
            
            // In state zero we continue to search for a peak
            if( iptr[i] > -1.0*threshold )
                state = 1;  // Re-evaluate this sample in the next state
            else
                i++;        // Haven't passed threshold yet. Keep searching.
        }
        else if( state == 1 ){
            // The signal is above threshold
            if( noutput_items > 5000 ){
                // We're done. Call it.
                return noutput_items;
            }
            else if( iptr[i] > peak_val ){
                // We have found a new peak value.
                peak_val = iptr[i];
                peak_ind = i;
                i ++;
            }
            else if( iptr[i] > -1.0*threshold ){
                // This is not a peak value but we remain above threshold.
                i++;
            }
            else{
                state = 2;
                // We have fallen below threshold. Record the peak value.
                // Return to the searching state.
                //optr[peak_ind] = 1;
                //state = 0;
                //peak_val = -(float)INFINITY;
            }
        }
        else{
            // signal below threshold but we're still looking in case this is
            // a sidelobe
            if( iptr[i] > -1.0*threshold ){
                // We've risen again go to state 1
                state = 1;
                counter = 0;
            }
            else if( counter < this->extra_search ){
                // Keep searching
                counter++;
                i++;
            }
            else{
                // We're done. Call it.
                counter = 0;
                optr[peak_ind] = 1;
                state = 0;
                peak_val = -(float)INFINITY;
            }
        }
    
    }
    
    
    /*
    while(i < noutput_items) {   
        if( state == 0 ){
            // We are still looking for the signal to rise above threshold.
            
            // In state zero we continue to search for a peak
            if( iptr[i] > -1.0*threshold ){
                state = 1;  // Re-evaluate this sample in the next state
                if( i )
                    std::cout << "Making transition\n";
            }
            else
                i++;        // Haven't passed threshold yet. Keep searching.
        }
        else{
            //if( noutput_items > 1000 || iptr[i] < -1.0*threshold ){
            if( iptr[i] < -1.0*threshold ){
                // We're done. Call it.
                std::cout << "Detection Made with Latency " << noutput_items << " samples\n";
                optr[peak_ind] = 1;
                state = 0;
                peak_val = -(float)INFINITY;
            }
            else if( iptr[i] > peak_val ){
                // We have found a new peak value.
                peak_val = iptr[i];
                peak_ind = i;
                i ++;
            }
            else{
                i++;
            }
        }
    }
    */

	// Tell runtime system how many output items we produced.
	if(state == 0) {
        //printf("Leave in State 0, produced %d\n",noutput_items);
        return noutput_items;
    }
    else {   // only return up to passing the threshold
        //printf("Leave in State 1, only produced %d of %d\n",peak_ind,noutput_items);
        return peak_ind; // setting this value to zero may be more robust
    }
}

