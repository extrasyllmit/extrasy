function [validpackets validstruct] = xml_arraygetfields(v,fieldlist)
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
%%function [validpackets validstruct] = xml_arraygetfields(v,fieldlist)

if ~iscell(fieldlist)
	error('fieldlist must be a cell array');
end

N = numel(v);
numfields = numel(fieldlist);

validpackets = [];
validstruct = [];

if (numfields == 0) || (N == 0)
	return
elseif numfields == 1
	[validpackets validstruct] = xml_arraygetsinglefield(v,fieldlist{1});
	return
else
	for n = 1:N
		[valid,value] = xml_getfield(v(n),fieldlist);
		
		if valid
			validpackets = [validpackets n];
			validstruct = [validstruct {value}]; %convert value to cell
		end
	end
	return
end
