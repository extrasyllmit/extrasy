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

#include "digital_ll_uhd_time_spec_t_builder.h"
#include <ctime>


uhd_time_spec_t_builder::uhd_time_spec_t_builder()
{
	m_time_spec_t = uhd::time_spec_t();
}

uhd_time_spec_t_builder::uhd_time_spec_t_builder(long long full_secs, double frac_secs)
{
	m_time_spec_t = uhd::time_spec_t((time_t)full_secs, frac_secs);
}

uhd::time_spec_t uhd_time_spec_t_builder::time_spec_t()
{
	return m_time_spec_t;
}

//uhd::time_spec_t make_uhd_time_spec_t(long long full_secs, double frac_secs)
//{
//	time_t new_time = (time_t)full_secs;
//	uhd::time_spec_t t = uhd::time_spec_t(new_time, frac_secs);
//	return t;
//}
