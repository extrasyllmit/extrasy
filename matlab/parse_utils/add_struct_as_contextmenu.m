function add_struct_as_contextmenu(a,figh,alias)
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
% FUNCTIONALITY
% Add a simple structure variable to context menu.  This function can be called
% multiple times to add more than one structure.
%
% If the variable name is the same as one already used, it will replace the
% existing variable without changing the display order.  (useful for
% updates)
%
%
% INPUT
%   a          a structure with one or several fields.
%              each field can be :
%                   - a short row vector of numbers or characters (not column vector)
%                   - a cell array of row vectors of numbers or characters
%                   - another structure with same rules
%              matrix is not supported.  only first row is displayed.
%              top variable can be a structure but not an array
%              sub-level variables can be an array
%
%   figh       optional, existing figure handle
%              default if not specified is current figure
%
%   alias      optional, alternative label instead of using variable name.
%              useful when struct a is passed in from an element of array
%              of structures in which case variable name alone is not usable
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

if isempty(cmh)
	%creat a ui context menu the first time only
	cmh = uicontextmenu;
	%attach it to current figure or figure passed in as argument
	set(figh,'UIContextMenu',cmh)
end

%check if this struct label already exists and delete its data
existed = get(cmh,'Children');
found = 0;

for k = 1:numel(existed)
	existedLabel = get(existed(k),'Label');
	if isequal(existedLabel,var_strg)
		mh1 = existed(k);
		mh1_children = get(mh1,'Children');
		for m = 1:numel(mh1_children)
			delete(mh1_children(m));
		end
		found = 1;
	end
end

if found == 0
	%add structure name as an item to context menu using normal uimenu
	mh1 = uimenu(cmh,'label',var_strg);
end

add_struct_to_menu(mh1,a);

function add_struct_to_menu(hd,a)

allfieldnames = fieldnames(a);
numfn = numel(allfieldnames);

for n = 1:numfn
	fn = allfieldnames{n};
	fv = a.(fn);
	
	if iscell(fv)
		hd2 = uimenu(hd,'label',sprintf('%s = ',fn));
		add_cell_to_menu(hd2,fv);
	elseif isstruct(fv)
		for m = 1:numel(fv)
			if numel(fv) > 1
				hd2 = uimenu(hd,'label',sprintf('%s(%i) = ',fn,m));
			else
				hd2 = uimenu(hd,'label',sprintf('%s = ',fn));
			end
			add_struct_to_menu(hd2,fv(m));
		end
	else
		fv_strg = evalc('fv');
		r_pos = find((fv_strg == 10) | (fv_strg == 13));
		fv_strg(r_pos) = ' ';

		if length(r_pos) >= 3			
			fv_strg_short = fv_strg(r_pos(3)+1:end);
		else % adding this to fix crash
			fv_strg_short = fv_strg(r_pos(2)+1:end);
		end
		
		uimenu(hd,'label',sprintf('%s = %s',fn,fv_strg_short));
	end
end

function add_cell_to_menu(hd,a)

numfn = numel(a);

for n = 1:numfn
	fv = a{n};
	fv_strg = evalc('fv');
	r_pos = find((fv_strg == 10) | (fv_strg == 13));
	
	if length(r_pos) >=4
		fv_strg_short = fv_strg(r_pos(3)+1:r_pos(4)-1);
	else %fixes crash
		fv_strg_short = fv_strg(r_pos(2)+1:end-4);
	end
    
	uimenu(hd,'label',sprintf('{%s}',fv_strg_short));
end