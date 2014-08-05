function error_codes = check_timestamps(node_log,max_diff_timestamps)
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
	max_diff_timestamps = 600;
end

num_nodes = numel(node_log);

error_codes = zeros(1,num_nodes);

ref_timestamps = 0;

for n = 1:num_nodes
	timestamps_array = get_timestamps(node_log{n});
	
	if numel(timestamps_array) < numel(node_log{n})
		error_codes(n) = 1;
		%error('proper timestamp(s) missing from some packet logs');
	elseif any(abs(diff(timestamps_array)) > max_diff_timestamps)
		error_codes(n) = 2;
		%error('some timestamp(s) seem to be out of range');
	end
	
	if numel(timestamps_array) > 0
		if (ref_timestamps > 0)
			if abs(timestamps_array(1) - ref_timestamps) > max_diff_timestamps
				error_codes(n) = 3;
			end
		else
			ref_timestamps = timestamps_array(1);
		end
	end
end

