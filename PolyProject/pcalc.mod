(*************************************************************

   Polytope Calculations

*************************************************************)

IMPLEMENTATION MODULE PCalc ;

FROM NodeMgr IMPORT Vector, nnodes, Nodes, Dimensions ;

FROM IntVector IMPORT VecType, ZeroVector, RandomVector,
                      ScaleVector, DotProdukt, AddVector,
                      SubVector, VectorLength, NormVector,
                      Sqr, Sqrt, Scale, Norm ;

PROCEDURE Normalize() ;
  VAR
    vec, tmp : Vector ;
    i, dim : INTEGER ;
    lmean : LONGINT ;
    max : INTEGER ;
BEGIN
  (* calculate central point *)
  (* we do it separately for each coordinate because, when the vectors
     are small as in the beginning, dividing down for building the mean
     would truncate everything. Therefore, the mean is calculated
     in LONGINT and the divided.
  *)
  ZeroVector (vec) ;
  FOR dim := 1 TO Dimensions DO
    lmean := 0 ;
    FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
      lmean := lmean + LONGINT(pos[dim]) ;
    END END ;
    IF nnodes > 0 THEN
      vec[dim] := INTEGER(lmean DIV LONGINT(nnodes)) ;
    END ;
  END ;

  (* move central point to zero *)
  IF VectorLength(vec) > 5 THEN  (* don't waste time *)
    FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
      SubVector(pos, vec) ;
    END END ;
  END ;

  (* scale picture. maximum vectorlength becomes Norm *)
  max := 1 ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IF VectorLength(pos) > max THEN max := VectorLength(pos) END ;
  END END ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    ScaleVector (pos, Norm, max) ;
  END END ;
END Normalize ;

PROCEDURE Backup() ;
  VAR i : INTEGER ;
BEGIN
    FOR i := 1 TO nnodes DO Nodes[i]^.old := Nodes[i]^.pos END ;
END Backup ;

PROCEDURE Spin() ;
VAR
  rotc, rots, i : INTEGER ;
  vec : Vector ;
BEGIN
  (* for small angles, sin(x) is about x, so: *)
  rots := Norm DIV 120 ;  (* small angle, 3 degrees *)
  rotc := Sqrt(Sqr(Norm)-Sqr(rots)) ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    vec := pos ;
    pos[1] := Scale(pos[1], rotc, Norm) + Scale(vec[3], rots, Norm) ;
    pos[3] := Scale(pos[3], rotc, Norm) - Scale(vec[1], rots, Norm) ;
  END END ;
END Spin ;

PROCEDURE Squeeze() ;
VAR
  len, mean : INTEGER ;
  vec : Vector ;
  i : INTEGER ;
BEGIN
  mean := 0 ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    mean := mean + VectorLength(pos) DIV nnodes ;
  END END ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    len := VectorLength(pos) ;
    IF len = 0 THEN len := 1 END ;
    vec := pos ;
    ScaleVector(vec, mean, len ) ;
    ScaleVector(vec, 1, 5) ;
    AddVector (pos, vec) ;

  END END ;
END Squeeze ;

PROCEDURE Punish() ;
  VAR
    i : INTEGER ;
    vec : Vector ;
BEGIN
  (* punish for use of high dimensions *)
  (* would be better to use "scherung" that minimizes a dim.
     at this time, we squeeze only a bit *)
  FOR i := 1 TO Dimensions DO
    vec[i] := INTEGER(
                LONGINT(Norm)*LONGINT(Norm)
                DIV
               (LONGINT(Norm)+LONGINT(i)*LONGINT(Norm) DIV 400) ) ;
  END ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    DotProdukt (pos, vec) ;
  END END ;
END Punish ;

PROCEDURE Contract(Algorithm: AlgType) ;
VAR
  i, j : INTEGER ;
  len, min, max : CARDINAL ;
  vec, tmp, cmp : Vector ;
  Lcount, Lsum : LONGCARD ;
  mean : CARDINAL ;
BEGIN
  IF Algorithm = a_New THEN
    (* find mean length *)
    Lcount := 0 ;
    Lsum := 0 ;
    FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
      FOR j := 1 TO nlink DO
        tmp := Nodes[links[j]]^.old ;
        SubVector(tmp, pos) ;
        INC(Lsum, LONGCARD(VectorLength(tmp))) ;
        INC(Lcount) ;
      END ;
    END END ;
    IF Lcount # 0 THEN
      mean := INTEGER(Lsum DIV Lcount)
    END ;
  END ;

  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO IF nlink > 0 THEN
    ZeroVector(vec) ;
    CASE Algorithm OF

    | a_Rubber :
      FOR j := 1 TO nlink DO
        tmp := Nodes[links[j]]^.old ;
        SubVector(tmp, pos) ;
        AddVector(vec, tmp) ;
      END ;
      ScaleVector(vec, 1, 3*nlink) ;
      AddVector (pos, vec) ;

    | a_Rubber2 :
      FOR j := 1 TO nlink DO
        tmp := Nodes[links[j]]^.old ;
        SubVector(tmp, pos) ;
        len := VectorLength(tmp) ;
        ScaleVector(tmp, len, nlink*Norm) ;
        AddVector(vec, tmp) ;
      END ;
      ScaleVector(vec, 1, 3*nlink) ;
      AddVector (pos, vec) ;

    | a_Ribbon :
      max := 1 ;
      min := MAX(INTEGER) ;
      FOR j := 1 TO nlink DO
        cmp := Nodes[links[j]]^.old ;
        SubVector(cmp, pos) ;
        len := VectorLength(cmp) ;
        IF len > max THEN
          max := len ;
          vec := cmp ;
        END ;
        IF len < min THEN
          min := len ;
        END ;
      END ;
      (* now walk along longest difference vector,
         but only in the range of longest-shortest *)
      ScaleVector(vec, (max-min) DIV 100, max) ;
      AddVector (pos, vec) ;

    | a_Mean :
      (* not bad, but nearly like rubber: *)
      FOR j := 1 TO nlink DO
        AddVector(pos, Nodes[links[j]]^.old) ;
      END ;

    | a_New :
      (* we try again to get all lengths equal.
         Find the mean of all edges in the graph.
         Then contract only those which are longer than
         the mean.
       *)

(*
      FOR j := 1 TO nlink DO
        tmp := Nodes[links[j]]^.old ;
        SubVector(tmp, pos) ;
        IF VectorLength(tmp) > mean THEN
          AddVector(vec, tmp) ;
        END ;
      END ;
      ScaleVector(vec, 1, 36) ;
      AddVector (pos, vec) ;
*)
      FOR j := 1 TO nlink DO
        AddVector(vec, Nodes[links[j]]^.old) ;
      END ;
      IF nlink > 0 THEN
        ScaleVector(vec, 1, 20*nlink) ;
        AddVector(pos, vec) ;
      END ;
      FOR j := 1 TO nlink DO
        tmp := Nodes[links[j]]^.old ;
        SubVector(tmp, pos) ;
        len := VectorLength(tmp) ;
        IF len > mean THEN
          ScaleVector(tmp, (len-mean) DIV nlink, 2*len) ;
          AddVector(pos, tmp) ;
        END ;
      END ;
      (* nochmal! *)
      FOR j := 1 TO nlink DO
        tmp := Nodes[links[j]]^.old ;
        SubVector(tmp, pos) ;
        len := VectorLength(tmp) ;
        IF len > mean THEN
          ScaleVector(tmp, (len-mean) DIV nlink, 2*len) ;
          AddVector(pos, tmp) ;
        END ;
      END ;

    END ;

  ELSE        (* nlink is 0 *)
    ZeroVector(pos) ;
  END END END ;
END Contract ;

PROCEDURE CanShrink() : BOOLEAN ;
VAR
  i, j : INTEGER ;
  vec : Vector ;
BEGIN
  ZeroVector(vec) ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    FOR j := 1 TO Dimensions DO
      IF ABS(pos[j]) > vec[j] THEN
        vec[j] := ABS(pos[j]) ;
      END ;
    END ;
  END END ;
  RETURN vec[Dimensions] <= vec[1] DIV 100 ;
END CanShrink ;

END PCalc.
