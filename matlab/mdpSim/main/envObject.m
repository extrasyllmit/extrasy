function [ENV,AGNT,STAT] = envObject(ENV,AGNT,STAT)
% Defines the environment's state machine and executes the current state

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

switch ENV.envObjectState
    
    case 'initialize' % do all the on-time calculations and preparations
        
        if ~isfield(ENV,'verbose'); ENV.USR.verbose = false; end
        if ~isfield(ENV,'animate'); ENV.USR.animate = false; end
        
        ENV.iscellP = iscell(ENV.P); % precomputed for speed
        ENV.iscellR = iscell(ENV.R); % precomputed for speed
        
        if ENV.USR.verbose
            disp('   __________')
            disp('__/ SCENARIO \__________________________________________________________________')
        end
        
        if ENV.USR.verbose
            if ENV.iscellP
                if any(sum(ENV.P{1}>0,2)>1)
                    fprintf('%s\n','   Environment has STOCHASTIC transitions');
                else
                    fprintf('%s\n','   Environment has DETERMINISTIC transitions');
                end
            else
                if any(sum(nnz(ENV.P),2)>1)
                    fprintf('%s\n','   Environment has STOCHASTIC transitions');
                else
                    fprintf('%s\n','   Environment has DETERMINISTIC transitions');
                end
            end;
        end
        
        % Precompute branching conditions (for speed and clarity)
        ENV.stochasticEpisodes = ~isempty(ENV.USR.stopStateIndex);
        ENV.deterministicEpisodes = ~isempty(ENV.USR.episodeLength);
        
        if ENV.stochasticEpisodes || ENV.deterministicEpisodes
            ENV.taskType = 'episodic';
        else
            ENV.taskType = 'continuous';
        end
        
        if ENV.USR.verbose;
            if ~ENV.stochasticEpisodes && ~ENV.deterministicEpisodes;
                fprintf('%s\n','   MDP is a continuing task');
            elseif ENV.stochasticEpisodes && ~ENV.deterministicEpisodes;
                fprintf('%s\n','   MDP has episodic tasks of stochastic duration');
            elseif ~ENV.stochasticEpisodes && ENV.deterministicEpisodes;
                fprintf('%s\n','   MDP has episodic tasks of deterministic duration');
            end
        end
        
        % Pre-compute the cumulative probability matrix for later use when choosing next states (done for speed)
        if ENV.iscellP
            ENV.cumsumP = cell(size(ENV.P));
            for ii = 1:numel(ENV.P)
                ENV.cumsumP{ii} = cumsum(ENV.P{ii},2);
            end
        else
            ENV.cumsumP = cumsum(ENV.P,2); % ENV.P is nStates x nStates x nActions
        end
        
        % Initialize the agent
        AGNT.agentObjectState = 'initialize';
        [AGNT] = agentObject(AGNT,ENV);

         % Initialize the simulation statistics
        STAT.statObjectState = 'initialize';
        [STAT] = statObject(ENV,AGNT,STAT);
       
        ENV.envObjectState = 'newTrial';

    case 'newTrial'

        ENV.ii_episode = 1; % episode counter
     
        % Initialize the environment state (has to be done now before the agentObject is called)
        if ENV.stochasticEpisodes
            ENV.s = ENV.USR.startStateIndex;
        else
            ENV.s = randi([1,ENV.numStates]); % start the next episode in a random state
        end
        
        % Initialize the Environment visitation count matrix
        ENV.stateActionVisitCount = zeros(ENV.numStates,AGNT.numActions);

        % Prepare the agent for a new trial
        AGNT.agentObjectState = 'newTrial';
        [AGNT] = agentObject(AGNT,ENV);
        
        % Allow the agent to execute its "begin" state (must be done at the
        % start of a trial regardliss of wether the MDP is a continuing
        % task or an episodic task)
        AGNT.agentObjectState = 'begin';
        [AGNT,ENV,STAT] = agentObject(AGNT,ENV,STAT);

        % Prepare the simulation statistics for a new trial
        STAT.statObjectState = 'newTrial';
        [STAT] = statObject(ENV,AGNT,STAT);
        
        ENV.envObjectState = 'step';
        
    case 'newEpisode'
        
        % Update the simulation statistics for the just-finished episode
        STAT.statObjectState = 'finishEpisode';
        [STAT] = statObject(ENV,AGNT,STAT);
        
        ENV.ii_episode = ENV.ii_episode + 1;
        
        % Reset the environment state
        if ENV.stochasticEpisodes
            % This is critical to do immediately when the stopping
            % state is reached and before the next Q-update happens
            ENV.s = ENV.USR.startStateIndex;
        elseif ENV.deterministicEpisodes
            ENV.s = randi([1,ENV.numStates]); % start the next episode in a random state
        end

        % Prepare the agent for the first epoch of the new episode
        AGNT.agentObjectState = 'begin';
        [AGNT,ENV,STAT] = agentObject(AGNT,ENV,STAT);
        
        ENV.envObjectState = 'step';

    case 'step' % execute the next epoch of the MDP
               
        % Allow the agent to execute a step
        AGNT.agentObjectState = 'step';
        [AGNT,ENV,STAT] = agentObject(AGNT,ENV,STAT);
        
        ENV.envObjectState = 'step';

    case 'finishTrial'
        
        % Allow the agent to execute it's final step
        AGNT.agentObjectState = 'finish';
        [AGNT,ENV,STAT] = agentObject(AGNT,ENV,STAT);
        
        STAT.statObjectState = 'finishTrial';
        [STAT] = statObject(ENV,AGNT,STAT);
        
        ENV.envObjectState = 'newTrial';

    case 'finish'
        
        STAT.statObjectState = 'finish';
        [STAT] = statObject(ENV,AGNT,STAT);

        ENV.envObjectState = 'done';
        
end

end % function
