(* jetzt mit Floyd-Steinberg: Fehlerverteilung ber Fl„che *)
MODULE Kugel ;

IMPORT Graph, DosUtil, BiosIO, Str, Lib, SYSTEM ;

FROM MATHLIB IMPORT Sin, Cos, ASin, ACos, Sqrt ;
FROM Lib IMPORT RANDOM ;

CONST

  Colors = 16 ;

  MinCo = 1 ;
  MaxCo = 14 ;       (* schwarz und weiá bleiben. *)
  ColorSteps = MaxCo-MinCo+1 ;
TYPE
  ColorTable = ARRAY[MinCo..MaxCo] OF INTEGER ;

VAR Weights : ColorTable ;

CONST
  radius = 200 ;
  pi = 3.1415926585 ;
  pihalbe = pi / 2.0 ;
  Shake = 3 * 600 DIV ColorSteps ;  (* war 600 bei 3 Farben *)

VAR Driver, Mode : INTEGER ;
    c : CHAR ;
    i, x, y : INTEGER ;
    co : CARDINAL ;
    xr, yr : CARDINAL ;
    x1, x2 : INTEGER ;
    x0, y0 : INTEGER ;
    r, r2, pr, hell : LONGREAL ;
    coval : INTEGER ;

(* Floyd-Steinberg :
   . . a b . . . . . .    gemerkte Fehler
   . . c * . . . . . .    -> Schreibrichtung

   Zum Farbwert von * werden die Fehler von a, b und c addiert.
   Faktoren:  2/8 * f(a) + 3/8 * f(b) + 3/8 * f(c)  .

Das Tolle daran ist, daá so der gesamte Fehler verteilt wird, denn jedes
Pixel ist genau einmal a, b oder c.
Algorithmus:
Merke die Fehler einer Zeile in einem Puffer.
Schreibe die neuen Fehler um eins verz”gert zurck.

Trick: um die Kugelsymmetrie nutzen zu k”nnen, lasse die Schleifen alle
um eins zu frh beginnen, damit das Fehlerarray gut vorbesetzt wird.
Dadurch sieht man keine N„hte!

*)

VAR F_S : ARRAY[-10..1024] OF INTEGER ;
  F_Hold : INTEGER ;

(* Dither-Version: *)

  DitBit : CARDINAL ;

TYPE DitherType = ARRAY[0..8] OF BITSET ;

CONST d0 =      {} ;
      d1 =      {0, 10} ;
      d2 = d1 + {2,  8} ;
      d3 = d2 + {5, 15} ;
      d4 = d3 + {7, 13} ;
      d5 = d4 + {3,  9} ;
      d6 = d5 + {1, 11} ;
      d7 = d6 + {6, 12} ;
      d8 = d7 + {4, 14} ;

CONST Dither = DitherType (d0, d1, d2, d3, d4, d5, d6, d7, d8) ;
(*

o ù ù ù   * ù o ù   * ù * ù   * ù * ù   * ù * o   * o * *   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù o ù ù   ù * ù o   ù * ù *   ù * ù *   ù * o *   o * * *
ù ù o ù   o ù * ù   * ù * ù   * ù * ù   * o * ù   * * * o   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù ù ù o   ù o ù *   ù * ù *   ù * ù *   o * ù *   * * o *

*)

LABEL
  outtahere ;

VAR Dith : BOOLEAN ;

PROCEDURE SetRgb (Color: CARDINAL ; r, g, b : CARDINAL) ;
BEGIN
  SYSTEM.Eval(Graph.RemapPalette
    (Color, LONGCARD(r + g << 8) + LONGCARD(b) << 16 )) ;
END SetRgb ;

VAR s : ARRAY[0..20] OF CHAR ;
    arg : LONGREAL ;
BEGIN
  Dith := TRUE ;
  FOR i := 1 TO Lib.ParamCount() DO
    Lib.ParamStr(s, i) ;
    Str.Caps(s) ;
    IF Str.Compare(s, "FLOYD") = 0 THEN Dith := FALSE END ;
  END ;
  IF NOT Graph.SetVideoMode(Graph._VRES16COLOR) THEN
    Lib.FatalError ("VGA-Karte n”tig") ;
  END ;
(*  Graph.GraphMode() ; *)

  FOR co := MinCo TO MaxCo DO
    i := co - MinCo ;
    Weights [co] := 10000 DIV ColorSteps * (i) (*+ 5000 DIV ColorSteps*) ;
(*
    SetRgb(co, 63-co, 3*co -1, 4*co -1) ;
*)
    SetRgb(co, 22 + 31*i DIV 10 , 35*i DIV 10 , 3+38*i DIV 10) ;
  END ;
  x0 := Graph.Width DIV 2 ;
  y0 := Graph.Depth DIV 2 ;
  r := LONGREAL(radius) ; r2 := r*r ;
  Lib.Fill(ADR(F_S), SIZE(F_S), 0) ;
  FOR y := -2 TO radius DO
    x1 := INTEGER(Sqrt(r2-LONGREAL(y)*LONGREAL(y))) ;
    coval := 0 ;
    F_Hold := 0 ;

(*  FOR x := x1 TO y-2 BY -1 DO *)
(* rckw„rts ist schlecht! gehe von Hell nach dunkel.
   jedoch wird der Rand nicht sehr sauber.
*)

    FOR x := y-2 TO x1 DO
      pr := Sqrt (LONGREAL(x)*LONGREAL(x) + LONGREAL(y)*LONGREAL(y)) ;
      arg := pr / r ;
      (* Bibliotheksfehler bei ACos(1.0) *)
      IF arg = 1.0 THEN hell := 0.0 ELSE
        hell := ACos (arg) / pihalbe ;
      END ;
(* Floyd-Steinberg-Version : Erweiterung meiner Sache *)
      coval := 3 * F_S[x] + 2 * F_S[x-1] + 3 * F_Hold ;
(* DIV 8 schon drin *)

      IF Dith THEN
        coval := INTEGER(10000.0 * hell) ;
        DitBit := (CARDINAL(x) MOD 4) * 4 + CARDINAL(y) MOD 4 ;
        co := MinCo ;
        WHILE (co < MaxCo) AND (coval >= Weights[co+1]) DO
          INC(co) ;
        END ;

        IF co < MaxCo THEN
          IF DitBit IN Dither[(coval-Weights[co])
                              DIV ((Weights[co+1]-Weights[co]) DIV 8)] THEN
            INC(co)
          END ;
        END ;

        F_S[x-1] := F_Hold ;
        F_Hold := coval DIV 8 ;

      ELSE
        INC(coval, INTEGER(10000.0 * hell) -Shake+INTEGER(RANDOM(2*Shake)) ) ;
(* alt:
        IF coval >= 9500 THEN
          DEC(coval, 9500) ;    (* weniger als 10000, damit weiáer Fleck *)
          co := COLOR3 ;
        ELSIF coval >= 5500 THEN
          DEC(coval, 5500) ;
          co := COLOR2 ;
        ELSIF coval >= 3000 THEN
          DEC(coval, 3000) ;
          co := COLOR1 ;
        ELSE
          DEC(coval, 0) ;
          co := COLOR0 ;
        END ;
neu:  *)
        co := MinCo ;
        WHILE (co < MaxCo) AND (coval >= Weights[co+1]) DO
          INC(co) ;
        END ;

        DEC(coval, Weights[co]) ;

        F_S[x-1] := F_Hold ;
        F_Hold := coval DIV 8 ;

    END ;

      IF x >= y THEN
        Graph.Plot (x0-x, y0-y, co) ;
        Graph.Plot (x0+x, y0-y, co) ;
        Graph.Plot (x0-x, y0+y, co) ;
        Graph.Plot (x0+x, y0+y, co) ;
        Graph.Plot (x0-y, y0-x, co) ;
        Graph.Plot (x0+y, y0-x, co) ;
        Graph.Plot (x0-y, y0+x, co) ;
        Graph.Plot (x0+y, y0+x, co) ;
      END ;
    END ;
    IF BiosIO.KeyPressed() THEN GOTO outtahere END ;
  END ;
  Graph.OutText ("Fertig.") ;
outtahere:
  c := BiosIO.RdKey() ;
  IF c <> CHR(27) THEN   (* l”sche nicht, wenn ESC *)
    Graph.TextMode () ;
  END ;
END Kugel.

(* Dither „hnlich Windows 3.0 Setup:

o ù ù ù   * ù o ù   * ù * ù   * ù * ù   * ù * o   * o * *   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù o ù ù   ù * ù o   ù * ù *   ù * ù *   ù * o *   o * * *
ù ù o ù   o ù * ù   * ù * ù   * ù * ù   * o * ù   * * * o   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù ù ù o   ù o ù *   ù * ù *   ù * ù *   o * ù *   * * o *


o ù ù ù   * ù o ù   * ù * ù   * ù * ù   * ù * o   * o * *   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù o ù ù   ù * ù o   ù * ù *   ù * ù *   ù * o *   o * * *
ù ù o ù   o ù * ù   * ù * ù   * ù * ù   * o * ù   * * * o   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù ù ù o   ù o ù *   ù * ù *   ù * ù *   o * ù *   * * o *
o ù ù ù   * ù o ù   * ù * ù   * ù * ù   * ù * o   * o * *   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù o ù ù   ù * ù o   ù * ù *   ù * ù *   ù * o *   o * * *
ù ù o ù   o ù * ù   * ù * ù   * ù * ù   * o * ù   * * * o   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù ù ù o   ù o ù *   ù * ù *   ù * ù *   o * ù *   * * o *
o ù ù ù   * ù o ù   * ù * ù   * ù * ù   * ù * o   * o * *   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù o ù ù   ù * ù o   ù * ù *   ù * ù *   ù * o *   o * * *
ù ù o ù   o ù * ù   * ù * ù   * ù * ù   * o * ù   * * * o   * * * *   * * * *
ù ù ù ù   ù ù ù ù   ù ù ù o   ù o ù *   ù * ù *   ù * ù *   o * ù *   * * o *

*)