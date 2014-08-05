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
from collections import defaultdict
from collections import namedtuple
from copy import deepcopy
import cPickle
import struct
import logging
from lxml import etree
import math
from math import floor
import os
import pickle
import Queue
from threading import Semaphore
import time

# third party library imports
from gnuradio import gr
from gruel import pmt

import numpy

# project specific imports
import digital_ll
from digital_ll import lincolnlog
from digital_ll import packet_utils2
from digital_ll import time_spec_t
from digital_ll.lincolnlog import dict_to_xml
from FrameSchedule import SimpleFrameSchedule
from FrameSchedule import SlotParamTuple
from FrameSchedule import timeit


# choose what protocol to use in pickling: 0 is normal default, 
# highest protocol (currently 2) uses more efficient binary format
PICKLE_PROT = pickle.HIGHEST_PROTOCOL
    
tdma_types_to_ints = {"other":0, 
                      "beacon":1, 
                      "data":2, 
                      "keepalive":3,
                      "feedback":4,
                      "dummy":5}    


# define the header format
# ! means network byte order
# each H is an unsigned short (2 bytes)
TDMA_HEADER_FORMAT = '!HHHHHHHHHdddHH4s'
TDMA_HEADER_MAX_FIELD_VAL = 2**16-1
TDMA_HEADER_LEN = struct.calcsize(TDMA_HEADER_FORMAT)
# from source code analysis
PHY_HEADER_LEN = 92
#'': 1333000000.0, '': 1, '': 1000000.0, '': 0, '': 0, '': 1, '': 0, 'linkdirection': 'down'

TDMA_HEADER_NAMES =  ('packetid pad_bytes fromID toID pktCode phyCode macCode '+
                      'sourceID destinationID rfcenterfreq frequency ' +
                      'bandwidth timeslotID frameID linkdirection')

TdmaHeaderTuple = namedtuple('TdmaHeaderTuple', TDMA_HEADER_NAMES)

class beacon_consumer(gr.sync_block):

    _beacon_timeout = None
    _beacon_list = None
    _schedule_valid = None
    _schedule = None
    _base_id = None # this is the id of the base station to listen to
    _beacon_lock = None
    _types_to_ints = None
    _ints_to_types = None
    _max_beacons = None
    _min_beacons = None
    _has_sync = None
    _sched_lock = None
    
  
    def __init__(self, options, overwrite_metadata=False):
        gr.sync_block.__init__(
            self,
            name = "beacon consumer",
            in_sig = [numpy.complex64],
            out_sig = None)
        
        self.dev_log = logging.getLogger('developer')
        
        self._types_to_ints = dict(tdma_types_to_ints)
        self._ints_to_types = dict()
        # map from ints back to slot types
        for key in self._types_to_ints:
            self._ints_to_types[self._types_to_ints[key]] = key
            
        # get parameters from options object
        self._beacon_timeout = options.beacon_sync_timeout
        self._min_beacons = options.min_sync_beacons
        self._max_beacons = options.max_sync_beacons
        self._base_id = options.base_station_mac_address
        self._beacon_error_thresh = options.max_beacon_error
        
        # if true, use measured values for metadata fields when available
        self._overwrite_metadata = overwrite_metadata
        
        self._beacon_list = []
        self._schedule_valid = False
        
        self._beacon_lock = Semaphore()
        self._sched_lock = Semaphore()
        
        self._has_sync = False
        
        self.found_time = False
        self.found_rate = False
        
        self.in_time_cal = True
        self.time_sync_offset = None
        
        # add timing monitoring code
        self.monitor_timing = True
        if self.monitor_timing == True:
            self.wall_time_window_start = None
            self.wall_time_deltas = []
            self.poll_interval = 5
        
        
        # don't propagate any tags, this block handles them manually
        self.set_tag_propagation_policy(gr.gr_block.TPP_DONT)
        
        self.IN_PORT = pmt.from_python('in')
        self.SCHEDULE_OUT_PORT = pmt.from_python('sched_out')
        self.TIME_CAL_OUT_PORT = pmt.from_python('time_cal_out')
        
        # register input ports
        self.message_port_register_in(self.IN_PORT)
        self.set_msg_handler(self.IN_PORT, self.beacon_callback)
        
        # register outgoing message ports
        self.message_port_register_out(self.SCHEDULE_OUT_PORT)
        self.message_port_register_out(self.TIME_CAL_OUT_PORT)
        
        self._dev_logger = logging.getLogger('developer')
        self._ll_logging     = lincolnlog.LincolnLog(__name__)
            
    def add_options(normal, expert):
        """
        Adds beacon consumer options to the Options Parser
        """
        
        normal.add_option("--beacon-sync-timeout", default=20, type="eng_float",
                          help=("Maximum duration in seconds to retain beacons " +
                                "[default=%default]"))
        normal.add_option("--min-sync-beacons", default=2, type="int",
                          help=("Number of received beacons needed to declare sync " +
                                "[default=%default]"))
        normal.add_option("--max-sync-beacons", default=10, type="int",
                          help=("Maximum number of beacons to keep for analysis " +
                                "[default=%default]"))
        normal.add_option("--base-station-mac-address", default=1, type="int",
                          help=("Node ID of the base station " +
                                "[default=%default]"))
        normal.add_option("--max-beacon-error", default=.01, type="eng_float",
                          help=("Maximum allowed magnitude of beacon timing error " +
                                "[default=%default]"))
        
    # Make a static method to call before instantiation
    add_options = staticmethod(add_options)
    
    
    def log_my_settings(self, indent_level,logger):
        '''
        Write out all initial parameter values to XML formatted file
        '''
        section_indent = indent_level
        
        # top level mac section param values
        params = {"beacon_timeout":self._beacon_timeout,
                  "min_beacons": self._min_beacons,
                  "max_beacons": self._max_beacons,
                  "base_id":self._base_id,
                  "beacon_error_thresh":self._beacon_error_thresh,
                  }
        logger.info(dict_to_xml(params, section_indent))
    
        
    def time_cal_is_successful(self):
        if self.time_sync_offset is None:
            return False
        else:
            return True
    
    def set_time_calibration_complete(self):
        self._dev_logger.debug("setting time cal complete")
        self.in_time_cal = False
        
    def schedule_is_valid(self):
        return self._schedule_valid
    
    #@timeit
    def beacon_callback(self, ok, payload, timestamp, channel):
        
        #self._dev_logger.debug("raw beacon int %ld frac %f",timestamp[0], timestamp[1])
        beacon_ts = time_spec_t(*timestamp)
        
        # do timing
        if self.monitor_timing == True:
                wall_start_ts = time.time()
                if self.wall_time_window_start is None:
                    self.wall_time_window_start = wall_start_ts
                
                
        
        self._dev_logger.debug("beacon callback called for packet timestamp %s",beacon_ts)
        if ok:
            self._dev_logger.debug("beacon passes CRC")
            meta, data = unpack_payload(payload)
            
            if meta is None:
                meta = {}
        
            meta["crcpass"] = True
            
            beacon_data = None
            
            # check if this is a beacon packet
            if self._ints_to_types[meta["pktCode"]] == "beacon":
                if meta["fromID"] == self._base_id:
                    self.dev_log.info("beacon found on channel %i", channel)
                    beacon_data = self.process_as_beacon(meta, data)
                else:
                    self.dev_log.warn("Dropping beacon packet with incorrect fromID")
            else:
                #self._dev_logger.debug("packet was not a beacon")
                beacon_data = None
            
            # beacons should have different access code from data packets so there should
            # only be beacons coming through here
            # however, if something makes it through but doesn't have a packet type of 
            # beacon, or if there's a problem extracting the beacon, the beacon data will 
            # be none
            if beacon_data is not None:
                self._dev_logger.debug("beacon with tx timestamp %s found at timestamp %s",
                                        beacon_data.tx_time, beacon_ts)
                
                self._dev_logger.debug("waiting to acquire beacon lock")
                self._beacon_lock.acquire()
                self._dev_logger.debug("beacon lock acquired")
                # only add beacon if its timing error is below some threshold
                ts_error = float(beacon_ts - beacon_data.tx_time)
                self._dev_logger.info("beacon_timing_error:%f error_thresh:%f", ts_error,self._beacon_error_thresh)
                
                if self.in_time_cal and not self.time_cal_is_successful():
                    self._dev_logger.debug("running time calibration")
                    self.do_time_calibration(ts_error)
                elif not self.in_time_cal:
                
                    # overwrite packet metadata with measured values
                    if self._overwrite_metadata:
                        meta["frequency"] = channel
                        
                
                    if abs(ts_error) < self._beacon_error_thresh:
                        self._beacon_list.append( (beacon_ts, meta, beacon_data ))
                        self._dev_logger.debug("adding beacon to list. in time cal: %s  time cal is successful: %s",
                                               self.in_time_cal,self.time_cal_is_successful())
                    else:
                        self._dev_logger.warning( ("rejecting beacon: error of %f s was too " +
                                                   "large. Tx timestamp %s found at " +
                                                   "timestamp %s") , ts_error, 
                                                   beacon_data.tx_time, beacon_ts)
                    
                self._dev_logger.debug("culling stale beacons: current time %s, timeout %s",
                                       beacon_ts, self._beacon_timeout)

                self.cull_stale_beacons(beacon_ts)
                
                # get a copy of the beacon list so we can release the beacon lock and
                # process the beacon list without blocking other threads 
                # threads
                beacon_list = list(self._beacon_list)
                
                
                self._beacon_lock.release()
                self._dev_logger.debug("beacon lock released")
                # if all the beacons in the list go stale, declare sync lost
                if len(beacon_list) ==0:
                    self.sync_lost(beacon_ts)
                
                # if we've met the threshold for number of beacons received to say we 
                # have sync, set the flag
                if not self._has_sync:
                    if len(beacon_list) >= self._min_beacons:
                        self.sync_acquired()
                
                # if we have sync, compute the schedule for the current set of beacons
                if self._has_sync:
                    self.compute_schedule(beacon_list)
        else:
            self._dev_logger.debug("beacon failed crc")
            meta = {"crcpass":False}
        
        #if not self.in_time_cal:
        # log packet    
        meta["timestamp"] = (time_spec_t(timestamp))
        meta["linkdirection"] = "down"
        meta["direction"] = "receive"    
        meta["messagelength"] = len(payload)   
                 
                    
        # always log that we received the packet once we're out of time cal
        self._ll_logging.packet(meta)  
        
        # do timer calcs at end of callback
        if self.monitor_timing == True:
            wall_end_ts = time.time()
            
            wall_delta_ts = wall_end_ts - wall_start_ts

            self.wall_time_deltas.append(wall_delta_ts)
            
            if wall_end_ts - self.wall_time_window_start >= self.poll_interval:
                
                if len(self.wall_time_deltas) > 0:
                    self._dev_logger.info("average processing time was %f wall seconds per beacon",
                                         numpy.mean(self.wall_time_deltas))
                    self._dev_logger.info("max processing time was %f wall seconds per beacon",
                                         max(self.wall_time_deltas))
                self.wall_time_deltas = []
                self.wall_time_window_start =  wall_end_ts
        
    def do_time_calibration(self, ts_error): 
        '''
        Take in the floating point time stamp error and if there's a change in the timing
        error calibration constant, publish a message with the new constant. This constant
        should be added to any rx_time tags, and subtracted from any tx_time tags.
        Constants will come from the set {-1,0,1} seconds, and are only used to correct
        for the pps ambiguity we're seeing with the gps timestamps
        '''    
        
        old_offset = self.time_sync_offset
        offset_valid = False
        
        # ts error is mobile_time - base_time
        
        # if the mobile is ahead of the base, we need to subtract a second from rx_times
        if (0.5 < ts_error) and (ts_error < 1.5):
            self.time_sync_offset = -1
            offset_valid = True
        # else if the mobile is behind the base, we should add a second to rx_times    
        elif ( -1.5 < ts_error) and ( ts_error < -0.5):
            self.time_sync_offset = 1
            offset_valid = True
        # else if the mobile is synced to the base, set offset to zero
        elif ( -self._beacon_error_thresh < ts_error ) and ( ts_error < self._beacon_error_thresh):
            self.time_sync_offset = 0
            offset_valid = True
        # else something unexpected is going on with sync. Throw out this result and
        # post a warning
        else:
            offset_valid = False
            self._dev_logger.warn( ("beacon timestamp error of %f seconds is out of " +
                                    "anticipated bounds. Not setting a calibration "+ 
                                    "constant"), ts_error)
            
        # if there's a valid offset and it's different from the old one, send a time cal
        # update    
        if offset_valid and (old_offset != self.time_offset):
            self._dev_logger.debug(("Time Calibration Successful: Mobile adjusting "+ 
                                    "times by %d seconds"), self.time_sync_offset)
           
            self._ll_logging._statelog.info("<time_calibration_constant>%f</time_calibration_constant>",
                                            self.time_sync_offset) 
            #self.set_time_calibration_complete()
            self.message_port_pub(self.TIME_CAL_OUT_PORT, pmt.from_python(self.time_sync_offset))
            
    #@timeit
    def cull_stale_beacons(self, current_time):
        stale_time = current_time - self._beacon_timeout
        
                
        # remove the beacons that we no longer need
        num_beacons = len(self._beacon_list)
        
        
        if num_beacons > self._max_beacons:
            self._dev_logger.debug("removing %d excess beacons",(num_beacons-self._max_beacons))
            self._beacon_list[:] = self._beacon_list[num_beacons-self._max_beacons:num_beacons] 
            num_beacons = len(self._beacon_list)
       

        # remove old beacons from beacon list
        if num_beacons > 0:
            self._beacon_list[:] = [x for x in self._beacon_list if x[0]>stale_time]
            if len(self._beacon_list) != num_beacons:
                self._dev_logger.debug("there are %d beacons left in the beacon list",
                                       len(self._beacon_list))
            
            
    def process_as_beacon(self, meta, data):
        
        if  (self._base_id is None) or (self._base_id == meta["fromID"]): 
                beacon_data = extract_beacon(data, self._dev_logger)
                # TODO: convert to using __setstate__ in beacon classes and remove call 
                # below 
                beacon_data.expand()  
        else:
            beacon_data = None
            
        return beacon_data
    
    def compute_schedule(self, beacon_list):
        # compute schedule, and if no errors, set schedule valid flag to true
        
        #print "computing schedule"
        
        # get last header and beacon in list
        last_ts, last_meta, last_beacon = beacon_list[-1]

        self._dev_logger.debug("last beacon's first frame num: %s timestamp: %s found in frame %s", 
                               last_beacon.first_frame_num, last_ts, last_meta["frameID"])   

        timing_deltas = [float(ts - beacon.tx_time) for ts, meta, beacon in beacon_list]
        delta_mags = [abs(x) for x in timing_deltas]
        timing_err = numpy.mean(timing_deltas)
        self._dev_logger.info("beacon_avg_err:%f", timing_err)
        if max(delta_mags) > 1:

            self._dev_logger.debug("Large beacon timing delta: %s", timing_deltas)     
            self._dev_logger.debug("timing err %f", timing_err)  
        

              
        # compute the start time of the next frame
        sched_t0 = last_ts+last_beacon.frame_offset-timing_err
        self._dev_logger.debug("schedule t0 is %s", sched_t0)  
        sched_t0 = sched_t0.round_to_sample(self.rate, self.floored_timestamp)
        self._dev_logger.debug("rounded schedule t0 is %s", sched_t0)  
#        sched_t0 = time_spec_t(sched_t0.int_s(), round(sched_t0.frac_s()*self.rate)/self.rate)         
        
        #print "last ts", last_ts

        #print "schedule is now valid"
        #print "schedule time is: %s" % sched_t0
        #print "schedule beacon is %s" % str(last_beacon)
        
            
        self._sched_lock.acquire()
        last_beacon.time_ref=sched_t0 
        self._dev_logger.debug("beacon t0 is %s", last_beacon.time_ref)         
        last_beacon.valid = True
        self._schedule = last_beacon
        pickled_sched = cPickle.dumps( (last_meta, self._schedule), PICKLE_PROT)
        self.message_port_pub(self.SCHEDULE_OUT_PORT, pmt.from_python(pickled_sched))
        
        self._schedule_valid = True
        self._sched_lock.release()
        
        return True
    #@timeit
    def sync_lost(self, timestamp):
        
        # if first transition after losing sync, must set state variables and
        # send a schedule update
        if self._schedule_valid: 
            self._sched_lock.acquire()
        
            self._has_sync = False
        
            self._schedule_valid = False
            self._schedule = None
            self._sched_lock.release()
            self._dev_logger.info("Sync lost")
            sched = SimpleFrameSchedule(valid=False,time_ref=timestamp.to_tuple(),
                                        frame_config=None)
            pickled_sched = cPickle.dumps(( {},sched), PICKLE_PROT)
            self.message_port_pub(self.SCHEDULE_OUT_PORT, pmt.from_python(pickled_sched))

            
            
    #@timeit        
    def sync_acquired(self):
        self._dev_logger.info("sync acquired")
        self._sched_lock.acquire()
        
        self._has_sync = True
        
        self._sched_lock.release()
        
    def reset(self):
        '''
        Clear out all entries in the beacon list, and if we think we're synced, unsync. 
        '''
        if self._has_sync:
            # apply the timestamp of the last beacon in the list to the "sync lost" message
            timestamp = self._beacon_list[-1][0]
            self.sync_lost(timestamp)
            
            
        self._beacon_lock.acquire()
        self._beacon_list[:] = []
        self._beacon_lock.release()
        
        
    
    # use the work function to cause old beacons to be dropped    
    def work(self, input_items, output_items):
        
        #process streaming samples and tags here
        in0 = input_items[0]
        nread = self.nitems_read(0) #number of items read on port 0
        ninput_items = len(input_items[0])
        
        #read all tags associated with port 0 for items in this work function
        tags = self.get_tags_in_range(0, nread, nread+ninput_items)

        if len(tags) > 0:
            self._dev_logger.debug("beacon consumer found new tags")
        
        for tag in tags:
            key_string = pmt.pmt_symbol_to_string(tag.key)
            if key_string == "rx_time":
                
                current_integer,current_fractional = pmt.to_python(tag.value)
                self.timestamp = time_spec_t(current_integer + current_fractional)
                self.floored_timestamp = time_spec_t(current_integer)
                self.time_offset = tag.offset
                self.found_time = True
                #print "rx time found: %s at offset %ld" %(self.timestamp, self.time_offset)
            elif key_string == "rx_rate":
                #print "rx rate found"
                self.rate = pmt.to_python(tag.value)
                self.sample_period = 1/self.rate
                self.found_rate = True
                
        # only clear out old packets if the time and rate are known
        if self.found_rate & self.found_time:
            #print "nread: %ld ninput_items: %ld self.time_offset %ld" % (nread, ninput_items, self.time_offset)
            t_end = (nread + ninput_items - self.time_offset)*self.sample_period + self.timestamp
            #print "t_end is %s" % t_end
            self._beacon_lock.acquire()
            
            self.cull_stale_beacons(t_end)
            num_beacons = len(self._beacon_list)
            
            self._beacon_lock.release()
            
            # if there aren't any valid beacons left in the queue, declare the sync was 
            # lost
            if num_beacons == 0:
                self.sync_lost(t_end)
                
        return ninput_items
        
        
            
            
def pack_payload( data, fromID, toID, packetid, pktCode, phyCode, macCode,
                  sourceID, destinationID, rfcenterfreq, frequency,
                  bandwidth, timeslotID, frameID, linkdirection, 
                  slot_total_bytes=0, slot_payload_bytes=0, **kwargs):
    """
    Concatenates 'header' fields with data to form a payload suitable 
    to pass into either the narrowband or ofdm packet structs
    
    """
    
    # get the length of our header
       
    #print "kwargs is %s" %kwargs 
    # pickle anything in kwargs as if it is metadata not already included in the header,
    # and pickle it with data in a tuple while we're at it. This will let us get at 
    # (meta, data) when we unpickle really easily
    
    #pickle_payload = cPickle.dumps((kwargs,data), PICKLE_PROT)
    
    #hardcoded K from configuration of RS coding in packet_utils.py
    RS_K = 4  #this number is in bytes

    #pad_tmp = (len(pickle_payload) + TDMA_HEADER_LEN +4) % RS_K  #+4 for crc since crc is performed before RS coding 
    pad_tmp = (len(data) + TDMA_HEADER_LEN +4) % RS_K  #+4 for crc since crc is performed before RS coding
    if pad_tmp == 0:
        pad_bytes =0
    else:
        pad_bytes = RS_K - pad_tmp
    
    
    packed_header = struct.pack(TDMA_HEADER_FORMAT, packetid, pad_bytes, fromID, toID, 
                                pktCode, phyCode, macCode, sourceID, destinationID, 
                                rfcenterfreq, frequency, bandwidth, timeslotID, frameID, 
                                linkdirection, slot_total_bytes, slot_payload_bytes)

    # add padding
    #payload = ''.join( (packed_header, pickle_payload,'0'*pad_bytes) )
    payload = ''.join( (packed_header, data,'0'*pad_bytes) )
    return payload
    
def unpack_payload(payload):
    """
    The inverse of pack_payload: This pulls the 'header' fields out
    of the provided payload and returns them as a list of tuples
    """
        
    # pull the header fields out of payload using a named tuple
    headerFields = TdmaHeaderTuple._make(struct.unpack_from(TDMA_HEADER_FORMAT, payload))
    
    try:       
        # get the metadata and data out of the packet
        #meta,data = cPickle.loads(payload[TDMA_HEADER_LEN:])
        if headerFields.pad_bytes > 0: 
            data = payload[TDMA_HEADER_LEN:-headerFields.pad_bytes]
        else:
            data = payload[TDMA_HEADER_LEN:]
            
        meta = dict()
    except (cPickle.UnpicklingError, AttributeError, EOFError, ImportError,IndexError ):    
        # if there's a problem unpickling, set meta to an empty dictionary and data to an
        # empty string
        meta = dict()
        data = ''
        
    # add info from header to metadata
    meta.update(headerFields._asdict())
    
    # remove the pad_bytes field from metadata since no one needs it
    del meta['pad_bytes']
    
    return meta, data
    #return ( fromID, toID, packet_id, packet_code_str, more_data_follows, data)
        

def extract_beacon(data, logger=None):
    try:
        if logger is not None:
            logger.debug("extracting beacon")
        beacon_data = cPickle.loads(data)
        
#        #print "beacon data was %s" % beacon_data
#        raw_slots = beacon_data["slots"]
#        # convert slots back into named tuples for readability
#        beacon_data["slots"] = [SlotParamTuple(*x) for x in raw_slots]
            
    except (cPickle.UnpicklingError, AttributeError, EOFError, ImportError,IndexError, KeyError ):
        beacon_data = None
        if logger is not None:
            logger.warning("beacon could not be extracted")
        
    return beacon_data

def dump_beacon(beacon_dict):
    return cPickle.dumps(beacon_dict, PICKLE_PROT)


def generate_packet(packet_format, samples_per_symbol, bits_per_symbol, access_code, 
                    pad_for_usrp, use_coding, whitener_offset, meta, data):
    '''
    Given packet metadata, the packet payload, packet format, and various other
    control parameters, generate the bytes to send over the wire
    '''            
    
    #print "meta is %s" %meta
    
    if packet_format == "tdma":
        # convert metadata dictionary and data into one combined payload
        payload = pack_payload(data=data, **meta)
        
    else:
        payload = ''
     
    pkt = packet_utils2.make_packet(payload, samples_per_symbol, bits_per_symbol,
                                     None,access_code, pad_for_usrp, use_coding,
                                     None,whitener_offset)   
    
    #print "data len was %d, packet len is %d" %(len(data), len(pkt))
    
    return pkt

def frame_config_to_xml(frame_config_in, indent_level):
    fc = deepcopy(frame_config_in)
    
    fc["t0"] = str(fc["t0"])
    for k, slot in enumerate(fc["slots"]):
        fc["slots"][k] = tuple(slot)
        
    return dict_to_xml(fc, indent_level)

def parse_frame_file(frame_file, t0, fs):
    #dtd = etree.DTD(dtd_file)
    
    logger = logging.getLogger('developer')

    slot_fields = dict([("owner","int"),
                        ("len","float"),
                        ("offset","float"),
                        ("type","string"),
                        ("rf_freq","float"),
                        ("bb_freq","int"),
                        ("bw","float")])


    parser = etree.XMLParser(dtd_validation=True)
    
    filepath = os.path.expandvars(os.path.expanduser(frame_file))
    filepath = os.path.abspath(filepath)
    xml = etree.parse(filepath, parser)
    root = xml.getroot()
    
    # convert xml tree to dictionary
    raw_frame = etree_to_dict(root)
    raw_frame = raw_frame["frame"]
    
    frame_config = {};
    # build up frame config dictionary
    frame_config["t0"] = time_spec_t(t0)
    frame_config["frame_len"] = float(raw_frame["frame_len"])

    # convert each field of each slot to the correct type
    raw_frame["slots"] = [convert_types(slot, slot_fields) for slot in raw_frame["slots"]]

    # add a placeholder tx_gain field to each slot
    for k in range(len(raw_frame["slots"])):
        raw_frame["slots"][k]["tx_gain"]=0 
        

    # now store off all the slots as a list of named tuples
    frame_config["slots"] = [SlotParamTuple(**slot) for slot in raw_frame["slots"]]
    
    # sort slots by order of offset
    frame_config["slots"].sort(key=lambda slot: slot.offset)
    
    # 
    # enforce slot/frame boundaries occur at integer samples
    #

    # check that t0 is at an integer sample
    t0_frac = frame_config["t0"].frac_s()   
    t0_frac_rounded = round(t0_frac*fs)/fs
    
    if t0_frac != t0_frac_rounded:
        logger.warn("rounding fractional seconds from %.15f to %.15f", t0_frac, 
                    t0_frac_rounded)
        frame_config["t0"] = time_spec_t(frame_config["t0"].int_s(), t0_frac_rounded)
    
    # check that frame len is at an integer sample
    frame_len_rounded = round(frame_config["frame_len"]*fs)/fs

    if frame_config["frame_len"] != frame_len_rounded:
        logger.warn("rounding frame len from %.15f to %.15f", frame_config["frame_len"], 
                    frame_len_rounded)
        frame_config["frame_len"] = frame_len_rounded
    try:    
    
        # do a limited amount of error checking
        for num, slot in enumerate(frame_config["slots"]):
            
            offset_rounded = round(slot.offset*fs)/fs
            len_rounded = round(slot.len*fs)/fs
            
            if slot.offset != offset_rounded:
                logger.warn("rounding slot %d offset from %.15f to %.15f", num, slot.offset,
                            offset_rounded)
                
            if slot.len != len_rounded:
                logger.warn("rounding slot %d len from %.15f to %.15f", num, slot.len,
                            len_rounded)
            
            # more precision fun
            end_of_slot = round( (offset_rounded + len_rounded)*fs)/fs
            
            
            if end_of_slot > frame_config["frame_len"]:
                raise InvalidFrameError(("slot %d with offset %f and len %f extends past " + 
                                         "the end of the frame, len %f") % (num, slot.offset,
                                          slot.len, frame_config["frame_len"]))
                
            frame_config["slots"][num] = slot._replace(offset=offset_rounded, len=len_rounded)
    
    except InvalidFrameError, err:
        logger.error("Invalid Frame: %s", err.msg)
        raise
    
    return frame_config
    
    

def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.iteritems():
                dd[k].append(v)
        d = {t.tag: {k:v[0] if len(v) == 1 else v for k, v in dd.iteritems()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.iteritems())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d

def convert_types(row, fields):
    # convert each entry to the correct type
    new_row = {}
    #print "converting row: %s" % row
    for field_name, field_type in fields.iteritems():
        if field_type == "string":
            new_row[field_name] = row[field_name].strip()
        if field_type == "int":
            new_row[field_name] = int(row[field_name].strip())
        if field_type == "float":
            new_row[field_name] = float(row[field_name].strip())            

    return new_row
    

class InvalidFrameError(Exception):
    """Raised when a frame configuration file is invalid

    Attributes:
        msg  -- explanation of why the frame isn't valid
    """

    def __init__(self, msg):
        self.msg = msg
