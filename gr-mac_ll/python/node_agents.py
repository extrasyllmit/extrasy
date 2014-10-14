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
import abc
from collections import defaultdict
import itertools
import logging
import logging.config
import json
import random
import sqlite3

# third party library imports

# project specific imports
from sm import SM


class Agent_Wrapper(object):
    '''
    Interface for code that wraps agents so they can interact with radios.
    
    Instance Variables: 
    
    _agent (object) Something that implements the interface defined in 
                    learning_agent.Agent. 
    '''
    
    __metaclass__ = abc.ABCMeta
    
    
    def __init__(self, agent):
        '''
        Keyword Arguments: 
        
        agent (object) Something that implements the interface defined in 
                       learning_agent.Agent.
        '''
        
        self._agent = agent 
            
    @abc.abstractmethod
    def estimate_state(self):
        '''
        Estimate the current state of the system in some way that is meaningful to
        the agent
        '''
        raise NotImplementedError  
    
    @abc.abstractmethod
    def compute_reward(self):
        '''
        Compute the reward gained from the last action in some way that is meaningful
        to the agent
        '''
        raise NotImplementedError
