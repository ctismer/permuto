% Postscript-Output from POLYTOP
% needs a prelude with the functions 
% SetDimension, DefNode, DefEdge, DefEdgeOp,
% DefAttributes and Finish.
% DefEdgeOp is used for /PG-Mode (Operators used).

3 SetDimension

% Node Positions:
/N1 dup [3491 0 2142  ] def DefNode
/N2 dup [-1592 2760 2570  ] def DefNode
/N3 dup [1428 3029 -2353  ] def DefNode
/N4 dup [-1423 -3034 2351  ] def DefNode
/N5 dup [1588 -2764 -2566  ] def DefNode
/N6 dup [-3494 0 -2137  ] def DefNode

% Node Attributes:
[ /N1 (1) (1122) 1 ] DefAttributes
[ /N2 (2) (1212) 1 ] DefAttributes
[ /N3 (3) (1221) 1 ] DefAttributes
[ /N4 (4) (2112) 3 ] DefAttributes
[ /N5 (5) (2121) 3 ] DefAttributes
[ /N6 (6) (2211) 3 ] DefAttributes

% List of Links:
 /N1 /N4  2 DefEdgeOp
 /N1 /N5  3 DefEdgeOp
 /N1 /N2  4 DefEdgeOp
 /N1 /N3  5 DefEdgeOp
 /N2 /N4  1 DefEdgeOp
 /N2 /N6  3 DefEdgeOp
 /N2 /N3  6 DefEdgeOp
 /N3 /N5  1 DefEdgeOp
 /N3 /N6  2 DefEdgeOp
 /N4 /N6  5 DefEdgeOp
 /N4 /N5  6 DefEdgeOp
 /N5 /N6  4 DefEdgeOp

% Generate the Picture:
Finish
