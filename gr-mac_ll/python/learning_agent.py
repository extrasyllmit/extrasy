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
from collections import defaultdict
from collections import deque
from functools import partial
import itertools
from itertools import islice
import pickle
import random
import sys

# third party library imports
import numpy as np
from numpy import ma

# project specific imports


class Agent(object):
    def __init__(self):
        pass
    
    @abc.abstractmethod 
    def start(observation):
        '''
        Used for the first iteration of an agent. 
        Given an observation, produce an action.
        '''
        raise NotImplementedError
    
    # (double, Observation) -> Action
    @abc.abstractmethod 
    def step(reward, observation):
        '''
        Run the agent for one iteration. 
        
        Given a reward, assumed to be a double, and an observation, produce an action.
        '''
        raise NotImplementedError
    
    # (double) -> void
    @abc.abstractmethod 
    def end(reward):
        '''
        If shutting down the agent, run one last iteration.
        
        Given a reward, assumed to be a double, update the agent's internal state in some
        appropriate way. Do not return an action.
        '''
        raise NotImplementedError
    
    # () -> void
    @abc.abstractmethod 
    def cleanup():
        pass

#    # (string) -> string
#    def agent_message(message):
#        pass


class State_Action_Learner(Agent):
    '''
    Base class for agents that have a concept of a state-value table
    
    Instance Variables:
     
    _q_table (masked array) Has dimensions of (num_states x num_actions). This table 
                            records the expected reward for each state-action transistion.
                            Invalid actions are denoted by setting the mask for the 
                            corresponding table element. Each element is a float.
    '''

    # TODO: add counter for number of visits per state 

    def __init__(self, num_states, num_actions, greedy_epsilon, q_mask=None, q_seed=None, 
                 reward_history_len=(0,0,0), dynamic_epsilon=False, min_visit_count=2):
        '''
        Constructor
        
        Keyword Arguments:
        
        num_states     (int)    The number of potential states
        num_actions    (int)    The total number of available actions
        q_mask  (bool array)    (num_states x num_actions) boolean array defining what 
                                actions are valid from a given state. A True element
                                means the corresponding state-action pair is masked, and
                                is therefore invalid 
        q_seed (float array)    (num_states x num_actions) array of initial values to 
                                assign to the q_table. If nothing is specified, all 
                                elements will be initialized to zero
        reward_history_len (tuple) (num old vals, guard region size, num recent vals)
                                   this controls the maximum size of each element's reward
                                   history length. Each deque in the reward history 
                                   will have a max length of old vals + guard region + 
                                   new vals.  
        '''
        super(State_Action_Learner, self).__init__()
        
        self._num_actions = num_actions
        self._num_states = num_states
        
        self._policyFrozen = False
        self._exploringFrozen = False
        
        if q_seed is None:
            # initialize q with random values on the order of magnitude of rounding errors
            initial_q_values = np.spacing(1)*np.random.rand(num_states, num_actions)

        else:
            # TODO: check dimensions of q_seed are num_states x num_actions, throw error
            # if not
            initial_q_values = q_seed
        
        if q_mask is None:
            # initialize q table    
            self._q_table = ma.array( initial_q_values )
        else:    
            self._q_table = ma.array( initial_q_values, mask=q_mask )
        
        # initialize a table to track state visitations
        self._visitation_table = np.array(np.zeros_like(self._q_table), dtype='int') 
        
        # initialize a dictionary to track reward history
        self._num_old_reward_vals = reward_history_len[0]
        self._num_guard_reward_vals = reward_history_len[1]
        self._num_new_reward_vals = reward_history_len[0]
        total_reward_vals = sum(reward_history_len)
        
        self._reward_history = defaultdict( partial(deque, maxlen=total_reward_vals))
        
        self._epsilon0 = greedy_epsilon
        self._epsilon = greedy_epsilon
        
        self._dynamic_epsilon=dynamic_epsilon
        self._do_exploit = False
        
        # this is the number of state visits required to switch from the median based 
        # epsilon calculation to the more aggressive epsilon decay state
        self._minimum_visit_count = min_visit_count
        self._epsilon_decay_state = None
    
    def freeze_policy(self,freezePolicy):
        self._policyFrozen = freezePolicy
    
    def freeze_exploring(self, freezeExploring):
        self._exploringFrozen = freezeExploring
          
    def save_value_function(self, fileName):
        theFile = open(fileName, "w")
        pickle.dump(self._q_table, theFile)
        theFile.close()

    def load_value_function(self, fileName):
        theFile = open(fileName, "r")
        self._q_table=pickle.load(theFile)
        theFile.close()
        
    def update_visitation_table(self, state, action):
        self._visitation_table[state, action] +=1
        
    def reset_visitation_table_state(self, state):
        self._visitation_table[state, :] =0    
    
    def update_reward_history(self, state, action, reward):
        self._reward_history[ (state, action)].append(reward)
       
    def get_reward_history_means(self, state, action):
        rewards = self._reward_history[(state, action)]
        
        if len(rewards) == self._num_old_reward_vals + self._num_guard_reward_vals + self._num_new_reward_vals:
            
            old_vals = itertools.islice(rewards, 0, self._num_old_reward_vals)
            old_mean = np.mean(list(old_vals))
            
            new_vals = itertools.islice(reversed(rewards), 0, self._num_new_reward_vals)
            new_mean = np.mean(list(new_vals))
            
        else:
            old_mean = np.NAN
            new_mean = np.NAN
            
        return old_mean, new_mean
    
    def get_reward_history_medians(self, state, action):
        rewards = self._reward_history[(state, action)]
        
        if len(rewards) == self._num_old_reward_vals + self._num_guard_reward_vals + self._num_new_reward_vals:
            
            old_vals = itertools.islice(rewards, 0, self._num_old_reward_vals)
            old_mean = np.median(list(old_vals))
            
            new_vals = itertools.islice(reversed(rewards), 0, self._num_new_reward_vals)
            new_mean = np.median(list(new_vals))
            
        else:
            old_mean = np.NAN
            new_mean = np.NAN
            
        return old_mean, new_mean
    
    def reset_reward_history_state(self, state):
        for a in range(self._num_actions):
            if (state, a) in self._reward_history:
                del self._reward_history[ (state, a)]

    def get_random_valid_action(self, next_state, exploit_action):
        
        # the valid actions are at unmasked array positions, so compute the inverse
        # of the mask of the relevant row
        valid_action_flags = ~ma.getmaskarray(self._q_table[next_state,:])
        
        # disallow the action we would have chosen if exploiting
        valid_action_flags[exploit_action] = False
        
        # get the indices of the valid actions and pick one at random
        next_action = random.choice(np.flatnonzero(valid_action_flags))
        
        return next_action
          
    def constant_eps_greedy_exploration(self, next_state, exploit_action ):
        
        self._epsilon = self._epsilon0
        
        do_exploit = random.random() > self._epsilon
        
        explore_action = self.get_random_valid_action(next_state, exploit_action)    
        
        return do_exploit, explore_action


    def two_state_decaying_eps_greedy_exploration(self, next_state, exploit_action ):
        
        # determine which stage of decaying epsilon we're in
        if np.min(self._visitation_table[next_state,:]) < self._minimum_visit_count:
            self._epsilon_decay_state = "median"
            self._epsilon = self._epsilon0/np.max([np.median(self._visitation_table[next_state,:]),1.0])
        else:
            self._epsilon_decay_state = "sum"
            self._epsilon = self._epsilon0/np.max([np.sum(self._visitation_table[next_state,:]),1.0])
        
        do_exploit = random.random() > self._epsilon

        explore_action = self.get_random_valid_action(next_state, exploit_action) 
        
        return do_exploit, explore_action
    
    def decaying_eps_greedy_exploration(self, next_state, exploit_action ):
        
        self._epsilon = self._epsilon0/np.max([np.median(self._visitation_table[next_state,:]),1.0])
        
        do_exploit = random.random() > self._epsilon

        explore_action = self.get_random_valid_action(next_state, exploit_action) 
        
        return do_exploit, explore_action
    
    def boltzman_exploration(self, next_state, exploit_action ):
        pass           


    @staticmethod
    def add_options(normal, expert):
        
        
        
        normal.add_option("--discount-factor", type="float", 
                          default=0.9,
                          help="scale factor used by the agent to discount the expected reward from the next state transition")

        normal.add_option("--agent-use-adaptive-greedy-epsilon", type="int", 
                          default=0,
                          help="Set to 1 to enable dynamic epsilon algorithm in agent [default=%default]")

        normal.add_option("--agent-epsilon-adaptation-threshold", type="int", 
                          default=2,
                          help="Threshold number of visits at which epsilon decay will switch from median to sum mode [default=%default]")
 
        normal.add_option("--agent-reward-oldbuffer-size", type="int", 
                          default=5,
                          help="number of elements used to compute a median value of the 'old' rewards for change detection [default=%default]")
       
        normal.add_option("--agent-reward-guardbuffer-size", type="int", 
                          default=5,
                          help="number of elements in between the 'old' rewards and 'new' rewards for change detection [default=%default]")

        normal.add_option("--agent-reward-newbuffer-size", type="int", 
                          default=5,
                          help="number of elements used to compute a median value of the 'new' rewards for change detection [default=%default]")
                
        normal.add_option("--greedy-epsilon", type="float", default=0.1, 
                          help="Probablility of chosing a random location to explore " +
                               "instead of using the available location with lowest BER" +
                               " [default=%default]")
                    

class Q_Learner(State_Action_Learner):
    '''
    This is an example implementation of a Q learning agent using greedy-epsilon based
    explore/exploit decisions
    
    Instance Variables: 
    
    _q_table (masked array) Has dimensions of (num_states x num_actions). This table 
                            records the expected reward for each state-action transistion.
                            Invalid actions are denoted by setting the mask for the 
                            corresponding table element. Each element is a float.
    _alpha0         (float) Initial value to use for _alpha in the case of a decaying 
                            _alpha value. Otherwise _alpha = _alpha0                             
    _alpha          (float) Scale factor on new information between 0 and 1 inclusive. 
                            _alpha of 0 results in ignoring new information, while _alpha
                            of 1 results in ignoring old information. Anything in between
                            is weighted according to (1-_alpha)*old + _alpha*new. _alpha
                            is synonymous with learning rate
    _gamma          (float) Discount factor on expected future reward, between 0 and 1
                            inclusive.
    _epsilon        (float) The probability that the agent will choose to explore instead
                            of exploiting on any given iteration. _epsilon = 1 means the 
                            agent will always explore. Also called greedy epsilon       
    _last_state       (int) The state index corresponding to the last observation                         
    _last_action      (int) The index corresponding to the last action taken by the agent
    _policyFrozen    (bool) If true, the agent will not update it's police (_q_table)
    _exploringFrozen (bool) If true, the agent will only exploit, regardless of the value
                            of _epsilon
    '''
    
    def __init__(self, num_states, num_actions, learning_rate, 
                 discount_factor, greedy_epsilon, q_mask=None, q_seed=None,
                 dynamic_alpha=False, dynamic_epsilon=False, reward_history_len=(0,0,0),
                 use_change_detection=False, min_visit_count=2):
        '''
        Keyword Arguments:
        
        num_states     (int)    The number of potential states
        num_actions    (int)    The total number of available actions
        learning_rate  (float)  Value assigned to instance variable _alpha
        discount_factor(float)  Value assigned to instance variable _gamma
        greedy_epsilon (float)  Value assigned to instance variable _epsilon
        q_mask  (bool array)    (num_states x num_actions) boolean array defining what 
                                actions are valid from a given state. A True element
                                means the corresponding state-action pair is masked, and
                                is therefore invalid 
        q_seed (float array)    (num_states x num_actions) array of initial values to 
                                assign to the q_table. If nothing is specified, all 
                                elements will be initialized to zero
        dynamic_alpha (bool)    If true, compute alpha dynamically\
        dynamic_epsilon (bool)  If true, compute epsilon dynamically                           
        '''
        
        super(Q_Learner, self).__init__(num_states, num_actions, greedy_epsilon, q_mask, q_seed,
                                        dynamic_epsilon=dynamic_epsilon,
                                        reward_history_len=reward_history_len,
                                        min_visit_count=min_visit_count)
        
        self._alpha0 = learning_rate
        self._alpha = learning_rate
        
        self._dynamic_alpha=dynamic_alpha
        
        self._gamma = discount_factor
        
        self._epoch_num = 0
        
        self._last_state = None
        self._last_action = None

        self._use_change_detection = use_change_detection
        self._change_detected = False
        
        # only used with median reward based change detection
        self._old_reward_median = np.NAN
        self._new_reward_median = np.NAN

    def start(self,observation):
        '''
        Handle the first iteration.
        
        Keyword Arguments:
        
        observation (int) The index of the most recent observation [0:num_states]
        
        Returns: 
        next_action (int) The index of the next action to take [0:num_actions]
        '''
        next_state = observation
        
        # the valid actions are at unmasked array positions, so compute the inverse
        # of the mask of the relevant row
        valid_action_flags = ~ma.getmaskarray(self._q_table[next_state,:])
        
        # get the indices of the valid actions and pick one at random
        next_action = random.choice(np.flatnonzero(valid_action_flags))

        # store off state for the next iteration
        self._last_state = next_state
        self._last_action = next_action
        
        # increment state visitation table
        self.update_visitation_table(next_state, next_action)
        self._epoch_num +=1
          
        return next_action


    def step(self, reward, observation):
        '''
        Given reward and an observation, compute the next action
        
        Keyword Arguments:
        
        reward    (float) The reward received due to the previous action
        observation (int) The index of the most recent observation [0:num_states]
        
        Returns: 
        next_action (int) The index of the next action to take [0:num_actions]
        
        '''
        next_state = observation
        
        if self._dynamic_alpha:
            self._alpha = self.compute_alpha(self._last_state, self._last_action)
        else:
            self._alpha = self._alpha0
            
        qt = self._q_table[self._last_state, self._last_action]
        max_qt1 = ma.max(self._q_table[next_state, :])
        
        # update value function
        qt_next = (1-self._alpha)*qt + self._alpha*(reward + self._gamma*max_qt1)
        
        if not self._policyFrozen:
            self._q_table[self._last_state, self._last_action] = qt_next

        # update the reward history only for 
        self.update_reward_history(self._last_state, self._last_action, reward)   
        
        # get the index to the maximum value in the relevant row
        exploit_action = ma.argmax(self._q_table[next_state, :])
        
     
        
        if self._dynamic_epsilon:
            self._do_exploit, explore_action = self.two_state_decaying_eps_greedy_exploration(next_state, exploit_action )
        else:
            self._do_exploit, explore_action = self.constant_eps_greedy_exploration(next_state, exploit_action )
        
        
        if self._do_exploit or self._exploringFrozen:
            # use this max value as the action if exploiting
            next_action = exploit_action
            
            # if we're on policy check if there's a change
            
            old_median, new_median = self.get_reward_history_medians(self._last_state, 
                                                                    self._last_action)
           
            # store median vals for debug logging
            self._old_reward_median = old_median
            self._new_reward_median = new_median
           
            self._change_detected = not np.isnan(old_median) and not np.isnan(new_median) and old_median != new_median
            # if there's a change, reset the change detection
            if self._change_detected:
                self.reset_reward_history_state(self._last_state)
            
                # if we're using the change detection to control exploration renewal, 
                # reset the visitation table
                if self._use_change_detection:
                    self.reset_visitation_table_state(self._last_state)
                
        else:
            next_action = explore_action
            
        # store off state for the next iteration
        self._last_state = next_state
        self._last_action = next_action
        
        # increment state visitation table
        self.update_visitation_table(next_state, next_action)
        self._epoch_num +=1
          
        return next_action
    
    def end(self, reward):
        '''
        Given reward, compute the final value function
        
        reward    (float) The reward received due to the previous action
        
        Returns: 
        nothing
        '''
        
        qt = self._q_table[self._last_state, self._last_action]
        
        if self._dynamic_alpha:
            self._alpha = self.compute_alpha(self._last_state, self._last_action)
        else:
            self._alpha = self._alpha0
        
        # update value function
        qt_next = (1-self._alpha)*qt + self._alpha*(reward + qt)
        
        if not self._policyFrozen:
            self._q_table[self._last_state, self._last_action] = qt_next
            
    def log_vars(self):
        
        # convert numpy arrays to lists for serialization
        
        return {"q_table":self._q_table.tolist(),
                "q_mask":ma.getmaskarray(self._q_table).tolist(),
                "exploiting":bool(self._do_exploit | self._exploringFrozen),
                "alpha":float(self._alpha),
                "epsilon":float(self._epsilon),
                "visit_table":self._visitation_table.tolist(),
                "epsilon_decay_state":self._epsilon_decay_state,
                "change_detected":bool(self._change_detected),
                "old_reward_median":float(self._old_reward_median),
                "new_reward_median":float(self._new_reward_median),
                "exploring_frozen":bool(self._exploringFrozen),
                "policy_frozen":bool(self._policyFrozen),}
        
    def compute_alpha(self, state, action):
        alpha = self._alpha0/float(self._visitation_table[state,action])
        return alpha

    @staticmethod
    def add_options(normal, expert):          

        State_Action_Learner.add_options(normal, expert)
        
        normal.add_option("--learning-rate", type="float", default=.9, 
                          help="Weight on new data. Old data will be weighted by "
                               "(1 - learning-rate) [default=%default]")


        normal.add_option("--agent-use-reward-change-detection", type="int", 
                          default=0,
                          help="Set to 1 to enable change detection in the agent [default=%default]")
        

        normal.add_option("--agent-use-adaptive-alpha", type="int", 
                          default=0,
                          help="Set to 1 to enable adaptive alpha algorithm in agent [default=%default]")
        
class Sarsa_Learner(State_Action_Learner):
    '''
    This is an example implementation of a SARSA learning agent using greedy-epsilon based
    explore/exploit decisions
    
    Instance Variables: 
    
    _q_table (masked array) Has dimensions of (num_states x num_actions). This table 
                            records the expected reward for each state-action transistion.
                            Invalid actions are denoted by setting the mask for the 
                            corresponding table element. Each element is a float.
    _alpha0         (float) Initial value to use for _alpha in the case of a decaying 
                            _alpha value. Otherwise _alpha = _alpha0                            
    _alpha          (float) Scale factor on new information between 0 and 1 inclusive. 
                            _alpha of 0 results in ignoring new information, while _alpha
                            of 1 results in ignoring old information. Anything in between
                            is weighted according to (1-_alpha)*old + _alpha*new. _alpha
                            is synonymous with learning rate
    _gamma          (float) Discount factor on expected future reward, between 0 and 1
                            inclusive.
    _epsilon        (float) The probability that the agent will choose to explore instead
                            of exploiting on any given iteration. _epsilon = 1 means the 
                            agent will always explore. Also called greedy epsilon                    
    _last_state       (int) The state index corresponding to the last observation                         
    _last_action      (int) The index corresponding to the last action taken by the agent
    _policyFrozen    (bool) If true, the agent will not update it's police (_q_table)
    _exploringFrozen (bool) If true, the agent will only exploit, regardless of the value
                            of _epsilon    
    '''
    
    _alpha = None
    _gamma = None
    _last_state = None
    _last_action = None
    
    def __init__(self, num_states, num_actions, learning_rate, 
                 discount_factor, greedy_epsilon, q_mask=None, q_seed=None,
                 dynamic_alpha=False, dynamic_epsilon=False, reward_history_len=(0,0,0),
                 use_change_detection=False):
        '''
        Keyword Arguments:
        
        num_states     (int)    The number of potential states
        num_actions    (int)    The total number of available actions
        learning_rate  (float)  Value assigned to instance variable _alpha
        discount_factor(float)  Value assigned to instance variable _gamma
        greedy_epsilon (float)  Value assigned to instance variable _epsilon
        q_mask  (bool array)    (num_states x num_actions) boolean array defining what 
                                actions are valid from a given state. A True element
                                means the corresponding state-action pair is masked, and
                                is therefore invalid 
        q_seed (float array)    (num_states x num_actions) array of initial values to 
                                assign to the q_table. If nothing is specified, all 
                                elements will be initialized to zero
        dynamic_alpha (bool)    If true, compute alpha dynamically
        '''
        
        super(Sarsa_Learner, self).__init__(num_states, num_actions, greedy_epsilon, q_mask, q_seed, 
                                            dynamic_epsilon=dynamic_epsilon, 
                                            reward_history_len=reward_history_len)
        
        self._alpha0 = learning_rate
        self._alpha = learning_rate
        self._dynamic_alpha=dynamic_alpha
        
        self._gamma = discount_factor
        

        self._epoch_num = 0
        
        self._last_state = None
        self._last_action = None

        self._policyFrozen = False
        self._exploringFrozen = False
        
        self._use_change_detection = use_change_detection

    def start(self, observation):
        '''
        Handle the first iteration.
        
        Keyword Arguments:
        
        observation (int) The index of the most recent observation [0:num_states]
        
        Returns: 
        next_action (int) The index of the next action to take [0:num_actions]
        '''
        next_state = observation
        
        # the valid actions are at unmasked array positions, so compute the inverse
        # of the mask of the relevant row
        valid_action_flags = ~ma.getmaskarray(self._q_table[next_state,:])
        
        # get the indices of the valid actions and pick one at random
        next_action = random.choice(np.flatnonzero(valid_action_flags))

        # store off state for the next iteration
        self._last_state = next_state
        self._last_action = next_action
        
        # increment state visitation table
        self.update_visitation_table(next_state, next_action)
        self._epoch_num +=1
          
        return next_action


    def step(self, reward, observation):
        '''
        Given reward and an observation, compute the next action
        
        Keyword Arguments:
        
        reward    (float) The reward received due to the previous action
        observation (int) The index of the most recent observation [0:num_states]
        
        Returns: 
        next_action (int) The index of the next action to take [0:num_actions]
        
        '''
        next_state = observation
        
        if self._dynamic_alpha:
            self._alpha = self.compute_alpha(self._last_state, self._last_action)
        else:
            self._alpha = self._alpha0

        # get the index to the maximum value in the relevant row
        exploit_action = ma.argmax(self._q_table[next_state, :])

        if self._dynamic_epsilon:
            self._do_exploit, explore_action = self.two_state_decaying_eps_greedy_exploration(next_state, exploit_action )
        else:
            self._do_exploit, explore_action = self.constant_eps_greedy_exploration(next_state, exploit_action )

        if self._do_exploit or self._exploringFrozen:
            # use this max value as the action if exploiting
            next_action = exploit_action
        else:
            next_action = explore_action     

        qt = self._q_table[self._last_state, self._last_action]
        qt1 = self._q_table[next_state, next_action]
        

        # update value function
        qt_next = (1-self._alpha)*qt + self._alpha*(reward + self._gamma*qt1)
        
        if not self._policyFrozen:
            self._q_table[self._last_state, self._last_action] = qt_next

        # store off state for the next iteration
        self._last_state = next_state
        self._last_action = next_action
        
        # increment state visitation table
        self.update_visitation_table(next_state, next_action)  
        self._epoch_num +=1
        
        return next_action            

    def end(self, reward):
        '''
        Given reward, compute the final value function
        
        reward    (float) The reward received due to the previous action
        
        Returns: 
        nothing
        '''
        qt = self._q_table[self._last_state, self._last_action]

        if self._dynamic_alpha:
            self._alpha = self.compute_alpha(self._last_state, self._last_action)
        else:
            self._alpha = self._alpha0

        # update value function
#        qt_next = (1-self._alpha0)*qt + self._alpha0*(reward + self._gamma*qt)
        qt_next = (1-self._alpha)*qt + self._alpha*(reward + qt)
        if not self._policyFrozen:
            self._q_table[self._last_state, self._last_action] = qt_next

    def log_vars(self):
        
        # convert numpy arrays to lists for serialization
        
        return {"q_table":self._q_table.tolist(),
                "q_mask":ma.getmaskarray(self._q_table).tolist(),
                "exploiting":bool(self._do_exploit),
                "alpha":float(self._alpha),
                "epsilon":float(self._epsilon),
                "visit_table":self._visitation_table.tolist(),
                "epsilon_decay_state":self._epsilon_decay_state,
                }
        
    def compute_alpha(self, state, action):
        alpha = self._alpha0/float(self._visitation_table[state,action])
        return alpha  

    @staticmethod
    def add_options(normal, expert):          

        State_Action_Learner.add_options(normal, expert)

        normal.add_option("--learning-rate", type="float", default=.9, 
                          help="Weight on new data. Old data will be weighted by "
                               "(1 - learning-rate) [default=%default]")


        normal.add_option("--agent-use-reward-change-detection", type="int", 
                          default=0,
                          help="Set to 1 to enable change detection in the agent [default=%default]")
        

        normal.add_option("--agent-use-adaptive-alpha", type="int", 
                          default=0,
                          help="Set to 1 to enable dynamic alpha algorithm in agent [default=%default]")


