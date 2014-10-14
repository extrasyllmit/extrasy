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
import logging
import logging.config
import os
import pprint
from textwrap import TextWrapper

# third party library imports

# project specific imports



log_levels = ['WARN', 'ERROR', 'DEBUG', 'INFO', 'WARNING','CRITICAL']

class ContextFilter(logging.Filter):
    """
    This is a filter which injects ascii color codes into the log.
    """

    color_mapping = { 
                     'DEBUG':'92',
                     'INFO':'94',
                     'WARNING':'93',
                     'ERROR':'91',
                     'CRITICAL':'95',
                     }

    def filter(self, record):
        if record.levelname in self.color_mapping:
            record.color = self.color_mapping[record.levelname]
        else:
            record.color = ''
            
        
        return True
    
    def printColored(self,msg, level):
        
        print "\033[1;" + self.color_mapping[level] + 'm%s\033[0m' % msg 

# define a common starting point for a logging configuration
log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '\033[1;%(color)sm %(asctime)s - %(levelname)s - %(filename)s - %(lineno)s \033[0m- { "%(message)s" }'
        },
        'detailed_no_color': {
            'format': '%(asctime)s - %(levelname)s - %(filename)s - %(lineno)s { "%(message)s" }'
        },
        'bare': {
            'format': '%(message)s'
        },
    },
    'handlers': {
        'default': {
            'level':'INFO',
            'class':'logging.StreamHandler',
        },
        'developer': {
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter':"detailed"
        },
        'agent': {
            'level':'DEBUG',
            'class':'logging.FileHandler',
            'formatter':"bare",
            'mode':'w',
            'filename':'/dev/null'
        },
        'database': {
            'level':'DEBUG',
            'class':'logging.FileHandler',
            'formatter':"bare",
            'mode':'w',
            'filename':'/dev/null'
        },
        'exceptions': {
            'level':'ERROR',
            'class':'logging.FileHandler',
            'formatter':"detailed_no_color",
            'mode':'w',
            'filename':'exceptions.log'
        },         
    },
    'loggers': {
        'developer': {                  
            'handlers': ['developer', 'exceptions'],
            'level': 'DEBUG',
            'propagate': True  
        },
        'agent': {                  
            'handlers': ['agent'],
            'level': 'DEBUG',
            'propagate': True  
        },
        'database': {                  
            'handlers': ['database'],
            'level': 'DEBUG',
            'propagate': True  
        },
        'exceptions': {                  
            'handlers': ['exceptions'],
            'level': 'DEBUG',
            'propagate': True  
        },
    }
}

def dict_to_xml(params, indent_level):
    items = []
    
    # build indented substrings out of key/value pairs in dictionary 
    for key in params:
        items.append("%s<%s>%s</%s>\n" % (indent_level*'\t', key, params[key], key) )
    
    # concatenate list of strings into single string for output
    finalString = ''.join(items)
    
    # if safe to do so, remove last newline character
    if(len(finalString) > 2):
        finalString = finalString[:-1]
        
    return finalString        

def dict_to_xml_complete(params, tag):
    indent_level = 1
    items = []
    
    # build indented substrings out of key/value pairs in dictionary
    items.append("<%s>\n" % (tag))
    for key in params:
        items.append("%s<%s>%s</%s>\n" % (indent_level*'\t', key, params[key], key) )
    items.append("</%s>\n" % (tag))
    
    # concatenate list of strings into single string for output
    finalString = ''.join(items)
    
    # if safe to do so, remove last newline character
    if(len(finalString) > 2):
        finalString = finalString[:-1]
        
    return finalString 

def dict_to_xml_newlines(params, indent_level):
    items = []
    wrapper = TextWrapper(width=500, 
                          initial_indent="\t"*(indent_level+1), 
                          subsequent_indent="\t"*(indent_level+2)) 
    
    # build indented substrings out of key/value pairs in dictionary 
    for key in params:
        
        param_str = pprint.pformat(params[key], indent=2)
        param_str = '\n'.join(wrapper.wrap(line)[0] for line in param_str.split('\n'))
        
        items.append("%s<%s>\n%s\n%s</%s>\n" % (indent_level*'\t', key, 
                                                param_str, 
                                                indent_level*'\t', key) )
    
    # concatenate list of strings into single string for output
    finalString = ''.join(items)
    
    # if safe to do so, remove last newline character
    if(len(finalString) > 2):
        finalString = finalString[:-1]
        
    return finalString   


# Lincoln Log Lapse (Exception for Lincoln Log)
class LincolnLogLapse(Exception):
    """ LincolnLogLapse is an exception for use with the LincolnLog class"""
    def __init__(self, msgerror):
        self.msgerror = msgerror

    def __str__(self):
        return repr(self.msgerror)

# Level Checking
def LincolnLogLevelCheck(lvl):
    # Check that the lvl is a type of supported level by the logging package
    if lvl is 'debug':
        lvl = logging.DEBUG
    elif lvl is 'info':
        lvl = logging.INFO
    else:
        raise LincolnLogLapse( lvl + ' not a supported level')
    return lvl

# Call the logging config file
def LincolnLogLayout(level = 'debug', debugfile = -1, packetfile = -1, statefile = -1, c2file = -1):
    dev_log = logging.getLogger('developer')
    
    # Check the level
    level = LincolnLogLevelCheck(level)
    
    global _MITLL_DEBUG_LOGGING_FLAG
    global _MITLL_PACKET_LOGGING_FLAG
    global _MITLL_STATE_LOGGING_FLAG
    global _MITLL_C2_LOGGING_FLAG
    
    # Create the base loggers
    # NOTE: Debug has two meanings in this class.  The first
    # is debug is a type of logging supported by this class (like state,
    # and packet). The second is a level of logging (like info or 
    # critical).
    if debugfile != -1:
        _MITLL_DEBUG_LOGGING_FLAG = True
        logger = logging.getLogger( 'debug' )
        logger.setLevel(level)
        
        debug_expanded_file = os.path.expandvars(os.path.expanduser(debugfile))
        debug_abs_file = os.path.abspath(debug_expanded_file)
        logger.addHandler(logging.FileHandler(debug_abs_file, 'w'))
        
        dev_log.info("saving debug log file to %s", debug_abs_file)
        
    else:
        _MITLL_DEBUG_LOGGING_FLAG = False
       
    if packetfile != -1:
        _MITLL_PACKET_LOGGING_FLAG = True
        logger = logging.getLogger( 'packet' )
        logger.setLevel(level)
        
        packet_expanded_file = os.path.expandvars(os.path.expanduser(packetfile))
        packet_abs_file = os.path.abspath(packet_expanded_file)
        logger.addHandler(logging.FileHandler(packet_abs_file, 'w'))
        
        dev_log.info("saving packet log file to %s", packet_abs_file)
        
    else:
        _MITLL_PACKET_LOGGING_FLAG = False
        
    if statefile != -1:
        
        _MITLL_STATE_LOGGING_FLAG = True
        logger = logging.getLogger( 'state' )
        logger.setLevel(level)
        
        state_expanded_file = os.path.expandvars(os.path.expanduser(statefile))
        state_abs_file = os.path.abspath(state_expanded_file)
        logger.addHandler(logging.FileHandler(state_abs_file, 'w'))
        
        dev_log.info("saving state log file to %s", state_abs_file)
    else:
        _MITLL_STATE_LOGGING_FLAG = False
        
    if c2file != -1:
        
        _MITLL_C2_LOGGING_FLAG = True
        logger = logging.getLogger( 'c2' )
        logger.setLevel(level)
        
        c2_expanded_file = os.path.expandvars(os.path.expanduser(c2file))
        c2_abs_file = os.path.abspath(c2_expanded_file)
        logger.addHandler(logging.FileHandler(c2_abs_file, 'w'))
        
        dev_log.info("saving c2 log file to %s", c2_abs_file)
    else:
        _MITLL_C2_LOGGING_FLAG = False

# Lincoln Log Class Definition
class LincolnLog:
    """LincolnLog - Implements debug, packet, state, and c2 logging"""
    
    # TODO: make this failsafe? check for existence of global variables in globals(), 
    # and if not there, assume no logging?
    
    # Lincolnlog Constructor
    def __init__(self, logname):
        
        # Fetch the globals
        global _MITLL_DEBUG_LOGGING_FLAG
        global _MITLL_PACKET_LOGGING_FLAG
        global _MITLL_STATE_LOGGING_FLAG
        global _MITLL_C2_LOGGING_FLAG
        
        # Define the 4 log types
        if _MITLL_DEBUG_LOGGING_FLAG:
            self._debuglog  = logging.getLogger( 'debug.' + logname )
            self._debugflag = True
        else:
            self._debugflag = False
            
        if _MITLL_PACKET_LOGGING_FLAG:
            self._packetlog = logging.getLogger( 'packet.' + logname )
            self._packetflag = True
        else:
            self._packetflag = False
            
        if _MITLL_STATE_LOGGING_FLAG:
            self._statelog  = logging.getLogger( 'state.' + logname )
            self._stateflag = True
        else:
            self._stateflag = False
            
        if _MITLL_C2_LOGGING_FLAG:
            self._c2log     = logging.getLogger( 'c2.' + logname )
            self._c2flag    = True
        else:
            self._c2flag    = False
        
    def debug(self, log, level='debug'):
        # This function writes to the debug file with logging level
        # specified by level
        
        global _MITLL_DEBUG_LOGGING_FLAG
        
        global _MITLL_DEBUG_LOGGING_FLAG
        
        if _MITLL_DEBUG_LOGGING_FLAG:
            # Check the level
            level = LincolnLogLevelCheck(level)
            
            # Create the string to write
            string = dict_to_xml_complete(log, 'debug')
            
            # Print the tag
            self._debuglog.log(level, string)
            
        
    def packet(self, log, level='debug'):
        # This function writes to the packet file with logging level
        # specified by level
        
        global _MITLL_PACKET_LOGGING_FLAG
        
        if _MITLL_PACKET_LOGGING_FLAG:
            # Check the level
            level = LincolnLogLevelCheck(level)
            
            # Create the string to write
            string = dict_to_xml_complete(log, 'packet')
            
            # Print the tag
            self._packetlog.log(level, string)
    
    def state(self, log, level='debug'):
        # This function writes to the state file with logging level
        # specified by level
        
        global _MITLL_STATE_LOGGING_FLAG
        
        if _MITLL_STATE_LOGGING_FLAG:
            # Check the level
            level = LincolnLogLevelCheck(level)
            
            # Create the string to write
            string = dict_to_xml_complete(log, 'state')
            
            # Print the tag
            self._statelog.log(level, string)
    
    def state_from_string( self, string, level='debug' ):
        # This function writes to the state file with logging level
        # specified by level. Log should be a string that will be
        # written directly to file
        global _MITLL_STATE_LOGGING_FLAG
        
        if _MITLL_STATE_LOGGING_FLAG:
            # Check the level
            level = LincolnLogLevelCheck(level)
            
            # Print the tag
            self._statelog.log(level, string)
    
    def c2(self, log, level='debug'):
        # This function writes to the c2 file with logging level
        # specified by level
        
        global _MITLL_C2_LOGGING_FLAG
        
        if _MITLL_C2_LOGGING_FLAG:
            # Check the level
            level = LincolnLogLevelCheck(level)
            
            # Create the string to write
            string = dict_to_xml_complete(log, 'c2')
            
            # Print the tag
            self._c2log.log(level, string)


#Python:
#    Programming as Guido indented it

