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
from collections import deque
from collections import defaultdict
import json
import os
import Queue
import time
import threading

# third party library imports
from matplotlib.pyplot import figure,subplot,legend, show, draw, pause
from matplotlib import pyplot as plt

import numpy as np


# project specific imports
from log_plotter_utils import readerThread
from log_plotter_utils import bulk_data_reader
from log_plotter_utils import shut_down

yTitleFontSize=14
yTitleRotation="vertical"
yTitleXPosition=-.125
yTitleYPosition=0.5
figTitleFontSize=16

styles= {'2':'x', '3':'+'}
styles2= {'2':'<', '3':'>'}
styles3= {'2':'o', '3':'d'}

def plot_verbose_network_states(fignum, data):
    
    epoch_nums = data["epoch_nums"]
    
    fig = figure(fignum)
    ax = fig.axes[0]
    ax.clear()
    [ax.plot(epoch_nums, val,label="mobile " + key, marker=styles[key]) for key,val in data["Od"].iteritems()]
    ax.margins(.1,.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Od epoch %i'%epoch_nums[-1])

    ax = fig.axes[1]
    ax.clear()
    [ax.plot(epoch_nums, val,label="mobile " + key, marker=styles[key]) for key,val in data["Ou"].iteritems()]
    ax.margins(.1,.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Ou epoch %i'%epoch_nums[-1])
    
    ax = fig.axes[2]
    ax.clear()
    [ax.plot(epoch_nums, val,label="mobile " + key, marker=styles[key]) for key,val in data["Ob"].iteritems()]
    ax.margins(.1,.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Ob epoch %i'%epoch_nums[-1])

    fig.tight_layout()
    fig.subplots_adjust(right=.8)
    fig.canvas.draw()

def plot_network_states(fignum,data):
    
    epoch_nums = data["epoch_nums"]
    
    fig = figure(fignum)
            
    ax = fig.axes[0]
    ax.clear()
    ax.plot(epoch_nums, data["net_states"],label="network state", marker='x')
    ax.margins(.1,.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Network State epoch %i'%epoch_nums[-1])
    
    ax = fig.axes[1]
    ax.clear()
    [ax.plot(epoch_nums, val,label="mobile " + key, marker=styles[key]) for key,val in data["v_net_states"].iteritems()]
    ax.set_ylim(-.1,1.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Verbose Network State epoch %i'%epoch_nums[-1])
    
    fig.tight_layout()
    fig.subplots_adjust(right=.75)
    fig.canvas.draw()
             
def plot_db_vars(fignum, data):
    
    epoch_nums = data["epoch_nums"]
    
    fig = figure(fignum)
    ax = fig.axes[0]
    ax.clear()
    
    [ax.plot(epoch_nums, val,label="total pkts mobile " + key, marker=styles[key], fillstyle='full') for key,val in data["dl_pkts_total"].iteritems()]
    [ax.plot(epoch_nums, val,label="known pkts mobile " + key, marker=styles2[key], fillstyle='full') for key,val in data["dl_pkts_known"].iteritems()]
    [ax.plot(epoch_nums, val,label="good pkts mobile " + key, marker=styles3[key], fillstyle='full') for key,val in data["dl_pkts_good"].iteritems()]
    ax.margins(.1,.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Downlink Packets epoch %i'%epoch_nums[-1])

    ax = fig.axes[1]
    ax.clear()
    [ax.plot(epoch_nums, val,label="total pkts mobile " + key, marker=styles[key], fillstyle='full') for key,val in data["ul_pkts_total"].iteritems()]
    [ax.plot(epoch_nums, val,label="good pkts mobile " + key, marker=styles2[key], fillstyle='full') for key,val in data["ul_pkts_good"].iteritems()]
    ax.margins(.1,.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Uplink Packets')
    
    ax = fig.axes[2]
    ax.clear()
    [ax.plot(epoch_nums, val,label="known pkts mobile " + key, marker=styles[key], fillstyle='full') for key,val in data["b_pkts_known"].iteritems()]
    [ax.plot(epoch_nums, val,label="good pkts mobile " + key, marker=styles2[key], fillstyle='full') for key,val in data["b_pkts_good"].iteritems()]
    ax.margins(.1,.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Beacon Packets')    
        
        
    ax = fig.axes[3]
    ax.clear()
    [ax.plot(epoch_nums, val,label="good pkts mobile " + key, marker=styles[key]) for key,val in data["fb_pkts_good"].iteritems()]
    ax.margins(.1,.1)
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.grid(True)
    if epoch_nums:
        ax.set_title('Feedback Packets')                        

    fig.tight_layout()
    fig.subplots_adjust(right=.8)
    fig.canvas.draw()

           
                        
def update_plots(data, figs):

    start = time.time()

    cur_figs = plt.get_fignums()
    if cur_figs:
        
        # plot verbose link states
        fignum = figs[0].number
        if fignum in cur_figs:
            plot_verbose_network_states(fignum, data)
        
        # plot all network states
        fignum = figs[1].number
        if fignum in cur_figs:
            plot_network_states(fignum, data)

        # plot lower level database vars
        fignum = figs[2].number
        if fignum in cur_figs:
            plot_db_vars(fignum, data)
            
        draw()
        plt.pause(.1)  
        
        end = time.time()

        print "Plotting time was: ", end-start, " seconds"
    else:
        time.sleep(1)
            

        
def process_data_points(entries,data):

    for d in entries:
        data["epoch_nums"].append(d["epoch_num"])
        data["frame_nums"].append(d["frame_num"])
        data["net_states"].append(d["network_state"])

            
        for key,val in d["verbose_link_state"]["Od"].iteritems():
            if np.isnan(val):
                data["Od"][key].append(1.0)
            else:
                data["Od"][key].append(2.0*val)      
        #[ Od[key].append(val) for key,val in d["verbose_link_state"]["Od"].iteritems()]
        [ data["Ou"][key].append(val) for key,val in d["verbose_link_state"]["Ou"].iteritems()]
        [ data["Ob"][key].append(val) for key,val in d["verbose_link_state"]["Ob"].iteritems()]
        [data["v_net_states"][key].append(val) for key,val in d["verbose_network_state"].iteritems()]
        [data["dl_pkts_total"][key].append(val) for key,val in d["dl_pkts_total"].iteritems()]
        [data["dl_pkts_good"][key].append(val) for key,val in d["dl_pkts_good"].iteritems()]
        [data["dl_pkts_known"][key].append(val) for key,val in d["dl_pkts_known"].iteritems()]
        [data["fb_pkts_good"][key].append(val) for key,val in d["fb_pkts_good"].iteritems()]
        [data["ul_pkts_total"][key].append(val) for key,val in d["ul_pkts_total"].iteritems()]
        [data["ul_pkts_good"][key].append(val) for key,val in d["ul_pkts_good"].iteritems()]
        [data["b_pkts_good"][key].append(val) for key,val in d["b_pkts_good"].iteritems()]
        [data["b_pkts_known"][key].append(val) for key,val in d["b_pkts_known"].iteritems()]

def initialize_figs():
    
    epoch_nums = deque()
    frame_nums = deque()
    net_states = deque()
    v_net_states = defaultdict(deque)

    Od = defaultdict(deque) 
    Ob = defaultdict(deque)
    Ou = defaultdict(deque)

    dl_pkts_total = defaultdict(deque)
    dl_pkts_good = defaultdict(deque)
    dl_pkts_known = defaultdict(deque)
    fb_pkts_good = defaultdict(deque)
    ul_pkts_total = defaultdict(deque)
    ul_pkts_good = defaultdict(deque)
    b_pkts_good = defaultdict(deque)
    b_pkts_known = defaultdict(deque)

    figs = []

    data = {"epoch_nums":epoch_nums,
            "frame_nums":frame_nums,
            "net_states":net_states,
            "v_net_states":v_net_states,
            "Od":Od,
            "Ob":Ob,
            "Ou":Ou,
            "dl_pkts_total":dl_pkts_total,
            "dl_pkts_good":dl_pkts_good,
            "dl_pkts_known":dl_pkts_known,
            "fb_pkts_good":fb_pkts_good,
            "ul_pkts_total":ul_pkts_total,
            "ul_pkts_good":ul_pkts_good,
            "b_pkts_good":b_pkts_good,
            "b_pkts_known":b_pkts_known,
            }

    # initialize figures    
    figs.append( figure(figsize=(12,6)) )
    ax1=subplot(311)
    subplot(312,sharex=ax1)
    subplot(313,sharex=ax1)

    figs.append( figure(figsize=(12,6)) )
    ax1=subplot(211)
    subplot(212,sharex=ax1)

    figs.append( figure(figsize=(12,6)) )
    ax1=subplot(411)
    subplot(412,sharex=ax1)
    subplot(413,sharex=ax1)
    subplot(414,sharex=ax1)

    return data, figs

def plot_log(filename):
    '''
    Plot the log entries from a logfile
    '''
    fp = open(filename, 'r')
        
    show(block=False)
    data, figs = initialize_figs()
        
    # read in the backlog in one go
    entries = bulk_data_reader(fp)
        
    # process and plot the accumulated data
    process_data_points(entries, data)
    update_plots(data, figs)

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
    arg_parser.add_argument("--log-file", help="log file to parse", default="database.log")
    arg_parser.add_argument("--show-gpl", action="store_true", default=False,
                            help="display the full GPL license for this program")
    opts = arg_parser.parse_args()
    
    if opts.show_gpl:
        show_full_gpl()
        return
    else:
        show_short_gpl()
        
    log_name = opts.log_file
    log_name = os.path.expandvars(os.path.expanduser(log_name))
    log_name = os.path.abspath(log_name)
    
    fp = open(log_name, 'r')



    workQueue = Queue.Queue(100)
    plotLock = threading.Lock()


    
    try:
        threadID = 1
        tName="ReaderThread"
        show(block=False)
        

        
        data, figs = initialize_figs()
        
        # read in the backlog in one go
        entries = bulk_data_reader(fp)
        
        # process and plot the accumulated data
        process_data_points(entries,data)
        update_plots(data, figs)
        
        reader_stop = threading.Event()
        reader = readerThread(threadID, tName, workQueue, fp, reader_stop)
        reader.start()


        while plt.get_fignums():
            
            if not workQueue.empty():
                d = workQueue.get()
                print "processing new data"
                process_data_points([d],data)
                plotLock.acquire()
                update_plots(data, figs)
                plotLock.release()
            else:
                print "waiting for new data from reader"
                pause(.5)
                
        reader_stop.set()
            
    except KeyboardInterrupt: 
        shut_down(reader, reader_stop, plotLock)  
        print "shut down complete"

if __name__ == '__main__':
    main()
    


    
