function vargout = nfigure(figTitle,figNum)

% figNum = nfigure(figTitle,figNum)
% 
% Creates a new figure where the figure's window is titled with the
% string figTitle instead of 'Figure #'. figNum is optional and
% causes the figure to be created having the figure handle equal to figNum.
% 

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
    figNum = figure;
elseif nargin == 2
    figNum = figure(figNum);
else
    figNum = figure;
    figTitle = '';
end

set(figNum,'NumberTitle','off','Name',[num2str(figNum),': ',figTitle]);

set(figNum,'Color','w')

if nargout == 1
    vargout = {figNum};
end
