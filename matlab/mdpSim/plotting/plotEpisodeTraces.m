function [] = plotEpisodeTraces(AGNT,ENV,STAT)
% plot episodic learning traces

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

episodeDurations = diff([1;STAT.episodeStopIndex]);

nfigure('Learning Profile')
    h_a1 = subplot(3,1,1);
        plotCoverEpsAlphaRenew(AGNT,ENV,STAT,h_a1)
        plotTitle(AGNT,ENV)
    h_a2 = subplot(3,1,2);
        semilogy((1:numel(episodeDurations)),episodeDurations)
        ylabel('Episode Duration')
        xlabel('Episode Index')
        ylim([1 10^ceil(log10(max(episodeDurations)))])
        xlim([1 numel(episodeDurations)])
        grid on
    h_a3 = subplot(3,1,3);
        plot((1:numel(STAT.episodeReward)),STAT.episodeReward,'Color',[0 127 0]/255)
        ylabel('Episode Reward')
%         ylim([floor(min(STAT.episodeReward)) ceil(max(STAT.episodeReward))])
        xlim([1 numel(STAT.episodeReward)])
        xlabel('Episode Index')
        grid on
    linkaxes([h_a2 h_a3],'x')
    
    h_z = zoom;
    set(h_z,'Motion','horizontal','Enable','on');
    h_p = pan;
    set(h_p,'Motion','horizontal','Enable','off');
    
    if ENV.USR.numTrials > 1
        
        axes(h_a2)
        hold on
        plot(h_a2,(1:numel(STAT.AVG.episodeDuration)),STAT.AVG.episodeDuration,'-','LineWidth',2,'Color',[180 180 255]/255)
        xlim([1 numel(STAT.AVG.episodeDuration)])
        
        axes(h_a3)
        hold on
        plot(h_a3,(1:numel(STAT.AVG.episodeReward)),STAT.AVG.episodeReward,'-','LineWidth',2,'Color',[180 255 180]/255)
        xlim([1 numel(STAT.AVG.episodeReward)])
        
    end
