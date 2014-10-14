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
import json
import threading

# third party library imports
import matplotlib as mpl
from matplotlib.patches import Ellipse
from matplotlib import pyplot as plt
from matplotlib.pyplot import figure, pcolormesh

import numpy as np
from numpy import ma


# project specific imports


patternColors = [np.array([148.0,139.0,84.0])/255, # brown - base
            np.array([149.0,55.0,53.0])/255, # red - mobile 1
            np.array([117.0,146.0,60.0])/255, # green - mobile 2
            np.array([55.0,96.0,145.0])/255, # blue - mobile 3
            np.array([96.0,73.0,123.0])/255, # purple - mobile 4
            np.array([128.0,128.0,128.0])/255, # grey - unassigned
            ]

def chan_num_to_y_coord(chan, num_channels):
    return (np.ceil(num_channels/2.0) - (chan +1))%num_channels


def place_up_arrow(ax, slot_offset, slot_len, chan_num, num_channels):
    
    x1 = slot_offset + 0.5*slot_len
    y1 = chan_num_to_y_coord(chan_num, num_channels) + 0.1
    dx=0
    dy=0.8

    ax.arrow(x1, y1, dx, dy, fc="w", ec="k",
             head_width=0.4*slot_len, head_length=0.2, width=0.2*slot_len, 
             length_includes_head=True )
    
def place_down_arrow(ax, slot_offset, slot_len, chan_num, num_channels):
    
    x1 = slot_offset + 0.5*slot_len
    y1 = chan_num_to_y_coord(chan_num, num_channels) + 0.9
    dx=0
    dy=-0.8

    ax.arrow(x1, y1, dx, dy, fc="w", ec="k",
             head_width=0.4*slot_len, head_length=0.2, width=0.2*slot_len, 
             length_includes_head=True )
    
def place_circle(ax, slot_offset, slot_len, chan_num, num_channels):
    x1 = slot_offset + 0.5*slot_len
    y1 = chan_num_to_y_coord(chan_num, num_channels) + 0.5
    d=0.5
    ax.add_patch(Ellipse( xy=(x1,y1), width=d*slot_len, height=d, fc="w", ec="k"))



def remove_symbols(ax):
    for i in xrange(len(ax.artists) - 1, -1, -1):
        mpl.artist.Artist.remove(ax.artists[i])
    
    for i in xrange(len(ax.patches) - 1, -1, -1):
        ax.patches[i].remove()

# map slot type to symbol plotting function
plot_symbol_functions = {"uplink":place_up_arrow,
                         "downlink":place_down_arrow,
                         "beacon":place_circle
                         }

def plot_pattern(fignum, pattern, num_channels, unique_ids):
    fig = figure(fignum)
    
    cmap = mpl.colors.ListedColormap(patternColors)
    bounds = np.linspace(0,6,7)
    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
    
    ax = fig.gca()
    ax.clear()
    #remove_symbols(ax)

    slots = pattern["slots"]
    
    # xy reversed due to plotting
    # have a gap in between each slot in case there are actual gaps in time between 
    # adjacent slots
    slot_grid = ma.masked_array(np.zeros((num_channels,2*len(slots)+2)), 
                                mask=True)
    
    t = np.array(np.zeros((2*len(slots)+2,1)))
    t[0] = 0
    t[-1] = pattern["frame_len"]
    chan_inds = np.arange(0, num_channels+1)
    
    # color in the grid and compute time axis values
    for slot_num, slot in enumerate(slots):
        # figure out what color this box should be
        color_ind = unique_ids.index(slot.owner)            
        print "color_ind ", color_ind
        # now get x and y coordinates 
        x = 2*slot_num+1
        y = chan_num_to_y_coord(slot.bb_freq, num_channels)
        t[2*slot_num+1] = slot.offset
        t[2*slot_num+2] = slot.offset + slot.len
        print "x %i, y %i"%(x,y)
        
        # xy reversed due to plotting
        slot_grid[y,x]=color_ind
                
        # plot symbols based on slot type
        plot_symbol_functions[slot.type](ax, slot.offset, slot.len, slot.bb_freq,num_channels)
    

    X,Y = np.meshgrid(t,chan_inds)
    
    slot_grid
    
    pcolormesh(X,Y,slot_grid,edgecolors="black", cmap=cmap, norm=norm,)       
    
                
            
    ax.set_yticks(np.array(range(num_channels))+.5 )
    ax.set_yticklabels([chan_num_to_y_coord(i, num_channels) for i in range(num_channels)])
    #ax.set_ylim([-.1,num_channels+.1])
    #ax.set_xlim([0, pattern["frame_len"]])
    ax.margins(0,0)
    ax.set_xticks(t)
    ax.autoscale(tight=True)
#    ax.set_xticklabels(range(data["num_slots"]))


class readerThread (threading.Thread):
    def __init__(self, threadID, name, q, fp, stop_me):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
        self.fp = fp
        self.stop_me = stop_me
    def run(self):
        print "Starting " + self.name
        watchFileThreaded(self.fp, self.q, self.stop_me)  
        print "Exiting " + self.name


def watchFileThreaded(fp, q, stop_me):
    while not stop_me.is_set():
        
        if not q.full():
            cur_pos = fp.tell()
            new = fp.readline()
            # either returns a new line or '' if all lines have been read
            # until the file changes and a new line appears
        
            if new:
                try:
                    d = json.loads(new)
                    q.put(d)
                    print "read new data"
                except:
                    fp.seek(cur_pos,0)
                    print "problem parsing data" 
                
                print "read new data"
          
            else:
                stop_me.wait(.5)
                print "waiting for new data in file"
          
        else:
            stop_me.wait(.5)
            print "waiting for space in queue"
            
def bulk_data_reader(fp):
    lines = fp.readlines()
    entries = [json.loads(line) for line in lines]
    return entries


def shut_down(reader, stop_reader, plotLock):

    print "Shutting down"
    print "telling reader to stop"
    stop_reader.set()
    print "shutdown is acquiring plotlock"
    plotLock.acquire()
    print "shutdown acquired plotlock"
    print "shutdown closing figures"
    plt.close('all')  
    print "shutdown closed figures"
    print "shutdown is releasing plotlock"
    plotLock.release() 
    print "shutdown released plotlock"
    print "shutdown is waiting for reader to finish"
    reader.join()
    print "reader has finished. Shutdown complete"            