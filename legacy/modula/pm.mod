(*************************************************************

   Permutographs

*************************************************************)

IMPLEMENTATION MODULE PM ;

IMPORT Str, IO, Window, Lib, Graph ;

IMPORT KEY ;

FROM NodeMgr IMPORT MaxNodesTot, MaxNodes, MaxLinks, MaxDimen, PermStr,
                    Dimensions, Nodes, nnodes, lastnode,
                    PackNodes, NodePtr, LinkArray,
                    ResetNodes ;

FROM IntVector IMPORT ZeroVector ;

IMPORT IntVector ;

FROM ScreenHandler IMPORT GotoXY, WhereX, WhereY, ClrEol ;

FROM UserIO IMPORT InputStr ;

FROM Utilities IMPORT SetZero ;

(* this nice procedure was taken from the examples directory
   of the TopSpeed environment and fitted nicely in here.
*)
PROCEDURE NextPerm(n:CARDINAL ; VAR s:ARRAY OF BYTE ;
                   VAR wrap:BOOLEAN) ;
VAR
  i:CARDINAL ; (* s[i-1] is the most significant byte changed *)
  j:CARDINAL ; (* s[j] is the byte to be swapped with s[i-1] *)
  tmp:BYTE ;
BEGIN
  IF n = 0 THEN
    wrap := TRUE ;
    RETURN ;
  END ;
  i := n - 1 ;
  LOOP
    IF i = 0 THEN
      wrap := TRUE ;
      EXIT ;
    END ;
    IF s[i-1] < s[i] THEN
      j := n - 1 ;
      WHILE s[j] <= s[i-1] DO
        j := j - 1 ;
      END ;
      tmp := s[j] ; s[j] := s[i-1] ; s[i-1] := tmp ; (* swap *)
      wrap := FALSE ;
      EXIT ;
    END ;
    i := i - 1 ;
  END ;
  (* s[i]..s[n-1] are in reverse order, reversing them
     yields the minimum permutation we require *)
  j := n - 1 ;
  WHILE i < j DO
    tmp := s[j] ; s[j] := s[i] ; s[i] := tmp ;
    i := i + 1 ;
    j := j - 1 ;
  END ;
END NextPerm ;

(* extension, 22.03.92:
   a mask is given, that determines, which places are taken
   to be equivalent. This is a trial, to factorize out subgroups.
   So, nextperm takes an additional parameter now.
*)
PROCEDURE ToLastInClass(VAR s : ARRAY OF CHAR ; equiv : ARRAY OF CHAR) ;
  VAR i, j, p, q, classlen : CARDINAL ; h : CHAR ;
BEGIN
  (* bring the values in equivalence class to their maximum
     position, so NextPermPure will skip the whole class.
     equiv must be '0' for each position that is not in the equivalence class.
  *)
  (* make equiv to an index table. o_a_copy must be true. *)
  classlen := 0 ;
  FOR i := 0 TO Str.Length(equiv) DO
    IF equiv[i] # '0' THEN
      equiv[classlen] := CHR(i) ;
      INC(classlen) ;
    END ;
  END ;
  FOR i := 0 TO classlen-2 DO
    FOR j := i TO classlen-1 DO
      p := ORD(equiv[i]) ; q := ORD(equiv[i+1]) ;
      IF s[p] < s[q] THEN
        h := s[p] ; s[p] := s[q] ; s[q] := h ;
      END ;
    END ;
  END ;
END ToLastInClass ;

(* Brute Force : find the Name of a given Permutation.
   We simply permute until we reached the goal.
 *)
(* 22.02.92: enhancement. permutations are now stored in a cache
             and sought there by bisection.
             PermBasisValid builds this table.
*)

VAR
  PermCache      : ARRAY[0..MaxNodesTot] OF PermStr ;
  PermCacheSize  : CARDINAL ;

PROCEDURE PermBisect (Perm : ARRAY OF CHAR) : CARDINAL ;
  VAR lo, hi, p: CARDINAL ;
BEGIN
  lo := 1 ;
  hi := PermCacheSize ;
  WHILE lo < hi DO
    p := (lo+hi) DIV 2 ;
    CASE Str.Compare(PermCache[p], Perm) OF
    |  0 : RETURN p ;   (* found it *)
    | -1 : lo := p+1 ;
    |  1 : hi := p-1 ;
    END ;
  END ;
  RETURN 0 ;
END PermBisect ;

PROCEDURE PermName (Order: CARDINAL ; Base, Perm: ARRAY OF CHAR) : CARDINAL ;
  VAR wrap : BOOLEAN ; Name : CARDINAL ;
BEGIN
  IF Str.Compare(Base,PermCache[0]) = 0 THEN
    Name := PermBisect(Perm) ;
  END ;
  IF Name # 0 THEN
    RETURN Name ;
  END ;

  (* not in cache, compute it *)
  Name := 0 ;
  REPEAT
    INC(Name) ;
    IF Str.Compare(Base, Perm) = 0 THEN RETURN Name END ;
    NextPerm(Order, Base, wrap) ;
  UNTIL wrap ;
  (* falsche Parameter, nix gefunden *)
  RETURN 0 ;
END PermName ;

PROCEDURE PermBasisValid (perm : ARRAY OF CHAR) : BOOLEAN ;
(* permute around, and when there is not more than MaxNodes,
   the string is ok.
   We don't allow more places than Dimensions of our Polytopes.
   22.02.92: as as side effect, this procedure also computes
             the PermCache.
*)
  VAR i : CARDINAL ;
      p1, p2 : PermStr ;
      order : INTEGER ;
      wrap : BOOLEAN ;
BEGIN
  order := Str.Length(perm) ;
  IF order > MaxDimen THEN RETURN FALSE END ;
  Str.Copy (p1, perm) ;
  Str.Copy (p2, perm) ;
  i := 0 ;
  PermCacheSize := 0 ;
  PermCache[0] := p1 ;
  REPEAT
    INC(PermCacheSize) ;
    PermCache[PermCacheSize] := p2 ;
    NextPerm(Order, p2, wrap) ;
    INC(i) ;
    IF i >= MaxNodes THEN
      PermCacheSize := 0 ;
      RETURN FALSE ;
    END ;
  UNTIL Str.Compare(p1, p2) = 0 ;
  RETURN TRUE ;
END PermBasisValid ;

PROCEDURE FindBase(VAR perm : ARRAY OF CHAR) ;
  (* find the lexicographic smallest representation for perm. *)
  VAR order, i, j : INTEGER ; c : CHAR ;
BEGIN
  order := Str.Length(perm) ;
  FOR i := 0 TO order-2 DO
    FOR j := i+1 TO order-1 DO
      IF perm[i] > perm[j] THEN
        c := perm[i] ; perm[i] := perm[j] ; perm[j] := c ;
      END ;
    END ;
  END ;
  (* straight sorting appropriate here *)
END FindBase ;

PROCEDURE ValidCycle (order : CARDINAL ; cyc : ARRAY OF CHAR) : BOOLEAN ;
  (* a cycle operator has to consist of the characters
     "1".."8", if MaxDimen is 8 *)
  VAR i : INTEGER ;
BEGIN
  FOR i := 0 TO Str.Length(cyc)-1 DO
    IF (cyc[i] < "1") OR (cyc[i] > CHR(ORD("0")+order)) THEN
      RETURN FALSE ;
    END ;
  END ;
  RETURN TRUE ;
END ValidCycle ;

PROCEDURE CyclicOperate (VAR perm : ARRAY OF CHAR ; op : ARRAY OF CHAR) ;
  (* lets a validated cyclic operator work on perm. *)
  VAR p : PermStr ; len : CARDINAL ; i, x, y : CARDINAL ;
BEGIN
  Str.Copy(p, perm) ;
  len := Str.Length(op) ;
  y := ORD(op[0]) - ORD("0") -1 ;  (* M2-strings count from 0 *)
  FOR i := 1 TO len DO
    x := y ;
    y := ORD(op[i MOD len]) - ORD("0") -1 ;
    perm[y] := p[x] ;
  END ;
END CyclicOperate ;

(* and now the application. this is really not my style,
 but under pressure ... *)

(* this code is really hacked, for to have at least something...
   will be replaced soon!
*)
PROCEDURE EditDisplay(row, col : INTEGER ; edit : BOOLEAN ) ;

  PROCEDURE _do_ (row, col : INTEGER ; name : ARRAY OF CHAR ;
                                   VAR vari : ARRAY OF CHAR ;
                                       isbase: BOOLEAN) ;
    VAR
      len : INTEGER ; ok : BOOLEAN ;
      chars : KEY.CharSet ;
      codes : KEY.CodeSet ;
      i : INTEGER ;
      c : CHAR ;
  BEGIN
    GotoXY (col, row) ;
    IO.WrStr(name) ;
    IF edit THEN
      SetZero(chars) ;
      SetZero(codes) ;
      FOR c := '0' TO '9' DO INCL(chars, c) END ;
      INCL(codes, KEY.UP) ;
      INCL(codes, KEY.DOWN) ;
      INCL(codes, KEY.ESC) ;
      INCL(codes, KEY.C_HOME) ;
      INCL(codes, KEY.C_END) ;
      INCL(codes, KEY.RETURN_) ;
      REPEAT
        GotoXY (col+5, row) ;
        InputStr(vari, chars, codes) ;
        IF isbase THEN
          ok := PermBasisValid(BasePerm) ;
        ELSE
          ok := ValidCycle(Str.Length(BasePerm), vari) ;
        END ;
      UNTIL ok ;
      IF isbase THEN
        FindBase(BasePerm) ;  (* take minimum representation *)
      END ;
    END ;
    GotoXY (col+5, row) ;
    IO.WrStr(vari) ;
    len := Str.Length(vari) ;
    IF len < MaxDimen THEN IO.WrCharRep(" ", MaxDimen-len) END ;
  END _do_ ;

  VAR i, j : CARDINAL ; ops : ARRAY[0..5] OF CHAR ;
      here, min, max : CARDINAL ;
BEGIN
  min := row ;
  max := min + MaxOps * MaxCyc
         + 1 (* base *)
         + 1 (* skipped line after base *)
         -1 ;
  here := min ;
  IF edit THEN here := min+LastEditLine-1 END ;
  IF (here<min) OR (here>max) THEN here := min END ;
  REPEAT
    IF here=min THEN
      _do_(row, col, "Base ", BasePerm, TRUE) ;
    ELSE
      ops := "Op 0" ;
      i := (here-min-2) DIV MaxCyc +1 ;
      j := (here-min-2) MOD MaxCyc +1 ;
      INC(ops[4-1], BYTE(i)) ;  (* "1","2","3" ... *)
      IF j # 1 THEN ops := '' END ;
      _do_(here, col, ops, OpTable[i, j], FALSE) ;
    END ;
    IF edit THEN
      LastEditLine := here-min+1 ;
      CASE KEY.Code OF
      | KEY.UP      : IF here > min THEN DEC(here) END ;
                      IF here = min+1 THEN DEC(here) END ;
      | KEY.DOWN    : IF here < max THEN INC(here) END ;
                      IF here = min+1 THEN INC(here) END ;
      | KEY.C_HOME  : here := min ;
      | KEY.C_END   : (* find last entry *)
              here := max ;
              WHILE (here > min+1) AND
                    (OpTable[(here-min-2) DIV MaxCyc +1,
                             (here-min-2) MOD MaxCyc +1 ] = PermStr("")) DO
                DEC(here) ;
              END ;
              IF here = min+1 THEN DEC(here) END ;
      | KEY.ESC,
        KEY.RETURN_ : here := max+1 ;
      END ;
    ELSE
      INC(here) ;
      IF here = min+1 THEN INC(here) END ;
    END ;
  UNTIL (here > max) ;
END EditDisplay ;


PROCEDURE PolytopFilter(perm: ARRAY OF CHAR) : BOOLEAN ;
  (* says if perm is valid or not *)
  (* disabled for now *)
BEGIN
  RETURN TRUE ;
(*    RETURN (perm[0]#'1') AND (perm[0]#'5') ; *)
END PolytopFilter ;

PROCEDURE NewPermutograph(reset : BOOLEAN) ;
  VAR p, q : PermStr ; wrap : BOOLEAN ; n, i, j: INTEGER ;
      from, to : CARDINAL ; already : BOOLEAN ;
      hold : INTEGER ;
      lastdimension : INTEGER ;
BEGIN
  IF reset THEN
    ResetNodes() ;  (* get rid of old junk *)
    FindBase(BasePerm) ;
    p := BasePerm ;
    Order := Str.Length(BasePerm) ;
    (* trigger cache computing, if forgotten *)
    IF NOT PermBasisValid(BasePerm) THEN HALT() END ;
    nnodes := 0 ;
    REPEAT
      INC(nnodes) ;
      WITH Nodes[nnodes]^ DO
        IF PolytopFilter(p) THEN
          num := nnodes ;
        ELSE
          num := 0 ;
        END ;
        perm := p ;
        (* color is position of first entry in base *)
        color := Str.Pos(BasePerm,perm[0]) +1 ;
      END ;
      NextPerm(Order, p, wrap) ;
    UNTIL wrap ;
    lastdimension := 0 ;
  ELSE
    (* no reset, only the links will be recomputed *)
    FOR i := 1 TO nnodes DO
      WITH Nodes[i]^ DO
        nlink := 0 ;
        SetZero(links) ;
        SetZero(opno) ;
        SetZero(state) ;
      END ;
    END ;
    lastdimension := Dimensions ;
  END ;  (* IF reset *)

  Dimensions := MaxDimen ;
  IntVector.SetDimensions(Dimensions) ;

  (* now we know the number of Permutations. We still have to
     link the balls and put them somewhere in the field : *)

  p := BasePerm ;
  FOR n := 1 TO nnodes DO
    (* let the operators operate *)
    FOR j := 1 TO MaxOps DO
      q := p ;
      FOR i := 1 TO MaxCyc DO
        CyclicOperate(q, OpTable[j,i]) ;
      END ;
      from := n ;
      to   := PermName(Order, BasePerm, q) ;
      (* now let's go *)
      IF (from <> to) AND PolytopFilter(p) AND PolytopFilter(q) THEN
        WITH Nodes[from]^ DO
          already := FALSE ;
          FOR i := 1 TO nlink DO IF links[i]=to THEN already:=TRUE END END ;
          IF NOT already THEN
            INC(nlink) ; links[nlink] := to ;
            opno[nlink] := SHORTCARD(j) ;
          END ;
        END ;
        WITH Nodes[to]^   DO
          already := FALSE ;
          FOR i := 1 TO nlink DO IF links[i]=from THEN already:=TRUE END END ;
          IF NOT already THEN
            INC(nlink) ; links[nlink] := from ;
            opno[nlink] := SHORTCARD(j) ;
          END ;
        END ;
      END ;
    END ;
    NextPerm(Order, p, wrap) ;

    (* last step: put ‚m somewhere *)
    (* initialize the new dimensions only,
       retain old picture if possible. *)

    WITH Nodes[n]^ DO
      (* make shure that collapsed structure gets shuffled *)
      FOR i := 1 TO lastdimension DO
        pos[i] := pos[i] + INTEGER(links[i]) MOD 43 ;  (* primes are good here *)
      END ;
      (* initiate the new dimensions *)
      FOR i := lastdimension+1 TO Dimensions DO
        pos[i] := links[i] ;
      END ;
    END ;
  END ;

  (* for future: kill all the unlinked nodes : *)
  lastnode := nnodes ;
  PackNodes() ;

END NewPermutograph ;

PROCEDURE EdPermuto(edit : BOOLEAN) ;
  (* edit base and cyclic operators, then generate the Permutograph *)
  VAR comp : PermStr ; i, j : INTEGER ;
BEGIN
  EditDisplay(4, 64, FALSE) ;
  IF edit THEN
    comp := BasePerm ;
    EditDisplay(4, 64, TRUE) ;

    (* check if there is an invalid Operator left and erase it *)
    FOR i := 1 TO MaxOps DO FOR j := 1 TO MaxCyc DO
      IF NOT ValidCycle(Str.Length(BasePerm), OpTable[i,j]) THEN
        SetZero(OpTable[i,j])
      END ;
    END END ;

    EditDisplay(4, 64, FALSE) ;
    NewPermutograph((comp # BasePerm) OR (nnodes=0)) ;
    (* if the same Base is used, we will use the same picture
       without erasing the positions. this makes a nice move
       from one contexture to another.
    *)
  END ;
END EdPermuto ;

PROCEDURE FindLink (n1, n2: CARDINAL) : CARDINAL ;
  VAR i : CARDINAL ;
BEGIN
  WITH Nodes[n1]^ DO
    FOR i := 1 TO nlink DO
      IF links[i] = n2 THEN RETURN i END ;
    END ;
  END ;
  RETURN 0 ;
END FindLink ;

PROCEDURE IsLinked(n1, n2: CARDINAL) : BOOLEAN ;
BEGIN
  IF (n1=n2) THEN RETURN TRUE END ;
  RETURN FindLink(n1, n2) > 0 ;
END IsLinked ;

PROCEDURE LinksAvail(n1, n2: CARDINAL) : BOOLEAN ;
  (* check if both have an empty slot *)
BEGIN
  RETURN (Nodes[n1]^.nlink < MaxLinks) AND
         (Nodes[n2]^.nlink < MaxLinks)
END LinksAvail ;

PROCEDURE Disconnect (n1, n2 : CARDINAL) ;
  VAR p : NodePtr ; i : INTEGER ;
BEGIN
  IF IsLinked(n1, n2) AND (n1#n2) THEN
    p := Nodes[n1] ;
    WITH p^ DO
      FOR i := FindLink(n1, n2) TO nlink-1 DO
        links[i] := links[i+1] ;
        opno[i]   := opno[i+1] ;
      END ;
      DEC(nlink) ;
    END ;
    Disconnect (n2, n1) ;
  END ;
END Disconnect ;

PROCEDURE ExecOperator(n1 : CARDINAL ; op : CARDINAL) : CARDINAL ;
  VAR
    p : PermStr ; i : INTEGER ;
BEGIN
  IF op = 0 THEN RETURN n1 END ;
  p := Nodes[n1]^.perm ;
  FOR i := 1 TO MaxCyc DO
    CyclicOperate(p, OpTable[op,i]) ;
  END ;
  RETURN PermName(Order, BasePerm, p) ;
END ExecOperator ;

PROCEDURE WhichOperator (n1, n2 : CARDINAL) : SHORTCARD ;
  VAR i : CARDINAL ;
BEGIN
  FOR i := 1 TO MaxOps DO
    IF (ExecOperator(n1, i) = n2)
    OR (ExecOperator(n2, i) = n1)
    THEN
      RETURN SHORTCARD(i) ;
    END ;
  END ;
  RETURN 0 ;
END WhichOperator ;

PROCEDURE Connect (n1, n2 : CARDINAL) ;
  VAR p : NodePtr ;
BEGIN
  IF NOT IsLinked(n1, n2) AND (n1>0) AND (n2>0) THEN
    IF LinksAvail(n1, n2) THEN
      p := Nodes[n1] ;
      WITH p^ DO
        INC(nlink) ;
        links[nlink] := n2 ;
        opno[nlink] := WhichOperator(n1, n2) ;
      END ;
      Connect(n2, n1) ;
    END ;
  END ;
END Connect ;

PROCEDURE Collapse (n1, n2 : CARDINAL) ;
  VAR i : CARDINAL ; node : CARDINAL ;
BEGIN
  IF IsLinked(n1, n2) THEN
    Disconnect(n1, n2) ;
    WITH Nodes[n1]^ DO
      FOR i := 1 TO nlink DO
        node := links[1] ;
        Disconnect(n1, node) ;
        Connect(node, n2) ;
      END ;
      (* index 1 is ok. link arrays get shifted by Disconnect *)
    END ;
  END ;
END Collapse ;

PROCEDURE Uncollapse (n1 : CARDINAL) ;
  VAR i, j, n : CARDINAL ; node : CARDINAL ;
      hold : LinkArray ;
BEGIN
  hold := Nodes[n1]^.links ;
  n    := Nodes[n1]^.nlink ;
  FOR i := 1 TO n DO
    Disconnect(n1, hold[i]) ;
  END ;
  FOR i := 1 TO MaxOps DO
    node := ExecOperator(n1, i) ;
    Connect (n1, node) ;
  END ;
END Uncollapse ;


BEGIN
  BasePerm := "1234" ;
  Lib.Fill(ADR(OpTable), SIZE(OpTable), 0) ;
  OpTable[1,1] := "12" ;
  OpTable[2,1] := "23" ;
  OpTable[3,1] := "34" ;

  LastEditLine := 0 ;
  Order := 0 ;
  SetZero(PermCache) ;
  PermCacheSize := 0 ;

END PM.
