function [table_count, table_alldelays] = get_transition_stat(eventstimeA, eventstimeB, PKTCODE)
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
allstatsA.time   = [eventstimeA.RTS eventstimeA.CTS eventstimeA.DATA eventstimeA.ACK];
allstatsA.pkcode = [repmat(PKTCODE.RTS,1,numel(eventstimeA.RTS)) ...
	                repmat(PKTCODE.CTS,1,numel(eventstimeA.CTS)) ...
	                repmat(PKTCODE.DATA,1,numel(eventstimeA.DATA)) ...
	                repmat(PKTCODE.ACK,1,numel(eventstimeA.ACK))];

allstatsB.time   = [eventstimeB.RTS eventstimeB.CTS eventstimeB.DATA eventstimeB.ACK];
allstatsB.pkcode = [repmat(PKTCODE.RTS,1,numel(eventstimeB.RTS)) ...
	                repmat(PKTCODE.CTS,1,numel(eventstimeB.CTS)) ...
	                repmat(PKTCODE.DATA,1,numel(eventstimeB.DATA)) ...
	                repmat(PKTCODE.ACK,1,numel(eventstimeB.ACK))];
				
s = struct('time',0,'pkcode',0,'direction',0);
N = numel(allstatsA.time) + numel(allstatsB.time);
allstats = repmat(s,1,N);
%keyboard
table_count = zeros(8,8);
table_alldelays = cell(8);

if N>0
	temp = num2cell([allstatsA.time   allstatsB.time]);
	[allstats.time]      = deal(temp{:});

	temp = num2cell([allstatsA.pkcode allstatsB.pkcode]);
	[allstats.pkcode]    = deal(temp{:});

	temp = num2cell([ones(1,numel(allstatsA.time)) 2*ones(1,numel(allstatsB.time))]);
	[allstats.direction] = deal(temp{:});

	[~,idx] = sort([allstats.time]);
	
	%sort by increasing time stamps
	allstats = allstats(idx);
	
	current = allstats(1);
	row = current.pkcode + (current.direction-1)*4;
	
	for k = 2:numel(allstats)
		next = allstats(k);
		column = next.pkcode + (next.direction-1)*4;
		
		table_count(row,column) = table_count(row,column) + 1;
		
		delay = next.time - current.time;
		table_alldelays{row,column} = [table_alldelays{row,column} delay];
		
		current = next;
		row = column;
	end
end