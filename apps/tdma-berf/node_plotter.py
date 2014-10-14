#!/usr/bin/env python
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
import argparse
from copy import deepcopy
import cPickle
import os
import time

# third party library imports
from matplotlib.pyplot import figure
from matplotlib.pyplot import show
from matplotlib.pyplot import draw
from matplotlib.pyplot import title
from matplotlib.pyplot import xlabel
from matplotlib.pyplot import ylabel
from matplotlib.pyplot import MaxNLocator
import matplotlib.pyplot as plt

import numpy as np
from numpy import ma

# project specific imports
from mac_ll import DataInterface
from mac_ll import base_slot_manager_ber_feedback




 
def initialize_learner_figures(link_ids, num_freq_slots, num_time_slots):
    fig = plt.figure()
    ax_handles = {}
    mesh_handles = {}
    
    
    # TODO: pull relevant info from database

    num_links = len(link_ids) 
    mask_vals = np.zeros((num_freq_slots, num_time_slots))
    
    for k, (peer_id, link_num) in enumerate(link_ids):
        key = (peer_id, link_num, 'upmask')
        ind = np.ravel_multi_index( (0,k), (4,num_links)) +1 # +1 for matlab
        ax_handles[key] = fig.add_subplot(4,num_links,ind)
        mesh_handles[key] = ax_handles[key].pcolormesh(mask_vals, edgecolors="black")
        mesh_handles[key].set_clim(0,1)
        
        ax_handles[key].set_xlabel('slots')
        ax_handles[key].set_ylabel('channels')
        ax_handles[key].set_title('id %i:%i uplink mask'%(peer_id, link_num))
               
        # force labels to integers
        ya = ax_handles[key].get_yaxis()
        ya.set_major_locator(MaxNLocator(integer=True))
        locs = ax_handles[key].get_yticks()
        ax_handles[key].set_yticks(locs, map(lambda x: "%i" % x, locs))

        
        key = (peer_id, link_num, 'uplink')
        ind = np.ravel_multi_index( (1,k), (4,num_links)) +1 # +1 for matlab
        ax_handles[key] = fig.add_subplot(4,num_links, ind )
        mesh_handles[key] = ax_handles[key].pcolormesh(mask_vals, edgecolors="black")
        mesh_handles[key].set_clim(0,1)
        ax_handles[key].set_xlabel('slots')
        ax_handles[key].set_ylabel('channels')
        ax_handles[key].set_title('id %i:%i uplink'%(peer_id, link_num))
        
        # force labels to integers
        ya = ax_handles[key].get_yaxis()
        ya.set_major_locator(MaxNLocator(integer=True))
        locs = ax_handles[key].get_yticks()
        ax_handles[key].set_yticks(locs, map(lambda x: "%i" % x, locs))
        
        key = (peer_id, link_num, 'downmask')
        ind = np.ravel_multi_index( (2,k), (4,num_links)) +1 # +1 for matlab
        ax_handles[key] = fig.add_subplot(4,num_links,ind)
        mesh_handles[key] = ax_handles[key].pcolormesh(mask_vals, edgecolors="black")
        mesh_handles[key].set_clim(0,1)
        ax_handles[key].set_xlabel('slots')
        ax_handles[key].set_ylabel('channels')
        ax_handles[key].set_title('id %i:%i downlink mask'%(peer_id, link_num))
        
        # force labels to integers
        ya = ax_handles[key].get_yaxis()
        ya.set_major_locator(MaxNLocator(integer=True))
        locs = ax_handles[key].get_yticks()
        ax_handles[key].set_yticks(locs, map(lambda x: "%i" % x, locs))
        
        key = (peer_id, link_num, 'downlink')
        ind = np.ravel_multi_index( (3,k), (4,num_links)) +1 # +1 for matlab
        ax_handles[key] = fig.add_subplot(4,num_links,ind)
        mesh_handles[key] = ax_handles[key].pcolormesh(mask_vals, edgecolors="black")
        mesh_handles[key].set_clim(0,1)
        ax_handles[key].set_xlabel('slots')
        ax_handles[key].set_ylabel('channels')
        ax_handles[key].set_title('id %i:%i downlink'%(peer_id, link_num))
        
        # force labels to integers
        ya = ax_handles[key].get_yaxis()
        ya.set_major_locator(MaxNLocator(integer=True))
        locs = ax_handles[key].get_yticks()
        ax_handles[key].set_yticks(locs, map(lambda x: "%i" % x, locs))

    fig.tight_layout()
           
    return fig, ax_handles, mesh_handles


def initialize_figures(db_int):
        
    with db_int.con as c:
        
        rows = c.execute("""
        SELECT owner, link_num FROM link_ids
        """) 

        link_ids = [ (row["owner"], row["link_num"]) for row in rows ]
    
        rows = c.execute("""
        SELECT num_freq_slots, num_time_slots 
            FROM scenario_config 
            LIMIT 1""")
        for row in rows:
            num_freq_slots = row["num_freq_slots"]
            num_time_slots = row["num_time_slots"]
        
    debug_figs = {}


    
    outs = initialize_learner_figures(link_ids, num_freq_slots, num_time_slots)
    
    learner_figs, ax_handles, mesh_handles = outs
    debug_figs["reinforcement_learner_fig"] = learner_figs
#        debug_meshes = mesh_handles
#        debug_axes = ax_handles      
    debug_meshes = dict(mesh_handles.items())
    debug_axes = dict(ax_handles.items())
    
     
    return debug_figs, debug_meshes, debug_axes, num_freq_slots, num_time_slots


def plot_masks(figs, axes, meshes, db_int):#valid_slots, peer_id, link_num, link_dir, ):
    
    # bail out if the database interface isn't fully initialized            
    if db_int.time_ref is None:
        return
    
    with db_int.con as c:
        
        # get data from most recent frame update
        rows = c.execute("""
        SELECT link_masks.frame_num, owner, link_num, link_type, data, frame_timestamp  
        FROM link_masks LEFT JOIN frames 
            ON link_masks.frame_num=frames.frame_num
         WHERE link_masks.frame_num IN(
             SELECT frames.frame_num 
             FROM frames INNER JOIN link_masks
                 ON frames.frame_num=link_masks.frame_num  
             ORDER BY frame_timestamp DESC LIMIT 1)
         """)
        for row in rows:
            valid_slots = cPickle.loads(row["data"])
            frame_num = row["frame_num"]
            link_dir = row["link_type"]
            peer_id = row["owner"]
            link_num = row["link_num"]
    
    
            if link_dir == 'uplink':
                plot_key = 'upmask'
            elif link_dir == 'downlink':
                plot_key = 'downmask'
            else:
                plot_key = ''
            
            if (peer_id, link_num, plot_key) in axes:
                ax = axes[(peer_id, link_num, plot_key)]
                mesh = meshes[(peer_id, link_num, plot_key)]
                
                
                mask_vals = ma.getmaskarray(valid_slots)
                
                mesh.set_array(deepcopy(mask_vals.ravel()))
            
                ax.set_title('id %i:%i %s mask for frame %i'%(peer_id, link_num, link_dir, frame_num))

def plot_bers(figs, axes, meshes, db_int):
    
    # bail out if the database interface isn't fully initialized            
    if db_int.time_ref is None:
        return
    
    task_codes = {"explore":'R',
                  "exploit":'T'}
    
    box_props = dict(boxstyle='round', fc="white", ec="none", alpha=.5)
    
    with db_int.con as c:
        
        # get data from most recent frame update
        rows = c.execute("""
        SELECT link_decisions.frame_num, owner, link_num, link_type, task, 
            decision_order, slot_num, channel_num, rf_freq, data, frame_timestamp  
        FROM link_decisions LEFT JOIN frames 
            ON link_decisions.frame_num=frames.frame_num
         WHERE link_decisions.frame_num IN(
             SELECT frames.frame_num 
             FROM frames INNER JOIN link_decisions
                 ON frames.frame_num=link_decisions.frame_num  
             ORDER BY frame_timestamp DESC LIMIT 1)
         """)
        for row in rows:
            ber_table = cPickle.loads(row["data"])
            frame_num = row["frame_num"]
            link_dir = row["link_type"]
            peer_id = row["owner"]
            link_num = row["link_num"]
            task = row["task"]
            order = row["decision_order"]
            slot_num = row["slot_num"]
            channel_num = row["channel_num"]
            rf_freq = row["rf_freq"]
            
            if (peer_id, link_num, link_dir) in axes:
                ax = axes[(peer_id, link_num, link_dir)]
                mesh = meshes[(peer_id, link_num, link_dir)]
                
                
                mesh.set_array(deepcopy(ber_table.ravel()))
                
                # remove old text labels
                labels = ax.texts
                labels[:] = [] 
                
                ax.annotate("%s:%i"%(task_codes[task],order), 
                            xy=( slot_num+.5,channel_num+.5),
                            horizontalalignment='center', 
                            verticalalignment='center',
                            bbox=box_props)
            
                ax.set_title('id %i:%i %s for frame %i rf_freq: %f'%(peer_id, 
                                                                     link_num, 
                                                                     link_dir, 
                                                                     frame_num,
                                                                     rf_freq))        


def update_figures(db_int, figs, axes, meshes, num_freq_slots, num_time_slots):
    
    slot_codes = {"uplink":0,
                  "beacon":1,
                  "downlink":2,} 
    
    
    plot_masks(figs, axes, meshes, db_int)
    plot_bers(figs, axes, meshes, db_int)


def show_short_gpl():
    print """
    ExtRaSy Copyright (C) 2013-2014  Massachusetts Institute of Technology

    This program comes with ABSOLUTELY NO WARRANTY; for details run this program
    with '--show-gpl'
    This is free software, and you are welcome to redistribute it under certain
    conditions; run this program with '--show-gpl' for details.
    """

def show_full_gpl():
    print """
    ExtRaSy
    
    Copyright (C) 2013-2014 Massachusetts Institute of Technology
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    """
    
def main():
    
    arg_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument("--db-file", help="database file to monitor", default="/tmp/ram/performance_history.sqlite")
    arg_parser.add_argument("--show-gpl", action="store_true", default=False,
                            help="display the full GPL license for this program")
    opts = arg_parser.parse_args()
    
    if opts.show_gpl:
        show_full_gpl()
        return
    else:
        show_short_gpl()
        
    db_name = opts.db_file
    db_name = os.path.expandvars(os.path.expanduser(db_name))
    db_name = os.path.abspath(db_name)
    
    
    db = DataInterface(flush_db=False, 
                       db_name=db_name)
    db.load_time_ref()

    outs = initialize_figures(db)

    debug_figs, debug_meshes, debug_axes, num_freq_slots, num_time_slots = outs

    plt.show(block=False)
    
    while True:
        update_figures(db, debug_figs, debug_axes, debug_meshes, 
                                                 num_freq_slots, num_time_slots)
        plt.draw()
        plt.pause(1)
    pass



if __name__ == '__main__':
    main()
