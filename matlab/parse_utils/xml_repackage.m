function w = xml_repackage(u)
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
if (numel(u) == 1) && ~iscell(u)
	v{1} = u;
else
	v = u;
end

w = [];

for m = 1:numel(v)
	%fprintf('Processing cell elememt #%i\n',m)
	fields = fieldnames(v{m});
	for n = 1:numel(fields)
		%fprintf('Processing field elememt #%i\n',n)
		currentfield = fields{n};
		if  ~isequal(currentfield,'ATTRIBUTE')
			%temp = getfield(v{m},currentfield);
			temp = v{m}.(currentfield);
			%disp(temp{1})
			if isfield(temp{1},'CONTENT')
				%w = setfield(w,{m},currentfield,temp{1}.CONTENT);
				w(m).(currentfield) = temp{1}.CONTENT;
			else
				%fprintf('CONTENT not found in cell#%i and field#%i.  Entering recursive call.\n',m,n);
				temp2 = xml_repackage(temp);
				%fprintf('Returned from recursive call.\n');
				%disp(temp2)
				w(m).(currentfield) = temp2;
			end
		end
	end
end
