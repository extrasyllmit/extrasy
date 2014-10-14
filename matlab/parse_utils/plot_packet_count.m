function plot_packet_count(nodeA_tx_data_timestamps, ...
	nodeB_rx_data_timestamps, ...
	nodeB_rx_data_goodcrc_timestamps, ...
	nodeB_rx_data_goodcrc_unique_timestamps, deltatime, time_edges)
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
if isempty(nodeA_tx_data_timestamps)
	n_nodeA_tx_data = zeros(size(time_edges));
else
	n_nodeA_tx_data = histc(nodeA_tx_data_timestamps,time_edges);
end

if isempty(nodeB_rx_data_timestamps)
	n_nodeB_rx_data = zeros(size(time_edges));
else
	n_nodeB_rx_data = histc(nodeB_rx_data_timestamps,time_edges);
end

if isempty(nodeB_rx_data_goodcrc_timestamps)
	n_nodeB_rx_data_goodcrc = zeros(size(time_edges));
else
	n_nodeB_rx_data_goodcrc = histc(nodeB_rx_data_goodcrc_timestamps,time_edges);
end

if isempty(nodeB_rx_data_goodcrc_unique_timestamps)
	n_nodeB_rx_data_goodcrc_unique = zeros(size(time_edges));
else
	n_nodeB_rx_data_goodcrc_unique = histc(nodeB_rx_data_goodcrc_unique_timestamps,time_edges);

end

temp = [time_edges(1:end-1); time_edges(2:end)];
time_edges_rep = temp(:).';

temp = repmat(n_nodeA_tx_data(1:end-1),2,1);
nn_nodeA_tx_data = temp(:).';

temp = repmat(n_nodeB_rx_data(1:end-1),2,1);
nn_nodeB_rx_data = temp(:).';

temp = repmat(n_nodeB_rx_data_goodcrc(1:end-1),2,1);
nn_nodeB_rx_data_goodcrc = temp(:).';

temp = repmat(n_nodeB_rx_data_goodcrc_unique(1:end-1),2,1);
nn_nodeB_rx_data_goodcrc_unique = temp(:).';

plot(time_edges_rep,nn_nodeA_tx_data,'r','LineWidth',2)
plot(time_edges_rep,nn_nodeB_rx_data,'b','LineWidth',2)
%plot(time_edges_rep,nn_nodeB_rx_data_goodcrc,'c','LineWidth',2)
plot(time_edges_rep,nn_nodeB_rx_data_goodcrc_unique,'m-.','LineWidth',2)

box on
set(gca,'ylim',[0 max(max(nn_nodeA_tx_data),max(nn_nodeB_rx_data))+1])
xlabel('Time (s)');
ylabel('Packet Count');
title(sprintf('Interval = %.4f s',deltatime));
%legend('Tx Data Packet','Rx Data Packet','Rx Good CRC','Rx Unique Packet IDs')
legend('Tx Data Packet','Rx Data Packet','Rx Good Data Packet')


