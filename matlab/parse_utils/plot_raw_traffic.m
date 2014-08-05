function plot_raw_traffic(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE, inittime)
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

y_A_tx = 0;
y_A_rx = 1;
y_B_tx = 2;
y_B_rx = 3;

%find indices with valid transmit (or receive)
ii_valid_A_tx = refine_log(nodeA_log,'direction','transmit');
ii_valid_A_rx = refine_log(nodeA_log,'direction','receive');

ii_valid_B_tx = refine_log(nodeB_log,'direction','transmit');
ii_valid_B_rx = refine_log(nodeB_log,'direction','receive');

ii_A_RTS  = plot_pktCode(nodeA_log(ii_valid_A_tx),PKTCODE.RTS, nodeA_ID,nodeB_ID,y_A_tx,'k','^',inittime);%1
ii_A_CTS  = plot_pktCode(nodeA_log(ii_valid_A_tx),PKTCODE.CTS, nodeA_ID,nodeB_ID,y_A_tx,'g','^',inittime);%3'
ii_A_DATA = plot_pktCode(nodeA_log(ii_valid_A_tx),PKTCODE.DATA,nodeA_ID,nodeB_ID,y_A_tx,'b','^',inittime);%5
ii_A_ACK  = plot_pktCode(nodeA_log(ii_valid_A_tx),PKTCODE.ACK, nodeA_ID,nodeB_ID,y_A_tx,'r','^',inittime);%7'

ii_A_All = (1:numel(ii_valid_A_tx));
ii_A_Legit = [ii_A_RTS ii_A_CTS ii_A_DATA ii_A_ACK];
ii_A_Else = setdiff(ii_A_All, ii_A_Legit);

timestamps = get_timestamps(nodeA_log(ii_valid_A_tx(ii_A_Else)));
if ~isempty(timestamps)
	plot(timestamps-inittime,y_A_tx, 'y*','MarkerSize',12,'LineWidth',2);
end

ii_B_RTS  = plot_pktCode(nodeB_log(ii_valid_B_rx),PKTCODE.RTS, nodeA_ID,nodeB_ID,y_B_rx,'k','v',inittime);%2
ii_B_CTS  = plot_pktCode(nodeB_log(ii_valid_B_rx),PKTCODE.CTS, nodeA_ID,nodeB_ID,y_B_rx,'g','v',inittime);%4'
ii_B_DATA = plot_pktCode(nodeB_log(ii_valid_B_rx),PKTCODE.DATA,nodeA_ID,nodeB_ID,y_B_rx,'b','v',inittime);%6
ii_B_ACK  = plot_pktCode(nodeB_log(ii_valid_B_rx),PKTCODE.ACK, nodeA_ID,nodeB_ID,y_B_rx,'r','v',inittime);%8'

ii_B_All = (1:numel(ii_valid_B_rx));
ii_B_Legit = [ii_B_RTS ii_B_CTS ii_B_DATA ii_B_ACK];
ii_B_Else = setdiff(ii_B_All, ii_B_Legit);

timestamps = get_timestamps(nodeB_log(ii_valid_B_rx(ii_B_Else)));
if ~isempty(timestamps)
	plot(timestamps-inittime,y_B_rx, 'y*','MarkerSize',12,'LineWidth',2);
end


%%
ii_B_RTS  = plot_pktCode(nodeB_log(ii_valid_B_tx),PKTCODE.RTS, nodeB_ID,nodeA_ID,y_B_tx,'k','v',inittime);%1'
ii_B_CTS  = plot_pktCode(nodeB_log(ii_valid_B_tx),PKTCODE.CTS, nodeB_ID,nodeA_ID,y_B_tx,'g','v',inittime);%3
ii_B_DATA  = plot_pktCode(nodeB_log(ii_valid_B_tx),PKTCODE.DATA,nodeB_ID,nodeA_ID,y_B_tx,'b','v',inittime);%5'
ii_B_ACK  = plot_pktCode(nodeB_log(ii_valid_B_tx),PKTCODE.ACK, nodeB_ID,nodeA_ID,y_B_tx,'r','v',inittime);%7

ii_B_All = (1:numel(ii_valid_B_tx));
ii_B_Legit = [ii_B_RTS ii_B_CTS ii_B_DATA ii_B_ACK];
ii_B_Else = setdiff(ii_B_All, ii_B_Legit);

timestamps = get_timestamps(nodeB_log(ii_valid_B_tx(ii_B_Else)));
if ~isempty(timestamps)
	plot(timestamps-inittime,y_B_tx, 'y*','MarkerSize',12,'LineWidth',2);
end

ii_A_RTS  = plot_pktCode(nodeA_log(ii_valid_A_rx),PKTCODE.RTS, nodeB_ID,nodeA_ID,y_A_rx,'k','^',inittime);%2'
ii_A_CTS  = plot_pktCode(nodeA_log(ii_valid_A_rx),PKTCODE.CTS, nodeB_ID,nodeA_ID,y_A_rx,'g','^',inittime);%4
ii_A_DATA = plot_pktCode(nodeA_log(ii_valid_A_rx),PKTCODE.DATA,nodeB_ID,nodeA_ID,y_A_rx,'b','^',inittime);%6'
ii_A_ACK  = plot_pktCode(nodeA_log(ii_valid_A_rx),PKTCODE.ACK, nodeB_ID,nodeA_ID,y_A_rx,'r','^',inittime);%8

ii_A_All = (1:numel(ii_valid_A_rx));
ii_A_Legit = [ii_A_RTS ii_A_CTS ii_A_DATA ii_A_ACK];
ii_A_Else = setdiff(ii_A_All, ii_A_Legit);

timestamps = get_timestamps(nodeA_log(ii_valid_A_rx(ii_A_Else)));
if ~isempty(timestamps)
	plot(timestamps-inittime,y_A_rx, 'y*','MarkerSize',12,'LineWidth',2);
end

box on
grid on
xlabel('Time (s)')
set(gca,'ylim',[-1 4])
set(gca,'YTick',(0:3))
set(gca,'YTickLabel',{'NodeA-Tx','NodeA-Rx','NodeB-Tx','NodeB-Rx'})



function ii_pktCode_fromID_toID = plot_pktCode(node_log,pkt_code,from_nodeID,to_nodeID,y0,color,marker,inittime)
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
if ~isempty(timestamps)
	plot(timestamps-inittime,y0, [color marker],'MarkerSize',12,'LineWidth',2);
end

%timestamps = get_timestamps(node_log(ii_pktCode_fromID_toID_not));
%if ~isempty(timestamps)
%	plot(timestamps-inittime,y0, [color 'o'],'MarkerSize',12,'LineWidth',2);
%end

