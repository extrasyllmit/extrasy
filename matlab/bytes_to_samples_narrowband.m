function num_samples = bytes_to_samples_narrowband( payload_len, ... 
                                                    crc_len, ...
                                                    preamble_len, ...
                                                    access_code_len, ...
                                                    header_len, ...
                                                    use_fec, ...
                                                    rs_n, ...
                                                    rs_k, ...
                                                    mod_order, ...
                                                    samps_per_sym, ...
                                                    pad_for_usrp)
%%
% This file is part of ExtRaSy
%
% Copyright (C) 2013-2014 Massachusetts Institute of Technology
%
% This program is free software: you can redistribute it and/or modify
% it under the terms of the GNU General Public License as published by
% the Free Software Foundation, either version 2 of the License, or
% (at your option) any later version.
%
% This program is distributed in the hope that it will be useful,
% but WITHOUT ANY WARRANTY; without even the implied warranty of
% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
% GNU General Public License for more details.
%
% You should have received a copy of the GNU General Public License
% along with this program.  If not, see <http://www.gnu.org/licenses/>.
%%

%bytes_to_samples_narrowband For a given mac layer packet length, return the number of complex samples
%   
% payload_len is length of a mac layer packet in bytes
% crc_len is the length of the crc code in bytes. Typically 4 
% preamble_len is the length of the preamble in bytes. Typically 38
% access_code_len is the length of the access code in bytes. Typically 8
% header_len is the length of the physical layer header in bytes. Typically 2
% use_fec should be true if using forward error correction, false otherwise
% rs_n and rs_k are parameters for reed-solomon encoding. rs_n is 8, rs_k is 4
% mod_order is the modulation order, ie bpsk is 2, qpsk is 4, etc 
% samps per sym is the number of complex samples per symbol. Configurable 
% 

%TODO: Verify through code test

  if use_fec == true
    fec_factor = (rs_n/rs_k);
  else
    fec_factor = 1;
  end
  
  rs_padding = mod(payload_len + crc_len, rs_k);
  
  if rs_padding ~= 0
    rs_padding = rs_k - rs_padding;
  end
  
  pkt_byte_len = (payload_len + +rs_padding + crc_len )*fec_factor + preamble_len*2 + access_code_len + ... 
    header_len*2;
  
  bits_per_sym = log2(mod_order);
  
  % padding for USRP expects 512 byte blocks. Each sample is 4 bytes (16 bit I and 16 bit Q)
  USRP_bytes_per_block = 512; % bytes
  USRP_bytes_per_sample = 4; % bytes per complex sample
  
  USRP_samples_per_block = USRP_bytes_per_block/USRP_bytes_per_sample;
  
  byte_modulus = lcm(USRP_samples_per_block/8, samps_per_sym) * bits_per_sym / samps_per_sym;
  
  r = mod(pkt_byte_len, byte_modulus);
  
  if r == 0
    nbytes_to_pad = 0;
  else
    nbytes_to_pad = byte_modulus - r;
  end
  
  padded_pkt_len = pkt_byte_len + nbytes_to_pad;
  
  num_samples = padded_pkt_len * 8 / bits_per_sym * samps_per_sym;


end

