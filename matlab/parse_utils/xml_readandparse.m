function structarray = xml_readandparse(filename,toptagname,maxSize,maxTime,verbose)
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
%read until either maxSize (#log entries) or maxTime is reached
%maxTime is applicable only when timestamp field exists

if nargin < 5
	verbose = 0;
end

if nargin < 4
	maxTime = Inf;
end

if nargin < 3
	maxSize = Inf;
end

fid = fopen(filename,'r');

if fid == -1
	error('cannot open file');
end

aline = [];

toptag = ['<' toptagname '>']; toptaglen = length(toptag);
matchtag = ['</' toptagname '>']; matchtaglen = length(matchtag);

linecount = 0;
structarray = [];

structCount = 0;
secondsread = 0;

while ~isequal(aline,-1)
	aline = fgets(fid);
	linecount = linecount + 1;
	
	if (length(aline) >= toptaglen) && isequal(aline(1:toptaglen),toptag)
		block = [];
		while ~isequal(aline,-1)
			block = [block aline];
			aline = fgets(fid);
			linecount = linecount + 1;
			
			if (length(aline) >= matchtaglen) && isequal(aline(1:matchtaglen),matchtag)
				block = [block aline];
				%one node_state is read
				
				%filename
				%linecount
				%block
				
				onestruct = xml_parseany(block);
				onestruct_repack = xml_repackage(onestruct);
				
				if isempty(structarray)
					currentfields = fieldnames(onestruct_repack);
				else
					newfields = fieldnames(onestruct_repack);
					missingnewfields = setdiff(currentfields,newfields);
					for k = 1:numel(missingnewfields)
						onestruct_repack.(missingnewfields{k}) = [];
					end
					missingoldfields = setdiff(newfields,currentfields);
					for k = 1:numel(missingoldfields)
						structarray(1).(missingoldfields{k}) = [];
					end
					currentfields = {currentfields{:} missingoldfields{:}}.';
				end
				
				%disp(structarray)
				%disp(onestruct_repack)
				%keyboard
				
				structarray = [structarray onestruct_repack];
				structCount = structCount + 1;
				
				if isfield(onestruct_repack,'timestamp')
					if structCount == 1
						inittime = str2double(onestruct_repack.timestamp);
					else
						currenttime = str2double(onestruct_repack.timestamp);
						difftime = currenttime-inittime;
						if floor(difftime) > secondsread
							secondsread = floor(difftime);
							if verbose==1 && mod(secondsread,15)==0
								fprintf('%s : parsed %i seconds (%.2f minutes) or %i entries.\n',filename,secondsread,secondsread/60,structCount);
							end
						end
						if difftime >= maxTime
							aline = -1;
						end
					end
				end
				
				if structCount >= maxSize
					aline = -1; %force termination, got enough packets
				end
				
				break
			end
		end
	end
end

if verbose==1
	fprintf('%s : parsed %i seconds (%.2f minutes) or %i entries.\n',filename,secondsread,secondsread/60,structCount);
	fprintf('%s : parsing finished.\n\n',filename);
end


fclose(fid);


