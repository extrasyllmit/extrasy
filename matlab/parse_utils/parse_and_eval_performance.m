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
%% checking to make sure all xml exist
for tt = TrialsToRun
	if numel(TestConfig(tt).node_xml) ~= TestConfig(tt).num_nodes
		error('node_xml length does not match num_nodes for TestConfig #%i',tt);
	end
	
	if numel(TestConfig(tt).node_ID) ~= TestConfig(tt).num_nodes
		error('node_ID length does not match num_nodes for TestConfig #%i',tt);
	end

	if max([TestConfig(tt).sets_evalnodes{:}]) > TestConfig(tt).num_nodes
		error('sets_evalnodes contain ID number greater num_nodes in TestConfig#%i',tt);
	end
	
	for ff = 1:TestConfig(tt).num_nodes
		fprintf('Checking if files exist for TestConfig %i - File %i\n',tt,ff);
		fn = fullfile(TestConfig(tt).logs_path, TestConfig(tt).node_xml{ff});
		xmlfileexist = exist(fn,'file');
		
		if ~xmlfileexist
			error('File %s does not exist',fn);
		else	
			fid = fopen(fn,'r');
			
			if fid == -1
				error('File %s exists but cannot be opened.',fn);
			else
				fclose(fid);
			end
		end
	end
end



if USE_PARFOR && RUN_PARSE_SECTION
	if matlabpool('size') < poolsize
		if matlabpool('size') > 0
			matlabpool close force
		end
		matlabpool('open','local', poolsize)
	end
end

%% PARSING from xml to dot mat file
if RUN_PARSE_SECTION
	skippedParsedTrials = [];
	
	for tt = TrialsToRun
		fprintf('Started Parsing TestConfig %i\n',tt);
		logs_path = TestConfig(tt).logs_path;
		node_xml  = TestConfig(tt).node_xml;
		[parse_success, node_log_numel] = parse_all_nodes(logs_path, node_xml, maxParseTime, USE_PARFOR);
		if parse_success == 0
			for n = 1:numel(node_log_numel)
				if node_log_numel(n) == 0
					warning('Failed to parse %s -- check file size and proper xml format.',node_xml{n});
				end
			end
			warning('Failed to completely parse TestConfig %i\n',tt);
			skippedParsedTrials = [skippedParsedTrials tt];
			break
		end
		fprintf('Finished Parsing TestConfig %i\n\n',tt);
	end

	if ~isempty(skippedParsedTrials)
		fprintf('The following test(s) may have failed in parsing (unless it is a valid empty packet log) : ');
		fprintf('%i ', skippedParsedTrials);
		fprintf('\n\n');
	end
end

%% EVALUATING link performance for trials already parsed
if RUN_EVAL_SECTION
	fignum1 = 20;
	
	if ~exist('ALLOW_EMPTY_LOG','var')
		ALLOW_EMPTY_LOG = 0;
	end
	
	%check to make sure node_log.mat exists for all trials to run
	for tt = TrialsToRun
		logs_path = TestConfig(tt).logs_path;
		matFileName = fullfile(logs_path, 'node_log.mat');
		if ~exist(matFileName,'file')
			error('Failed to locate node_log.mat for TestConfig %i.  Run the parsing section first.\n',tt);
		end
	end
	
	skippedTrials = [];
	
	for tt = TrialsToRun
		num_nodes = TestConfig(tt).num_nodes;
		mactype = TestConfig(tt).mactype;
		node_ID = TestConfig(tt).node_ID;
		
		%make old mactype format compatible with new mactype
		if ~iscell(mactype)
			mactype = repmat({mactype},1,num_nodes);
		end
		
		clear PKTCODE %don't want to overlap different types
		if isequal(mactype{1}(1:4),'csma')
			PKTCODE.RTS  = 1;
			PKTCODE.CTS  = 2;
			PKTCODE.DATA = 3;
			PKTCODE.ACK  = 4;
		elseif isequal(mactype{1}(1:4),'tdma')
			PKTCODE.OTHER     = 0;
			PKTCODE.BEACON    = 1;
			PKTCODE.DATA      = 2;
			PKTCODE.KEEPALIVE = 3;
			PKTCODE.FEEDBACK  = 4;
		else
			error('unknown mactype specification for TestConfig %i',tt);
		end
		
		clear node_log
		logs_path = TestConfig(tt).logs_path;
		matFileName = fullfile(logs_path, 'node_log.mat');
		load(matFileName);
		
		if ~exist('node_log','var')
			warning('node_log does not exist for TestConfig %i.  This TestConfig is skipped.\n',tt);
			skippedTrials = [skippedTrials tt];
			break
		end
		
		%check time stamps for consistency
		error_codes = check_timestamps(node_log);
		if any(error_codes == 1)
			%allow error code 1 now since drop packets have [] time stamp
			%strg1 = sprintf('timestamp problems with Node %i\n',find(error_codes==1));
			%strg2 = sprintf('proper timestamp(s) missing from packet logs for TestConfig %i.  This TestConfig is skipped.\n',tt);
			%warning([strg1 strg2]);
			%skippedTrials = [skippedTrials tt];
			%break
		elseif any(error_codes >= 2)
			strg1 = sprintf('timestamp problems with Node %i\n',find(error_codes>=2));
			strg2 = sprintf('some timestamp(s) seem to be out of range for TestConfig %i.  This TestConfig is skipped.\n',tt);
			warning([strg1 strg2]);
			skippedTrials = [skippedTrials tt];
			break
		end
		
		%prune log data to target certain interval for evaluation
		original_time = get_time_info(node_log);
		
		if ~isequal(evalTimeRange, [0 Inf])
			node_log = prune_log_data(node_log, evalTimeRange);
		end
		
		if ~ALLOW_EMPTY_LOG
			node_log_numel = cellfun(@numel, node_log, 'UniformOutput',true);
			if any(node_log_numel(unique([TestConfig(tt).sets_evalnodes{:}]))==0)
				warning('at least one of the nodes has no packet logs for this evaluation time range.  TestConfig %i is skipped.\n',tt);
				skippedTrials = [skippedTrials tt];
				break
			end
		end
		pruned_time = get_time_info(node_log);
		evalTimeRangeUpdated = [pruned_time.inittime pruned_time.endtime] - original_time.inittime;
		
		save_params.SAVERESULTS = SAVERESULTS;
		save_params.evalTimeRangeUpdated = evalTimeRangeUpdated;
		
		fprintf('Started Evaluating TestConfig %i\n',tt);
		perform = evaluate_tdma_nodes(node_log, TestConfig(tt), fignum1, save_params, PKTCODE);
		fprintf('Finished Evaluating TestConfig %i\n',tt);
	end

	if ~isempty(skippedTrials)
		fprintf('The following test(s) have failed in processing : ');
		fprintf('%i ', skippedTrials);
		fprintf('\n\n');
	end
end
