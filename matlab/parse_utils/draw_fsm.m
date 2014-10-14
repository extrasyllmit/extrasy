function [P,Q] = draw_fsm(table_count, table_alldelays, mactype, labelmode, nn, fignum)
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
transitiontime = cellfun(@sum,table_alldelays);
totaltime = sum(sum(transitiontime));
totalcount = sum(sum(table_count));

%swap row and columns to match drawing order
P = transitiontime([1,6,3,8,5,2,7,4],[1,6,3,8,5,2,7,4]);
Q = table_count([1,6,3,8,5,2,7,4],[1,6,3,8,5,2,7,4]);

if isequal(labelmode,'bytime')
	Values = P;
	Percent = P/totaltime*100;
else %isequal(labelmode,'bycount')
	Values = Q;
	Percent = Q/totalcount*100;
end

unused_states = find((sum(P)==0) & (sum(P.')==0));

legalMacTable = legalMAC(mactype);

figure(fignum); clf;

hold on;

if numel(unused_states) > 0
	plot(0,0,'bo');
	plot(0,0,'go');
	plot(0,0,'o','Color',[0.8 0.8 0.8]);
	legend(sprintf('Node%i transmits to others',nn),sprintf('Others transmit to Node%i',nn),'N/A or Unreachable');
else
	plot(0,0,'bo');
	plot(0,0,'go');
	legend(sprintf('Node%i transmits to others',nn),sprintf('Others transmit to Node%i',nn));
end

loc = zeros(8,2);
for k = 1:4
	loc(k,:)   = [20+(k-1)*40 50];
	loc(k+4,:) = [20+(k-1)*40 10];	
end

circleD = 8;

%draw all the transition curves first
all_hd = zeros(64,3);
all_midcurve = zeros(64,2);
for m = 1:8
	for n = 1:8
		if Values(m,n) > 0
			[hd, midcurve] = draw_curve(loc,circleD,m,n);
			all_hd((m-1)*8+n,:) = hd;
			all_midcurve((m-1)*8+n,:) = midcurve;

			if (m~=n) && (legalMacTable(m,n)==0)
				set(hd,'Color','m');
			end
			
			if Percent(m,n) < 1
				set(hd,'LineWidth',3);
				set(hd,'LineStyle','-.');
			elseif Percent(m,n) < 10
				set(hd,'LineWidth',3);
				set(hd,'LineStyle','-');
			else
				set(hd,'LineWidth',5);
				set(hd,'LineStyle','-');
			end
		end
	end
end

%draw filled circles for each state on top of curves
for k = 1:4
	h(k)   = draw_circle(loc(k,:),circleD);
	h(k+4) = draw_circle(loc(k+4,:),circleD);	
end

axis equal


for k = [1,3,6,8]
	set(h(k),'EdgeColor','b')
	set(h(k),'LineWidth',3)
	set(h(k),'FaceColor',[1 1 1]);
end

for k = [2,4,5,7]
	set(h(k),'EdgeColor','g')
	set(h(k),'LineWidth',3)
	set(h(k),'FaceColor',[1 1 1]);
end

%unused_states = find((sum(P)==0) & (sum(P.')==0));
for k = unused_states
	set(h(k),'EdgeColor',[0.9 0.9 0.9])
	set(h(k),'LineWidth',3)
	set(h(k),'FaceColor',[1 1 1]);
end

labelstrg = {'RTS','CTS','DATA','ACK'};
for k = 1:4
	ht(k) = text(loc(k,1), loc(k,2),labelstrg{k});
	set(ht(k),'HorizontalAlignment','center');
	set(ht(k),'VerticalAlignment','middle');
	ht(k+4) = text(loc(k+4,1), loc(k+4,2),labelstrg{k});
	set(ht(k+4),'HorizontalAlignment','center');
	set(ht(k+4),'VerticalAlignment','middle');
end

for k = unused_states
	set(ht(k),'Color',[0.9 0.9 0.9]);
end

%draw P values
for m = 1:8
	for n = 1:8
		if Values(m,n) > 0
			midcurve = all_midcurve((m-1)*8+n,:);

			if isequal(labelmode,'bytime')
				ht = text(midcurve(1),midcurve(2),sprintf('%.1f%% (%.1fms*%i)',Percent(m,n),P(m,n)/Q(m,n)*1e3,Q(m,n)));
			else
				ht = text(midcurve(1),midcurve(2),sprintf('%.1f%% (%i)',Percent(m,n),Values(m,n)));
			end
			set(ht,'FontSize',8);
			set(ht,'HorizontalAlignment','center');
			set(ht,'VerticalAlignment','middle');
			set(ht,'Color','r')
			set(ht,'BackgroundColor',[1 1 0.7])
		end
	end
end

hold on;
axis equal
axis([10 155 -10 70])
axis off
set(gcf,'Color',[1 1 1])
set(gcf,'PaperOrientation','landscape')
set(gcf,'PaperPosition',[-1.5 0 13.5 8.5])
if isequal(labelmode,'bytime')
	title(sprintf('Protocol diagram for node %i weighted by time (%i transitions in %i seconds)',nn,sum(sum(table_count)),round(sum(sum(transitiontime)))))
else
	title(sprintf('Protocol diagram for node %i weighted by transition count (%i transitions in %i seconds)',nn,sum(sum(table_count)),round(sum(sum(transitiontime)))))
end






function h = draw_circle(loc,sz)
h = rectangle('Position',[loc(1)-sz/2 loc(2)-sz/2 sz sz],'Curvature',[1 1]);

function [h, midcurve] = draw_curve(loc,circleD,m,n)

if m==n
	sz = 7;
	h(1) = rectangle('Position',[loc(m,1)-sz/2 loc(m,2)-sz/2-5*(m>4)+5*(m<=4) sz sz],'Curvature',[1 1]);
	set(h(1),'EdgeColor','k');
	if (m<=4)
		h(2) = plot([loc(m,1)+2.8 loc(m,1)+4.2],[loc(m,2)+2.9 loc(m,2)+3.0],'k');
		h(3) = plot([loc(m,1)+2.8 loc(m,1)+2.7],[loc(m,2)+2.9 loc(m,2)+4.3],'k');
	else
		h(2) = plot([loc(m,1)-2.8 loc(m,1)-4.2],[loc(m,2)-2.9 loc(m,2)-3.0],'k');
		h(3) = plot([loc(m,1)-2.8 loc(m,1)-2.7],[loc(m,2)-2.9 loc(m,2)-4.3],'k');
	end
	%midcurve = [loc(m,1)-5 loc(m,2)-(sz+5)*(m>4)+(sz+5)*(m<=4)];
	midcurve = [loc(m,1) loc(m,2)-(sz+2)*(m>4)+(sz+2)*(m<=4)];
	return
end

mid = (loc(m,:) + loc(n,:))/2;

diff = loc(n,:)-loc(m,:);

center = mid+[diff(2) -diff(1)]*1.2; %1.2 to reduce curvature

a1 = loc(m,1)-center(1);
a2 = loc(n,1)-center(1);

s1 = loc(m,2)-center(2);
s2 = loc(n,2)-center(2);

c1 = sqrt(sum((loc(m,:)-center).^2));
c2 = sqrt(sum((loc(n,:)-center).^2));

ang1 = sign(s1)*acos(a1/c1);
ang2 = sign(s2)*acos(a2/c1);

if abs(ang1-ang2)>pi
	ang1 = mod(ang1+2*pi,2*pi);
	ang2 = mod(ang2+2*pi,2*pi);
end
r = norm(loc(m,:)-center);

xx = r*cos((ang1:-pi/1000:ang2))+center(1);
yy = r*sin((ang1:-pi/1000:ang2))+center(2);

idx = max(floor(length(xx)*0.47),1);

yshift = 0; %((loc(n,1)-loc(m,1))>0)*5 + ((loc(n,1)-loc(m,1))<0)*(-5);
xshift = 0; %((loc(n,2)-loc(m,2))>0)*(-20) + 2;

midcurve = [xx(idx)+xshift yy(idx)+yshift];

idx2 = find( sqrt(sum(([xx; yy]-repmat([xx(end); yy(end)],1,numel(xx))).^2))   < (circleD/2)*1.03,1);

h(1) = plot(xx(1:idx2),yy(1:idx2),'k');

idx3 = find( sqrt(sum(([xx; yy]-repmat([xx(end); yy(end)],1,numel(xx))).^2))   < (circleD/2)*1.5,1);

tip = [xx(idx2) yy(idx2)];

tip2 = [xx(idx3) yy(idx3)]; %adjust arrow size here
theta = pi/4;
rotmat = [cos(theta) -sin(theta); sin(theta) cos(theta)];
edge1 = (rotmat*(tip2-tip)')'+tip;
theta = -pi/4;
rotmat = [cos(theta) -sin(theta); sin(theta) cos(theta)];
edge2 = (rotmat*(tip2-tip)')'+tip;
h(2) = plot([edge1(1) tip(1)],[edge1(2) tip(2)],'k');
h(3) = plot([edge2(1) tip(1)],[edge2(2) tip(2)],'k');






