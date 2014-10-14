function save_fig_with_quicklook(fignum,evalTimeRangeUpdated,result_path,filename,qlfiletype,SAVERESULTS)
%%
% This file is part of ExtRaSy
%
% Copyright (C) 2013-2014 Massachusetts Institute of Technology
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
%%

if SAVERESULTS
	strg1 = sprintf('time%ito%is_',round(evalTimeRangeUpdated));
	
	longFileName = fullfile(result_path, [strg1 filename '.fig']);
	if exist(longFileName,'file'), delete(longFileName); end
	saveas(fignum, longFileName, 'fig');
	
	longFileName = fullfile(result_path, [strg1 filename '.' qlfiletype]);
	if exist(longFileName,'file'), delete(longFileName); end
	saveas(fignum, longFileName, 'png');	
end
