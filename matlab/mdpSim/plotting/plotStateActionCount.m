function plotStateActionCount(windowTitle,fnctn,PLOTPAR)
% Plots the state-action count matrix for a learning agent

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

if iscell(fnctn)
    fnctnSize = size(fnctn{1});
else
    fnctnSize = size(fnctn);
end

if ~isfield(PLOTPAR,'yTicklabel'); PLOTPAR.yTicklabel = 1:fnctnSize(1); end
if ~isfield(PLOTPAR,'xTicklabel'); PLOTPAR.xTicklabel = 1:fnctnSize(2); end
if ~isfield(PLOTPAR,'xLabel'); PLOTPAR.xLabel = ''; end
if ~isfield(PLOTPAR,'yLabel'); PLOTPAR.yLabel = ''; end
if ~isfield(PLOTPAR,'fnctnLabel'); PLOTPAR.fnctnLabel = ''; end
if ~isfield(PLOTPAR,'cmap'); PLOTPAR.cmap = 'rainbow'; end

cmap = flipud(gray(16));
cmap = [[1 0 0];cmap(2:end,:)];

nfigure(windowTitle)
if iscell(fnctn) % the function is a cell array and each cell is given it's own axes
    fnctn_cat = cat(1,fnctn{:});
    fnctn_cat_log10 = log10(fnctn_cat);
    if min(fnctn_cat_log10(:))+2 < max(fnctn_cat_log10(:))
        fnctn_cat = fnctn_cat_log10;
        logScaleLabel = '(log scale)';
    else
        logScaleLabel = '';
    end
    
    if ~isempty(logScaleLabel)
        minVal = min(min(fnctn_cat(~isinf(fnctn_cat))));
    else
        minVal = min(min(fnctn_cat(fnctn_cat~=0)));
    end
    colorRange = [-abs(max(fnctn_cat(:)) - minVal)/14 + minVal max(fnctn_cat(:))];
    
    for aa = 1:numel(fnctn)
        subplot(ceil(sqrt(numel(fnctn))),ceil(sqrt(numel(fnctn))),aa)
        if ~isempty(logScaleLabel)
            fnctn{aa} = log10(fnctn{aa});
        end
        plotFunction2D3D(fnctnSize,fnctn{aa},colorRange,PLOTPAR,cmap,logScaleLabel)
    end
else % the function is an array and is plotted on a single axis
    fnctn_log10 = log10(fnctn);
    if min(fnctn_log10(:))+2 < max(fnctn_log10(:))
        fnctn = fnctn_log10;
        logScaleLabel = '(log scale)';
    else
        logScaleLabel = '';
    end
    
    if ~isempty(logScaleLabel)
        minVal = min(min(fnctn(~isinf(fnctn))));
    else
        minVal = min(min(fnctn(fnctn~=0)));
    end
    colorRange = [-abs(max(fnctn(:)) - minVal)/14 + minVal max(fnctn(:))];
    
    plotFunction2D3D(fnctnSize,fnctn,colorRange,PLOTPAR,cmap,logScaleLabel)
end

drawnow



function [] = plotFunction2D3D(fnctnSize,fnctn,colorRange,PLOTPAR,cmap,logScaleLabel)

if numel(fnctnSize) == 2
    imagesc(fnctn)
    caxis(colorRange)
    set(gca,'Xtick',1:fnctnSize(2),'Ytick',1:fnctnSize(1),'XaxisLocation','bottom')
    hold on
    axis ij; axis image;
    set(gca,'YtickLabel',PLOTPAR.yTicklabel)
    set(gca,'XtickLabel',PLOTPAR.xTicklabel)
    xlabel(PLOTPAR.xLabel,'Fontsize',12,'FontWeight','bold')
    ylabel(PLOTPAR.yLabel,'Fontsize',12,'FontWeight','bold')
    colormap(cmap)
    h_c = colorbar;
    ylabel(h_c,{PLOTPAR.fnctnLabel;logScaleLabel},'Fontsize',12,'FontWeight','bold')
    
elseif numel(fnctnSize) == 3
    h_q = quiver3d(quivYXZ(:,2),quivYXZ(:,1),quivYXZ(:,3),quivVUW(:,2),quivVUW(:,1),quivVUW(:,3),(V-min(V))./(max(V)-min(V)),0);
    set(h_q,'LineWidth',1)
end

