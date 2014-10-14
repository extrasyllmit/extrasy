function [AGNT, STAT, ENV] = mdpSim(AGNT, ENV)
% MDPSIM simulates the Markov Decision Process of an agent interacting with its environment.
% 
% 
% Notation:   S = number of states; A = number of actions
% 
% Inputs
% ----------------------------------------------------------------------------------------------
% ENV.USR
%              modelForP: Name of the model to use to generate the envitonment transition matrix
%              modelForR: Name of the model to use to generate the agent's reward matrix
%       environmentModel: Name of the model to use for envitonments reaction to agent actions
%              numEpochs: Number of epochs of the MDP to simulate
%          episodeLength: (OPTIONAL) Number of epochs comprising an episode
%                animate: (OPTIONAL) Animate the grid world [doesn't work]
%                verbose: Flag enabling verbose command line output
%              numTrials: Number of trials of the MDP task to run
% 
% AGNT.USR
%                actionSet: indexed jset of agent actions
%         stateSensorModel: name of model used for the agent sensor
%                algorithm: Choice of algorithm. 'Q-learn','SARSA'
%                 alphaVal: learning rate. [0,1]
%                           1 causes value update to disregard the past value. 
%              alphaPolicy: learning rate policy. 'constant', 'visitThreshold'
%      alphaVisitThreshold: visit count threshold for 'visitThreshold' policy
%                           Setting alphaVal = 1 and alphaVisitThreshold = -1
%                           results in the decaying learning rate
%                           proposed by Sigaud and Buffet, p51.
%                 gammaVal: discount factor. [0,1]
%                           1 is undiscounted.
%                           Near 1 emphasizes future expected reward.
%                           Near 0 emphasizes immediate reward.
%                           0 is myopic
%                lambdaVal: The forgetting factor of the eligibility trace
%                           setting to 0 disables eligibility traces
%                           setting to 1 uses eligibility traces with no memory decay
%                   epsVal: exploration rate. [0,1]
%                           0 causes all exploitation and no exploration
%                epsPolicy: ecploration policy. 'constant',timeFast','timeSlow','visitSingh',visitFair','boltzman'
%        epsVisitThreshold: visit count threshold for 'visitFair' policy
%                    Qseed: (OPTIONAL) used to initialize the Q-matrix 
%     renewableExploration: true,false
%              renewalType: 'local' or 'global'
%        rewardBufferDepth: odd positive integers
%       rewardDistribution: 'discrete' or 'continuous'
%                policyOpt: (OPTIONAL) the optimal policy 
%                     vOpt: (OPTIONAL) the optimal value function 
%         
% 
% Outputs
% ----------------------------------------------------------------------------------------------
% AGNT = 
%                       USR: User-defined input parameters
%                numActions: Number of actions
%                         P: The agent's state transition probability matrix 
%                            Option 1: Ax1 cell array of sparse SxS arrays (memory efficient)
%                            Option 2: SxSxA array
%                         R: The agent's reward matrix 
%                            Option 1: Ax1 cell array of sparse SxS arrays (memory efficient)
%                            Option 2: SxA array
%                         Q:the agent's learned Q-matrix 
%                         V:the learned value function
%                    policy:the learned policy
% 
% ENV = 
%                       USR: User-defined input parameters
%                         P: The environment's state transition probability matrix 
%                            Option 1: Ax1 cell array of sparse SxS arrays (memory efficient)
%                            Option 2: SxSxA array
%                  gridDims: [3 9]
%                         R: The environment's reward matrix 
%                            Option 1: Ax1 cell array of sparse SxS arrays (memory efficient)
%                            Option 2: SxA array
% 
% 
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

%    ____________
% __/ INITIALIZE \__________________________________________________________________
% Initialize the environment
ENV.envObjectState = 'initialize';
[ENV,AGNT,STAT] = envObject(ENV,AGNT);

%    ____________
% __/ TRIAL LOOP \__________________________________________________________________
for trialCounter = 1:ENV.USR.numTrials
    
    ENV.trialCounter = trialCounter;
    disp(['Trial ',num2str(trialCounter)])

    % Reset the environment for a new trial
    ENV.envObjectState = 'newTrial';
    [ENV,AGNT,STAT] = envObject(ENV,AGNT,STAT);
        
    %    __________
    % __/ MDP LOOP \__________________________________________________________________
    for ii_epoch = 1:ENV.USR.numEpochs
        
        ENV.ii_epoch = ii_epoch;
        
        ENV.envObjectState = 'step';
        [ENV,AGNT,STAT] = envObject(ENV,AGNT,STAT);
        
        if strcmp(ENV.taskType,'episodic')        
            if ENV.stochasticEpisodes && any(ENV.s == ENV.USR.stopStateIndex)
                % Re-initialize when a terminal state is reached
                ENV.envObjectState = 'newEpisode';
                [ENV,AGNT,STAT] = envObject(ENV,AGNT,STAT);
            elseif ENV.deterministicEpisodes && mod(ENV.ii_epoch,ENV.USR.episodeLength) == 1
                % Re-initializewhen the terminal duration is reached
                ENV.envObjectState = 'newEpisode';
                [ENV,AGNT,STAT] = envObject(ENV,AGNT,STAT);
            end
        end
        
    end
    
    ENV.envObjectState = 'finishTrial';
    [ENV,AGNT,STAT] = envObject(ENV,AGNT,STAT);
    
end

ENV.envObjectState = 'finish';
[ENV,AGNT,STAT] = envObject(ENV,AGNT,STAT);

end % function


%    _______________
% __/ SUB-FUNCTIONS \__________________________________________________________________
% none


