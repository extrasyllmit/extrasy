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
logtxt = fileread('logrx1.xml');
v_xml = xml_parseany(logtxt);

v = xml_repackage(v_xml);

% ii is array of numbers
% allFromIDs is cell array of strings
[iiFromIDs, tempFromIDs] = xml_arraygetfields(v,{'fromID'});

%if you know if field contains number instead of strings
%convert cell array of strings to array of numbers
allFromIDs = cellfun(@str2num,tempFromIDs,'UniformOutput',true)

[iiTimestamp, tempTimestamp] = xml_arraygetfields(v,{'timestamp'});
allTiemstamp = cellfun(@str2num,tempTimestamp,'UniformOutput',true)


%example converting 'True'/'False' to 1/0
[iiCrcpass, tempCrcpass] = xml_arraygetfields(v,{'crcpass'});
allCrcpass = cellfun(@(x) isequal(lower(x),'true')||isequal(lower(x),'1'),tempCrcpass,'UniformOutput',true)

%example converting 'True'/'False' or '1'/'0'to 1/0
[iiFecpass, tempFecpass] = xml_arraygetfields(v,{'fecpass'});
allFecpass = cellfun(@(x) isequal(lower(x),'true')||isequal(lower(x),'1'),tempFecpass,'UniformOutput',true)

tic
maclogtxt = fileread('exampleMacLogEdited.xml');
maclog_xml = xml_parseany(maclogtxt);
maclog = xml_repackage(maclog_xml);
toc

%alternatively, if xml is very very large.  maclog2 should equal maclog
tic
maclog2 = xml_readandparse('exampleMacLogEdited.xml','node_state');
toc

%pretend one is not csma
maclog(4).mac.type = 'tdma';
[ii_type, alltypes] = xml_arraygetfields(maclog,{'mac','type'});

%ii_csma is a list of all node states with csma as mac/type
ii_csma = find(cellfun(@(x) isequal(x,'csma'), alltypes));

ii_csma_type = ii_type(ii_csma);
[ii_timestamp, csma_timestamps] = xml_arraygetfields(maclog(ii_csma_type),{'timestamp'});

%indices that give valid timestamps for all csma types
%timestamps are in csma_timestamps
ii_timestamp_csma_type = ii_csma_type(ii_timestamp);




