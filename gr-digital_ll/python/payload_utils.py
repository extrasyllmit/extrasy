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

import struct

from argparse import Namespace

class Payload_Packet:  
    # packet types 
   
    def __init__(self):
        
        # map packet type to integers
        self.types_to_ints = self.packet_types_to_ints()
        
        self.ints_to_types = dict()
        
        # map from integers back to packet type
        for key in self.types_to_ints:
            self.ints_to_types[self.types_to_ints[key]] = key
        
#        self.to_id = ''
#        self.from_id = ''
#        self.packet_id = 0
#        self.packet_code = 'rts'
#        self.data = ''
        
    
    def pack_payload(self, from_id, to_id, pktno, pad_bytes, pkt_code_str, phy_code, mac_code, 
                more_data, data):
        """
        Concatenates 'header' fields with data to form a payload suitable 
        to pass into either the narrowband or ofdm packet structs
        
        from_id is 16 bit unsigned short
        to_id is 16 bit unsigned short
        packet_id is 16 bit unsigned short
        packet_code_int is 16 bit unsigned short
        more_data_follows is a flag added to data packets to signal that more data is left in session
            more_data is 16 bit field with flag in LSB
        """
        
        
        
        pkt_code = self.types_to_ints[pkt_code_str]  
        
#        print "packing packet type %s as code %s" % (pkt_code_str, pkt_code)
         
        packed_header = struct.pack('!HHHHHHH', pktno, pad_bytes, from_id, to_id, pkt_code, 
                                    phy_code, mac_code)
        
        if pkt_code_str == 'DATA':
            more_dat = struct.pack('!B', more_data)
            payload = ''.join((packed_header,more_dat, data))
        else:
            payload = packed_header
        
        return payload
    
    def unpack_payload(self, payload):
        """
        The inverse of pack_payload: This pulls the 'header' fields out
        of the provided payload and returns them as a list of tuples
        """
        
#        (pktno,)     = struct.unpack('!H', payload[0:2])
#        (pad_bytes,) = struct.unpack('!H', payload[2:4])
#        (from_id,)    = struct.unpack('!H', payload[4:6])
#        (to_id,)      = struct.unpack('!H', payload[6:8])
#        (pkt_code,)   = struct.unpack('!H', payload[8:10])
#        (phy_code,)   = struct.unpack('!H', payload[10:12])
#        (mac_code,)   = struct.unpack('!H', payload[12:14])
        (pktno, pad_bytes, from_id, to_id, pkt_code, phy_code, mac_code,) = \
            struct.unpack_from('!HHHHHHH', payload)
        
        pkt_code_str = self.ints_to_types[ pkt_code ]
        
#        print "unpacking packet code %s as type %s" % ( pkt_code, pkt_code_str)
        
        if pkt_code_str == 'DATA':
            # more data field is at byte 14 of payload
            # struct.unpack returns a tuple, even for 1 item
            (more_data,) = struct.unpack('!B', payload[14])
            
            # data follows from bytes 15 to end
            data = payload[15:len(payload)]
        else:
            more_data = 0
            data = ''
            
        # build namespace object to return results    
        
        outs = (from_id, to_id, pktno, pad_bytes, pkt_code_str, phy_code, mac_code, 
                more_data, data)
        return outs
        #return ( from_id, to_id, packet_id, packet_code_str, more_data_follows, data)
        
    def pad_payload(self, payload):
        '''
        Given a packet as a character string that already includes the 'header' fields
        inserted by pack_payload, pad the payload and modify the pay_bytes header field
        as required by the phy layer (note: this should be moved into the phy layer)
        '''
              
        # unpack packet to get at header and payload separately
        (from_id, to_id, pktno, pad_bytes, pkt_code_str, phy_code, mac_code, 
                more_data, data) = self.unpack_payload(payload)
        
        #hardcoded K from configuration of RS coding in packet_utils.py
        RS_K = 4  #this number is in bytes
    
        pad_tmp = (len(payload)+4) % RS_K  #+4 for crc since crc is performed before RS coding 
        
        if pad_tmp == 0:
            pad_bytes =0
        else:
            pad_bytes = RS_K - pad_tmp
        
        payload = self.pack_payload(from_id, to_id, pktno, pad_bytes, pkt_code_str, phy_code, 
                                 mac_code, more_data, data)
        
        # add padding
        payload = ''.join( (payload,'0'*pad_bytes) )
        
        return payload 

    def packet_types_to_ints():
        return dict(other=0, RTS=1, CTS=2, DATA=3, ACK=4, )
    packet_types_to_ints = staticmethod(packet_types_to_ints)
    
