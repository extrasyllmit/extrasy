function [AGNT] = agentStateSensorModel(ENV,AGNT)
% Defines the agent's state sensor model

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

switch AGNT.USR.stateSensorModel
    
    case 'perfectlyObservable' % The state is perfectly observable (though the environment is not fully observable)
        
        AGNT.stateWords = ENV.stateWords;
        AGNT.numStates = size(AGNT.stateWords,1);
        AGNT.stateSensorFunction = (1:ENV.numStates).';
        
    case 'networkStateAndComAction'
        % The agent is only able to partially observe the environment's state
        % We need to define a mapping of environment states to agent states
        
        AGNT.stateWords = countMultiBase({AGNT.networkStateSet AGNT.USR.actionSet});
        AGNT.numStates = size(AGNT.stateWords,1);
        AGNT.stateWordColumnLabels = ENV.stateWordColumnLabels(1:2);
        
        AGNT.stateSensorFunction = zeros(ENV.numStates,1);
        
        for ii = 1:ENV.numStates % Each environment state corresponds to one agent state
            AGNT.stateSensorFunction(ii) = find(all(repmat(ENV.stateWords(ii,1:2), [AGNT.numStates 1]) == AGNT.stateWords,2));
        end
        
    otherwise
        error('Value specified for AGNT.USR.stateSensorModel is not valid.')

end

% Compute the agent's state transition matrix as perceived by the sensor 
AGNT = agentStateTransitionMatrix(ENV,AGNT);
AGNT.gridDims = [1 AGNT.numStates];
