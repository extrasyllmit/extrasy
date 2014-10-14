function perform = plot_tdma_goodput(perform, config, time_params, fignum, save_params)
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

sets_evalnodes = config.sets_evalnodes;
num_links = numel(sets_evalnodes);

deltatime = time_params.deltatime;
time_edges = time_params.time_edges;

for n = 1:num_links
	
	figure(fignum+n);
	clf; hold on;
	
	evalnodes = sets_evalnodes{n};
	A = evalnodes(1);
	B = evalnodes(end);

	nodeB_bitpersec = get_goodput(perform(n).nodeB_rx_data_goodcrc_unique_timestamps, ...
	                              perform(n).nodeB_rx_data_goodcrc_unique_messagelengths, ...
                                  deltatime, time_edges);
							  
	[xx,yy] = stairs(time_edges, nodeB_bitpersec/1e3);
	plot(xx(1:end-1),yy(1:end-1),'b','LineWidth',2);

	nodeA_bitpersec = get_goodput(perform(n).nodeA_rx_data_goodcrc_unique_timestamps, ...
	                              perform(n).nodeA_rx_data_goodcrc_unique_messagelengths, ...
                                  deltatime, time_edges);
							  
	[xx,yy] = stairs(time_edges, nodeA_bitpersec/1e3);
	plot(xx(1:end-1),yy(1:end-1),'g-.','LineWidth',2);
	
	nodeAB_bitpersec = nodeA_bitpersec + nodeB_bitpersec;
	[xx,yy] = stairs(time_edges, nodeAB_bitpersec/1e3);
	plot(xx(1:end-1),yy(1:end-1),'r','LineWidth',2);
	
	xlabel('Time (s)');
	ylabel('Throughput (kb/s)');
	legend(sprintf('%i->%i',A,B),sprintf('%i->%i',B,A),sprintf('%i<=>%i',A,B))
	title(sprintf('Throughput between node %i and node %i',A,B));
	box on
	
	perform(n).nodeA_bitpersec  = nodeA_bitpersec;
	perform(n).nodeB_bitpersec  = nodeB_bitpersec;
	perform(n).nodeAB_bitpersec = nodeAB_bitpersec;
	
	evalTimeRangeUpdated = save_params.evalTimeRangeUpdated;
	result_path = config.result_path;
	filename = sprintf('goodput_node%iand%i',A,B);
	qlfiletype = 'png';
	SAVERESULTS = save_params.SAVERESULTS;
	
	save_fig_with_quicklook(fignum+n,evalTimeRangeUpdated,result_path,filename,qlfiletype,SAVERESULTS)
	
end