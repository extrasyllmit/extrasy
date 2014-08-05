function h = plot_simple_packet_count(timestamp_series, deltatime, time_edges, linecolor, linesize)
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
if nargin < 5
	linesize = 2;
end

if nargin < 4
	linecolor = 'b';
end

if isempty(timestamp_series)
	histc_data = zeros(size(time_edges));
else
	histc_data = histc(timestamp_series,time_edges)/deltatime;
end

[xx,yy] = stairs(time_edges, histc_data);
h = plot(xx(1:end-1),yy(1:end-1),linecolor,'LineWidth',linesize);

box on

ylimval = get(gca,'ylim');
set(gca,'ylim',[0 max(max(histc_data)+1,ylimval(2))])
xlabel('Time (s)');
ylabel('Packets per second');
title(sprintf('Interval = %.4f s',deltatime));


