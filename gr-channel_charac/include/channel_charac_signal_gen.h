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

#ifndef INCLUDED_CHANNEL_CHARAC_SIGNAL_GEN_H
#define INCLUDED_CHANNEL_CHARAC_SIGNAL_GEN_H

#include <channel_charac_api.h>
#include <gr_sync_block.h>

class channel_charac_signal_gen;
typedef boost::shared_ptr<channel_charac_signal_gen> channel_charac_signal_gen_sptr;

CHANNEL_CHARAC_API channel_charac_signal_gen_sptr channel_charac_make_signal_gen (const std::vector<gr_complex> &signal, int delay, int quit);

/*!
 * \brief <+description+>
 *
 */
class CHANNEL_CHARAC_API channel_charac_signal_gen : public gr_sync_block
{
	friend CHANNEL_CHARAC_API channel_charac_signal_gen_sptr channel_charac_make_signal_gen (const std::vector<gr_complex> &signal, int delay, int quit);

	channel_charac_signal_gen (const std::vector<gr_complex> &signal, int delay, int quit);
    gr_complex *signal;
    int size;
    int pos;
    int delay;
    int quit;
    long long nsamps;

 public:
	~channel_charac_signal_gen ();


	int work (int noutput_items,
		gr_vector_const_void_star &input_items,
		gr_vector_void_star &output_items);
		
		
    int get_samples_processed();
    
    int done();
    
    void poke();
};

#endif /* INCLUDED_CHANNEL_CHARAC_SIGNAL_GEN_H */

