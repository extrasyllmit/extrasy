function alltimestamps_num = get_timestamps(node_log)
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
if isempty(node_log)
	alltimestamps_num = [];
	return
end

%get to validate filtered results
[~, alltimestamps] = xml_arraygetfields(node_log,{'timestamp'});
if isempty(alltimestamps)
	alltimestamps_num = [];
else
	alltimestamps_num = cellfun(@str2num,alltimestamps,'UniformOutput',true);
end