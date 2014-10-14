function num_packets = annotate_iq_with_traffic(fn,maxParseTime, t0, y_lims)
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

%define packet code
% PKTCODE.RTS = 1;
% PKTCODE.CTS = 2;
% PKTCODE.DATA = 3;
% PKTCODE.ACK = 4;
% pktcode_colors = {'k','g','b','r'};

PKTCODE.BEACON    = 1;
PKTCODE.DATA      = 2;
PKTCODE.KEEPALIVE = 3;
PKTCODE.OTHER     = 4;
pktcode_colors = {'r','k','g','b'};



y_range = y_lims(2)-y_lims(1);

y_values = [y_lims(2)+.1*y_range  y_lims(2)-.2*y_range];
y_syms = {'v', '^'};

%parsing
node_log = xml_readandparse(fn,'packet',Inf,maxParseTime);
num_packets = numel(node_log);

inittime = t0;

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
			hold on
      plot(timestamps-inittime,y_values(k), [pktcode_colors{pkt_code} y_syms{k}],'MarkerSize',12,'LineWidth',2);
			hold on
		end		
	end
	
	ii_unknown = setdiff((1:numel(ii_valid{k})),ii_known);
	timestamps = get_timestamps(node_log(ii_valid{k}(ii_unknown)));
	if ~isempty(timestamps)
    hold on
		plot(timestamps-inittime,y_values(k), ['y' y_syms{k}],'MarkerSize',12,'LineWidth',2);
		hold on
	end
	
end

%handle rx with bad crc separately
timestamps = get_timestamps(node_log(ii_valid_rx_badcrc));
if ~isempty(timestamps)
  hold on
	plot(timestamps-inittime,y_values(2), ['y' '*'],'MarkerSize',12,'LineWidth',2);
	hold on
end


% set(h_ax,'YLim',[y_lims(1) y_lims(2)+.2*y_range  ])



