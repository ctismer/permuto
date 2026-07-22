% Postscript-Output from POLYTOP
% needs a prelude with the functions 
% SetDimension, DefNode, DefEdge, DefEdgeOp,
% DefAttributes and Finish.
% DefEdgeOp is used for /PG-Mode (Operators used).

3 SetDimension

% Node Positions:
/N1 dup [-70 -1110 3929  ] def DefNode
/N2 dup [-3002 2701 682  ] def DefNode
/N3 dup [-2792 -2865 -874  ] def DefNode
/N4 dup [2999 -2705 -682  ] def DefNode
/N5 dup [73 1111 -3929  ] def DefNode
/N6 dup [2787 2870 875  ] def DefNode

% Node Attributes:
[ /N1 (1) (111112) 1 ] DefAttributes
[ /N2 (2) (111121) 1 ] DefAttributes
[ /N3 (3) (111211) 1 ] DefAttributes
[ /N4 (4) (112111) 1 ] DefAttributes
[ /N5 (5) (121111) 1 ] DefAttributes
[ /N6 (6) (211111) 6 ] DefAttributes

% List of Links:
 /N1 /N6  1 DefEdgeOp
 /N1 /N3  2 DefEdgeOp
 /N1 /N2  1 DefEdgeOp
 /N1 /N4  2 DefEdgeOp
 /N2 /N6  2 DefEdgeOp
 /N2 /N3  1 DefEdgeOp
 /N2 /N5  2 DefEdgeOp
 /N3 /N5  2 DefEdgeOp
 /N3 /N4  1 DefEdgeOp
 /N4 /N5  1 DefEdgeOp
 /N4 /N6  2 DefEdgeOp
 /N5 /N6  1 DefEdgeOp

% Generate the Picture:
Finish
