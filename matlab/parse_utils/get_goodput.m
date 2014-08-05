function nodeB_rx_data_goodcrc_unique_bitpersec = get_goodput(nodeB_rx_data_goodcrc_unique_timestamps, ...
	nodeB_rx_data_goodcrc_unique_messagelengths, deltatime, time_edges)
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
if isempty(nodeB_rx_data_goodcrc_unique_timestamps)
	n_nodeB_rx_data_goodcrc_unique = zeros(size(time_edges));
    bin_num = [];
else
	[n_nodeB_rx_data_goodcrc_unique, bin_num] = histc(nodeB_rx_data_goodcrc_unique_timestamps,time_edges);
end

temp = zeros(size(time_edges));

for k = 1:numel(bin_num)
	n = bin_num(k);
	temp(n) = temp(n) + nodeB_rx_data_goodcrc_unique_messagelengths(k);	
end
nodeB_rx_data_goodcrc_unique_goodput = temp;
nodeB_rx_data_goodcrc_unique_bitpersec = nodeB_rx_data_goodcrc_unique_goodput * 8 / deltatime;






