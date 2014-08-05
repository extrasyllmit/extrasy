#!/usr/bin/env python
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
import logging
import logging.config
import math
import os
import pickle
import sqlite3
import sys
import time 

# third party library imports

# project specific imports
from digital_ll import time_spec_t

                                               

def timeit(method):

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print 'TIMER: %r:  %2.6f sec' % \
              (method.__name__, te-ts)
        return result

    return timed


class DataInterfaceError(Exception):
    def __init__(self, args):
        super(DataInterfaceError,self).__init__(args)
        
class TimeRefError(DataInterfaceError):
    def __init__(self):
        args = ("No time reference defined. Try calling load_time_ref() " + 
                "after the database is initialized")
        
        super(TimeRefError,self).__init__(args)

class DataInterface(object):
    """
    Database interface object. 
    
    If you want acceptable performance, make sure the database is stored on a ramdisk.
    Use
    mkdir -p /tmp/ram
    sudo mount -t tmpfs -o size=512M tmpfs /tmp/ram
    
    to set up the ramdisk, where 512M is larger than the largest you expect your database to grow.
    """
    def __init__(self, flush_db=False, time_ref=None, db_name="/tmp/ram/performance_history.sqlite"):
        
        # fire up logging service
        self.dev_log = logging.getLogger('developer')
        self.x_log = logging.getLogger('exceptions')
        
        if time_ref is not None:
            self.time_ref = time_spec_t(math.floor(time_ref))
            self.dev_log.debug("setting database time reference to %s", self.time_ref)
        else:
            self.time_ref = None
            self.dev_log.debug("not setting database time at init. This must be done after " + 
                               " the database has been initialized by calling load_time_ref()")
            
        
        # open database file
        try:
            self.dev_log.debug("connecting to database file %s", db_name)
            self.con = sqlite3.connect(db_name)
            self.dev_log.debug("database connection successful")
        except sqlite3.OperationalError as err:
            self.dev_log.exception("Could not open database file named %s.\n" + 
                                   "If using a file on a ramdisk, try using:\n" + 
                                   "mkdir -p /tmp/ram\n" + 
                                   "sudo mount -t tmpfs -o size=512M tmpfs /tmp/ram\n", db_name)
            quit()
            
        db_expanded_name = os.path.expandvars(os.path.expanduser(db_name))
        self._db_path = os.path.dirname(os.path.abspath(db_expanded_name))
        self._db_basename = os.path.basename(os.path.abspath(db_expanded_name))
        
        # use Row wrapper so you can get at rows using field names and/or indexes
        self.con.row_factory = sqlite3.Row

        # make all text ascii only
        self.con.text_factory = str
        
        if flush_db:
            try:
                
                
                self.dev_log.debug("initializing database")
                self.init_database()
                self.dev_log.debug("database initialization complete")
            except Exception as error:
                self.dev_log.exception("Could not initialize the database: Exception %s", error)
                quit()
        
    def init_database(self):
        '''
        Flush out any existing data in the database and build all the tables from scratch
        '''
        
        
        foreign_keys_on_sql = """
        PRAGMA foreign_keys = ON;
        """
        
        foreign_keys_off_sql = """
        PRAGMA foreign_keys = OFF;
        """
        
        drop_tables_sql = """
        DROP TABLE IF EXISTS time_ref;
        DROP TABLE IF EXISTS packets;
        DROP TABLE IF EXISTS pending_rx_slots;
        DROP TABLE IF EXISTS slots;
        DROP TABLE IF EXISTS frames;
        DROP TABLE IF EXISTS frame_nums;
        """
        
        time_ref_table_sql = """
        CREATE TABLE IF NOT EXISTS time_ref(
            id INTEGER PRIMARY KEY NOT NULL,
            t0 BLOB NOT NULL);
        """
        
        frame_num_table_sql = """
        CREATE TABLE IF NOT EXISTS frame_nums(
            frame_num INTEGER PRIMARY KEY NOT NULL
            );
        """        
        
        frame_table_sql = """
        CREATE TABLE IF NOT EXISTS frames(
            frame_num INTEGER PRIMARY KEY NOT NULL,
            frame_timestamp REAL NOT NULL,
            first_frame_num INTEGER NOT NULL,
            frame_len REAL NOT NULL,
            FOREIGN KEY(frame_num) REFERENCES frame_nums(frame_num) ON DELETE CASCADE
            );
        """
        
        slot_table_sql = """
        CREATE TABLE IF NOT EXISTS slots(
           frame_num INTEGER NOT NULL,
           slot_num INTEGER NOT NULL,
           channel_num INTEGER NOT NULL,
           rf_freq REAL NOT NULL,
           owner INTEGER NOT NULL,
           slot_len REAL NOT NULL,
           slot_offset REAL NOT NULL,
           slot_type TEXT NOT NULL,
           PRIMARY KEY (frame_num, slot_num, channel_num),
           FOREIGN KEY(frame_num) REFERENCES frame_nums(frame_num) ON DELETE CASCADE
           );
        """
        
        packet_table_sql = """
        CREATE TABLE IF NOT EXISTS packets(
            packet_guid INTEGER PRIMARY KEY NOT NULL,
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            destination_id INTEGER NOT NULL,
            packet_num INTEGER NOT NULL,
            packet_code INTEGER NOT NULL,
            link_direction TEXT NOT NULL,
            channel_num INTEGER NOT NULL,
            slot_num INTEGER NOT NULL,
            frame_num INTEGER NOT NULL,
            packet_timestamp REAL NOT NULL,
            status TEXT NOT NULL,
            payload_bits INTEGER NOT NULL,
            total_bits INTEGER NOT NULL,
            FOREIGN KEY(frame_num) 
                REFERENCES frame_nums(frame_num) ON DELETE CASCADE
            -- FOREIGN KEY(frame_num, slot_num, channel_num) 
            --     REFERENCES slots(frame_num, slot_num, channel_num) 
            );           
        """
        
        pending_rx_slot_table_sql = """
        CREATE TABLE IF NOT EXISTS pending_rx_slots(
            frame_num INTEGER NOT NULL,
            slot_num INTEGER NOT NULL,
            channel_num INTEGER NOT NULL,
            owner INTEGER NOT NULL,
            base_id INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            payload_bits INTEGER NOT NULL,
            total_bits INTEGER NOT NULL,
            passed_payload_bits INTEGER NOT NULL,
            passed_total_bits INTEGER NOT NULL,
            PRIMARY KEY (frame_num, slot_num, channel_num),
            -- FOREIGN KEY (frame_num, slot_num, channel_num) REFERENCES 
            -- slots(frame_num, slot_num, channel_num) 
            FOREIGN KEY (frame_num) REFERENCES frame_nums(frame_num) ON DELETE CASCADE
            );
        """ 
        
        #FOREIGN KEY(frame_num, slot_num, channel_num) REFERENCES slots(frame_num, slot_num, channel_num));           
        with self.con as c:
            
            c.executescript(foreign_keys_off_sql)
            
            rows = c.execute("""
            SELECT name FROM sqlite_master WHERE type = 'table'
            """
            )
            table_names = [row["name"] for row in rows]
            
            for name in table_names:
                c.execute("DROP TABLE IF EXISTS %s"%name)
            
            
                
            c.executescript(foreign_keys_on_sql)
            c.executescript(frame_num_table_sql)
            c.executescript(time_ref_table_sql)
            c.executescript(frame_table_sql)
            c.executescript(slot_table_sql)
            c.executescript(packet_table_sql)
            c.executescript(pending_rx_slot_table_sql)
            
            # insert the time reference into the database so other connections can access it
            c.execute("insert into time_ref(t0) values (?)", 
                      [pickle.dumps(self.time_ref)])

    def load_time_ref(self):
        '''
        Try to load in the database's time reference if this database interface didn't set it itself
        '''
        try:
            with self.con as c:
                for row in c.execute("SELECT t0 FROM time_ref ORDER BY ID ASC LIMIT 1"):
                
                    self.time_ref = pickle.loads(row["t0"])
                    self.dev_log.debug("setting database time reference to %s", self.time_ref)
                
            if self.time_ref is None:
                raise TimeRefError
            
        except DataInterfaceError as err:
            self.dev_log.exception("%s.%s: %s", err.__module__, err.__class__.__name__, 
                                   err.message)
            quit()
            
        except sqlite3.Error as err:
            
            self.dev_log.error("The database hasn't been properly initialized yet: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
    
    def preload_frame_num(self, frame_num):
        '''
        Get a frame number reference into the database first so all the foreign key checks
        don't fail
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
                 
        try:
            
            with self.con as c:
                #add to the frame table
                c.execute("""
                INSERT OR IGNORE INTO frame_nums(frame_num) values (?)
                """, (frame_num,))      
        
        except sqlite3.Error as err:
            
            self.dev_log.exception("error inserting frame number %i: %s.%s: %s", 
                                 frame_num, err.__module__, err.__class__.__name__, 
                                 err.message)            
                
    #@timeit         
    def add_frame_config(self, frame_config, frame_num):
        '''
        Add a new frame config file to the database, populating the frame and slots tables
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
                 
        try:
                
        
            first_frame_num = frame_config["first_frame_num"]
            frame_len = frame_config["frame_len"]
            frame_time_delta = (frame_num-frame_config["t0_frame_num"])*frame_len
            
            # compute the frame timestamp with respect to the database's reference time
            frame_timestamp = float(frame_config["t0"] - self.time_ref) + frame_time_delta
            
            # pull out the slot parameters we need for the database
            # store number of bits in slot as 0 for temporary placeholders
            slot_params = [(frame_num, k, s.owner, s.len, s.offset, s.type, s.bb_freq, 
                            s.rf_freq) 
                           for k,s in enumerate(frame_config["slots"])]
        
        
        
            with self.con as c:
                #add to the frame table
                c.execute("insert into frames" + 
                  "(frame_num, frame_timestamp, first_frame_num, frame_len) values " + 
                  "(?,?,?,?)", (frame_num, frame_timestamp, first_frame_num, frame_len))
                # add to the slot table
                c.executemany("insert into slots" + 
                  "(frame_num, slot_num, owner, slot_len, slot_offset, slot_type," +
                  " channel_num, rf_freq) " +
                  "values (?, ?, ?, ?, ?, ?, ?, ?)", slot_params)
        
        
        
        except sqlite3.Error as err:
            
            self.dev_log.exception("error inserting frame number %i: %s.%s: %s", 
                                 frame_num, err.__module__, err.__class__.__name__, 
                                 err.message)
    
    #@timeit        
    def add_tx_packets(self, packet_list, frame_num, packet_overhead, types_to_ints):
        '''
        Add a list of packets to the database. Packet list items are tuples of (meta, data)
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
        
        
        if self.time_ref is None:
            self.dev_log.warning("Could not load time reference from database, so cannot store packets")
            return

        
        try:
            
            # add packets to database
            with self.con as c:
                
                for (meta, data) in packet_list:
                    
                    if meta["pktCode"] != types_to_ints["beacon"]:
                        # get packet timestamp to be in respect to the database time reference
                        packet_timestamp = float(time_spec_t(meta["timestamp"])-self.time_ref)
                        
                        payload_bits = len(data)*8
                        total_bits = payload_bits + packet_overhead*8
                    
                        packet_params= (meta["fromID"], meta["toID"], meta["sourceID"],
                                               meta["destinationID"], meta["packetid"], 
                                               meta["pktCode"], meta["linkdirection"],
                                               meta["frequency"],meta["timeslotID"],
                                               frame_num, packet_timestamp, "pending", 
                                               payload_bits, total_bits) 
                      
            
                
                        # add to the slot table
                        c.execute("insert into packets" + 
                          "(from_id, to_id, source_id, destination_id, packet_num," +
                          " packet_code, link_direction, channel_num, slot_num," + 
                          " frame_num, packet_timestamp, status, payload_bits, total_bits) " +  
                          "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", packet_params)
                
#                c.execute("UPDATE slots SET payload_bits=( SUM(payload_bits)  )

        except sqlite3.Error as err:
        
            self.dev_log.exception("error inserting tx packet:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
            
        except KeyError as err:
            self.dev_log.exception("key error: meta contents: %s ", meta)
            raise KeyError
            
    #@timeit
    def add_rx_packets(self, packet_list, packet_overhead, status, types_to_ints):
        '''
        Add a list of packets to the database. Packet list items are tuples of (meta, data)
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
        
        
        if self.time_ref is None:
            self.dev_log.warning("Could not load time reference from database, so cannot store packets")
            return

        
        try:
            
            # add packets to database
            with self.con as c:
                
                
                
                
                for (meta, data) in packet_list:
            
                    # get packet timestamp to be in respect to the database time reference
                    packet_timestamp = float(time_spec_t(meta["timestamp"])-self.time_ref)
                    
                    packet_payload_bits = len(data)*8
                    packet_total_bits = packet_payload_bits + packet_overhead*8
                    
                    packet_params= (meta["fromID"], meta["toID"], meta["sourceID"],
                                           meta["destinationID"], meta["packetid"], 
                                           meta["pktCode"], meta["linkdirection"],
                                           meta["frequency"],meta["timeslotID"],
                                           meta["frameID"],packet_timestamp, status, 
                                           packet_payload_bits, packet_total_bits) 
                    
                    # add slot byte info so we can update the dummy packets in 
                    # the database with accurate numbers of bytes sent
                    slot_bytes_params = (meta["slot_payload_bytes"]*8,
                                            meta["slot_total_bytes"]*8,
                                            packet_payload_bits,
                                            packet_total_bits,
                                            meta["frameID"],
                                            meta["timeslotID"],
                                            meta["frequency"],
                                            )

                    
                    # add to the slot table
                    c.execute("insert into packets" + 
                      "(from_id, to_id, source_id, destination_id, packet_num," +
                      " packet_code, link_direction, channel_num, slot_num," + 
                      " frame_num, packet_timestamp, status, payload_bits, total_bits) " +  
                      "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", packet_params)
                    
#                # if there are new answers to the total number of bytes sent in this slot,
#                # and the number of payload bytes in this slot, update the database
#                if len(slot_bytes_params)>0:
#                    c.executemany("UPDATE slots SET payload_bits=?,total_bits=? " + 
#                              "WHERE frame_num=? AND slot_num=? " + 
#                              "AND channel_num=?",list(slot_bytes_params))

                    c.execute("""
                    UPDATE pending_rx_slots 
                    SET payload_bits=?, total_bits=?,
                        passed_payload_bits = pending_rx_slots.passed_payload_bits + ?,
                        passed_total_bits = pending_rx_slots.passed_total_bits + ?
                    WHERE frame_num=? AND slot_num=?  AND channel_num=?""",
                    slot_bytes_params   
                    )

        except sqlite3.Error as err:
        
            self.dev_log.exception("error inserting rx packet: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)

    #@timeit
    def add_dummy_rx_feedback(self, frame_config, frame_num, base_id, packet_overhead, 
                              types_to_ints):
        '''
        Add a dummy feedback packet to the database
        '''
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
        
        
        if self.time_ref is None:
            self.dev_log.warning("Could not load time reference from database, so cannot store packets")
            return

        slot_params = []
        frame_timestamp = frame_config["t0"] + (frame_num-frame_config["t0_frame_num"])*frame_config["frame_len"]
        
        for slot_num, slot in enumerate(frame_config["slots"]):
            
            if slot.type == 'uplink' and slot.owner > 0:
                packet_timestamp = float(frame_timestamp-self.time_ref)+slot.offset
                # store all dummy packets as packet id 0 so they're easy to find
                payload_bits = 0
                total_bits = payload_bits + packet_overhead*8
                
                slot_params.append((frame_num, slot_num, slot.bb_freq, 
                                    payload_bits, total_bits, 0, 0, packet_timestamp, 
                                    slot.owner, base_id))
        
        try:
            
            # add pending receive slot info to the database
            with self.con as c:
                
                c.executemany("""
                insert into pending_rx_slots
                (frame_num, slot_num, channel_num, payload_bits, total_bits, 
                    passed_payload_bits, passed_total_bits, timestamp, owner, base_id)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, slot_params)                

        except sqlite3.Error as err:
        
            self.dev_log.exception("error inserting dummy packets: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)

#    @timeit        
    def update_packet_status(self, packet_list, status):
        """Update the packets in packet list to have a status given by the status param
        
        packet_list is a list of (packet_num, source_id) tuples. 
        status is a string containing either "pass" or "fail"
        """
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            update_params = [ (status, packet_num, source_id) 
                             for (packet_num, source_id) in packet_list]
            
            # update packets
            with self.con as c:
                c.executemany("UPDATE packets SET status=? " + 
                              "WHERE packet_num=? AND source_id=?", update_params)    
        
        except sqlite3.Error as err:
        
            self.dev_log.exception("error updating packet status:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
    
#    @timeit
    def update_pending_tx_packets(self, num_frames):
        """
        Change the status of all pending packets that are at least num_frames old to "unknown"
        """
        
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            with self.con as c:
                
                # TODO: Consider choosing tx packets only by joining on slots and 
                # selecting packets from slots based on the slot type
                c.execute("UPDATE packets SET status='unknown' " + 
                          "WHERE frame_num NOT IN(SELECT frame_num FROM frames " + 
                          "ORDER BY rowid DESC LIMIT ?) " +
                          "AND status='pending' AND link_direction='down'",
                          (num_frames,))
                
        except sqlite3.Error as err:
        
            self.dev_log.exception("error updating pending tx packets:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
            
    def fail_missing_tx_packets(self, feedback_regions):
        """
        Find packets that occurred in a feedback region that were in a downlink slot 
        assigned to the node in the feedback_region's 'fromID' field
        change the status fields for any of those packets that have not been acked
        to 'fail' 
        """
        
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            with self.con as c:
                for (start_frame, start_slot, end_frame, end_slot), to_id in feedback_regions:
                    
                    c.execute("""
                    UPDATE packets SET status='imminentfail'
                    WHERE packet_guid IN
                        (SELECT packet_guid 
                         FROM packets
                         WHERE packet_timestamp >= 
                            (SELECT frame_timestamp + slot_offset
                             FROM frames, slots 
                             WHERE frames.frame_num=? AND slots.frame_num=? AND slot_num=?
                            ) 
                            AND packet_timestamp < 
                            (SELECT frame_timestamp + slot_offset + slot_len - .000000001
                            FROM frames, slots 
                            WHERE frames.frame_num=? AND slots.frame_num=? AND slot_num=?
                            )
                            AND status='pending' AND link_direction='down' AND to_id=?
                    )""",(start_frame, start_frame, start_slot,
                          end_frame, end_frame, end_slot, to_id) )
                    
                    c.execute("""
                    UPDATE packets SET status='fail'
                    WHERE packet_guid IN
                        (SELECT packet_guid 
                         FROM packets
                         WHERE status='imminentfail' AND link_direction='down' AND to_id=? 
                         AND packet_timestamp < 
                            (SELECT frame_timestamp + slot_offset
                             FROM frames, slots 
                             WHERE frames.frame_num=? AND slots.frame_num=? AND slot_num=?
                            )
                        )
                    """, (to_id, start_frame, start_frame, start_slot))
                    
                    
                
        except sqlite3.Error as err:
        
            self.dev_log.exception("error failing missing tx packets:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)            
        
    #@timeit    
    def update_pending_dummy_packets(self, num_frames, types_to_ints):
        """
        Change the status of all pending dummy packets that are at least num_frames old 
        to "fail" and update the number of total bits and payload bits 
        """
        
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            with self.con as c:
                
                # make dummy failed rx packet with appropriate number of failed bits
                c.execute("""
                INSERT INTO packets(
                    from_id, to_id, source_id, destination_id, packet_num, packet_code, 
                    link_direction, channel_num, slot_num, frame_num, packet_timestamp, 
                    status, payload_bits, total_bits)
                SELECT 
                    owner, base_id, owner, base_id, 0, ?, 
                    'up', channel_num, slot_num, frame_num, timestamp, 
                    'fail', payload_bits-passed_payload_bits, total_bits-passed_total_bits 
                FROM pending_rx_slots 
                WHERE pending_rx_slots.frame_num NOT IN(
                    SELECT DISTINCT frame_num 
                    FROM pending_rx_slots 
                    ORDER BY timestamp DESC LIMIT ?)
                """, (types_to_ints["dummy"], num_frames)
                )
                
                # remove the slots from pending rx packets that now have dummy 
                # rx packets in the packets table
                c.execute("""
                DELETE FROM pending_rx_slots WHERE pending_rx_slots.frame_num NOT IN(
                    SELECT DISTINCT frame_num 
                    FROM pending_rx_slots 
                    ORDER BY rowid DESC LIMIT ?)
                """, (num_frames,))
                

        except sqlite3.Error as err:
        
            self.dev_log.exception("error updating packet status:%s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
    
#    @timeit            
    def get_total_bits_to_user(self, to_id, frame_window):
        """
        Get a list of (status, total_bits, frame_num, slot_num, channel_num) tuples for 
        all downlink packets sent to to_id in the past frame_window frames
        """
        
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            with self.con as c:
                rows = c.execute("""
                  SELECT status, total_bits, frame_num, slot_num, channel_num 
                  FROM packets
                  WHERE frame_num IN(
                      SELECT frame_num 
                      FROM frames
                      ORDER BY rowid DESC LIMIT ?
                      ) 
                      AND to_id=? 
                      AND link_direction='down'
                      AND status<>'imminentfail' 
                      AND status<>'pending'""",
                 (frame_window, to_id))
                
                result = [ (row["status"], row["total_bits"], row["frame_num"], 
                            row["slot_num"], row["channel_num"]) for row in rows ]
                
            return result
                
                
        except sqlite3.Error as err:
        
            self.dev_log.exception("error retrieving number of bits to user: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)        
            return []
        
    def get_total_bits_from_user(self, from_id, frame_window):
        """
        Get a list of (status, total_bits, frame_num, slot_num, channel_num) tuples for 
        all uplink packets sent from from_id in the past frame_window frames
        """
        
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            with self.con as c:
                rows = c.execute("""
                  SELECT status, total_bits, frame_num, slot_num, channel_num 
                  FROM packets
                  WHERE frame_num IN(
                      SELECT frame_num 
                      FROM frames
                      ORDER BY rowid DESC LIMIT ?
                      ) 
                      AND from_id=? 
                      AND link_direction='up' 
                      AND status<>'pending'""",
                 (frame_window, from_id))
                
                result = [ (row["status"], row["total_bits"], row["frame_num"], 
                            row["slot_num"], row["channel_num"]) for row in rows ]
                
            return result
                
                
        except sqlite3.Error as err:
        
            self.dev_log.exception("error retrieving number of bits from user: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)        
            return []        
    
#    @timeit    
    def prune_tables(self, frame_window):
        """
        keep only the most recent frame_window frames
        """
        
        disk_stats = os.statvfs(self._db_path) 
        db_size = float(os.path.getsize(os.path.join(self._db_path, self._db_basename)))
        disk_free_space = float(disk_stats.f_bavail*disk_stats.f_frsize)
        #disk_total_space = float(disk_stats.f_blocks*disk_stats.f_frsize)
        
        percent_free_use = db_size/(db_size+disk_free_space)*100
        
        if percent_free_use > 50:
            self.dev_log.warning("Database size of %f MB is using %f %% of available space on mount point.",
                                 db_size/(2**20), percent_free_use)
        self.dev_log.debug("Database size before pruning: %f MB", db_size/(2**20))
        try:
            with self.con as c:
                c.execute("DELETE FROM frame_nums " + 
                          "WHERE rowid NOT IN(SELECT rowid FROM frame_nums " + 
                          "ORDER BY rowid DESC LIMIT ?)", (frame_window,))
        
        
                
        except sqlite3.Error as err:
        
            self.dev_log.exception("error pruning tables", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
    
#    @timeit        
    def get_slot_sums(self, to_id, from_id, frame_window, rf_freq):
        # if time_ref hasn't been loaded yet, try to load it
        if self.time_ref is None:
            self.load_time_ref()
            
        try:
            
            with self.con as c:
                rows = c.execute("""
                         SELECT packets.slot_num, packets.channel_num, status, 
                             SUM(total_bits) AS slot_total_bits, 
                             SUM(payload_bits) as slot_payload_bits 
                         FROM packets INNER JOIN slots ON 
                             packets.frame_num = slots.frame_num AND
                             packets.slot_num = slots.slot_num AND
                             packets.channel_num = slots.channel_num
                         WHERE status<>'pending' AND status<>'unknown' AND status<>'imminentfail'
                             AND to_id=? AND from_id = ? AND slots.rf_freq=?
                             AND packets.frame_num IN(
                                 SELECT frame_num 
                                 FROM frames 
                                 ORDER BY rowid DESC LIMIT ?
                                 )
                         GROUP BY packets.slot_num, packets.channel_num, status""",
                         ( to_id, from_id, rf_freq, frame_window)) 
                
                if rows.rowcount==0:
                    self.dev_log.debug("zero packets returned in slot sums query for to_id: %i from_id: %i frame_win: %i rf_freq: %f",
                                       to_id, from_id, frame_window, rf_freq)   
        
            return rows
        
        except sqlite3.Error as err:
        
            self.dev_log.exception("error retrieving number of bits by slot: %s.%s: %s", 
                                   err.__module__, err.__class__.__name__, 
                                   err.message)
            return []        
        

#    @timeit        
    def count_recent_rx_packets(self, num_frames, types_to_ints):
        """
        Count the number of packets received in the last frame_window frames
        """
        
        num_packets = 0
        
        try:
            with self.con as c:
                # count the number of non-dummy uplink packets in the last n frames 
                rows = c.execute("""
                SELECT COUNT(*) as num_packets
                FROM packets
                WHERE packet_code<>? AND link_direction = 'up' AND 
                packets.frame_num IN(
                    SELECT frame_num FROM frames 
                    ORDER BY rowid DESC LIMIT ?
                    )
                """, (types_to_ints["dummy"], num_frames))
                
                for row in rows:
                    num_packets = row["num_packets"]
                    
            return num_packets

        except sqlite3.Error as err:
        
            self.dev_log.exception("error retrieving number of received packets for packet_code %s, num_frames %s: %s.%s: %s", 
                                   types_to_ints["dummy"], num_frames, err.__module__, err.__class__.__name__, 
                                   err.message)
            return num_packets                      
                    
