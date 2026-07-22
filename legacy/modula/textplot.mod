(**********************************************************
   TextPlot
   Prototype Version for very small text in Graphics. Has
   to be developed further before it will get into LIB.
   20.12.91
***********************************************************)

IMPLEMENTATION MODULE TextPlot ;

  IMPORT IO, Graph, MiniFont, Str ;
  FROM MiniFont IMPORT  First, Last, PixX, PixY, PixDX ;

  VAR p : MiniFont.Font ;

  PROCEDURE PlotChar(x, y : INTEGER ; c : CHAR ; Color : CARDINAL) ;
    VAR row, col : INTEGER ; b : CARDINAL ;bits : SET OF [0..7] ;
  BEGIN
    IF (c<CHR(First)) OR (c>CHR(Last)) THEN RETURN END ;
    b := 0 ;
    FOR row := 0 TO PixY-1 DO
      FOR col := 0 TO PixX-1 DO
        IF (b MOD 8)=0 THEN bits := p^[ORD(c)][b DIV 8] END ;
        IF (7- b MOD 8) IN bits THEN Graph.Plot(x+col, y+row, Color) END ;
        INC(b) ;
      END ;
    END ;
  END PlotChar ;

  PROCEDURE PlotCenteredStr(x, y : INTEGER ;
                               s : ARRAY OF CHAR ;
                            Color : CARDINAL) ;
    (* Plots string x-y-centered at (x,y) *)
    VAR i, len, mid : INTEGER ;
  BEGIN
    len := Str.Length(s) ;
    (* account for len*x-space of characters + len-1 space between *)
    mid := (len*(PixX+PixDX)-PixDX +1) DIV 2 ;
    x := x-mid ;
    y := y - PixY DIV 2 +1 ;  (* chars have more space at bottom *)
    FOR i := 0 TO len-1 DO
      PlotChar(x, y, s[i], Color) ;
      INC(x, PixX+PixDX) ;
    END ;
  END PlotCenteredStr ;

BEGIN
  p := MiniFont.Attach() ;

END TextPlot.



