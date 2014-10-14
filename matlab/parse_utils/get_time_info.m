function timeinfo = get_time_info(node_log)
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
num_nodes = numel(node_log);

inittime = Inf;
for n = 1:num_nodes
	if numel(node_log{n}) > 0
		inittime = min(str2double(node_log{n}(1).timestamp), inittime);
	end
end

timeinfo.inittime = inittime;

endtime = -1;
for n = 1:num_nodes
	if numel(node_log{n}) > 0
		endtime = max(str2double(node_log{n}(end).timestamp), endtime);
	end
end

timeinfo.endtime = endtime;

