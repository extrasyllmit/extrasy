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
error('Please use the example process_many_test.m script.  this script is no longer supported.');

addpath('./xml_toolbox');

NEWXML = 0;
SAVERESULTS = 1;

logs_path = '/home/g103homes/a/tri/generalized-sdr-comms/Testing/Test4/20121025T151647/';
%logs_path = '/home/g103homes/a/tri/generalized-sdr-comms/Testing/Test4/20121025T132749/';

%logs_path = '/home/g103homes/a/tri/generalized-sdr-comms/Testing/Test1/20121025T120248/';
%logs_path = '/home/g103homes/a/tri/generalized-sdr-comms/Testing/Test1/20121024T120139/';
%logs_path = '/home/g103homes/a/tri/generalized-sdr-comms/Testing/Test1/20121024T190243/';

node_xml{1} = 'node1phy.xml';
node_xml{2} = 'node2phy.xml';
node_xml{3} = 'node3phy.xml';

node_ID = [16 32 64];

%specify 1,2 or 1,3 or 2,3
pairIDs = [2 3];

num_nodes = numel(node_xml);

if NEWXML

	for n = 1:num_nodes
		node_log{n} = xml_readandparse(fullfile(logs_path, node_xml{n}),'packet',Inf,10*60);
	end
	
	save(fullfile(logs_path, 'node_log.mat'),'node_log','node_ID');
	
elseif exist(fullfile(logs_path, 'node_log.mat'),'file')
	load(fullfile(logs_path, 'node_log.mat'));
else
	fprintf('node_log.mat does not exist.  Try running with NEWXML=1 for the first time.\n');
	break
end

%% don't change definitions below, change pairIDs if switching pair of nodes
nodeA_log = node_log{pairIDs(1)};
nodeB_log = node_log{pairIDs(2)};

nodeA_ID = node_ID(pairIDs(1));
nodeB_ID = node_ID(pairIDs(2));

%define packet code
PKTCODE.RTS = 1;
PKTCODE.CTS = 2;
PKTCODE.DATA = 3;
PKTCODE.ACK = 4;

%% debugging
disp('Size of node A');
disp(size(nodeA_log));
disp('Size of node B');
disp(size(nodeB_log));

ii_valid_A_tx = refine_log(nodeA_log,'direction','transmit');
ii_valid_A_rx = refine_log(nodeA_log,'direction','receive');

ii_valid_B_tx = refine_log(nodeB_log,'direction','transmit');
ii_valid_B_rx = refine_log(nodeB_log,'direction','receive');

disp('Node A transmits');
disp('     from IDs : ');
disp(unique(cellfun(@str2double,{nodeA_log(ii_valid_A_tx).fromID})));
disp('     to IDs : ');
disp(unique(cellfun(@str2double,{nodeA_log(ii_valid_A_tx).toID})));

disp('Node A receives');
disp('     from IDs : ');
disp(unique(cellfun(@str2double,{nodeA_log(ii_valid_A_rx).fromID})));
disp('     to IDs : ');
disp(unique(cellfun(@str2double,{nodeA_log(ii_valid_A_rx).toID})));


disp('Node B transmits');
disp('     from IDs : ');
disp(unique(cellfun(@str2double,{nodeB_log(ii_valid_B_tx).fromID})));
disp('     to IDs : ');
disp(unique(cellfun(@str2double,{nodeB_log(ii_valid_B_tx).toID})));

disp('Node B receives');
disp('     from IDs : ');
disp(unique(cellfun(@str2double,{nodeB_log(ii_valid_B_rx).fromID})));
disp('     to IDs : ');
disp(unique(cellfun(@str2double,{nodeB_log(ii_valid_B_rx).toID})));


%%
inittime = min(str2double(nodeA_log(1).timestamp),str2double(nodeB_log(1).timestamp));
endtime = max(str2double(nodeA_log(end).timestamp),str2double(nodeB_log(end).timestamp));

deltatime = 5; %0.25; %seconds
time_edges = (0:deltatime:endtime-inittime+deltatime);

fignum = 20;
figure(fignum); clf;
subplot(3,1,1);
plot_raw_traffic(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE, inittime)

% useful only in debugging; data different for A->B vs B->A
% y0 = 0;
% plot(nodeA_tx_data_timestamps,y0,'ro','MarkerSize',6,'LineWidth',2);
% y0 = 3;
% plot(nodeB_rx_data_timestamps,y0,'bo','MarkerSize',6,'LineWidth',2);
% y0 = 3;
% plot(nodeB_rx_data_goodcrc_timestamps,y0,'c*','MarkerSize',5,'LineWidth',2);
% y0 = 3;
% plot(nodeB_rx_data_goodcrc_unique_timestamps,y0,'m+','MarkerSize',4,'LineWidth',2);

nodeLabel = 'A->B';

for rep = 1:2
	
	%swith A,B
	if rep==2
		bitpersec_AB = bitpersec;
		
		nodeA_log_temp = nodeA_log;
		nodeA_ID_temp  = nodeA_ID;
		
		nodeA_log = nodeB_log;
		nodeA_ID  = nodeB_ID;
		
		nodeB_log = nodeA_log_temp;
		nodeB_ID  = nodeA_ID_temp;
		
		nodeLabel = 'B->A';
	end
		
		
	%% extract performance results for A->B
	[nodeA_tx_data_timestamps, ...
		nodeB_rx_data_timestamps, ...
		nodeB_rx_data_goodcrc_timestamps, ...
		nodeB_rx_data_goodcrc_unique_timestamps, ...
		nodeB_rx_data_goodcrc_unique_messagelengths] = get_performance(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE, inittime);
	
	if rep==1
		y0 = 3;
		colormarker = 'cv';
	else
		y0 = 1;
		colormarker = 'c^';
	end
	if ~isempty(nodeB_rx_data_goodcrc_timestamps)
		figure(fignum);
		subplot(3,1,1);
		plot(nodeB_rx_data_goodcrc_timestamps,y0, colormarker,'MarkerSize',4,'LineWidth',3);
	end
	if ~isempty(nodeB_rx_data_goodcrc_unique_timestamps)
		figure(fignum);
		subplot(3,1,1);
		plot(nodeB_rx_data_goodcrc_unique_timestamps,y0, 'm.','MarkerSize',10,'LineWidth',4);
	end	
	
	%% plot packet count for A->B
	figure(fignum);
	subplot(3,1,1+rep);
	hold on;

	plot_packet_count(nodeA_tx_data_timestamps, ...
		nodeB_rx_data_timestamps, ...
		nodeB_rx_data_goodcrc_timestamps, ...
		nodeB_rx_data_goodcrc_unique_timestamps, deltatime, time_edges);
	
	if rep==1
		title(sprintf('A->B, Interval = %.4f s',deltatime));
	else
		title(sprintf('B->A, Interval = %.4f s',deltatime));
	end
	
	%% get and plot goodput for A->B
	figure(fignum+1);

	if rep==1
		symbol = 'g-';
		clf;
	else
		symbol = 'c-.';
		hold on;
	end

	bitpersec = plot_goodput(nodeB_rx_data_goodcrc_unique_timestamps, ...
		nodeB_rx_data_goodcrc_unique_messagelengths, deltatime, time_edges, symbol);
	
	%% get delays
	figure(fignum+1+rep);
	[diff_timestamps self_diff_timestamps pkt_diff_timestamps pkt_count] = ...
		get_all_delays(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE, inittime);
	fn = fieldnames(PKTCODE);
	for k = 1:4
		subplot(4,2,k);
		hist(diff_timestamps{k},100);
		title(sprintf('%s, %s',nodeLabel,fn{k}'))
		xlabel('Time (s)');
	end
	for k = 1:4
		subplot(4,2,k+4);
		hist(self_diff_timestamps{k},100);
		title(sprintf('%s, %s, self-receive',nodeLabel,fn{k}'))
		xlabel('Time (s)');
	end
	
	%% plot delays between RTS and CTS, DATA and ACK
	figure(fignum+1+3);
	subplot(2,2,(rep-1)*2+1);
	hist(pkt_diff_timestamps{1},100);
	title(sprintf('%s, %s(%i)->%s(%i), %0.1f%%',nodeLabel, fn{1}, pkt_count(1).tx, fn{2}', pkt_count(1).rx, (pkt_count(1).rx/pkt_count(1).tx*100)))
	xlabel('Time (s)');
	subplot(2,2,(rep-1)*2+2);
	hist(pkt_diff_timestamps{2},100);
	title(sprintf('%s, %s(%i)->%s(%i), %0.1f%%',nodeLabel, fn{3}, pkt_count(2).tx, fn{4}', pkt_count(2).rx, (pkt_count(2).rx/pkt_count(2).tx*100)))
	xlabel('Time (s)');
	
	
	%keyboard
end

%switch back A,B
bitpersec_BA = bitpersec;

nodeA_log_temp = nodeA_log;
nodeA_ID_temp  = nodeA_ID;

nodeA_log = nodeB_log;
nodeA_ID  = nodeB_ID;

nodeB_log = nodeA_log_temp;
nodeB_ID  = nodeA_ID_temp;

nodeLabel = 'A->B';

%% continue plotting goodput for A->B
figure(fignum+1);
bitpersec_total = bitpersec_AB + bitpersec_BA;
temp = [time_edges(1:end-1); time_edges(2:end)];
time_edges_rep = temp(:).';
temp = repmat(bitpersec_total(1:end-1),2,1);
nn_total_bitpersec = temp(:).';
plot(time_edges_rep,nn_total_bitpersec/1e3, 'r-','LineWidth',2)
legend('A->B','B->A','Combined');
title(sprintf('Goodput (mean=%.1f Kbits/s)',mean(bitpersec_total)/1e3))
grid on

%% save results
if SAVERESULTS
	pairStrg = sprintf('node%iand%i_',pairIDs(1:2));
	
	save(fullfile(logs_path, [pairStrg 'perform_results.mat']));
		
	saveas(fignum,   fullfile(logs_path, [pairStrg 'traffic.fig']), 'fig');
	saveas(fignum+1, fullfile(logs_path, [pairStrg 'goodput.fig']), 'fig');
	saveas(fignum+2, fullfile(logs_path, [pairStrg 'delay_AB.fig']), 'fig');
	saveas(fignum+3, fullfile(logs_path, [pairStrg 'delay_BA.fig']), 'fig');
	saveas(fignum+4, fullfile(logs_path, [pairStrg 'delay_roundtrip.fig']), 'fig');
	
	saveas(fignum,   fullfile(logs_path, [pairStrg 'traffic.png']), 'png');
	saveas(fignum+1, fullfile(logs_path, [pairStrg 'goodput.png']), 'png');
	saveas(fignum+2, fullfile(logs_path, [pairStrg 'delay_AB.png']), 'png');
	saveas(fignum+3, fullfile(logs_path, [pairStrg 'delay_BA.png']), 'png');
	saveas(fignum+4, fullfile(logs_path, [pairStrg 'delay_roundtrip.png']), 'png');
end


