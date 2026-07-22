MODULE GenPerm ;

(* Erzeuge alle Permutationen des Parameterstrings. *)

IMPORT IO, Str, Lib, perms ;

VAR OrigStr, PermStr : ARRAY[0..128] OF CHAR ;
    wrap : BOOLEAN ;
    PermLen : CARDINAL ;
BEGIN
  IF Lib.ParamCount() <> 1 THEN
    IO.WrStr("GenPerm - Parameter ist der zu permutierende String.") ;
    Lib.SetReturnCode(1) ;
    HALT ;
  END ;
  Lib.ParamStr(OrigStr, 1) ;
  PermStr := OrigStr ;
  PermLen := Str.Length(PermStr) ;
  REPEAT
    IO.WrStr(PermStr) ; IO.WrLn() ;
    perms.NextPerm(PermLen, PermStr, wrap) ;
  UNTIL PermStr = OrigStr ;
END GenPerm.
