function plot_raw_logs(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE)
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
warning('this function is no longer supported.');
return


hold on;

inittime = min(str2num(nodeA_log(1).timestamp),str2num(nodeB_log(1).timestamp));
endtime = max(str2num(nodeA_log(end).timestamp),str2num(nodeB_log(end).timestamp));

for n = 1:numel(nodeA_log)
	t = str2num(nodeA_log(n).timestamp) - inittime;
	pktCode = str2num(nodeA_log(n).pktCode);
	
	direction = nodeA_log(n).direction;
	fromID = str2num(nodeA_log(n).fromID);
	
	if isequal(direction,'transmit')
		y0 = 0;
		marker = '^';
	elseif isequal(direction,'receive')
		y0 = 1;
		if fromID == nodeA_ID
			marker = 'o';
		else
			marker = '^';
		end
	else
		y0 = 10;
		marker = '*';
		warning('unknown direction');
	end
	
	if pktCode == PKTCODE.RTS
		plot(t,y0,['k' marker],'MarkerSize',8,'LineWidth',2);
	elseif pktCode == PKTCODE.CTS
		plot(t,y0,['g' marker],'MarkerSize',8,'LineWidth',2);
	elseif pktCode == PKTCODE.DATA
		plot(t,y0,['b' marker],'MarkerSize',8,'LineWidth',2);
	elseif pktCode == PKTCODE.ACK
		plot(t,y0,['r' marker],'MarkerSize',8,'LineWidth',2);
	else
		warning('unknown packet code found at %i',n);
	end
end


for n = 1:numel(nodeB_log)
	t = str2num(nodeB_log(n).timestamp) - inittime;
	pktCode = str2num(nodeB_log(n).pktCode);
	
	direction = nodeB_log(n).direction;
	fromID = str2num(nodeB_log(n).fromID);
	
	if isequal(direction,'transmit')
		y0 = 2;
		marker = 'v';
	elseif isequal(direction,'receive')
		y0 = 3;
		if fromID == nodeB_ID
			marker = 'o';
		else
			marker = 'v';
		end
	else
		y0 = 10;
		marker = '*';
		warning('unknown direction');
	end
	
	if pktCode == PKTCODE.RTS
		plot(t,y0,['k' marker],'MarkerSize',8,'LineWidth',2);
	elseif pktCode == PKTCODE.CTS
		plot(t,y0,['g' marker],'MarkerSize',8,'LineWidth',2);
	elseif pktCode == PKTCODE.DATA
		plot(t,y0,['b' marker],'MarkerSize',8,'LineWidth',2);
	elseif pktCode == PKTCODE.ACK
		plot(t,y0,['r' marker],'MarkerSize',8,'LineWidth',2);
	else
		warning('unknown packet code found at %i',n);
	end
end

box on
grid on
set(gca,'ylim',[-1 4])
set(gca,'YTick',[0:3])
set(gca,'YTickLabel',{'NodeA-Tx','NodeA-Rx','NodeB-Tx','NodeB-Rx'})

