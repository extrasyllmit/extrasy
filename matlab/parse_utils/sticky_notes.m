function sticky_notes(a)
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
 a_strg = evalc('a');
 
 my_textbox = uicontrol('style','text');
 
 tmp =  find((a_strg == 10) | (a_strg == 13));

 nrow = numel(tmp);

 ncol = max(diff(tmp));
 
 set(my_textbox,'String',a_strg(tmp(3):end));
 
 set(my_textbox,'FontName','FreeMono')
 fontsize = 10;
 set(my_textbox,'FontSize',fontsize)
 set(my_textbox,'Units','characters');

 set(my_textbox,'BackgroundColor',[1 1 168/255])
 
 set(my_textbox,'Position',[0 0 ncol*1.4 (nrow)]);

 set(my_textbox,'HorizontalAlignment','left');
 
 