function make_fake_logfiles(nodeA_logfilename, nodeB_logfilename, perfdata, inittime)
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
% define packet code
PKTCODE.RTS  = 1;
PKTCODE.CTS  = 2;
PKTCODE.DATA = 3;
PKTCODE.ACK  = 4;

nodeA_ID = 17;
nodeB_ID = 19;

%% Node A : send RTS and DATA
fid = fopen(nodeA_logfilename,'w');

if fid==-1
	error('cannot open file Node A tx log')
end

timecount = inittime;

RTSID = 0;
DATAID = 0;

probarray = zeros(1,numel(perfdata));

for n = 1:numel(perfdata)
	probarray(n) = rand;
	
	for m = 1:perfdata(n).RTScount
		fprintf(fid,'<packet>\n');
		fprintf(fid,'    <direction>transmit</direction>\n');
		fprintf(fid,'    <messagelength>2000</messagelength>\n');
		fprintf(fid,'    <toID>%i</toID>\n',nodeB_ID);
		fprintf(fid,'    <macCode>0</macCode>\n');
		fprintf(fid,'    <fromID>%i</fromID>\n',nodeA_ID);
		timecount = timecount + 0.1;
		fprintf(fid,'    <timestamp>%0.2f</timestamp>\n',timecount);
		fprintf(fid,'    <pktCode>%i</pktCode>\n',PKTCODE.RTS);
		fprintf(fid,'    <phyCode>0</phyCode>\n');
		RTSID = RTSID + 1;
		fprintf(fid,'    <packetid>%i</packetid>\n',RTSID);
		fprintf(fid,'</packet>\n');
	end
	
	timecount = timecount + 0.1;
	
	if perfdata(n).CTScount > 0
		fprintf(fid,'<packet>\n');
		fprintf(fid,'    <direction>receive</direction>\n');
		fprintf(fid,'    <messagelength>2000</messagelength>\n');
		fprintf(fid,'    <toID>%i</toID>\n',nodeA_ID);
		fprintf(fid,'    <macCode>0</macCode>\n');
		fprintf(fid,'    <fromID>%i</fromID>\n',nodeB_ID);
		fprintf(fid,'    <timestamp>%0.2f</timestamp>\n',timecount);
		fprintf(fid,'    <pktCode>%i</pktCode>\n',PKTCODE.CTS);
		fprintf(fid,'    <phyCode>0</phyCode>\n');
		fprintf(fid,'    <packetid>%i</packetid>\n',RTSID);
		fprintf(fid,'</packet>\n');
	end	
	
	DATAID = DATAID + 1;
	for m = 1:perfdata(n).DATAcount
		fprintf(fid,'<packet>\n');
		fprintf(fid,'    <direction>transmit</direction>\n');
		fprintf(fid,'    <messagelength>2000</messagelength>\n');
		fprintf(fid,'    <toID>%i</toID>\n',nodeB_ID);
		fprintf(fid,'    <macCode>0</macCode>\n');
		fprintf(fid,'    <fromID>%i</fromID>\n',nodeA_ID);
		timecount = timecount + 0.1;
		fprintf(fid,'    <timestamp>%0.2f</timestamp>\n',timecount);
		fprintf(fid,'    <pktCode>%i</pktCode>\n',PKTCODE.DATA);
		fprintf(fid,'    <phyCode>0</phyCode>\n');
		fprintf(fid,'    <packetid>%i</packetid>\n',DATAID);
		fprintf(fid,'</packet>\n');
	end	
	
	timecount = timecount + 0.1;
	
	if (perfdata(n).ACKcount > 0) && (probarray(n) < perfdata(n).DATAprob)
		fprintf(fid,'<packet>\n');
		fprintf(fid,'    <direction>receive</direction>\n');
		fprintf(fid,'    <messagelength>2000</messagelength>\n');
		fprintf(fid,'    <toID>%i</toID>\n',nodeA_ID);
		fprintf(fid,'    <macCode>0</macCode>\n');
		fprintf(fid,'    <fromID>%i</fromID>\n',nodeB_ID);
		fprintf(fid,'    <timestamp>%0.2f</timestamp>\n',timecount);
		fprintf(fid,'    <pktCode>%i</pktCode>\n',PKTCODE.ACK);
		fprintf(fid,'    <phyCode>0</phyCode>\n');
		fprintf(fid,'    <packetid>%i</packetid>\n',DATAID);
		fprintf(fid,'</packet>\n');
	end			
end


fclose(fid);

%% Node B : receive RTS and DATA
fid = fopen(nodeB_logfilename,'w');

if fid==-1
	error('cannot open file Node B rx log')
end

timecount = inittime;

RTSID = 0;
DATAID = 0;

for n = 1:numel(perfdata)
	for m = 1:perfdata(n).RTScount
		timecount = timecount + 0.1;
		RTSID = RTSID + 1;
		
		fprintf(fid,'<packet>\n');
		fprintf(fid,'    <direction>receive</direction>\n');
		fprintf(fid,'    <messagelength>2000</messagelength>\n');
		fprintf(fid,'    <toID>%i</toID>\n',nodeB_ID);
		fprintf(fid,'    <macCode>0</macCode>\n');
		fprintf(fid,'    <fecpass>1</fecpass>\n');
		fprintf(fid,'    <fromID>%i</fromID>\n',nodeA_ID);
		fprintf(fid,'    <timestamp>%0.2f</timestamp>\n',timecount);
		fprintf(fid,'    <crcpass>1</crcpass>\n');
		fprintf(fid,'    <pktCode>%i</pktCode>\n',PKTCODE.RTS);
		fprintf(fid,'    <phyCode>0</phyCode>\n');
		fprintf(fid,'    <packetid>%i</packetid>\n',RTSID);
		fprintf(fid,'</packet>\n');
	end
	
	timecount = timecount + 0.1;

	if perfdata(n).CTScount > 0
		fprintf(fid,'<packet>\n');
		fprintf(fid,'    <direction>transmit</direction>\n');
		fprintf(fid,'    <messagelength>2000</messagelength>\n');
		fprintf(fid,'    <toID>%i</toID>\n',nodeA_ID);
		fprintf(fid,'    <macCode>0</macCode>\n');
		fprintf(fid,'    <fecpass>1</fecpass>\n');
		fprintf(fid,'    <fromID>%i</fromID>\n',nodeB_ID);
		fprintf(fid,'    <timestamp>%0.2f</timestamp>\n',timecount);
		fprintf(fid,'    <crcpass>1</crcpass>\n');
		fprintf(fid,'    <pktCode>%i</pktCode>\n',PKTCODE.CTS);
		fprintf(fid,'    <phyCode>0</phyCode>\n');
		fprintf(fid,'    <packetid>%i</packetid>\n',RTSID);
		fprintf(fid,'</packet>\n');
	end
	
	
	DATAID = DATAID + 1;
	for m = 1:perfdata(n).DATAcount
		timecount = timecount + 0.1;

		if probarray(n) < perfdata(n).DATAprob
			fprintf(fid,'<packet>\n');
			fprintf(fid,'    <direction>receive</direction>\n');
			fprintf(fid,'    <messagelength>2000</messagelength>\n');
			fprintf(fid,'    <toID>%i</toID>\n',nodeB_ID);
			fprintf(fid,'    <macCode>0</macCode>\n');
			fprintf(fid,'    <fecpass>1</fecpass>\n');
			fprintf(fid,'    <fromID>%i</fromID>\n',nodeA_ID);
			fprintf(fid,'    <timestamp>%0.2f</timestamp>\n',timecount);
			fprintf(fid,'    <crcpass>%i</crcpass>\n',mod(round(timecount*10),2));
			fprintf(fid,'    <pktCode>%i</pktCode>\n',PKTCODE.DATA);
			fprintf(fid,'    <phyCode>0</phyCode>\n');
			fprintf(fid,'    <packetid>%i</packetid>\n',DATAID);
			fprintf(fid,'</packet>\n');
		end
	end
	
	timecount = timecount + 0.1;
	
	if (perfdata(n).ACKcount > 0) && (probarray(n) < perfdata(n).DATAprob)
		fprintf(fid,'<packet>\n');
		fprintf(fid,'    <direction>transmit</direction>\n');
		fprintf(fid,'    <messagelength>2000</messagelength>\n');
		fprintf(fid,'    <toID>%i</toID>\n',nodeA_ID);
		fprintf(fid,'    <macCode>0</macCode>\n');
		fprintf(fid,'    <fecpass>1</fecpass>\n');
		fprintf(fid,'    <fromID>%i</fromID>\n',nodeB_ID);
		fprintf(fid,'    <timestamp>%0.2f</timestamp>\n',timecount);
		fprintf(fid,'    <crcpass>1</crcpass>\n');
		fprintf(fid,'    <pktCode>%i</pktCode>\n',PKTCODE.ACK);
		fprintf(fid,'    <phyCode>0</phyCode>\n');
		fprintf(fid,'    <packetid>%i</packetid>\n',DATAID);
		fprintf(fid,'</packet>\n');
	end	

end

fclose(fid);

