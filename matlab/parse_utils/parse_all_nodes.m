function [parse_success, node_log_numel] = parse_all_nodes(logs_path, node_xml, maxParseTime, USE_PARFOR)
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
%addpath('./xml_toolbox');

if nargin < 4
	USE_PARFOR = 0;
end

num_nodes = numel(node_xml);
parse_success = 0;

for n = 1:num_nodes
	fn = fullfile(logs_path, node_xml{n});
	xmlfileexist = exist(fn,'file');

	if ~xmlfileexist
		warning('File %s does not exist.  Parsing aborted',fn);
		return
	end
end

if USE_PARFOR
	parfor n = 1:num_nodes
		fn = fullfile(logs_path, node_xml{n});
		fprintf('Parsing %s\n',fn);
		node_log{n} = xml_readandparse(fn,'packet',Inf,maxParseTime,1);
	end
else
	for n = 1:num_nodes
		fn = fullfile(logs_path, node_xml{n});
		fprintf('Parsing %s\n',fn);
		node_log{n} = xml_readandparse(fn,'packet',Inf,maxParseTime,1);
	end	
end

save(fullfile(logs_path, 'node_log.mat'),'node_log');

node_log_numel = cellfun(@numel, node_log, 'UniformOutput',true);

%consider parsing succussful if every xml has at least 1 valid packet entry
parse_success =  all(node_log_numel>0);

