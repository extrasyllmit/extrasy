function evaluate_tdma_single_test_node(logs_path,node_xml)
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
addpath('./xml_toolbox');

%parse xml file
parse_success = parse_all_nodes(logs_path, node_xml, Inf, 0);
if parse_success == 0
	error('Failed to parse Trial %i\n',tt);
end
fprintf('Finished parsing %s\n\n',node_xml{1});

%load node_log.mat from parsing result above
matFileName = fullfile(logs_path, 'node_log.mat');
load(matFileName);

%hardcode here: replicate to 2 nodes
node_log = [node_log node_log];

num_nodes = numel(node_log);

%define packet code
PKTCODE.BC = 1;
PKTCODE.DATA = 2;

%%
inittime = Inf;
for n = 1:num_nodes
	inittime = min(str2double(node_log{n}(1).timestamp), inittime);
end

endtime = -1;
for n = 1:num_nodes
	endtime = max(str2double(node_log{n}(end).timestamp), endtime);
end

deltatime = 5; %0.25; %seconds
time_edges = (0:deltatime:endtime-inittime+deltatime);

time_params.inittime = inittime;
time_params.endtime = endtime;
time_params.deltatime = deltatime;
time_params.time_edges = time_edges;


%% extract and draw raw traffic pattern
config.node_ID = [2 3];  %hardcode here
fignum = 30;
save_params.SAVERESULTS = 0;
plot_tdma_traffic(node_log, config, PKTCODE, time_params, fignum, save_params);
