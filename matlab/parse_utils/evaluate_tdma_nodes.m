function perform = evaluate_tdma_nodes(node_log, config, fignum, save_params,PKTCODE)
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

time_params = get_time_info(node_log);

deltatime = 1; %0.25; %seconds
time_edges = (0:deltatime:time_params.endtime-time_params.inittime+deltatime);

time_params.deltatime = deltatime;
time_params.time_edges = time_edges;


%% extract and draw raw traffic pattern
plot_tdma_traffic(node_log, config, PKTCODE, time_params, fignum, save_params);

%% characterize intermediate performance
perform = plot_tdma_intermediate_performance(node_log, config, PKTCODE, time_params, fignum+10, save_params);

%% plot final goodput
perform = plot_tdma_goodput(perform, config, time_params, fignum+20, save_params);

%% plot overview
perform = plot_overview_results(perform, config, time_params, fignum+30, save_params);

%% save mat results
evalTimeRangeUpdated = save_params.evalTimeRangeUpdated;
result_path = config.result_path;
filename = sprintf('time%ito%is_results',round(evalTimeRangeUpdated));
SAVERESULTS = save_params.SAVERESULTS;

if SAVERESULTS
	longFileName = fullfile(result_path, [filename '.mat']);
	if exist(longFileName,'file'), delete(longFileName); end
	save(longFileName,'perform','config','time_params');
end