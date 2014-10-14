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


%% initialization
clear

%add path to xml_toolbox
addpath('../jsonlab');
addpath('./parse_utils');
addpath('../xml_toolbox');


%% set up test config
home_path = '~';

test_names = {'tdma-simple', 'tdma_node1.ini';
              'tdma-sequential-agent', 'sagent_node1.ini';
              'tdma-berf-power', 'berf_power_node1.ini';
              'tdma-berf-beaconhop', 'berf_beaconhop_node1.ini';
              'tdma-berf', 'berf_node1.ini';
              'tdma-agent', 'rlagent_node1.ini'};

% Test8
% for n=1:length(test_names)
% 
%   TestConfig(n).logs_path = fullfile(home_path, test_names{n,1}, 'logs');
%   TestConfig(n).initfile = fullfile(home_path, test_names{n,1}, test_names{n,2});
%   TestConfig(n).num_nodes   = 3;
%   TestConfig(n).mactype = 'tdma';
%   TestConfig(n).topology{1} = [2 3];
%   TestConfig(n).topology{2} = [1];
%   TestConfig(n).topology{3} = [1];
%   TestConfig(n).node_xml{1} = 'packet_log_node1.xml';
%   TestConfig(n).node_xml{2} = 'packet_log_node2.xml';
%   TestConfig(n).node_xml{3} = 'packet_log_node3.xml';
%   TestConfig(n).node_state_xml{1} = 'state_log_node1.xml';
%   TestConfig(n).node_state_xml{2} = 'state_log_node1.xml';
%   TestConfig(n).node_state_xml{3} = 'state_log_node1.xml';
%   TestConfig(n).node_ID = [1 2 3];
%   TestConfig(n).sets_evalnodes = {[1 2],[1 3]};
%   TestConfig(n).result_path = fullfile(TestConfig(n).logs_path, 'results');
% 
%   if ~isdir(TestConfig(n).result_path)
%     mkdir(TestConfig(n).result_path)
%   end
% end

test_names = {'tdma-agent', 'tdma_node1.ini';
              'tdma-sequential-agent', 'tdma_node1.ini';
              };

for n=1:length(test_names)

  TestConfig(n).logs_path = fullfile(home_path, test_names{n,1}, 'logs');
  TestConfig(n).initfile = fullfile(home_path, test_names{n,1}, test_names{n,2});
  TestConfig(n).num_nodes   = 3;
  TestConfig(n).mactype = 'tdma';
  TestConfig(n).topology{1} = [2 3];
  TestConfig(n).topology{2} = [1];
  TestConfig(n).topology{3} = [1];
  TestConfig(n).node_xml{1} = 'packet_log_node1.xml';
  TestConfig(n).node_xml{2} = 'packet_log_node2.xml';
  TestConfig(n).node_xml{3} = 'packet_log_node3.xml';
  TestConfig(n).node_state_xml{1} = 'state_log_node1.xml';
  TestConfig(n).node_state_xml{2} = 'state_log_node1.xml';
  TestConfig(n).node_state_xml{3} = 'state_log_node1.xml';
  TestConfig(n).node_ID = [1 2 3];
  TestConfig(n).sets_evalnodes = {[1 2],[1 3]};
  TestConfig(n).result_path = fullfile(TestConfig(n).logs_path, 'results');

  if ~isdir(TestConfig(n).result_path)
    mkdir(TestConfig(n).result_path)
  end
end


%% specify selected TestConfigs and how much time to process
TrialsToRun = 1:numel(TestConfig);
RUN_PARSE_SECTION = 1;
maxParseTime = 10*60; %seconds, parse only first maxParseTime seconds
USE_PARFOR = 1; %enable parallel matlab pool in parsing only
poolsize = 4;


RUN_EVAL_SECTION = 1;
evalTimeRange = [0 Inf]; %[100 150]; %[0 10*60]; %seconds
SAVERESULTS = 1;						

%% call script to parse and evaluate performance
parse_and_eval_performance;

