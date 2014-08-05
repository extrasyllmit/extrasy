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

#ifndef INCLUDED_DIGITAL_LL_CONTEXT_TAG_MANAGER
#define INCLUDED_DIGITAL_LL_CONTEXT_TAG_MANAGER

#include <digital_ll_api.h>
#include <deque>
#include <vector>
#include <map>
#include <utility>
#include <string>
#include <gr_tags.h>

//DIGITAL_LL_API
class digital_ll_context_tag_manager
{

	typedef std::deque<gr_tag_t> tag_deque;
	typedef tag_deque::iterator tag_deque_it;
	typedef std::pair< tag_deque_it, tag_deque_it> it_pair;

	static bool compare_tag_offset_lt(const gr_tag_t & t1, const gr_tag_t & t2);

	static bool compare_tag_offset_gt(const gr_tag_t & t1, const gr_tag_t & t2);

private:
	std::map<std::string, tag_deque > d_context_tag_map;
	gr_tag_t d_dummy_tag;




	tag_deque_it find_tag_less_than(int64_t offset,
			tag_deque & tag_deque);

	it_pair find_tags_in_range(int64_t start_offset, int64_t end_offset,
			tag_deque & tag_deque);

	void clean_tag_deque(tag_deque_it current_tag_it,
			tag_deque & tag_deque);

  protected:

  public:

	digital_ll_context_tag_manager();

	digital_ll_context_tag_manager(std::vector<std::string> context_keys);

	std::vector<gr_tag_t> get_latest_context_tags(int64_t offset);
	std::vector<gr_tag_t> get_latest_context_tags(int64_t start_offset, int64_t end_offset);

	void add_context_tag(gr_tag_t tag);



};

#endif /* INCLUDED_DIGITAL_LL_CONTEXT_TAG_MANAGER */
