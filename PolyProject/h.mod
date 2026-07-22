(* dieses programm dient nur dazu, festzustellen, wie viele
   wege der l„nge 17 es im 120er von 1 aus gibt.  17.11.91

   Ergebnis:
   85477800 Wege der L„nge 17 gibt es ab Knoten 1.

*)

(* H    Hamilton-Kreise finden            kr0te, 13.11.91
*)

MODULE H ;

IMPORT IO, FIO, Lib, Window ;

CONST
  Grad = 5 ;

  Grad3 = Grad = 3 ;
  Grad4 = Grad = 4 ;
  Grad5 = Grad = 5 ;
  Grad6 = Grad = 6 ;
  Grad7 = Grad = 7 ;

(* es gibt Grad! Knoten *)
(*%T Grad3*) Nodes = 3*2*1 ; (*%E*)
(*%T Grad4*) Nodes = 4*3*2*1 ; (*%E*)
(*%T Grad5*) Nodes = 5*4*3*2*1 ; (*%E*)
(*%T Grad6*) Nodes = 6*5*4*3*2*1 ; (*%E*)
(*%T Grad7*) Nodes = 7*6*5*4*3*2*1 ; (*%E*)

  Links = Grad-1 ;

(* es gibt (Links ber 2) Kreise, da Kreise aus allen Paaren aus
   Negationen gebildet werden.
*)

  Circles = (Links) * (Links-1) DIV 2 ;

(* jeder Operator kommt in (Links-1) Kreisen vor. *)

  CperLink = Links-1 ;

TYPE
  LinkList = ARRAY[0..Links] OF INTEGER ;
  NodeRec = RECORD
              L : LinkList ;
              M : INTEGER ;
            END ;
  NodeTab = ARRAY[0..Nodes] OF NodeRec ;

  NameType = ARRAY[0..Grad] OF CHAR ;

PROCEDURE ResetLinkList (VAR L : LinkList) ;
  VAR i : INTEGER ;
BEGIN
  FOR i := 0 TO Links DO L[i] := 0 END ;
END ResetLinkList ;

PROCEDURE ResetMarks (VAR N : NodeTab) ;
  VAR i : INTEGER ;
BEGIN
  FOR i := 0 TO Nodes DO N[i].M := 0 END ;
END ResetMarks ;

PROCEDURE ResetNodes (VAR N : NodeTab) ;
  VAR i : INTEGER ;
BEGIN
  FOR i := 0 TO Nodes DO ResetLinkList(N[i].L) END ;
  ResetMarks(N) ;
END ResetNodes ;

PROCEDURE NumToName(Num : INTEGER ; VAR Name : NameType) ;
  VAR i, p : INTEGER ; c : CHAR ;
      split : ARRAY[0..Grad-1] OF INTEGER ;
BEGIN
  DEC(Num) ;
  Name[Grad] := 0C ;
  FOR i := Grad-1 TO 0 BY -1 DO
    split[i] := Num MOD (Grad-i) ;
    Num := Num DIV (Grad-i) ;
    Name[i] := CHR(ORD('1') + i) ;
  END ;
  FOR i := 0 TO Grad-1 DO
    c := Name[split[i]+i] ;
    FOR p := split[i]+i TO i+1 BY -1 DO
      Name[p] := Name[p-1] ;
    END ;
    Name[i] := c ;
  END ;
END NumToName ;

PROCEDURE NameToNum(Name : NameType) : INTEGER ;
  VAR i, p : INTEGER ; c : CHAR ;
      Num : INTEGER ;
BEGIN
  Num := 0 ;
  FOR i := 0 TO Grad-1 DO
    Num := Num * (Grad-i) ;
    c := Name[i] ;
    FOR p := i+1 TO Grad-1 DO
      IF c > Name[p] THEN INC(Num) END ;
    END ;
  END ;
  RETURN Num+1 ;
END NameToNum ;

PROCEDURE BuildGraph (VAR g : NodeTab) ;
  VAR i, op : INTEGER ; Name, Name2 : NameType ;
BEGIN
  FOR i := 1 TO Nodes DO
    NumToName(i, Name) ;
    FOR op := 1 TO Links DO
      Name2 := Name ;
      Name2[op] := Name[op-1] ;
      Name2[op-1] := Name[op] ;
      g[i].L[op] := NameToNum(Name2) ;
    END ;
  END ;
END BuildGraph ;

CONST F = FIO.StandardOutput ;

(* simpler rekursiver Ansatz *)
PROCEDURE HamiltonCircles(VAR g : NodeTab) ;
  VAR
    ops : ARRAY[0..Nodes] OF CHAR ;
    count, calls : LONGINT ;

  PROCEDURE try(lev, node : INTEGER) ;
    VAR op : INTEGER ; next : INTEGER ;
  BEGIN
    IF (lev < 17+1) THEN
      FOR op := 1 TO Links DO
        next := g[node].L[op] ;
        IF g[next].M = 0 THEN
          g[next].M := node ;   (* Marks gehen hier rckw„rts *)
          ops[lev-1] := CHR(ORD('0')+op) ;
          INC(calls) ;
          try(lev+1, next) ;
          g[next].M := 0 ;
        END ;
      END ;
    ELSE
      INC(count) ;
      IF (count MOD 100) = 0 THEN
        IO.WrLngInt(count,5) ;
        IO.WrStr("  ") ;
        ops[lev-1] := 0C ;
        IO.WrStr(ops) ;
        IF (count MOD 2500) = 0 THEN Window.GotoXY(1,1) ELSE
          IO.WrLn() ;
        END ;
      END ;
    END ;
  END try ;

BEGIN
  count := 0 ;
  calls := 0 ;
  ops[Nodes] := 0C ;
  try(1, 1) ;
  FIO.WrLngInt(F, count,0) ;
  FIO.WrStr(F, ' Hamiltonkreise gefunden. ') ;
  FIO.WrLngInt(F, calls,0) ;
  FIO.WrStr(F, ' rekursive Aufrufe.') ;
  FIO.WrLn(F) ;
END HamiltonCircles ;


(* komplizierterer Ansatz : operiere mit Maschen.
   versuche, Kanten durch Maschen zu ersetzen, bis gefunden.
*)

TYPE
  CycleType = RECORD               (* Beschreibung eines Zyklus *)
    len : INTEGER ;
    ops : ARRAY[1..6] OF INTEGER ;
  END ;

(* Tabelle, die fr jeden Operator (=Link) die m”glichen Kreise angibt: *)
VAR
  CycTab : ARRAY[1..Links] OF ARRAY[1..CperLink] OF CycleType ;

PROCEDURE BuildCycTab(VAR g : NodeTab) ;
  (* g muá intakten Permutographen enthalten. *)
  (* fr jeden Operator (=Link) wird eine Liste der Kreise angelegt,
     die durch diesen Link gehen. Die Liste ist jeweils lexikographisch
     sortiert.
  *)
  VAR link, op1, op2, pos, i : INTEGER ;
BEGIN
  Lib.Fill(ADR(CycTab), SIZE(CycTab), 0) ;
  FOR link := 1 TO Links DO
    i := 0 ;
    op1 := link ;
    FOR op2 := 1 TO Links DO
      IF (op1 # op2) THEN
        INC(i) ;
        pos := 1 ;
        WITH CycTab[link] [i] DO
          len := 0 ;
          REPEAT
            INC(len) ;
            ops[len] := op1 ;
            pos := g[pos].L[op1] ;
            INC(len) ;
            ops[len] := op2 ;
            pos := g[pos].L[op2] ;
          UNTIL pos = 1 ;
        END ;
      END ;
    END ;
  END ;
END BuildCycTab ;

PROCEDURE MakeCycle(VAR g : NodeTab ;    (* I/O *)
                        n : INTEGER ;      (* I *)
                    VAR c : CycleType) ;   (* I *)
  (* hier werden nur die Operatoren gespeichert, keine Knotennummern! *)
  VAR i, op : INTEGER ;
BEGIN
  FOR i := 1 TO c.len DO
    op := c.ops[i] ;
    g[n].M := op ;   (* hier gehen Marks vorw„rts. *)
    n := g[n].L[op] ;
  END ;
END MakeCycle ;

PROCEDURE Try_Curl(VAR g : NodeTab ;
                       node : INTEGER ;
                       op   : INTEGER ;
                       cyc  : INTEGER ) : BOOLEAN ;
  (* es wird getestet, ob die zus„tzlichen Knoten frei sind,
     um eine Schlinge aus der Kante "op", die von "node" kommt,
     zu machen.
  *)
  VAR no, i : INTEGER ;
BEGIN
  WITH CycTab[op, cyc] DO
    (* der CycTab-Eintrag beginnt immer mit "op".
       Wir mssen daher den zweiten zuerst nehmen.
       Es reicht dann, len-2 Knoten zu testen, da wir zwei schon kennen.
    *)
    no := node ;
    FOR i := 2 TO len-1 DO
      no := g[no].L[ops[i]] ;
      IF g[no].M <> 0 THEN
        (* Mark war nicht leer *)
        RETURN FALSE ;
      END ;
    END ;
    RETURN TRUE ;
  END
END Try_Curl ;

PROCEDURE Lay_Curl(VAR g : NodeTab ;
                       node : INTEGER ;
                       op   : INTEGER ;
                       cyc  : INTEGER ) ;
  (* es wird eine Schlinge gelegt. *)
  VAR no, i : INTEGER ;
BEGIN
  WITH CycTab[op, cyc] DO
    (* der CycTab-Eintrag beginnt immer mit "op".
       Wir mssen daher den zweiten zuerst nehmen.
       Hier gehts bis zum Ende.
    *)
    no := node ;
    FOR i := 2 TO len DO
      g[no].M := ops[i] ;
      no := g[no].L[ops[i]] ;
    END ;
  END ;
END Lay_Curl ;

PROCEDURE Rem_Curl(VAR g : NodeTab ;
                       node : INTEGER ;
                       op   : INTEGER ;
                       cyc  : INTEGER ) ;
  (* Eine Schlinge wird entfernt. *)
  VAR no, i : INTEGER ;
BEGIN
  WITH CycTab[op, cyc] DO
    no := node ;
    g[no].M := op ;     (* restauriert *)
    FOR i := 2 TO len-1 DO
      no := g[no].L[ops[i]] ;
      g[no].M := 0 ;    (* geputzt *)
    END ;
  END ;
END Rem_Curl ;

PROCEDURE HamiltonCirc2(VAR g : NodeTab) ;
  VAR
    count, calls : LONGINT ;

  (* wir laufen den Kreis ab "node" entlang und versuchen an jeder
     Kante, ob wir eine Schlinge ansetzen k”nnen.
     Wenn das geht, starten wir ab da eine Rekursion.
     Danach wird die Schlinge wieder abgebaut.
     Wenn eine Inkarnation die L„nge des Hamiltonkreises erreicht,
     hat sie offenbar einen gefunden.
  *)
  PROCEDURE try(lev, node : INTEGER) ;
    VAR op : INTEGER ; i, cyc : INTEGER ; next : INTEGER ;
  BEGIN
    (* laufe durch den Kreis. *)
    REPEAT
      op := g[node].M ;
      (* sieh nach, ob man Schlingen machen kann *)
      FOR cyc := 1 TO CperLink DO
        IF Try_Curl(g, node, op, cyc) THEN
          Lay_Curl(g, node, op, cyc) ;
          INC(calls) ;
          try(lev, node) ;    (* probiere beliebig weit *)
          Rem_Curl(g, node, op, cyc) ;
        END ;
      END ;
      INC(lev) ;
      node := g[node].L[op] ;
    UNTIL node = 1 ;
    (* bin einmal rum *)

    IF lev > Nodes THEN   (* Treffer! *)
      INC(count) ;
      FIO.WrLngInt(F, calls,0) ;
      FIO.WrStr(F, ": ") ;
      FIO.WrLngInt(F, count,0) ;
      FIO.WrStr(F, "  ") ;
      node := 1 ;
      REPEAT
        FIO.WrChar(F, CHR(ORD('0')+g[node].M)) ;
        node := g[node].L[g[node].M] ;
      UNTIL node = 1 ;
      FIO.WrLn(F) ;
    END ;
  END try ;

BEGIN
  count := 0 ;
  calls := 0 ;
  MakeCycle(g, 1, CycTab[1,1]) ;  (* der wird nun dauernd umgebaut. *)
  try(1, 1) ;
  FIO.WrLngInt(F, count,0) ;
  FIO.WrStr(F, ' Hamiltonkreise gefunden. ') ;
  FIO.WrLngInt(F, calls,0) ;
  FIO.WrStr(F, ' rekursive Aufrufe.') ;
  FIO.WrLn(F) ;
END HamiltonCirc2 ;


VAR
  N : NodeTab ;
  i,j,k : INTEGER ;
  op : INTEGER ;
  s : NameType ;

tbuf : ARRAY[1..4196+FIO.BufferOverhead] OF CHAR ;

BEGIN
  Lib.EnableBreakCheck() ;

  FIO.AssignBuffer(FIO.StandardOutput, tbuf) ;
  ResetNodes(N) ;
  BuildGraph(N) ;
  BuildCycTab(N) ;

  MakeCycle(N, 1, CycTab[1,1]) ;

  FOR i := 1 TO Nodes DO
    NumToName(i, s) ;
    IO.WrStr(s) ;
    IO.WrInt(i,5) ;
    IO.WrStr(" --> ") ;
    FOR op := 1 TO Links DO IO.WrInt(N[i].L[op],5) END ;
    IO.WrLn() ;
  END ;
  ResetMarks (N) ;
  IF Grad < 5 THEN HamiltonCircles (N) END ;
  HamiltonCircles (N) ;
END H.
