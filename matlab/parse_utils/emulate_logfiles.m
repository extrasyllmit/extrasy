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

%% make up some performance data for simple example
%normal: everything is sent once
perfdata(1).RTScount  = 1;
perfdata(1).CTScount  = 1;
perfdata(1).DATAcount = 1; perfdata(1).DATAprob = 1;
perfdata(1).ACKcount  = 1;


%special case
perfdata(2).RTScount  = 3;
perfdata(2).CTScount  = 0;
perfdata(2).DATAcount = 0; perfdata(2).DATAprob = 1;
perfdata(2).ACKcount  = 0;

%special case
perfdata(3).RTScount  = 4;
perfdata(3).CTScount  = 1;
perfdata(3).DATAcount = 5; perfdata(3).DATAprob = 1;
perfdata(3).ACKcount  = 1;

%special case
perfdata(4).RTScount  = 5;
perfdata(4).CTScount  = 1;
perfdata(4).DATAcount = 0; perfdata(4).DATAprob = 1;
perfdata(4).ACKcount  = 0;

%special case
perfdata(5).RTScount  = 3;
perfdata(5).CTScount  = 1;
perfdata(5).DATAcount = 1; perfdata(5).DATAprob = 1;
perfdata(5).ACKcount  = 0;

%special case
perfdata(6).RTScount  = 2;
perfdata(6).CTScount  = 1;
perfdata(6).DATAcount = 1; perfdata(6).DATAprob = 1;
perfdata(6).ACKcount  = 0;

for k = 7:20
	%special case
	perfdata(k).RTScount  = 2;
	perfdata(k).CTScount  = 1;
	perfdata(k).DATAcount = 1; perfdata(k).DATAprob = 0.5;
	perfdata(k).ACKcount  = 1;
end

inittime = 1349122285.70;
make_fake_logfiles('nodeA_log.xml', 'nodeB_log.xml', perfdata, inittime);

%%
tic
Nsessions = 1e3;

for k = 1:Nsessions
	perfdatalarge(k).RTScount  = round(rand*10);
	perfdatalarge(k).CTScount  = 1;
	perfdatalarge(k).DATAcount = round(rand*10); perfdatalarge(k).DATAprob = 0.7;
	perfdatalarge(k).ACKcount  = 1;	
end
inittime = 1349122285.70;
make_fake_logfiles('nodeA_log_large.xml', 'nodeB_log_large.xml', perfdatalarge, inittime);
toc

