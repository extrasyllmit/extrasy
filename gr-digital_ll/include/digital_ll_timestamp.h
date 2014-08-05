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

#ifndef INCLUDED_DIGITAL_LL_TIMESTAMP_UTILS
#define INCLUDED_DIGITAL_LL_TIMESTAMP_UTILS

#include <digital_ll_api.h>
#include <stdint.h>
#include <math.h>

/*! \dontinclude digital_ll_timestamp.h
 *  \dontinclude digital_ll_timestamp.cc
 */

class DIGITAL_LL_API digital_ll_timestamp
{

 private:

  int64_t d_int_s;
  double d_frac_s;


  void normalize();

 public:
  digital_ll_timestamp();
  digital_ll_timestamp(double frac_s);
  digital_ll_timestamp(int64_t int_s, double frac_s);
  ~digital_ll_timestamp();

  //accessors
  int64_t int_s() const;
  double frac_s() const;
  operator double() const;

  //operators
  digital_ll_timestamp & operator=(const digital_ll_timestamp &rhs);
  digital_ll_timestamp & operator+=(const digital_ll_timestamp &rhs);
  digital_ll_timestamp & operator-=(const digital_ll_timestamp &rhs);
  const digital_ll_timestamp operator+(const digital_ll_timestamp &other) const;
  const digital_ll_timestamp operator-(const digital_ll_timestamp &other) const;

  digital_ll_timestamp & operator+=(const double &rhs);
  digital_ll_timestamp & operator-=(const double &rhs);
  const digital_ll_timestamp operator+(const double &other) const;
  const digital_ll_timestamp operator-(const double &other) const;

  bool operator==(const digital_ll_timestamp &other) const;
  bool operator!=(const digital_ll_timestamp &other) const;
  bool operator<(const digital_ll_timestamp &other) const;
  bool operator<=(const digital_ll_timestamp &other) const;
  bool operator>(const digital_ll_timestamp &other) const;
  bool operator>=(const digital_ll_timestamp &other) const;


};

#endif /* INCLUDED_DIGITAL_LL_FRAMER_SINK_1_H */
