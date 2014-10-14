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
#

from sm import SM

# mac state machine
import sm



#=========================================================================================
# top level state machine for csma mac variants
#=========================================================================================
class csma(SM):
    '''
    Implements CSMA Variants (CSMA, CSMA-CA, CSMA-ARQ, CSMA-CA-ARQ)
    '''    
    manager = None
    switch = None
    
    def __init__(self, mac_type):
        
        self.manager = generic_session_manager()
        self._mac_type = mac_type
        
        # define an object to hold session history information and pass it between
        # tx and rx paths. The contents of this dictionary are defined by the transmit
        # and receive paths that use it
        self._session_history = dict()
        

        if mac_type == "csma-ca-arq":
            self.rx = csma_ca_arq_rx_sm()
            self.tx = csma_ca_arq_tx_sm()
    
            # add rx request validation function
            self.validate_rx_request = lambda inp: inp['rx_pkt'].type == "rts_to_me"

            # adding variables for logging
            self.type = "csma"
            self.collision_avoidance = True
            self.automatic_repeat_request = True

        elif mac_type == "csma-ca":
            self.rx = csma_ca_rx_sm()
            self.tx = csma_ca_tx_sm()
    
            # add rx request validation function
            self.validate_rx_request = lambda inp: inp['rx_pkt'].type == "rts_to_me"

            # adding variables for logging
            self.type = "csma"
            self.collision_avoidance = True
            self.automatic_repeat_request = False

        elif mac_type == "csma-arq":
            self.rx = csma_arq_rx_sm()
            self.tx = csma_arq_tx_sm()
    
            # add rx request validation function
            self.validate_rx_request = lambda inp: inp['rx_pkt'].type == "data_to_me"

            # adding variables for logging
            self.type = "csma"
            self.collision_avoidance = False
            self.automatic_repeat_request = True

        elif mac_type == "csma":
            self.rx = csma_rx_sm()
            self.tx = csma_tx_sm()
    
            # add rx request validation function
            self.validate_rx_request = lambda inp: inp['rx_pkt'].type == "data_to_me"

            # adding variables for logging
            self.type = "csma"
            self.collision_avoidance = False
            self.automatic_repeat_request = False

        
        # this assumes the input to the switch will be formatted similarly to (state, ( other stuff), (still other stuff) )
        self.stateList = ["tx", "rx", "backoff"]
        self.switch = sm.MultiSwitch(lambda control: self.stateList.index(control), [self.tx, self.rx])
    
        self.startState = (self.manager.startState, self.switch.startState)
        

    

    def getNextValues(self, state, inp):
        
        (man_state, sw_state) = state

        # check if the rx packet is a valid receive request for this mac
        inp["rx_request"] = self.validate_rx_request(inp)      
        
        
        # get next state of session manager
        (ms, mo) = self.manager.getNextValues(man_state, inp) 
        
        # add session history object to inputs so it can be used and modified by the tx
        # and rx paths
        inp["session_history"] = self._session_history
         
        # get inputs needed for switched state machine pair (tx and rx paths)
        # note that the first input is the control input
        s_inp = ( ms, inp)
        
        # pass current state of session manager into controlled switch along with
        # current inputs
        (ss, so) = self.switch.getNextValues(sw_state, s_inp)
        
        # check if switch routed inputs to null
        if (so is None):
            # TODO: +++++ adaptive in progress +++++  
            success_arq_counter = inp['success_arq_counter']
            #If not running a state machine path, don't pop rx packets 
            pop_rx_pkt = True
            so = (False, [], [], [], [], 0, False, success_arq_counter, pop_rx_pkt)
            # ++++++++++++++++++++++++++++++++++++++
            #so = (False, [], [], [], [], 0, False)
        
        nextState = self.getNextState(state, (ms, ss, inp) )
        
        outputs = (so)
        
        return (nextState, outputs)
    
    def getNextState(self, state, inp):
        
        (ms, ss, inputs) = inp
        
        if inputs == 'undefined':
            return (ms, ss)
        
        else: 
            return (ms, ss)      
        
    def add_options(opt_parser):

        # add mac options to parser
        
        opt_parser.add_option("--node-source-address", type="float", 
                              help="set node source address")
        
        # if mac option is already defined, extend choices list to include csma types
        if opt_parser.has_option("--mac"):
            mac_opt = opt_parser.get_option("--mac")
            mac_choices = mac_opt.choices 
            
            mac_choices.extend(csma.mac_types())
            
            mac_opt.choices = mac_choices
            mac_opt.help = "Select mac type from: %s [default=%%default}" % (", ".join(mac_choices))
        # otherwise add the mac option
        else:
            opt_parser.add_option("--mac", type="choice", choices=(csma.mac_types()),
                              default="csma-ca-arq",
                              help="Select mac type from: %s [default=%%default}" % (", ".join(csma.mac_types())) ) 
            
        opt_parser.add_option("--backoff-min-time", type="float",
                              help="minimum value of channel busy backoff in seconds" )
        opt_parser.add_option("--backoff-max-time", type="float",
                              help="maximum value of channel busy backoff in seconds" )
        opt_parser.add_option("--backoff-time", type="float",
                              help="initial value of backoff timer in seconds (only used at mac startup, typically = backoff-min-time)" )
        opt_parser.add_option("--tx-session-time", type="float",
                              help="maximum allowed duration of a transmit session in seconds" )
        opt_parser.add_option("--rx-session-time", type="float",
                              help="maximum allowed duration of a receive session in seconds" )
        opt_parser.add_option("--cts-time", type="float",
                              help="time a mac using RTS-CTS will wait for a CTS reply to an RTS before going to backoff, in seconds" )
        opt_parser.add_option("--ack-time", type="float",
                              help="time a mac using ARQ will wait for an ACK reply to a data packet before retransmitting data, in seconds" ) 
        
    # Make a static method to call before instantiation
    add_options = staticmethod(add_options)
    
    
    def mac_types():
        '''
        Define the mac types supported by this class
        '''
        
        return ["csma", "csma-ca", "csma-arq", "csma-ca-arq"]
    
    # Make a static method to call before instantiation
    mac_types = staticmethod(mac_types)
    
#=========================================================================================
# session manager shared by the following csma mac variants: csma, csma-ca, csma-arq, 
# csma-ca-arq
#=========================================================================================
class generic_session_manager(SM):
    '''
    General session manager that interacts with a transmit state machine and receive state
    machine. 
    The transmit path is enabled only when a backoff timer expires, and assumes that
    the transmit path will declare the tx session as done when it is complete.
    
    The receive path is enabled only when the transmit path is inactive and a valid 
    receive request (as determined by the top level state machine) is present. It assumes
    that the receive path will declare the rx session as done when it is complete.
    '''
    startState = None
    
    def __init__(self):
        self.startState = "backoff"
    
      
    def getNextValues(self, state, inp):             
        
        
        if inp == 'undefined':
            
            return (state, state )
        
        rx_request = inp['rx_request']
        expired_timers = inp['expired_timers']
        session_done = inp['session_done']

        
        if state == "backoff":
            # if received an rts addressed to me, go to rx
            if rx_request == True:
                nextState = "rx"
               
                
            # else if backoff timer has expired, go to tx
            elif ("backoff" in expired_timers):
                nextState =  "tx"
                  
            # otherwise stay in backoff
            else:
                nextState = "backoff"
                
        elif state == "rx":
            # stay in rx state until the rx path says it is done
            if ("rx" in session_done):
                # if rx_session completes and the backoff timer has expired, go directly to tx
                if ("backoff" in expired_timers):
                    nextState = "tx"
                # otherwise go to backoff    
                else:
                    nextState = "backoff"
                
            else:
                nextState = "rx"
                         
        elif state == "tx":
            # stay in the tx state until the tx path says it is done
            if ("tx" in session_done):
                nextState = "backoff"
                
            else:
                nextState = "tx"
                
        else:
            nextState = "error"
            
            
        return (nextState, nextState)    
            
#=========================================================================================
# csma_ca_arq MAC implementation
#=========================================================================================
class csma_ca_arq_tx_sm(SM):
    """ This is the transmit path state machine for a csma_ca_arq MAC
    
    This class must be used with a packet class object that provides at least the following
    fields and methods: 
    
    fields:
        type = {"ack_to_me", "cts_to_me"}
        more_data = { True, False }
    """
    
    startState = None
    
    def __init__(self):
        self.startState = "backoff"
        self.rts_num = 0
        self.rts_num_max = 65535
        
    
    def getNextValues(self, state, inp):
        """ This gets the next values of outputs and the next state
        
        """
        if inp == 'undefined':
            return (state, None)

        # unpack inputs
        expired_timers = inp['expired_timers']
        session_done = inp['session_done']
        channel_free = inp['channel_free']
        data_pkt = inp['data_pkt']
        next_data_pkt = inp['next_data_pkt']
        rx_pkt = inp['rx_pkt']

        tx_pkts = list()
        starting_timers = list()
        clearing_timers = list()
        pop_tx_pkt = False
        backoff_control = 0
        new_data_received = False
        
        # get a copy of the list of complete sessions (should be empty 99% of the time)
        session_done_out = list(session_done)
        
        # TODO: +++++ adaptive in progress +++++  
        success_arq_counter = inp['success_arq_counter']
        use_adaptive_coding = inp["use_adaptive_coding"]
        counter_size        = inp["success_arq_counter_size"]
        success_arq_counter = _update_success_arq_counter( state, inp, use_adaptive_coding, counter_size, success_arq_counter )
        # ++++++++++++++++++++++++++++++++++++++
        nextState = self.getNextState(state, inp )
        
        if ( state == "backoff"):
            # if in backoff and passed in tx session done
            if ("tx" in session_done):
                # remove tx from session_done list
                session_done_out.remove('tx')
                
            # if the backoff timer hasn't expired, do nothing    
            if (nextState == "backoff") &  (not ("backoff" in expired_timers)):
                pass
            
            # if backoff timer expires but there are no tx packets available
            elif ( (nextState == "backoff") & ("backoff" in expired_timers) &
                   (data_pkt.type == "other") ):
                
                clearing_timers.append('backoff')
                starting_timers.append('backoff')
                session_done_out.append('tx') 

                
            
            # if staying in backoff because channel was occupied
            elif (nextState == "backoff") and (channel_free == False):
               
                clearing_timers.append('backoff')
                starting_timers.append('backoff')
                session_done_out.append('tx') 
                
                # increase backoff value
                backoff_control = 1
            
            # if channel was available and the backoff timer had expired
            elif (nextState == "txRTS"):
                
                # schedule an rts packet transmission
                tx_pkts.append({"type":"rts", "to_id":data_pkt.to_id, "pktno":self.rts_num})
                self.rts_num = (self.rts_num +1) % self.rts_num_max
                
                # start the tx session and cts timers and clear the backoff timer
                clearing_timers.append('backoff')
                starting_timers.append('cts')
                starting_timers.append('tx_session')
                
                # reduce backoff value
                backoff_control = -1
                
        elif (state == "txRTS"):
 
            # if going back to backoff, clear cts and tx session timers, 
            # and start backoff timer
            if (nextState == "backoff"):
                clearing_timers.append('cts')
                clearing_timers.append('tx_session')
                
                starting_timers.append('backoff')
                
                # notify next layer up that tx session is done
                session_done_out.append('tx') 
                
            # if staying in txRTS, no action required    
            elif (nextState == "txRTS"):
                pass
                
            # if going to txDATA, we must have received a CTS. Send the current data packet    
            elif (nextState == "txDATA"):
                clearing_timers.append('cts')
                tx_pkts.append({"type":"data", "to_id":data_pkt.to_id, "pktno":data_pkt.pktno})
                starting_timers.append('ack')
                
            else:
                # TODO: log unexpected transition
                pass
                
        elif (state == "txDATA"):
            # if going back to backoff, clear ack and tx session timers, 
            # and start backoff timer
            if (nextState == "backoff"):
            
                clearing_timers.append('ack')            
                clearing_timers.append('tx_session')
                
                starting_timers.append('backoff') 
                
                # notify next layer up that tx session is done
                session_done_out.append('tx') 
            
                # either the current packet was successfully transmitted and there's no follow on
                # data, or the tx_session timed out after at least one attempt at sending a data
                # packet. Either way, we should remove the current data packet from the transmit
                # queue 
                pop_tx_pkt = True
                
            elif (nextState == "txDATA"):
                
                # if ack timer expired, we need to retransmit current packet and restart ack timer
                if ("ack" in expired_timers): 
                    
                    tx_pkts.append({"type":"data", "to_id":data_pkt.to_id, "pktno":data_pkt.pktno})
                    clearing_timers.append('ack')
                    starting_timers.append('ack')
                
                # if received an ack addressed to me and there's more data to transmit, 
                # send the next packet and reset the ack and tx_session timers
                elif (data_pkt.more_data == True) & (rx_pkt.type == "ack_to_me"):
                    
                    # move on to next tx packet
                    pop_tx_pkt = True
                    
                    tx_pkts.append({"type":"data", "to_id":next_data_pkt.to_id, 
                                    "pktno":next_data_pkt.pktno})
                    
                    clearing_timers.append('ack')
                    clearing_timers.append('tx_session')
                    
                    starting_timers.append('ack')
                    starting_timers.append('tx_session')
                    
                    
                # do nothing    
                else:
                    pass
        
        # default to True to keep previous behavior until this is more thoroughly looked at
        pop_rx_pkt = True          
        outputs = (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
                   backoff_control, new_data_received, success_arq_counter, pop_rx_pkt)
        
        return (nextState, outputs)

    
    def getNextState(self, state, inp):
                
        expired_timers = inp['expired_timers']
        channel_free = inp['channel_free']
        data_pkt = inp['data_pkt']
        next_data_pkt = inp['next_data_pkt']
        rx_pkt = inp['rx_pkt']
               
        if state == 'backoff':
            if (channel_free == True) & ( "backoff" in expired_timers) & (data_pkt.type != "other"):
                nextState = "txRTS"
            else:
                nextState = "backoff"
                
        elif state == "txRTS":
            # if the CTS or tx session timer expires
            if ("cts" in expired_timers) or ("tx_session" in expired_timers):
                nextState = "backoff"
            
            # if I get a cts packet addressed to me, go to txDATA    
            elif (rx_pkt.type == "cts_to_me") & (rx_pkt.from_id == data_pkt.to_id):
                nextState = 'txDATA' 
            # otherwise, stay put    
            else:
                nextState = "txRTS"
                
        elif state == "txDATA":
            # if the tx session timer has expired
            if ("tx_session" in expired_timers):
                nextState = "backoff"
                
            # if tx session hasn't expired, check if ack timer has expired    
            elif ("ack" in expired_timers):
                # if the ack timer expires, stay in txDATA state
                nextState = "txDATA"
                
            # if packet is ack addressed to me for most recent DATA packet    
            elif (rx_pkt.type == "ack_to_me") & (rx_pkt.from_id == data_pkt.to_id):
                # if there is supposed to be more data in the session, and that data
                # is available, stay in txData
                if (data_pkt.more_data == True) & (next_data_pkt.type != "other"):
                    nextState = "txDATA"
                # if there's no more data in the session, go to backoff
                else:
                    nextState = "backoff"
            
            # otherwise stay put
            else:
                nextState = "txDATA"        
                    
        return nextState
                      
        
class csma_ca_arq_rx_sm(SM):
    """ This is the receive path state machine for a csma_ca_arq MAC
    
    This class must be used with a packet class object that provides at least the following
    fields and methods: 
    
    fields:
        type = {"data_to_me", "rts_to_me" }
        more_data = { True, False }
    methods: 
        check_crc()
        
    """
    startState = None
        
    def __init__(self):
        session = {"rx_source":-1, "reply_pktno":-1}
        self.startState = ("backoff", session )

    def getNextValues(self, state, inp):
        
        if inp == 'undefined':
            return (state, None)
        
        expired_timers = inp['expired_timers']
        session_done = inp['session_done']
        rx_pkt = inp['rx_pkt']
        
            
        tx_pkts = list()
        starting_timers = list()
        clearing_timers = list()
        pop_tx_pkt = False
        backoff_control = 0
        new_data_received = False
        
        # get a copy of the list of complete sessions (should be empty 99% of the time)
        session_done_out = list(session_done)
        
        # TODO: +++++ adaptive in progress +++++  
        success_arq_counter = inp['success_arq_counter']
        # ++++++++++++++++++++++++++++++++++++++
        nextState = self.getNextState(state, inp )
        
        stateName = state[0]
        nextStateName = nextState[0]
        session = nextState[1]
        
        # if we're staying in backoff
        if (stateName == "backoff") & ("rx" in session_done_out):
            session_done_out.remove("rx")
                 
        # if we just started a new rx session, send a CTS and start the rx session timer
        if (stateName == "backoff") & (nextStateName == "txCTS"):
            
            starting_timers.append("rx_session")
            tx_pkts.append({"type":"cts", "to_id":session["rx_source"], 
                            "pktno":session["reply_pktno"]})
            
        # if we're staying in the tx CTS state    
        elif ( stateName == "txCTS") & (nextStateName == "txCTS"):
            
            if (rx_pkt.type == "data_to_me" ) & (rx_pkt.from_id == session["rx_source"]):
                # test if packet passes CRC check
                crc_check = rx_pkt.check_crc()
                
                # if packet passes CRC check, send ack
                if (crc_check == True):
                    tx_pkts.append({"type":"ack", "to_id":session["rx_source"],
                                    "pktno":session["reply_pktno"]})
                    new_data_received = True
                      
                    # if there's more data available, restart rx_session timer
                    if (rx_pkt.more_data == True):
                        clearing_timers.append("rx_session")
                        starting_timers.append("rx_session") 
                
                # crc failed, do nothing        
                else:
                    pass     
                        
        # if the session is done, clear the rx session timer and declare the session done    
        elif ( stateName == "txCTS" ) & (nextStateName == "backoff"):
            clearing_timers.append("rx_session")
            session_done_out.append("rx")
            
            # if transition was due to successful rx of data packet, send ack
            if (not "rx_session" in expired_timers) & (rx_pkt.type == "data_to_me" ) & (rx_pkt.from_id == session["rx_source"]):
                tx_pkts.append({"type":"ack", "to_id":session["rx_source"],
                                "pktno":session["reply_pktno"]})
                new_data_received = True
                backoff_control = -1
        
        # default to True to keep previous behavior until this is more thoroughly looked at
        pop_rx_pkt = True     
        
        outputs = (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
                   backoff_control, new_data_received, success_arq_counter, pop_rx_pkt) 
        
        return (nextState, outputs)  
      
    
    def getNextState(self, state, inp): 

        # unpack inputs
        expired_timers = inp['expired_timers']
        rx_pkt = inp['rx_pkt']
        
        stateName = state[0]
        session = state[1]
        
        if ( stateName ==  "backoff"):
            if (rx_pkt.type == "rts_to_me"):
                # if rx packet is rts to me (which it should be if things are working as expected), 
                # go to txCTS
                nextStateName = "txCTS"
                
                # store session info
                session["rx_source"] = rx_pkt.from_id
                session["reply_pktno"] = rx_pkt.pktno
                
            else:
                nextStateName = "backoff"
            
        elif ( stateName ==  "txCTS"):
            # if the rx session timer has expired
            if ("rx_session" in expired_timers):
                nextStateName = "backoff"
            
            # if packet is data addressed to me from the session source
            elif (rx_pkt.type == "data_to_me" ) & (rx_pkt.from_id == session["rx_source"]):
                # test if packet passes CRC check
                crc_check = rx_pkt.check_crc()
                
                # if packet passes CRC check and there's more data available, stay in txCTS
                if (crc_check == True) & (rx_pkt.more_data == True):
                    nextStateName = "txCTS"
                    
                    # store data packet number ( for acking ) 
                    session["reply_pktno"] = rx_pkt.pktno
                
                # if packet passes CRC check and there's no more data available, go to backoff    
                elif (crc_check == True) & (rx_pkt.more_data == False):  
                    
                    nextStateName = "backoff"
                    
                    # store data packet number (for acking)
                    session["reply_pktno"] = rx_pkt.pktno

                # if the packet failed crc, stay in txCTS
                else:
                    nextStateName = "txCTS"
            
            # packet isn't data to me, so ignore it
            else:
                nextStateName = "txCTS" 
         
        return (nextStateName, session)    

#=========================================================================================
# csma_ca MAC implementation
#=========================================================================================       
class csma_ca_tx_sm(SM):
    """ This is the transmit path state machine for a csma_ca MAC
    """
    
    startState = None
    
    def __init__(self):
        self.startState = "backoff"
        self.rts_num = 0
        self.rts_num_max = 65535
        
    
    def getNextValues(self, state, inp):
        """ This gets the next values of outputs and the next state
        
        """
        if inp == 'undefined':
            return (state, None)

        # unpack inputs
        expired_timers = inp['expired_timers']
        session_done = inp['session_done']
        channel_free = inp['channel_free']
        data_pkt = inp['data_pkt']
        rx_pkt = inp['rx_pkt']

        tx_pkts = list()
        starting_timers = list()
        clearing_timers = list()
        pop_tx_pkt = False
        backoff_control = 0
        new_data_received = False
        
        # get a copy of the list of complete sessions (should be empty 99% of the time)
        session_done_out = list(session_done)
        
        # TODO: +++++ adaptive in progress +++++  
        success_arq_counter = inp['success_arq_counter']
        # ++++++++++++++++++++++++++++++++++++++
        nextState = self.getNextState(state, inp )
        
        if ( state == "backoff"):
            # if in backoff and passed in tx session done
            if ("tx" in session_done):
                # remove tx from session_done list
                session_done_out.remove('tx')
                
            # if the backoff timer hasn't expired, do nothing    
            if (nextState == "backoff") &  (not ("backoff" in expired_timers)):
                pass
            
            # if backoff timer expires but there are no tx packets available
            elif ( (nextState == "backoff") & ("backoff" in expired_timers) &
                   (data_pkt.type == "other") ):
                
                clearing_timers.append('backoff')
                starting_timers.append('backoff')
                session_done_out.append('tx') 

                
            
            # if staying in backoff because channel was occupied
            elif (nextState == "backoff") and (channel_free == False):
               
                clearing_timers.append('backoff')
                starting_timers.append('backoff')
                session_done_out.append('tx') 
                
                # increase backoff value
                backoff_control = 1
            
            # if channel was available and the backoff timer had expired
            elif (nextState == "txRTS"):
                
                # schedule an rts packet transmission
                tx_pkts.append({"type":"rts", "to_id":data_pkt.to_id, "pktno":self.rts_num})
                self.rts_num = (self.rts_num +1) % self.rts_num_max
                
                # start the tx session and cts timers and clear the backoff timer
                clearing_timers.append('backoff')
                starting_timers.append('cts')
                starting_timers.append('tx_session')
                
                # reduce backoff value
                backoff_control = -1
                
        elif (state == "txRTS"):
 
            # if going back to backoff, clear cts and tx session timers and start backoff 
            # timer 
            if (nextState == "backoff"):
                
                clearing_timers.append('cts')
                clearing_timers.append('tx_session')
                
                starting_timers.append('backoff')
                
                # notify next layer up that tx session is done
                session_done_out.append('tx') 
                
                
                # if transition to backoff is due to valid cts to me, send the current 
                # data packet and pop it from the tx queue
                if(rx_pkt.type == "cts_to_me") & (rx_pkt.from_id == data_pkt.to_id):
                    tx_pkts.append({"type":"data", "to_id":data_pkt.to_id, "pktno":data_pkt.pktno})
                    pop_tx_pkt = True
                    
            # if staying in txRTS, no action required    
            elif (nextState == "txRTS"):
                pass
                
        # default to True to keep previous behavior until this is more thoroughly looked at
        pop_rx_pkt = True               
        outputs = (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
                   backoff_control, new_data_received, success_arq_counter, pop_rx_pkt)
        
        return (nextState, outputs)

    
    def getNextState(self, state, inp):
                
        expired_timers = inp['expired_timers']
        channel_free = inp['channel_free']
        data_pkt = inp['data_pkt']        
        rx_pkt = inp['rx_pkt']
               
        if state == 'backoff':
            if (channel_free == True) & ( "backoff" in expired_timers) & (data_pkt.type != "other"):
                nextState = "txRTS"
            else:
                nextState = "backoff"
                
        elif state == "txRTS":
            # if the CTS or tx session timer expires
            if ("cts" in expired_timers) or ("tx_session" in expired_timers):
                nextState = "backoff"
            
            # if I get a cts packet addressed to me, go to backoff    
            elif (rx_pkt.type == "cts_to_me") & (rx_pkt.from_id == data_pkt.to_id):
                nextState = 'backoff' 
            # otherwise, stay put    
            else:
                nextState = "txRTS"    
                    
        return nextState
                      
        
class csma_ca_rx_sm(SM):
    """ This is the receive path state machine for a csma_ca MAC
    
    This class must be used with a packet class object that provides at least the following
    fields and methods: 
        
    """
    startState = None
        
    def __init__(self):
        session = {"rx_source":-1, "reply_pktno":-1}
        self.startState = ("backoff", session )

    def getNextValues(self, state, inp):
        
        if inp == 'undefined':
            return (state, None)
        
        expired_timers = inp['expired_timers']
        session_done = inp['session_done']
        rx_pkt = inp['rx_pkt']
        
            
        tx_pkts = list()
        starting_timers = list()
        clearing_timers = list()
        pop_tx_pkt = False
        backoff_control = 0
        new_data_received = False
        
        # get a copy of the list of complete sessions (should be empty 99% of the time)
        session_done_out = list(session_done)
        
        # TODO: +++++ adaptive in progress +++++  
        success_arq_counter = inp['success_arq_counter']
        # ++++++++++++++++++++++++++++++++++++++
        nextState = self.getNextState(state, inp )
        
        stateName = state[0]
        nextStateName = nextState[0]
        session = nextState[1]
        
        # if we're staying in backoff
        if (stateName == "backoff") & ("rx" in session_done_out):
            session_done_out.remove("rx")
                 
        # if we just started a new rx session, send a CTS and start the rx session timer
        if (stateName == "backoff") & (nextStateName == "txCTS"):
            
            starting_timers.append("rx_session")
            tx_pkts.append({"type":"cts", "to_id":session["rx_source"], 
                            "pktno":session["reply_pktno"]})
            
        # if we're staying in the tx CTS state    
        elif ( stateName == "txCTS") & (nextStateName == "txCTS"):
            # do nothing
            pass     
                        
        # if the session is done, clear the rx session timer and declare the session done    
        elif ( stateName == "txCTS" ) & (nextStateName == "backoff"):
            clearing_timers.append("rx_session")
            session_done_out.append("rx")
            
            # if transition was due to successful rx of data packet, tell network layer
            # that there's new data and reduce the backoff timeout
            if (not "rx_session" in expired_timers) & (rx_pkt.type == "data_to_me" ) & (session["rx_source"] == rx_pkt.from_id):
                new_data_received = True
                backoff_control = -1
        
        
        # default to True to keep previous behavior until this is more thoroughly looked at
        pop_rx_pkt = True     
        outputs = (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
                   backoff_control, new_data_received, success_arq_counter, pop_rx_pkt) 
        
        return (nextState, outputs)  
      
    
    def getNextState(self, state, inp): 

        # unpack inputs
        expired_timers = inp['expired_timers']
        rx_pkt = inp['rx_pkt']
        
        stateName = state[0]
        session = state[1]
        
        if ( stateName ==  "backoff"):
            if (rx_pkt.type == "rts_to_me"):
                # if rx packet is rts to me (which it should be if things are working as expected), 
                # go to txCTS
                nextStateName = "txCTS"
                
                # store session info
                session["rx_source"] = rx_pkt.from_id
                session["reply_pktno"] = rx_pkt.pktno
                
            else:
                nextStateName = "backoff"
            
        elif ( stateName ==  "txCTS"):
            # if the rx session timer has expired
            if ("rx_session" in expired_timers):
                nextStateName = "backoff"
            
            # if packet is data addressed to me, go to backoff 
            elif (rx_pkt.type == "data_to_me" ) & (session["rx_source"] == rx_pkt.from_id):
        
                nextStateName = "backoff"

            # packet isn't data to me, so ignore it
            else:
                nextStateName = "txCTS" 
         
        return (nextStateName, session)    

#=========================================================================================
# csma_arq MAC implementation
#=========================================================================================     
class csma_arq_tx_sm(SM):
    """ This is the transmit path state machine for a csma_arq MAC
    
    """
    
    startState = None
    
    def __init__(self):
        self.startState = "backoff"
        
    
    def getNextValues(self, state, inp):
        """ This gets the next values of outputs and the next state
        
        """
        if inp == 'undefined':
            return (state, None)

        # unpack inputs
        expired_timers = inp['expired_timers']
        session_done = inp['session_done']
        channel_free = inp['channel_free']
        data_pkt = inp['data_pkt']
        next_data_pkt = inp['next_data_pkt']
        rx_pkt = inp['rx_pkt']
        session_history = inp['session_history']

        tx_pkts = list()
        starting_timers = list()
        clearing_timers = list()
        pop_tx_pkt = False
        backoff_control = 0
        
        # get a copy of the list of complete sessions (should be empty 99% of the time)
        session_done_out = list(session_done)
        
        # TODO: +++++ adaptive in progress +++++  
        success_arq_counter = inp['success_arq_counter']
        use_adaptive_coding = inp["use_adaptive_coding"]
        counter_size        = inp["success_arq_counter_size"]
        success_arq_counter = _update_success_arq_counter( state, inp, use_adaptive_coding, counter_size, success_arq_counter )
        # ++++++++++++++++++++++++++++++++++++++
        nextState = self.getNextState(state, inp )
        
        # if we get a data_to_me packet that passes crc, always ack to it and handle 
        # the new_data_received and session_history variables appropriately
        outvars = _csma_arq_handle_data(rx_pkt, tx_pkts, session_history)
        
        (crc_check, new_data_received, tx_pkts, session_history) = outvars  
        
        
        if ( state == "backoff"):
            # if in backoff and passed in tx session done
            if ("tx" in session_done):
                # remove tx from session_done list
                session_done_out.remove('tx')
                
            # if the backoff timer hasn't expired, do nothing    
            if (nextState == "backoff") &  (not ("backoff" in expired_timers)):
                pass
            
            # if backoff timer expires but there are no tx packets available
            elif ( (nextState == "backoff") & ("backoff" in expired_timers) &
                   (data_pkt.type == "other") ):
                
                clearing_timers.append('backoff')
                starting_timers.append('backoff')
                session_done_out.append('tx') 

                
            
            # if staying in backoff because channel was occupied
            elif (nextState == "backoff") and (channel_free == False):
               
                clearing_timers.append('backoff')
                starting_timers.append('backoff')
                session_done_out.append('tx') 
                
                # increase backoff value
                backoff_control = 1
            
            # if channel was available and the backoff timer had expired
            elif (nextState == "txDATA"):
                
                # schedule a data packet transmission
                tx_pkts.append({"type":"data", "to_id":data_pkt.to_id, "pktno":data_pkt.pktno})
                
                # start the tx session and cts timers and clear the backoff timer
                starting_timers.append('ack')
                clearing_timers.append('backoff')
                starting_timers.append('tx_session')
                
                # reduce backoff value
                backoff_control = -1
                
        elif (state == "txDATA"):
            # if going back to backoff, clear ack and tx session timers, 
            # and start backoff timer
            if (nextState == "backoff"):
            
                clearing_timers.append('ack')            
                clearing_timers.append('tx_session')
                
                starting_timers.append('backoff') 
                
                # notify next layer up that tx session is done
                session_done_out.append('tx') 
            
                # either the current packet was successfully transmitted and there's no follow on
                # data, or the tx_session timed out after at least one attempt at sending a data
                # packet. Either way, we should remove the current data packet from the transmit
                # queue 
                pop_tx_pkt = True
                
            elif (nextState == "txDATA"):
                
                # if ack timer expired, we need to retransmit current packet and restart ack timer
                if ("ack" in expired_timers): 
                    
                    tx_pkts.append({"type":"data", "to_id":data_pkt.to_id, "pktno":data_pkt.pktno})
                    clearing_timers.append('ack')
                    starting_timers.append('ack')
                
                # if received an ack addressed to me and there's more data to transmit, 
                # send the next packet and reset the ack and tx_session timers
                elif (data_pkt.more_data == True) & (rx_pkt.type == "ack_to_me") & (rx_pkt.from_id == data_pkt.to_id):
                    
                    # move on to next tx packet
                    pop_tx_pkt = True
                    
                    # send out next packet (can't have nextState == txData) unless the
                    # next packet exists, see getNextState
                    tx_pkts.append({"type":"data", "to_id":next_data_pkt.to_id, 
                                    "pktno":next_data_pkt.pktno})
                    
                    clearing_timers.append('ack')
                    clearing_timers.append('tx_session')
                    
                    starting_timers.append('ack')
                    starting_timers.append('tx_session')
                    
                    
                # do nothing    
                else:
                    pass
        
        # default to True to keep previous behavior until this is more thoroughly looked at
        pop_rx_pkt = True               
        outputs = (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
                   backoff_control, new_data_received, success_arq_counter, pop_rx_pkt)
        
        return (nextState, outputs)

    
    def getNextState(self, state, inp):
                
        expired_timers = inp['expired_timers']
        channel_free = inp['channel_free']
        data_pkt = inp['data_pkt']
        next_data_pkt = inp['next_data_pkt']
        rx_pkt = inp['rx_pkt']
               
        if state == 'backoff':
            if (channel_free == True) & ( "backoff" in expired_timers) & (data_pkt.type != "other"):
                nextState = "txDATA"
            else:
                nextState = "backoff"
                
        elif state == "txDATA":
            # if the tx session timer has expired
            if ("tx_session" in expired_timers):
                nextState = "backoff"
                
            # if tx session hasn't expired, check if ack timer has expired    
            elif ("ack" in expired_timers):
                # if the ack timer expires, stay in txDATA state
                nextState = "txDATA"
                
            # if packet is ack addressed to me for most recent DATA packet    
            elif (rx_pkt.type == "ack_to_me") & (rx_pkt.from_id == data_pkt.to_id):
                # if there is supposed to be more data in the session, stay in txData
                if (data_pkt.more_data == True) & (next_data_pkt.type != "other"):
                    nextState = "txDATA"
                # if there's no more data in the session, go to backoff
                else:
                    nextState = "backoff"
            
            # otherwise stay put
            else:
                nextState = "txDATA"        
                    
        return nextState
                      
        
class csma_arq_rx_sm(SM):
    """ This is the receive path state machine for a csma_arq MAC
        
    """
    startState = None
        
    def __init__(self):
        session = {"rx_source":-1, "reply_pktno":-1}
        self.startState = ("backoff", session )

    def getNextValues(self, state, inp):
        
        if inp == 'undefined':
            return (state, None)
        
        expired_timers = inp['expired_timers']
        session_done = inp['session_done']
        rx_pkt = inp['rx_pkt']
        session_history = inp['session_history']
            
        tx_pkts = list()
        starting_timers = list()
        clearing_timers = list()
        pop_tx_pkt = False
        backoff_control = 0
        new_data_received = False
        
        # get a copy of the list of complete sessions (should be empty 99% of the time)
        session_done_out = list(session_done)
        
        # TODO: +++++ adaptive in progress +++++  
        success_arq_counter = inp['success_arq_counter']
        # ++++++++++++++++++++++++++++++++++++++
        nextState = self.getNextState(state, inp )
        
        stateName = state[0]
        nextStateName = nextState[0]
        session = state[1] 
                
        # if rx is in session_done
        if (stateName == "backoff") & ("rx" in session_done_out):
            session_done_out.remove("rx")
                       
        # if we're staying in backoff
        if (stateName == "backoff") & (nextStateName == "backoff"):
            
            # if staying in backoff, rx session must be done
            session_done_out.append("rx")
                
            # if we've received a single data packet with no follow on data, 
            # declare the rx session is done, and reduce backoff
            if(rx_pkt.type == "data_to_me" ):
            
                # if we get a data_to_me packet that passes crc, ack to it and handle 
                # the new_data_received and session_history variables appropriately
                outvars = _csma_arq_handle_data(rx_pkt, tx_pkts, session_history)
                
                (crc_check, new_data_received, tx_pkts, session_history) = outvars   
                
                
                # crc check will always be done for data_to_me packets
                #crc_check = rx_pkt.check_crc()
                if crc_check:
                    
                    backoff_control = -1
                    
                     
        # if we just started a new rx session, start the rx session timer
        elif (stateName == "backoff") & (nextStateName == "txCTS"):
            
            # if we get a data_to_me packet that passes crc, ack to it and handle 
            # the new_data_received and session_history variables appropriately
            outvars = _csma_arq_handle_data(rx_pkt, tx_pkts, session_history)
            
            (crc_check, new_data_received, tx_pkts, session_history) = outvars  
            starting_timers.append("rx_session")
            
        # if we're staying in the tx CTS state    
        elif ( stateName == "txCTS") & (nextStateName == "txCTS"):
            
            if (rx_pkt.type == "data_to_me" ) & (rx_pkt.from_id == session["rx_source"]):
                
                # if we get a data_to_me packet that passes crc, ack to it and handle 
                # the new_data_received and session_history variables appropriately
                outvars = _csma_arq_handle_data(rx_pkt, tx_pkts, session_history)
                
                (crc_check, new_data_received, tx_pkts, session_history) = outvars   
                
                # if packet passes CRC check, and there's more data available, 
                # restart rx_session timer
                if (crc_check == True) & (rx_pkt.more_data == True):

                    clearing_timers.append("rx_session")
                    starting_timers.append("rx_session") 
                
                # crc failed, do nothing        
                else:
                    pass     
                        
        # if the session is done, clear the rx session timer and declare the session done    
        elif ( stateName == "txCTS" ) & (nextStateName == "backoff"):
            clearing_timers.append("rx_session")
            session_done_out.append("rx")
            
            # if transition was due to successful rx of data packet, reduce backoff
            if (not "rx_session" in expired_timers) & (rx_pkt.type == "data_to_me" ) & (rx_pkt.from_id == session["rx_source"]):

                # if we get a data_to_me packet that passes crc, ack to it and handle 
                # the new_data_received and session_history variables appropriately
                outvars = _csma_arq_handle_data(rx_pkt, tx_pkts, session_history)
                
                (crc_check, new_data_received, tx_pkts, session_history) = outvars  
                
                backoff_control = -1
        
        # default to True to keep previous behavior until this is more thoroughly looked at
        pop_rx_pkt = True     
        
        outputs = (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
                   backoff_control, new_data_received, success_arq_counter, pop_rx_pkt) 
        
        return (nextState, outputs)  
      
    
    def getNextState(self, state, inp): 

        # unpack inputs
        expired_timers = inp['expired_timers']
        rx_pkt = inp['rx_pkt']
        
        stateName = state[0]
        session = state[1]
        
        if ( stateName ==  "backoff"):
            if (rx_pkt.type == "data_to_me" ):
                # test if packet passes CRC check
                crc_check = rx_pkt.check_crc()
                
                # if packet passes CRC check and there's more data available, go to txCTS
                if (crc_check == True) & (rx_pkt.more_data == True):
                    nextStateName = "txCTS"
                    
                    # store data packet number and source ( for acking )
                    session["rx_source"] = rx_pkt.from_id
                    session["reply_pktno"] = rx_pkt.pktno
                
                # if packet passes CRC check and there's no more data available, go to backoff    
                elif (crc_check == True) & (rx_pkt.more_data == False):  
                    
                    nextStateName = "backoff"
                    
                    # store data packet number (for acking)
                    session["reply_pktno"] = rx_pkt.pktno

                # if the packet failed crc, stay in backoff
                else:
                    nextStateName = "backoff"
            
            # packet isn't data to me, so ignore it
            else:
                nextStateName = "backoff"
                
        elif ( stateName ==  "txCTS"):
            # if the rx session timer has expired
            if ("rx_session" in expired_timers):
                nextStateName = "backoff"
            
            # if we get another data packet from the same rx source    
            elif (rx_pkt.type == "data_to_me" ) & (rx_pkt.from_id == session["rx_source"]):
                # test if packet passes CRC check
                crc_check = rx_pkt.check_crc()
                
                # if packet passes CRC check and there's more data available, stay in txCTS
                if (crc_check == True) & (rx_pkt.more_data == True):
                    nextStateName = "txCTS"
                    
                    # store data packet number ( for acking ) 
                    session["reply_pktno"] = rx_pkt.pktno
                
                # if packet passes CRC check and there's no more data available, go to backoff    
                elif (crc_check == True) & (rx_pkt.more_data == False):  
                    
                    nextStateName = "backoff"
                    
                    # store data packet number (for acking)
                    session["reply_pktno"] = rx_pkt.pktno

                # if the packet failed crc, stay in txCTS
                else:
                    nextStateName = "txCTS"
            
            # packet isn't data to me, so ignore it
            else:
                nextStateName = "txCTS"  
         
        return (nextStateName, session)

# utility function shared by csma-arq-tx and csma-arq-rx    
def _csma_arq_handle_data(rx_pkt, tx_pkts, session_history):
    
    new_data_received = False
    crc_check = False
    
    if(rx_pkt.type == "data_to_me" ):
            
        crc_check = rx_pkt.check_crc()
        if crc_check:
            
            # send ack
            tx_pkts.append({"type":"ack", "to_id":rx_pkt.from_id,
                            "pktno":rx_pkt.pktno})
            
            # check if packet source is already in the session history
            if rx_pkt.from_id in session_history:
                # if the packet number for the current source is different from the 
                # previous data packet from that same source, call the packet new
                # and update the session history
                if rx_pkt.pktno != session_history[rx_pkt.from_id]:
                    new_data_received = True
                    session_history[rx_pkt.from_id] = rx_pkt.pktno
                    
            # if the packet source isn't in the session history, it has to be new.
            # Call it a new packet and update the session history        
            else:
                new_data_received = True
                session_history[rx_pkt.from_id] = rx_pkt.pktno
        
    return (crc_check, new_data_received, tx_pkts, session_history)

# Utility function for incrementing and decrementing the success/failure counters
def _update_success_arq_counter( state, inp, use_adaptive_coding, counter_size, success_arq_counter ):

    # Get the necessary data from inp.
    expired_timers = inp['expired_timers']
    channel_free = inp['channel_free']
    data_pkt = inp['data_pkt']
    next_data_pkt = inp['next_data_pkt']
    rx_pkt = inp['rx_pkt']

    if state == "txDATA" and use_adaptive_coding:
        # if the tx session timer has expired
        if ("tx_session" in expired_timers):
            # We had a failure. Decrement the success_arq_counter
            success_arq_counter[str(data_pkt.to_id)] = [0,] + success_arq_counter[str(data_pkt.to_id)][:counter_size-1]
            
        # if tx session hasn't expired, check if ack timer has expired    
        elif ("ack" in expired_timers):
            # TODO:For now we do nothing. We may change this at some time.
            pass
            
        # if packet is ack addressed to me for most recent DATA packet    
        elif (rx_pkt.type == "ack_to_me") & (rx_pkt.from_id == data_pkt.to_id):
            # We had a success. Increment the success_arq_counter
            success_arq_counter[str(data_pkt.to_id)] = [1,] + success_arq_counter[str(data_pkt.to_id)][:counter_size-1]
        
        # otherwise stay put
        else:
            pass
             
    return success_arq_counter
    

#=========================================================================================
# csma MAC implementation
#=========================================================================================    
class csma_tx_sm(SM):
    """ This is the transmit path state machine for a csma MAC
    
    This class must be used with a packet class object that provides at least the following
    fields and methods: 
    
    fields:
        type = {"data_to_other", "other"}
    """
    
    startState = None
    
    def __init__(self):
        self.startState = "backoff"
        
    
    def getNextValues(self, state, inp):
        """ This gets the next values of outputs and the next state
        
        """
        if inp == 'undefined':
            return (state, None)

        # unpack inputs
        expired_timers = inp['expired_timers']
        session_done = inp['session_done']
        channel_free = inp['channel_free']
        data_pkt = inp['data_pkt']

        tx_pkts = list()
        starting_timers = list()
        clearing_timers = list()
        pop_tx_pkt = False
        backoff_control = 0
        new_data_received = False
        
        # get a copy of the list of complete sessions (should be empty 99% of the time)
        session_done_out = list(session_done)
        nextState = "backoff"
        
        # TODO: +++++ adaptive in progress +++++  
        success_arq_counter = inp['success_arq_counter']
        # ++++++++++++++++++++++++++++++++++++++
           
        # if in backoff and passed in tx session done
        if ("tx" in session_done_out):
            # remove tx from session_done list
            session_done_out.remove('tx')
        
        # if backoff timer has exired
        if ( "backoff" in expired_timers):
            # if the channel is free and there are tx packets available 
            if (channel_free == True) & (data_pkt.type != "other"):
                # send data packet and tell next layer to pop the sent packet off the queue
                tx_pkts.append({"type":"data", "to_id":data_pkt.to_id, "pktno":data_pkt.pktno})
                pop_tx_pkt = True
                
                # reduce backoff value
                backoff_control = -1
            
            # if channel was busy, increase backoff    
            elif (channel_free == False):
                # increase backoff value
                backoff_control = 1

            # whether or not the data packet was sent, the session is considered done and the 
            # backoff timer needs to be restarted
            session_done_out.append('tx')
            clearing_timers.append('backoff')
            starting_timers.append('backoff')      
             
        # if the backoff timer hasn't expired, do nothing
        else:                    
            pass
        
        # this path does not look at RX packets at all, so don't pop
        pop_rx_pkt = False               
        outputs = (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
                   backoff_control, new_data_received, success_arq_counter, pop_rx_pkt)
        
        return (nextState, outputs)

                      
        
class csma_rx_sm(SM):
    """ This is the receive path state machine for a csma MAC
    
    This class must be used with a packet class object that provides at least the following
    fields and methods: 
    
    fields:
        type = {"data_to_me" }
    methods: 
        check_crc()
        
    """
    startState = None
        
    def __init__(self, logger=None):
        self.startState = "backoff"        
        
    def getNextValues(self, state, inp):
        
        if inp == 'undefined':
            return (state, None)
        
        session_done = inp['session_done']
        rx_pkt = inp['rx_pkt']
            
        tx_pkts = list()
        starting_timers = list()
        clearing_timers = list()
        pop_tx_pkt = False
        backoff_control = 0
        new_data_received = False
        
        # get a copy of the list of complete sessions (should be empty 99% of the time)
        session_done_out = list(session_done)
        
        # TODO: +++++ adaptive in progress +++++  
        success_arq_counter = inp['success_arq_counter']
        # ++++++++++++++++++++++++++++++++++++++./
        nextState = "backoff"
        
        # if the rx session is done, remove that from session_done
        if "rx" in session_done_out:
            session_done_out.remove("rx")
            
        # rx session always declares done regardless of correct packet or not
        session_done_out.append("rx")
        
        # if packet is data addressed to me
        if (rx_pkt.type == "data_to_me" ):
            # test if packet passes CRC check
            crc_check = rx_pkt.check_crc()
               
            # if packet passes CRC check, notify the next layer that there's new data and reduce 
            # backoff    
            if (crc_check == True):  
                new_data_received = True
                backoff_control = -1
        
        # packet isn't data to me, so ignore it
        else:
            pass
        
        # default to True to keep previous behavior until this is more thoroughly looked at
        pop_rx_pkt = True     
        outputs = (pop_tx_pkt, tx_pkts, clearing_timers, starting_timers, session_done_out, 
                   backoff_control, new_data_received, success_arq_counter, pop_rx_pkt) 
        
        return (nextState, outputs)  

#
# Add the csma family of macs to the mac registry
#
sm.add_mac_type('csma', csma)
