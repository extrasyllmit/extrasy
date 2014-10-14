function plotRewardMatrix(R,figTitle)
% Plots the reward matrix from a learning agent

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
    figTitle = 'Reward Matrix';
end

nfigure(figTitle)
if iscell(R)
    R_cat = cat(1,R{:});
    R_cat(isinf(R_cat)) = 0;
    [cmap,Rmin,Rmax] = setupColorMap(R_cat);
    for aa = 1:numel(R)
        subplot(ceil(sqrt(numel(R))),ceil(sqrt(numel(R))),aa)
        imagesc(R{aa})
        caxis([Rmin Rmax])
        if size(cmap,1) == 1
            text(min(xlim),min(ylim),'ALL REWARDS ARE EQUAL')
        end
        colormap(cmap);
        title(['Action:',num2str(aa)])
        axis ij; axis image;
        set(gca,'XaxisLocation','bottom')
        [infI,infJ] = find(isinf(R{aa}));
        hold on
        plot(infJ,infI,'ws','MarkerFaceColor','k','MarkerSize',6)
    end
else
    imagesc(R)
    R_noInf = R;
    R_noInf(isinf(R_noInf)) = 0;
    [cmap,Rmin,Rmax] = setupColorMap(R_noInf);
    caxis([Rmin Rmax])
    if size(cmap,1) == 1
        text(min(xlim),min(ylim),'ALL REWARDS ARE EQUAL')
    end
    colormap(cmap);
    xlabel('Action Index')
    ylabel('State Index')
    axis ij; axis image;
    set(gca,'XaxisLocation','bottom')
    h_c = colorbar;
    set(get(h_c,'Ylabel'),'String','Reward')
    [infI,infJ] = find(isinf(R));
    hold on
    plot(infJ,infI,'ws','MarkerFaceColor','k','MarkerSize',6)
end

if ~isempty(infI)
    h_l = legend('-Inf Reward');
    set(h_l,'Location','NorthWestOutside')
end

end % function

function [cmap,Rmin,Rmax] = setupColorMap(RR)

    Rmin = min(RR(:));
    Rmax = max(RR(:));
    if Rmin == Rmax
        Rmax = Rmax + 1;
    end
    Rdelt = Rmax-Rmin;
    if Rmin < 0 && Rmax > 0
        cmap_neg = [ ((0:-Rmin)/-Rmin).' ((0:-Rmin)/-Rmin).' ones(-Rmin+1,1) ];
        cmap_pos = [ ones(Rmax+1,1) ((0:Rmax)/Rmax).' ((0:Rmax)/Rmax).' ];
        cmap = [cmap_neg;flipud(cmap_pos)];
    elseif Rmin < 0 && Rmax <= 0
        cmap = [ ones(numel(0:(Rdelt+1)),1) ((0:(Rdelt+1))/(Rdelt+1)).' ((0:(Rdelt+1))/(Rdelt+1)).' ];
    elseif Rmin >= 0 && Rmax > 0
        cmap = [ ((0:(Rdelt+1))/(Rdelt+1)).' ((0:(Rdelt+1))/(Rdelt+1)).' ones(numel(0:(Rdelt+1)),1) ];
    end
    
end
