function p = unwrap_packet_id(p,maxNum)
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
%unwrap id with range from 0..maxNum-1 or 0..2^16-1 as default

if nargin < 2
	maxNum = 2^16;
end

if (numel(p) == 0) || (numel(p) == 1)
	return
else
	half_max = round(maxNum/2);

	add_on = cumsum(double(diff(p) < -half_max))*maxNum;

	p(2:end) = p(2:end) + add_on;
end
