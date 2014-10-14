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
import json
import logging
import logging.config
import random

# third party library imports

# project specific imports
from digital_ll import PatternFrameSchedule
from learning_agent import Agent
from node_agents import Agent_Wrapper
from sm import SM




class Sequential_Pattern_Agent(Agent):
    '''
    Sequential pattern tdma agent based on Agent
    '''
    def __init__(self, sequential_pattern_order):

        
        self.pattern_order = sequential_pattern_order
        self.n_patterns = len(sequential_pattern_order)
        self.index = 0
    
    def start(self,observation):
        self.next_action = self.pattern_order[0]
        self.index = 0
        return self.next_action

    def step(self, reward, observation):
        next_action = self.next_action
        index = self.index
        
        if index == self.n_patterns-1:
            index = 0
        else:
            index = index + 1        

        self.index = index
        self.next_action = self.pattern_order[index]
        
        return next_action

    def end(self, reward):
        pass

class Sequential_Pattern_Agent_Wrapper(Agent_Wrapper, SM):
    '''
    Simple wrapper to support basic over the air testing
    
    Instance Variables: 
    
    _agent          (object) Something that implements the interface defined in 
                             learning_agent.Agent. Furthermore, it expects its 
                             observations to be integers and its rewards to be floats. Its 
                             actions are also integers.                
    startState      (string) defines the state the state machine will be in when it is 
                             first initialized
    db        (SQL database) the database used to estimate the current state and compute 
                             rewards
    _epoch_len         (int) number of frames per agent epoch
    _num_states        (int) number of possible agent states 
    _initial_state     (int) beginning agent state index
    _last_action       (int) The action index from the most recent agent iteration
    _last_state        (int) The state estimate from the most recent agent iteration
    _change_delay      (int) The node will need to announce actions this many frames in 
                             advance of when they will take effect
    _mobile_ids   (int list) The ids of all the mobiles in the scenario 
    _uplink_thresh   (float) Minimum packet success rate to declare an uplink as "good"
    _downlink_thresh (float) Minimum packet success rate to declare a downlink as "good"
    _last_link_status (dict) Keyed by (mobile id, link type) tuples. A true value means
                             that the link corresponding to the key was good. The status
                             for each link is retained across iterations so the algorithm
                             can 'coast' and assume the link state has not changed if 
                             there is no new information                                   
    '''
    
    def __init__(self, agent, epoch_len, num_states, change_delay, mobile_ids,
                 initial_state=None, num_channels=1):
        '''
        Keyword Arguments:
        
        agent          (object) Something that implements the interface defined in 
                                learning_agent.Agent. Furthermore, it expects its 
                                observations to be integers and its rewards to be floats.  
                                Its actions are also integers.                
        epoch_len         (int) number of frames per agent epoch
        num_states        (int) number of possible agent states 
        
        change_delay      (int) The node will need to announce actions this many frames in 
                                advance of when they will take effect
        mobile_ids   (int list) The ids of all the mobiles in the scenario 
        uplink_thresh   (float) Minimum packet success rate to declare an uplink as "good"
        downlink_thresh (float) Minimum packet success rate to declare a downlink as "good"
        initial_state     (int) beginning agent state index                                            
        '''
    
        super(Sequential_Pattern_Agent_Wrapper, self).__init__(agent)
        
        self.startState = "init"
        
        # this can't be initialized in init since the database must be created in the same
        # thread from which it will be used. 
        self.db = None
        
        
        self.epoch_len = epoch_len
        self._num_states = num_states
        self._num_channels = num_channels
        
        self._initial_state = initial_state
        
        self._last_action = None
        self._last_state = None

        self._change_delay = change_delay
        
        
        self.epoch_num = 0
        
        self.agent_log = logging.getLogger('agent')

   

    def getNextValues(self, state, inp):
        """
        Handle inputs and determine next value of outputs.
        
        Once every epoch_len frames, tell the agent to pick the next action
        """        
        next_state = self.getNextState(state, inp)
        state_counter = inp["state_counter"]
        
        # sched_params defaults to None if the agent didn't supply a new action
        sched_params = None
        
        # handle any first run setup
        if state == "init":
            
            # get the state_counter running
            state_counter = self.epoch_len-1
            
            # set the agent's first state
            if self._initial_state is None: 
                initial_agent_state = random.randrange(self._num_states)
            else:
                initial_agent_state = self._initial_state
            
            # do initial iteration of the agent
            action = self._agent.start(initial_agent_state)
            
            agent_vars = {}
            agent_vars["action"]=int(action)
            # assume log is for the end of an epoch, so the first entry will be at -1
            agent_vars["epoch_num"]=int(self.epoch_num)-1
            
            pfs = PatternFrameSchedule()
            action_space = pfs.get_action_space()
            pattern_fields = pfs.PatternTuple._fields
            # store off action space and fields from action space pattern named tuple
            # to make log parsing easier
            agent_vars["action_space"] = action_space
            agent_vars["action_space_pattern_fields"]=pattern_fields
            agent_vars["number_digital_channels"] = self._num_channels
            self.agent_log.info("%s", json.dumps(agent_vars))
            
            
            # store off the results of the first run to be used in subsequent iterations
            self._last_action = action
            self._last_state = initial_agent_state
            
            # record when the action will first take effect and the frame number that the
            # current epoch began. Also record when the action is supposed to end and when
            # the current epoch will end. This is all needed for doing state estimation 
            # and computing the reward from the most recent agent action
            self._action_start = inp["frame_num"] + self._change_delay
            self._epoch_start = inp["frame_num"]
            
            self._action_end = inp["frame_num"] + self._change_delay - 1
            self._epoch_end = inp["frame_num"] - 1
            
            sched_params = (action, self._action_start)
            
        # if in countdown, decrement the counter    
        elif state == "countdown":
            state_counter -=1
            
        # if the state duration is over, run the agent    
        elif state == "reset":
            state_counter = self.epoch_len-1
            
            # get a new state estimate 
            new_state = self.estimate_state()
            # compute the reward accrued during the most recent epoch
            reward = self.compute_reward()
            # choose a new action
            action = self._agent.step(reward, new_state)
            
            self._last_action = action
            self._last_state = new_state
            
            # update start of action and epoch periods for next iteration
            self._action_start = inp["frame_num"] + self._change_delay
            self._epoch_start = inp["frame_num"]
            
            sched_params = (action, self._action_start)
        
            agent_vars = {}
            agent_vars["action"]=int(action)
            agent_vars["epoch_num"]=int(self.epoch_num)
            
            self.epoch_num = 1 + self.epoch_num
            
            # log out agent vars
            self.agent_log.info("%s", json.dumps(agent_vars))
            
        outp = {"state_counter":state_counter,
                "sched_params":sched_params,
                "epoch_num":self.epoch_num}
        
        return (next_state, outp)     
            
    def getNextState(self, state, inp):
        """
        Manage a counter to trigger every epoch_len frames
        """
        
        state_counter = inp["state_counter"]
        
        # is this the first iteration? If so, switch to the initial exploration state.
        if state == "init":
            next_state = "countdown"

        elif state == "countdown":
            if state_counter-1 > 0:
                next_state = state
            else:
                next_state = "reset"
        # this is in reset, go back to countdown
        else:
            next_state = "countdown"
             
        return next_state

    
    def estimate_state(self):
        '''
        Stub function that always returns state 0
        '''
        
        return 0
           
    def compute_reward(self):
        '''
        Stub function that always returns a reward of 0
        '''    

        return 0