function [node_log, state_log] = plot_traffic_standalone(fn_packet,fn_state,mactype,maxParseTime,loadexisting)
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
if nargin < 5
	loadexisting = 1;
end

if nargin < 4
	maxParseTime = Inf;
end

if nargin < 3
	mactype = 'tdma';
end

addpath('./parse_utils');
addpath('./parse_utils/xml_toolbox');

clear PKTCODE %don't want to overlap different types
if isequal(mactype(1:4),'csma')
	PKTCODE.RTS  = 1;
	PKTCODE.CTS  = 2;
	PKTCODE.DATA = 3;
	PKTCODE.ACK  = 4;
elseif isequal(mactype(1:4),'tdma')
	PKTCODE.OTHER     = 0;
	PKTCODE.BEACON    = 1;
	PKTCODE.DATA      = 2;
	PKTCODE.KEEPALIVE = 3;
	PKTCODE.FEEDBACK  = 4;
else
	error('unknown mactype specification');
end

[fpath, fname, fext] = fileparts(fn_packet);
fn_packet_dotmat = fullfile(fpath, [fname '.mat']);
if exist(fn_packet_dotmat) && loadexisting
	load(fn_packet_dotmat);
else
	node_log = xml_readandparse(fn_packet,'packet',Inf,maxParseTime,1);
	save(fullfile(fpath, [fname '.mat']),'node_log');
end

[fpath, fname, fext] = fileparts(fn_state);
fn_state_dotmat = fullfile(fpath, [fname '.mat']);
if exist(fn_state_dotmat) && loadexisting
	load(fn_state_dotmat);
else
	state_log = xml_readandparse(fn_state,'node_state');
	node_options = xml_readandparse(fn_state,'options');
	save(fullfile(fpath, [fname '.mat']),'state_log','node_options');
end

inittime = str2double(node_log(1).timestamp);

figure;
draw_traffic_with_frequencies(node_log, state_log, PKTCODE, inittime);

function [n_tx, n_rx] = draw_traffic_with_frequencies(node_log, state_log, PKTCODE, inittime)

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
			hold on
			
			hd = plot(timestamps-inittime,y_values(k)+frequencies, [pktcode_colors{pkt_code+1} y_syms{k}],'MarkerSize',4,'LineWidth',2);
			hd_vec = [hd_vec; hd];
			lgcell = [lgcell {sprintf('%i%s',n,pktnames{n})}]; %leading integer for forced order
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
		lgcell = [lgcell {'9Unknown'}];
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
ylabel('Frequency')
box on

hold off





