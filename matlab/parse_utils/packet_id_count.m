function [link1cnt,link2cnt] = packet_id_count(nodeA_log,nodeB_log,nodeA_ID,nodeB_ID,packetID)
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
for k = 1:4
	[ii timestamps] = filter_log(nodeA_log,'transmit',nodeA_ID,nodeB_ID,k);
	cnt1(k,1) = numel(refine_log(nodeA_log(ii),'packetid',packetID));
	[ii timestamps] = filter_log(nodeB_log,'receive',nodeA_ID,nodeB_ID,k);
	cnt1(k,2) = numel(refine_log(nodeB_log(ii),'packetid',packetID));
end

for k = 1:4
	[ii timestamps] = filter_log(nodeB_log,'transmit',nodeB_ID,nodeA_ID,k);
	cnt2(k,1) = numel(refine_log(nodeB_log(ii),'packetid',packetID));
	[ii timestamps] = filter_log(nodeA_log,'receive',nodeB_ID,nodeA_ID,k);
	cnt2(k,2) = numel(refine_log(nodeA_log(ii),'packetid',packetID));
end


link1cnt = [cnt1(1,:); cnt2(2,:); cnt1(3,:); cnt2(4,:)];
link2cnt = [cnt2(1,:); cnt1(2,:); cnt2(3,:); cnt1(4,:)];
