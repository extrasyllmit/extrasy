function [nodeA_tx_data_timestamps, ...
	      nodeA_tx_data_unique_timestamps, ...
    nodeB_rx_data_timestamps, ...
	nodeB_rx_data_goodcrc_timestamps, ...
	nodeB_rx_data_goodcrc_unique_timestamps, ...
	nodeB_rx_data_goodcrc_unique_messagelengths] = get_performance(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, pktCode, inittime)
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
[ii_valid timestamps] = filter_log(nodeA_log,'transmit',nodeA_ID,nodeB_ID,pktCode);
nodeA_tx_data_timestamps = timestamps - inittime;

%refine to get just those with unique packet id
[ii, allcells] = xml_arraygetfields(nodeA_log(ii_valid),{'packetid'});
if ~isempty(allcells)
	allnums = cellfun(@str2double,allcells,'UniformOutput',true);
	[unique_pktID,uniq_ii,~] = unique(unwrap_packet_id(allnums));
	ii_tx_data_unique = ii_valid(ii(uniq_ii));
	nodeA_tx_data_unique_timestamps = nodeA_tx_data_timestamps(ii(uniq_ii));
else
	nodeA_tx_data_unique_timestamps = [];
end

%get all receive packets
[ii timestamps] = filter_log(nodeB_log,'receive',nodeA_ID,nodeB_ID,pktCode);
ii_rx_data_goodcrc = ii;
nodeB_rx_data_goodcrc_timestamps = timestamps - inittime;

%do this so that this function is backward compatible
nodeB_rx_data_timestamps = nodeB_rx_data_goodcrc_timestamps;

%refine to get just those with unique packet id
[ii, allcells] = xml_arraygetfields(nodeB_log(ii_rx_data_goodcrc),{'packetid'});
if isempty(ii)
	nodeB_rx_data_goodcrc_unique_timestamps = [];
    nodeB_rx_data_goodcrc_unique_messagelengths = [];
	return
end
allnums = cellfun(@str2double,allcells,'UniformOutput',true);
[unique_pktID,uniq_ii,~] = unique(unwrap_packet_id(allnums));
ii_rx_data_goodcrc_unique = ii_rx_data_goodcrc(ii(uniq_ii));
nodeB_rx_data_goodcrc_unique_timestamps = nodeB_rx_data_goodcrc_timestamps(ii(uniq_ii));

nodeB_rx_data_goodcrc_unique_messagelengths = zeros(1,numel(nodeB_rx_data_goodcrc_unique_timestamps));
[ii, allcells] = xml_arraygetfields(nodeB_log(ii_rx_data_goodcrc_unique),{'messagelength'});
allnums = cellfun(@str2double,allcells,'UniformOutput',true);
nodeB_rx_data_goodcrc_unique_messagelengths(ii) = allnums;

