function remove_struct_as_contextmenu(a,figh,alias)
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
% FUNCTIONALITY
% Remove a simple structure variable from context menu.  This function can be called
% multiple times to remove more than one structure.
%
%
% INPUT
%   a          a simple structure (only variable name matter, its content doesn't matter)
%
%   figh       optional, existing figure handle
%              default if not specified is current figure
%
%   alias      optional, alternative label instead of using variable name
%
% Author : Tri Phuong

if nargin < 3
	var_strg = inputname(1);
else
	var_strg = alias;
end

if nargin < 2
	figh = gcf;
end

cmh = get(figh,'UIContextMenu'); 

if ~isempty(cmh)
	%check if this struct label already exists and delete its data
	existed = get(cmh,'Children');

	for k = 1:numel(existed)
		existedLabel = get(existed(k),'Label');
		if isequal(existedLabel,var_strg)
			delete(existed(k));
		end
	end
end

