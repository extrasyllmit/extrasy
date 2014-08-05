function [P,Q] = plot_node_stat(node_log, node_ID, mactype, nn, fignum, evalTimeRange)
%%
% This file is part of ExtRaSy
%
% Copyright (C) 2013-2014 Massachusetts Institute of Technology
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
%%
num_nodes = numel(node_log);

other = setdiff((1:num_nodes),nn);
this_node_ID   = node_ID(nn);
other_node_ID = node_ID(other);

%define packet code
PKTCODE.RTS = 1;
PKTCODE.CTS = 2;
PKTCODE.DATA = 3;
PKTCODE.ACK = 4;

%define legal transitions

%%
timeinfo = get_time_info(node_log);

figure(fignum);
subplot(num_nodes,1,nn);
[eventstimeA, eventstimeB] = plot_node_traffic(node_log, node_ID, nn, PKTCODE, timeinfo.inittime);
set(gca,'XLim',[evalTimeRange(1) evalTimeRange(2)]-evalTimeRange(1));
title(sprintf('Node %i packet traffic',nn));

figure(fignum+1);
subplot(num_nodes,2,(nn-1)*2+1); hold on;
bar(1, numel(eventstimeA.RTS), 0.8, 'k')
bar(2, numel(eventstimeB.CTS), 0.8, 'g')
bar(3, numel(eventstimeA.DATA), 0.8, 'b')
bar(4, numel(eventstimeB.ACK), 0.8, 'r')
set(gca,'XTick',(1:4));
set(gca,'XTickLabel',{'RTS','CTS','DATA','ACK'})
box on
ylabel('Tx count')
title(sprintf('N%i->others',nn));

figure(fignum+1);
subplot(num_nodes,2,(nn-1)*2+2); hold on;
bar(1, numel(eventstimeB.RTS), 0.8, 'k')
bar(2, numel(eventstimeA.CTS), 0.8, 'g')
bar(3, numel(eventstimeB.DATA), 0.8, 'b')
bar(4, numel(eventstimeA.ACK), 0.8, 'r')
set(gca,'XTick',(1:4));
set(gca,'XTickLabel',{'RTS','CTS','DATA','ACK'})
box on
ylabel('Tx count')
title(sprintf('others->N%i',nn));

[table_count, table_alldelays] = get_transition_stat(eventstimeA, eventstimeB, PKTCODE);
fnum = fignum+2;
[P,Q] = draw_fsm(table_count, table_alldelays, mactype, 'bytime', nn, fnum);
%[P,Q] = draw_fsm2(table_count, table_alldelays, mactype, 'off', nn, fnum);
fnum = fignum+3;
[P,Q] = draw_fsm(table_count, table_alldelays, mactype, 'bycount', nn, fnum);
%[P,Q] = draw_fsm2(table_count, table_alldelays, mactype, 'off', nn, fnum);

fnum = fignum+4;
figure(fnum); clf
table_count = table_count([1,6,3,8,5,2,7,4],[1,6,3,8,5,2,7,4]);
table_alldelays = table_alldelays([1,6,3,8,5,2,7,4],[1,6,3,8,5,2,7,4]);
alllabels = {'R','(C)','D','(A)','(R)','C','(D)','A'};
axisall = [];
for m = 1:8
	for n = 1:8
		if table_count(m,n) > 0
			subplot(8,8,(m-1)*8+n);
			hist(table_alldelays{m,n}*1e3,100);
			ylabel([alllabels{m} '->' alllabels{n}]);
			title(sprintf('%.1fms (%i)',mean(table_alldelays{m,n})*1e3,table_count(m,n)));
			ax = axis;
			axisall = [axisall; axis];
		end
	end
end
set(gcf,'PaperOrientation','landscape')
set(gcf,'PaperPosition',[0 0 11 8.5])

% axis_max = [min(axisall(:,1)) max(axisall(:,2)) min(axisall(:,3)) max(axisall(:,4))];
% for m = 1:8
% 	for n = 1:8
% 		if table_count(m,n) > 0
% 			subplot(8,8,(m-1)*8+n);
% 			axis(axis_max);
% 		end
% 	end
% end

%disp('check fsm');
%keyboard


