MODULE PM ;

FROM perms IMPORT NextPerm ;
IMPORT SYSTEM, IO, Lib, Str ;

(* Brute Force : finde den Namen einer gegebenen Permutation *)

PROCEDURE PermName (Order: CARDINAL ; Base, Perm : ARRAY OF CHAR) : CARDINAL ;
  VAR wrap : BOOLEAN ; Name : CARDINAL ;
BEGIN
  Name := 0 ;
  REPEAT
    INC(Name) ;
    IF Str.Compare(Base, Perm) = 0 THEN RETURN Name END ;
    NextPerm(Order, Base, wrap) ;
  UNTIL wrap ;
  (* falsche Parameter, nix gefunden *)
  RETURN 0 ;
END PermName ;

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
  Order = 5 ;
  MaxNegs = 20 ;

VAR
  s, s0, neg : ARRAY[1..Order] OF CHAR ;
  i : INTEGER ;
  wrap : BOOLEAN ;
  Name : CARDINAL ;
  NNegs : CARDINAL ;
  Negationen : ARRAY [1..MaxNegs] OF NegationsTyp ;

BEGIN
  s0 := "12345" ;
  s := s0 ;
  Name := 0 ;
  NNegs := 4 ;
  FOR i := 1 TO NNegs DO
    Negationen[i].n1 := i ;
    Negationen[i].n2 := i+1 ;
  END ;

  REPEAT
    INC(Name) ;

    (* Erzeuge alle Negationen und finde deren Namen *)
    FOR i := 1 TO NNegs DO WITH Negationen[i] DO
      IO.WrCard(Name, 4) ;
      IO.WrStr(" ") ;
      Negiere(s, n1, n2, neg) ;
      IO.WrCard(PermName(Order, s0, neg), 3) ;
    END END ;
    IO.WrLn() ;

    NextPerm(Order, s, wrap) ;
  UNTIL wrap ;
  IO.WrLn() ;
END PM.
