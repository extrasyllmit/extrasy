function [ii, num] = get_any_id(node_log,id)
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
if isempty(node_log)
	ii = [];
	num = [];
	return
end

%get to validate filtered results
[ii, cellarray1] = xml_arraygetfields(node_log,{id});
if isempty(cellarray1)
	ii = [];
	num = [];
else
	num = cellfun(@str2double,cellarray1,'UniformOutput',true);
end