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

#ifndef INCLUDED_DIGITAL_LL_DOWNCOUNTER_H
#define INCLUDED_DIGITAL_LL_DOWNCOUNTER_H

#include <digital_ll_api.h>
#include <gr_sync_block.h>

class digital_ll_downcounter;
typedef boost::shared_ptr<digital_ll_downcounter> digital_ll_downcounter_sptr;

DIGITAL_LL_API digital_ll_downcounter_sptr digital_ll_make_downcounter (int number);

/*!
 * \brief <+description+>
 *
 */
class DIGITAL_LL_API digital_ll_downcounter : public gr_sync_block
{
	friend DIGITAL_LL_API digital_ll_downcounter_sptr digital_ll_make_downcounter (int number);

	digital_ll_downcounter (int number);
	int reset_number;
	int counter;
	unsigned long long nprocsamps;

 public:
	~digital_ll_downcounter ();

    void setMaxCount( int number );
    
    int checkFlag( );

	int work (int noutput_items,
		gr_vector_const_void_star &input_items,
		gr_vector_void_star &output_items);
};

#endif /* INCLUDED_DIGITAL_LL_DOWNCOUNTER_H */

