% WINDY GRIDWORLD MDP (from Sutton and Barto Ch6)

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

%    _______________________
% __/ SIMULATION PARAMETERS \____________________________________________________
ENV.USR.modelForP = 'stochasticWindyGridworld';
ENV.USR.modelForR = 'stochasticNextState';
ENV.USR.numEpochs = 10e3;
ENV.USR.episodeLength = [];
ENV.USR.animate = false;
ENV.USR.verbose = true;
ENV.USR.numTrials = 1;

[ENV,AGNT] = genMdpModel(ENV);

AGNT.USR.algorithm = 'SARSA';
AGNT.USR.alphaVal = 0.25;
AGNT.USR.alphaPolicy = 'constant';
AGNT.USR.alphaVisitThreshold = -1;
AGNT.USR.gammaVal = 1;
AGNT.USR.lambdaVal = 0.9;
AGNT.USR.epsVal = 0.75;
AGNT.USR.epsPolicy = 'visitFair';
AGNT.USR.epsVisitThreshold = 2;
AGNT.USR.Qseed = [];
AGNT.USR.renewableExploration = false;
AGNT.USR.renewalType = 'local';
AGNT.USR.rewardBufferDepth = 3;
AGNT.USR.rewardDistribution = 'discrete';
AGNT.USR.policyOpt = [];
AGNT.USR.vOpt = [];

%    ________________
% __/ MDP SIMULATION \____________________________________________________
[AGNT, STAT, ENV] = mdpSim(AGNT, ENV);


%    _________________________
% __/ PLOT SIMULATION RESULTS \____________________________________________________
% PLOT LEARNING TRACES
plotEpisodeTraces(AGNT,ENV,STAT);

% PLOT LEARNED Q-VALUE AND POLICY
PLOTPAR.fnctnLabel = 'Q-Value';
PLOTPAR.xLabel = 'State';
PLOTPAR.yLabel = 'Action';
h_axes = plotFunction('Learned Q Values and Policy',AGNT.Q.',PLOTPAR);
plot((1:AGNT.numStates).',AGNT.policy,'ok','MarkerFaceColor','k')
plotTitle(AGNT,ENV)

% PLOT STATE VISIT COUNTS
visitCountEnv = reshape(sum(ENV.stateActionVisitCount,2),ENV.gridDims);
PLOTPAR.fnctnLabel = 'Visits';
PLOTPAR.xLabel = 'State';
PLOTPAR.yLabel = 'Action';
plotStateActionCount('Visits to Environment States',visitCountEnv,PLOTPAR)
plotTitle(AGNT,ENV)

% PLOT STATE VISIT COUNT PER ACTION
PLOTPAR.fnctnLabel = 'Visits';
PLOTPAR.xLabel = 'State';
PLOTPAR.yLabel = 'Action';
visitCountAgntStatePerAction = cell(size(AGNT.stateActionVisitCount,2),1);
for ii = 1:size(AGNT.stateActionVisitCount,2) % reshape the state-action visit count result into something plotable
    visitCountAgntStatePerAction{ii} = reshape(AGNT.stateActionVisitCount(:,ii),ENV.gridDims);
end
plotStateActionCount('Visits to Environment States per Action',visitCountAgntStatePerAction,PLOTPAR)

% PLOT ELIGIBILITY TRACE
if AGNT.USR.lambdaVal > 0
    PLOTPAR.fnctnLabel = 'Visits';
    plotStateActionCount('Eligibility Trace',reshape(sum(AGNT.eTrace,2),ENV.gridDims),PLOTPAR)
    plotTitle(AGNT,ENV)

    PLOTPAR.fnctnLabel = 'Visits';
    eTracePerAction = cell(size(AGNT.stateActionVisitCount,2),1);
    for ii = 1:size(AGNT.eTrace,2) % reshape the state-action visit count result into something plotable
        eTracePerAction{ii} = reshape(AGNT.eTrace(:,ii),AGNT.gridDims);
    end
    plotStateActionCount('Eligibility Trace Per Action',eTracePerAction,PLOTPAR)
end


% PLOT LEARNED VALUE & POLICY 
PLOTPAR.fnctnLabel = 'Expected Value';
PLOTPAR.cmap = 'rainbow';
h_lrnAxes = plotFunction('Learned Value Function & Policy',reshape(AGNT.V,ENV.gridDims),PLOTPAR);
plotGridworldMovesOnGrid(reshape(AGNT.V,ENV.gridDims),h_lrnAxes,AGNT.policy,AGNT.USR.actionSet)
plotTitle(AGNT,ENV)
