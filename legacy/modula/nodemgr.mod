(**********************************************************

   Node Management

***********************************************************)

IMPLEMENTATION MODULE NodeMgr ;

IMPORT IO, FIO, Lib, MacFns, Lib1 ;

FROM ScreenHandler IMPORT CloseGraph ;

FROM Utilities IMPORT nl ;

IMPORT PM ;  (* load/save - Zugriff auf Strukturen *)

PROCEDURE LimitCheck (txt : ARRAY OF CHAR ; arg, min, max : CARDINAL) ;
BEGIN
  IF (arg < min) OR (arg > max) THEN
    CloseGraph() ;
    IO.WrStr("Error: ") ;
    IO.WrStr(txt) ;
    IO.WrStr(" is not in the range ") ;
    IO.WrCard(min,0) ;
    IO.WrStr(" to ") ;
    IO.WrCard(max,0) ;
    IO.WrLn() ;
    HALT ;
  END ;
END LimitCheck ;


VAR NodeIndex : CARDINAL ;  (* nur fÅr Sortierung *)

PROCEDURE CompareLinkList (a, b : CARDINAL) : BOOLEAN ;
BEGIN
  WITH Nodes[NodeIndex]^ DO RETURN links[a] < links[b] END ;
END CompareLinkList ;

PROCEDURE SwapLinkList (a, b : CARDINAL) ;
  VAR hold : CARDINAL ;
BEGIN
  WITH Nodes[NodeIndex]^ DO
    hold := links[a] ;
    links[a] := links[b] ;
    links[b] := hold
  END ;
END SwapLinkList ;

PROCEDURE MoveNode(from, to : CARDINAL) ;
  VAR i, j : INTEGER ;
BEGIN
  Nodes[to]^ := Nodes[from]^ ;
  Lib.Fill(ADR(Nodes[from]^), SIZE(Nodes[from]^), 0) ;
  WITH Nodes[to]^ DO
    num := to ;
    FOR i := 1 TO nlink DO
      WITH Nodes[links[i]]^ DO
        FOR j := 1 TO nlink DO  (* relink nodes which point here *)
          IF links[j] = from THEN links[j] := to END ;
        END ;
      END ;
    END ;
  END ;
END MoveNode ;

PROCEDURE ResetNodes() ;
  VAR i : INTEGER ;
BEGIN
  nnodes := 0 ;
  lastnode := 0 ;
  FOR i := 1 TO MaxNodes DO
    Lib.Fill(ADR(Nodes[i]^), SIZE(Nodes[i]^), 0) ;
  END ;
END ResetNodes ;

PROCEDURE PackNodes() ;
  VAR i, p : CARDINAL ;
BEGIN
  p := 1 ;
  FOR i := 1 TO lastnode DO
    IF Nodes[i]^.num = 0 THEN   (* shift together *)
      IF p < i THEN p := i END ;
      WHILE (p <= lastnode) AND (Nodes[p]^.num = 0) DO
        INC(p) ;
        IF p > MaxNodes THEN Lib.FatalError("!pack!") END ;
      END ;
      IF p > CARDINAL(lastnode) THEN  (* at end, shrink *)
        nnodes := i-1 ;
        lastnode := nnodes ;  (* sic! *)
        RETURN ;
      END ;
      MoveNode(p, i) ;
    END ;
  END ;
END PackNodes ;

PROCEDURE ReadNodes(name : ARRAY OF CHAR) ;

  VAR f : FIO.File ;
      from, to : CARDINAL ;
      i : CARDINAL ;
      already : BOOLEAN ;
BEGIN
  f := FIO.Open (name) ;
  nnodes := 0 ;
  lastnode := 0 ;
  LOOP
    from := FIO.RdCard(f) ; IF NOT FIO.OK THEN EXIT END ;
    to   := FIO.RdCard(f) ; IF NOT FIO.OK THEN EXIT END ;
    LimitCheck ("Nodenumber", from, 1, MaxNodes) ;
    LimitCheck ("Nodenumber", to  , 1, MaxNodes) ;
    (* now let's go *)
    IF from > lastnode THEN lastnode := from END ;
    IF to   > lastnode THEN lastnode := to   END ;
    IF from <> to THEN
      WITH Nodes[from]^ DO
        IF num = 0 THEN INC(nnodes) END ;
        already := FALSE ;
        FOR i := 1 TO nlink DO IF links[i]=to THEN already:=TRUE END END ;
        IF NOT already THEN
          LimitCheck ("Links per Node", nlink+1, 0, MaxLinks) ;
          INC(nlink) ; links[nlink] := to   ; num := from ;
        END ;
      END ;
      WITH Nodes[to]^   DO
        IF num = 0 THEN INC(nnodes) END ;
        already := FALSE ;
        FOR i := 1 TO nlink DO IF links[i]=from THEN already:=TRUE END END ;
        IF NOT already THEN
          LimitCheck ("Links per Node", nlink+1, 0, MaxLinks) ;
          INC(nlink) ; links[nlink] := from ; num := to ;
        END ;
      END ;
    END ;
  END ;
  FIO.Close(f) ;
  PackNodes() ;
  FOR i := 1 TO nnodes DO
    NodeIndex := i ;
    Lib.HSort (Nodes[NodeIndex]^.nlink, CompareLinkList, SwapLinkList) ;
  END ;
END ReadNodes ;

PROCEDURE SavePicture() ;
  (* Output of picture as postscript program.
     All nodes will be defined and named.
     22.01.92: Color and more.
   *)
  VAR f : FIO.File ; fName : ARRAY[0..80] OF CHAR ;
      i, j : CARDINAL ; ok : BOOLEAN ;
BEGIN
  IO.WrStr("Postscript - outputfile = ") ;
  IO.RdItem(fName) ;
  f := FIO.Create(fName) ;
  FIO.WrStr(f, "% Postscript-Output from POLYTOP"+nl) ;
  FIO.WrStr(f, "% needs a prelude with the functions "+nl) ;
  FIO.WrStr(f, "% SetDimension, DefNode, DefEdge, DefEdgeOp,"+nl) ;
  FIO.WrStr(f, "% DefAttributes and Finish."+nl) ;
  FIO.WrStr(f, "% DefEdgeOp is used for /PG-Mode (Operators used)."+nl) ;
  FIO.WrLn(f) ;
  FIO.WrCard(f, Dimensions, 0) ;
  FIO.WrStr(f, " SetDimension"+nl) ;

  FIO.WrLn(f) ;
  FIO.WrStr(f, "% Node Positions:"+nl) ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    FIO.WrStr(f, "/N") ;
    FIO.WrCard(f, num , 0) ;
    FIO.WrStr(f, " dup [") ;
    FOR j := 1 TO Dimensions DO
      FIO.WrInt(f, INTEGER(pos[j]), 0) ;
      FIO.WrStr(f, " ") ;
    END ;
    FIO.WrStr(f, " ] def DefNode" +nl) ;
  END END ;

  FIO.WrLn(f) ;
  FIO.WrStr(f, "% Node Attributes:"+nl) ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    FIO.WrStr(f, "[ /N") ;
    FIO.WrCard(f, num , 0) ;
    FIO.WrStr(f, " (") ;
    FIO.WrCard(f, num , 0) ;
    FIO.WrStr(f, ") (") ;
    FIO.WrStr(f, perm) ;
    FIO.WrStr(f, ") ") ;
    FIO.WrCard(f, color, 0) ;
    FIO.WrStr(f, " ] DefAttributes" +nl) ;
  END END ;

  FIO.WrLn(f) ;
  FIO.WrStr(f, "% List of Links:"+nl) ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    FOR j := 1 TO nlink DO
      IF num < Nodes[links[j]]^.num THEN
        (* sonst bekomme ich alles doppelt gemalt *)
        FIO.WrStr(f, " /N") ;
        FIO.WrCard(f, CARDINAL(num), 0) ;
        FIO.WrStr(f, " /N") ;
        FIO.WrCard(f, CARDINAL(Nodes[links[j]]^.num ), 0) ;
        IF opno[j] = 0 THEN
          FIO.WrStr(f, " DefEdge"+nl) ;
        ELSE
          FIO.WrStr(f, "  ") ;
          FIO.WrCard(f, CARDINAL(opno[j]), 0) ;
          FIO.WrStr(f, " DefEdgeOp"+nl) ;
        END ;
      END ;
    END ;
  END END ;

  FIO.WrLn(f) ;
  FIO.WrStr(f, "% Generate the Picture:"+nl) ;
  FIO.WrStr(f, "Finish"+nl) ;
END SavePicture ;

PROCEDURE LoadPoly(VAR x : ARRAY OF BYTE) ;
  (* Read Polytop binary file   (19.09.95)
   *)
  VAR f : FIO.File ; fName : ARRAY[0..80] OF CHAR ;
      i, got : CARDINAL ; ok : BOOLEAN ;
  PROCEDURE rd(VAR x : ARRAY OF BYTE) ;
  BEGIN
    got := FIO.RdBin(f, x, SIZE(x)) ;
  END rd ;

BEGIN
  IO.WrStr("Polytop - binary file = ") ;
  IO.RdItem(fName) ;
  f := FIO.Open(fName) ;
  rd(x) ;
  rd(PM.BasePerm) ;
  rd(PM.OpTable) ;
  rd(PM.LastEditLine) ;
  PM.NewPermutograph(TRUE) ;
  rd(Dimensions) ;
  rd(nnodes) ;
  FOR i := 1 TO nnodes DO
    rd(Nodes[i]^) ;
  END ;
  FIO.Close(f) ;
END LoadPoly ;

PROCEDURE SavePoly(x : ARRAY OF BYTE) ;
  (* Read Polytop binary file   (19.09.95)
   *)
  VAR f : FIO.File ; fName : ARRAY[0..80] OF CHAR ;
      i, got : CARDINAL ; ok : BOOLEAN ;
  PROCEDURE wr(x : ARRAY OF BYTE) ;
  BEGIN
    FIO.WrBin(f, x, SIZE(x)) ;
  END wr ;

BEGIN
  IO.WrStr("Polytop - binary file = ") ;
  IO.RdItem(fName) ;
  f := FIO.Create(fName) ;
  wr(x) ;
  wr(PM.BasePerm) ;
  wr(PM.OpTable) ;
  wr(PM.LastEditLine) ;
  wr(Dimensions) ;
  wr(nnodes) ;
  FOR i := 1 TO nnodes DO
    wr(Nodes[i]^) ;
  END ;
  FIO.Close(f) ;
END SavePoly ;

BEGIN
  MaxNodes := 0 ;

END NodeMgr.