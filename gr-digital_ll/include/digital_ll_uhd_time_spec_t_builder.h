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

#ifndef INCLUDED_DIGITAL_LL_UHD_TIME_SPEC_T_BUILDER_H
#define INCLUDED_DIGITAL_LL_UHD_TIME_SPEC_T_BUILDER_H



#include <uhd/types/time_spec.hpp>
#include <digital_ll_api.h>


class DIGITAL_LL_API uhd_time_spec_t_builder
{
	public:

	uhd_time_spec_t_builder();

	uhd_time_spec_t_builder(long long full_secs, double frac_secs);

	uhd::time_spec_t time_spec_t();

	private:

	uhd::time_spec_t m_time_spec_t;
};

#endif /* INCLUDED_DIGITAL_LL_UHD_TIME_SPEC_T_BUILDER_H */
