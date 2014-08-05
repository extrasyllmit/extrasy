# Copyright 2012 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

#import pmt, first from local super tree if possible
try: import pmt
except ImportError: from gruel import pmt

from gnuradio import gr
import pmt_to_python #injects into pmt

class pmt_rpc(gr.basic_block):
    """
    The PMT RPC block accepts formatted messages, performs an RPC, and returns the result.

    Request PMT format:
        msg.key = the name of the function to call
        msg.value = (args_tuple, kwargs_dict)
            Thats a tuple of args, kwargs.

    Response PMT format:
        msg.key = the same name of the function call
        msg.value = (args, kwargs, result, error)
            Thats the same args, kwargs passed before.
            The result is the return value.
            Error is null or a string error message.

    Special python exec programming arg:
        If the arg is a string starting with #!,
        the handler will execute the string,
        and the new arg will get the value of
        the "arg" variable. Example:

        #!
        import numpy
        foo = numpy.array([1, 2, 3])
        bar = sum(foo)
        arg = max(bar, 0) #arg is the result

    """

    def __init__(self, obj, result_msg = True):
        """
        Make the PMT RPC.
        @param obj the object to make function calls on
        @param result_msg true to produce result messages
        """
        self._obj = obj
        self._result_msg = result_msg
        gr.basic_block.__init__(
            self,
            name = "pmt rpc",
            in_sig = None,
            out_sig = None
        )
        self.IN_PORT = pmt.from_python('in')
        self.OUT_PORT = pmt.from_python('out')
        
        
        self.message_port_register_out(self.OUT_PORT)
        self.message_port_register_in(self.IN_PORT)
        self.set_msg_handler(self.IN_PORT, self.handle_request)
        
    def work(self, input_items, output_items):
        while True:
            pass
#            try: msg = self.pop_msg_queue()
#            except: return -1
#            result = self.handle_request(pmt.to_python(msg.key), pmt.to_python(msg.value))
#            try: msg.value = pmt.from_python(result)
#            except Exception as ex: msg.value = pmt.from_python(str(ex))
#            if self._result_msg: self.post_msg(0, msg)

    @staticmethod
    def _exec_arg(arg):
        if isinstance(arg, str) and arg.startswith('#!'):
            d = dict()
            try: exec(arg, d)
            except: pass
            try: return d['arg']
            except KeyError: pass
        return arg

    def handle_request(self, pdu ):
        if pmt.pmt_is_pair(pdu):
        
            # get the first and last elements of the pair
            fcn_name = pmt.to_python(pmt.pmt_car(pdu))
            request = pmt.to_python(pmt.pmt_cdr(pdu))
            
        #try to parse the request
        try:
            args, kwargs = request
            if args is None: args = tuple()
            if kwargs is None: kwargs = dict()
        except:
            err = 'cannot parse request for %s, expected tuple of args, kwargs'%fcn_name
            print err
            #return request, None, err
            return

        #exec python code and squash down to objects
        args = map(self._exec_arg, args)
        for key, val in kwargs.iteritems():
            kwargs[key] = self._exec_arg(val)

        #fly through dots to get the fcn pointer
        try:
            fcn_ptr = self._obj
            for name in fcn_name.split('.'):
                fcn_ptr = getattr(fcn_ptr, name)
        except:
            err = 'cannot find function %s in %s'%(fcn_name, self._obj)
            print err
            #return request, None, err
            return
        
        #try to execute the request
        try:
            ret = fcn_ptr(*args, **kwargs)
        except Exception as ex:
            err = 'cannot execute request for %s, got error %s'%(fcn_name, ex)
            print err
            #return request, None, err
            return
        
        #return the sucess result
        #return request, ret, None
        self.message_port_pub(self.OUT_PORT, pmt.from_python(ret)) 
