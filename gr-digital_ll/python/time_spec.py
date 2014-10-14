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
from math import floor
from math import ceil

# third party library imports
import numpy

# project specific imports



class time_spec_t():
    '''
    classdocs
    '''
    _int_s = None
    _frac_s = None

    def __init__(self, *args):
        '''
        Constructor
        '''
        
        if len(args) == 0:
            self._int_s = 0
            self._frac_s = 0.0
            
        # if just one arg, check if its a time_spec_t, sequence, or a numeric type
        elif len(args) == 1:
            if (hasattr(args[0],"int_s")) & (hasattr(args[0],"frac_s")):
                self._int_s = args[0].int_s()
                self._frac_s = args[0].frac_s()
            elif hasattr(args[0], '__iter__'):
                self._int_s = long(args[0][0])
                self._frac_s = float(args[0][1])
            else:
                self._int_s = long(args[0])
                self._frac_s = float(args[0] - self._int_s)
        
        elif len(args) == 2:
            self._int_s = long(args[0])
            self._frac_s = float(args[1])
       
            
        else:
            raise TypeError("time_spec_t supports at most 2 input arguments")
        
        self._normalize()        
                
    def __repr__(self):
        return "time_spec_t(%ld,%.15f)" % (self._int_s, self._frac_s)
    
    def __str__(self):
        if (self._int_s+1 < 0) & (self._frac_s-1 < 0):
            return "%ld" % long(self._int_s+1) + ("%.15f" % float(self._frac_s-1)).lstrip('-0')
        elif (self._int_s+1 == 0) & (self._frac_s-1 < 0):
            return "%.15f" % float(self._frac_s-1)
        else:
            return "%ld" % long(self._int_s) + ("%.15f" % float(self._frac_s)).lstrip('0')
        
    def _normalize(self):
        # normalize will enforce that the fractional seconds parameter is always 
        # a positive number less than 1
        if self._frac_s < 0:
            self._int_s += ( ceil(self._frac_s) - 1)
            self._frac_s -= (ceil(self._frac_s) - 1)
            
        if self._frac_s >= 1:
            self._int_s += floor(self._frac_s)
            self._frac_s -= floor(self._frac_s)
    
        self._int_s = long(self._int_s)
        self._frac_s = float(self._frac_s)
        
    def __float__(self):
        return self._int_s + self._frac_s
    
    def int_s(self):
        if (self._int_s+1 <= 0) & (self._frac_s-1 < 0):
            return long(self._int_s+1)
        else:
            return long(self._int_s)
    
    def frac_s(self):
        if (self._int_s+1 <= 0) & (self._frac_s-1 < 0):
            return float(self._frac_s-1)
        else:
            return float(self._frac_s)
        
    def to_tuple(self):
        '''
        to tuple preps timestamps for output. This rounds to the nearest femtosecond 
        so unit tests don't get bogged down by double precision issues
        '''
        return (self.int_s(), round(self.frac_s()*1E15)/1E15)
    
    def round_to_sample(self,fs,t0):
        '''
        round_to_sample handles rounding a timestamp to an integer number of samples
        since t0
        '''
        delta_t = float(self-t0)
        rounded_t = time_spec_t(round( delta_t*fs)/fs)
        
        return t0 + rounded_t
        
        
    def __lt__(self, other):
        other_t = time_spec_t(other)
        return ( (self._int_s < other_t._int_s) |
                 ((self._int_s == other_t._int_s) & (self._frac_s < other_t._frac_s))
               ) 
        
    def __le__(self, other):
        return self.__lt__(other) | self.__eq__(other)
        
    def __eq__(self, other):
        other_t = time_spec_t(other)
        return (self._int_s == other_t._int_s) & (self._frac_s == other_t._frac_s) 
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __gt__(self, other):
        return not self.__le__(other)
        
    def __ge__(self, other):
        return not self.__lt__(other)

    def __nonzero__(self):
        return (self._int_s != 0) | (self._frac_s != 0)

    def __add__(self, other):
        other_t = time_spec_t(other)
        
        other_t._int_s = self._int_s + other_t._int_s
        other_t._frac_s = self._frac_s + other_t._frac_s
        other_t._normalize()
        
        return other_t
        
    def __sub__(self, other):
        
        other_t = time_spec_t(other)
        
        other_t._int_s = self._int_s - other_t._int_s
        other_t._frac_s = self._frac_s - other_t._frac_s
        other_t._normalize()
        
        return other_t

    def __radd__(self, other):
        return self.__add__(other)
    
    def __rsub__(self, other):
        
        other_t = time_spec_t(other)
        
        other_t._int_s =  other_t._int_s - self._int_s
        other_t._frac_s = other_t._frac_s - self._frac_s
        other_t._normalize()
        
        return other_t

    def __iadd__(self, other):
        
        other_t = time_spec_t(other)
        
        self._int_s = self._int_s + other_t._int_s
        self._frac_s = self._frac_s + other_t._frac_s
        self._normalize()
        
        return self
        
    def __isub__(self, other):
        
        other_t = time_spec_t(other)
        
        self._int_s = self._int_s - other_t._int_s
        self._frac_s = self._frac_s - other_t._frac_s
        self._normalize()
        
        return self
                