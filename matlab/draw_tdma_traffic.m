function num_packets = draw_tdma_traffic(fn,maxParseTime)
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
if nargin < 2
	maxParseTime = Inf;
end

addpath('./parse_utils');
addpath('./parse_utils/xml_toolbox');

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

y_values = [0 0]; %[1 2];
y_syms = {'^', 'v'};
y_lab = {'Rx','Tx'};

%parsing
node_log = xml_readandparse(fn,'packet',Inf,maxParseTime);
num_packets = numel(node_log);

inittime = str2double(node_log(1).timestamp);

pktnames = fieldnames(PKTCODE);

%find indices with valid transmit (or receive)
ii_valid_tx = refine_log(node_log,'direction','transmit');
ii_valid_rx = refine_log(node_log,'direction','receive');

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
	ylab_uniq = [ylab_uniq {sprintf(['ch=%i'],uniq_freq_both(f))}];
end


%handle rx with bad crc separately
timestamps = get_timestamps(node_log(ii_valid_rx_badcrc));
if ~isempty(timestamps)
	hd = plot(timestamps-inittime,y_values(1), ['y' '*'],'MarkerSize',4,'LineWidth',2);
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



