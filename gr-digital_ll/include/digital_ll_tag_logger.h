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

#ifndef INCLUDED_GR_TAG_LOGGER_H
#define INCLUDED_GR_TAG_LOGGER_H

#include <digital_ll_api.h>
#include <gr_sync_block.h>
#include <gruel/thread.h>
#include <stddef.h>
#include <fstream>

class digital_ll_tag_logger;
typedef boost::shared_ptr<digital_ll_tag_logger> digital_ll_tag_logger_sptr;

DIGITAL_LL_API digital_ll_tag_logger_sptr digital_ll_make_tag_logger(size_t sizeof_stream_item, const std::string &name);

/*!
 * \brief Bit bucket that prints out any tag received.
 * \ingroup sink_blk
 *
 * This block collects all tags sent to it on all input ports and
 * displays them to stdout in a formatted way. The \p name parameter
 * is used to identify which debug sink generated the tag, so when
 * connecting a block to this debug sink, an appropriate name is
 * something that identifies the input block.
 *
 * This block otherwise acts as a NULL sink in that items from the
 * input stream are ignored. It is designed to be able to attach to
 * any block and watch all tags streaming out of that block for
 * debugging purposes.
 *
 * The tags from the last call to this work function are stored and
 * can be retrieved using the function 'current_tags'.
 */
class DIGITAL_LL_API digital_ll_tag_logger : public gr_sync_block
{
  friend DIGITAL_LL_API digital_ll_tag_logger_sptr digital_ll_make_tag_logger(size_t itemsize, const std::string &name);

  private:

    std::vector<gr_tag_t> d_tags;
    std::vector<gr_tag_t>::iterator d_tags_itr;
    bool d_display;
    gruel::mutex d_mutex;
    std::ofstream d_out;


  protected:
    digital_ll_tag_logger(size_t sizeof_stream_item, const std::string &name);

  public:
  ~digital_ll_tag_logger();

  /*!
   * \brief Returns a vector of gr_tag_t items as of the last call to
   * work.
   */
  std::vector<gr_tag_t> current_tags();

  /*!
   * \brief Open filename and begin output to it.
   */
  bool open(const std::string &name);

  /*!
   * \brief Close current output file.
   *
   * Closes current output file and ignores any output until
   * open is called to connect to another file.
   */
  void close();


  /*!
   * \brief Set the display of tags to stdout on/off.
   */
  void set_display(bool d);

  int work(int noutput_items,
	   gr_vector_const_void_star &input_items,
	   gr_vector_void_star &output_items);
};

#endif /* INCLUDED_GR_TAG_LOGGER_H */
