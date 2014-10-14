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
#include <channel_charac_test.h>
#include <iostream>


channel_charac_test_sptr
channel_charac_make_test (int nfft, int K, int Lt, int n_avg, int wait_time_signal, int wait_time_noise)
{
	return channel_charac_test_sptr (new channel_charac_test (nfft, K, Lt, n_avg, wait_time_signal, wait_time_noise));
}


channel_charac_test::channel_charac_test (int nfft, int K, int Lt, int n_avg, int wait_time_signal, int wait_time_noise)
	: gr_sync_block ("test",
		gr_make_io_signature (1, 1, nfft*sizeof (gr_complex)),
		gr_make_io_signature (0, 0, 0))
{
    // Assign the constructor variables
    this->nfft              = nfft;
    this->K                 = K;
    this->Lt                = Lt;
    this->n_avg             = n_avg;
    this->wait_time_signal  = wait_time_signal;
    this->wait_time_noise   = wait_time_noise;
    this->running           = 0;
    
    // Assign other variables
    this->samples_proc      = 0;
    this->avg_itr_signal    = 0; // iteration number counter for averaging signal
    this->avg_itr_noise     = 0; // iteration number counter for averaging noise
    this->P                 = new float[n_avg*Lt];   // Power signal
    this->N                 = new float[n_avg];      // Power noise during signal
    this->N_silent          = new float[n_avg];      // Power noise before signal
    
    // Initialize array values to zero
    for( int n = 0; n < n_avg; n++)
    {
        this->N_silent[n] = 0.0;
        this->N[n]        = 0.0;
    }
    
    for( int n = 0; n < n_avg*Lt; n++)
        this->P[n] = 0.0;
    
    // Check that k is divisible by Lt
    assert( K % Lt == 0 );
}


channel_charac_test::~channel_charac_test ()
{
    delete [] P;
    delete [] N;
    delete [] N_silent;
}


int
channel_charac_test::work (int noutput_items,
			gr_vector_const_void_star &input_items,
			gr_vector_void_star &output_items)
{
	const gr_complex *in = (const gr_complex *) input_items[0];
    gr_complex bin;
    int offset;
    int who;
    int loc;

    if( running )
    {
        if( avg_itr_noise < n_avg && samples_proc >= wait_time_noise && samples_proc < wait_time_signal )
        {
            for( int n = 0; n < noutput_items && avg_itr_noise < n_avg; n++ )
            {            
                for( int k = 0; k < nfft; k++ )
                {
                    bin = in[n*nfft+k]; // assign the bins value to bin for ease
                    N_silent[avg_itr_noise] = N_silent[avg_itr_noise]
                        + bin.real()*bin.real() + bin.imag()*bin.imag();
                }
                avg_itr_noise++;
            }
        }
        else if( avg_itr_signal < n_avg && samples_proc >= wait_time_signal )
        {   // Calculate the Power and Noise of the Process
        
	        for( int n = 0; n < noutput_items && avg_itr_signal < n_avg; n++ )
	        {   // Loop over the number of FFT's that have come in.
	        
	        
                for( int k = 0; k < nfft; k++ )
                {  // Loop over the indices
                   
                   bin = in[n*nfft+k]; // assign the bins value to bin for ease
                   
                   if( k >= nfft/2 - K && k <= nfft/2 + K )
                   {  // We are within the frequency range. Take values.
                      if( k > nfft/2 )
                      { // In the upper (positive) half of the spectrum
                        offset = k - nfft/2;
                        if( offset%2 == 1 )
                        {   // This is a noise bin
                            N[avg_itr_signal] = N[avg_itr_signal]
                                + bin.real()*bin.real() + bin.imag()*bin.imag();
                        }
                        else
                        {   // This is a transmit bin. Figure out who is the
                            // transmitter and calculate that value.
                            who = ((offset-2)/2) % Lt;
                            loc = avg_itr_signal + who*n_avg;
                            P[loc] = P[loc] + bin.real()*bin.real() + bin.imag()*bin.imag();
                        }
                      }
                      else if( k < nfft/2 )
                      { // In the lower (negative) half of the spectrum
                        offset = nfft/2 - k;
                        if( offset%2 == 1 )
                        {
                            // This is a noise bin
                            N[avg_itr_signal] = N[avg_itr_signal]
                                + bin.real()*bin.real() + bin.imag()*bin.imag();
                        }
                        else
                        {   // This is a transmit bin. Figure out who is the
                            // transmitter and calculate that value.
                            who = Lt - 1 - (((offset-2)/2) % Lt);
                            loc = avg_itr_signal + who*n_avg;
                            P[loc] = P[loc] + bin.real()*bin.real() + bin.imag()*bin.imag();
                        }
                      }  // end if upper/lower band
                   } // end if within band               
                } // end for nfft
                avg_itr_signal++;
	        } // end for noutput iterms
	    }
	    
	    samples_proc = samples_proc + noutput_items*nfft; // account for the number of samples_proc
	    
	    // Setting running to false if we are done.
	    if( avg_itr_signal >= n_avg )
	        running = 0;
    } // end if running

	// Tell runtime system how many output items we produced.
	return noutput_items;
}


// Function to be called to calculate the SNR to transmitter tx_num
float
channel_charac_test::return_SNR( int tx_num )
{
    tx_num = tx_num - 1;
    float tx_pwr = 0;
    float n_pwr  = 0;
    float snr    = 0;
    
    // Return the SNR for the specified transmitter
    for( int n = 0; n < n_avg; n++ )
    {
        tx_pwr = tx_pwr + P[n + n_avg*tx_num]/( nfft*nfft );
        n_pwr  = n_pwr + N[n]/( K*nfft );
    }
    tx_pwr = tx_pwr/n_avg;
    n_pwr  = n_pwr/n_avg;
    
    snr = tx_pwr/n_pwr;
    
    return snr;
}

// Function to be called to calculate the SNR to transmitter tx_num
// in a 2 step process
float
channel_charac_test::return_SNR_2step( int tx_num )
{
    tx_num = tx_num - 1;
    float tx_pwr = 0;
    float n_pwr  = 0;
    float snr    = 0;
    
    // Return the SNR for the specified transmitter
    for( int n = 0; n < n_avg; n++ )
    {
        tx_pwr = tx_pwr + P[n + n_avg*tx_num]/( nfft*nfft );
        n_pwr  = n_pwr + N_silent[n]/( nfft*nfft );
    }
    tx_pwr = tx_pwr/n_avg;
    n_pwr  = n_pwr/n_avg;
    
    snr = tx_pwr/n_pwr;
    
    return snr;
}

//Function to be called to return the power of the signal
float
channel_charac_test::return_sig_power( int tx_num )
{
    tx_num = tx_num - 1;
    float tx_pwr = 0;
    
    for( int n = 0; n < n_avg; n++ )
    {
        tx_pwr = tx_pwr + P[n + n_avg*tx_num]/( nfft*nfft );
    }
    
    tx_pwr = tx_pwr/n_avg;
    
    return tx_pwr;
}

// Function to be called to check if enough data has been processed to
// calculate the SNR.
int
channel_charac_test::SNR_calculation_ready()
{
    if( avg_itr_signal >= n_avg )
        return 1;
    else
        return 0;
}

// Function return the noise power
float
channel_charac_test::return_noise_power( int tx_num )
{
    tx_num = tx_num - 1;
    float n_pwr  = 0;
    
    // Return the SNR for the specified transmitter
    for( int n = 0; n < n_avg; n++ )
    {
        n_pwr  = n_pwr + N_silent[n]/( nfft*nfft );
    }
    n_pwr  = n_pwr/n_avg;
    
    return n_pwr;
}

// Function return the Odd Bin Power (Note: by odd I mean unoccupied)
float
channel_charac_test::return_odd_bin_power( int tx_num )
{
    tx_num = tx_num - 1;
    float n_pwr  = 0;
    
    // Return the SNR for the specified transmitter
    for( int n = 0; n < n_avg; n++ )
    {
        n_pwr  = n_pwr + N[n]/( K*nfft );
    }
    n_pwr  = n_pwr/n_avg;
    
    return n_pwr;
}

// Function to kick off the processing
void
channel_charac_test::poke()
{
    running = 1;
    samples_proc      = 0;
    avg_itr_signal    = 0; // iteration number counter for averaging signal
    avg_itr_noise     = 0; // iteration number counter for averaging noise
    
    // Initialize array values to zero
    for( int n = 0; n < n_avg; n++)
    {
        this->N_silent[n] = 0.0;
        this->N[n]        = 0.0;
    }
    
    for( int n = 0; n < n_avg*Lt; n++)
        this->P[n] = 0.0;
}


// BEWARE: Code Graveyard Below
/*
	const gr_complex *in = (const gr_complex *) input_items[0];
    gr_complex bin;
    int offset;
    int who;
    int loc;

    if( avg_itr_noise < n_avg && samples_proc >= wait_time_noise && samples_proc < wait_time_signal )
    {
        for( int n = 0; n < noutput_items && avg_itr_noise < n_avg; n++ )
        {
            for( int k = 0; k < nfft; k++ )
            {
                bin = in[n*nfft+k]; // assign the bins value to bin for ease
                N_silent[avg_itr_noise] = N_silent[avg_itr_noise]
                    + bin.real()*bin.real() + bin.imag()*bin.imag();
            }
            avg_itr_noise++;
        }
    }
    else if( avg_itr_signal < n_avg && samples_proc >= wait_time_signal )
    {   // Calculate the Power and Noise of the Process
    
        if(avg_itr_signal == 0)
        {
            std::cout << "\n";
            for( int k = 0; k < nfft; k++ )
            {
                std::cout << "A(" << k+1 << ")=" << in[k].real() << "+ 1i*" << in[k].imag() << "\n";
            }
        }
    
	    for( int n = 0; n < noutput_items && avg_itr_signal < n_avg; n++ )
	    {   // Loop over the number of FFT's that have come in.
            for( int k = 0; k < nfft; k++ )
            {  // Loop over the indices
               
               bin = in[n*nfft+k]; // assign the bins value to bin for ease
               
               if( k >= nfft/2 - K && k <= nfft/2 + K )
               {  // We are within the frequency range. Take values.
                  if( k > nfft/2 )
                  { // In the upper (positive) half of the spectrum
                    offset = k - nfft/2;
                    if( offset%2 == 1 )
                    {   // This is a noise bin
                        N[avg_itr_signal] = N[avg_itr_signal]
                            + bin.real()*bin.real() + bin.imag()*bin.imag();
                    }
                    else
                    {   // This is a transmit bin. Figure out who is the
                        // transmitter and calculate that value.
                        who = ((offset-2)/2) % Lt;
                        loc = avg_itr_signal + who*n_avg;
                        P[loc] = P[loc] + bin.real()*bin.real() + bin.imag()*bin.imag();
                    }
                  }
                  else if( k < nfft/2 )
                  { // In the lower (negative) half of the spectrum
                    offset = nfft/2 - k;
                    if( offset%2 == 1 )
                    {
                        // This is a noise bin
                        N[avg_itr_signal] = N[avg_itr_signal]
                            + bin.real()*bin.real() + bin.imag()*bin.imag();
                    }
                    else
                    {   // This is a transmit bin. Figure out who is the
                        // transmitter and calculate that value.
                        who = Lt - 1 - (((offset-2)/2) % Lt);
                        loc = avg_itr_signal + who*n_avg;
                        P[loc] = P[loc] + bin.real()*bin.real() + bin.imag()*bin.imag();
                    }
                  }  // end if upper/lower band
               } // end if within band               
            } // end for nfft
            avg_itr_signal++;
	    } // end for noutput iterms
	}
	

    samples_proc = samples_proc + noutput_items*nfft; // account for the number of samples_proc

	// Tell runtime system how many output items we produced.
	return noutput_items;
*/


/*
	const gr_complex *in = (const gr_complex *) input_items[0];
    gr_complex bin;
    int offset;
    int who;
    int loc;

    if( avg_itr_noise < n_avg && samples_proc >= wait_time_noise && samples_proc < wait_time_signal )
    {
        for( int n = 0; n < noutput_items && avg_itr_noise < n_avg; n++ )
        {
            for( int k = 0; k < nfft; k++ )
            {
                bin = in[n*nfft+k]; // assign the bins value to bin for ease
                N_silent[avg_itr_noise] = N_silent[avg_itr_noise]
                    + bin.real()*bin.real() + bin.imag()*bin.imag();
            }
            avg_itr_noise++;
        }
    }
    else if( avg_itr_signal < n_avg && samples_proc >= wait_time_signal )
    {   // Calculate the Power and Noise of the Process
    
	    for( int n = 0; n < noutput_items && avg_itr_signal < n_avg; n++ )
	    {   // Loop over the number of FFT's that have come in.
            for( int k = 0; k < nfft; k++ )
            {  // Loop over the indices
               
               bin = in[n*nfft+k]; // assign the bins value to bin for ease
               
               if( (k <= K || k >= nfft - K) && k != 0 )
               {  // We are within the frequency range. Take values.
                  if( k <= K )
                  { // In the upper (positive) half of the spectrum
                    offset = k;
                    if( offset%2 == 1 )
                    {   // This is a noise bin
                        N[avg_itr_signal] = N[avg_itr_signal]
                            + bin.real()*bin.real() + bin.imag()*bin.imag();
                    }
                    else
                    {   // This is a transmit bin. Figure out who is the
                        // transmitter and calculate that value.
                        who = ((offset-2)/2) % Lt;
                        if( who == 0 )
                            std::cout << k+1 << "\n";
                        loc = avg_itr_signal + who*n_avg;
                        P[loc] = P[loc] + bin.real()*bin.real() + bin.imag()*bin.imag();
                    }
                  }
                  else if( k >= nfft - K )
                  { // In the lower (negative) half of the spectrum
                    offset = nfft - k;
                    if( offset%2 == 1 )
                    {
                        // This is a noise bin
                        N[avg_itr_signal] = N[avg_itr_signal]
                            + bin.real()*bin.real() + bin.imag()*bin.imag();
                    }
                    else
                    {   // This is a transmit bin. Figure out who is the
                        // transmitter and calculate that value.
                        who = Lt - 1 - (((offset-2)/2) % Lt);
                        if( who == 0 )
                            std::cout << k+1 << "\n";
                        loc = avg_itr_signal + who*n_avg;
                        P[loc] = P[loc] + bin.real()*bin.real() + bin.imag()*bin.imag();
                    }
                  }  // end if upper/lower band
               } // end if within band               
            } // end for nfft
            avg_itr_signal++;
	    } // end for noutput iterms
	}
	

    samples_proc = samples_proc + noutput_items*nfft; // account for the number of samples_proc

	// Tell runtime system how many output items we produced.
	return noutput_items;
*/
