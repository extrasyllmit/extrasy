function [ENV,AGNT] = networkTransitions(ENV,AGNT)
% Generates a radio network transition matrix

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

AGNT.networkStateSet = unique(ENV.USR.networkStateMatrix(:)); % the possible network state symbols
ENV.environmentActionset = unique(ENV.USR.environmentActions(:)); % the possible environment actions symbols

ENV.stateWords = countMultiBase({AGNT.networkStateSet AGNT.USR.actionSet ENV.environmentActionset});
ENV.numStates = size(ENV.stateWords,1);
ENV.stateWordColumnLabels = {'networkState';'networkAction';'environmentAction'};

% compute a environment state transition matrix for all possible actions for fully observable states
ENV.P = cell(AGNT.numActions,1);
for aa = 1:AGNT.numActions
    
    ENV.P{aa} = sparse(ENV.numStates,ENV.numStates);
    
    for currentEnvironmentStateIndex = 1:ENV.numStates
        
        currentEnvironmentState = ENV.stateWords(currentEnvironmentStateIndex,:);
        
        switch ENV.USR.environmentModel
            case 'random'
                % The environment selects a action for a given agent action the mapping of environment to agent actions is randomly assigned.
                nextEnvironmentAction = randi(numel(ENV.USR.environmentActions),1);

            case 'sequential'
                % The environment steps (deterministically) through a sequence of actions and then repeats.
                currentEnvironmentAction = find(currentEnvironmentState(3) == ENV.USR.environmentActions);
                nextEnvironmentAction = ENV.USR.environmentActions(mod(currentEnvironmentAction,numel(ENV.USR.environmentActions))+1);
                
            otherwise
                error('The ENV.USR.environmentModel specified was not valid')
        end
        
        nextNetworkAction = aa;
        nextNetworkState = ENV.USR.networkStateMatrix(nextEnvironmentAction,nextNetworkAction);
        nextStateIndex = find((ENV.stateWords(:,1) == nextNetworkState) & (ENV.stateWords(:,2) == nextNetworkAction) & (ENV.stateWords(:,3) == nextEnvironmentAction));
        
        ENV.P{aa}(currentEnvironmentStateIndex,nextStateIndex) = 1;
        
    end
    
end

AGNT.invalidActions = false(0);
