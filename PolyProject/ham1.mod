(* HAM1    Hamilton-Kreise finden            kr0te, 13.11.91
*)

MODULE HAM1 ;

IMPORT IO, FIO, Str, Lib, DosUtil, Window, Graph ;

CONST
  TRACE = NOT TRUE ;

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

(* es gibt (Links Åber 2) Kreise, da Kreise aus allen Paaren aus
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

(* simpler rekursiver Ansatz *)
PROCEDURE HamiltonCircles(VAR g : NodeTab) ;
  VAR
    ops : ARRAY[0..Nodes] OF CHAR ;
    count, calls : LONGINT ;

  PROCEDURE try(lev, node : INTEGER) ;
    VAR op : INTEGER ; next : INTEGER ;
  BEGIN
    IF (node <> 1) OR (lev = 1) THEN
      FOR op := 1 TO Links DO
        next := g[node].L[op] ;
        IF g[next].M = 0 THEN
          g[next].M := node ;   (* Marks gehen hier rÅckwÑrts *)
          ops[lev-1] := CHR(ORD('0')+op) ;
          INC(calls) ;
          try(lev+1, next) ;
          g[next].M := 0 ;
        END ;
      END ;
    ELSIF (lev > Nodes) THEN (* Node 1 nur als letzter erlaubt *)
      INC(count) ;
      IO.WrLngInt(count,5) ;
      IO.WrStr("  ") ;
      IO.WrStr(ops) ;
      IO.WrLn() ;
    END ;
  END try ;

BEGIN
  count := 0 ;
  calls := 0 ;
  ops[Nodes] := 0C ;
  try(1, 1) ;
  IO.WrLngInt(count,0) ;
  IO.WrStr(' Hamiltonkreise gefunden. ') ;
  IO.WrLngInt(calls,0) ;
  IO.WrStr(' rekursive Aufrufe.') ;
  IO.WrLn() ;
END HamiltonCircles ;

TYPE
  OpColorTable = ARRAY[1..6] OF Window.Color ;

CONST OpColors = OpColorTable (
  Window.Red, Window.Green, Window.Yellow, Window.LightRed,
  Window.LightBlue, Window.White ) ;

PROCEDURE PlotOperators (VAR g : NodeTab ; x, y : CARDINAL) ;
  (* Ausgabe der Operatoren im Graphikmode *)
  VAR n, i, op : CARDINAL ;
BEGIN
  n := 1 ;
  i := 0 ;
  REPEAT
    IF y+i >= Graph.Width THEN RETURN END ;
    op := g[n].M ;
    Graph.Plot(x, y+i, ORD(OpColors[op])) ;
    INC(i,2) ;
    n := g[n].L[op] ;
  UNTIL n = 1 ;
END PlotOperators ;

(* komplizierterer Ansatz : operiere mit Maschen.
   versuche, Kanten durch Maschen zu ersetzen, bis gefunden.
*)

TYPE
  CycleType = RECORD               (* Beschreibung eines Zyklus *)
    len : INTEGER ;
    ops : ARRAY[1..6] OF INTEGER ;
  END ;

(* Tabelle, die fÅr jeden Operator (=Link) die mîglichen Kreise angibt: *)
VAR
  CycTab : ARRAY[1..Links] OF ARRAY[1..CperLink] OF CycleType ;

PROCEDURE BuildCycTab(VAR g : NodeTab) ;
  (* g mu· intakten Permutographen enthalten. *)
  (* fÅr jeden Operator (=Link) wird eine Liste der Kreise angelegt,
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
    g[n].M := op ;   (* hier gehen Marks vorwÑrts. *)
    n := g[n].L[op] ;
  END ;
END MakeCycle ;

PROCEDURE TryCycle(VAR g : NodeTab ;
                       n : INTEGER ;
                   VAR c : CycleType) : BOOLEAN ;
  (* Teste, ob ein Zyklus angelegt werden kann oder schon was besetzt ist.
   *)
  VAR i, op : INTEGER ;
BEGIN
  FOR i := 1 TO c.len DO
    IF g[n].M <> 0 THEN RETURN FALSE END ;
    op := c.ops[i] ;
    n := g[n].L[op] ;
  END ;
  RETURN TRUE ;
END TryCycle ;

PROCEDURE ClearCycle(VAR g : NodeTab ;    (* I/O *)
                         n : INTEGER ) ;      (* I *)
  (* rupft die Verbindung 'raus, egal wo lang *)
  VAR op : INTEGER ;
BEGIN
  op := g[n].M ;
  WHILE op <> 0 DO
    g[n].M := 0 ;
    n := g[n].L[op] ;
    op := g[n].M ;
  END ;
END ClearCycle ;

PROCEDURE Try_Curl(VAR g : NodeTab ;
                       node : INTEGER ;
                       op   : INTEGER ;
                       cyc  : INTEGER ) : BOOLEAN ;
  (* es wird getestet, ob die zusÑtzlichen Knoten frei sind,
     um eine Schlinge aus der Kante "op", die von "node" kommt,
     zu machen.
  *)
  VAR no, i : INTEGER ;
BEGIN
  WITH CycTab[op, cyc] DO
    (* der CycTab-Eintrag beginnt immer mit "op".
       Wir mÅssen daher den zweiten zuerst nehmen.
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
       Wir mÅssen daher den zweiten zuerst nehmen.
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

PROCEDURE HamiltonCirc2(VAR g : NodeTab ; Plot : BOOLEAN) ;
  VAR
    count, calls : LONGINT ;

  (* wir laufen den Kreis ab "node" entlang und versuchen an jeder
     Kante, ob wir eine Schlinge ansetzen kînnen.
     Wenn das geht, starten wir ab da eine Rekursion.
     Danach wird die Schlinge wieder abgebaut.
     Wenn eine Inkarnation die LÑnge des Hamiltonkreises erreicht,
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
      IF Plot THEN
        PlotOperators(g, 2*INTEGER((count-1) MOD
                         LONGINT(Graph.Width DIV 2)), 200) ;
      ELSE
        IO.WrLngInt(calls,0) ;
        IO.WrStr(": ") ;
        IO.WrLngInt(count,0) ;
        IO.WrStr("  ") ;
        node := 1 ;
        REPEAT
          IO.WrChar(CHR(ORD('0')+g[node].M)) ;
          node := g[node].L[g[node].M] ;
        UNTIL node = 1 ;
        IO.WrLn() ;
      END ;
    END ;
  END try ;

BEGIN
  count := 0 ;
  calls := 0 ;
  MakeCycle(g, 1, CycTab[1,1]) ;  (* der wird nun dauernd umgebaut. *)
  try(1, 1) ;
  IO.WrLngInt(count,0) ;
  IO.WrStr(' Hamiltonkreise gefunden. ') ;
  IO.WrLngInt(calls,0) ;
  IO.WrStr(' rekursive Aufrufe.') ;
  IO.WrLn() ;
END HamiltonCirc2 ;

PROCEDURE Trace (VAR g : NodeTab) ;
  (* Teste aktuelle Schleife *)
  VAR n, i, op : INTEGER ;
BEGIN
  n := 1 ;
  i := 0 ;
  IO.WrStr( "Trace: ") ;
  REPEAT
    op := g[n].M ;
    IF op = 0 THEN
      IO.WrStr(" Fehler in Knoten ") ;
      IO.WrInt(n,0) ;
      IO.WrLn() ;
      RETURN ;
    END ;
    IO.WrChar(CHR(ORD("0")+op)) ;
    n := g[n].L[op] ;
    INC(i) ;
  UNTIL n = 1 ;
  IO.WrStr ("  len=") ; IO.WrInt(i,0) ; IO.WrLn() ;
END Trace ;

  (* verbesserte Version des Schlingenalgorithmus.
     Die Ausgabe erfolgt lexikographisch.
     GezÑhlt werden nicht mehr Rekursionen, sondern gefundene Kreise.
     Als Nebeneffekt wird eine Tabelle mit allen Kreisen aller LÑngen
     aufgestellt.
  *)

VAR CircleCounts : ARRAY[1..Nodes] OF LONGINT ;

PROCEDURE HamiltonCirc3(VAR g : NodeTab ; Plot : BOOLEAN) ;
  VAR
    count, circles : LONGINT ;

  (* wir laufen den Kreis ab "node" entlang und versuchen an jeder
     Kante, ob wir eine Schlinge ansetzen kînnen.
     Wenn das geht, starten wir ab da eine Rekursion.
     Danach wird die Schlinge wieder abgebaut.
     Wenn eine Inkarnation die LÑnge des Hamiltonkreises erreicht,
     hat sie offenbar einen gefunden.
     Die Kreise an sich werden nicht unbedingt lexikographisch durchlaufen,
     wohl aber die Hamiltonkreise!

     Wunderbarer Algorithmus, aber offenbar ein so ungÅnstiger Einstieg,
     da· er beim 5er eewig nix findet.
  *)
  PROCEDURE try(node, length : INTEGER) ;
    VAR op : INTEGER ; i, cyc : INTEGER ; next : INTEGER ;
  BEGIN
    (* Depth first, wir wollen stets das lexikographisch kleinste haben.
       Daher wird zuerst getestet, ob ausgegeben werden mu· und dann
       lexikographisch in Rekursion gegangen.
    *)
    (*%T TRACE*) Trace (g) ; (*%E*)
    (*%T TRACE*) IF length > Nodes THEN
      IO.WrStr("length zu gro·: ") ; IO.WrInt(length,0) ;
      HALT END ;
    (*%E*)
    op := g[node].M ;
    next := g[node].L[op] ;
    IF next = 1 THEN   (* habe einen Kreis durchlaufen *)
      INC(CircleCounts[length]) ;
      INC(circles) ;
      IF length = Nodes THEN   (* Treffer! *)
        INC(count) ;
        IF Plot THEN
          PlotOperators(g, 2*INTEGER((count-1) MOD
                           LONGINT(Graph.Width DIV 2)), 200) ;
        ELSE
          IO.WrLngInt(circles,0) ;
          IO.WrStr(": ") ;
          IO.WrLngInt(count,0) ;
          IO.WrStr("  ") ;
          node := 1 ;
          REPEAT
            IO.WrChar(CHR(ORD('0')+g[node].M)) ;
            node := g[node].L[g[node].M] ;
          UNTIL node = 1 ;
          IO.WrLn() ;
        END ;
      END ;
    END ;

    (* versuche, den Kreis weiterzulaufen *)
    IF next <> 1 THEN
      try(next, length) ;
    END ;

    (* sieh nach, ob man Schlingen machen kann *)
    FOR cyc := 1 TO CperLink DO
      IF Try_Curl(g, node, op, cyc) THEN
        Lay_Curl(g, node, op, cyc) ;
        try(node, length+CycTab[op,cyc].len-2) ;
        Rem_Curl(g, node, op, cyc) ;
      END ;
    END ;

  END try ;

  VAR i : INTEGER ;
BEGIN
  count := 0 ;
  circles := 0 ;
  FOR i := 1 TO Nodes DO CircleCounts[i] := 0 END ;
  MakeCycle(g, 1, CycTab[1,1]) ;  (* der wird nun dauernd umgebaut. *)
  try(1, CycTab[1,1].len) ;
  ClearCycle(g, 1) ;
  (* mehr als ein Startkreis hat keinen Sinn. Die anderen werden von da
     aus alle erzeugt.
  *)
  IO.WrLngInt(count,0) ;
  IO.WrStr(' Hamiltonkreise gefunden. ') ;
  IO.WrLngInt(circles,0) ;
  IO.WrStr(' Kreise durch (1).') ;
  IO.WrLn() ;
END HamiltonCirc3 ;

PROCEDURE Disjunkte_6er (VAR g : NodeTab) ;
  (* zerlege Graph in disjunkte Secherkreise.
     Wir versuchen, das dann zu einem Hamiltonkreis zusammenzufÅgen.
  *)
  VAR i : INTEGER ;
BEGIN
  ResetMarks(g) ;
  FOR i := 1 TO Nodes DO
    IF g[i].M = 0 THEN
      IF NOT TryCycle(g, i, CycTab[1,1]) THEN
        IO.WrStr(" Denkfehler, keine disjunkte Zerlegung!") ;
        HALT ;
      END ;
      MakeCycle(g, i, CycTab[1,1]) ;
    END ;
  END ;
END Disjunkte_6er ;

(* das "Disjunkte_6er" brauche ich wahrscheinlich garnicht.
   Ich gehe so vor:
   Lege einen 6er. Laufe das Ding entlang, lege einen 4er sobald es geht,
   gehe an die andere Seite des 4ers und mache rekursiv weiter.
   Im Prinzip wie HamiltonCirc3, aber eben mit diesen Strukturen.
   Es wird immer der gleiche 6er benutzt, er pa·t immer wieder an den
   4er dran.
*)
PROCEDURE HamiltonCirc4(VAR g : NodeTab ; Plot : BOOLEAN) ;
  VAR
    count, circles : LONGINT ;

  PROCEDURE try(node, length : INTEGER) ;
    VAR op : INTEGER ; i, cyc : INTEGER ; next : INTEGER ;
  BEGIN
    (* Depth first, wir wollen stets das lexikographisch kleinste haben.
       Daher wird zuerst getestet, ob ausgegeben werden mu· und dann
       lexikographisch in Rekursion gegangen.
    *)
    (*%T TRACE*) Trace (g) ; (*%E*)
    (*%T TRACE*) IF length > Nodes THEN
      IO.WrStr("length zu gro·: ") ; IO.WrInt(length,0) ;
      HALT END ;
    (*%E*)
    op := g[node].M ;
    next := g[node].L[op] ;
    IF next = 1 THEN   (* habe einen Kreis durchlaufen *)
      INC(CircleCounts[length]) ;
      INC(circles) ;
      IF length = Nodes THEN   (* Treffer! *)
        INC(count) ;
        IF Plot THEN
          PlotOperators(g, 2*INTEGER((count-1) MOD
                           LONGINT(Graph.Width DIV 2)), 200) ;
        ELSE
          IO.WrLngInt(circles,0) ;
          IO.WrStr(": ") ;
          IO.WrLngInt(count,0) ;
          IO.WrStr("  ") ;
          node := 1 ;
          REPEAT
            IO.WrChar(CHR(ORD('0')+g[node].M)) ;
            node := g[node].L[g[node].M] ;
          UNTIL node = 1 ;
          IO.WrLn() ;
        END ;
      END ;
    END ;

    (* versuche, den Kreis weiterzulaufen *)
    IF next <> 1 THEN
      try(next, length) ;
    END ;

    (* sieh nach, ob man Schlingen machen kann *)
    FOR cyc := 1 TO CperLink DO
      (* versuche, einen 4er anzuhÑngen *)
      IF CycTab[op,cyc].len = 4 THEN
        IF Try_Curl(g, node, op, cyc) THEN
          Lay_Curl(g, node, op, cyc) ;
          next := g[node].L[g[node].M] ;
          (* bin auf der anderen Seite. Hier mu· ein weiterer 6er
             dranpassen, wenn Platz ist.
           *)
          IF g[next].M = 1 THEN (* es mu· einer von beiden sein *)
            IF Try_Curl(g, next, 1, 1) THEN
              Lay_Curl(g, next, 1, 1) ;
              try(next, length+6) ;
              Rem_Curl(g, next, 1, 1) ;
            END ;
          ELSIF g[next].M = 2 THEN
            IF Try_Curl(g, next, 2, 1) THEN
              Lay_Curl(g, next, 2, 1) ;
              try(next, length+6) ;
              Rem_Curl(g, next, 2, 1) ;
            END ;
          ELSE
            IO.WrStr("Theorie wackelig") ; IO.WrLn() ;
            HALT ;
          END ;
          Rem_Curl(g, node, op, cyc) ;
        END ;
      END ;
    END ;

  END try ;

  VAR i : INTEGER ;
BEGIN
  count := 0 ;
  circles := 0 ;
  FOR i := 1 TO Nodes DO CircleCounts[i] := 0 END ;
  MakeCycle(g, 1, CycTab[1,1]) ;  (* der wird nun dauernd umgebaut. *)
  try(1, CycTab[1,1].len) ;
  ClearCycle(g, 1) ;
  (* mehr als ein Startkreis hat keinen Sinn. Die anderen werden von da
     aus alle erzeugt.
  *)
  IO.WrLngInt(count,0) ;
  IO.WrStr(' Hamiltonkreise gefunden. ') ;
  IO.WrLngInt(circles,0) ;
  IO.WrStr(' Kreise durch (1).') ;
  IO.WrLn() ;
END HamiltonCirc4 ;


(*# save, call(o_a_copy=>off) *)
  PROCEDURE WriteOut(s : ARRAY OF CHAR) ;
  BEGIN FIO.WrStr(FIO.StandardOutput, s)
  END WriteOut ;
(*# restore *)


VAR
  N : NodeTab ;
  i,j,k : INTEGER ;
  op : INTEGER ;
  s : NameType ;
  par : ARRAY[0..127] OF CHAR ;

  tbuf : ARRAY[1..4096+FIO.BufferOverhead] OF CHAR ;
  Use_Graph : BOOLEAN ;

BEGIN
  Lib.ParamStr(par, 1) ;
  Str.Caps(par) ;
  Use_Graph := Str.Compare(par, 'GRAPH') = 0 ;

  IF NOT DosUtil.FileIsConOut(FIO.StandardOutput) THEN
    FIO.AssignBuffer(FIO.StandardOutput, tbuf) ;
    IO.WrStrRedirect := WriteOut ;
  END ;

  IF Use_Graph THEN
    IF NOT Graph.SetVideoMode(Graph._VRES16COLOR) THEN
      Lib.FatalError ("VGA-Karte nîtig") ;
    END ;
  END ;


  Lib.EnableBreakCheck ;
  ResetNodes(N) ;
  BuildGraph(N) ;
  BuildCycTab(N) ;

  (***)
  Disjunkte_6er(N) ;

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
  HamiltonCirc2 (N, Use_Graph) ;
  IF Use_Graph THEN
    Graph.TextMode() ;
  END ;
END HAM1.
