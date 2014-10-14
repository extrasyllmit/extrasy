function plotTransProbMatrix(P,startStates,figTitle)
% Plots the transition probability matrix for a MDP

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

if nargin == 1 
    figTitle = 'Transition Probability Matrix';
end

legend_labels = {};

[unreachableStates,terminalStates] = findSpecialStates(P);

if ~isempty(startStates)
    legend_labels = cat(2,legend_labels,'Initial States');
end
if ~isempty(terminalStates)
    legend_labels = cat(2,legend_labels,'Terminal States');
end
if ~isempty(unreachableStates)
    legend_labels = cat(2,legend_labels,'Unreachable States');
end



nfigure(figTitle)
ah = zeros(numel(P),1);
for aa = 1:numel(P)
    ah(aa) = subplot(ceil(sqrt(numel(P))),ceil(sqrt(numel(P))),aa);
    imagesc(P{aa})
    hold on
    plot(min(xlim)*ones(1,numel(startStates)),startStates,'g>','Markerfacecolor','g')
    plot(terminalStates,terminalStates,'cs')
    plot(unreachableStates,min(ylim)*ones(1,numel(unreachableStates)),'rv','Markerfacecolor','r')
    caxis([0 1])
    cmap = flipud(gray(256));
    colormap([[1 1 1];cmap(32:end,:)]);
    title(['Action:',num2str(aa)])
    axis ij; axis image;
    set(gca,'XaxisLocation','bottom')
    h_l = legend(legend_labels);
    set(h_l,'Location','NorthOutside', 'Orientation','Horizontal')
end

linkaxes(ah,'xy')
drawnow


