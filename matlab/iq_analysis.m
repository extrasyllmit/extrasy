function iq_analysis(gnuRadioRootPath,gsdrcRootPath,tagFiles,iqFiles, packetLogName)
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
% example gnuRadioRootPath = '/home/interlaken/a/cr22845/SDR/gnuradio';
% example gsdrcRootPath = '/home/interlaken/a/cr22845/SDR/generalized-sdr-comms/';
% tagFiles is cell array of the names of tag log files
% iqFiles is cell array of IQ log files corresponding to the files listed in tagFiles cell array
% packetLogName is the name of a single xml packet log to process. This should be the log file
%    from whichever node is storing the IQ
off_col = 1;
src_col = 2;
key_col = 3;
val_col = 4;

if length(tagFiles) ~= length(iqFiles)
  error('There must be one stream tag log file for each IQ log file')
end

%data_path = '/home/interlaken/a/cr22845/SDR/slot_selector_analysis';

%% path setup
gnuRadioUtilsPath = '/gnuradio-core/src/utils';
parseUtilsPath = 'gr-digital_ll/matlab/parse_utils/';
xmlUtilsPath = 'gr-digital_ll/matlab/parse_utils/xml_toolbox/';

if isempty(which('read_complex_binary'))
  addpath(path, fullfile(gnuRadioRootPath,gnuRadioUtilsPath));
end  

if isempty(which('xml_readandparse'))
  addpath(fullfile(gsdrcRootPath, parseUtilsPath));
  addpath(fullfile(gsdrcRootPath, xmlUtilsPath));
end  

%% process each tag file, iq file pair
for k=1:length(tagFiles)

  tagFileName = fullfile(tagFiles{k});
  sampFileName = fullfile(iqFiles{k});

  % read IQ
  fprintf('reading %s\n', iqFiles{k})
  samps{k} = read_complex_binary(sampFileName);
  fprintf('%s read complete\n', iqFiles{k})

  % read and parse the tags
  f0 = fopen(tagFileName);
  tags{k} = textscan(f0, 'Offset: %d Source: %s Key: %s Value: %s', ...
                        'Delimiter', '\t', 'CommentStyle', 'Input Stream');
  fclose(f0);
  
  % find the rate tags
  rate_tag_inds{k} = find(strcmp(tags{k}{key_col}, 'rx_rate'));
  
  % find the time tags
  time_tag_inds{k} = find(strcmp(tags{k}{key_col}, 'rx_time'));
  
  % pull out the integer and fractional portion of each time tag
  timePairs{k} = textscan([tags{k}{val_col}{time_tag_inds{k}}], '{%u64 %f}');

  % build up a struct for each tag containing the offset of the tag, the time reference, and the 
  % rate. This assumes that the rate and time tags always appear in pairs at the same offset
  meta{k} = struct('offset',num2cell(tags{k}{off_col}(time_tag_inds{k})), ...
                      't_ref_int', num2cell(timePairs{k}{1}), ...
                      't_ref_frac', num2cell(timePairs{k}{2}), ...
                      'rate',num2cell(str2double(tags{k}{val_col}(rate_tag_inds{k}))));

  % insert dummy tags at the end of each struct array to make the index to time conversion easier
  meta{k}(end+1) = meta{k}(end);
  meta{k}(end).offset = Inf;


end

%% Choose a timestamp to be t0
% get at the first struct in each cell and pull out the integer and fractional seconds of the time
% reference
t0_ints = cellfun( @(x) x(1).t_ref_int, meta);
t0_fracs = cellfun( @(x) x(1).t_ref_frac, meta);

% pick the lowest timestamp to be t0
[t0_min, ind] = min(double(t0_ints) + t0_fracs);


t0_int = t0_ints(ind);
t0_frac = t0_fracs(ind);

% turn off 3d rendering
f = figure;
set(f,'renderer','painters');
ax_handles = [];

% plot each IQ/Tag file pair
for k=1:length(tagFiles)

  % offset the timestamps by t0
  for m=1:length(meta{k})
    meta{k}(m).t_ref_int = meta{k}(m).t_ref_int - t0_int;
  end

  sampTimes = zeros(length(samps{k}),1);

  sampRate = meta{k}(1).rate;

  % compute a timestamp for each sample
  for m=1:length(meta{k})-1
    blockInds = (meta{k}(m).offset+1):(min([length(samps{k}),meta{k}(m+1).offset]));

    sampTimes(blockInds) = double(blockInds-blockInds(1))/sampRate + ...
      double(meta{k}(m).t_ref_int) + meta{k}(m).t_ref_frac;
  end


  subplot(length(iqFiles),1,k)
  [pathstr, name, ext] = fileparts(iqFiles{k});

  plot(sampTimes, 20*log10(abs(samps{k})), '.')
  grid on
  xlabel(sprintf('%s samples in seconds since %lu', name, t0_int),'Interpreter', 'none') 
  ax_handles = [ax_handles,gca];

  y_lims = ylim(ax_handles(k));
  y_lims(2) = 20*log10(max(abs(samps{k})));

  if k==1
    annotate_iq_with_traffic(packetLogName,Inf, double(t0_int), y_lims);
  end



end

linkaxes(ax_handles)
  
