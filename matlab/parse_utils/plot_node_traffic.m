function [eventstimeA, eventstimeB] = plot_node_traffic(node_log, node_ID, nn, PKTCODE, inittime)
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
hold on;

num_nodes = numel(node_log);

other = setdiff((1:num_nodes),nn);
this_node_ID   = node_ID(nn);
other_node_ID = node_ID(other);

%to simplify naming convention, A is this node and B represents all other nodes
y_A_tx = 0;
y_B_tx = 1;

%find indices with valid transmit
ii_valid_A_tx = refine_log(node_log{nn},'direction','transmit');

for k = 1:numel(other)
	eventstime_A_RTS{k}  = plot_new_pktCode(node_log{nn}(ii_valid_A_tx),PKTCODE.RTS, this_node_ID,other_node_ID(k),y_A_tx,'k','^',inittime);%1
	eventstime_A_CTS{k}  = plot_new_pktCode(node_log{nn}(ii_valid_A_tx),PKTCODE.CTS, this_node_ID,other_node_ID(k),y_A_tx,'g','^',inittime);%3'
	eventstime_A_DATA{k} = plot_new_pktCode(node_log{nn}(ii_valid_A_tx),PKTCODE.DATA,this_node_ID,other_node_ID(k),y_A_tx,'b','^',inittime);%5
	eventstime_A_ACK{k}  = plot_new_pktCode(node_log{nn}(ii_valid_A_tx),PKTCODE.ACK, this_node_ID,other_node_ID(k),y_A_tx,'r','^',inittime);%7'
end

eventstimeA.RTS  = [eventstime_A_RTS{:}];
eventstimeA.CTS  = [eventstime_A_CTS{:}];
eventstimeA.DATA = [eventstime_A_DATA{:}];
eventstimeA.ACK  = [eventstime_A_ACK{:}];

for k = 1:numel(other)
	ii_valid_B_tx = refine_log(node_log{other(k)},'direction','transmit');

	eventstime_B_RTS{k}  = plot_new_pktCode(node_log{other(k)}(ii_valid_B_tx),PKTCODE.RTS, other_node_ID(k),this_node_ID,y_B_tx,'k','v',inittime);%2
	eventstime_B_CTS{k}  = plot_new_pktCode(node_log{other(k)}(ii_valid_B_tx),PKTCODE.CTS, other_node_ID(k),this_node_ID,y_B_tx,'g','v',inittime);%4'
	eventstime_B_DATA{k} = plot_new_pktCode(node_log{other(k)}(ii_valid_B_tx),PKTCODE.DATA,other_node_ID(k),this_node_ID,y_B_tx,'b','v',inittime);%6
	eventstime_B_ACK{k}  = plot_new_pktCode(node_log{other(k)}(ii_valid_B_tx),PKTCODE.ACK, other_node_ID(k),this_node_ID,y_B_tx,'r','v',inittime);%8'
end

eventstimeB.RTS  = [eventstime_B_RTS{:}];
eventstimeB.CTS  = [eventstime_B_CTS{:}];
eventstimeB.DATA = [eventstime_B_DATA{:}];
eventstimeB.ACK  = [eventstime_B_ACK{:}];

box on
grid on
xlabel('Time (s)')
set(gca,'ylim',[-1 2])
set(gca,'YTick',(0:1))
set(gca,'YTickLabel',{sprintf('N%i->others',nn),sprintf('others->N%i',nn)})



function eventstime = plot_new_pktCode(node_log,pkt_code,from_nodeID,to_nodeID,y0,color,marker,inittime)
%refine to all valid transmit with RTS
ii_pktCode = refine_log(node_log,'pktCode',pkt_code);

%refine to match from_nodeID
ii = refine_log(node_log(ii_pktCode),'fromID',from_nodeID);
ii_pktCode_fromID = ii_pktCode(ii);

%refine to match to_nodeID
ii = refine_log(node_log(ii_pktCode_fromID),'toID',to_nodeID);
ii_pktCode_fromID_toID = ii_pktCode_fromID(ii);
%ii_pktCode_fromID_toID_not = setdiff(ii_pktCode, ii_pktCode_fromID_toID);

%get time stamps and plot
timestamps = get_timestamps(node_log(ii_pktCode_fromID_toID));
eventstime = timestamps-inittime;
if ~isempty(timestamps)
	plot(eventstime,y0, [color marker],'MarkerSize',12,'LineWidth',2);
end






