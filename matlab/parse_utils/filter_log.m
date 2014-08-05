function [ii_valid alltimestamps_num] = filter_log(node_log,direction,from_nodeID,to_nodeID,pktCode)
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
%%[ii_valid alltimestamps_num] = filter_log(node_log,direction,from_nodeID,to_nodeID,pktCode)

%find indices with valid transmit (or receive)
ii_valid_trx = refine_log(node_log,'direction',direction);

%if direction is 'receive', also make sure crcpass is True, otherwise, the
%rest may be invalid
if isequal(lower(direction),'receive')
	%filter out those don't pass crc
	ii = refine_log(node_log(ii_valid_trx),'crcpass','True');
	ii_valid_trx = ii_valid_trx(ii);
end

%refine to match from_nodeID
ii = refine_log(node_log(ii_valid_trx),'fromID',from_nodeID);
ii_valid_trx_A = ii_valid_trx(ii);

%refine to match to_nodeID
ii = refine_log(node_log(ii_valid_trx_A),'toID',to_nodeID);
ii_valid_trx_AtoB = ii_valid_trx_A(ii);


%out of those with valid transmits from A to B, find pktCode with DATA code
ii = refine_log(node_log(ii_valid_trx_AtoB),'pktCode',pktCode);
ii_valid_trx_AtoB_PKT = ii_valid_trx_AtoB(ii);

if isempty(ii_valid_trx_AtoB_PKT)
	ii_valid = [];
	alltimestamps_num = [];
	return
end

%get to validate filtered results
[ii, alltimestamps] = xml_arraygetfields(node_log(ii_valid_trx_AtoB_PKT),{'timestamp'});
alltimestamps_num = cellfun(@str2double,alltimestamps,'UniformOutput',true);
ii_valid = ii_valid_trx_AtoB_PKT(ii);