% Postscript-Output from POLYTOP
% needs a prelude with the functions 
% SetDimension, DefNode, DefEdge, DefEdgeOp,
% DefAttributes and Finish.
% DefEdgeOp is used for /PG-Mode (Operators used).

3 SetDimension

% Node Positions:
/N1 dup [-503 -1754 -3667  ] def DefNode
/N2 dup [-1374 3557 -1493  ] def DefNode
/N3 dup [3818 1062 -1029  ] def DefNode
/N4 dup [1371 -3556 1495  ] def DefNode
/N5 dup [-3818 -1062 1029  ] def DefNode
/N6 dup [504 1751 3668  ] def DefNode

% Node Attributes:
[ /N1 (1) (123) 1 ] DefAttributes
[ /N2 (2) (132) 1 ] DefAttributes
[ /N3 (3) (213) 2 ] DefAttributes
[ /N4 (4) (231) 2 ] DefAttributes
[ /N5 (5) (312) 3 ] DefAttributes
[ /N6 (6) (321) 3 ] DefAttributes

% List of Links:
 /N1 /N5  1 DefEdgeOp
 /N1 /N3  2 DefEdgeOp
 /N1 /N2  3 DefEdgeOp
 /N1 /N4  1 DefEdgeOp
 /N2 /N3  1 DefEdgeOp
 /N2 /N5  2 DefEdgeOp
 /N2 /N6  1 DefEdgeOp
 /N3 /N6  1 DefEdgeOp
 /N3 /N4  3 DefEdgeOp
 /N4 /N6  2 DefEdgeOp
 /N4 /N5  1 DefEdgeOp
 /N5 /N6  3 DefEdgeOp

% Generate the Picture:
Finish
