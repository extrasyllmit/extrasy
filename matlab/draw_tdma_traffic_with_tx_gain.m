function num_packets = draw_tdma_traffic_with_tx_gain(fn,maxParseTime)
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
if nargin < 2
	maxParseTime = Inf;
end

addpath('./parse_utils');
addpath('./parse_utils/xml_toolbox');

clf;

%define packet code
% PKTCODE.RTS = 1;
% PKTCODE.CTS = 2;
% PKTCODE.DATA = 3;
% PKTCODE.ACK = 4;
% pktcode_colors = {'k','g','b','r'};

PKTCODE.OTHER     = 0;
PKTCODE.BEACON    = 1;
PKTCODE.DATA      = 2;
PKTCODE.KEEPALIVE = 3;
PKTCODE.FEEDBACK  = 4;
pktcode_colors = {'c','r','b','g','k'};


y_values = [2 1];
y_syms = {'v', '^'};

%parsing
[p,n,e] = fileparts(fn);
mat_fn = fullfile(p,'node_log.mat');
if exist(mat_fn)
	load(mat_fn);
	node_log = node_log{1};
else
	node_log = xml_readandparse(fn,'packet',Inf,maxParseTime);
	num_packets = numel(node_log);
end

inittime = str2double(node_log(1).timestamp);

pktnames = fieldnames(PKTCODE);

%find indices with valid transmit (or receive)
ii_valid_tx = refine_log(node_log,'direction','transmit');
ii_valid_rx = refine_log(node_log,'direction','receive');

ii_goodcrc = refine_log(node_log(ii_valid_rx),'crcpass','true');
ii_valid_rx_goodcrc = ii_valid_rx(ii_goodcrc);
ii_valid_rx_badcrc  = setdiff(ii_valid_rx, ii_valid_rx_goodcrc);

ii_valid = {ii_valid_tx, ii_valid_rx_goodcrc};

for k = 1:numel(ii_valid)
	
	ii_known = [];
	
	for n = 1:numel(pktnames)
		
		pkt_code = PKTCODE.(pktnames{n});
		
		ii_pktCode = refine_log(node_log(ii_valid{k}),'pktCode',pkt_code);
		ii_known = [ii_known ii_pktCode];
		
		timestamps = get_timestamps(node_log(ii_valid{k}(ii_pktCode)));
		if ~isempty(timestamps)
			h1 = subplot(2,1,1);
			plot(timestamps-inittime,y_values(k), [pktcode_colors{pkt_code+1} y_syms{k}],'MarkerSize',12,'LineWidth',2);
			hold on
		end		
	end
	
	ii_unknown = setdiff((1:numel(ii_valid{k})),ii_known);
	timestamps = get_timestamps(node_log(ii_valid{k}(ii_unknown)));
	if ~isempty(timestamps)
		h1 = subplot(2,1,1);
		plot(timestamps-inittime,y_values(k), ['y' y_syms{k}],'MarkerSize',12,'LineWidth',2);
		hold on
	end
	
end

%handle rx with bad crc separately
timestamps = get_timestamps(node_log(ii_valid_rx_badcrc));
if ~isempty(timestamps)
	h1 = subplot(2,1,1);
	plot(timestamps-inittime,y_values(2), ['y' '*'],'MarkerSize',12,'LineWidth',2);
	hold on
end

%retrieve tx gain
ii = refine_log(node_log(ii_valid_tx),'linkdirection','down');
ii_valid_tx_downlink = ii_valid_tx(ii);

[ii_toID, toID] = get_any_id(node_log(ii_valid_tx_downlink),'toID');

unique_toID = unique(toID);

if min(unique_toID) == 0, unique_toID = unique_toID+1; end

h2 = subplot(2,1,2);
color_style = {'bo','ro','go','ko','co','mo','yo','b*','r*','g*','k*','c*','m*','y*'};
hold on;
lg = {};
for k = 1:numel(unique_toID)

	thisID = unique_toID(k);
	lg = [lg {sprintf('ID = %i',thisID)}];
	
	ii = refine_log(node_log(ii_valid_tx_downlink),'toID',thisID);
	ii_valid_tx_downlink_thisID = ii_valid_tx_downlink(ii);

	[ii_txgain, tx_gain] = get_any_id(node_log(ii_valid_tx_downlink_thisID),'tx_gain');
	ii_valid_tx_downlink_thisID_txgain = ii_valid_tx_downlink_thisID(ii_txgain);

	timestamps = get_timestamps(node_log(ii_valid_tx_downlink_thisID_txgain));

	plot(timestamps-inittime,tx_gain,color_style{k})
end

legend(lg);
set(gca,'YLim',[0 35])
ylabel('Tx Gain (dB)');
xlabel('Time (s)')
box on

h1 = subplot(2,1,1);
set(gca,'YLim',[y_values(2)-0.5 y_values(1)+0.5])
set(gca,'YTick',[y_values(2) y_values(1)])
set(gca,'YTickLabel',{'Rx','Tx'})

xlabel('Time (s)')
box on
hold off


linkaxes([h1 h2],'x');



