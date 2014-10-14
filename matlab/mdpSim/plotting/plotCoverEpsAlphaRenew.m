function [] = plotCoverEpsAlphaRenew(AGNT,ENV,STAT,axHandle)
% plot learning traces for coverage, epsilon, alpha, and renewal

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

numCoverableStatesAgnt = numel(AGNT.Q)-numel(ENV.USR.stopStateIndex);
numCoverableStatesEnv = numel(ENV.R)-numel(ENV.USR.stopStateIndex);
renewals = find(STAT.renewedExploration).';

axes(axHandle)
legend_labels = {};

if ENV.USR.numTrials > 1
    
    plot(STAT.AVG.alphaVal,'-','LineWidth',2,'Color',[175 215 255]/255)
    hold on
    plot(STAT.AVG.epsVal,'-','LineWidth',2,'Color',[255 195 195]/255)
    plot(STAT.AVG.coverageAgnt/numCoverableStatesAgnt,'.','LineWidth',2,'Color',[180 255 180]/255)
    plot(STAT.AVG.coverageEnv/numCoverableStatesEnv,'.','LineWidth',2,'Color',[0.68 0.47 0])
    legend_labels = cat(2,legend_labels,'Avg. alpha','Avg. epsilon','Avg. Agent-Coverage','Avg. Environment-Coverage');

end


plot(STAT.alphaVal,'b-','LineWidth',2)
hold on
plot(STAT.epsVal,'r-','LineWidth',2)
plot(STAT.coverageAgnt/numCoverableStatesAgnt,'g','LineWidth',2)
plot(STAT.coverageEnv/numCoverableStatesEnv,'Color',[0.75 0.75 0],'LineWidth',2)
plot([renewals;renewals],[zeros(size(renewals));ones(size(renewals))],'c')
ylim([0 1])
xlabel('Epoch Index')
ylabel('Rate')
legend_labels = cat(2,legend_labels,'alpha','epsilon','Agent Coverage','Environment Coverage');

if ~isempty(renewals)
    legend_labels = cat(2,legend_labels,'reward');
end


legend(legend_labels)

grid on
