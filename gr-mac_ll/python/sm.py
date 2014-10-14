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

_mac_state_machines = {}

def mac_types():
    return _mac_state_machines

def add_mac_type(name, mac_class):
    _mac_state_machines[name] = mac_class

def splitValue(v):

    if v == 'undefined':
    
        return ('undefined', 'undefined')
    
    else:
    
        return v

class SM:
    startState = None
    state = None
    name = None


    def start(self, traceTasks=[], verbose=False, compact=True, printInput=True):
        self.state = self.startState
        
    def step(self, (inp, verbose)):
        (s, o) = self.getNextValues(self.state, inp)
        
        if verbose == True:
            print "In:", str(inp), "Out: ", str(o), "Next State:", str(s)
        self.state = s
        return o
    
    def transduce(self, inputs, verbose=False, traceTasks=[], compact=True, printInput=True, 
                  check=False):
        self.start()
        results = [self.step((inp, verbose)) for inp in inputs if not self.done(self.state)]
        
        if verbose == True:
            print results
        
        return results
           
    def run(self, n = 10):
        return self.transduce([None]*n)

    def getNextValues(self, state, inp):
        nextState = self.getNextState(state, inp)
        return (nextState, nextState)
    
    def getNextState(self, state, inp):
        return state

    def done(self, state):
        return False

    def getStartState(self):
        return self.startState

class Cascade (SM):
    def __init__(self, sm1, sm2):
        self.m1 = sm1
        self.m2 = sm2
        self.startState = (sm1.startState, sm2.startState)
        
    def getNextValues(self, state, inp):
        
        (s1, s2) = state
        
        (newS1, o1) = self.m1.getNextValues(s1, inp)
        
        (newS2, o2) = self.m2.getNextValues(s2, o1)
        
        return ((newS1, newS2), o2)
    
    
class Parallel (SM):
    def __init__(self, sm1, sm2):
        self.m1 = sm1
        self.m2 = sm2
        self.startState = (sm1.startState, sm2.startState)
        
    def getNextValues(self, state, inp):
    
        (s1, s2) = state
        
        (newS1, o1) = self.m1.getNextValues(s1, inp)
        
        (newS2, o2) = self.m2.getNextValues(s2, inp)
        
        return ((newS1, newS2), (o1, o2))

class Parallel2 (Parallel):
    def getNextValues(self, state, inp):
    
        (s1, s2) = state
        
        (i1, i2) = splitValue(inp)
        
        (newS1, o1) = self.m1.getNextValues(s1, i1)
        
        (newS2, o2) = self.m2.getNextValues(s2, i2)
        
        return ((newS1, newS2), (o1, o2))



      

#class Feedback (SM):
#    def __init__(self, sm):
#    
#        self.m = sm
#        
#        self.startState = self.m.startState
#
#    def getNextValues(self, state, inp):
#    
#        (ignore, o) = self.m.getNextValues(state, "undefined")
#        
#        (newS, ignore) = self.m.getNextValues(state, o)
#        
#        return (newS, o)



class Switch (SM):
    
    def __init__(self, condition, sm1, sm2):
        self.m1 = sm1
        self.m2 = sm2
        self.condition = condition
        self.startState = (self.m1.startState, self.m2.startState)

    def getNextValues(self, state, inp):
        (s1, s2) = state
        if self.condition(inp):
            (ns1, o) = self.m1.getNextValues(s1, inp)
            return ((ns1, s2), o)
        else:
            (ns2, o) = self.m2.getNextValues(s2, inp)
            return ((s1, ns2), o)

class ControlledSwitch (Switch):
    

    def getNextValues(self, state, inp):
        (s1, s2) = state
        (control, inputs) = inp
        if self.condition(control):
            (ns1, o) = self.m1.getNextValues(s1, inputs)
            return ((ns1, s2), o)
        else:
            (ns2, o) = self.m2.getNextValues(s2, inputs)
            return ((s1, ns2), o)

class MultiSwitch (SM):
    def __init__(self, selector, sm_list):
        self.sm_list = sm_list
        self.selector = selector
        startStates = []
        
        for sm in sm_list:
            startStates.append(sm.startState)
        
        self.startState = startStates

    def getNextValues(self, state, inp):
        
        (control, inputs) = inp
        
        # get a copy of the current states
        nextStates = list(state)
        
        # if selector picks a valid state machine
        sm_ind = self.selector(control)
        if sm_ind < len(self.sm_list):
            (nextStates[sm_ind], o) = self.sm_list[sm_ind].getNextValues(state[sm_ind], inputs)
            return (nextStates, o)
        else:
            return (nextStates, None)


class Mux (Switch):
 
    def getNextValues(self, state, inp):
        (s1, s2) = state
        (ns1, o1) = self.m1.getNextValues(s1, inp)
        (ns2, o2) = self.m2.getNextValues(s2, inp)
        if self.condition(inp):
            return ((ns1, ns2), o1)
        else:
            return ((ns1, ns2), o2)

class If (SM):
    startState = ('start', None)
    def __init__(self, condition, sm1, sm2):
        self.sm1 = sm1
        self.sm2 = sm2
        self.condition = condition
        
    def getFirstRealState(self, inp):
        if self.condition(inp):
            return ('runningM1', self.sm1.startState)     
        else:
            return ('runningM2', self.sm2.startState)
        
    def getNextValues(self, state, inp):
        (ifState, smState) = state
        
        if ifState == 'start':
            (ifState, smState) = self.getFirstRealState(inp)
        if ifState == 'runningM1':
            (newS, o) = self.sm1.getNextValues(smState, inp)
            return (('runningM1', newS), o)
        else:
            (newS, o) = self.sm2.getNextValues(smState, inp)
            return (('runningM2', newS), o)

class Valve (SM):
    def __init__(self, condition, sm):
        self.m = sm
        self.condition = condition
        self.startState = self.m.startState

    def getNextValues(self, state, inp):

        if self.condition(inp):
            (s, o) = self.m.getNextValues(state, inp)
            return (s, o)
        else:
            return (state, 'undefined')    
        
class NoOp (SM):
    """ class to stay in single state and spit back same result
        may be used with switch to disable and reanable SMs"""
    
    def __init__(self, outputs):

        self.outputs = outputs
        self.startState = 0

    def getNextValues(self, state, inp):
        return (state, self.outputs)
        
class Repeat (SM):
    def __init__(self, sm, n = None):
        self.sm = sm   
        self.startState = (0, self.sm.startState)    
        self.n = n

    def advanceIfDone(self, counter, smState):
        while self.sm.done(smState) and not self.done((counter, smState)):
            counter = counter + 1
            smState = self.sm.startState
        return (counter, smState)

    def getNextValues(self, state, inp):
        (counter, smState) = state
        (smState, o) = self.sm.getNextValues(smState, inp) 
        (counter, smState) = self.advanceIfDone(counter, smState)
        return ((counter, smState), o)

    def done(self, state):
        (counter, smState) = state   
        return counter == self.n


class Sequence (SM):
    def __init__(self, smList):
        self.smList = smList
        self.startState = (0, self.smList[0].startState)
        self.n = len(smList)
        
    def advanceIfDone(self, counter, smState):
        while self.smList[counter].done(smState) and counter + 1 < self.n:
            counter = counter + 1
            smState = self.smList[counter].startState      
        return (counter, smState)

    def getNextValues(self, state, inp):
        (counter, smState) = state
        (smState, o) = self.smList[counter].getNextValues(smState, inp)
        (counter, smState) = self.advanceIfDone(counter, smState)
        return ((counter, smState), o)

    def done(self, state):  
        (counter, smState) = state
        return self.smList[counter].done(smState)
    
    
class RepeatUntil (SM):
    def __init__(self, condition, sm):
        self.sm = sm      
        self.condition = condition
        self.startState = (False, self.sm.startState)
    
    def getNextValues(self, state, inp):
        (condTrue, smState) = state
        (smState, o) = self.sm.getNextValues(smState, inp)
        condTrue = self.condition(inp)
        if self.sm.done(smState) and not condTrue:
            smState = self.sm.getStartState()
        return ((condTrue, smState), o)
    
    def done(self, state):
        (condTrue, smState) = state
        return self.sm.done(smState) and condTrue

class Until (SM):
    def __init__(self, condition, sm):
        self.sm = sm      
        self.condition = condition
        self.startState = (False, self.sm.startState)
    
    def getNextValues(self, state, inp):
        (condTrue, smState) = state
        (smState, o) = self.sm.getNextValues(smState, inp)
        condTrue = self.condition(inp)
#        if self.sm.done(smState) and not condTrue:
#            smState = self.sm.getStartState()
        return ((condTrue, smState), o)
    
    def done(self, state):
        (condTrue, smState) = state
        return self.sm.done(smState) or condTrue













