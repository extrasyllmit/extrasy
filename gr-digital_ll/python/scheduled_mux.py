#
# This file is part of ExtRaSy
#
# Copyright (C) 2013-2014 Massachusetts Institute of Technology
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# standard python library imports
import logging

# third party library imports
from gnuradio import gr

# project specific imports
from digital_ll import slot_selector
from digital_ll import time_spec_t


class scheduled_mux(gr.hier_block2):
    """A hier2 block with M outputs, where data is forwarded through output m according to a schedule."""
    def __init__(self, item_size, num_outputs, fs, schedule_list=None):
        """
        Selector constructor.
        @param item_size the size of the gr data stream in bytes
        @param num_outputs the number of outputs (integer)
        @param schedule_list list of schedules, one per output.
        """
        gr.hier_block2.__init__(
            self, 'selector',
            gr.io_signature(1, 1, item_size),
            gr.io_signature(num_outputs, num_outputs, item_size),
        )
        
        self._dev_logger = logging.getLogger('developer')
        
        #slot selector blocks
        self.select_blocks = []
        for i in range(num_outputs):
            if hasattr(schedule_list, "len") and ( len(schedule_list) >i):                
                frame_len, slot_lens, slot_offsets, frame_t0, stream_t0 = schedule_list[i]
            else:
                frame_len = 1.333
                
                if i == 0:
                    slot_lens = [1.0]
                else:
                    slot_lens = [0.0]
                
                slot_offsets = [0.0] 
                slot_nums = [0]
                frame_t0 = time_spec_t(0) 
                stream_t0 = time_spec_t(0) 
                
                
                
            self.select_blocks.append(slot_selector(item_size, frame_len, slot_lens, 
                                                    slot_offsets, 
                                                    frame_t0.int_s(), frame_t0.frac_s(), 
                                                    stream_t0.int_s(), stream_t0.frac_s(), 
                                                    fs ))
            
    
        #connections
        for i in range(num_outputs): 
            self.connect(self, self.select_blocks[i], (self, i))

        self.item_size = item_size 
        self.num_outputs = num_outputs


    def set_schedules(self, schedule_list):
        """
        Update the schedule for each select block.
        Should be a list of tuples, each containing
        frame_len, slot_lens, slot_offsets, slot_nums, (frame_t0_int_s, frame_t0_frac_s)
        """ 
        self._dev_logger.debug("Schedule Change: new schedule is %s",
                                    schedule_list)
        for i in range(len(schedule_list)):
            frame_len, slot_lens, slot_offsets,frame_t0= schedule_list[i]
            (frame_t0_int_s, frame_t0_frac_s) = frame_t0
            
            self.select_blocks[i].set_schedule(frame_len, slot_lens, slot_offsets, 
                                               frame_t0_int_s, frame_t0_frac_s)
            
    def test_schedules_off(self):
        """
        debug code only
        """
        sched0 = ( 2.0, [2.0], [0.0], time_spec_t(0))
        sched1 = ( 2.0, [0], [0.0], time_spec_t(0))
        sched_list = [sched0, sched1]
        
        self.set_schedules(sched_list)
        
    def test_schedules_on(self):
        """
        debug code only
        """
        sched0 = ( 2.0, [2.0], [0.0], time_spec_t(0))
        sched1 = ( 2.0, [2.0], [0.0], time_spec_t(0))
        sched_list = [sched0, sched1]
        
        self.set_schedules(sched_list)