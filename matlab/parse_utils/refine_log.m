function ii_refined = refine_log(node_log,field,fieldvalue)
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
%%function ii_refined = refine_log(node_log,field,fieldvalue)

if isempty(node_log)
	ii_refined = [];
	return
end

if isnumeric(fieldvalue)
	[ii, allcells] = xml_arraygetfields(node_log,{field});
	allnums = cellfun(@str2double,allcells,'UniformOutput',true);
	ii_matched = find(allnums==fieldvalue);
	ii_refined = ii(ii_matched);
elseif ischar(fieldvalue)
	fieldvalue = lower(fieldvalue);
	[ii, allcells] = xml_arraygetfields(node_log,{field});
	matched = cellfun(@(x) isequal(lower(x),fieldvalue),allcells,'UniformOutput',true);
	ii_matched = find(matched);
	ii_refined = ii(ii_matched);	
else
	error('unknown type of fieldvalue');
end

