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

#ifndef INCLUDED_CHANNEL_CHARAC_TEST_H
#define INCLUDED_CHANNEL_CHARAC_TEST_H

#include <channel_charac_api.h>
#include <gr_sync_block.h>

class channel_charac_test;
typedef boost::shared_ptr<channel_charac_test> channel_charac_test_sptr;

CHANNEL_CHARAC_API channel_charac_test_sptr channel_charac_make_test (int nfft, int K, int Lt, int n_avg, int wait_time_signal, int wait_time_noise);

/*!
 * \brief <+description+>
 *
 */
class CHANNEL_CHARAC_API channel_charac_test : public gr_sync_block
{
	friend CHANNEL_CHARAC_API channel_charac_test_sptr channel_charac_make_test (int nfft, int K, int Lt, int n_avg, int wait_time_signal, int wait_time_noise);

	channel_charac_test (int nfft, int K, int Lt, int n_avg, int wait_time_signal, int wait_time_noise);

    int Lt;
	int K;
	int nfft;
	int n_avg;
	int wait_time_signal;
	int wait_time_noise;
	int running;
	
	int samples_proc;
	int avg_itr_signal;
	int avg_itr_noise;
	float *P;
	float *N;
	float *N_silent;

 public:
	~channel_charac_test ();


	int work (int noutput_items,
		gr_vector_const_void_star &input_items,
		gr_vector_void_star &output_items);
		
    float return_SNR(int tx_num);
    
    float return_SNR_2step(int tx_num);
    
    float return_sig_power(int tx_num);
    
    int SNR_calculation_ready();
    
    void poke();
    
    float return_noise_power( int tx_num );
    
    float return_odd_bin_power( int tx_num );
    
};

#endif /* INCLUDED_CHANNEL_CHARAC_TEST_H */

