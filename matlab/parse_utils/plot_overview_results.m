function perform = plot_overview_results(perform, config, time_params, fignum, save_params)
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
num_nodes = config.num_nodes;
sets_evalnodes = config.sets_evalnodes;
num_links = numel(sets_evalnodes);
result_path = config.result_path;
logs_path = config.logs_path;

node_ID = config.node_ID;

inittime = time_params.inittime;
endtime = time_params.endtime;
deltatime = time_params.deltatime;
time_edges = time_params.time_edges;


xx = cos(((1:num_nodes)-1)/num_nodes*2*pi+pi/2);
yy = sin(((1:num_nodes)-1)/num_nodes*2*pi+pi/2);

figure(fignum); clf;

set(fignum,'Color',[1 1 1])
hold on
for k = 1:num_nodes
	text(xx(k)*1.4-.15,yy(k)*1.4-.1,sprintf('Node %i (ID=%i)',k,node_ID(k)),'color','r','fontsize',16);
end
axis([-2 2 -2 2])
axis square
axis off

add_struct_as_contextmenu(config,fignum,'Test setup params');

clear node_state_info
clear channel_sounding_info
clear tx_channelizer_info rx_channelizer_info

for k = 1:num_nodes

	if isfield(config,'state_xml') && iscell(config.state_xml)
		%first check if direct state log file name exists
		fn_state = fullfile(logs_path, config.state_xml{k});
	elseif isfield(config,'node_state_xml') && iscell(config.node_state_xml)
		%check if alternative direct state log file name exists
		fn_state = fullfile(logs_path, config.node_state_xml{k});		
	else
		fn_packet = config.node_xml{k};
		ifind = strfind(fn_packet,'packet');
		
		if ~isempty(ifind)
			%assume state log file is same as packet file name, but replace
			%'packet' with 'state'
			fn_state = fullfile(logs_path, [fn_packet(1:ifind(1)-1) 'state' fn_packet(ifind(1)+6:end)]);
		else			
			ifind = strfind(fn_packet,'pkt');
			if ~isempty(ifind)
				%assume state log file is same as packet file name, but replace
				%'pkt' with 'state'
				fn_state = fullfile(logs_path, [fn_packet(1:ifind(1)-1) 'state' fn_packet(ifind(1)+3:end)]);
			else
				%assume state log is just node#_state.xml
				fn_state = fullfile(logs_path, sprintf('node%i_state.xml',k));
			end
		end
		
		fprintf('State log file name is not specified.  State log file name is assumed to be : %s if file exists.\n',fn_state);
	end
	
	if exist(fn_state,'file')
		temp_state = xml_readandparse(fn_state,'node_state');
		if ~isempty(temp_state)
			node_state_info.(sprintf('node%i_state',k)) = temp_state;
		end
		temp_chansound = xml_readandparse(fn_state,'channel_sounding');
		if ~isempty(temp_chansound)
			channel_sounding_info.(sprintf('node%i_channel',k)) = temp_chansound;
		end
		temp_tx_chan = xml_readandparse(fn_state,'tx_channelizer');
		if ~isempty(temp_tx_chan)
			tx_channelizer_info.(sprintf('node%i_tx_channelizer',k)) = temp_tx_chan;
		end
		temp_rx_chan = xml_readandparse(fn_state,'rx_channelizer');
		if ~isempty(temp_rx_chan)
			rx_channelizer_info.(sprintf('node%i_rx_channelizer',k)) = temp_rx_chan;
		end
	end
end
if exist('node_state_info','var') && ~isempty(node_state_info)
	add_struct_as_contextmenu(node_state_info,fignum,'Node state');
	for n = 1:num_links
		perform(n).node_state = node_state_info;
	end	
end
if exist('channel_sounding_info','var') && ~isempty(channel_sounding_info)
	add_struct_as_contextmenu(channel_sounding_info,fignum,'Channel sounding');
	pathloss_matrix = ones(num_nodes,num_nodes)*99999;
	for k = 1:num_nodes
		nodek_channel = sprintf('node%i_channel',k);
		for p = 1:num_nodes
			if isfield(channel_sounding_info,nodek_channel)
				pathloss_matrix(k,p) = str2double(channel_sounding_info.(nodek_channel).results(p).pathloss_dB);
			end
		end
	end
	for n = 1:num_links
		perform(n).pathloss = pathloss_matrix;
		perform(n).channel_sounding = channel_sounding_info;
	end
end
if exist('tx_channelizer_info','var') && ~isempty(tx_channelizer_info)
	add_struct_as_contextmenu(tx_channelizer_info,fignum,'Tx channelizer');
	for n = 1:num_links
		perform(n).tx_channelizer = tx_channelizer_info;
	end	
end
if exist('rx_channelizer_info','var') && ~isempty(rx_channelizer_info)
	add_struct_as_contextmenu(rx_channelizer_info,fignum,'Rx channelizer');
	for n = 1:num_links
		perform(n).rx_channelizer = rx_channelizer_info;
	end	
end


for n = 1:num_links
	evalnodes = sets_evalnodes{n};
	
	bitpersec_BA = perform(n).nodeA_bitpersec;
	bitpersec_AB = perform(n).nodeB_bitpersec;
	bitpersec_total = perform(n).nodeAB_bitpersec;

	enodes = [evalnodes(1) evalnodes(end)];
	x0 = mean(xx(enodes));
	y0 = mean(yy(enodes));

	line(xx(evalnodes),yy(evalnodes), 'Color','r','LineWidth', 4);
	text(3*x0-.7,3*y0+0.2-.3,sprintf('%i-->%i (%4.1f Kbits/s)',evalnodes(1),evalnodes(end),mean(bitpersec_AB)/1e3));
	text(3*x0-.7,3*y0+0.0-.3,sprintf('%i<--%i (%4.1f Kbits/s)',evalnodes(1),evalnodes(end),mean(bitpersec_BA)/1e3));
	text(3*x0-.7,3*y0-0.2-.3,sprintf('%i<=>%i (%4.1f Kbits/s)',evalnodes(1),evalnodes(end),mean(bitpersec_total)/1e3));
	if exist('channel_sounding_info','var') && ~isempty(channel_sounding_info)
		if pathloss_matrix(evalnodes(2),evalnodes(1)) ~= 99999
			text(3*x0-.7,3*y0-0.4-.3,sprintf('Path loss %i-->%i = %4.1f dB',evalnodes(1),evalnodes(2),pathloss_matrix(evalnodes(2),evalnodes(1))));
		end
		if numel(evalnodes) == 3
			if pathloss_matrix(evalnodes(2),evalnodes(3)) ~= 99999
				text(3*x0-.7,3*y0-0.6-.3,sprintf('Path loss %i-->%i = %4.1f dB',evalnodes(3),evalnodes(2),pathloss_matrix(evalnodes(2),evalnodes(3))));
			end			
		end
	end
end

plot(xx,yy,'ko','MarkerSize',10,'LineWidth',4);


evalTimeRangeUpdated = save_params.evalTimeRangeUpdated;
result_path = config.result_path;
filename = 'overview';
qlfiletype = 'png';
SAVERESULTS = save_params.SAVERESULTS;

save_fig_with_quicklook(fignum,evalTimeRangeUpdated,result_path,filename,qlfiletype,SAVERESULTS);


