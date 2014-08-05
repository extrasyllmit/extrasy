function [quivYXZ,quivVUW] = genPolicyQuiver(policy,actions,manifoldSize)
% Generate a policy quiver in a format that can be used by QUIVER and QUIVER3D

% Copyright 2013-2014 Massachusetts Institute of Technology
% $Revision: alpha
% Revised 2014-02-25
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

numDims = numel(manifoldSize);
quivYXZ = ind2subN(manifoldSize,1:prod(manifoldSize)).';
quivVUW = 0.8.*actions(policy,:).*repmat(sum(abs(actions(policy,:)).^2,2).^-0.5,[1 numDims]);
% quivVUW = 0.8.*repmat(V-min(V),[1 numDims])./(max(V)-min(V)).*actions(policy,:).*repmat(sum(abs(actions(policy,:)).^2,2).^-0.5,[1 numDims]);
quivVUW(isnan(quivVUW)) = 0;
