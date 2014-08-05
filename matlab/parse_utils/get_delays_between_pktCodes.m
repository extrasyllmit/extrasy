function [diff_timestamps count delayinfo] = get_delays_between_pktCodes(nodeA_log, nodeA_ID, nodeB_ID, pktCode, inittime)
%%
% This file is part of ExtRaSy
%
% Copyright (C) 2013-2014 Massachusetts Institute of Technology
%
% This program is free software: you can redistribute it and/or modify
% it under the terms of the GNU General Public License as published by
% the Free Software Foundation, either version 3 of the License, or
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
%get all transmit packets
[ii timestamps] = filter_log(nodeA_log,'transmit',nodeA_ID,nodeB_ID,pktCode(1));
ii_tx_data = ii;
nodeA_tx_data_timestamps = timestamps - inittime;

%get transmit packet id's
[ii, nodeA_tx_data_packetid] = get_any_id(nodeA_log(ii_tx_data),'packetid');
nodeA_tx_data_timestamps = nodeA_tx_data_timestamps(ii); %in case of missing packetid's
ii_tx_data = ii_tx_data(ii);
nodeA_tx_data_packetid = unwrap_packet_id(nodeA_tx_data_packetid);

count.tx       = numel(nodeA_tx_data_packetid);
count.txunique = numel(unique(nodeA_tx_data_packetid));

%get all receive packets
[ii_rx_data timestamps] = filter_log(nodeA_log,'receive',nodeB_ID,nodeA_ID,pktCode(2));
nodeA_rx_data_timestamps = timestamps - inittime;
count.rx = numel(nodeA_rx_data_timestamps);

%filter out those don't pass crc
ii = refine_log(nodeA_log(ii_rx_data),'crcpass','True');
ii_rx_data_goodcrc = ii_rx_data(ii);
nodeA_rx_data_goodcrc_timestamps = nodeA_rx_data_timestamps(ii);

%get receive packet id's
[ii, nodeA_rx_data_goodcrc_packetid] = get_any_id(nodeA_log(ii_rx_data_goodcrc),'packetid');
nodeA_rx_data_goodcrc_timestamps = nodeA_rx_data_goodcrc_timestamps(ii); %in case of missing packetid's
ii_rx_data_goodcrc = ii_rx_data_goodcrc(ii); %in case of missing packetid's
nodeA_rx_data_goodcrc_packetid = unwrap_packet_id(nodeA_rx_data_goodcrc_packetid);

count.rx       = numel(nodeA_rx_data_goodcrc_packetid);
count.rxunique = numel(unique(nodeA_rx_data_goodcrc_packetid));


diff_timestamps = [];
for k = 1:numel(nodeA_rx_data_goodcrc_timestamps)
	
	rx_timestamp = nodeA_rx_data_goodcrc_timestamps(k);
	rx_packetid = nodeA_rx_data_goodcrc_packetid(k);
	
	ii = (nodeA_tx_data_packetid == rx_packetid);
	tx_timestamps = nodeA_tx_data_timestamps(ii);
	
	if ~isempty(tx_timestamps)
		delays = rx_timestamp - tx_timestamps;
		del = min(delays); %use max if measuring from 1st tx packet
		
		if del>0.1
			fprintf('Large delay of %.3f from ID=%i to ID=%i at time %.3f.\n',del,nodeA_ID,nodeB_ID,rx_timestamp);
			%keyboard
		elseif del<0
			fprintf('Negative delay of %.3f from ID=%i to ID=%i at time %.3f.\n',del,nodeA_ID,nodeB_ID,rx_timestamp);
		end
		
		if del>0
			diff_timestamps = [diff_timestamps del];
		end
	end	
end

delayinfo.tx_timestamps = nodeA_tx_data_timestamps;
delayinfo.tx_packetids  = nodeA_tx_data_packetid;
delayinfo.rx_timestamps = nodeA_rx_data_goodcrc_timestamps;
delayinfo.rx_packetids  = nodeA_rx_data_goodcrc_packetid;
