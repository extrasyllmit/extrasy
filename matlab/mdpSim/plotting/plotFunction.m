function [axesHandle] = plotFunction(windowTitle,fnctn,PLOTPAR)
% plots one of the matrix-valued function associated with learning

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

switch PLOTPAR.cmap
    case 'gray'
        cmap = flipud(gray(256));
        cmap = [[1 1 1];cmap(32:end,:)];
    case 'rainbow'
        cmap = jet(9);
end

nfigure(windowTitle)
if numel(fnctnSize) == 2
    imagesc(fnctn);
    axesHandle = gca;
    set(axesHandle,'Xtick',1:fnctnSize(2),'Ytick',1:fnctnSize(1),'XaxisLocation','bottom')
    hold on
    axis ij; axis image;
    set(axesHandle,'YtickLabel',PLOTPAR.yTicklabel)
    set(axesHandle,'XtickLabel',PLOTPAR.xTicklabel)
    xlabel(PLOTPAR.xLabel,'Fontsize',12,'FontWeight','bold')
    ylabel(PLOTPAR.yLabel,'Fontsize',12,'FontWeight','bold')
    colormap(cmap)
    h_c = colorbar;
    ylabel(h_c,PLOTPAR.fnctnLabel,'Fontsize',12,'FontWeight','bold')    
end

