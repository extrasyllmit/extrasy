function TestConfig = get_sweep_results(sweep_name,linux_home_path)
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
if nargin < 2
    linux_home_path = '/home/g103homes/a/tri';
end

central_result_path = '/home/bdworker1/a/SDR/Sweep';

load(fullfile(linux_home_path,'generalized-sdr-comms/gr-digital_ll/matlab',[sweep_name '.mat']), 'TestConfig')


skippedTests = [];
for tt = 1:numel(TestConfig)
	%update logs_path since data is moved to bdworker1
	[~,TestN,~] = fileparts(TestConfig(tt).logs_path);
	TestConfig(tt).logs_path = fullfile(central_result_path,sweep_name,TestN);
	TestConfig(tt).packetstat = [];
	
	dd = dir(fullfile(TestConfig(tt).logs_path,'Result*'));
	
	if numel(dd) == 0
		skippedTests = [skippedTests tt];
		fprintf('... Result directory for test %i not found.  Test skipped\n',tt);
	else
		dn = zeros(1,numel(dd));
		for k = 1:numel(dd)
			dn(k) = datenum(dd(k).date);
		end
		[~,mxi] = max(dn); %find out latest datenum for latest run
		
		result_dir = fullfile(TestConfig(tt).logs_path, dd(mxi).name);
	
		evalnodesets = TestConfig(tt).sets_evalnodes;
		
		evalTimeRangeAll = zeros(numel(evalnodesets),2);
		
		for k = 1:numel(evalnodesets)
			dk = dir(fullfile(result_dir,sprintf('*_node%iand%i_results.mat',evalnodesets{k})));
			if numel(dk)==0
				skippedTests = [skippedTests tt];
				fprintf('... Result mat for test %i not found.  Test skipped\n',tt);
				break
			else
				fprintf('... Result mat for test %i found.\n',tt);
				result_mat = fullfile(result_dir,dk(1).name);
				
				load(result_mat,'bitpersec_total');
				TestConfig(tt).bitpersec(k) = mean(bitpersec_total);
				
				load(result_mat,'evalTimeRange');
				evalTimeRangeAll(k,:) = evalTimeRange;
				
				load(result_mat,'packetstat');
				TestConfig(tt).packetstat = [TestConfig(tt).packetstat packetstat];
			end
		end
		TestConfig(tt).evalTime = diff(min(evalTimeRangeAll,[],1));
		temp_rts  = sum(reshape([TestConfig(tt).packetstat.rts],2,numel(evalnodesets)*2),2);
		temp_cts  = sum(reshape([TestConfig(tt).packetstat.cts],2,numel(evalnodesets)*2),2);
		temp_data = sum(reshape([TestConfig(tt).packetstat.data],2,numel(evalnodesets)*2),2);
		temp_ack  = sum(reshape([TestConfig(tt).packetstat.ack],2,numel(evalnodesets)*2),2);
		TestConfig(tt).packetcnt = [temp_rts.', temp_cts.', temp_data.', temp_ack.'];
	end	
end

validTests = setdiff((1:numel(TestConfig)),skippedTests);
for k = 1:numel(validTests)
	v = validTests(k);
	TestConfig(v).bitpersec_network = sum(TestConfig(v).bitpersec);
end

for k = 1:numel(skippedTests)
	v = skippedTests(k);
	TestConfig(v).bitpersec_network = 0;
end

