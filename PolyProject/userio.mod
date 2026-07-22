(**********************************************************

   User Dialog

***********************************************************)

IMPLEMENTATION MODULE UserIO ;

IMPORT IO, Str, Graph, KEY ;
FROM ScreenHandler IMPORT ClrEol, WhereX, WhereY, GotoXY ;
FROM Utilities IMPORT SetZero ;

  (* removed cursor problems by own cursor in InputStr.
     None else is used.
  *)

  PROCEDURE UserWantsToExit() : BOOLEAN ;
    VAR x, y : CARDINAL ; ch : CHAR ;
  BEGIN
    x := WhereX() ; y := WhereY() ;
    ClrEol() ;
    IO.WrStr("Do You want to exit? (Y/N)") ;
    ch := CHR(KEY.Stroke()) ;
    GotoXY(x, y) ;
    ClrEol() ;
    CASE ch OF
    | "y","Y",             (* English *)
      "j", "J",            (* Deutsch *)
      "o", "O",            (* France *)
      CHR(13) : RETURN TRUE ;
    ELSE        RETURN FALSE ;
    END ;
  END UserWantsToExit ;

  PROCEDURE EscapePressed() : BOOLEAN ;
  BEGIN
    RETURN KEY.Code = KEY.ESC ;
  END EscapePressed ;

  (* this code is leaned out from Window module and changed for our needs.
     old message from last december:
       "Oh, what a hurry, Gerhard comes in 20 min.
        Now he sits here and hopes..."
  *)
  PROCEDURE InputStr ( VAR S : ARRAY OF CHAR ;     (* the string *)
                       allowed : KEY.CharSet ;   (* what may appear.
                                                      "" means all. *)
                       exit : KEY.CodeSet        (* which keys exit *)
                     ) ;
    (* all other keys will vanish *)
  VAR
    ins     : BOOLEAN ;
    k       : CARDINAL ;
    c       : CHAR ;
    x,y,p,l : CARDINAL ;
  BEGIN
    x := WhereX() ; y := WhereY() ;
    IO.WrCharRep(" ", SIZE(S)) ;
    GotoXY(x, y) ;
    p := MAX(CARDINAL) ;
    p := 0 ;
    (* no, I start at the end  CT *)
    p := Str.Length(S) ;
    (* ins := TRUE ; (* Insert mode *)*)
    ins := FALSE ; (* no, overwrite is better here.. *)
    LOOP
      l := Str.Length(S) ;
      IF p>l THEN p := l END ;
      IO.WrStrAdj(S,0-SIZE(S)-1) ;  (* one longer, for hanging cursor *)
      GotoXY(x+p,y) ;
      IO.WrChar(CHAR(219)) ;  (* Cursor *)
      GotoXY(x+p,y) ;
      k := KEY.Stroke() ;
      IF k IN exit THEN EXIT END ;
      CASE k OF
      | ORD(' ')..ORD('~') :
                   c := CHR(k) ;
                   IF c IN allowed THEN
                     IF ins    THEN Str.Insert(S,c,p) ;
                     ELSIF p=l THEN Str.Append(S,c) ;
                     ELSE S[p] := c ;
                     END ;
                     INC(p) ;
                   END ;
      | KEY.HOME  :     p := 0 ;
      | KEY.END_  :     p := l ;
      | KEY.LEFT  :     IF p>0 THEN DEC(p) END ;
      | KEY.RIGHT :     IF p<l THEN INC(p) END ;
      | KEY.DEL   :     IF p<l THEN
                          Str.Delete(S,p,1) ;
                        END ;
      | KEY.BACKSPACE : IF p>0 THEN
                          DEC(p) ; Str.Delete(S,p,1) ;
                        END ;
      | KEY.INS       : ins := NOT ins ;         (* Toggle Ins/Ovr *)
      | KEY.RETURN_   : EXIT ;                 (* Enter *)
      END ;
      GotoXY (x, y) ;
    END ;
    GotoXY (x, y) ;
    IO.WrStrAdj(S,0-SIZE(S)-1) ;  (* last time without cursor *)
  END InputStr ;

  PROCEDURE ReadLong (min, max : LONGINT) : LONGINT ;
    (* reads a number in range. will simply be clipped into range.
       return keys are return and escape. the caller can inspect
       the code in KEY.Code to check for escape.
    *)
    VAR hold, res : LONGINT ; i : INTEGER ;
        buf : ARRAY[0..12] OF CHAR ;
        x, y : INTEGER ;
        chars : KEY.CharSet ;
        codes : KEY.CodeSet ;
        c : CHAR ;
        ok, dum : BOOLEAN ;
  BEGIN
    IF (min > max) THEN hold := min ; min := max ; max := hold END ;
    x := WhereX() ; y := WhereY() ;
    buf[0] := 0C ;

    SetZero(chars) ;
    SetZero(codes) ;
    FOR c := '0' TO '9' DO INCL(chars, c) END ;
    IF min<0 THEN INCL(chars, '-') END ;
    INCL(codes, KEY.RETURN_) ;
    INCL(codes, KEY.ESC) ;
    REPEAT
      GotoXY(x, y) ;
      InputStr(buf, chars, codes) ;
      res := Str.StrToInt(buf, 10, ok) ;
      IF res < min THEN ok := FALSE ; res := min END ;
      IF res > max THEN ok := FALSE ; res := max END ;
      Str.IntToStr(res, buf, 10, dum) ;
    UNTIL ok OR (KEY.Code = KEY.ESC) ;
    RETURN res ;
  END ReadLong ;

  PROCEDURE ReadInt (min, max : INTEGER) : INTEGER ;
  BEGIN
    RETURN INTEGER(ReadLong(LONGINT(min), LONGINT(max))) ;
  END ReadInt ;

  PROCEDURE ReadLongReal (min, max : LONGREAL ; prec : INTEGER) : LONGREAL ;
    (* reads a number in range. will simply be clipped into range.
       return keys are return and escape. the caller can inspect
       the code in KEY.Code to check for escape.
    *)
    VAR hold, res : LONGREAL ; i : INTEGER ;
        buf : ARRAY[0..30] OF CHAR ;
        x, y : INTEGER ;
        chars : KEY.CharSet ;
        codes : KEY.CodeSet ;
        c : CHAR ;
        ok, dum : BOOLEAN ;
  BEGIN
    IF (min > max) THEN hold := min ; min := max ; max := hold END ;
    x := WhereX() ; y := WhereY() ;
    buf[0] := 0C ;

    SetZero(chars) ;
    SetZero(codes) ;
    FOR c := '0' TO '9' DO INCL(chars, c) END ;
    INCL(chars, '.') ;
    IF min<0.0 THEN INCL(chars, '-') END ;
    INCL(codes, KEY.RETURN_) ;
    INCL(codes, KEY.ESC) ;
    REPEAT
      GotoXY(x, y) ;
      InputStr(buf, chars, codes) ;
      res := Str.StrToReal(buf, ok) ;
      IF res < min THEN ok := FALSE ; res := min END ;
      IF res > max THEN ok := FALSE ; res := max END ;
      Str.FixRealToStr(res, prec, buf, dum) ;
      hold := res ;
      res := Str.StrToReal(buf, dum) ;
      IF res <> hold THEN
        ok := FALSE ;         (* zuviel Stellen *)
      END ;
    UNTIL ok OR (KEY.Code = KEY.ESC) ;
    RETURN res ;
  END ReadLongReal ;

  PROCEDURE ReadReal (min, max : REAL ; prec : INTEGER) : REAL ;
  BEGIN
    RETURN REAL(ReadLongReal(LONGREAL(min), LONGREAL(max), prec)) ;
  END ReadReal ;

  PROCEDURE SelectCard(VAR a : ARRAY OF CARDINAL; len : INTEGER) : INTEGER ;
    (* selects an integer from a list. User presses space until he is
       satisfied. on return, the index is the result.
       Return value is with index origin 1.
    *)
    VAR pos : INTEGER ; x, y : INTEGER ; key : CARDINAL ;
  BEGIN
    pos := 0 ;
    x := WhereX() ; y := WhereY() ;
    REPEAT
      IO.WrInt(a[pos], 6) ;
      key := KEY.Stroke() ;
      IF key = KEY.SPACE THEN
        pos := (pos+1) MOD len ;
      END ;
      GotoXY(x, y) ;
    UNTIL (key=KEY.RETURN_) OR (key=KEY.ESC) ;
    RETURN pos+1 ;
  END SelectCard ;

END UserIO.