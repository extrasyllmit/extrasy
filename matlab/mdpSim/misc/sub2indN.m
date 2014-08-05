function ind = sub2indN(siz,subN)
% Like sub2ind but takes a single array arguement whose Nth row holds the
% subscript indices to the Nth dimensions 
% 
% EXAMPLE: the linear indices of the diagonal elements of a 2x3x4 element are
% 
%    ind = sub2indN([2,3,4],[[1 2 1 2 1 2 1 2];[1 2 1 2 1 2 1 2];[1 1 2 2 3 3 4 4]])
%    ind =
%          1     4     7    10    13    16    19    22
% 

% Copyright 2013-2014 Massachusetts Institute of Technology
% $Revision: alpha
% Revised 2014-02-25
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

tmp = mat2cell(subN,ones(1,size(subN,1)));
ind = sub2ind(siz,tmp{:});
