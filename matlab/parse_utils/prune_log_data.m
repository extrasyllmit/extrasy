function node_log = prune_log_data(node_log, evalTimeRange)
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
timeinfo = get_time_info(node_log);

num_nodes = numel(node_log);

for n = 1:num_nodes	
	[ii_validtimestamp, timestamps] = get_any_id(node_log{n},'timestamp');
	timestamps = timestamps - timeinfo.inittime; %normalize to the same reference init time
	
	ii_test = (timestamps >= evalTimeRange(1)) & (timestamps <= evalTimeRange(2));

	node_log{n} = node_log{n}(ii_validtimestamp(ii_test));
end
