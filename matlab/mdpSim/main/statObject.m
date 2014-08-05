function [STAT] = statObject(ENV,AGNT,STAT)
% Defines the sumulation statistics recorder's state machine and executes the current state

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

switch STAT.statObjectState
    
    case 'initialize'
        
        if ENV.USR.numTrials > 1 && strcmp(ENV.envObjectState,'initialize'); % epoch statistics averaged over multiple trials
            STAT.AVG.alphaVal = zeros(ENV.USR.numEpochs,1);
            STAT.AVG.epsVal = zeros(ENV.USR.numEpochs,1);
            STAT.AVG.reward = zeros(ENV.USR.numEpochs,1);
            STAT.AVG.coverageAgnt = zeros(ENV.USR.numEpochs,1);
            STAT.AVG.coverageEnv = zeros(ENV.USR.numEpochs,1);
            if strcmp(ENV.taskType,'episodic') % episode statistics averaged over multiple trials
                STAT.AVG.trialsPerEpisode = zeros(1e3,1);
                STAT.AVG.episodeDuration = zeros(1e3,1);
                STAT.AVG.episodeReward = zeros(1e3,1);
                STAT.AVG.episodeCoverageAgnt = zeros(1e3,1);
                STAT.AVG.episodeCoverageEnv = zeros(1e3,1);
                if ~isempty(AGNT.USR.vOpt)
                    STAT.AVG.episodeVlueMSE = zeros(1e3,1);
                end
                if ~isempty(AGNT.USR.policyOpt)
                    STAT.AVG.episodePolicyDistance = zeros(1e3,1);
                end
            end
        end
        
        STAT.statObjectState = 'newTrial';

    case 'newTrial'
        
        % initialize epoch statistics
        STAT.envState = NaN(ENV.USR.numEpochs,1);
        STAT.agentEstState = NaN(ENV.USR.numEpochs,1); % the agent's estiumated astate may be different than it's true state
        STAT.action = NaN(ENV.USR.numEpochs,1);
        STAT.reward = NaN(ENV.USR.numEpochs,1);
        STAT.alphaVal = NaN(ENV.USR.numEpochs,1);
        STAT.epsVal = NaN(ENV.USR.numEpochs,1);
        STAT.coverageAgnt = NaN(ENV.USR.numEpochs,1);
        STAT.coverageEnv = NaN(ENV.USR.numEpochs,1);
        STAT.wasExplore = false(ENV.USR.numEpochs,1);
        STAT.renewedExploration = false(ENV.USR.numEpochs,1);

        % initialize episode statistics
        if strcmp(ENV.taskType,'episodic')
            STAT.episodeStopIndex = zeros(1e3,1);
            STAT.episodeReward = zeros(1e3,1);
            STAT.episodeCoverageAgnt = NaN(1e3,1);
            STAT.episodeCoverageEnv = NaN(1e3,1);
            if ~isempty(AGNT.USR.policyOpt)
                STAT.episodePolicyDistance = NaN(1e3,1);
            end
            if ~isempty(AGNT.USR.vOpt)
                STAT.episodeVlueMSE = NaN(1e3,1);
            end
        end
        
        STAT.statObjectState = 'step';
        
    case 'step'
        % This case should only be called from the agentObject
        % (and usually from within the agent's update algorithm)
        
        STAT.envState(ENV.ii_epoch) = ENV.s;
        STAT.agentEstState(ENV.ii_epoch) = AGNT.s;
        STAT.action(ENV.ii_epoch) = AGNT.a;
        STAT.reward(ENV.ii_epoch) = AGNT.r;
        STAT.alphaVal(ENV.ii_epoch) = AGNT.alphaVal;
        STAT.epsVal(ENV.ii_epoch) = AGNT.epsVal;
        STAT.wasExplore(ENV.ii_epoch) = AGNT.wasExplore;
        STAT.renewedExploration(ENV.ii_epoch) = AGNT.explorationRenewed;
        STAT.coverageAgnt(ENV.ii_epoch) = nnz(AGNT.stateActionVisitCount);
        STAT.coverageEnv(ENV.ii_epoch) = nnz(ENV.stateActionVisitCount);
        
        if strcmp(ENV.taskType,'episodic')
            STAT.episodeReward(ENV.ii_episode) = STAT.episodeReward(ENV.ii_episode) + AGNT.r;
        end
        
        STAT.statObjectState = 'step';
        
    case 'finishEpisode'
        
        if numel(STAT.episodeStopIndex) == ENV.ii_episode
            % grow episodic variables blockwise at infrequent regular intervals
            % (can't preallocate because don't know how many episodes will
            % occur for the given number of epochs)
            STAT.episodeStopIndex = [STAT.episodeStopIndex ; zeros(1e3,1)];
            STAT.episodeReward = [STAT.episodeReward ; zeros(1e3,1)];
            STAT.episodeCoverageAgnt = [STAT.episodeCoverageAgnt ; NaN(1e3,1)];
            STAT.episodeCoverageEnv = [STAT.episodeCoverageEnv ; NaN(1e3,1)];
            if ~isempty(AGNT.USR.policyOpt)
                STAT.episodePolicyDistance = [STAT.episodePolicyDistance ; NaN(1e3,1)];
            end
            if ~isempty(AGNT.USR.vOpt)
                STAT.episodeVlueMSE = [STAT.episodeVlueMSE ; NaN(1e3,1)];
            end
        end
                
        % Now record the episode's statistics 
        STAT.episodeStopIndex(ENV.ii_episode) = ENV.ii_epoch;
        STAT.episodeCoverageAgnt(ENV.ii_episode) = nnz(AGNT.stateActionVisitCount);
        STAT.episodeCoverageEnv(ENV.ii_episode) = nnz(ENV.stateActionVisitCount);
        if ~isempty(AGNT.USR.policyOpt)
            [~, policyTmp] = max(AGNT.Q,[],2);
             % a "Hamming" distance between the current and optimal policies
             STAT.episodePolicyDistance(ENV.ii_episode) = nnz(policyTmp ~= AGNT.USR.policyOpt);
        end
        if ~isempty(AGNT.USR.vOpt)
            [Vtmp, ~] = max(AGNT.Q,[],2);
            % Compute the mean square error between the current and optimal policies
            STAT.episodeVlueMSE(ENV.ii_episode) = sum((Vtmp(:) - AGNT.USR.vOpt(:)).^2)/numel(Vtmp);
        end
        
        STAT.statObjectState = 'step';
        
    case 'finishTrial'

        if strcmp(ENV.taskType,'episodic')
            
            % prepare to prune the final trial's statistics
            if ENV.stochasticEpisodes 
                if ~any(ENV.s == ENV.USR.stopStateIndex)
                    % The last episode did not reach a terminal state and is incomplete
                    lastCompleteEpisode = ENV.ii_episode-1;
                else
                    lastCompleteEpisode = ENV.ii_episode;
                end
            elseif ENV.deterministicEpisodes 
                if mod(ENV.ii_epoch,ENV.USR.episodeLength) ~= 1
                    % The last episode did not reach a terminal state and is incomplete
                    lastCompleteEpisode = ENV.ii_episode-1;
                else
                    lastCompleteEpisode = ENV.ii_episode;
                end
            end

            % prune variables that grew too long
            STAT.episodeStopIndex = STAT.episodeStopIndex(1:lastCompleteEpisode);
            STAT.episodeReward = STAT.episodeReward(1:lastCompleteEpisode);
            STAT.episodeCoverageAgnt = STAT.episodeCoverageAgnt(1:lastCompleteEpisode);
            STAT.episodeCoverageEnv = STAT.episodeCoverageEnv(1:lastCompleteEpisode);
            if ~isempty(AGNT.USR.policyOpt)
                STAT.episodePolicyDistance = STAT.episodePolicyDistance(1:lastCompleteEpisode);
            end
            if ~isempty(AGNT.USR.vOpt)
                STAT.episodeVlueMSE = STAT.episodeVlueMSE(1:lastCompleteEpisode);
            end
            
            % grow average statistics variables as needed
            if (ENV.USR.numTrials > 1) && (numel(STAT.AVG.trialsPerEpisode) < lastCompleteEpisode)
                additionalZeros = lastCompleteEpisode - numel(STAT.AVG.trialsPerEpisode);
                % grow episodic variables (can't preallocate because don't know
                % how many episodes will occur for the given number of epochs)
                STAT.AVG.trialsPerEpisode = [STAT.AVG.trialsPerEpisode ; zeros(additionalZeros,1)];
                STAT.AVG.episodeDuration = [STAT.AVG.episodeDuration ; zeros(additionalZeros,1)];
                STAT.AVG.episodeReward = [STAT.AVG.episodeReward ; zeros(additionalZeros,1)];
                STAT.AVG.episodeCoverageAgnt = [STAT.AVG.episodeCoverageAgnt ; zeros(additionalZeros,1)];
                STAT.AVG.episodeCoverageEnv = [STAT.AVG.episodeCoverageEnv ; zeros(additionalZeros,1)];
                if ~isempty(AGNT.USR.vOpt)
                    STAT.AVG.episodeVlueMSE = [STAT.AVG.episodeVlueMSE ; zeros(additionalZeros,1)];
                end
                if ~isempty(AGNT.USR.policyOpt)
                    STAT.AVG.episodePolicyDistance = [STAT.AVG.episodePolicyDistance ; zeros(additionalZeros,1)];
                end
            end
            
        end
        
        if ENV.USR.numTrials > 1 % epoch statistics averaged over multiple trials
            STAT.AVG.alphaVal = STAT.AVG.alphaVal + STAT.alphaVal/ENV.USR.numTrials;
            STAT.AVG.epsVal = STAT.AVG.epsVal + STAT.epsVal/ENV.USR.numTrials;
            STAT.AVG.reward = STAT.AVG.reward + STAT.reward/ENV.USR.numTrials;
            STAT.AVG.coverageAgnt = STAT.AVG.coverageAgnt + STAT.coverageAgnt/ENV.USR.numTrials;
            STAT.AVG.coverageEnv = STAT.AVG.coverageEnv + STAT.coverageEnv/ENV.USR.numTrials;
            if strcmp(ENV.taskType,'episodic') % episode statistics averaged over multiple trials
                additionalZeros = numel(STAT.AVG.trialsPerEpisode) - numel(STAT.episodeStopIndex);
                STAT.AVG.trialsPerEpisode(STAT.episodeStopIndex>0) = STAT.AVG.trialsPerEpisode(STAT.episodeStopIndex>0) + 1;
                STAT.AVG.episodeDuration = STAT.AVG.episodeDuration + [diff([0;STAT.episodeStopIndex]) ; zeros(additionalZeros,1)];
                STAT.AVG.episodeReward = STAT.AVG.episodeReward + [STAT.episodeReward ; zeros(additionalZeros,1)];
                STAT.AVG.episodeCoverageAgnt = STAT.AVG.episodeCoverageAgnt + [STAT.episodeCoverageAgnt ; zeros(additionalZeros,1)];
                STAT.AVG.episodeCoverageEnv = STAT.AVG.episodeCoverageEnv + [STAT.episodeCoverageEnv ; zeros(additionalZeros,1)];
                if ~isempty(AGNT.USR.vOpt)
                    STAT.AVG.episodeVlueMSE = STAT.AVG.episodeVlueMSE + [STAT.episodeVlueMSE ; zeros(additionalZeros,1)];
                end
                if ~isempty(AGNT.USR.policyOpt)
                    STAT.AVG.episodePolicyDistance = STAT.AVG.episodePolicyDistance + [STAT.episodePolicyDistance ; zeros(additionalZeros,1)];
                end
            end
        end
        
        STAT.statObjectState = 'newTrial';
    
    case 'finish'
        
        if strcmp(ENV.taskType,'episodic') && ENV.USR.numTrials > 1% episode statistics averaged over multiple trials
            longestEpisode = nnz(STAT.AVG.trialsPerEpisode);
            STAT.AVG.trialsPerEpisode = STAT.AVG.trialsPerEpisode(1:longestEpisode);
            STAT.AVG.episodeDuration = STAT.AVG.episodeDuration(1:longestEpisode)./STAT.AVG.trialsPerEpisode;
            STAT.AVG.episodeReward = STAT.AVG.episodeReward(1:longestEpisode)./STAT.AVG.trialsPerEpisode;
            STAT.AVG.episodeCoverageAgnt = STAT.AVG.episodeCoverageAgnt(1:longestEpisode)./STAT.AVG.trialsPerEpisode;
            STAT.AVG.episodeCoverageEnv = STAT.AVG.episodeCoverageEnv(1:longestEpisode)./STAT.AVG.trialsPerEpisode;
            if ~isempty(AGNT.USR.vOpt)
                STAT.AVG.episodeVlueMSE = STAT.AVG.episodeVlueMSE(1:longestEpisode)./STAT.AVG.trialsPerEpisode;
            end
            if ~isempty(AGNT.USR.policyOpt)
                STAT.AVG.episodePolicyDistance = STAT.AVG.episodePolicyDistance(1:longestEpisode)./STAT.AVG.trialsPerEpisode;
            end
        end
        
        STAT.statObjectState = 'done';

end

end % function
