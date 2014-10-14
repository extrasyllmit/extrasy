function perform = plot_tdma_intermediate_performance(node_log, config, PKTCODE, time_params, fignum, save_params)
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
num_nodes = numel(node_log);

sets_evalnodes = config.sets_evalnodes; %{[1 2], [2 1 3], [3 1 4]} %1 is base
num_links = numel(sets_evalnodes);

node_ID = config.node_ID;

inittime = time_params.inittime;
endtime = time_params.endtime;
deltatime = time_params.deltatime;
time_edges = time_params.time_edges;



for n = 1:num_links
	
	figure(fignum+n); clf; hold on;
	
	evalnodes = sets_evalnodes{n};
	A = evalnodes(1);
	B = evalnodes(end);

	if numel(evalnodes) == 2
		nodeA_log = node_log{A};
		nodeB_log = node_log{B};
		
		nodeA_ID = node_ID(A);
		nodeB_ID = node_ID(B);
		
		%from node A to node B
		[nodeA_tx_data_timestamps, ...
		 nodeA_tx_data_unique_timestamps, ...	
			nodeB_rx_data_timestamps, ...
			nodeB_rx_data_goodcrc_timestamps, ...
			nodeB_rx_data_goodcrc_unique_timestamps, ...
			nodeB_rx_data_goodcrc_unique_messagelengths] = get_performance(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE.DATA, inittime);
				
		perform(n).nodeA_tx_data_unique_timestamps = nodeA_tx_data_unique_timestamps;
		perform(n).nodeB_rx_data_goodcrc_unique_timestamps = nodeB_rx_data_goodcrc_unique_timestamps;
		perform(n).nodeB_rx_data_goodcrc_unique_messagelengths = nodeB_rx_data_goodcrc_unique_messagelengths;
		
		subplot(2,1,1); hold on;
		plot_simple_packet_count(nodeA_tx_data_timestamps, deltatime, time_edges, 'b');
		plot_simple_packet_count(nodeB_rx_data_goodcrc_unique_timestamps, deltatime, time_edges, 'r-.');
		title(sprintf('Packet count from Node %i to Node %i',A,B));
		legend(sprintf('Tx@%i',A),sprintf('Rx@%i',B));
		
		%Reverse from node B to A
		[nodeB_tx_data_timestamps, ...
		 nodeB_tx_data_unique_timestamps, ...
			nodeA_rx_data_timestamps, ...
			nodeA_rx_data_goodcrc_timestamps, ...
			nodeA_rx_data_goodcrc_unique_timestamps, ...
			nodeA_rx_data_goodcrc_unique_messagelengths] = get_performance(nodeB_log, nodeA_log, nodeB_ID, nodeA_ID, PKTCODE.DATA, inittime);
		
		perform(n).nodeB_tx_data_unique_timestamps = nodeB_tx_data_unique_timestamps;
		perform(n).nodeA_rx_data_goodcrc_unique_timestamps = nodeA_rx_data_goodcrc_unique_timestamps;
		perform(n).nodeA_rx_data_goodcrc_unique_messagelengths = nodeA_rx_data_goodcrc_unique_messagelengths;
		
		subplot(2,1,2); hold on;
		plot_simple_packet_count(nodeB_tx_data_timestamps, deltatime, time_edges, 'b');
		plot_simple_packet_count(nodeA_rx_data_goodcrc_unique_timestamps, deltatime, time_edges, 'r-.');
		title(sprintf('Packet count from Node %i to Node %i',B,A));
		legend(sprintf('Tx@%i',B),sprintf('Rx@%i',A));
		
		
		evalTimeRangeUpdated = save_params.evalTimeRangeUpdated;
		result_path = config.result_path;
		filename = sprintf('packetcount_node%iand%i',A,B);
		qlfiletype = 'png';
		SAVERESULTS = save_params.SAVERESULTS;
		
		save_fig_with_quicklook(fignum+n,evalTimeRangeUpdated,result_path,filename,qlfiletype,SAVERESULTS);				
	
	
	elseif numel(evalnodes) == 3
		 %mobile to mobile via base
		
		nodeA_log = node_log{A};
		nodeB_log = node_log{B};
		
		nodeA_ID = node_ID(A);
		nodeB_ID = node_ID(B);
		
		Base = evalnodes(2);
		nodeBase_log = node_log{Base};
		nodeBase_ID = node_ID(Base);

		%Going from node A to Base
		[nodeA_tx_data_timestamps, ...
		 nodeA_tx_data_unique_timestamps, ...
			nodeBase_rx_data_timestamps, ...
			nodeBase_rx_data_goodcrc_timestamps, ...
			nodeBase_rx_data_goodcrc_unique_timestamps, ...
			nodeBase_rx_data_goodcrc_unique_messagelengths] = get_performance_destination(nodeA_log, nodeBase_log, nodeA_ID, nodeBase_ID, nodeB_ID, PKTCODE.DATA, inittime);
		
		%Continue from Base to node B
		[nodeBase_tx_data_timestamps, ...
		 nodeBase_tx_data_unique_timestamps, ...
			nodeB_rx_data_timestamps, ...
			nodeB_rx_data_goodcrc_timestamps, ...
			nodeB_rx_data_goodcrc_unique_timestamps, ...
			nodeB_rx_data_goodcrc_unique_messagelengths] = get_performance_source(nodeBase_log, nodeB_log, nodeBase_ID, nodeB_ID, nodeA_ID, PKTCODE.DATA, inittime);
		
		perform(n).nodeA_tx_data_unique_timestamps = nodeA_tx_data_unique_timestamps;
		perform(n).nodeB_rx_data_goodcrc_unique_timestamps = nodeB_rx_data_goodcrc_unique_timestamps;
		perform(n).nodeB_rx_data_goodcrc_unique_messagelengths = nodeB_rx_data_goodcrc_unique_messagelengths;
		
		subplot(2,1,1); hold on;
		plot_simple_packet_count(nodeA_tx_data_timestamps, deltatime, time_edges, 'b', 4);
		plot_simple_packet_count(nodeBase_rx_data_goodcrc_unique_timestamps, deltatime, time_edges, 'g-.', 4);
		plot_simple_packet_count(nodeBase_tx_data_timestamps, deltatime, time_edges, 'k', 2);
		plot_simple_packet_count(nodeB_rx_data_goodcrc_unique_timestamps, deltatime, time_edges, 'r-.', 2);
		title(sprintf('Packet count from Node %i to Base to Node %i',A,B));
		legend(sprintf('Tx@%i',A),sprintf('Rx@%i',Base),sprintf('Tx@%i',Base),sprintf('Rx@%i',B));
		
		%Reverse from node B to Base
		[nodeB_tx_data_timestamps, ...
		 nodeB_tx_data_unique_timestamps, ...
			nodeBase_rx_data_timestamps, ...
			nodeBase_rx_data_goodcrc_timestamps, ...
			nodeBase_rx_data_goodcrc_unique_timestamps, ...
			nodeBase_rx_data_goodcrc_unique_messagelengths] = get_performance_destination(nodeB_log, nodeBase_log, nodeB_ID, nodeBase_ID, nodeA_ID, PKTCODE.DATA, inittime);
		
		%Continue from Base to node A
		[nodeBase_tx_data_timestamps, ...
		 nodeBase_tx_data_unique_timestamps, ...
			nodeA_rx_data_timestamps, ...
			nodeA_rx_data_goodcrc_timestamps, ...
			nodeA_rx_data_goodcrc_unique_timestamps, ...
			nodeA_rx_data_goodcrc_unique_messagelengths] = get_performance_source(nodeBase_log, nodeA_log, nodeBase_ID, nodeA_ID, nodeB_ID, PKTCODE.DATA, inittime);
		
		perform(n).nodeB_tx_data_unique_timestamps = nodeB_tx_data_unique_timestamps;
		perform(n).nodeA_rx_data_goodcrc_unique_timestamps = nodeA_rx_data_goodcrc_unique_timestamps;
		perform(n).nodeA_rx_data_goodcrc_unique_messagelengths = nodeA_rx_data_goodcrc_unique_messagelengths;
		
		subplot(2,1,2); hold on;
		plot_simple_packet_count(nodeB_tx_data_timestamps, deltatime, time_edges, 'b', 4);
		plot_simple_packet_count(nodeBase_rx_data_goodcrc_unique_timestamps, deltatime, time_edges, 'g-.', 4);
		plot_simple_packet_count(nodeBase_tx_data_timestamps, deltatime, time_edges, 'k', 2);
		plot_simple_packet_count(nodeA_rx_data_goodcrc_unique_timestamps, deltatime, time_edges, 'r-.', 2);
		title(sprintf('Packet count from Node %i to Base to Node %i',B,A));
		legend(sprintf('Tx@%i',B),sprintf('Rx@%i',Base),sprintf('Tx@%i',Base),sprintf('Rx@%i',A));
		
		
		evalTimeRangeUpdated = save_params.evalTimeRangeUpdated;
		result_path = config.result_path;
		filename = sprintf('packetcount_node%iand%i',A,B);
		qlfiletype = 'png';
		SAVERESULTS = save_params.SAVERESULTS;
		
		save_fig_with_quicklook(fignum+n,evalTimeRangeUpdated,result_path,filename,qlfiletype,SAVERESULTS);	
	else
		error('Incorrect number of eval nodes in sets_evalnodes');
	end
end
