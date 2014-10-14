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

#include <digital_ll_timestamp.h>
/*! \dontinclude digital_ll_timestamp.h
 *
 */

// correct for fractional second overflow (positive or negative)
void digital_ll_timestamp::normalize()
{

	if( d_frac_s < 0)
	{
		d_int_s +=(ceil(d_frac_s) - 1);
		d_frac_s -=(ceil(d_frac_s) - 1);
	}

	if(d_frac_s >=1)
	{
		d_int_s +=(floor(d_frac_s));
		d_frac_s -=(floor(d_frac_s));
	}

}

digital_ll_timestamp::digital_ll_timestamp()
{
  d_int_s = 0;
  d_frac_s = 0;

}

digital_ll_timestamp::digital_ll_timestamp(double frac_s)
{
  d_int_s = 0;
  d_frac_s = frac_s;

  this->normalize();

}

digital_ll_timestamp::digital_ll_timestamp(int64_t int_s, double frac_s)
{
  d_int_s = int_s;
  d_frac_s = frac_s;

  this->normalize();

}

digital_ll_timestamp::~digital_ll_timestamp ()
{
}

int64_t digital_ll_timestamp::int_s() const
{
	if( (d_int_s+1 <= 0) & (d_frac_s-1 < 0))
	{
		return d_int_s+1;
	}
	else
	{
	    return d_int_s;
	}
}

double digital_ll_timestamp::frac_s() const
{
    if ((d_int_s+1 <= 0) & (d_frac_s-1 < 0))
    {
    	return d_frac_s-1.0;
    }
    else
    {
        return d_frac_s;
    }
}

digital_ll_timestamp::operator double() const
{
	return double(d_int_s) + d_frac_s;
}

digital_ll_timestamp & digital_ll_timestamp::operator=(
		const digital_ll_timestamp &rhs)
{
	d_int_s = rhs.d_int_s;
	d_frac_s = rhs.d_frac_s;

	this->normalize();

	return *this;
}

digital_ll_timestamp & digital_ll_timestamp::operator+=(
		const digital_ll_timestamp &rhs)
{
	d_int_s += rhs.d_int_s;
	d_frac_s += rhs.d_frac_s;

	this->normalize();

	return *this;
}
digital_ll_timestamp & digital_ll_timestamp::operator-=(
		const digital_ll_timestamp &rhs)
{
	d_int_s -= rhs.d_int_s;
	d_frac_s -= rhs.d_frac_s;

	this->normalize();

	return *this;
}
const digital_ll_timestamp digital_ll_timestamp::operator+(
		const digital_ll_timestamp &other) const
{

	digital_ll_timestamp result = *this;
	result += other;
	return result;

}

const digital_ll_timestamp digital_ll_timestamp::operator-(
		const digital_ll_timestamp &other) const
{
	digital_ll_timestamp result = *this;
	result -= other;
	return result;
}

digital_ll_timestamp & digital_ll_timestamp::operator+=(const double &rhs)
{
	d_frac_s += rhs;

	this->normalize();

	return *this;
}

digital_ll_timestamp & digital_ll_timestamp::operator-=(const double &rhs)
{
	d_frac_s -= rhs;

	this->normalize();

	return *this;
}

const digital_ll_timestamp digital_ll_timestamp::operator+(const double &other) const
{
	digital_ll_timestamp result = *this;
	result += other;
	return result;
}

const digital_ll_timestamp digital_ll_timestamp::operator-(const double &other) const
{
	digital_ll_timestamp result = *this;
	result -= other;
	return result;
}

bool digital_ll_timestamp::operator==(const digital_ll_timestamp &other) const
{
	return (d_int_s == other.d_int_s) & (d_frac_s == other.d_frac_s);
}

bool digital_ll_timestamp::operator!=(const digital_ll_timestamp &other) const
{
	return !(*this == other);
}

bool digital_ll_timestamp::operator<(const digital_ll_timestamp &other) const
{
	return (this->d_int_s < other.d_int_s) | ( (this->d_int_s == other.d_int_s) &
			(this->d_frac_s < other.d_frac_s));
}

bool digital_ll_timestamp::operator<=(const digital_ll_timestamp &other) const
{
	return (*this == other) | (*this < other);
}

bool digital_ll_timestamp::operator>(const digital_ll_timestamp &other) const
{
	return !(*this <= other );
}

bool digital_ll_timestamp::operator>=(const digital_ll_timestamp &other) const
{
	return !(*this < other);
}


