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
 */

#ifndef INCLUDED_DIGITAL_LL_PEAK_DETECTOR_SIMPLE_H
#define INCLUDED_DIGITAL_LL_PEAK_DETECTOR_SIMPLE_H

#include <digital_ll_api.h>
#include <gr_sync_block.h>

class digital_ll_peak_detector_simple;
typedef boost::shared_ptr<digital_ll_peak_detector_simple> digital_ll_peak_detector_simple_sptr;

DIGITAL_LL_API digital_ll_peak_detector_simple_sptr digital_ll_make_peak_detector_simple (float threshold);

/*!
 * \brief <+description+>
 *
 */
class DIGITAL_LL_API digital_ll_peak_detector_simple : public gr_sync_block
{
	friend DIGITAL_LL_API digital_ll_peak_detector_simple_sptr digital_ll_make_peak_detector_simple (float threshold);

	digital_ll_peak_detector_simple (float threshold);
	float threshold;
	int extra_search;

 public:
	~digital_ll_peak_detector_simple ();


	int work (int noutput_items,
		gr_vector_const_void_star &input_items,
		gr_vector_void_star &output_items);
};

#endif /* INCLUDED_DIGITAL_LL_PEAK_DETECTOR_SIMPLE_H */

