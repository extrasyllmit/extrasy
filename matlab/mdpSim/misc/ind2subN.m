function subN = ind2subN(siz,ind)
% Like ind2sub but produces a single array whose Nth row holds the
% subscript indices to the Nth dimensions
% 
% EXAMPLE: the subscript indices of the diagonal elements of a 2x3x4 element are
% 
% ind = ind2subN([2,3,4], [1 4 7 10 13 16 19 22])
% 
% ind =
%      1     2     1     2     1     2     1     2
%      1     2     1     2     1     2     1     2
%      1     1     2     2     3     3     4     4
% 

% Copyright 2013-2014 Massachusetts Institute of Technology
% $Revision: alpha
% Revised 2014-02-25
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

[tmp{1:length(siz),1}] = ind2sub(siz,ind);
subN = cell2mat(tmp);

