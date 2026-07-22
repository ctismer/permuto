% Postscript-Output from POLYTOP
% needs a prelude with the functions 
% SetDimension, DefNode, DefEdge, DefEdgeOp,
% DefAttributes and Finish.
% DefEdgeOp is used for /PG-Mode (Operators used).

3 SetDimension

% Node Positions:
/N1 dup [-3476 2160 -56  ] def DefNode
/N2 dup [-1313 336 -3850  ] def DefNode
/N3 dup [-659 -3735 -1544  ] def DefNode
/N4 dup [-2832 -1913 2240  ] def DefNode
/N5 dup [1312 -335 3848  ] def DefNode
/N6 dup [3476 -2156 51  ] def DefNode
/N7 dup [2827 1919 -2244  ] def DefNode
/N8 dup [657 3739 1538  ] def DefNode

% Node Attributes:
[ /N1 (1) (11111112) 1 ] DefAttributes
[ /N2 (2) (11111121) 1 ] DefAttributes
[ /N3 (3) (11111211) 1 ] DefAttributes
[ /N4 (4) (11112111) 1 ] DefAttributes
[ /N5 (5) (11121111) 1 ] DefAttributes
[ /N6 (6) (11211111) 1 ] DefAttributes
[ /N7 (7) (12111111) 1 ] DefAttributes
[ /N8 (8) (21111111) 8 ] DefAttributes

% List of Links:
 /N1 /N4  2 DefEdgeOp
 /N1 /N8  3 DefEdgeOp
 /N1 /N2  2 DefEdgeOp
 /N2 /N7  3 DefEdgeOp
 /N2 /N3  2 DefEdgeOp
 /N3 /N6  4 DefEdgeOp
 /N3 /N4  2 DefEdgeOp
 /N4 /N5  4 DefEdgeOp
 /N5 /N8  1 DefEdgeOp
 /N5 /N6  1 DefEdgeOp
 /N6 /N7  1 DefEdgeOp
 /N7 /N8  1 DefEdgeOp

% Generate the Picture:
Finish
