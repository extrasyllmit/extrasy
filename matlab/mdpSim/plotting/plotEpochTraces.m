function [] = plotEpochTraces(AGNT,ENV,STAT)
% plots learning statistics for each epoch

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

nfigure('Epoch Traces')
    h_a1 = subplot(4,1,1);
        plotCoverEpsAlphaRenew(AGNT,ENV,STAT,h_a1)
        plotTitle(AGNT,ENV)
    h_a2 = subplot(4,1,2);
        plot(STAT.action,'r.-')
        hold on
        plot(find(STAT.wasExplore),STAT.action(STAT.wasExplore),'ko','LineWidth',2)
        ylabel('Agent Action')
        ylim([min(AGNT.USR.actionSet)-1 max(AGNT.USR.actionSet)+1])
        grid on
        legend('Action Trace','Exploratory Actions')
    h_a3 = subplot(4,1,3);
        plot(ENV.stateWords(STAT.envState,3),'b.-')
        ylabel('Environment Action')
        ylim([min(ENV.stateWords(:,3))-1 max(ENV.stateWords(:,3))+1])
        grid on        
    h_a4 = subplot(4,1,4);
        [h_axyy,h_l1,h_l2] = plotyy((1:numel(STAT.envState)),ENV.stateWords(STAT.envState,1),(1:numel(STAT.reward)),STAT.reward);
        set(h_l1,'LineStyle','-','Marker','.')
        set(h_l2,'LineStyle','-','Marker','.')
        set(get(h_axyy(1),'Ylabel'),'String','Net State')
        set(get(h_axyy(2),'Ylabel'),'String','Reward')
        set(h_axyy(1),'Ylim',[min(ENV.stateWords(:,1))-1 max(ENV.stateWords(:,1))+1],'YTickMode','auto')
        set(h_axyy(2),'Ylim',[min(STAT.reward)-1 max(STAT.reward)+1],'YTickMode','auto')
        xlim([1 numel(STAT.envState)])
        ylim([min(ENV.stateWords(:,1))-1 max(ENV.stateWords(:,1))+1])
        grid on
        xlabel('Epoch Index')
    linkaxes([h_a1 h_a2 h_a3 h_axyy],'x')

    h_z = zoom;
    set(h_z,'Motion','horizontal','Enable','on');
    h_p = pan;
    set(h_p,'Motion','horizontal','Enable','off');
    
    if ENV.USR.numTrials > 1
        axes(h_axyy(2))
        hold on
        plot(h_axyy(2),(1:numel(STAT.reward)),STAT.AVG.reward,'-','LineWidth',2,'Color',[180 255 180]/255)
    end
