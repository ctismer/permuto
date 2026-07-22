(* PMtest       berechnete Permutationsnamen      kr0te, 20.10.91
   aus PM.MOD.

   Algorithmische Bestimmung des Permutationsnamens.
   Es wird eine Zahlendarstellung mit variabler Basis benutzt.
*)

MODULE PMtest ;

FROM perms IMPORT NextPerm ;
IMPORT SYSTEM, IO, Lib, Str ;

(* Brute Force : finde den Namen einer gegebenen Permutation *)

PROCEDURE PermName (Order: CARDINAL ; Orig, Perm : ARRAY OF CHAR) : CARDINAL ;
  VAR wrap : BOOLEAN ; Name : CARDINAL ;
BEGIN
  Name := 0 ;
  REPEAT
    INC(Name) ;
    IF Str.Compare(Orig, Perm) = 0 THEN RETURN Name END ;
    NextPerm(Order, Orig, wrap) ;
  UNTIL wrap ;
  (* falsche Parameter, nix gefunden *)
  RETURN 0 ;
END PermName ;

(* Vergleich: Algorithmische Version. *)

PROCEDURE PermName2 (Order: CARDINAL ; Orig, Perm : ARRAY OF CHAR) : CARDINAL ;
  (* wir nehmen an, da· Orig kleinstmîgliche Darstellung ist, also
     keine weitere Normierung nîtig. Au·erdem sind nur 10 verschiedene
     Zeichen erlaubt. SpÑter erlauben wir sowieso nur noch Ziffern.
     Erstmal ausprobieren. Dies ist ja nur ein Test.
  *)
  VAR
    Name, Base, i, p : CARDINAL ;
    chars, freqs : ARRAY[0..10] OF CHAR ;
    c : CHAR ;
BEGIN
  Name := 0 ;
  Base := 0 ;
  Lib.Fill(ADR(chars), SIZE(chars), 0) ;
  Lib.Fill(ADR(freqs), SIZE(freqs), 0) ;
  FOR i := 0 TO Str.Length(Orig)-1 DO
    c := Orig[i] ;
    p := Str.CharPos(chars, c) ;
    IF p <= Base THEN
      INC(freqs[p])
    ELSE
      p := Base ;
      INC(Base) ;
      chars[p] := c ;
      freqs[p] := '1' ;
    END ;
  END ;

  (* jetzt haben wir die Tabelle. Dies wird zukÅnftig nur einmal berechnet.
     Dies ist die dynamische Basis. Bei jedem Zeichen wird die Position
     des Zeichens gesucht und mit der aktuellen Basis kodiert. Die
     Frequenz des Zeichens wird verringert. Wird sie 0, so wird das
     Zeichen aus der Tabelle entfernt und die Basis verkleinert.
  *)

  FOR i := 0 TO Str.Length(Perm)-1 DO
    p := Str.CharPos(chars, Perm[i]) ;
    Name := Name * Base + p ;
    DEC(freqs[p]) ;
    IF freqs[p] = '0' THEN
      Str.Delete(chars, p, 1) ;
      Str.Delete(freqs, p, 1) ;
      DEC(Base) ;
    END ;
  END ;

  RETURN Name+1 ;
END PermName2 ;

(* Algorithmische Version ging nur bei der symmetrischen Gruppe richtig.
   Wenn Bindungen vorhanden sind, mu· man offenbar anders vorgehen.
   Ich rolle die Sache von hinten auf und beachte stets die eindeutige
   Zerlegbarkeit durch Modulo. *)

PROCEDURE PermName3 (Order: CARDINAL ; Orig, Perm : ARRAY OF CHAR) : CARDINAL ;
  (* wir nehmen an, da· Orig kleinstmîgliche Darstellung ist, also
     keine weitere Normierung nîtig. Au·erdem sind nur 10 verschiedene
     Zeichen erlaubt. SpÑter erlauben wir sowieso nur noch Ziffern.
     Erstmal ausprobieren. Dies ist ja nur ein Test.
  *)
  VAR
    Name, Base, Factor, i, p : CARDINAL ;
    chars, freqs : ARRAY[0..10] OF CHAR ;
    c : CHAR ;
BEGIN
  Name := 0 ;
  Base := 0 ;
  Lib.Fill(ADR(chars), SIZE(chars), 0) ;
  Lib.Fill(ADR(freqs), SIZE(freqs), 0) ;
  FOR i := 0 TO Str.Length(Orig)-1 DO
    c := Orig[i] ;
    p := Str.CharPos(chars, c) ;
    IF p <= Base THEN
      INC(freqs[p])
    ELSE
      p := Base ;
      INC(Base) ;
      chars[p] := c ;
      freqs[p] := '1' ;
    END ;
  END ;

  (* jetzt haben wir die Tabelle. Dies wird zukÅnftig nur einmal berechnet.
     Ab jetzt wird von rechts nach links kodiert. Rechnet man Modulo Anzahl
     aktueller Mîglichkeiten, erhÑlt man ein eindeutiges Ergebnis.
     Also mu· dieser Algorithmus stimmen. Wir prÅfen das dennoch nach:
  *)

  Factor := 1 ;
  FOR i := Str.Length(Perm)-1 TO 0 BY -1 DO
    p := Str.CharPos(chars, Perm[i]) ;
    Name := Name + (Factor * (Base-p-1)) ;
    Factor := Factor * Base ;
    DEC(freqs[p]) ;
    IF freqs[p] = '0' THEN
      Str.Delete(chars, p, 1) ;
      Str.Delete(freqs, p, 1) ;
      DEC(Base) ;
    END ;
  END ;

  RETURN Name+1 ;
END PermName3 ;

(* beliebiger Austausch vom PlÑtzen *)
PROCEDURE Negiere (Old : ARRAY OF CHAR ;
                    N1, N2 : CARDINAL ;
                    VAR New : ARRAY OF CHAR) ;
BEGIN
  Str.Copy (New, Old) ;
  IF (N1 > SIZE(New)) OR (N2 > SIZE(New)) THEN
    Lib.FatalError("Ortsindex au·erhalb Bereich.") ;
  END ;
  DEC(N1) ; DEC(N2) ;  (* mÅssen ab 0 indizieren *)
  New[N2] := Old[N1] ;
  New[N1] := Old[N2] ;
END Negiere ;

TYPE
  NegationsTyp = RECORD n1, n2 : CARDINAL ; END ;

CONST
  MaxNegs = 20 ;
  MaxOrder = 8 ;
VAR
  s, s0, neg : ARRAY[1..MaxOrder] OF CHAR ;
  Order : CARDINAL ;
  i : INTEGER ;
  wrap : BOOLEAN ;
  Name : CARDINAL ;
  NNegs : CARDINAL ;
  Negationen : ARRAY [1..MaxNegs] OF NegationsTyp ;

BEGIN
(* fÅr den 120er
  s0 := "12345" ;
*)
(* fÅr den "kleinen" fÅrs Telefon
  s0 := "11223" ;
*)
(* order 8, komisches Ding *)
  s0 := "11111122" ;
  s := s0 ;
  Name := 0 ;
  NNegs := 7 ;
(*
  FOR i := 1 TO NNegs DO
    Negationen[i].n1 := i ;
    Negationen[i].n2 := i+1 ;
  END ;
*)
  Negationen[1] := NegationsTyp (1,2) ;
  Negationen[2] := NegationsTyp (1,3) ;
  Negationen[3] := NegationsTyp (1,5) ;
  Negationen[4] := NegationsTyp (1,7) ;
  Negationen[5] := NegationsTyp (2,4) ;
  Negationen[6] := NegationsTyp (2,6) ;
  Negationen[7] := NegationsTyp (2,8) ;

  IF Lib.ParamCount() = 0 THEN
    IO.WrStr("Parameter = Permutationsstring") ;
    Lib.SetReturnCode(1) ;
    HALT ;
  END ;

  Lib.ParamStr(s0, 1) ;
  s := s0 ;
  Order := Str.Length(s0) ;
  NNegs := 1 ;
  Name := 0 ;
  Negationen[1] := NegationsTyp (1,2) ;
  Negationen[2] := NegationsTyp (2,3) ;
  Negationen[3] := NegationsTyp (3,4) ;
  Negationen[4] := NegationsTyp (4,5) ;

  REPEAT
    INC(Name) ;

    (* Erzeuge alle Negationen und finde deren Namen *)
    IO.WrStr(s) ; IO.WrStr(" ") ;
    FOR i := 1 TO NNegs DO WITH Negationen[i] DO
      IO.WrCard(Name, 4) ;
      IO.WrStr("==") ;
      IO.WrCard(PermName2(Order, s0, s), 3) ;
      IO.WrStr("/") ;
      IO.WrCard(PermName3(Order, s0, s), 3) ;
      IO.WrStr("  ") ;
      Negiere(s, n1, n2, neg) ;
      IO.WrCard(PermName(Order, s0, neg), 3) ;
    END END ;
    IO.WrLn() ;

    NextPerm(Order, s, wrap) ;
  UNTIL wrap ;
  IO.WrLn() ;
END PMtest.
