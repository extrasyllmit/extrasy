% RADIO NETWORKS MDP

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

%    _______________________
% __/ SIMULATION PARAMETERS \____________________________________________________
ENV.USR.modelForP = 'extrasy2network';
ENV.USR.modelForR = '3NetworkStates';
ENV.USR.environmentModel = 'sequential';
ENV.USR.numEpochs = 500;
ENV.USR.episodeLength = [];
ENV.USR.animate = false;
ENV.USR.verbose = true;
ENV.USR.numTrials = 1;

[ENV,AGNT] = genMdpModel(ENV);

AGNT.USR.algorithm = 'Q-learn';
AGNT.USR.alphaVal = 0.25;
AGNT.USR.alphaPolicy = 'constant';
AGNT.USR.alphaVisitThreshold = -1;
AGNT.USR.gammaVal = 0.9;
AGNT.USR.lambdaVal = 0;
AGNT.USR.epsVal = 0.5;
AGNT.USR.epsPolicy = 'visitFair';
AGNT.USR.epsVisitThreshold = 1;
AGNT.USR.Qseed = [];
AGNT.USR.renewableExploration = true;
AGNT.USR.renewalType = 'local';
AGNT.USR.rewardBufferDepth = 5;
AGNT.USR.rewardDistribution = 'discrete';
AGNT.USR.policyOpt = [];
AGNT.USR.vOpt = [];


%    ________________
% __/ MDP SIMULATION \____________________________________________________
[AGNT, STAT, ENV] = mdpSim(AGNT, ENV);


%    _________________________
% __/ PLOT SIMULATION RESULTS \____________________________________________________
% PLOT LEARNING TRACES
plotEpochTraces(AGNT,ENV,STAT)

% PLOT LEARNED Q-VALUE AND POLICY
PLOTPAR.fnctnLabel = 'Q-Value';
PLOTPAR.xLabel = 'State';
PLOTPAR.yLabel = 'Action';
h_axes = plotFunction('Learned Q Values and Policy',AGNT.Q.',PLOTPAR);
plot((1:AGNT.numStates).',AGNT.policy,'ok','MarkerFaceColor','k')
plotTitle(AGNT,ENV)

% PLOT STATE VISIT COUNTS
PLOTPAR.xLabel = 'State';
PLOTPAR.yLabel = 'Action';
PLOTPAR.fnctnLabel = 'Visits';
plotStateActionCount('Visits to Agent States',AGNT.stateActionVisitCount.',PLOTPAR)
plotTitle(AGNT,ENV)
plotStateActionCount('Visits to Environment States',ENV.stateActionVisitCount.',PLOTPAR)
plotTitle(AGNT,ENV)
