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
%% specifying test configurations for each trial

%add path to xml_toolbox
addpath('./jsonlab');
addpath('./parse_utils');
addpath('./parse_utils/xml_toolbox');

home_path = '/home/g103homes/a/tri';
sweep_name = 'Sweep_Phy120_Mac1536';

central_result_path = '/home/bdworker1/a/SDR/Sweep';

load([sweep_name '.mat']);

%% specify selected trials and how much time to process
TrialsToRun = 1:numel(TestConfig);
	
	
%% checking to make sure all xml exist
action_count = 0;
for tt = TrialsToRun
	%update logs_path since data is moved to bdworker1
	[~,TestN,~] = fileparts(TestConfig(tt).logs_path);
	TestConfig(tt).logs_path = fullfile(central_result_path,sweep_name,TestN);

	dd = dir(fullfile(TestConfig(tt).logs_path,sprintf('Node%i*',1)));
		
	result_dir = ['Result_' dd(1).name(end-14:end)];
	full_result_dir = fullfile(TestConfig(tt).logs_path,result_dir);
	
	old_result_dir = ['Old_' dd(1).name(end-14:end)];
	full_old_result_dir = fullfile(TestConfig(tt).logs_path,old_result_dir);
	
% 	if exist(full_old_result_dir)
% 		rmdir(full_old_result_dir,'s');
% 		fprintf('Deleted %s\n',full_old_result_dir);
% 	end
	
%     if exist(full_result_dir)
% 		movefile(full_result_dir,full_old_result_dir);
% 		action_count = action_count + 1;
% 	end


%   	if ~exist(full_result_dir)
%   		[mkdirsuccess,~,~] = mkdir(TestConfig(tt).logs_path,result_dir);
%  	end
% 	
% 	matFileName = fullfile(full_old_result_dir, 'node_log.mat');
% 	copyfile(matFileName, full_result_dir);
% 	
% 	xmlFileName = fullfile(full_old_result_dir, 'node1phy.xml');
% 	copyfile(xmlFileName, full_result_dir);
% 	
% 	xmlFileName = fullfile(full_old_result_dir, 'node2phy.xml');
% 	copyfile(xmlFileName, full_result_dir);
% 	
% 	xmlFileName = fullfile(full_old_result_dir, 'node3phy.xml');
% 	copyfile(xmlFileName, full_result_dir);
% 	
% 	action_count = action_count + 1;


end

fprintf('Number of items executed is %i\n',action_count);



