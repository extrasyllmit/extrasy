function plotGridworldMovesOnGrid(fnctn,axesHandle,policy,gridWorldActions)
% Plots the gridworld moves for a policy on top of the gridworld matrix

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

if iscell(fnctn)
    fnctnSize = size(fnctn{1});
else
    fnctnSize = size(fnctn);
end

if nargin > 3;
    % Generate learned policy quiver
    [quivYXZ,quivVUW] = genPolicyQuiver(policy,gridWorldActions,fnctnSize);
else
    quivYXZ = [];
    quivVUW = [];
end

axes(axesHandle)
hold on

if numel(fnctnSize) == 2
    if ~isempty(quivVUW)
        h_q = quiver(quivYXZ(:,2),quivYXZ(:,1),quivVUW(:,2),quivVUW(:,1),0);
        set(h_q,'Color',[0 0 0],'LineWidth',1)
    end
elseif numel(fnctnSize) == 3
    h_q = quiver3d(quivYXZ(:,2),quivYXZ(:,1),quivYXZ(:,3),quivVUW(:,2),quivVUW(:,1),quivVUW(:,3),(V-min(V))./(max(V)-min(V)),0);
    set(h_q,'LineWidth',1)
end

