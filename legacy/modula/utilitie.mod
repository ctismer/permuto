(**********************************************************
   Utilities
   perhaps to be extracted into a Module, when more
   For technicl reasons extracted prematurely.
***********************************************************)

IMPLEMENTATION MODULE Utilities ;

IMPORT Lib ;

  PROCEDURE SetZero(VAR obj : ARRAY OF BYTE) ;
  BEGIN
    Lib.Fill(ADR(obj), SIZE(obj), 0) ;
  END SetZero ;

END Utilities.


