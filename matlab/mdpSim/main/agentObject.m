function [AGNT,ENV,STAT] = agentObject(AGNT,ENV,STAT)
% Defines the agent's state machine and executes the current state

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

switch AGNT.agentObjectState
    
    case 'initialize'
        
        if strcmp(AGNT.USR.alphaVal,'constant')
             % See Sigaud and Buffet p51
             disp('   WARNING:   alpha is constant => learning may not converge')
        end
        if AGNT.USR.gammaVal < 1 && isempty(ENV.USR.stopStateIndex)
             % See Sigaud and Buffet p51
             disp('   WARNING:   gamma is < 1 and there is no absorbing state => learning may not converge')
        end
                
        AGNT.agentObjectState = 'newTrial';

    case 'newTrial'
        
        if ~isempty(AGNT.USR.Qseed);
            AGNT.Q = AGNT.USR.Qseed;
        else
            AGNT.Q = rand(AGNT.numStates,AGNT.numActions)*eps; % initialize to very small number instead of 0 (avoids ties)
        end;
        
        if ~isempty(AGNT.invalidActions)
            AGNT.Q(logical(AGNT.invalidActions)) = -Inf; % prevents invalid actions from being chosen
            AGNT.validActions = cell(1,AGNT.numStates);
            for ss = 1:AGNT.numStates
                AGNT.validActions{ss} = find(~AGNT.invalidActions(ss,:)); % precomputed for speed
            end
        else % all actions are valid
            AGNT.validActions = cell(1,AGNT.numStates);
            for ss = 1:AGNT.numStates
                AGNT.validActions{ss} = 1:AGNT.numActions; % precomputed for speed
            end
        end;
        
        % Initialize the visitation count matrix
        AGNT.stateActionVisitCount = zeros(AGNT.numStates,AGNT.numActions);
        
        % Initialize the learning rate variables
        AGNT.alphaVal = AGNT.USR.alphaVal;
        AGNT.alphaMtrx = AGNT.USR.alphaVal*ones(size(AGNT.Q));
        
        % Initialize the exploration renewal buffers
        if AGNT.USR.renewableExploration == 1
            AGNT.rewardBufferOld = nan(AGNT.numStates,AGNT.numActions,AGNT.USR.rewardBufferDepth);
            AGNT.rewardBufferNew = nan(AGNT.numStates,AGNT.numActions,AGNT.USR.rewardBufferDepth);
        end
        
        % initialize the eligibility trace matrix
        if AGNT.USR.lambdaVal > 0
            AGNT.eTrace = zeros(size(AGNT.Q));
        else
            AGNT.eTrace = [];
        end
        
        if isempty(AGNT.USR.policyOpt)
            AGNT.USR.policyOpt = [];
        end
        
        if ~isfield(AGNT,'vOpt')
            AGNT.USR.vOpt = [];
        end

        % Initialize the agent's internal time counters
        AGNT.ii_epoch = 1;
        AGNT.ii_episode = 0;

        AGNT.agentObjectState = 'begin';
        
    case 'begin'
        
        % Update the agent's internal episode counter
        AGNT.ii_episode = AGNT.ii_episode + 1;

        % Let the agent estimate the initial state from the environment
        [AGNT.s] = agentStateSensor(AGNT,ENV.s);

        if strcmp(AGNT.USR.algorithm,'SARSA');
            % SRASA requires that the first action be initialized before an episode or trial begins
            [AGNT.a,AGNT.wasExplore,AGNT.epsVal] = chooseAction(AGNT.s,AGNT);
        end
        
        AGNT.agentObjectState = 'step';
        
    case 'step'
        
        % Update the agent's internal epoch counter
        AGNT.ii_epoch = AGNT.ii_epoch + 1;

        switch AGNT.USR.algorithm
            case 'Q-learn'
                [AGNT,ENV,STAT] = qLearnUpdate(AGNT,ENV,STAT);
            case 'SARSA'
                [AGNT,ENV,STAT] = sarsaUpdate(AGNT,ENV,STAT);
            otherwise
                error('Invalid AGNT.USR.algorithm')
        end
        
        AGNT.agentObjectState = 'step';
        
    case 'finish'
        
        % Compute the learned reward and policy
        [AGNT.V, AGNT.policy] = max(AGNT.Q,[],2);
        
        AGNT.agentObjectState = 'done';

end

end % function



%    _______________
% __/ SUB-FUNCTIONS \__________________________________________________________________
% References
% ----------------------------------------------------------------------------------------------
% [1] R. S. Sutton and A. G. Barto, "Reinforcement Learning," The MIT Press, 1998
% [2] O. Sigaud and O. Buffet, "Markov Decision Processes in Artificial Intelligence," Wiley, 2010
% [3] S. P. Singh, T. Jaakkola, M. L. Littman, and C. Szepesvari, "Convergence Results for Single-Step 
%     On-Policy Reinforcement Learning Algorithms," Machine Learning, vol. 38, no. 3, pp. 287-308, 2000.

function [AGNT,ENV,STAT] = qLearnUpdate(AGNT,ENV,STAT)
% Q-learning step for updating the Q-function (see Sutton and Barto 1998, Sigaud and Buffet 2010)

% The agent selects an action from its current state
[AGNT.a,AGNT.wasExplore,AGNT.epsVal] = chooseAction(AGNT.s,AGNT);

AGNT.stateActionVisitCount(AGNT.s,AGNT.a) = AGNT.stateActionVisitCount(AGNT.s,AGNT.a) + 1;
ENV.stateActionVisitCount(ENV.s,AGNT.a) = ENV.stateActionVisitCount(ENV.s,AGNT.a) + 1;

% Generate the next environment state using the selected action (i.e. execute the action)
if ENV.iscellP
    ENV.sNext = find( rand(1) < ENV.cumsumP{AGNT.a}(ENV.s,:), 1, 'first');
else
    ENV.sNext = find( rand(1) < ENV.cumsumP(ENV.s,:,AGNT.a), 1, 'first');
end;

% Let the agent estimate the next state
[sNext] = agentStateSensor(AGNT,ENV.sNext);

% Alow the agent to retrieve the reward
if ENV.iscellR
    AGNT.r = ENV.R{AGNT.a}(ENV.s,ENV.sNext); % Reward is stochastic
else
    AGNT.r = ENV.R(ENV.s,AGNT.a); % Reward is deterministic
end

% Allow the agent to update it's exploration policy parameters
[AGNT] = updateExplorationParams(AGNT);

if any(ENV.sNext == ENV.USR.stopStateIndex)
    qNext = 0; % This may not be needed for Q-learning like it is for SARSA (see Sutton & Barto pg. 145)
    % The use of this terminal update in the minesweeper task did not affect the outcome of Q-learning
else
    qNext = max(AGNT.Q(sNext,:));
end

% Compute the learning rate parameter
[AGNT] = getAlpha(AGNT);

% Update the value function
delta = AGNT.r + AGNT.USR.gammaVal*qNext - AGNT.Q(AGNT.s,AGNT.a); % NOTE: we could add eps*rand(1,AGNT.numActions) to the arguement of max() to break ties
AGNT.Q(AGNT.s,AGNT.a) = AGNT.Q(AGNT.s,AGNT.a) + AGNT.alphaVal*delta;

% Update the simulation statistics for this epoch
STAT.statObjectState = 'step';
[STAT] = statObject(ENV,AGNT,STAT);

ENV.s = ENV.sNext;
AGNT.s = sNext;

end % function



function [AGNT,ENV,STAT] = sarsaUpdate(AGNT,ENV,STAT)
% SARSA step for updating the Q-function (see Sutton and Barto 1998, Sigaud and Buffet 2010)

AGNT.stateActionVisitCount(AGNT.s,AGNT.a) = AGNT.stateActionVisitCount(AGNT.s,AGNT.a) + 1;
ENV.stateActionVisitCount(ENV.s,AGNT.a) = ENV.stateActionVisitCount(ENV.s,AGNT.a) + 1;

% Generate the next environment state using the selected action (i.e. execute the action)
if ENV.iscellP
    ENV.sNext = find( rand(1) < ENV.cumsumP{AGNT.a}(ENV.s,:), 1, 'first');
else
    ENV.sNext = find( rand(1) < ENV.cumsumP(ENV.s,:,AGNT.a), 1, 'first');
end;

% Let the agent estimate the next state
[sNext] = agentStateSensor(AGNT,ENV.sNext);

% Alow the agent to retrieve the reward
if ENV.iscellR
    AGNT.r = ENV.R{AGNT.a}(ENV.s,ENV.sNext); % Reward is stochastic
else
    AGNT.r = ENV.R(ENV.s,AGNT.a); % Reward is deterministic
end;

% Allow the agent to update it's exploration policy parameters
[AGNT] = updateExplorationParams(AGNT);

% The agent selects the next action from its next state
[aNext,wasExploreNext,epsValNext] = chooseAction(sNext,AGNT);

if any(ENV.sNext == ENV.USR.stopStateIndex)
    AGNT.Q(sNext,aNext) = 0; % see Sutton & Barto pg. 145
end

% Compute the learning rate parameter
[AGNT] = getAlpha(AGNT);

% Update the value function
delta = AGNT.r + AGNT.USR.gammaVal*AGNT.Q(sNext,aNext) - AGNT.Q(AGNT.s,AGNT.a);
if AGNT.USR.lambdaVal > 0 % use eligibility trace
    AGNT.eTrace(AGNT.s,AGNT.a) = AGNT.eTrace(AGNT.s,AGNT.a)+1; % extend the trace
    AGNT.Q = AGNT.Q + AGNT.alphaMtrx.*AGNT.eTrace.*delta;
    AGNT.eTrace = AGNT.USR.lambdaVal*AGNT.USR.gammaVal*AGNT.eTrace; % decay the trace for the next epoch
else
    AGNT.Q(AGNT.s,AGNT.a) = AGNT.Q(AGNT.s,AGNT.a) + AGNT.alphaVal*delta;
end

% Update the simulation statistics for this epoch
STAT.statObjectState = 'step';
[STAT] = statObject(ENV,AGNT,STAT);

ENV.s = ENV.sNext;
AGNT.s = sNext;
AGNT.a = aNext;
AGNT.wasExplore = wasExploreNext;
AGNT.epsVal = epsValNext;

end % function



function [AGNT] = getAlpha(AGNT)

switch AGNT.USR.alphaPolicy
    case 'constant'
        % AGNT.alphaMtrx remains unchanged from it's initial assignment
        % AGNT.alphaVal remains unchanged from it's initial assignment
    case 'visitThreshold' 
        % Setting AGNT.USR.alphaVal = 1 and AGNT.USR.alphaVisitThreshold = -1 
        % results in the definition how to decay the learning rate proposed by Sigaud and Buffet, p51.
        if AGNT.stateActionVisitCount(AGNT.s,AGNT.a) > AGNT.USR.alphaVisitThreshold
            AGNT.alphaMtrx(AGNT.s,AGNT.a) = AGNT.USR.alphaVal./max([1 AGNT.stateActionVisitCount(AGNT.s,AGNT.a)]);
            AGNT.alphaVal = AGNT.alphaMtrx(AGNT.s,AGNT.a);
        end
    otherwise
        error('Invalid AGNT.USR.alphaPolicy')
end

end % function



function [a,wasExplore,epsVal] = chooseAction(s,AGNT)
% Select an action to execute while in the current state acording to some exploration/exploitation strategy

% NOTE: the input state parameter, s, needs to be it's own input rather
% than passed as part of AGNT.s because sometimes s = sNext and other times s = AGNT.s

% compute the reward maximizing action (doesn't mean this action will be used)
[~,exploitAction] = max(AGNT.Q(s,:)); % invalid actions likely not chosen b/c they are initialized to -Inf
                                 % NOTE: we could add eps*rand(1,AGNT.numActions) to the arguement of max() to break ties
exploreActions = setdiff(AGNT.validActions{s},exploitAction);

if numel(exploreActions) >  1 % check if there is a choice of actions
    
    switch AGNT.USR.epsPolicy
        case 'constant'
            epsVal = AGNT.USR.epsVal;
            [a,wasExplore] = loreloit(epsVal,exploitAction,exploreActions);
        case 'timeFast' % Prob(exploration) approaches 0 as the number of epochs approaches infinity
            % Use a faster decaying function for episodic tasks
            epsVal = AGNT.USR.epsVal/AGNT.ii_episode; % Decreasing the base of the logarithm will accelerate the shift from explore to exploit
            [a,wasExplore] = loreloit(epsVal,exploitAction,exploreActions);
        case 'timeSlow' % Prob(exploration) approaches 0 as the number of epochs approaches infinity
            % Use a slower decaying function for continuing tasks
            epsVal = AGNT.USR.epsVal/(log10(AGNT.ii_epoch+10)); % Decreasing the base of the logarithm will accelerate the shift from explore to exploit
            [a,wasExplore] = loreloit(epsVal,exploitAction,exploreActions);
        case 'visitSingh' % see [Singh 2000] pg. 15 Appendix A.2
            epsVal = AGNT.USR.epsVal/max([1 sum(AGNT.stateActionVisitCount(s,:))]);
            [a,wasExplore] = loreloit(epsVal,exploitAction,exploreActions);
        case 'visitFair'
            if min(AGNT.stateActionVisitCount(s,:)) <= AGNT.USR.epsVisitThreshold
                epsVal = AGNT.USR.epsVal/max([median(AGNT.stateActionVisitCount(s,:)) 1]); % max(.,1) addresses problem of dividing by 0
            else
                epsVal = AGNT.USR.epsVal/max([1 sum(AGNT.stateActionVisitCount(s,:))]);
            end
            [a,wasExplore] = loreloit(epsVal,exploitAction,exploreActions);
        case 'boltzmann' % Action selected for exploration is from a Boltzmann exploration policy [Singh 2000]
            exploitActionIndx = find(exploitAction == AGNT.validActions{s});
            % There is preliminary decision to explore or exploit. Each valid action has a probability of being selected.
            maxDelta = max(abs(AGNT.Q(s,AGNT.validActions{s}) - AGNT.Q(s,exploitAction))); % only include valid actions to avoid -Inf values in Q
            betaVal = max(log(sum(AGNT.stateActionVisitCount(s,AGNT.validActions{s}))),eps)/maxDelta;% The max( ,eps) is for the initial epoch of SARSA
            Pr_aValid = exp(betaVal*AGNT.Q(s,AGNT.validActions{s}))+eps; % The +eps is to avoid the zero vector
            Pr_aValid = Pr_aValid./sum(Pr_aValid); % normalize to make a probaility distribution
            indx = find( rand(1) < cumsum(Pr_aValid) ,1,'first');
            a = AGNT.validActions{s}( indx );
            epsVal = sum( Pr_aValid( exploitActionIndx ~= 1:numel(Pr_aValid) ));
            wasExplore = indx ~= exploitActionIndx;
        otherwise
            error('Invalid AGNT.USR.epsPolicy')
    end
else
    a = exploitAction;
    wasExplore = false;
    epsVal = 0; % no chance of exploration
end

end % function



function [a,wasExplore] = loreloit(epsVal,exploitAction,exploreActions)
    % Follow an epsilon-greedy policy for action selection
    if (rand(1) > epsVal) % exploitation
        a = exploitAction;
        wasExplore = false;
    else % exploration
        a = exploreActions( randi([1,numel(exploreActions)]) );
        wasExplore = true;
    end

end % function



function [AGNT] = updateExplorationParams(AGNT)

if AGNT.USR.renewableExploration && (strcmp(AGNT.USR.epsPolicy,'visit') || strcmp(AGNT.USR.epsPolicy,'visitThreshold'))
    % renew exploration from the current state if the reward hustory for
    % the current state-action pair is non-stationary.
    
    % FIFO update the reward buffers (first page in the buffer is the first-in)
    AGNT.rewardBufferOld(AGNT.s,AGNT.a,2:end) = AGNT.rewardBufferOld(AGNT.s,AGNT.a,1:end-1);
    AGNT.rewardBufferOld(AGNT.s,AGNT.a,1) = AGNT.rewardBufferNew(AGNT.s,AGNT.a,end);
    AGNT.rewardBufferNew(AGNT.s,AGNT.a,2:end) = AGNT.rewardBufferNew(AGNT.s,AGNT.a,1:end-1);
    AGNT.rewardBufferNew(AGNT.s,AGNT.a,1) = AGNT.r;
    
    buffersInitialized = ~any(isnan([squeeze(AGNT.rewardBufferOld(AGNT.s,AGNT.a,:));squeeze(AGNT.rewardBufferNew(AGNT.s,AGNT.a,:))]));
    
    % Check if the action was exploitative and the reward buffers are fully initialized
    if ~AGNT.wasExplore && buffersInitialized
        
        % check if the new and old reward distributions are significantly different
        switch AGNT.USR.rewardDistribution
            
            case 'discrete'
                
                if median(AGNT.rewardBufferNew(AGNT.s,AGNT.a,:)) ~= median(AGNT.rewardBufferOld(AGNT.s,AGNT.a,:));
                    
                    AGNT.explorationRenewed = true;
                    
                    switch AGNT.USR.renewalType
                        case 'local'
                            AGNT.stateActionVisitCount(AGNT.s,:) = 0;
                            AGNT.rewardBufferOld(AGNT.s,:,:) = nan;
                            AGNT.rewardBufferNew(AGNT.s,:,:) = nan;
                            AGNT.alphaMtrx(AGNT.s,:) = 0;
                        case 'global'
                            AGNT.stateActionVisitCount = zeros(AGNT.numStates,AGNT.numActions);
                            AGNT.rewardBufferOld = nan(AGNT.numStates,AGNT.numActions,AGNT.USR.rewardBufferDepth);
                            AGNT.rewardBufferNew = nan(AGNT.numStates,AGNT.numActions,AGNT.USR.rewardBufferDepth);
                            AGNT.alphaMtrx = zeros(AGNT.numStates,AGNT.numActions);
                            AGNT.Q = rand(AGNT.numStates,AGNT.numActions)*eps; % initialize to very small number instead of 0 (avoids ties)
                        otherwise
                            error('Invalid AGNT.USR.renewalType')
                    end
                    
                end
                
            case 'continuous'
                % this is a placeholder
                
            otherwise
                error('Invalid AGNT.USR.rewardDistribution')
        end
    end
else
    AGNT.explorationRenewed = false;
end

end % function
