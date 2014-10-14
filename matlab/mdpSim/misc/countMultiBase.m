function [counting] = countMultiBase(bases)
% countMultiBase will generates a dictionary of words where each word has N
% digits and each digit has its own base.
% 
% If BASES is a N x 1 vector of integers then the nth element is the base
% for the nth digit in the word.
% 
% If BASES is a N x 1 cell array then the nth element of BASES is a vector
% of the symbols to use for the nth digit
% 
% The first element in BASES is the most significant digit.
%
% countMultiBase is a generalization of countBase which has similar
% functionality to index2subscript.m and ind2sub and ind2subN
% 

% Copyright 2013-2014 Massachusetts Institute of Technology
% $Revision: alpha
% Revised 2014-02-25
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


if iscell(bases)
    counting = bases{end}(:);
elseif isnumeric(bases)
    counting = (0:(bases(end)-1)).';
else
    error('Invalid argumnet specified for bases')
end

for ii = numel(bases)-1:-1:1
    newKernel = [];
    if iscell(bases)
        baseSymbols = bases{ii};
    else
        baseSymbols = 0:(bases(ii)-1);
    end
    for newSymbolIndx = 1:numel(baseSymbols)
        newSymbol = baseSymbols(newSymbolIndx);
        newSymbolCol = newSymbol*ones(size(counting,1),1);
        newBlock = [newSymbolCol counting];
        newKernel = [newKernel;newBlock];
    end
    counting = newKernel;
end
