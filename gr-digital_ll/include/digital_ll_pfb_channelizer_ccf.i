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
 *
 * This file incorporates work covered by the following copyright:
 *
 *
 * Copyright 2009,2010 Free Software Foundation, Inc.
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

GR_SWIG_BLOCK_MAGIC(gr,pfb_channelizer_ccf);

digital_ll_pfb_channelizer_ccf_sptr digital_ll_make_pfb_channelizer_ccf (unsigned int numchans,
							 const std::vector<float> &taps,
							 float oversample_rate=1);

class digital_ll_pfb_channelizer_ccf : public gr_block
{
 private:
  digital_ll_pfb_channelizer_ccf (unsigned int numchans,
			  const std::vector<float> &taps,
			  float oversample_rate);

 public:
  ~digital_ll_pfb_channelizer_ccf ();

  void set_taps (const std::vector<float> &taps);
  void print_taps();
  std::vector<std::vector<float> > taps() const;

  void set_channel_map(const std::vector<int> &map);
  std::vector<int> channel_map() const;
};
