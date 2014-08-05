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
import argparse
from collections import deque
from collections import namedtuple
from decimal import Decimal
import os
import Queue
import time
import threading

# third party library imports
import matplotlib as mpl
from matplotlib.pyplot import figure, subplot, legend, show, draw, pause, plot
from matplotlib.pyplot import xlabel, ylabel, setp, locator_params, pcolormesh, colorbar 
from matplotlib.pyplot import clim
from matplotlib.pyplot import vlines
from matplotlib import pyplot as plt
from matplotlib import cm
from matplotlib._png import read_png
from matplotlib.offsetbox import TextArea, DrawingArea, OffsetImage, AnnotationBbox

import numpy as np
from numpy import ma

# project specific imports
from log_plotter_utils import readerThread
from log_plotter_utils import bulk_data_reader
from log_plotter_utils import shut_down
from log_plotter_utils import plot_pattern


visitThresh = 1
coverageThresh = 1
# set up custom color map with light blue mapped to smallest numbers
#myCmap = mpl.colors.ListedColormap(cm.Greys(np.arange(.2,1,1/256.0)))
#myCmap.set_bad('k', .80)

myCmap = cm.Greys
myCmap.set_bad('r')

yTitleFontSize=14
yTitleRotation="vertical"
yTitleXPosition=-.125
yTitleYPosition=0.5
figTitleFontSize=16
    
        
def plot_q_tables(fignum, data, explore_img, exploit_img):
    
    # set up any custom plot formatting functions
    def format_q_table_coord(x, y):
        if data["q_tables"]:
            q_table = data["q_tables"][-1].T
            
            (num_actions, num_states) = q_table.shape
            col = int(x)
            row = int(y)
            if col>=0 and col<num_states and row>=0 and row<num_actions:
            
                z = q_table[row,col]
                
                return 'row=%d, col=%d, z=%1.4f'%(row, col, z)
            else:
                return 'row=%d, col=%d'%(row, col)
        else:
            return 'row=%d, col=%d'%(row, col)
        
    fig=figure(fignum)
    # make sure there is data to plot
    if data["q_tables"]:
        
        epoch_nums = data["epoch_nums"]
        
        # check if mesh exists
        if not fig.axes[0].collections:
            # if plotting for the first time, make a new mesh
            plot_data = data["q_tables"][-1].T
            pcolormesh(plot_data,edgecolors="black")
            ax = fig.axes[0]
            #cbaxes = fig.add_axes([0.8, 0.1, 0.03, 0.8])
            cb = colorbar(ax=ax,use_gridspec=True)
            cb.ax.set_ylabel('Q Value', fontsize=yTitleFontSize, weight='bold')
            min_clim = np.min( [np.min(plot_data), -100])
            max_clim = np.max( [np.max(plot_data), 100])
            clim(min_clim,max_clim)
            ax.format_coord = format_q_table_coord
            ax.set_title('Q Table for Epoch %i\n'%epoch_nums[-1], fontsize=figTitleFontSize, weight='bold')
            ax.set_xlabel("State", fontsize=yTitleFontSize, weight='bold')
            ax.set_ylabel("Action", fontsize=yTitleFontSize, weight='bold')
            fig.tight_layout()
             
            
            ax.set_yticks(np.array(range(data["num_actions"]))+.5 )
            ax.set_yticklabels(range(data["num_actions"]))
            ax.set_xticks(np.array(range(data["num_states"]))+.5 )
            ax.set_xticklabels(range(data["num_states"]))
        else:
            # otherwise update existing mesh data values
            ax = fig.axes[0]
            plot_data = data["q_tables"][-1].T
            ax.collections[0].set_array(plot_data.ravel())
            ax.set_title('Q Table for Epoch %i\n'%epoch_nums[-1], fontsize=figTitleFontSize, weight='bold')
            min_clim = np.min( [np.min(plot_data), -100])
            max_clim = np.max( [np.max(plot_data), 100])
            clim(min_clim,max_clim)
        # plot the action logged in epoch N-1 since that is the action used
        # during epoch N
        if len(data["q_tables"]) >= 2:
            
            # remove all annotations from figure in reverse order so items
            # aren't skipped 
            [art.remove() for art in ax.artists[::-1]]   
            [txt.remove() for txt in ax.texts[::-1]]


            if data["exploit_decisions"][-1]:
                imagebox = exploit_img
            else:
                imagebox = explore_img
            
            
            x2 = data["state_estimates"][-2] + .5
            y2 = data["actions"][-2] + .5
            
            ab = AnnotationBbox(imagebox, (x2, y2),
                               xybox=None,
                               xycoords='data',
                               boxcoords='data',
                               frameon=False) 
            ax.add_artist(ab)
            
            
            x3 = data["state_estimates"][-1] + .5
            y3 = data["actions"][-1] + .5
            
            dx = x3-x2
            dy = y3-y2
                
            if dx > 0:
                arrow_x3 = x3 - 0.25
            elif dx < 0:
                arrow_x3 = x3 + 0.25
            else:
                arrow_x3 = x3
                
            if dy > 0:
                arrow_y3 = y3 - 0.25
            elif dy < 0:
                arrow_y3 = y3 + 0.25
            else:
                arrow_y3 = y3
                
            print "dx: ", dx, " dy: ", dy
                
            # only plot arrow if it has length greater than zero
            if (np.abs(dx) > 0) or (np.abs(dy) > 0):
                    
                ax.annotate("",
                            xy=(arrow_x3, arrow_y3), xycoords='data',
                            xytext=(x2, y2), textcoords='data',
                            size=20,
                            arrowprops=dict(arrowstyle="simple",
                                            connectionstyle="arc3",
                                            fc='k',
                                            ec='w'),
                            )
            
            
            
            if len(data["q_tables"]) >= 3:
                x1 = data["state_estimates"][-3] + .5
                y1 = data["actions"][-3] + .5
            
                dx = x2-x1
                dy = y2-y1
                
                if dx > 0:
                    arrow_x2 = x2 - 0.25
                elif dx < 0:
                    arrow_x2 = x2 + 0.25
                else:
                    arrow_x2 = x2
                    
                if dy > 0:
                    arrow_y2 = y2 - 0.25
                elif dy < 0:
                    arrow_y2 = y2 + 0.25
                else:
                    arrow_y2 = y2
                
                print "dx: ", dx, " dy: ", dy
                
                # only plot arrow if it has length greater than zero
                if (np.abs(dx) > 0) or (np.abs(dy) > 0):
                    
                    ax.annotate("",
                                xy=(arrow_x2, arrow_y2), xycoords='data',
                                xytext=(x1, y1), textcoords='data',
                                size=12,
                                arrowprops=dict(arrowstyle="simple",
                                                connectionstyle="arc3",
                                                fc='k',
                                                ec='w'),
                                )

                    #ax.arrow(x1, y1, dx, dy, fc="k", ec="w",
                    #         head_width=0.1, head_length=0.1, width=0.05, 
                    #         length_includes_head=True )
    
        fig.canvas.draw()    

def plot_current_action(fignum, data):
    fig=figure(fignum)
    # make sure there is data to plot
    if "actions" in data and data["actions"] and "action_space" in data and data["action_space"] and "unique_ids" in data and data["unique_ids"]:
        epoch_nums = data["epoch_nums"]
        
        # check if mesh exists
        if not fig.axes[0].collections:

            ax = fig.axes[0]
            
            rf_freq = data["action_space"][data["actions"][-1]]["rf_freq"]
            rf_freq = Decimal(rf_freq)
            # needed to display in engineering notation correctly
            rf_freq = rf_freq.normalize()
            
            plot_pattern(fignum, data["action_space"][data["actions"][-1]], 
                         data["number_digital_channels"], 
                         data["unique_ids"])
            
            
#                        #cbaxes = fig.add_axes([0.8, 0.1, 0.03, 0.8])
#                        colorbar(ax=ax,use_gridspec=True)
#                        clim(-20,100)
#                        ax.format_coord = format_ax1_coord
#                        ax.set_title('Q Table for Epoch %i\n'%epoch_nums[-1], fontsize=figTitleFontSize, weight='bold')
#                        ax.set_ylabel("Action State", fontsize=yTitleFontSize, weight='bold')
#                        ax.set_xlabel("Action", fontsize=yTitleFontSize, weight='bold')
            ax.set_title('Action for Epoch %i: %i\n'%(epoch_nums[-1], data["actions"][-1]), fontsize=figTitleFontSize, weight='bold')
            ax.set_xlabel("Time (s)\nRF Freq: %s"%rf_freq.to_eng_string(), fontsize=yTitleFontSize, weight='bold')
            fig.tight_layout()
        else:
            ax = fig.axes[0]
            
            # otherwise update existing mesh data values
            rf_freq = data["action_space"][data["actions"][-1]]["rf_freq"]
            rf_freq = Decimal(rf_freq)
            # needed to display in engineering notation correctly
            rf_freq = rf_freq.normalize()
            
            plot_pattern(fignum, data["action_space"][data["actions"][-1]], 
                         data["number_digital_channels"], 
                         data["unique_ids"])
#                        ax.collections[0].set_array(data["q_tables"][-1].ravel())
#                        ax.set_title('Q Table for Epoch %i\n'%epoch_nums[-1], fontsize=figTitleFontSize, weight='bold')
            ax.set_title('Action for Epoch %i: %i\n'%(epoch_nums[-1], data["actions"][-1]), fontsize=figTitleFontSize, weight='bold')
            ax.set_xlabel("Time (s)\nRF Freq: %s"%rf_freq.to_eng_string(), fontsize=yTitleFontSize, weight='bold')
            
        fig.canvas.draw()            

def plot_agent_vars(fignum, data):
    
    #TODO: What parameters should be shifted left/right by one index? 
    epoch_nums = np.array(data["epoch_nums"])
    fig = figure(fignum)          
    ax = fig.axes[0]
    ax.clear()
    ax.plot(epoch_nums, data["alphas"],label="alpha", marker='.')
    #ax.locator_params(axis='y', prune='lower')
    ax.set_ylim(-.1,1.1)
    ax.set_yticks(np.arange(0,1.2,.2))
    #ax.margins(.1,.2)
    #ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
#    ax.set_ylabel("Alpha", rotation=yTitleRotation, 
#                  fontsize=yTitleFontSize, weight='bold',
#                  horizontalalignment='center')
    
    ax.yaxis.set_label_coords(yTitleXPosition, yTitleYPosition)
    setp(ax.get_xticklabels(), visible=False)
    ax.grid(True)
    
#    if len(epoch_nums) > 0:
#        ax.set_title('Current Epoch %i\n'%epoch_nums[-1], fontsize=figTitleFontSize, weight='bold')
#
#    # plot epsilon vs epoch color coded by epsilon decay state
#    ax = fig.axes[1]
#    ax.clear()
    ax.plot(epoch_nums, data["epsilons"], 'r', label="Epsilon", marker='.')
    #ax.locator_params(axis='y', prune='both', nbins=6)
#    ax.set_yticks(np.arange(.1,1,.2))
#    ax.set_ylim(0,1)
#    ax.margins(.1,.2)
    #ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    
#    if len(data["epsilons"])>0:
#        ax.plot(epoch_nums, data["epsilons"], 'r', marker='.')

    if len(data["sum_epsilons"])>0:    
#        ax.plot(data["sum_epsilon_epochs"], data["sum_epsilons"], 'ko',
#                label="Sum Decay", mfc="None", markeredgecolor='k',
#                markeredgewidth=2)
        ax.plot(data["sum_epsilon_epochs"], data["sum_epsilons"], 'k.',
                label="Sum Decay")    
#    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    
    
#    ax.set_ylabel("Epsilon", rotation=yTitleRotation, 
#                  fontsize=yTitleFontSize, weight='bold',
#                  horizontalalignment='center')
    
#    ax.yaxis.set_label_coords(yTitleXPosition, yTitleYPosition)
#    setp(ax.get_xticklabels(), visible=False)
#    ax.grid(True)
#    
#    # plot coverage vs epoch
#    ax = fig.axes[2]
#    ax.clear()
    ax.plot(epoch_nums, data["coverage"], 'g', label="coverage", marker='.')
    #ax.locator_params(axis='y', prune='upper',nbins=6)
    ax.margins(.1,.2)
    #ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.set_ylabel("Rate", rotation=yTitleRotation, 
                  fontsize=yTitleFontSize, weight='bold',
                  horizontalalignment='center')
                  
#    ax.set_yticks(np.arange(.1,1,.2))
#    ax.set_ylim(0,1)
    ax.yaxis.set_label_coords(yTitleXPosition, yTitleYPosition)
    setp(ax.get_xticklabels(), visible=False)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.05, 0.5), loc=6, borderaxespad=0.)

    # draw vertical lines to show change detections on this subplot
    # TODO: FIXME
    change_epochs = [epoch_nums[ind]-1 for ind, y in enumerate(data["change_detections"]) if y > 0]
    if len(change_epochs) > 0:
        ax.vlines(change_epochs, -.1, 1.1, 'c')

    
    
    # plot action index color coded by explore decision
    ax = fig.axes[1]
    ax.clear()
    
    if len(data["actions"])>0:
        ax.plot(epoch_nums, data["actions"], 'r', marker='.')

    if len(data["explore_epochs"])>0:    
        ax.plot(data["explore_epochs"], data["explore_actions"], 'ko',
                label="Explore", mfc="None", markeredgecolor='k',
                markeredgewidth=2)
        
    # plot changes in exploring locked
    explore_locked_epochs = [epoch_nums[ind] for ind, y in enumerate(data["exploring_frozen_changes"]) if y > 0]
    explore_unlocked_epochs = [epoch_nums[ind] for ind, y in enumerate(data["exploring_frozen_changes"]) if y < 0]
    
    if len(explore_locked_epochs) > 0:
        ax.vlines(explore_locked_epochs, -.1, 1.1, 'g')
    
    if len(explore_unlocked_epochs) > 0:
        ax.vlines(explore_locked_epochs, -.1, 1.1, 'c')
        
    ax.locator_params(axis='y', prune='both',nbins=6)
    ax.margins(.1,.2)
    ax.legend(bbox_to_anchor=(1.05, 0.5), loc=6, borderaxespad=0.)
    ax.set_ylabel("Action\nIndex", rotation=yTitleRotation, 
                  fontsize=yTitleFontSize, weight='bold',
                  horizontalalignment='center')
    
    ax.yaxis.set_label_coords(yTitleXPosition, yTitleYPosition)
    setp(ax.get_xticklabels(), visible=False)
    ax.grid(True)


    # plot reward vs epoch   
    ax = fig.axes[2]
    ax.clear()
    if len(epoch_nums) > 0:
        ax.plot(epoch_nums-1, data["rewards"], 'g', label="Reward", marker='.')
        #ax.locator_params(axis='y', prune='both', nbins=6)
        ax.set_yticks(np.arange(-100,70,50))
        ax.set_ylim(-110,60)
        ax.margins(.1,.2)
        #ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        ax.set_ylabel("Reward", rotation=yTitleRotation, 
                      fontsize=yTitleFontSize, weight='bold',
                      horizontalalignment='center')
    
    ax.yaxis.set_label_coords(yTitleXPosition, yTitleYPosition)
    setp(ax.get_xticklabels(), visible=False)
    ax.grid(True)


    
    # plot state index vs epoch
    ax = fig.axes[3]
    ax.clear()
    ax.plot(epoch_nums, data["state_estimates"], 'b', label="State", marker='.')
    ax.locator_params(axis='y', prune='upper',nbins=6)
    ax.margins(.1,.2)
    #ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    ax.set_ylabel("State\nIndex", rotation=yTitleRotation, 
                  fontsize=yTitleFontSize, weight='bold',
                  horizontalalignment='center')
    
    ax.yaxis.set_label_coords(yTitleXPosition, yTitleYPosition)
    setp(ax.get_xticklabels(), visible=False)
    ax.grid(True)
    
#    # plot change intermediate statistics vs epoch
#    ax = fig.axes[6]
#    ax.clear()
#    if len(epoch_nums) > 0:
#        ax.plot(epoch_nums-1, data["old_reward_medians"], 'bx', label="Old Reward Median",)
#        ax.plot(epoch_nums-1, data["new_reward_medians"], 'r+', label="New Reward Median",)
#        ax.locator_params(axis='y', prune='upper',nbins=6)
#        ax.margins(.1,.2)
#        #ax.set_ylim(-.1,1.1)
#        ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
#        ax.set_ylabel("Median\nRewards", rotation=yTitleRotation, 
#                      fontsize=yTitleFontSize, weight='bold',
#                      horizontalalignment='center')
#    
#    ax.yaxis.set_label_coords(yTitleXPosition, yTitleYPosition)
#    setp(ax.get_xticklabels(), visible=False)
#    ax.grid(True)

#    # plot change detections vs epoch
#    ax = fig.axes[4]
#    ax.clear()
#    if len(epoch_nums) > 0:
#        ax.plot(epoch_nums-1, data["change_detections"],label="Change Detection", marker='.')
#        ax.locator_params(axis='y', prune='upper',nbins=6)
#        ax.margins(.1,.2)
#        ax.set_ylim(-.1,1.1)
#        #ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
#        ax.set_ylabel("Change\nDetection", rotation=yTitleRotation, 
#                      fontsize=yTitleFontSize, weight='bold',
#                      horizontalalignment='center')
#    
#        ax.yaxis.set_label_coords(yTitleXPosition, yTitleYPosition)
#    
#    setp(ax.get_xticklabels(), visible=False)
#    ax.grid(True)
#
#    if not np.all(np.isnan(data["old_reward_medians"])):
        
        

    setp(ax.get_xticklabels(), visible=True)
    ax.set_xlabel("Epoch", fontsize=yTitleFontSize, weight='bold')
    
    # workaround for autoscaling bug
    ax = fig.axes[0]
    if len(epoch_nums) > 0:
        ax.set_xlim([epoch_nums[0]-1, epoch_nums[-1]+1])
    
#            fig.tight_layout()
    fig.subplots_adjust(hspace=0.0,right=.785, left=0.125)
    fig.canvas.draw()

def plot_visit_table(fignum, data):
    
    # set up any custom plot formatting functions
    def format_visit_table_coord(x, y):
        if data["visit_tables"]:
            visit_table = data["visit_tables"][-1].T
            
            (num_actions, num_states) = visit_table.shape
            col = int(x)
            row = int(y)
            if col>=0 and col<num_states and row>=0 and row<num_actions:
            
                z = visit_table[row,col]
                
                return 'row=%d, col=%d, z=%1.4f'%(row, col, z)
            else:
                return 'row=%d, col=%d'%(row, col)
        else:
            return 'row=%d, col=%d'%(row, col)  
    
    fig=figure(fignum)
    # make sure there is data to plot
    if data["visit_tables"]:
        
        epoch_nums = data["epoch_nums"]
        
        # check if mesh exists
        if fig.axes and not fig.axes[0].collections:
            # if plotting for the first time, make a new mesh
            plot_data = ma.masked_less_equal(data["visit_tables"][-1].T, visitThresh)
            
            pcolormesh(plot_data,edgecolors="black", cmap=myCmap)
            
            ax = fig.axes[0]
            #cbaxes = fig.add_axes([0.8, 0.1, 0.03, 0.8])
            cb = colorbar(ax=ax,use_gridspec=True, cmap=myCmap)
            clim(0, np.max( [np.max(plot_data),10]))
            cb.ax.set_ylabel("Visit Count", fontsize=yTitleFontSize, weight='bold')
            ax.format_coord = format_visit_table_coord
            ax.set_title('Visitation Table for Epoch %i\n'%epoch_nums[-1], fontsize=figTitleFontSize, weight='bold')
            ax.set_xlabel("State", fontsize=yTitleFontSize, weight='bold')
            ax.set_ylabel("Action", fontsize=yTitleFontSize, weight='bold')
            
            ax.set_yticks(np.array(range(data["num_actions"]))+.5 )
            ax.set_yticklabels(range(data["num_actions"]))
            ax.set_xticks(np.array(range(data["num_states"]))+.5 )
            ax.set_xticklabels(range(data["num_states"]))
            
            fig.tight_layout()
        elif fig.axes:
            # otherwise update existing mesh data values
            ax = fig.axes[0]
            plot_data = ma.masked_less_equal(data["visit_tables"][-1].T, visitThresh)
            clim(0, np.max( [np.max(plot_data),10]))
            ax.collections[0].set_array(plot_data.ravel())
            ax.set_title('Visitation Table for Epoch %i\n'%epoch_nums[-1], fontsize=figTitleFontSize, weight='bold')
    
    
        fig.canvas.draw()
            
def update_plots(data, explore_img, exploit_img, figs):

    start = time.time()

    cur_figs = plt.get_fignums()
    if cur_figs:        
        
        # plot q table if it hasn't been closed yet
        fignum = figs[0].number
        if fignum in cur_figs:
            plot_q_tables(fignum, data, explore_img, exploit_img)
        
        # plot current action if it hasn't been closed yet
        fignum = figs[1].number    
        if fignum in cur_figs:
            plot_current_action(fignum, data)  
        
        # plot agent vars in a subplot if it hasn't been closed yet
        fignum = figs[2].number
        if fignum in cur_figs:
            plot_agent_vars(fignum, data)
            
        # plot visit table if it hasn't been closed yet
        fignum = figs[3].number
        if fignum in cur_figs:
            plot_visit_table(fignum, data)           

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
        data["rewards"].append(d.get("reward",np.nan)) # reward not present for first iteration, insert nan
        data["exploit_decisions"].append(d["exploiting"])
        data["state_estimates"].append(d["state"])
        data["epsilons"].append(d["epsilon"])
        data["epsilon_decay_states"].append(d["epsilon_decay_state"])
        data["actions"].append(d["action"])
        data["alphas"].append(d["alpha"])
        data["q_tables"].append(np.array(d["q_table"]))
        data["visit_tables"].append(np.array(d["visit_table"]))
        
        # check for existence of change detection field and use False as default
        # if it isn't present
        if "change_detected" in d:
            data["change_detections"].append(d["change_detected"])
        else:
            data["change_detections"].append(False)
            
        if "old_reward_median" in d:
            data["old_reward_medians"].append(d["old_reward_median"])
            data["new_reward_medians"].append(d["new_reward_median"])
        else:
            data["old_reward_medians"].append(np.nan)
            data["new_reward_medians"].append(np.nan)    
            
        if d["epsilon_decay_state"] == "median":
            data["median_epsilon_epochs"].append(d["epoch_num"])
            data["median_epsilons"].append(d["epsilon"])
        elif d["epsilon_decay_state"] == "sum":
            data["sum_epsilon_epochs"].append(d["epoch_num"])
            data["sum_epsilons"].append(d["epsilon"])
        
        if "exploring_frozen" in d:
            data["exploring_frozen"].append(d["exploring_frozen"])
        else:
            data["exploring_frozen"].append(False)
        
        if len(data["exploring_frozen"]) == 1:
            data["exploring_frozen_changes"].append(0)
        else:
            data["exploring_frozen_changes"].append(data["exploring_frozen"][-1] - data["exploring_frozen"][-2])
        
        if d["exploiting"]:
            data["exploit_epochs"].append(d["epoch_num"])
            data["exploit_actions"].append(d["action"])
        else:
            data["explore_epochs"].append(d["epoch_num"])
            data["explore_actions"].append(d["action"])
        
        if "action_space" in d and "action_space_pattern_fields" in d and "number_digital_channels" in d:
            data["number_digital_channels"] = d["number_digital_channels"]
            
            # initialize the pattern tuple from the fields in the log file
            tupFields = d["action_space_pattern_fields"]
            # convert from unicode
            tupFields = [s.encode('ascii') for s in tupFields]
            PatternTup = namedtuple("PatternTup", " ".join(tupFields))
            
            data["action_space"] = d["action_space"]
            # convert bare tuples in pattern slots into named tuples for easier 
            # processing later
            data["unique_ids"] = set()
            print data["unique_ids"]
            for act_ind, action in enumerate(data["action_space"]):
                
                # handle both formats of pattern file so we can still plot old logs
                if "pattern" in action:                
                    for slot_ind, slot in enumerate(action["pattern"]["slots"]):
                                                
                        action["pattern"]["slots"][slot_ind] = PatternTup(*slot)
                        
                        data["unique_ids"].add(action["pattern"]["slots"][slot_ind].owner)
                    
                    action["pattern"]["slots"][slot_ind] = PatternTup(*slot)
                    
                    action = action.update(action["pattern"])
                    del action["pattern"]
                else:
                    for slot_ind, slot in enumerate(action["slots"]):
                                                
                        action["slots"][slot_ind] = PatternTup(*slot)
                        
                        data["unique_ids"].add(action["slots"][slot_ind].owner)
                    
                    action["slots"][slot_ind] = PatternTup(*slot)
                    
                    
                # may not be necessary, but I'm being paranoid today
                data["action_space"][act_ind]=action
                
            # get unique ids as sorted list
            data["unique_ids"] = list(data["unique_ids"])
            
            data["unique_ids"].sort()
            
            data["num_slots"] = len(data["action_space"][0]["slots"])
            
            # derive the number of total states, number of actions, and number of
            # stochastic states
            (data["num_states"], data["num_actions"])  = data["q_tables"][0].shape
            data["num_stochastic_states"] = data["num_states"]/data["num_actions"]
            
            #print data["action_space"]
            print "\n\n"
            print data["unique_ids"]
            print "\n\n"
            
        
        # count how many states have been visited
        num_visited = np.count_nonzero(data["visit_tables"][-1]>=coverageThresh)
        num_visit_elements = data["num_states"] * data["num_actions"]
         
        data["coverage"].append(float(num_visited)/float(num_visit_elements))
        
            


def initialize_figs():

    epoch_nums = deque()
    frame_nums = deque()
    rewards = deque()
    exploit_decisions = deque()
    exploit_epochs = deque()
    exploit_actions = deque()
    explore_epochs = deque()
    explore_actions = deque()
    explore_frozen = deque()
    explore_frozen_changes = deque()
    state_estimates = deque()
    epsilons = deque()
    epsilon_decay_states = deque()
    median_epsilon_epochs = deque()
    median_epsilons = deque()
    sum_epsilon_epochs = deque()
    sum_epsilons = deque()
    actions = deque()
    alphas = deque()
    q_tables = deque()
    visit_tables = deque()
    coverage = deque()
    change_detections = deque()
    old_medians = deque()
    new_medians = deque()
    
    figs = []
    
    data = {"epoch_nums":epoch_nums,
            "frame_nums":frame_nums,
            "rewards":rewards,
            "exploit_decisions":exploit_decisions,
            "state_estimates":state_estimates,
            "epsilons":epsilons,
            "epsilon_decay_states":epsilon_decay_states,
            "median_epsilon_epochs":median_epsilon_epochs,
            "median_epsilons":median_epsilons,
            "sum_epsilon_epochs":sum_epsilon_epochs,
            "sum_epsilons":sum_epsilons,
            "actions":actions,
            "alphas":alphas,
            "q_tables":q_tables,
            "visit_tables":visit_tables,
            "exploit_epochs":exploit_epochs,
            "exploit_actions":exploit_actions,
            "explore_epochs":explore_epochs,
            "explore_actions":explore_actions,
            "exploring_frozen":explore_frozen,
            "exploring_frozen_changes":explore_frozen_changes,
            "coverage":coverage,
            "change_detections":change_detections,
            "old_reward_medians":old_medians,
            "new_reward_medians":new_medians,
            }

    # initialize figures
    
    dpi = 115.0
        
    figs.append( figure(figsize=(1380.0/dpi,460.0/dpi), dpi=dpi) )
    ax = subplot(111)
    ax.set_aspect('equal')
    

    figs.append( figure(figsize=(6,8)) )
    ax = subplot(111)

    # this looked miserable at 115 dpi so bumping up to standard printer dpi
    dpi_high=96.0
    figs.append( figure(figsize=(1024.0/dpi_high,768.0/dpi_high), dpi=dpi_high) )
    ax1=subplot(411)
    subplot(412,sharex=ax1)
    subplot(413,sharex=ax1)
    subplot(414,sharex=ax1)
#    subplot(515,sharex=ax1)
#    subplot(816,sharex=ax1)
#    subplot(817,sharex=ax1)
#    subplot(818,sharex=ax1)
    
#    figs.append( figure(figsize=(12,4)) )
#    subplot(111)    
    figs.append( figure(figsize=(1380.0/dpi,460.0/dpi), dpi=dpi) )
    ax = subplot(111)
    ax.set_aspect('equal')
        
    explore_path = os.path.abspath("./resources/search.png")
    exploit_path = os.path.abspath("./resources/dollar_currency_sign.png")    
    
    
    explore_fn = open(explore_path, 'r')
    exploit_fn = open(exploit_path, 'r')    
    explore_arr = read_png(explore_fn)
    exploit_arr = read_png(exploit_fn)
    explore_imbox = OffsetImage(explore_arr, zoom=0.15, alpha=1)
    exploit_imbox = OffsetImage(exploit_arr, zoom=0.15, alpha=1)
    explore_fn.close()
    exploit_fn.close()
    
    return data, explore_imbox, exploit_imbox, figs
    
      
def plot_log(log_name):
    '''
    Plot the log entries from a logfile
    '''
    fp = open(log_name, 'r')
        
    show(block=False)
    data, explore_imbox, exploit_imbox, figs = initialize_figs()
        
    # read in the backlog in one go
    entries = bulk_data_reader(fp)
        
    # process and plot the accumulated data
    process_data_points(entries, data)
    update_plots(data, explore_imbox, exploit_imbox, figs)
        
        
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
    the Free Software Foundation, either version 3 of the License, or
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
    arg_parser.add_argument("--log-file", help="log file to parse", default="agent.log")
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
    data, explore_imbox, exploit_imbox, figs = initialize_figs()
    
    try:
        threadID = 1
        tName="ReaderThread"
        show(block=False)
        
        # read in the backlog in one go
        entries = bulk_data_reader(fp)
        
        # process and plot the accumulated data
        process_data_points(entries,data)
        
        # plot, but make sure an exception in the plotting routine doesn't keep the plotLock
        try:
            plotLock.acquire()
            update_plots(data, explore_imbox, exploit_imbox, figs)
            plotLock.release()
        
        except:
            try:
                plotLock.release() 
            except threading.ThreadError:
                pass
            raise

        
        reader_stop = threading.Event()
        reader = readerThread(threadID, tName, workQueue, fp, reader_stop)
        reader.start()


        while plt.get_fignums():
            
            if not workQueue.empty():
                d = workQueue.get()
                print "processing new data"
                process_data_points([d],data)
                plotLock.acquire()
                update_plots(data, explore_imbox, exploit_imbox, figs)
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
