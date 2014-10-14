function [unreachableStates,terminalStates] = findSpecialStates(P)
% Finds states that are terminal or unreachable

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

% Find terminal and unreachable states
% Terminal states have transitions to themselves.

if iscell(P)
    Pall = zeros(size(P{1}));
    for ii = 1:numel(P)
        Pall = Pall + P{ii};
    end
    unreachableStates = find(sum(Pall,1) == 0);
    terminalStates = find(diag(Pall) == numel(P));
else
    unreachableStates = find(sum(P,1) == 0);
    terminalStates = find(diag(P) == 1);
end
