function [AGNT] = agentStateTransitionMatrix(ENV,AGNT)
% Computes the agent's state transition matrix

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

% Use the agent's sensor to compute the agent's state transition
% probability matrix from the environment state transition probability
% matrix
AGNT.P = cell(AGNT.numActions,1);

for aa = 1:AGNT.numActions
    
    AGNT.P{aa} = sparse(AGNT.numStates,AGNT.numStates);
    
    for envCurrentState = 1:ENV.numStates
        
        agentCurrentState = AGNT.stateSensorFunction(envCurrentState);
        envNextState = find(ENV.P{aa}(envCurrentState,:));
        
        for ss = 1:numel(envNextState)
            
            agentNextState = AGNT.stateSensorFunction(envNextState(ss));
            
            % Transfer the probability from the environment's matrix to the agent's matrix
            AGNT.P{aa}(agentCurrentState,agentNextState) = AGNT.P{aa}(agentCurrentState,agentNextState) + ...
                                                           ENV.P{aa}(envCurrentState,envNextState(ss));
        end
        
    end
    
    % Normalize the matrix so that it is stochastic
    AGNT.P{aa} = AGNT.P{aa} ./ ( sum(AGNT.P{aa},2) * ones(1,AGNT.numStates) );
    
end
