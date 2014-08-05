function [diff_timestamps self_diff_timestamps pkt_diff_timestamps pkt_count delayinfo] = ...
	get_all_delays(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE, inittime)
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
diff_timestamps{1} = get_delays(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE.RTS, inittime);
diff_timestamps{2} = get_delays(nodeB_log, nodeA_log, nodeB_ID, nodeA_ID, PKTCODE.CTS, inittime);
diff_timestamps{3} = get_delays(nodeA_log, nodeB_log, nodeA_ID, nodeB_ID, PKTCODE.DATA, inittime);
diff_timestamps{4} = get_delays(nodeB_log, nodeA_log, nodeB_ID, nodeA_ID, PKTCODE.ACK, inittime);

self_diff_timestamps{1} = get_delays(nodeA_log, nodeA_log, nodeA_ID, nodeB_ID, PKTCODE.RTS, inittime);
self_diff_timestamps{2} = get_delays(nodeB_log, nodeB_log, nodeB_ID, nodeA_ID, PKTCODE.CTS, inittime);
self_diff_timestamps{3} = get_delays(nodeA_log, nodeA_log, nodeA_ID, nodeB_ID, PKTCODE.DATA, inittime);
self_diff_timestamps{4} = get_delays(nodeB_log, nodeB_log, nodeB_ID, nodeA_ID, PKTCODE.ACK, inittime);

[pkt_diff_timestamps{1} pkt_count(1) delayinfo(1)] = get_delays_between_pktCodes(nodeA_log, nodeA_ID, nodeB_ID, [PKTCODE.RTS PKTCODE.CTS], inittime);
[pkt_diff_timestamps{2} pkt_count(2) delayinfo(2)] = get_delays_between_pktCodes(nodeA_log, nodeA_ID, nodeB_ID, [PKTCODE.DATA PKTCODE.ACK], inittime);


