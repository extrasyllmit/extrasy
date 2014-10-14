function diff_timestamps = get_delays(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, pktCode, inittime)
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
%get all transmit packets
[ii timestamps] = filter_log(nodeA_log,'transmit',nodeA_ID,nodeB_ID,pktCode);
ii_tx_data = ii;
nodeA_tx_data_timestamps = timestamps - inittime;


%get all receive packets
[ii timestamps] = filter_log(nodeB_log,'receive',nodeA_ID,nodeB_ID,pktCode);
ii_rx_data = ii;
nodeB_rx_data_timestamps = timestamps - inittime;

diff_timestamps = [];
for k = 1:numel(nodeB_rx_data_timestamps)
	c = nodeB_rx_data_timestamps(k) - nodeA_tx_data_timestamps;
	f = find(c>=0);
	del = min(c(f));
	
	%if del > 1
	%	fprintf('Large delay : pktCode=%i at %.3fs\n\n',pktCode,nodeB_rx_data_timestamps(k));
	%end
	
	diff_timestamps = [diff_timestamps del];
end

