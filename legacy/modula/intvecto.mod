(***********************************************************

   Vector Operations


  20.02.92: rewrote this with no vector results. is slightly
            quicker when target is supplied by caller.
***********************************************************)

IMPLEMENTATION MODULE IntVector ;

IMPORT Lib, MacFns, Lib1 ;

CONST DEBUG = NOT TRUE ;

VAR
  Dimensions : INTEGER ;   (* kept local, access by Set/GetDimensions *)

PROCEDURE SetDimensions (dim : INTEGER) ;
BEGIN
  IF dim <= 0 THEN dim := 3 END ;
  Dimensions := dim ;
END SetDimensions ;

PROCEDURE GetDimensions () : INTEGER ;
BEGIN
  RETURN Dimensions ;
END GetDimensions ;


PROCEDURE ZeroVector (VAR vec : ARRAY OF VecType) ;
  VAR i : CARDINAL ;
BEGIN
  FOR i := 0 TO Dimensions-1 DO
    vec[i] := 0 ;
  END ;
END ZeroVector ;

PROCEDURE RandomVector (VAR vec : ARRAY OF VecType; range : INTEGER) ;
  VAR i : CARDINAL ; n : INTEGER ;
BEGIN
  range := ABS(range) ;
  FOR i := 0 TO Dimensions-1 DO
    n := INTEGER(Lib.RANDOM(2*range)) - INTEGER(range) ;
    vec[i] := n ;
  END ;
END RandomVector ;

PROCEDURE ScaleVector (VAR vec : ARRAY OF VecType ; mul, div : INTEGER) ;
  VAR i : CARDINAL ;
BEGIN
  FOR i := 0 TO Dimensions-1 DO
    vec[i] := Scale(vec[i], mul, div) ;
  END ;
END ScaleVector ;

PROCEDURE DotProdukt (VAR vec : ARRAY OF VecType; w : ARRAY OF VecType) ;
  VAR i : CARDINAL ;
BEGIN
  FOR i := 0 TO Dimensions-1 DO
    vec[i] := Scale(vec[i], w[i], Norm) ;
  END ;
END DotProdukt ;

PROCEDURE AddVector (VAR vec : ARRAY OF VecType ; w : ARRAY OF VecType) ;
  VAR i : CARDINAL ;
BEGIN
  FOR i := 0 TO Dimensions-1 DO
    (*%T DEBUG*) IF ABS(LONGINT(vec[i])+LONGINT(w[i])) > MAX(INTEGER) THEN
                   i := i ;  (* dummy, place breakpoint here *)
                 END ;
    (*%E*)
    vec[i] := vec[i] + w[i] ;
  END ;
END AddVector ;

PROCEDURE SubVector (VAR vec : ARRAY OF VecType ; w : ARRAY OF VecType) ;
  VAR i : CARDINAL ;
BEGIN
  FOR i := 0 TO Dimensions-1 DO
    vec[i] := vec[i] - w[i] ;
  END ;
END SubVector ;

PROCEDURE VectorLength (VAR v : ARRAY OF VecType) : INTEGER ;
  VAR i : CARDINAL ; len : LONGINT ;
BEGIN
  len := 0 ;
  FOR i := 0 TO Dimensions-1 DO
    len := len + LONGINT(Sqr(v[i])) ;
  END ;
  RETURN INTEGER(Sqrt(len)) ;
  (* with maximum coordinates of 10000 and maximal 10 dimensions
     this will be no larger than 32000
  *)
END VectorLength ;

PROCEDURE NormVector (VAR v : ARRAY OF VecType) ;
  VAR len : INTEGER ;
BEGIN
  len := VectorLength(v) ;
  IF len = 0 THEN v[1] := 1 ; len := 1 END ;
  ScaleVector(v, Norm, len) ;
END NormVector ;

PROCEDURE Sqr(x: INTEGER) : LONGINT ;
BEGIN
  RETURN MacFns.I_MUL_I(x, x) ;
END Sqr ;

PROCEDURE Sqrt(x: LONGINT) : INTEGER ;
BEGIN
  RETURN INTEGER(Lib1.Root(LONGCARD(x))) ;
END Sqrt ;

PROCEDURE Scale(x: INTEGER; mul, div: INTEGER) : INTEGER ;
  (* fast routine with macros, but no check for overflow! *)
BEGIN
  RETURN MacFns.LI_DIV_I ( MacFns.I_MUL_I ( x, mul), div) ;
END Scale ;

BEGIN
  Dimensions := 3 ;  (* if forgotten *)
END IntVector.