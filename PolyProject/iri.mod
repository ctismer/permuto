(* 11.07.92 : don't allow for target to be a broken node
              added a rest function
*)

IMPLEMENTATION MODULE Iri ;

IMPORT Str, Window ;

FROM NodeMgr IMPORT Nodes, nnodes ;

FROM IntVector IMPORT Norm, Scale ;

FROM Utilities IMPORT SetZero ;

CONST
  DEBUG = NOT TRUE ;

(*%T DEBUG *) Freq = 5 ; (*%E*)
(*%F DEBUG *) Freq = 9 ; (*%E*)

  C9 = CHR(Freq+ORD("0")) ; (* max possible char *)
  limit = (Freq+1)*(Freq+2) DIV 2 ;
VAR
  namestr : Label ;       (* actual name *)
  toright : BOOLEAN ;
  MessageNumber : CARDINAL ;

(********* constructing the network ********)

PROCEDURE Built() : BOOLEAN ;
BEGIN
  RETURN nnodes = limit ;
END Built ;

PROCEDURE Sweep () : Label ;
  (* build next name *)
  VAR res : Label ;
BEGIN
  res := namestr ;
  IF     toright AND (res[0]="0") THEN
    (* begin a new line *)
    DEC(res[1]) ; INC(res[2]) ;
    toright := FALSE ;
  ELSIF NOT toright AND (res[2]="0") THEN
    (* begin a new line *)
    DEC(res[1]) ; INC(res[0]) ;
    toright := TRUE ;
  ELSE
    IF toright THEN
      DEC(res[0]) ; INC(res[2]) ;
    ELSE
      INC(res[0]) ; DEC(res[2]) ;
    END ;
  END ;

  RETURN res ;
END Sweep ;

PROCEDURE Operate(this : Label ; op : INTEGER) : Label ;
  (* operation 1..6 *)
  VAR
    res : Label ; p1, p2 : INTEGER ;
BEGIN
  res := this ;
  CASE op OF
  | 1 : p1 := 1 ; p2 := 2 ;
  | 2 : p1 := 0 ; p2 := 2 ;
  | 3 : p1 := 0 ; p2 := 1 ;
  | 4 : p2 := 1 ; p1 := 2 ;
  | 5 : p2 := 0 ; p1 := 2 ;
  | 6 : p2 := 0 ; p1 := 1 ;
  ELSE RETURN this ;
  END ;
  IF (res[p1]<C9) & (res[p2] > "0") THEN
    INC(res[p1]) ; DEC(res[p2]) ;
  END ;
  RETURN res ;
END Operate ;

PROCEDURE SeekNode(name : Label) : INTEGER ;
  (* seeks if a node with "name" is already there.
     only for setup, so speed is no issue. *)
  VAR i : INTEGER ;
BEGIN
  FOR i := 1 TO nnodes DO
    IF Str.Compare(Nodes[i]^.perm, name) = 0 THEN
      RETURN i ;
    END ;
  END ;
  RETURN 0 ;
END SeekNode ;

PROCEDURE NewNode() ;
  (* inserts next node, if possible *)
VAR
  name : Label ;
  op, node2 : INTEGER ;
BEGIN
  name := namestr ;
  IF nnodes # limit THEN  (* i got more to create *)
    INC(nnodes) ;
    WITH Nodes[nnodes]^ DO
      Str.Copy(perm, name) ;
      num := nnodes ;
      CASE nnodes OF
      | 1, 2 : pos[1] := 0 ;
               pos[2] := Norm ;
      | 3    : pos[1] := Norm ;
               pos[2] := 0 ;
      ELSE
        pos[1] := Nodes[nnodes-1]^.pos[1] * 4 DIV 3 ;
        pos[2] := Nodes[nnodes-1]^.pos[2] * 4 DIV 3 ;
      END ;
      color := ORD(Window.Yellow) ;
      iri.avail := 10000 ;
      iri.avbak := 10000 ;
      FOR op := 1 TO 6 DO
        name := Operate(namestr, op) ;
        node2 := 0 ;
        IF (name # namestr) THEN
          node2 := SeekNode(name) ;
        END ;
        IF node2 # 0 THEN
          INC(nlink) ;
          links[nlink] := node2 ;
          WITH Nodes[node2]^ DO
            INC(nlink) ;
            links[nlink] := nnodes ;
          END ;
        END ;
      END ;
    END ;
  END ;
  namestr := Sweep() ;
END NewNode ;

PROCEDURE KillNode(name : Label) ;
  VAR num : INTEGER ;
BEGIN
  num := SeekNode(name) ;
  IF num # 0 THEN WITH Nodes[num]^ DO
    IF iri.avail # 0 THEN
      iri.avail := 0
    ELSE
      iri.avail := 10000 ;
    END ;
  END END ;
END KillNode ;


VAR ActColor : CARDINAL ;

PROCEDURE NextColor() : CARDINAL ;
BEGIN
  REPEAT
    ActColor := (ActColor+1) MOD 16 ;
  UNTIL NOT (ActColor IN
    { ORD(Window.Blue), ORD(Window.Yellow), ORD(Window.Black) }) ;
  RETURN ActColor ;
END NextColor ;

PROCEDURE Transmit (from, to : Label ; repeat: CARDINAL) ;
  (* new: if repeat # 0, we will store this for later resending *)
  VAR n1, n2 : INTEGER ;
BEGIN
  n1 := SeekNode(from) ;
  n2 := SeekNode(to) ;
  IF (n1 # 0) AND (n2 # 0) THEN WITH Nodes[n1]^ DO
    IF (iri.avail # 0) AND (Nodes[n2]^.iri.avail # 0) THEN
      iri.target := n2 ;
      MessageNumber := (MessageNumber MOD 100) + 1 ;
      iri.message.num := MessageNumber ;
      iri.message.color := ORD(Window.Red) ;
      Nodes[n2]^.color := ORD(Window.Blue) ;
      Nodes[n2]^.iri.message.num := MessageNumber ;
      IF repeat # 0 THEN
        iri.sender.target := n2 ;
        iri.sender.repeat := repeat ;
        iri.sender.color := NextColor() ;
        color := iri.sender.color ;
      END ;
      IF iri.sender.repeat # 0 THEN
        iri.message.color := iri.sender.color ;
      END ;
      color := iri.message.color ;
    END ;
  END END ;
END Transmit ;

PROCEDURE NumToLabel(num : CARDINAL) : Label ;
  VAR
    res : Label ;
BEGIN
  res[3] := 0C ;
  res[2] := CHR(ORD("0")+num MOD 10) ; num := num DIV 10 ;
  res[1] := CHR(ORD("0")+num MOD 10) ; num := num DIV 10 ;
  res[0] := CHR(ORD("0")+num MOD 10) ; num := num DIV 10 ;
  RETURN res ;
END NumToLabel ;

PROCEDURE Distance(p1, p2 : ARRAY OF CHAR) : INTEGER ;
  VAR
    i, dist : INTEGER ;
    x1, x2 : INTEGER ;
BEGIN
  dist := 0 ;
  FOR i := 0 TO 2 DO
    x1 := ORD(p1[i])-ORD("0") ;
    x2 := ORD(p2[i])-ORD("0") ;
    dist := dist+ABS(x2-x1) ;
  END ;
  RETURN dist ;
END Distance ;

PROCEDURE BestMove(node : CARDINAL) : CARDINAL ;
  VAR
    qual  : ARRAY[1..6] OF INTEGER ;
    avail : ARRAY[1..6] OF INTEGER ;
    i : INTEGER ;
    dist, dist2 : INTEGER ;
    best : INTEGER ;
    tstr : Label ;
BEGIN
  SetZero(qual) ;
  WITH Nodes[node]^ DO
    Str.Copy(tstr, Nodes[iri.tarbak]^.perm) ;
    dist := Distance(perm, tstr) ;
    FOR i := 1 TO nlink DO
      dist2 := Distance(Nodes[links[i]]^.perm, tstr) ;
      IF    dist < dist2 THEN qual[i] := 2
      ELSIF dist = dist2 THEN qual[i] := 3
      ELSE                    qual[i] := 5
      END ;
      (* now, quality can be seen as a level of intention. In a future
         version, we will introduce priorities here.
      *)
      avail[i] := Nodes[links[i]]^.iri.avbak ;
    END ;

    (* now decide *)
    best := 0 ;
    FOR i := nlink TO 1 BY -1 DO
      (* try to find just one possible move to compare with *)
      IF (avail[i] # 0)
      AND (Nodes[links[i]]^.iri.target = 0) THEN best := i END ;
    END ;
    IF best = 0 THEN
      (* cannot move anyway *)
      RETURN node ;
    END ;

    (* this is the final decision step. The intention is weighted by
       the availability.
    *)
    FOR i := 1 TO nlink DO
      IF (Nodes[links[i]]^.iri.target = 0)
      AND (Scale(qual[i], avail[i], 5) > Scale(qual[best], avail[best], 5))
      THEN best := i END ;
    END ;
    RETURN links[best] ;
  END ;
END BestMove ;

PROCEDURE Movements() ;
  VAR
    i  : INTEGER ;
    tg : INTEGER ;
    to : INTEGER ;
    msg : INTEGER ;
    col : INTEGER ;
BEGIN
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IF iri.avail # 0 THEN
      IF iri.tarbak # 0 THEN
        tg := iri.tarbak ;
        to := BestMove(i) ;
        msg := iri.message.num ;
        col := iri.message.color ;
        iri.target := 0 ;
        iri.message.num := 0 ;
        iri.avail := Scale(iri.avail, 8000, 10000) ;  (* discharge for use *)
        IF tg # i THEN
          Nodes[to]^.iri.target := tg ;
          Nodes[to]^.iri.message.num := msg ;
          Nodes[to]^.iri.message.color := col ;
        (* else we found the target *)
        END ;
        color := ORD(Window.Yellow) ;
      END ;
    END ;
  END END ;

  (* now we have cleaned up. hidden message numbers must
     be revived, if they were hidden in multiple targets *)
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IF iri.avail # 0 THEN
      IF iri.target # 0 THEN
        color := iri.message.color ;
        to := iri.target ;
        IF Nodes[to]^.iri.target = 0 THEN
          Nodes[to]^.iri.message := iri.message ;
          Nodes[to]^.color := ORD(Window.Blue) ;
        END ;
      END ;
    END ;
  END END ;
END Movements ;

PROCEDURE Repeat () ;  (* repeat all stored messages *)
  VAR
    i  : INTEGER ;
    tg : INTEGER ;
    to : INTEGER ;
    msg : INTEGER ;
BEGIN
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IF iri.avail # 0 THEN
      IF iri.target = 0 THEN
        IF iri.sender.repeat # 0 THEN
          to := iri.sender.target ;
          IF Nodes[to]^.iri.avail # 0 THEN
            Transmit(Label(perm), Label(Nodes[to]^.perm), 0) ;
            DEC(iri.sender.repeat) ;
          END ;
        END ;
      END ;
    END ;
  END END ;
END Repeat ;

PROCEDURE Step() ;
  (* compute new network status *)
  VAR
    i, j : INTEGER ;
    av : CARDINAL ;
BEGIN
  (* backup availability and targets *)
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    iri.avbak  := iri.avail ;
    iri.tarbak := iri.target ;
  END END ;

  (* compute new availability *)
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IF iri.avail # 0 THEN
      av := 0 ;
      FOR j := 1 TO nlink DO
        av := av + Nodes[links[j]]^.iri.avbak ;
      END ;
      (* take neighbourhood into account, and also recharge *)
      av := av DIV nlink ;
      iri.avail := Scale(iri.avail, 6500, 10000)   (* own value *)
                 + Scale(av,        3000, 10000)   (* neighbours *)
                 + Scale(10000,      500, 10000) ; (* recharge *)
    END ;
  END END ;

  (* move information *)
  Movements() ;
END Step ;

PROCEDURE Reset() ;    (* remove any states from the network *)
  VAR
    i : INTEGER ;
BEGIN
  FOR i := 1 TO nnodes DO
    WITH Nodes[i]^ DO
      color := ORD(Window.Yellow) ;
      SetZero(iri) ;
      iri.avail := 10000 ;
      iri.avbak := 10000 ;
    END ;
  END ;
  ActColor := ORD(Window.Red)-1 ;
END Reset ;

BEGIN
  namestr  := "0" + C9 + "0" ;
  toright := TRUE ;
  MessageNumber := 0 ;
  ActColor := ORD(Window.Red)-1 ;

END Iri.
