#
# This file is part of ExtRaSy
#
# Copyright (C) 2013-2014 Massachusetts Institute of Technology
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
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
import abc
from collections import namedtuple
from collections import defaultdict
from copy import deepcopy
import cPickle
import itertools
import logging
from operator import itemgetter
import os
import sys
import time

# third party library imports
import numpy as np
import numpy.ma as ma

# project specific imports
from digital_ll import time_spec_t
from SortedCollection import SortedCollection



SlotParamTuple = namedtuple('SlotParamTuple', 'owner len offset type rf_freq bb_freq bw tx_gain')

GridUpdateTuple = namedtuple('GridUpdateTuple', 'owner type channel_num order rf_freq')


import time                                                

def timeit(method):

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print 'TIMER: %r:  %2.6f sec' % \
              (method.__name__, te-ts)
        return result

    return timed


#=========================================================================================
# Base class for Schedule Objects
#=========================================================================================        
class FrameScheduleBase(object):
    ''' 
    Defines the required behavior of a FrameSchedule-based object
    '''
    __metaclass__ = abc.ABCMeta
    
    tx_time=None
    frame_offset=None
    time_ref=None
    first_frame_num=None
    frame_num_ref=None
    valid=None
    
    def __init__(self, tx_time=None, frame_offset=None, time_ref=None, 
                 first_frame_num=None, frame_num_ref=None, valid=None):
        '''
        Initialize required data members
        '''
        if tx_time is not None:
            self.tx_time = time_spec_t(tx_time)
        
        self.frame_offset = frame_offset
        
        if time_ref is not None:
            self.time_ref = time_spec_t(time_ref)
        
        self.first_frame_num = first_frame_num
        self.frame_num_ref = frame_num_ref
        self.valid = valid

    
    @abc.abstractmethod
    def compute_frame(self, frame_num=None):
        '''
        Produce the requested frame configuration
        '''
        pass
    
    def compact(self):
        '''
        If possible, shrink how much space this object would take up in a beacon
        '''
        pass
    
    def expand(self):
        '''
        If compact is implemented, this is the inverse function
        '''
        pass
    

#=========================================================================================
# Simple Schedule Object
#=========================================================================================        
class SimpleFrameSchedule(FrameScheduleBase):
    ''' 
    Schedules of this type contain a frame_config structure and can compute the timestamp
    of a given frame number
    '''
    
    
    def __init__(self, frame_config, tx_time=None, frame_offset=None, time_ref=None, 
                 first_frame_num=None, frame_num_ref=None, valid=None,
                  ):
        '''
        Store frame config
        '''
        if frame_config is not None:
            if time_ref is None:
                time_ref = time_spec_t(frame_config["t0"])
        
        super(SimpleFrameSchedule, self).__init__(tx_time, frame_offset, time_ref, 
                                                  first_frame_num, frame_num_ref, 
                                                  valid)
        
        self._frame_config = deepcopy(frame_config)
    
    
    def compute_frame(self, frame_num=None):
        '''
        Produce the requested frame configuration
        '''
        if self.valid == False:
            frame_config = None
        else:
            if frame_num == None:
                frame_num = self.frame_num_ref
            
            frame_config = deepcopy(self._frame_config)
            frame_config["t0"] = self.time_ref + (frame_num-self.frame_num_ref)*frame_config["frame_len"]
            frame_config["t0_frame_num"] = frame_num
            frame_config["first_frame_num"] = self.first_frame_num
            frame_config["valid"] = self.valid
                    
        return frame_config
    
#=========================================================================================
# Grid Frame Schedule
#=========================================================================================        
class GridFrameSchedule(FrameScheduleBase):
    '''
    Schedules of this type assume that time and frequency are separated out into 
    a rectangular grid of time/frequency tiles. Time slots need not be adjacent.
    Channels in frequency must be adjacent. Time slots cannot overlap, and extend across
    all channels. 
    '''
    
    
    frame_len = None
    num_freq_slots = None
    num_time_slots = None
    slots = None
    time_ref = None
    frame_num_ref = None
    first_frame_num = None
    valid = None
    LinkTuple = namedtuple('LinkTuple', 'owner linktype')
    
#    slot_codes = {"beacon":1,
#                       "uplink":0,
#                       "downlink":2}
    
    old_frame_config = None
    
    def __init__(self, tx_time=None, frame_offset=None, time_ref=None, 
                 first_frame_num=None, frame_num_ref=None, valid=None,
                 frame_config=None, num_channels=1):
        
        # set up safe defaults that can be overwritten as needed
        self.first_frame_num = 0
        self.frame_num_ref = 0
        
        if frame_config is not None:
            
            self.frame_len = frame_config["frame_len"]
            self.slots = deepcopy(frame_config["slots"])
            self.num_time_slots = len(self.slots)
            
            if time_ref is None:
                self.time_ref = time_spec_t(frame_config["t0"])
            if valid is None:
                self.valid = frame_config["valid"]
            
            self.old_frame_config = self.compute_frame()
        
            
        self.num_freq_slots = num_channels
        
        # initialize params if specifically called out, otherwise load from frame config
        if time_ref is not None:
            self.time_ref = time_spec_t(time_ref)
        
        if frame_num_ref is not None:    
            self.frame_num_ref = frame_num_ref
            
        if first_frame_num is not None:
            self.first_frame_num = first_frame_num
        
        if valid is not None:
            self.valid = valid
            
        
        
    def compute_frame(self, frame_num=None):
        
        if frame_num is None:
            frame_num = self.frame_num_ref
        
        
        if frame_num < self.first_frame_num:
            frame_config = deepcopy(self.old_frame_config)
            frame_delta = frame_num - frame_config["t0_frame_num"]
            frame_config["t0"] = frame_config["t0"] + frame_config["frame_len"]*frame_delta
            frame_config["t0_frame_num"] = frame_num
        else:
            frame_config = {"frame_len":self.frame_len,
                            "slots":deepcopy(self.slots),
                            "first_frame_num":self.first_frame_num,
                            "valid":self.valid}
        
        
            frame_delta = frame_num - self.frame_num_ref
            
            # TODO: Round times to nearest sample
            frame_config["t0"] = self.time_ref + self.frame_len*frame_delta
            frame_config["t0_frame_num"] = frame_num
            
                 
        return frame_config

    def update_grid(self, grid_updates, first_frame_num):
        '''
        Update the slots.
        
        grid_updates is expected to be a dictionary keyed by slot number containing 
        (owner, type, channel_num) named tuples
        '''
        
        for k, slot in enumerate(self.slots):
            if k in grid_updates:
                
                self.slots[k] = slot._replace(owner=grid_updates[k].owner, 
                                              type=grid_updates[k].type,
                                              bb_freq=int(grid_updates[k].channel_num),
                                              rf_freq=grid_updates[k].rf_freq)
                
#            # if slot was not assigned, set owner to -1, type to uplink, and channel to 0
#            elif self.slots[k].type != "beacon":
#                self.slots[k] = slot._replace(owner=-1, 
#                                              type="uplink",
#                                              bb_freq=0)
        self.first_frame_num = first_frame_num
        
    def replace_grid(self, grid_updates, first_frame_num):
        '''
        Update the slots.
        
        grid_updates is expected to be a dictionary keyed by slot number containing 
        (owner, type, channel_num) named tuples
        '''
        
        for k, slot in enumerate(self.slots):
            if k in grid_updates:
                
                self.slots[k] = slot._replace(owner=grid_updates[k].owner, 
                                              type=grid_updates[k].type,
                                              bb_freq=int(grid_updates[k].channel_num),
                                              rf_freq=grid_updates[k].rf_freq)
                
            # if slot was not assigned, set owner to -1, type to uplink, and channel to 0
            elif self.slots[k].type != "beacon":
                self.slots[k] = slot._replace(owner=-1, 
                                              type="uplink",
                                              bb_freq=0)
        self.first_frame_num = first_frame_num
        
    def store_tx_gain(self, owner, linktype, gain):
        '''
        Update the gain setting for the current and next schedules by owner and link type
        '''    
        for k, slot in enumerate(self.slots):
            if slot.owner == owner and slot.type == linktype:
                self.slots[k] = slot._replace(tx_gain=gain)
            
        for k, slot in enumerate(self.old_frame_config["slots"]):
            if slot.owner == owner and slot.type == linktype:
                self.old_frame_config["slots"][k] = slot._replace(tx_gain=gain)    
                
    
    def get_unique_links(self):
        '''
        Return a list of unique owner-link type tuples 
        ''' 
        
        unique_links = set()
        
        # add links from the 'next' frame config
        for slot in self.slots:
            unique_links.add(self.LinkTuple(owner=slot.owner, linktype=slot.type))
        
        # add links from the previous frame config
        for slot in self.old_frame_config["slots"]:
            unique_links.add(self.LinkTuple(owner=slot.owner, linktype=slot.type))   
        
        return list(unique_links)
    
    def get_uplink_gain(self, owner):
        '''
        Get the uplink gain associated with an owner
        '''
        uplink_gain = None
        
        # search current schedule for an uplink slot with owner id matching owner
        for slot in self.old_frame_config["slots"]:
            if slot.owner == owner and slot.type == "uplink":
                uplink_gain = slot.tx_gain    
        
        # if the uplink gain wasn't found yet, search the next schedule 
        if uplink_gain is None:  
            for slot in self.slots:
                if slot.owner == owner and slot.type == "uplink":
                    uplink_gain = slot.tx_gain
        
        return uplink_gain
    

    def store_current_config(self):
        self.old_frame_config = self.compute_frame()
        
    
    def compact(self):
        '''
        Shrink this object so it can be pickled more efficiently
        '''
        if self.time_ref is not None and hasattr(self.time_ref, 'to_tuple'):
            self.time_ref = self.time_ref.to_tuple()
            
        if self.tx_time is not None and hasattr(self.tx_time, 'to_tuple'):
            self.tx_time = self.tx_time.to_tuple()
            
        
        if self.slots is not None:
            for k, slot in enumerate(self.slots):
                self.slots[k] = tuple(slot)
                
        if self.old_frame_config is not None:
            for k, slot in enumerate(self.old_frame_config["slots"]):
                self.old_frame_config["slots"][k] = tuple(slot)
                
            if hasattr(self.old_frame_config["t0"], 'to_tuple'):
                self.old_frame_config["t0"] = self.old_frame_config["t0"].to_tuple()
                
                
                
    def expand(self):
        '''
        Reverse a compact operation
        '''             
        if self.time_ref is not None:
            self.time_ref = time_spec_t(self.time_ref)
            
        if self.tx_time is not None:
            self.tx_time = time_spec_t(self.tx_time)
            
        if self.slots is not None:
            for k, slot in enumerate(self.slots):
                self.slots[k] = SlotParamTuple(*slot)
                
        if self.old_frame_config is not None:
            for k, slot in enumerate(self.old_frame_config["slots"]):
                self.old_frame_config["slots"][k] = SlotParamTuple(*slot)
                
            self.old_frame_config["t0"] = time_spec_t(self.old_frame_config["t0"])       
           
    
    @staticmethod
    def initialize_database_table(db_int):
        
        drop_tables_sql = """
        DROP TABLE IF EXISTS grid_updates;
        """
        
        grid_updates_table_sql = """
        CREATE TABLE IF NOT EXISTS grid_updates(
            frame_num INTEGER PRIMARY KEY NOT NULL,
            data TEXT NOT NULL ,
            FOREIGN KEY (frame_num) REFERENCES frame_nums(frame_num) ON DELETE CASCADE
            );   
        """

        with db_int.con as c:
            
            c.executescript(drop_tables_sql)
            c.executescript(grid_updates_table_sql)
        
    
        

#    @timeit
    def store_update(self, frame_num, grid_updates, db_int):
        
        with db_int.con as c:
            
            # store this grid update to database    
            c.execute("""
            insert into grid_updates
            (frame_num, data) values
            (?,?)""",
            (frame_num,cPickle.dumps(grid_updates)))
           
#            # remove old grid updates
#            c.execute("""
#            DELETE FROM grid_updates
#            WHERE rowid NOT IN(SELECT rowid FROM grid_updates
#            ORDER BY rowid DESC LIMIT 4)""") 
#        
    
      
        
#=========================================================================================
# Patterned Frame Schedule
#=========================================================================================        
class PatternFrameSchedule(FrameScheduleBase):
    '''
    Schedules of this type assume that time and frequency are separated out into 
    a rectangular grid of time/frequency tiles. Time slots need not be adjacent.
    Channels in frequency must be adjacent. Time slots cannot overlap, and extend across
    all channels. Each pattern of time/frequency/owner allocations is mapped to an index.
    
    The action space stored in _action_space must include at least one time/frequency
    allocation pattern or this schedule will not work
    
    '''
    stateTup = namedtuple('stateTup', 'time_ref frame_num_ref first_frame_num action_ind epoch_num')
    LinkTuple = namedtuple('LinkTuple', 'owner linktype')
    varTup = namedtuple('varTup', ('frame_offset tx_time valid tx_gain gains slot_bw schedule_seq max_scheds rf_freq'))
    
    PatternTuple = namedtuple("PatternTuple", 'owner len offset type bb_freq')
    
    
    gains = None
    slot_bw = None
    schedule_seq = None
    max_scheds = None
    
    # this variable will be tricky: It'll be modified as a class level variable, and won't
    # be sent across during pickle/unpickle operations but will rely on the classes on
    # remote machines being configured properly
    _action_space = None
    
    sync_space = None
    num_actions = None
    
    def __init__(self, tx_time=None, frame_offset=None, time_ref=None, 
                 first_frame_num=None, frame_num_ref=None, valid=None,
                 tx_gain=None, max_schedules=2, action_ind=None,
                 rf_freq=None, slot_bw=0.0, epoch_num=None):
        
        if tx_time is not None:
            self.tx_time = time_spec_t(tx_time)
        else:
            self.tx_time = None
            
        self.frame_offset = frame_offset
        
        self.valid = valid
        
        
        # this is the list of schedule states this schedule object knows about.
        # The schedules are ordered by first_frame_num
        self.schedule_seq = SortedCollection(key=itemgetter(2))  
        self.max_scheds = max_schedules
        
        # use a default dict so slots with no initialized gain will use the default tx
        # gain 
        
        self.tx_gain = tx_gain
        self.gains = defaultdict(self.constant_factory(self.tx_gain))
        
        # set default values for all controllable parameters. These are what will be used
        # if the action space doesn't specify a value
        self.rf_freq = rf_freq
        
        self.slot_bw = slot_bw
        
        first_state = (time_ref, frame_num_ref, first_frame_num, action_ind, epoch_num)
        # only add the initial state if all the necessary params are defined
        if all( v is not None for v in first_state):
            self.add_schedule(*first_state)
            
    @staticmethod    
    def constant_factory(value):
            return itertools.repeat(value).next 
            
    def add_schedule(self, time_ref, frame_num_ref, first_frame_num, action_ind, epoch_num=None):
        '''
        Add a schedule to the end of the schedule queue, and if the queue is over 
        capacity, pop off the oldest element
        '''
        self.schedule_seq.insert((time_spec_t(time_ref).to_tuple(), frame_num_ref, first_frame_num, action_ind, epoch_num))
        
        if len(self.schedule_seq) > self.max_scheds:
            # find the first element in the list when sorted by frame number
            self.schedule_seq.remove(self.schedule_seq[0])
            
                    
    def compute_frame(self, frame_num=None):
        '''
        Given a frame number, produce an individual frame configuration
        '''
    
        
        
        if frame_num is None:
            sched = self.stateTup(*self.schedule_seq[0])
        
        else:
            try:
                sched_tup = self.schedule_seq.find_le(frame_num)
            except ValueError:
                sched_tup = self.schedule_seq[0]
            sched = self.stateTup(*sched_tup)
        
        #print "Frame num is %i, action ind is %i"%(frame_num, sched.action_ind)
        #print "schedule sequence is %s"%self.schedule_seq
            
        action = self._action_space[sched.action_ind]     
#        if "pattern" not in action:
#            # TODO: Make a better exception for when there aren't any patterns
#            raise KeyError("Expected at least one pattern object in the action space")  
#        else:
        frame_len = action["frame_len"]
        frame_delta = frame_num - sched.frame_num_ref
        
        t0 = time_spec_t(sched.time_ref) + frame_len*frame_delta
        
        frame_config = {"frame_len":frame_len,
                        "t0":t0,
                        "t0_frame_num":frame_num,
                        "first_frame_num":sched.first_frame_num,
                        "valid":self.valid,
                        "epoch_num":sched.epoch_num,
                        }
        
        # get all the parameters needed for computing each slot in frame_config
        
        if "rf_freq" in action:
            rf_freq = action["rf_freq"]
        else:
            rf_freq = self.rf_freq
        
        # get the list of gains per slot
        act_slots = action["slots"]
        gains = [ self.gains[(s.owner, s.type)] for s in act_slots]  
        
         
        slots = [SlotParamTuple(owner=s.owner, len=s.len, offset=s.offset, type=s.type,
                                rf_freq=rf_freq, bb_freq=s.bb_freq, bw=self.slot_bw,
                                tx_gain=gain) for gain, s in zip(gains, act_slots)]
        
        frame_config["slots"] = slots

        for s in slots:
            if s.type == "beacon":
                pass
                #print ("frame at time %s beacon slot at offset %f fr freq %f and "
                #       +"channel %f")%(frame_config["t0"], s.offset, s.rf_freq, s.bb_freq)
       
        return frame_config

     
    def store_current_config(self):
        '''
        No longer needed
        '''
        pass

    def store_tx_gain(self, owner, linktype, gain):
        '''
        Update the gain setting for the current and next schedules by owner and link type
        '''    
        self.gains[(owner, linktype)] = gain   
                
    
    def get_unique_links(self, frame_num):
        '''
        Return a list of unique owner-link type tuples 
        ''' 
        # get the schedule in effect for frame_num
        
        try:
            sched = self.stateTup(*self.schedule_seq.find_le(frame_num))
        except ValueError:
            # didn't find any frames less than or equal frame number, so return an empty
            # list
            return list()
            
        action = self._action_space[sched.action_ind]
        
        unique_links = set()
        # add links from the 'next' frame config
        for s in action["pattern"]["slots"]:
            unique_links.add(self.LinkTuple(s.owner, s.type))  
        
        return list(unique_links)
    
    def get_uplink_gain(self, owner):
        '''
        Get the uplink gain associated with an owner
        '''

        uplink_gain = self.gains[(owner, "uplink")]    
        
        return uplink_gain
    @property    
    def time_ref(self):
        return time_spec_t(self.schedule_seq[-1][0])
    
    @time_ref.setter
    def time_ref(self, value):
        # ignore values here until redesign makes this unnecessary
        pass
     
    def __getstate__(self):
        '''
        load all the instance variables into a namedtuple and then return that as 
        a plain tuple to cut down on the size of the pickled object
        '''
        try:
            
            inst_vars = self.__dict__.copy()
            inst_vars["schedule_seq"] = list(inst_vars["schedule_seq"])
            inst_vars["gains"] = dict(inst_vars["gains"])
            temp_tup = self.varTup(**inst_vars)
            

        except TypeError:
            found_fields = inst_vars.keys()
            expected_fields = self.varTup._fields
            raise TypeError(("The beacon class does not support adding or removing " +
                             "variables when pickling. " + 
                             "Found %s, expected %s" % (found_fields, expected_fields)))
        

                
        return tuple(temp_tup) 
            
    def __setstate__(self,b):
        '''
        load b, which will be a plain tuple, into a namedtuple and then convert that to
        this instance's __dict__ attribute
        '''
        try:
            temp_tup = self.varTup(*b)
            self.__dict__.update(temp_tup._asdict())
            
            self.schedule_seq = SortedCollection(temp_tup.schedule_seq,
                                                 key=itemgetter(2))
            self.gains = defaultdict(self.constant_factory(self.tx_gain))
            self.gains.update(temp_tup.gains)
            
        except TypeError:
            raise TypeError(("The beacon class does not support adding or removing " +
                             "variables when pickling"))

    def __cmp__(self, other):
        simp_vals_equal = all([ self.__dict__[key] == val for key,val 
                               in other.__dict__.iteritems() 
                               if (key != "gains") and (key != "schedule_seq")])
        
        gains_equal = dict(self.__dict__["gains"]) == dict(other.__dict__["gains"])
        seq_equal = list(self.__dict__["schedule_seq"]) == list(other.__dict__["schedule_seq"])
         
        return all([simp_vals_equal, gains_equal, seq_equal])

    def __eq__(self, other): 
        simp_vals_equal = all([ self.__dict__[key] == val for key,val 
                               in other.__dict__.iteritems() 
                               if (key != "gains") and (key != "schedule_seq")])
        
        gains_equal = dict(self.__dict__["gains"]) == dict(other.__dict__["gains"])
        seq_equal = list(self.__dict__["schedule_seq"]) == list(other.__dict__["schedule_seq"])
         
        return all([simp_vals_equal, gains_equal, seq_equal])
    
    def __repr__(self):
        
        s = ["PatternFrameSchedule(",
             "frame_offset=%r"%self.frame_offset,
             ", tx_time=%r"%self.tx_time,
             ", valid=%r"%self.valid,
             ", tx_gain=%r"%self.tx_gain,
             ", gains=%r"%dict(self.gains),
             ", slot_bw=%r"%self.slot_bw,
             ", schedule_seq=%r"%list(self.schedule_seq),
             ", max_scheds=%r"%self.max_scheds,
             ", rf_freq=%r"%self.rf_freq,
             ")"]
        
        repr_str = ''.join(s)    
        
        return repr_str
    
    @staticmethod
    def check_types(slot, fields):
        # convert each entry to the correct type
        types_valid = True
        failed_fields = []
        #print "converting row: %s" % row
        for field_name in slot._fields:
            
            if not isinstance(getattr(slot, field_name), fields[field_name]):
                wrong_type = type(getattr(slot, field_name))
                failed_fields.append((field_name, fields[field_name], wrong_type))
                types_valid = False
                
        return types_valid, failed_fields
       
    
    @staticmethod
    def load_pattern_set_from_file(pattern_file, set_name, fs):
        dev_log = logging.getLogger('developer')
        
        # sanitize path name and pull apart path from base file name
        abs_pattern_file = os.path.expandvars(os.path.expanduser(pattern_file))
        abs_pattern_file = os.path.abspath(abs_pattern_file)
        abs_pattern_dir = os.path.dirname(abs_pattern_file)
        pattern_basename = os.path.basename(abs_pattern_file)
        
        if os.path.isdir(abs_pattern_dir):
            sys.path.append(abs_pattern_dir)
        else:
            dev_log.error("pattern directory does not exist: %s",abs_pattern_dir)
            return False
        
        try:
            sanitized_pattern_file = os.path.splitext(pattern_basename)[0]
            group_module = __import__(sanitized_pattern_file)
            dev_log.info("using pattern sets from %s", group_module.__file__)
            
            pattern_set = getattr(group_module, set_name)
        except ImportError:
            dev_log.error("Could not import %s from directory %s", 
                          pattern_basename, abs_pattern_dir)
            raise ImportError
        except AttributeError:
            dev_log.error("Pattern set %s not found in file %s", 
                          set_name, group_module.__file__)
            raise AttributeError
        
        slot_fields = dict([("owner",int),
                            ("len",float),
                            ("offset",float),
                            ("type",str),
                            ("rf_freq",float),
                            ("bb_freq",int),
                            ("bw",float),
                            ("tx_gain",float),])
        
        all_rf_freqs_found = True
        
        for m, frame in enumerate(pattern_set):
            # check that the pattern set includes rf_frequency for each action
            
            if "rf_freq_ind" not in frame:
                
                dev_log.warning("RF frequency index not specified in action number %i in Pattern set %s in file %s", 
                              m, set_name, group_module.__file__)
                all_rf_freqs_found = False
                
            
            for n, slot in enumerate(frame["slots"]):
                types_valid, failed_fields = PatternFrameSchedule.check_types(slot, slot_fields)
                
                if not types_valid:
                    for failure in failed_fields:
                        
                        dev_log.warning("Field %s in Slot %i in frame index %i failed field type validation. Type was %s but should be %s",
                                        failure[0], n, m, failure[2], failure[1])
            
            # log an error and raise an exception if there's a missing rf frequency field        
            if not all_rf_freqs_found:
                dev_log.error("At least one action in the pattern file was missing an rf_freq_ind field")
                raise AttributeError
       
        
        
        # sort slots by order of offset
        for m, frame in enumerate(pattern_set):
            frame["slots"].sort(key=lambda slot: slot.offset)
            frame_len_rounded = round(frame["frame_len"]*fs)/fs

        
        # 
        # enforce slot/frame boundaries occur at integer samples
        #
        
        # check that frame len is at an integer sample
            if frame["frame_len"] != frame_len_rounded:
                dev_log.warn("rounding frame len from %.15f to %.15f", frame["frame_len"], 
                             frame_len_rounded)
                pattern_set[m]["frame_len"] = frame_len_rounded
            
        try:    
        
            # do a limited amount of error checking    
            for ind, frame in enumerate(pattern_set):
                for num, slot in enumerate(frame["slots"]):
                
                    offset_rounded = round(slot.offset*fs)/fs
                    len_rounded = round(slot.len*fs)/fs
                    
                    if slot.offset != offset_rounded:
                        dev_log.warn("rounding frame %d slot %d offset from %.15f to %.15f",
                                     ind, num, slot.offset,offset_rounded)
                        
                    if slot.len != len_rounded:
                        dev_log.warn("rounding frame %d slot %d len from %.15f to %.15f", 
                                     ind, num, slot.len, len_rounded)
                    
                    # more precision fun
                    end_of_slot = round( (offset_rounded + len_rounded)*fs)/fs        
                    
                    if end_of_slot > frame["frame_len"]:
                        raise InvalidFrameError(("slot %d with offset %f and len %f extends past " + 
                                                 "the end of the frame, len %f") % (num, slot.offset,
                                                  slot.len, frame["frame_len"]))
                        
                    pattern_set[ind]["slots"][num] = slot._replace(offset=offset_rounded, 
                                                                    len=len_rounded)
        
        except InvalidFrameError, err:
            dev_log.error("Invalid Frame: %s", err)
            raise
        

#        self.__class__.pattern_set = deepcopy(pattern_set)
        return pattern_set
    
    
    @classmethod
    def store_action_space(self, pattern_set, owner_ids, rf_freqs, **kwargs):
        dev_log = logging.getLogger('developer')
        
        ps_update = deepcopy(pattern_set)
        
        beacon_chans = set()
        
        # change the owner in each slot to the corresponding owner id. 
        # owner 0 becomes owner_ids[0], owner 1 becomes owner_ids[1], etc
        # Also record all possible beacon channels
        for f_ind, frame in enumerate(pattern_set):
            
            if frame["rf_freq_ind"] >= len(rf_freqs):
                dev_log.warning("Pattern set specifies frequency index of %i but only %f frequencies are in rf freq list. Wrapping index",
                                frame["rf_freq_ind"], len(rf_freqs))
                
            ps_update[f_ind]["rf_freq"] = rf_freqs[frame["rf_freq_ind"]%len(rf_freqs)]
            
            for s_ind, slot in enumerate(frame["slots"]):
                if slot.owner < len(owner_ids):
                    ps_update[f_ind]["slots"][s_ind] = slot._replace(owner=owner_ids[slot.owner])
                    
                if slot.type == "beacon":
                    beacon_chans.add(slot.bb_freq)
                    
#        # get all the combinations of input parameter lists
#        prod = itertools.product(ps_update, *kwargs.itervalues())
        
#        labels = ["pattern"]
#        labels.extend(kwargs.keys())
        
#        # store the actions as a list of dictionaries with labeled parameters
#        # the pattern is stored with the key "pattern", other parameters are stored 
#        # by their keyword argument
#        action_space = [dict(zip(labels, action)) for action in prod]
        
        # only use parameters from the pattern set file for now
        action_space = ps_update
        
        # store the action space to the class variable
        # remember, as a class method, self refers to the class, not the instance
        self._action_space = deepcopy(action_space)
        
        self.num_actions = len(self._action_space)
        
        # configure sync space
        sync_labels = ["beacon_chan", "rf_freq"]      
        sync_prod = itertools.product(beacon_chans, rf_freqs)
        self.sync_space = [dict(zip(sync_labels, action)) for action in sync_prod]

    def log_action_space(self):
        action_space = deepcopy(self._action_space)
        [act.update({"action_index":ind}) for ind, act in enumerate(action_space)]
        
        action_list = [{"action":act} for act in action_space]
           
        for act in action_list:
        
            xml_str =  lincolnlog.dict_to_xml_newlines(act, 1)
            print xml_str
            
    def get_action_space(self):
        action_space = deepcopy(self._action_space)
        
        return action_space
    
    @classmethod
    def set_sync_space(self, action_labels, action_tuples):
        '''
        Directly specify the list of actions to use during sync instead of deriving from
        the action space
        '''
        
        # assume action labels is a list of strings that describe what each element in 
        # an action tuple corresponds to
        
        # assume action_tuples is a list of action tuples. For example, each tuple in 
        # the tuple list for action_labels = ['beacon_chan', 'rf_freq'] would look like
        # this: ( beacon_chan0, rf_freq0) 
        
        # configure sync space        
        self.sync_space = [dict(zip(action_labels, action)) for action in action_tuples]
        
class InvalidFrameError(Exception):
    """Invalid Frame Error."""
    pass  