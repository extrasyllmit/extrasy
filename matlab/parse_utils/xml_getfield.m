function [check, field] = xml_getfield(x,fieldlist)
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
%function to check if a field of another field exists and is not empty
%   input x is a nested structure of structures
%   output check is 1 or 0 for true or false
%   output field is the retrieved field values, [] if invalid
%for example,
%   xml_isfield_and_notempty(some_structure,{'world'})
%   xml_isfield_and_notempty(some_structure,{'world','country'})
%   xml_isfield_and_notempty(some_structure,{'world','country','city'})

numfields = length(fieldlist);

fieldtocheck = fieldlist{1}; %string
	
field = [];

if isfield(x,fieldtocheck)
	f = x.(fieldtocheck);
	if ~isempty(f)
		if numfields==1
			check = 1; %last field passed test
			field = f;
		else
			[check, field] = xml_getfield(f,fieldlist(2:end)); %varargin(2:end) is cell array
		end
	else
		check = 0;
		field = [];
	end
else
	check = 0;
	field = [];
end
	