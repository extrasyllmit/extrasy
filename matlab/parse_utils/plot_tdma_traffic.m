function plot_tdma_traffic(node_log, config, PKTCODE, time_params, fignum, save_params)
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
figure(fignum); clf; hold on;

if isfield(PKTCODE,'BEACON') %tdma
	figure(fignum+1); clf; hold on;
end

num_nodes = numel(node_log);

xlim_all = zeros(num_nodes,2);
ylim_all = zeros(num_nodes,2);
ax = zeros(num_nodes,1);

PLOT_FREQ_INSTEAD_OF_CHANNEL = 0;

for n = 1:num_nodes
	
	if isfield(PKTCODE,'BEACON') %tdma
		figure(fignum)
		ax(n) = subplot(num_nodes,1,n);
		if PLOT_FREQ_INSTEAD_OF_CHANNEL
			logs_path = config.logs_path;
			fn_state = config.node_state_xml{n};
			state_log = xml_readandparse(fullfile(logs_path,fn_state),'node_state');
			[n_tx, n_rx] = draw_traffic_with_frequencies(node_log{n}, state_log, n, PKTCODE, time_params.inittime);
		else
			[n_tx, n_rx] = draw_traffic_with_channels(node_log{n}, n, PKTCODE, time_params.inittime);
		end
		title(sprintf('Node %i (ID=%i) Ntx=%i Nrx=%i',n,config.node_ID(n),n_tx,n_rx));
		
		figure(fignum+1)
		subplot(num_nodes,1,n);
		draw_tdma_traffic_with_tx_gain(node_log{n}, n, PKTCODE, time_params.inittime);
		title(sprintf('Node %i (ID=%i)',n,config.node_ID(n)));
	else %csma
		figure(fignum)
		ax(n) = subplot(num_nodes,1,n);
		[n_tx, n_rx] = draw_traffic(node_log{n}, n, PKTCODE, time_params.inittime);
		title(sprintf('(ID=%i) Ntx=%i Nrx=%i',config.node_ID(n),n_tx,n_rx));
	end
	
	figure(fignum)
	ax(n) = subplot(num_nodes,1,n);	
	xlim_all(n,:) = get(gca,'XLim');
	ylim_all(n,:) = get(gca,'YLim');
end

xlim_common = [min(xlim_all(:,1)) max(xlim_all(:,2))];
ylim_common = [min(ylim_all(:,1)) max(ylim_all(:,2))];
figure(fignum)
for n = 1:num_nodes
	subplot(num_nodes,1,n);
	set(gca,'XLim',xlim_common);
	set(gca,'YLim',ylim_common+[0 1]);
	set(gca,'Xgrid','on','Ygrid','on','XminorTick','on','XminorGrid','on');
end

linkaxes(ax,'x');

if save_params.SAVERESULTS
	evalTimeRangeUpdated = save_params.evalTimeRangeUpdated;
	result_path = config.result_path;
	filename = 'traffic';
	qlfiletype = 'png';
	SAVERESULTS = save_params.SAVERESULTS;
	
	save_fig_with_quicklook(fignum,evalTimeRangeUpdated,result_path,filename,qlfiletype,SAVERESULTS)

	
	if isfield(PKTCODE,'BEACON') %tdma
		evalTimeRangeUpdated = save_params.evalTimeRangeUpdated;
		result_path = config.result_path;
		filename = 'txgain';
		qlfiletype = 'png';
		SAVERESULTS = save_params.SAVERESULTS;
		
		save_fig_with_quicklook(fignum+1,evalTimeRangeUpdated,result_path,filename,qlfiletype,SAVERESULTS)
	end
end



function [n_tx, n_rx] = draw_traffic(node_log, nodenum, PKTCODE, inittime)

if isfield(PKTCODE,'BEACON')
	pktcode_colors = {'c','r','b','g','k'};
else %use different color coding for CSMA
	pktcode_colors = {'c','k','g','b','r'};
end

y_values = [2 1];
y_syms = {'^', '^'}; %{'v', '^'};

pktnames = fieldnames(PKTCODE);

%find indices with valid transmit (or receive)
ii_valid_tx = refine_log(node_log,'direction','transmit');
ii_valid_rx = refine_log(node_log,'direction','receive');

n_tx = numel(ii_valid_tx);
n_rx = numel(ii_valid_rx);

ii_goodcrc = refine_log(node_log(ii_valid_rx),'crcpass','true');
ii_valid_rx_goodcrc = ii_valid_rx(ii_goodcrc);
ii_valid_rx_badcrc  = setdiff(ii_valid_rx, ii_valid_rx_goodcrc);

ii_valid = {ii_valid_tx, ii_valid_rx_goodcrc};
hd_vec = [];
lgcell = {};

for k = 1:numel(ii_valid)
	
	ii_known = [];
	
	for n = 1:numel(pktnames)
		
		pkt_code = PKTCODE.(pktnames{n});
		
		ii_pktCode = refine_log(node_log(ii_valid{k}),'pktCode',pkt_code);
		ii_known = [ii_known ii_pktCode];
		
		timestamps = get_timestamps(node_log(ii_valid{k}(ii_pktCode)));
		if ~isempty(timestamps)
			hd = plot(timestamps-inittime,repmat(y_values(k),1,numel(timestamps)), [pktcode_colors{pkt_code+1} y_syms{k}],'MarkerSize',12,'LineWidth',2);
			hd_vec = [hd_vec; hd];
			lgcell = [lgcell {sprintf('%i%s',n,pktnames{n})}]; %leading integer for forced order
			hold on
		end		
	end
	
	ii_unknown = setdiff((1:numel(ii_valid{k})),ii_known);
	timestamps = get_timestamps(node_log(ii_valid{k}(ii_unknown)));
	if ~isempty(timestamps)
		hd = plot(timestamps-inittime,repmat(y_values(k),1,numel(timestamps)), ['y' y_syms{k}],'MarkerSize',12,'LineWidth',2);
		hd_vec = [hd_vec; hd];
		lgcell = [lgcell {'8Unknown'}];
		hold on
	end
	
end

%handle rx with bad crc separately
timestamps = get_timestamps(node_log(ii_valid_rx_badcrc));
if ~isempty(timestamps)
	hd = plot(timestamps-inittime,repmat(y_values(2),1,numel(timestamps)), ['g' '*'],'MarkerSize',12,'LineWidth',2);
	hd_vec = [hd_vec; hd];
	lgcell = [lgcell {'9Rx bad CRC'}];
	hold on
end

[lgcell_unique,ii_unique,~] = unique(lgcell,'first');
hd_vec_unique = hd_vec(ii_unique);

%strip off leading integer used in forced order
lgcell_unique = cellfun(@(x) {x(2:end)},lgcell_unique);

if ~isempty(hd_vec_unique)
	legend(hd_vec_unique, lgcell_unique);
end

set(gca,'YLim',[0.5 2.5])
set(gca,'YTick',[1 2])
set(gca,'YTickLabel',{sprintf('Node%i:Rx',nodenum),sprintf('Node%i:Tx',nodenum)})

xlabel('Time (s)')
box on

hold off


function [n_tx, n_rx] = draw_traffic_with_channels(node_log, nodenum, PKTCODE, inittime)

if isfield(PKTCODE,'BEACON')
	pktcode_colors = {'c','r','b','g','k'};
else %use different color coding for CSMA
	pktcode_colors = {'c','k','g','b','r'};
end

y_values = [0 0]; %[1 2];
y_syms = {'^', 'v'};
y_lab = {'Rx','Tx'};

pktnames = fieldnames(PKTCODE);

%find indices with valid transmit (or receive)
ii_valid_tx = refine_log(node_log,'direction','transmit');
ii_valid_rx = refine_log(node_log,'direction','receive');

n_tx = numel(ii_valid_tx);
n_rx = numel(ii_valid_rx);

ii_goodcrc = refine_log(node_log(ii_valid_rx),'crcpass','true');
ii_valid_rx_goodcrc = ii_valid_rx(ii_goodcrc);
ii_valid_rx_badcrc  = setdiff(ii_valid_rx, ii_valid_rx_goodcrc);

ii_valid = {ii_valid_rx_goodcrc, ii_valid_tx};

uniq_freq = {[],[]};
ylab_uniq = {};

hd_vec = [];
lgcell = {};

for k = 1:numel(ii_valid)
	
	ii_known = [];
	
	for n = 1:numel(pktnames)
		
		pkt_code = PKTCODE.(pktnames{n});
		
		ii_pktCode = refine_log(node_log(ii_valid{k}),'pktCode',pkt_code);
		ii_known = [ii_known ii_pktCode];
		
		timestamps = get_timestamps(node_log(ii_valid{k}(ii_pktCode)));
		[ii_frq frequencies] = get_any_id(node_log(ii_valid{k}(ii_pktCode)),'frequency');
		uniq_freq{k} = unique([uniq_freq{k} unique(frequencies)]);
		if ~isempty(timestamps)
			hd = plot(timestamps-inittime,y_values(k)+frequencies, [pktcode_colors{pkt_code+1} y_syms{k}],'MarkerSize',4,'LineWidth',2);
			hd_vec = [hd_vec; hd];
			lgcell = [lgcell {sprintf('%i%s',n,pktnames{n})}]; %leading integer for forced order
			hold on
		end		
	end
	
	ii_unknown = setdiff((1:numel(ii_valid{k})),ii_known);
	timestamps = get_timestamps(node_log(ii_valid{k}(ii_unknown)));
	[ii_frq frequencies] = get_any_id(node_log(ii_valid{k}(ii_unknown)),'frequency');
	uniq_freq{k} = unique([uniq_freq{k} unique(frequencies)]);
	if ~isempty(timestamps)
		hd = plot(timestamps-inittime,y_values(k)+frequencies, ['y' y_syms{k}],'MarkerSize',4,'LineWidth',2);
		hd_vec = [hd_vec; hd];
		lgcell = [lgcell {'8Unknown'}];
		hold on
	end
	
% 	n = numel(uniq_freq{k});
% 	for f = 1:n
% 		ylab_uniq = [ylab_uniq {sprintf([y_lab{k} '(ch=%i)'],uniq_freq{k}(f))}];
% 	end

end

uniq_freq_both = unique([uniq_freq{1} uniq_freq{2}]);
n = numel(uniq_freq_both);
for f = 1:n
	ylab_uniq = [ylab_uniq {sprintf(['%i'],uniq_freq_both(f))}];
end


%handle rx with bad crc separately
timestamps = get_timestamps(node_log(ii_valid_rx_badcrc));
if ~isempty(timestamps)
	hd = plot(timestamps-inittime,y_values(1), ['g' '*'],'MarkerSize',4,'LineWidth',2);
	hd_vec = [hd_vec; hd];
	lgcell = [lgcell {'9Rx bad CRC'}];
	hold on
end

[lgcell_unique,ii_unique,~] = unique(lgcell,'first');
hd_vec_unique = hd_vec(ii_unique);

%strip off leading integer used in forced order
lgcell_unique = cellfun(@(x) {x(2:end)},lgcell_unique);

if ~isempty(hd_vec_unique)
	legend(hd_vec_unique, lgcell_unique);
end

%set(gca,'YLim',[0.5 3.0])
%set(gca,'YTick',[y_values(1)+unique(uniq_freq{1})/10 y_values(2)+unique(uniq_freq{2})/10])
set(gca,'YTick',uniq_freq_both)
set(gca,'YTickLabel',ylab_uniq)

xlabel('Time (s)')
ylabel('Channel')
box on

hold off

function draw_tdma_traffic_with_tx_gain(node_log, nodenum, PKTCODE, inittime)

if isfield(PKTCODE,'BEACON')
	pktcode_colors = {'c','r','b','g','k'};
else %use different color coding for CSMA
	pktcode_colors = {'c','k','g','b','r'};
end

y_values = [2 1];
y_syms = {'v', '^'};

pktnames = fieldnames(PKTCODE);

%find indices with valid transmit (or receive)
ii_valid_tx = refine_log(node_log,'direction','transmit');
ii_valid_rx = refine_log(node_log,'direction','receive');

ii_goodcrc = refine_log(node_log(ii_valid_rx),'crcpass','true');
ii_valid_rx_goodcrc = ii_valid_rx(ii_goodcrc);
ii_valid_rx_badcrc  = setdiff(ii_valid_rx, ii_valid_rx_goodcrc);

ii_valid = {ii_valid_tx, ii_valid_rx_goodcrc};


%retrieve tx gain
[~, toID] = get_any_id(node_log(ii_valid_tx),'toID');

unique_toID = unique(toID);

color_style = {'bo','ro','go','ko','co','mo','yo','b*','r*','g*','k*','c*','m*','y*'};
hold on;
lg = {};
for k = 1:numel(unique_toID)

	thisID = unique_toID(k);
	lg = [lg {sprintf('ID = %i',thisID)}];
	
	ii = refine_log(node_log(ii_valid_tx),'toID',thisID);
	ii_valid_tx_thisID = ii_valid_tx(ii);

	[ii_txgain, tx_gain] = get_any_id(node_log(ii_valid_tx_thisID),'tx_gain');
	ii_valid_tx_thisID_txgain = ii_valid_tx_thisID(ii_txgain);

	timestamps = get_timestamps(node_log(ii_valid_tx_thisID_txgain));

	plot(timestamps-inittime,tx_gain,color_style{k})
end

legend(lg);
set(gca,'YLim',[0 35])
ylabel('Tx Gain (dB)');
xlabel('Time (s)')
box on


function [n_tx, n_rx] = draw_traffic_with_frequencies(node_log, state_log, nodenum, PKTCODE, inittime)

if isfield(PKTCODE,'BEACON')
	pktcode_colors = {'c','r','b','g','k'};
	[~, num_chan] = xml_arraygetfields(state_log,{'phy','digital_hopper','tx_channelizer','number_digital_channels'});
	num_chan = str2double(num_chan);
	[~, rf_centerfrequency] = xml_arraygetfields(state_log,{'radio','tx_frontend','rf_frequency'});
	rf_centerfrequency = str2double(rf_centerfrequency);
else %use different color coding for CSMA
	pktcode_colors = {'c','k','g','b','r'};
end

y_values = [0 0]; %[1 2];
y_syms = {'^', 'v'};
y_lab = {'Rx','Tx'};

pktnames = fieldnames(PKTCODE);

%find indices with valid transmit (or receive)
ii_valid_tx = refine_log(node_log,'direction','transmit');
ii_valid_rx = refine_log(node_log,'direction','receive');

n_tx = numel(ii_valid_tx);
n_rx = numel(ii_valid_rx);

ii_goodcrc = refine_log(node_log(ii_valid_rx),'crcpass','true');
ii_valid_rx_goodcrc = ii_valid_rx(ii_goodcrc);
ii_valid_rx_badcrc  = setdiff(ii_valid_rx, ii_valid_rx_goodcrc);

ii_valid = {ii_valid_rx_goodcrc, ii_valid_tx};

uniq_freq = {[],[]};
ylab_uniq = {};

hd_vec = [];
lgcell = {};

for k = 1:numel(ii_valid)
	
	ii_known = [];
	
	for n = 1:numel(pktnames)
		
		pkt_code = PKTCODE.(pktnames{n});
		
		ii_pktCode = refine_log(node_log(ii_valid{k}),'pktCode',pkt_code);
		ii_known = [ii_known ii_pktCode];
		
		timestamps = get_timestamps(node_log(ii_valid{k}(ii_pktCode)));
		[~, rfcenterfreq] = get_any_id(node_log(ii_valid{k}(ii_pktCode)),'rfcenterfreq');
		[~, channel] = get_any_id(node_log(ii_valid{k}(ii_pktCode)),'frequency');
		[~, bandwidth] = get_any_id(node_log(ii_valid{k}(ii_pktCode)),'bandwidth');
		
		neg_chan = channel > num_chan/2;
		channel = (~neg_chan).*channel + (neg_chan).*(channel-num_chan);
		bbfreq = bandwidth.*channel;
		frequencies = rfcenterfreq + bbfreq;
		
		uniq_freq{k} = unique([uniq_freq{k} unique(frequencies)]);
		if ~isempty(timestamps)
			hd = plot(timestamps-inittime,y_values(k)+frequencies, [pktcode_colors{pkt_code+1} y_syms{k}],'MarkerSize',4,'LineWidth',2);
			hd_vec = [hd_vec; hd];
			lgcell = [lgcell {sprintf('%i%s',n,pktnames{n})}]; %leading integer for forced order
			hold on
		end		
	end
	
	ii_unknown = setdiff((1:numel(ii_valid{k})),ii_known);
	timestamps = get_timestamps(node_log(ii_valid{k}(ii_unknown)));
	[~, rfcenterfreq] = get_any_id(node_log(ii_valid{k}(ii_unknown)),'rfcenterfreq');
	[~, channel] = get_any_id(node_log(ii_valid{k}(ii_unknown)),'frequency');
	[~, bandwidth] = get_any_id(node_log(ii_valid{k}(ii_unknown)),'bandwidth');
	
	neg_chan = channel > num_chan/2;
	channel = (~neg_chan).*channel + (neg_chan).*(channel-num_chan);
	bbfreq = (bandwidth./num_chan).*channel;
	frequencies = rfcenterfreq + bbfreq;
	
	uniq_freq{k} = unique([uniq_freq{k} unique(frequencies)]);
	if ~isempty(timestamps)
		hd = plot(timestamps-inittime,y_values(k)+frequencies, ['y' y_syms{k}],'MarkerSize',4,'LineWidth',2);
		hd_vec = [hd_vec; hd];
		lgcell = [lgcell {'8Unknown'}];
		hold on
	end
	
% 	n = numel(uniq_freq{k});
% 	for f = 1:n
% 		ylab_uniq = [ylab_uniq {sprintf([y_lab{k} '(ch=%i)'],uniq_freq{k}(f))}];
% 	end

end

uniq_freq_both = unique([uniq_freq{1} uniq_freq{2}]);
n = numel(uniq_freq_both);
for f = 1:n
	ylab_uniq = [ylab_uniq {sprintf(['%i'],uniq_freq_both(f))}];
end


%handle rx with bad crc separately
timestamps = get_timestamps(node_log(ii_valid_rx_badcrc));

if ~isempty(timestamps)
	hd = plot(timestamps-inittime,y_values(1)+rf_centerfrequency, ['g' '*'],'MarkerSize',4,'LineWidth',2);
	hd_vec = [hd_vec; hd];
	lgcell = [lgcell {'9Rx bad CRC'}];
	hold on
end

[lgcell_unique,ii_unique,~] = unique(lgcell,'first');
hd_vec_unique = hd_vec(ii_unique);

%strip off leading integer used in forced order
lgcell_unique = cellfun(@(x) {x(2:end)},lgcell_unique);

if ~isempty(hd_vec_unique)
	legend(hd_vec_unique, lgcell_unique);
end

%set(gca,'YLim',[0.5 3.0])
%set(gca,'YTick',[y_values(1)+unique(uniq_freq{1})/10 y_values(2)+unique(uniq_freq{2})/10])
set(gca,'YTick',uniq_freq_both)
set(gca,'YTickLabel',ylab_uniq)

xlabel('Time (s)')
ylabel('Channel')
box on

hold off




