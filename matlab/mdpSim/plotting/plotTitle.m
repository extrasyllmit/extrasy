function [] = plotTitle(AGNT,ENV)
% Adds title information to a plot

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

alphaText = [num2str(AGNT.USR.alphaVal),' ',AGNT.USR.alphaPolicy];
epsText = [num2str(AGNT.USR.epsVal),' ',AGNT.USR.epsPolicy];
gammaText = num2str(AGNT.USR.gammaVal);
lambdaText = num2str(AGNT.USR.lambdaVal);

title({['[ENV] P: ',ENV.USR.modelForP,', R: ',ENV.USR.modelForR,' Task: ',ENV.taskType]; ...
       ['[AGNT] ',AGNT.USR.algorithm,',  \alpha=',alphaText,', \epsilon=',epsText,...
       ',  \gamma=',gammaText,',  \lambda=',lambdaText];...
       ['SimTimeStamp: ',datestr(now,30)]},'Interpreter','Tex')
