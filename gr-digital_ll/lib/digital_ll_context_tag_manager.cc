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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <digital_ll_context_tag_manager.h>

#include <algorithm>

/*! \dontinclude digital_ll_context_tag_manager.
 *
 */

typedef digital_ll_context_tag_manager ctm;

static pmt::pmt_t DUMMY_SYM = pmt::pmt_string_to_symbol("dummy");

bool digital_ll_context_tag_manager::compare_tag_offset_lt(const gr_tag_t & t1, const gr_tag_t & t2)
{
	return t1.offset < t2.offset;
}

bool digital_ll_context_tag_manager::compare_tag_offset_gt(const gr_tag_t & t1, const gr_tag_t & t2)
{
	return t1.offset > t2.offset;
}

// don't use this
digital_ll_context_tag_manager::digital_ll_context_tag_manager()
{
	d_dummy_tag.offset = 0;
	d_dummy_tag.value = NULL;
	d_dummy_tag.srcid = DUMMY_SYM;
	d_dummy_tag.key = DUMMY_SYM;
}


digital_ll_context_tag_manager::digital_ll_context_tag_manager(std::vector<std::string> context_keys)
{
	std::vector<std::string>::iterator it;

	// preallocate a vector for each type of context key

	for(it=context_keys.begin(); it!=context_keys.end(); it++)
	{
		tag_deque empty_vec;
		d_context_tag_map[*it] = empty_vec;
	}

	d_dummy_tag.offset = 0;
	d_dummy_tag.value = NULL;
	d_dummy_tag.srcid = DUMMY_SYM;
	d_dummy_tag.key = DUMMY_SYM;

}

ctm::tag_deque_it digital_ll_context_tag_manager::find_tag_less_than(int64_t offset,
		ctm::tag_deque & tags)
{

	// if the deque is empty, we can't find a match.
	if( tags.empty() )
	{
		return tags.end();
	}
	// if the front tag's offset is greater than the offset we're looking for, we won't
	// find a match
	else if(tags.front().offset > offset)
	{
		return tags.end();
	}
	// if there's only one element, since it's not greater than the offset we're looking
	// for, it must be the match
	else if(tags.size() == 1)
	{
		return tags.begin();
	}
	// otherwise we search
	else
	{
		tag_deque_it it = tags.begin();
		while(it!=tags.end())
		{
			it++;
			// at least one of the tags is less than the offset, and there's more than one
			// tag, so we'll always find a matching tag.
			// if all of the tags are less than the offset, we should return the
			// last one. If not all of the tags are less than the offset, we should return
			// the tag just before the tag that first exceeds the offset
			if( (it==tags.end()) || (it->offset > offset) )
			{
				it--;
				return it;
			}

		}
		return it;
	}

}


ctm::it_pair digital_ll_context_tag_manager::find_tags_in_range(int64_t start_offset,
		int64_t end_offset, ctm::tag_deque & tags)
{
	// find the first element in the range (start_offset, end_offset]
	// note that the first element offset must be greater than start_offset
	ctm::it_pair tag_range;

	d_dummy_tag.offset = start_offset;

	tag_range.first = std::upper_bound(tags.begin(), tags.end(), d_dummy_tag,
			compare_tag_offset_lt);

	std::deque<gr_tag_t>::reverse_iterator rev_it;

	d_dummy_tag.offset = end_offset;
	rev_it = std::lower_bound(tags.rbegin(), tags.rend(), d_dummy_tag,
			compare_tag_offset_gt);

	//convert to forward iterator one item past the element pointed to by rev_it
	tag_range.second = rev_it.base();

	return tag_range;

}


void digital_ll_context_tag_manager::clean_tag_deque(ctm::tag_deque_it current_tag_it,
		ctm::tag_deque & tags)
{
	if( (current_tag_it != tags.end()) && (current_tag_it != tags.begin()) )
	{
		tags.erase(tags.begin(), current_tag_it);
	}
}


std::vector<gr_tag_t> digital_ll_context_tag_manager::get_latest_context_tags(int64_t offset)
{
	std::vector<gr_tag_t> out_tags;
	tag_deque_it current_tag_it;

	std::map<std::string, tag_deque >::iterator map_it;

	for( map_it=d_context_tag_map.begin(); map_it!=d_context_tag_map.end(); map_it++)
	{
		// only bother processing the vector if it is non empty
		if( !(map_it->second.empty()) )
		{
			current_tag_it = this->find_tag_less_than(offset, map_it->second);
			if( current_tag_it != map_it->second.end())
			{
				// if a valid tag was found, append it to the output vector and clean
				// up the tag deque to remove any tags older than the current tag
				out_tags.push_back(*current_tag_it);
				this->clean_tag_deque(current_tag_it,map_it->second);
			}
		}
	}
	return out_tags;
}


std::vector<gr_tag_t> digital_ll_context_tag_manager::get_latest_context_tags(int64_t start_offset,
		int64_t end_offset)
{
	std::vector<gr_tag_t> out_tags;
	tag_deque_it current_tag_it;
	it_pair tag_range;


	std::map<std::string, tag_deque >::iterator map_it;

	for( map_it=d_context_tag_map.begin(); map_it!=d_context_tag_map.end(); map_it++)
	{
		// only bother processing the vector if it is non empty
		if( !(map_it->second.empty()) )
		{
			// find the first tag
			current_tag_it = this->find_tag_less_than(start_offset, map_it->second);
			if( current_tag_it != map_it->second.end())
			{
				// if a valid tag was found, append it to the output vector and clean
				// up the tag deque to remove any tags older than the current tag
				out_tags.push_back(*current_tag_it);
				out_tags.rbegin()->offset=start_offset;
				this->clean_tag_deque(current_tag_it,map_it->second);
			}

			// now find all the tags in range (start_offset,end offset]
			// note that we're excluding the starting point since that will be covered by
			// the return value of find_tag_less_than
			tag_range = find_tags_in_range(start_offset,end_offset, map_it->second);

			// append found tags to outputs
			out_tags.insert(out_tags.begin(), tag_range.first, tag_range.second);
		}
	}
	return out_tags;
}

void digital_ll_context_tag_manager::add_context_tag(gr_tag_t tag)
{
	//only add allowed context keys
	std::string tag_key = pmt::pmt_symbol_to_string(tag.key);

	if (d_context_tag_map.count(tag_key) > 0)
	{
		d_context_tag_map[tag_key].push_back(tag);
	}
	return;
}
