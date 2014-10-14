function [bitpersec_AB, bitpersec_BA] = evaluate_pair_of_nodes(node_log, node_ID, pairIDs, SAVERESULTS, result_path, fignum, evalTimeRange)
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

% disp('Node A transmits');
% disp('     from IDs : ');
% disp(unique(cellfun(@str2double,{nodeA_log(ii_valid_A_tx).fromID})));
% disp('     to IDs : ');
% disp(unique(cellfun(@str2double,{nodeA_log(ii_valid_A_tx).toID})));
% 
% disp('Node A receives');
% disp('     from IDs : ');
% disp(unique(cellfun(@str2double,{nodeA_log(ii_valid_A_rx).fromID})));
% disp('     to IDs : ');
% disp(unique(cellfun(@str2double,{nodeA_log(ii_valid_A_rx).toID})));
% 
% 
% disp('Node B transmits');
% disp('     from IDs : ');
% disp(unique(cellfun(@str2double,{nodeB_log(ii_valid_B_tx).fromID})));
% disp('     to IDs : ');
% disp(unique(cellfun(@str2double,{nodeB_log(ii_valid_B_tx).toID})));
% 
% disp('Node B receives');
% disp('     from IDs : ');
% disp(unique(cellfun(@str2double,{nodeB_log(ii_valid_B_rx).fromID})));
% disp('     to IDs : ');
% disp(unique(cellfun(@str2double,{nodeB_log(ii_valid_B_rx).toID})));


%%
time_params = get_time_info(node_log);
inittime = time_params.inittime;
endtime = time_params.endtime;

deltatime = 1; %0.25; %seconds
time_edges = (0:deltatime:time_params.endtime-time_params.inittime+deltatime);

for n = 0:6
	figure(fignum+n); clf;
end

figure(fignum); clf;
subplot(3,1,1);
plot_raw_traffic(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE, inittime)
title(sprintf('Packet traffic for eval time from %is to %is',round(evalTimeRange)));

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
	[nodeA_tx_rts_timestamps, ...
	 nodeA_tx_rts_unique_timestamps, ...	
		nodeB_rx_rts_timestamps, ...
		nodeB_rx_rts_goodcrc_timestamps, ...
		nodeB_rx_rts_goodcrc_unique_timestamps, ...
		nodeB_rx_rts_goodcrc_unique_messagelengths] = get_performance(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE.RTS, inittime);

	[nodeB_tx_cts_timestamps, ...
	 nodeB_tx_cts_unique_timestamps, ...	
		nodeA_rx_cts_timestamps, ...
		nodeA_rx_cts_goodcrc_timestamps, ...
		nodeA_rx_cts_goodcrc_unique_timestamps, ...
		nodeA_rx_cts_goodcrc_unique_messagelengths] = get_performance(nodeB_log, nodeA_log, nodeB_ID, nodeA_ID, PKTCODE.CTS, inittime);
	
	[nodeA_tx_data_timestamps, ...
	 nodeA_tx_data_unique_timestamps, ...	
		nodeB_rx_data_timestamps, ...
		nodeB_rx_data_goodcrc_timestamps, ...
		nodeB_rx_data_goodcrc_unique_timestamps, ...
		nodeB_rx_data_goodcrc_unique_messagelengths] = get_performance(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE.DATA, inittime);
	
	[nodeB_tx_ack_timestamps, ...
	 nodeB_tx_ack_unique_timestamps, ...	
		nodeA_rx_ack_timestamps, ...
		nodeA_rx_ack_goodcrc_timestamps, ...
		nodeA_rx_ack_goodcrc_unique_timestamps, ...
		nodeA_rx_ack_goodcrc_unique_messagelengths] = get_performance(nodeB_log, nodeA_log, nodeB_ID, nodeA_ID, PKTCODE.ACK, inittime);

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

	packetstat(rep).rts  = [numel(nodeA_tx_rts_unique_timestamps)  numel(nodeB_rx_rts_goodcrc_unique_timestamps)];
	packetstat(rep).cts  = [numel(nodeB_tx_cts_unique_timestamps)  numel(nodeA_rx_cts_goodcrc_unique_timestamps)];
	packetstat(rep).data = [numel(nodeA_tx_data_unique_timestamps) numel(nodeB_rx_data_goodcrc_unique_timestamps)];
	packetstat(rep).ack  = [numel(nodeB_tx_ack_unique_timestamps)  numel(nodeA_rx_ack_goodcrc_unique_timestamps)];
	
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
	figure(fignum+1+rep); clf;
	[diff_timestamps self_diff_timestamps pkt_diff_timestamps pkt_count delayinfo] = ...
		get_all_delays(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE, inittime);
	fn = fieldnames(PKTCODE);
	fig2xlim = [0 max([[diff_timestamps{:}]*1e3 1])];
	for k = 1:4
		subplot(4,2,k);
		hist(diff_timestamps{k}*1e3,100);
		title(sprintf('%s, %s',nodeLabel,fn{k}'))
		xlabel('Time (ms)');
		set(gca,'XLim',ceil(fig2xlim));
	end
	for k = 1:4
		subplot(4,2,k+4);
		hist(self_diff_timestamps{k}*1e3,100);
		title(sprintf('%s, %s, self-receive',nodeLabel,fn{k}'))
		xlabel('Time (ms)');
		set(gca,'XLim',ceil(fig2xlim));
	end
	figure(fignum+1+rep);
	figxlim = [0 1];
	figylim = [0 1];
	for m = 1:8
		subplot(4,2,m);
		tmp = get(gca,'XLim');
		figxlim(1) = min(figxlim(1),tmp(1));
		figxlim(2) = max(figxlim(2),tmp(2));
		tmp = get(gca,'YLim');
		figylim(1) = min(figylim(1),max(tmp(1),0));
		figylim(2) = max(figylim(2),tmp(2));
	end
	for m = 1:8
		subplot(4,2,m);
		set(gca,'Xlim',figxlim);
		set(gca,'YLim',figylim);
	end

	%% plot delays between RTS and CTS, DATA and ACK
	figure(fignum+1+3);
	fig4xlim = [0 max(max([pkt_diff_timestamps{1}*1e3 1]),max([pkt_diff_timestamps{2}*1e3 1]))];
	
	subplot(2,2,(rep-1)*2+1);
	hist(pkt_diff_timestamps{1}*1e3,100);
	title(sprintf('%s, %s(%i)->%s(%i), %0.1f%%',nodeLabel, fn{1}, pkt_count(1).tx, fn{2}', pkt_count(1).rx, (pkt_count(1).rx/pkt_count(1).tx*100)))
	xlabel('Time (ms)');
	set(gca,'XLim',ceil(fig4xlim));
	subplot(2,2,(rep-1)*2+2);
	hist(pkt_diff_timestamps{2}*1e3,100);
	title(sprintf('%s, %s(%i)->%s(%i), %0.1f%%',nodeLabel, fn{3}, pkt_count(2).tx, fn{4}', pkt_count(2).rx, (pkt_count(2).rx/pkt_count(2).tx*100)))
	xlabel('Time (ms)');
	set(gca,'XLim',ceil(fig4xlim));
	
	
	%% stemp plot packet count over time
	figure(fignum+5);
	subplot(2,1,rep);
	stemcolor = {'k','g','b','r'};
	hold on
	mxcount = 1;
	numelcount = zeros(2,2);
	lgtxt = {'RTS (tx)','CTS (rx)','DATA (tx)','ACK (rx)'};
	
	for k = 1:2 %k=1 is RTS->CTS, k=2 is DATA->ACK
		
		for m = 1:2
			if m == 1
				timestamps = delayinfo(k).tx_timestamps; %nodeA_tx_data_timestamps;
				packetids =  delayinfo(k).tx_packetids;  %nodeA_tx_data_packetid;
			else
				timestamps = delayinfo(k).rx_timestamps; %nodeA_rx_data_goodcrc_timestamps;
				packetids =  delayinfo(k).rx_packetids;  %nodeA_rx_data_goodcrc_packetid;
			end

			maxid = max(packetids);
			count = zeros(1,maxid+1);
			meantime = zeros(1,maxid+1);
			for n = 1:maxid+1
				ii = (packetids==(n-1));
				count(n) = sum(ii); %will be 0 for non-existing ID
				meantime(n) = mean(timestamps(ii));  %will be NaN for non-existing ID
			end

			numelcount(m,k) = numel(count);
			if numel(count)>0
				stem(meantime, count, stemcolor{(k-1)*2+m});
				mxcount = max(mxcount,max(count));
			end
			
			ii = ~isnan(meantime);
			repeatedPacketCount{k,m} = count(ii);
		end
	end
	title(sprintf('Packet count for each unique packet ID (%s) @%s',nodeLabel,nodeLabel(1)));
	xlabel('Time (s)');
	ylabel('Packet Count');
	box on
	set(gca,'ylim',[0 mxcount+1]);
	tmp = numelcount(:);
	legend(lgtxt(tmp>0));
	
	%keyboard
	
	%% plot histogram of unique packet ID count
	figure(fignum+6);
	subplot(2,2,(rep-1)*2+1);
	hold on;
	Nhist = histc(repeatedPacketCount{1,1},(1:mxcount));
	Nsessions1 = sum(Nhist);
	Npackets1 = sum(Nhist.*(1:mxcount));
	if Npackets1>0
		r1 = Nsessions1/Npackets1;
	else
		r1 = 0;
	end
	bar((1:mxcount) - 0.2, Nhist, 0.3, 'k')

	Nhist = histc(repeatedPacketCount{1,2},(1:mxcount));
	Nsessions2 = sum(Nhist);
	Npackets2 = sum(Nhist.*(1:mxcount));
	if Npackets2 > 0
		r2 = Nsessions2/Npackets2;
	else
		r2 = 0;
	end
	bar((1:mxcount) + 0.2, Nhist, 0.3, 'g')
	
	r3 = Nsessions2/Nsessions1;
	
	set(gca,'XTick',(1:mxcount))
	xlabel('Number of repeated packets');
	ylabel('Number of sessions');
	title(sprintf('%s, RTS(%.1f%%), CTS(%.1f%%), CTS/RTS(%.1f%%)',nodeLabel,r1*100,r2*100,r3*100));
	box on
	
	subplot(2,2,(rep-1)*2+2);
	hold on;
	Nhist = histc(repeatedPacketCount{2,1},(1:mxcount));
	Nsessions1 = sum(Nhist);
	Npackets1 = sum(Nhist.*(1:mxcount));
	if Npackets1>0
		r1 = Nsessions1/Npackets1;
	else
		r1 = 0;
	end
	%numel(Nhist) is at least 1
	bar((1:numel(Nhist)) - 0.2, Nhist, 0.3, 'b')

	Nhist = histc(repeatedPacketCount{2,2},(1:mxcount));
	Nsessions2 = sum(Nhist);
	Npackets2 = sum(Nhist.*(1:mxcount));
	if Npackets2 > 0
		r2 = Nsessions2/Npackets2;
	else
		r2 = 0;
	end
	%numel(Nhist) is at least 1
	bar((1:numel(Nhist)) + 0.2, Nhist, 0.3, 'r')
	
	r3 = Nsessions2/Nsessions1;

	set(gca,'XTick',(1:mxcount))
	xlabel('Number of repeated packets');
	ylabel('Number of sessions');
	title(sprintf('%s, DATA(%.1f%%), ACK(%.1f%%), ACK/DATA(%.1f%%)',nodeLabel,r1*100,r2*100,r3*100));
	box on

	
	
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

figure(fignum);
subplot(3,1,1);
figxlim = get(gca,'XLim');

figure(fignum);
subplot(3,1,2);
figylim1 = get(gca, 'YLim');
subplot(3,1,3);
figylim2 = get(gca, 'YLim');

figure(fignum);
subplot(3,1,2);
set(gca, 'XLim', figxlim);
set(gca, 'YLim', [0 max(figylim1(2),figylim2(2))]);
subplot(3,1,3);
set(gca, 'XLim', figxlim);
set(gca, 'YLim', [0 max(figylim1(2),figylim2(2))]);

figure(fignum+5);
subplot(2,1,1);
figylim1 = get(gca, 'YLim');
subplot(2,1,2);
figylim2 = get(gca, 'YLim');

figure(fignum+5);
subplot(2,1,1);
set(gca, 'XLim', figxlim);
set(gca, 'YLim', [0 max(figylim1(2),figylim2(2))]);
subplot(2,1,2);
set(gca, 'XLim', figxlim);

figure(fignum+1);
set(gca, 'XLim', figxlim);

figure(fignum+2);
figxlim = [0 1];
figylim = [0 1];
for m = 1:8
	subplot(4,2,m);
	tmp = get(gca,'XLim');
	figxlim(1) = min(figxlim(1),tmp(1));
	figxlim(2) = max(figxlim(2),tmp(2));
	tmp = get(gca,'YLim');
	figylim(1) = min(figylim(1),max(tmp(1),0));
	figylim(2) = max(figylim(2),tmp(2));
end
figure(fignum+3);
for m = 1:8
	subplot(4,2,m);
	tmp = get(gca,'XLim');
	figxlim(1) = min(figxlim(1),tmp(1));
	figxlim(2) = max(figxlim(2),tmp(2));
	tmp = get(gca,'YLim');
	figylim(1) = min(figylim(1),max(tmp(1),0));
	figylim(2) = max(figylim(2),tmp(2));
end
figure(fignum+2);
for m = 1:8
	subplot(4,2,m);
	set(gca,'Xlim',figxlim);
	set(gca,'YLim',figylim);
end
figure(fignum+3);
for m = 1:8
	subplot(4,2,m);
	set(gca,'Xlim',figxlim);
	set(gca,'YLim',figylim);
end

figure(fignum+4);
fig4xlim = [0 1];
fig4ylim = [0 1];
for m = 1:4
	subplot(2,2,m);
	tmp = get(gca,'XLim');
	fig4xlim(1) = min(fig4xlim(1),tmp(1));
	fig4xlim(2) = max(fig4xlim(2),tmp(2));	
	tmp = get(gca,'YLim');
	fig4ylim(1) = min(fig4ylim(1),max(tmp(1),0));
	fig4ylim(2) = max(fig4ylim(2),tmp(2));		
end
for m = 1:4
	subplot(2,2,m);
	set(gca,'Xlim',fig4xlim);
	set(gca,'YLim',fig4ylim);
end


figure(fignum+6);
fig6xlim = [0 6];
fig6ylim = [0 10];
for m = 1:4
	subplot(2,2,m);
	tmp = get(gca,'XLim');
	fig6xlim(1) = min(fig6xlim(1),tmp(1));
	fig6xlim(2) = max(fig6xlim(2),tmp(2));	
	tmp = get(gca,'YLim');
	fig6ylim(1) = min(fig6ylim(1),tmp(1));
	fig6ylim(2) = max(fig6ylim(2),tmp(2));		
end
for m = 1:4
	subplot(2,2,m);
	set(gca,'Xlim',fig6xlim);
	set(gca,'XTick',(fig6xlim(1)+1:fig6xlim(2)-1));
	set(gca,'YLim',fig6ylim);
	set(gca,'XTick',(fig6xlim(1)+1:fig6xlim(2)-1));
end

%% continue plotting goodput for A->B
figure(fignum+1);
bitpersec_total = bitpersec_AB + bitpersec_BA;
temp = [time_edges(1:end-1); time_edges(2:end)];
time_edges_rep = temp(:).';
temp = repmat(bitpersec_total(1:end-1),2,1);
nn_total_bitpersec = temp(:).';
plot(time_edges_rep,nn_total_bitpersec/1e3, 'r-','LineWidth',2)
legend(sprintf('A-->B (%4.1f Kbits/s)',mean(bitpersec_AB)/1e3), ...
	sprintf('B-->A (%4.1f Kbits/s)',mean(bitpersec_BA)/1e3), ...
	sprintf('A<=>B (%4.1f Kbits/s)',mean(bitpersec_total)/1e3));
%title(sprintf('Goodput (mean=%.1f Kbits/s)',mean(bitpersec_total)/1e3))
title('Goodput')
grid on

%% save results
if SAVERESULTS
	strg1 = sprintf('time%ito%is_',round(evalTimeRange));
	strg2 = sprintf('node%iand%i_',pairIDs(1:2));
	pairStrg = [strg1 strg2];
	
	%save mat file
	longFileName = fullfile(result_path, [pairStrg 'results.mat']);
	if exist(longFileName,'file'), delete(longFileName); end 
	save(longFileName);
	
	%save all fig files
	longFileName = fullfile(result_path, [pairStrg 'traffic.fig']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum,   longFileName, 'fig');
	
	longFileName = fullfile(result_path, [pairStrg 'goodput.fig']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+1, longFileName, 'fig');
	
	longFileName = fullfile(result_path, [pairStrg 'delay_AB.fig']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+2, longFileName, 'fig');
	
	longFileName = fullfile(result_path, [pairStrg 'delay_BA.fig']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+3, longFileName, 'fig');
	
	longFileName = fullfile(result_path, [pairStrg 'delay_roundtrip.fig']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+4, longFileName, 'fig');
	
	longFileName = fullfile(result_path, [pairStrg 'packet_count.fig']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+5, longFileName, 'fig');
	
	longFileName = fullfile(result_path, [pairStrg 'MAC_stat.fig']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+6, longFileName, 'fig');
	
	%save all png files
	longFileName = fullfile(result_path, [pairStrg 'traffic.png']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum,   longFileName, 'png');
	
	longFileName = fullfile(result_path, [pairStrg 'goodput.png']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+1, longFileName, 'png');
	
	longFileName = fullfile(result_path, [pairStrg 'delay_AB.png']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+2, longFileName, 'png');
	
	longFileName = fullfile(result_path, [pairStrg 'delay_BA.png']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+3, longFileName, 'png');
	
	longFileName = fullfile(result_path, [pairStrg 'delay_roundtrip.png']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+4, longFileName, 'png');
	
	longFileName = fullfile(result_path, [pairStrg 'packet_count.png']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+5, longFileName, 'png');
	
	longFileName = fullfile(result_path, [pairStrg 'MAC_stat.png']);
	if exist(longFileName,'file'), delete(longFileName); end 	
	saveas(fignum+6, longFileName, 'png');
end


