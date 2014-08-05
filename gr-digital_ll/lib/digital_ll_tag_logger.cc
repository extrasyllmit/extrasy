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
 *
 * This file incorporates work covered by the following copyright:
 *
 *
 * Copyright 2012 Free Software Foundation, Inc.
 *
 * This file is part of GNU Radio
 *
 * GNU Radio is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * GNU Radio is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GNU Radio; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <digital_ll_tag_logger.h>
#include <gr_io_signature.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <stdexcept>

digital_ll_tag_logger_sptr
digital_ll_make_tag_logger(size_t itemsize, const std::string &name)
{
  return gnuradio::get_initial_sptr(new digital_ll_tag_logger(itemsize, name));
}

digital_ll_tag_logger::~digital_ll_tag_logger()
{
	close();
}

digital_ll_tag_logger::digital_ll_tag_logger(size_t itemsize, const std::string &name)
  : gr_sync_block("tag_logger",
		  gr_make_io_signature(1, -1, itemsize),
		  gr_make_io_signature(0, 0, 0)),
    d_display(true)
{
	if (!open(name))
	{
		throw std::runtime_error("can't open file");
	}
}

std::vector<gr_tag_t>
digital_ll_tag_logger::current_tags()
{
  gruel::scoped_lock l(d_mutex);
  return d_tags;
}

/*!
 * \brief Open filename and begin output to it.
 */
bool digital_ll_tag_logger::open(const std::string &name)
{
	d_out.open(name.c_str());

	return d_out.is_open();
}

/*!
 * \brief Close current output file.
 *
 * Closes current output file and ignores any output until
 * open is called to connect to another file.
 */
void digital_ll_tag_logger::close()
{
	if (d_out.is_open())
	{
		d_out.close();
	}
	return;
}


void
digital_ll_tag_logger::set_display(bool d)
{
  gruel::scoped_lock l(d_mutex);
  d_display = d;
}

int
digital_ll_tag_logger::work(int noutput_items,
		   gr_vector_const_void_star &input_items,
		   gr_vector_void_star &output_items)
{


  gruel::scoped_lock l(d_mutex);


  uint64_t abs_N, end_N;
  for(size_t i = 0; i < input_items.size(); i++) {
    abs_N = nitems_read(i);
    end_N = abs_N + (uint64_t)(noutput_items);

    d_tags.clear();
    get_tags_in_range(d_tags, i, abs_N, end_N);

    if(d_display) {
      if ( d_tags.begin() != d_tags.end())
      {
    	  d_out << "Input Stream:\t" << i << std::endl;
      }

      for(d_tags_itr = d_tags.begin(); d_tags_itr != d_tags.end(); d_tags_itr++) {
	d_out << "Offset:\t" << d_tags_itr->offset << "\t"
		  << "Source:\t" << pmt::pmt_symbol_to_string(d_tags_itr->srcid) << "\t"
		  << "Key:\t" << pmt::pmt_symbol_to_string(d_tags_itr->key) << "\t"
		  << "Value:\t" << pmt::pmt_write_string(d_tags_itr->value) << "\t"
	      << std::endl;
      }
    }
  }

  return noutput_items;
}
