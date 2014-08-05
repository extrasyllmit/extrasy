function [P,numActions,actionSet,invalidActions] = gridworldTransitions(ENV,AGNT,windVector)
% Generates a gridworld transition matrix

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

if isempty(windVector)
    windVector = cell(numel(ENV.gridDims),1);
    for dd = 1:numel(ENV.gridDims)
        windVector{dd} = 0;
    end
end
    
switch AGNT.USR.gridMoveType
    % First dimension is rows on the gridworld. Second dimension is columns on the gridworld
    case 'king' % "Kings Moves": Three actions per dimension:  0=nochange, 1=increment, -1=decrement,
        actionSet = countMultiBase(3*ones(numel(ENV.gridDims),1))-1; % enumerate the actions (one action per row, one column per dimension). 3^D actions for D dimensions
    case 'cross5' % "Cross Moves" 5 moves including no-move: Three actions per dimension:  0=nochange, 1=increment, -1=decrement,
        actionSet = countMultiBase(3*ones(numel(ENV.gridDims),1))-1; % enumerate the actions (one action per row, one column per dimension). 3^D actions for D dimensions
        mask = sum(abs(actionSet),2) <= 1;
        actionSet = actionSet(mask,:);
    case 'cross4' % "Cross Moves" with 4 moves: Three actions per dimension: 1=increment, -1=decrement,
        actionSet = countMultiBase(3*ones(numel(ENV.gridDims),1))-1; % enumerate the actions (one action per row, one column per dimension). 3^D actions for D dimensions
        mask = sum(abs(actionSet),2) <= 1;
        mask(all(actionSet == 0,2)) = false; % don't allow the no-move action
        actionSet = actionSet(mask,:);
    otherwise
        error('WARNING: Invalid AGNT.USR.gridMoveType Specified')
end
numActions = size(actionSet,1);
P = cell(numActions,1);

currStateSubs = ind2subN(ENV.gridDims,1:ENV.numStates); % the n'th row contains the subscript indices for all states in the n'th dimension
nextStateSubs = zeros(size(currStateSubs));
invalidActions = false(ENV.numStates,numActions); % actions that cause the next state to be out of bounds
for aa = 1:numActions
    
    for dd = 1:numel(ENV.gridDims)
        % let the action manipulate the subscript
        % the wind value applied to the action is that of the current state (not the next state). i.e. a departure wind
        nextStateSubs(dd,:) = currStateSubs(dd,:) + actionSet(aa,dd) + windVector{dd}; 
        outOfBoundMask = nextStateSubs(dd,:) > ENV.gridDims(dd);
        nextStateSubs(dd,outOfBoundMask) = ENV.gridDims(dd); % upper bound the subscripts to the valid range
        invalidActions(outOfBoundMask,aa) = true;
    end
    outOfBoundMask = nextStateSubs < 1;
    nextStateSubs(outOfBoundMask) = 1; % lower bound the subscripts to the valid range
    invalidActions(any(outOfBoundMask,1),aa) = true;
    
    nextStateIndx = sub2indN(ENV.gridDims,nextStateSubs);
    P{aa} = sparse(1:ENV.numStates,nextStateIndx,ones(ENV.numStates,1),ENV.numStates,ENV.numStates);

    % Create terminal states for indeterminite horizon episodic MDP's (e.g. minsweeper problem)
    if ~isempty([ENV.USR.startStateIndex(:); ENV.USR.stopStateIndex(:)]);
       P{aa}(ENV.USR.stopStateIndex,:) = 0; % overwrite any transitions out of the terminal states
%        P{aa}(ENV.USR.stopStateIndex(:),ENV.USR.startStateIndex*ones(numel(ENV.USR.stopStateIndex),1)) = 1; % force transitions from terminal states to the initial state
       P{aa}(sub2ind([ENV.numStates ENV.numStates],ENV.USR.stopStateIndex(:),ENV.USR.stopStateIndex(:))) = 1; % force terminal states to be absorbing
    end

end
invalidActions = sparse(invalidActions);

% invalidActions are a mechanism for (a) letting the agent learn the
% boundaries of the grid or (b) tweaking the gridworld
% I am disabling them because they are a legacy capability
fprintf('\n%s\n','   COMMENT: Invalid Actions are disabled')
invalidActions = false(0);
