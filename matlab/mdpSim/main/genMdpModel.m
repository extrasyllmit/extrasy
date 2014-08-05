function [ENV,AGNT] = genMdpModel(ENV)
% Generates the environment model and agent model

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

switch ENV.USR.modelForP % State transition model for the environment
    
    case 'extrasy2network'
        
        % Define a matrix whose elements are the bidirectional network state as a function of the 
        % environment state (rows) and agent network action (columns).
        ENV.USR.networkStateMatrix = [...    
            [2 0 1];...
            [0 0 2];...
            [1 2 0]];
        
        % The manifold is a lookup table. First column is the network state. Second column is the corresponding reward
        ENV.USR.rewardManifold = [[0 1 2]' [-100 -10 10]'];
        ENV.USR.environmentActions = [1 2 3];
        ENV.USR.startStateIndex = [];
        ENV.USR.stopStateIndex = [];
        
        AGNT.USR.actionSet = [1 2 3];
        AGNT.USR.stateSensorModel = 'networkStateAndComAction';

        AGNT.numActions = numel(AGNT.USR.actionSet);
        [ENV,AGNT] = networkTransitions(ENV,AGNT);
        ENV.gridDims = [AGNT.numActions ENV.numStates/AGNT.numActions];
        
                
    case 'mineSweeper'  % etch-a-sketch through a grid-world with cross-moves, an initial state, and multiple termonal states
        
        ENV.USR.rewardManifold = ...
            [[  -1,  -1,  -1,  -1,  -1,  -1,-100,-100,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1];...
            [  -1,  -1,  -1,  -1,-100,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1];...
            [  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,-100,-100,-100,  -1,  -1,  -1,  -1,  -1];...
            [  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  10,  -1,  -1,  -1,  -1,  -1,  -1]];
        ENV.USR.windVector = {};

        AGNT.USR.stateSensorModel = 'perfectlyObservable';
        AGNT.USR.gridMoveType = 'cross4';
     
        ENV.gridDims = size(ENV.USR.rewardManifold);
        ENV.numStates = prod(ENV.gridDims);
        ENV.stateWords = (1:ENV.numStates).';
        
        ENV.USR.startStateIndex = sub2ind(ENV.gridDims,1,2);
        ENV.USR.stopStateIndex = sub2ind(ENV.gridDims,[1,1,2,3,3,3,4],[7,8,5,9,10,11,10]);
        
        [ENV.P,AGNT.numActions,AGNT.USR.actionSet,AGNT.invalidActions] = gridworldTransitions(ENV,AGNT,ENV.USR.windVector);
                
       
    case 'deterministicWindyGridworld'
        
        ENV.USR.rewardManifold = -ones(7,10); % Reward is -1 everywhere except the episode's stop state.
        ENV.USR.rewardManifold(53) = 0; % the stopping reward was not specified in Sutton & Barto
        
        ENV.gridDims = size(ENV.USR.rewardManifold);
        ENV.numStates = prod(ENV.gridDims);
        ENV.stateWords = (1:ENV.numStates).';


        % one row per grid dimension. pos for up, 0, or neg for down
        ENV.USR.windVector = {{vec(repmat(-[0 0 0 1 1 1 2 2 1 0],[ENV.gridDims(1),1])).'   ; zeros(1,prod(ENV.gridDims))}};
        ENV.USR.startStateIndex = sub2ind(ENV.gridDims,4,1);
        ENV.USR.stopStateIndex = sub2ind(ENV.gridDims,4,8);

        AGNT.USR.stateSensorModel = 'perfectlyObservable';
        AGNT.USR.gridMoveType = 'cross4';

        Ptmp = cell(numel(ENV.USR.windVector),1);
        for ww = 1:numel(ENV.USR.windVector)
            [Ptmp{ww},AGNT.numActions,AGNT.USR.actionSet,IAtmp] = gridworldTransitions(ENV,AGNT,ENV.USR.windVector{ww});
            if ww == 1; AGNT.invalidActions = false(size(IAtmp)); end
            AGNT.invalidActions = AGNT.invalidActions | IAtmp;
        end
        ENV.P = cell(size(Ptmp{1}));
        for aa = 1:numel(Ptmp{1})
            ENV.P{aa} = zeros(size(Ptmp{ww}{1}));
            for ww = 1:numel(ENV.USR.windVector)
                ENV.P{aa} = ENV.P{aa} + Ptmp{ww}{aa}/numel(ENV.USR.windVector);
            end
        end
        
    case 'stochasticWindyGridworld'
        ENV.USR.rewardManifold = -ones(7,10); % Reward is -1 everywhere except the episode's stop state.
        ENV.USR.rewardManifold(53) = 0; % the stopping reward was not specified in Sutton & Barto
        
        ENV.gridDims = size(ENV.USR.rewardManifold);
        ENV.numStates = prod(ENV.gridDims);
        ENV.stateWords = (1:ENV.numStates).';
        

        % one row per grid dimension. pos for up, 0, or neg for down
        ENV.USR.windVector = {{vec(repmat(-[0 0 0 1 1 1 2 2 1 0],[ENV.gridDims(1),1])).'   ; zeros(1,prod(ENV.gridDims))};...
                      {vec(repmat(-[0 0 0 1 1 1 2 2 1 0]-1,[ENV.gridDims(1),1])).' ; zeros(1,prod(ENV.gridDims))};...
                      {vec(repmat(-[0 0 0 1 1 1 2 2 1 0]+1,[ENV.gridDims(1),1])).' ; zeros(1,prod(ENV.gridDims))}};
        ENV.USR.startStateIndex = sub2ind(ENV.gridDims,4,1);
        ENV.USR.stopStateIndex = sub2ind(ENV.gridDims,4,8);

        AGNT.USR.gridMoveType = 'cross4';
        AGNT.USR.stateSensorModel = 'perfectlyObservable';

        Ptmp = cell(numel(ENV.USR.windVector),1);
        for ww = 1:numel(ENV.USR.windVector)
            [Ptmp{ww},AGNT.numActions,AGNT.USR.actionSet,IAtmp] = gridworldTransitions(ENV,AGNT,ENV.USR.windVector{ww});
            if ww == 1; AGNT.invalidActions = false(size(IAtmp)); end
            AGNT.invalidActions = AGNT.invalidActions | IAtmp;
        end
        ENV.P = cell(size(Ptmp{1}));
        for aa = 1:numel(Ptmp{1})
            ENV.P{aa} = zeros(size(Ptmp{ww}{1}));
            for ww = 1:numel(ENV.USR.windVector)
                ENV.P{aa} = ENV.P{aa} + Ptmp{ww}{aa}/numel(ENV.USR.windVector);
            end
        end
        
    otherwise
        
        error('Invalid ENV.USR.modelForP specified')
               
end

[AGNT] = agentStateSensorModel(ENV,AGNT);


switch ENV.USR.modelForR
    
    case '3NetworkStates'
        ENV.R = zeros([ENV.numStates,AGNT.numActions]);
        AGNT.R = cell(AGNT.numActions,1);
        for aa = 1:AGNT.numActions
            
            %__ First compute the reward as a function of the environment states and agent actions
            [envCurrentState, envNextState] = find(ENV.P{aa});
            nextNetState = ENV.stateWords(envNextState,1);
            % reward is based on the next state (a reward for arrival)
            % Find the row in the reward manifold that corresponds to the next network state
            [~,manifoldrow] = find(repmat(nextNetState,[1 size(ENV.USR.rewardManifold,1)]) == repmat(ENV.USR.rewardManifold(:,1).',[numel(envNextState) 1]));
            ENV.R(envCurrentState,aa) = ENV.USR.rewardManifold(manifoldrow,2);
            
            %__ Next compute the reward as a function of the agent states and agent actions
            [agentCurrentState, agentNextState] = find(AGNT.P{aa});
            nextNetState = AGNT.stateWords(agentNextState,1);
            % reward is based on the next state (a reward for arrival)
            % Find the row in the reward manifold that corresponds to the next network state
            [~,manifoldrow] = find(repmat(nextNetState,[1 size(ENV.USR.rewardManifold,1)]) == repmat(ENV.USR.rewardManifold(:,1).',[numel(agentNextState) 1]));            
            AGNT.R{aa} = sparse(agentCurrentState, agentNextState, ENV.USR.rewardManifold(manifoldrow,2),AGNT.numStates,AGNT.numStates);
            
        end
        
    case 'deterministicNextState' % reward is based on the next state (a reward for arrival)
        ENV.R = zeros([ENV.numStates,AGNT.numActions]);
        for aa = 1:AGNT.numActions
            [envCurrentState, envNextState] = find(ENV.P{aa});
            ENV.R(envCurrentState,aa) = ENV.USR.rewardManifold(envNextState);
            % This next line causes invalid actions to be learned from receiving -Inf reward.
            % It is not be necessary when Q is initialized with AGNT.invalidActions being -Inf.
        end
        ENV.R(AGNT.invalidActions) = -Inf;
        AGNT.R = ENV.R;
        
    case 'stochasticNextState' % reward is based on the next state (a reward for arrival)
        ENV.R = cell(AGNT.numActions,1);
        for aa = 1:AGNT.numActions
            [envCurrentState, envNextState] = find(ENV.P{aa});
            ENV.R{aa} = sparse(envCurrentState, envNextState, ENV.USR.rewardManifold(envNextState),numel(ENV.USR.rewardManifold),numel(ENV.USR.rewardManifold));
            % This next line causes invalid actions to be learned from receiving -Inf reward.  
            % It is not be necessary when Q is initialized with AGNT.invalidActions being -Inf. 
            ENV.R{aa}(AGNT.invalidActions) = -Inf;
        end
        AGNT.R = ENV.R;
        
end


plotTransProbMatrix(ENV.P,ENV.USR.startStateIndex,'Environment Transition Matrix')
drawnow

plotRewardMatrix(ENV.R,'Environment Reward Model')
drawnow

if ~strcmp(AGNT.USR.stateSensorModel,'perfectlyObservable')
    
    plotTransProbMatrix(AGNT.P,AGNT.stateSensorFunction(ENV.USR.startStateIndex),'Agent Transition Matrix')
    drawnow
    
    plotRewardMatrix(AGNT.R,'Agent Reward Model')
    drawnow
    
end

