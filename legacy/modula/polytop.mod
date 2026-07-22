(*   Polytop
     19.09.95
     enhanced PS-Output
     file load and save

     ReRenamed to Polytop
*)

(*   SimOne
     Salzburg Simulation
     Renamed PolyTop for major changes
     and a good friend of Horst

29.07.92 Slight enhancements: Skipping intro by keystroke.
         Allow multiple sources. Not the whole suggestion of Yee-Wei,
         but more than nothing.

11.07.92 Introduced Clear graph after recommendation from Yee-Wei.
         Forbid transmission to broken node.
         Repeat function temporarily does two steps before inserting the
         new node. This is for the lack of packet storage in the nodes.
         Will rewrite this, when multiple packets per node are possible.

05.07.92 Broke it down into small pieces. Redesign of the parts
         should be much easier now. And, I can build in the
         Iridium simulation without problems.
         It's 2 a clock in the morning of the presentation.
         But I think, I can make it...

03.07.92 Extraction of several Modules, to make changes easier.
*)
(*******************************************************************

     POLYTOP

     A Program to touch Polytopes and Permutographs.

     Copyright 1990,91,92 by Christian Tismer.

     This program contains ideas that are strongly related to
     the patents of Gerhard G. Thomas. Therefore, the source
     code of this program is to be considered as highly confidential.
     Distribution of the executable file is possible after consulting
     Mr. Tismer or Mr. Thomas.

     This coding is a part of the Permutographics project.
     Permutographics will buy the copyright after foundation.

********************************************************************)

(* 19.02.92: Subpermutographs, SPA, Parsum *)
(* 22.01.92: Extended Postscript: Color, Number, Name *)
(* 20.12.91: Last but not least: Permutographs are now available! *)
(* 20.12.91: a bit of windowing. *)
(* 20.12.91: much easier and faster, to clear with Graph.Rectangle *)
(* 20.12.91: created very small font for permutation numbers. *)
(* 17.12.91: absolutely no more REAL necessary. 11k code saved *)
(* 16.12.91: removed indirect nodenumbers. Now direct, from 1 *)
(* 16.12.91: Try to move to Integer-Math *)
(* 16.12.91: noch ein Alg: Rubber mit Zusatz des l„ngsten *)

(* 28.11.91: weiterer Algorithmus: Rubber mit skalierter Kraft *)

(* 08.02.91: Postscript-Ausgabe eingebaut.
             Wiederbelebung der Ribbonversion.
             Man arbeitet nun zuerst mit dem Rubberalgorithmus und
             schaltet dann auf den Ribbonalgorithmus um.
             Der zieht in Richtung der l„ngsten Strippe. *)
(* 30.11.90: Mehr Kanten. Korrektur gewichtet nach Anz. Links *)
(* 07.11.90: Mehr Knoten *)
(* 30.09.90: Versuch: Jetzt wird nicht mehr in die Summe der F„den gezogen,
             sondern in die Summe der Richtungen. Also ist die Kraft
             von den L„ngen unabh„ngig. Vermutlich strebt das zu
             gleichm„áigen Winkeln und damit zu gleichen L„ngen.
             Schade, funktioniert nicht.
*)
(* 29.09.90: Verwendung von 2 Bildern, wenn m”glich. *)
(* Polytop    -- ganz schnelle Implementierung.       kr0te, 24.09.90
   Es werden nur einfache Striche gemalt.
   Hier geht's nur um die Demonstration des Algorithmus.
   Dreidimensionale Knoten werden verbunden und irgendwie in den
   Raum geworfen. Die Verbindungen werden auf den Schirm projiziert.
   Dann werden die Knoten um einen Bruchteil in Richtung der Summe
   der Verbindungsvectoren gezogen. Danach werden alle Vectoren
   wieder hochskaliert, damit das Bild nicht zusammenf„llt.
   Dies wird iteriert.
*)

MODULE Polytop ;

IMPORT Graph, Str, Lib, SYSTEM, IO, FIO, Window ;

IMPORT DosUtil, Lib1, MacFns, KEY ;

FROM Lib IMPORT RANDOM ;
FROM Storage IMPORT ALLOCATE, DEALLOCATE, Available ;

FROM ScreenHandler IMPORT SetupGraph2, CloseGraph, GotoXY, WhereX, WhereY,
                          ClrEol ;

FROM Utilities IMPORT SetZero, nl ;

FROM UserIO IMPORT InputStr, UserWantsToExit, ReadInt, EscapePressed,
                   SelectCard ;

FROM TextPlot IMPORT PlotCenteredStr ;

FROM PM IMPORT NewPermutograph, EdPermuto, Collapse, Uncollapse ;

FROM NodeMgr IMPORT MaxNodesTot, MaxNodes, MaxLinks, MaxDimen, PermStr,
                    Dimensions, Nodes, nnodes, lastnode,
                    PackNodes, NodePtr, LinkArray,
                    ResetNodes, ReadNodes,
                    NodeTable, LineStatus,
                    LimitCheck,
                    CompareLinkList, SwapLinkList,
                    MoveNode, ResetNodes, PackNodes,
                    ReadNodes, SavePicture,
                    LoadPoly, SavePoly ;

IMPORT IntVector ;

IMPORT MiniFont ;

IMPORT PmProgs ;

IMPORT PmDisp ;

IMPORT PCalc ;     (* Polytope Calculations *)

IMPORT Iri ;       (* new prototype bunch *)

CONST DEBUG = NOT TRUE ;

CONST Version    = 1.4 ;
      VersionStr = "1.4" ;

(*%T DEBUG *)
(* geht leider nicht.
   er erzeugt ein .DBD, aber tr„gt nicht ins .EXE ein,
   daá ein Debug da ist. Also immer im
   Project-File machen.
   # debug(vid => full, public => on) *)
(*%E*)


CONST GraphMode ::= SetupGraph2 ;
      TextMode ::= CloseGraph ;
      (* do not use Routines from graph directly, because Screenhandler
         manages the switch between the Graph - and Window-Module *)



(*************************************************************

   Main Program

*************************************************************)

VAR
  Active, Visual : CARDINAL ;
  MaxPage : CARDINAL ;

PROCEDURE DisplayPicture(namemode : CARDINAL ; withstep : BOOLEAN ;
                         select : PmProgs.ProgramType) ;
  (* caution: swaps screen pages.
     screen is built hidden and then shown.
     after call, active=display. *)
  VAR page, dum : CARDINAL ;
BEGIN
  IF MaxPage = 0 THEN
    (* wipe old picture *)
    PmDisp.WipeOldPicture() ;
    (* draw new picture *)
    PmDisp.DrawEdges (Nodes, namemode, select) ;
    PmDisp.DrawNodes (Nodes, namemode, withstep, select) ;
  ELSE
    (* wipe old picture *)
    Active := MaxPage - Active ;
    dum := Graph.SetActivePage (Active) ;
    Visual := MaxPage - Active ;
    dum := Graph.SetVisualPage (Visual) ;
    PmDisp.WipeOldPicture() ;
    (* draw new picture *)
    PmDisp.DrawEdges (Nodes, namemode, select) ;
    PmDisp.DrawNodes (Nodes, namemode, withstep, select) ;
    Visual := Active ;
    dum := Graph.SetVisualPage (Visual) ;
  END ;
END DisplayPicture ;


PROCEDURE SetupPolytope(s : ARRAY OF CHAR) ;
  VAR
    i, j : INTEGER ;
    ch: CHAR ;
BEGIN
  ReadNodes (s) ;
  IO.WrCard (nnodes, 0) ;
  IO.WrStr( " nodes found." + nl) ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IO.WrStr("Node ") ; IO.WrCard(num,0) ;
    IO.WrStr(" --> ") ;
    FOR j := 1 TO nlink DO
      IO.WrChar(" ") ; IO.WrCard(links[j],0) ;
    END ;
    IO.WrLn() ;
  END END ;

  Lib.RANDOMIZE() ;

  (* leave the nodes somewhere in the wood *)
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IntVector.RandomVector (pos, IntVector.Norm) ;
  END END ;

  (* colors simply derived from nodenumbers: *)
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IF nnodes <= 24 THEN
      color := 1 + (num-1) DIV 6 ;
    ELSE
      color := 1 + (num-1) DIV 24 ;    (* awkward *)
    END ;
  END END ;

  IO.WrStr("--- press any key ---") ;

  ch := CHR(KEY.Stroke()) ;
END SetupPolytope ;



CONST
  NameCases  = 4 ;
  NameIsDisplay = 3 ;
  (* 0=none 1=node# 2=perm 3=display *)

VAR s : ARRAY[0..20] OF CHAR ;

  i, j, k : INTEGER ;

  ch : CHAR ;

  Config : Graph.VideoConfig ;
  ScreenPages : CARDINAL ;    (* do I use 1 oder 2 Pages? *)
  PagesToPrint: CARDINAL ;

  Algorithm : PCalc.AlgType ;

  Changed : BOOLEAN ;   (* do I have to show something? *)
  Spinning : BOOLEAN ;
  Running : BOOLEAN ;
  Calculating : BOOLEAN ;
  NameMode : CARDINAL ;
  ProgramMode   : BOOLEAN ;
  ProgramSelect : PmProgs.ProgramType ;

  Iteration : LONGCARD ;

  Permuto : BOOLEAN ;

  Iridium : BOOLEAN ;

  HurryUp : BOOLEAN ;

  dum  : BOOLEAN ;
  flag : BOOLEAN ;
  node, node1, node2, repeat, link : CARDINAL ;

PROCEDURE StandardProg() ;
BEGIN
  GotoXY(1, PmDisp.MenuLine_2) ;
  IO.WrStr("Nodes available = ") ;
  IO.WrCard(MaxNodes, 0) ;
  Lib.Delay(1000) ;
  LOOP
    (* Calculate new Positions *)

    PCalc.Backup() ;

    IF Calculating THEN
      (* the hopefully contracting mapping ... *)
      PCalc.Contract(Algorithm) ;

      (* now let's squeeze it a bit more roundly *)
      PCalc.Squeeze() ;

  (* punishing will only be done for known stable algorithms that are not
     harmed by punishing.
     at this time, only Rubber is really stable.
     we punish for the use of high dimensions.
  *)
      IF Algorithm = PCalc.a_Rubber THEN
        PCalc.Punish() ;
      END ;
    END ;  (* IF Calculating *)

    (* a little rotation, just for fun *)
    IF Spinning AND (NOT HurryUp OR NOT Calculating)
    AND (Dimensions >= 3) THEN
      PCalc.Spin() ;
    END ;

    PCalc.Normalize() ;   (* move into center and grow to maximum size *)

    (* if this runs the first time, set "old" to the cleaned "pos" *)
    IF Iteration = 0 THEN
      PCalc.Backup() ;    (* copy pos into old *)
    END ;

    (* at some time show status and see, if dimension can be reduced *)
    IF Iteration MOD 25 = 0 THEN Changed := TRUE END ;

    (* Display Picture *)
    IF Changed OR NOT HurryUp THEN
      DisplayPicture(NameMode, ProgramMode, ProgramSelect) ;
    END ;

    IF Changed THEN PagesToPrint := ScreenPages END ;

    IF Changed THEN
      (* see if we can remove a dimension. The idea is:
         find the abs max of each coordinate.
         if the highest coordinate's max is much less than
         the first coordinate's max, it can be removed.
         this is the case, because we punished the graph
         for the use of high dimensions, and it will tend
         to leave them.
      *)
      Changed := FALSE ;

      WHILE PCalc.CanShrink() DO
        (* remove this dimension *)
        DEC(Dimensions) ;
        IntVector.SetDimensions(Dimensions) ;
        Changed := TRUE ;
      END ;
    END ;

    (* print text and frame into the visual page. *)
    IF PagesToPrint > 0 THEN
      (* it seems to be a problem with some BIOSes if you try to
         write an invisual page. Therefore, the texts are always
         output onto the shown page. This seems to be fast enough,
         for there are only slight updates.
         I will rewrite the Text IO with graphic primitives to
         overcome this problem. CT 16.12.91
      *)

      DEC(PagesToPrint) ;

      (* this comes first, to print it before the beam is there *)
      GotoXY(1, PmDisp.MenuLine_2) ;
      IO.WrStr(" iter=") ;
      IF Iteration <> 0 THEN
        IO.WrLngCard(Iteration+LONGCARD(PagesToPrint)-1,0) ;
      ELSE
        IO.WrCard(0,0) ;
      END ;
      (* guess why this is necessary... *)
      IO.WrStr(" dim=") ;
      IO.WrCard(Dimensions, 0) ;
      IO.WrStr(" nodes=") ;
      IO.WrCard(nnodes, 0) ;
      IO.WrStr("  A=") ;
      IO.WrStr(PCalc.AlgNames[Algorithm]) ;
      IO.WrStr("    ") ;

      PmDisp.DrawPicFrame() ;

      GotoXY(1, PmDisp.MenuLine_1) ;
      IO.WrStr("(A)lgo  (C)alc ") ;
      IF Calculating THEN IO.WrStr("T")
                     ELSE IO.WrStr("F") ;
      END ;
      IO.WrStr("  (R)un ") ;
      IF Running THEN IO.WrStr("T")
                    ELSE IO.WrStr("F") ;
      END ;
      IO.WrStr("  (H)urry ") ;
      IF HurryUp    THEN IO.WrStr("T")
                    ELSE IO.WrStr("F") ;
      END ;
      IO.WrStr("  (F)ile  (S)pin ") ;
      IF Spinning THEN IO.WrStr("T")
                  ELSE IO.WrStr("F") ;
      END ;

      IO.WrStr("  (N)ame  (P)rog") ;

      IF Permuto THEN
        IO.WrStr("  (E)dit ") ;
      END ;


      IF Permuto THEN EdPermuto(FALSE) END ;  (* display *)

    END ;

    INC(Iteration) ;

    (* program iteration *)
       (* this should appear after display, but before Menu, to
          show the initial state before starting *)
    IF ProgramMode THEN
      CASE ProgramSelect OF
      | PmProgs.P_SPA    : ProgramMode := PmProgs.ShortestPath() ;
      | PmProgs.P_PARSUM : ProgramMode := PmProgs.ParSum() ;
(*      | P_SPTA   : ProgramMode := LocalShortestPath() ; *)
      END ;
      IF NOT ProgramMode THEN
        ProgramSelect := PmProgs.P_Idle ;
      END ;
    END ;

    (* keyboard control *)
    IF NOT Running OR KEY.Pressed() THEN
      GotoXY(1, PmDisp.MenuLine_2) ;
      ch := CHR(KEY.Stroke()) ;
      CASE ch OF
      | "c", "C" :    (* toggle continuous calculation *)
        Calculating := NOT Calculating ;
      | "r", "R" :    (* toggle continuous running *)
        Running := NOT Running ;
      | "s", "S" :    (* toggle spinning *)
        Spinning := NOT Spinning ;
      | "n", "N" :    (* toggle naming of nodes *)
        REPEAT
          NameMode := (NameMode+1) MOD NameCases ;
        UNTIL Permuto OR (NameMode # 2) ;        (* have no perm strings *)
      | CHR(27)  : IF UserWantsToExit() THEN EXIT END ;
      | "a", "A" :    (* toggle calculation mode *)
        Algorithm := PCalc.AlgType((ORD(Algorithm)+1) MOD
                                    (1+ORD(MAX(PCalc.AlgType)))) ;
        (* next Algorithm *)
      | "f", "F" :    (* File menu *)
        GotoXY(1, PmDisp.MenuLine_1) ;
        ClrEol() ;
        IO.WrStr("(Q)uit  (O)utput  (L)oad  (S)ave") ;
        GotoXY(1, PmDisp.MenuLine_2) ;
        ch := CHR(KEY.Stroke()) ;
        CASE ch OF
        | CHR(27), "q", "Q" : IF UserWantsToExit() THEN EXIT END ;
        | "o", "O" :    (* print postscript to file *)
          TextMode() ;
          SavePicture() ;
          GraphMode() ;
        | "l", "L" :    (* load ply file *)
          TextMode() ;
          LoadPoly(Permuto) ;
          GraphMode() ;
        | "s", "S" :    (* save ply file *)
          TextMode() ;
          SavePoly(Permuto) ;
          GraphMode() ;
        END ;
        ch := 0C ;
      | "h", "H" :    (* Hurry up, display seldom *)
        HurryUp := NOT HurryUp ;

      | "p", "P" :    (* Program menu *)
        (* need names here *)
        DisplayPicture(1, FALSE, ProgramSelect) ;
        DisplayPicture(1, FALSE, ProgramSelect) ;   (* both, easy. *)
        GotoXY(1, PmDisp.MenuLine_1) ;
        ClrEol() ;
        IO.WrStr("Kill/Repair (N)ode / (L)ine   run (S)PA  SP(T)A  (P)ARSUM") ;
        GotoXY(1, PmDisp.MenuLine_2) ;
        ClrEol() ;
        ch := CHR(KEY.Stroke()) ;
        CASE ch OF
        | "n", "N" :
            IO.WrStr(' Node=') ;
            node1 := ReadInt(1, nnodes) ;
            IF NOT EscapePressed() THEN
              WITH Nodes[node1]^ DO state.dead := NOT state.dead END ;
            END ;
        | "l", "L" :
            IO.WrStr(' Node 1=') ; node1 := ReadInt(1, nnodes) ;
            WITH Nodes[node1]^ DO
              IF (NOT EscapePressed()) AND (nlink > 0) THEN
                IO.WrStr('   select Node 2:') ;
                link := SelectCard(links, nlink) ;
                IF (NOT EscapePressed()) THEN
                  state.broken := state.broken / {link} ;
                  node2 := links[link] ;
                  WITH Nodes[node2]^ DO
                    FOR link := 1 TO nlink DO
                      IF links[link]=node1 THEN
                        state.broken := state.broken / {link} ;
                      END ;
                    END ;
                  END ;
                END ;
              END ;
            END ;

        | "c", "C" :   (* Collapse *)
            IO.WrStr(' Collapse Node=') ; node1 := ReadInt(1, nnodes) ;
            WITH Nodes[node1]^ DO
              IF (NOT EscapePressed()) AND (nlink > 0) THEN
                IO.WrStr('   onto Node :') ;
                node2 := links[SelectCard(links, nlink)] ;
                Collapse(node1, node2) ;
              END ;
            END ;

        | "u", "U" :   (* Uncollapse *)
            IO.WrStr(' Uncollapse Node=') ; node1 := ReadInt(1, nnodes) ;
            WITH Nodes[node1]^ DO
              IF (NOT EscapePressed()) THEN
                Uncollapse(node1) ;
              END ;
            END ;

        | "s", "S" :    (* shortest path, very quickly hacked *)
          GotoXY(1, PmDisp.MenuLine_2) ;
          ClrEol() ;
          IO.WrStr(' StartNode=') ;
          node1 := ReadInt(1, nnodes) ;
          IF NOT EscapePressed() THEN
            PmProgs.InitSPA(node1) ;
            ProgramMode   := TRUE ;
            ProgramSelect := PmProgs.P_SPA ;
            NameMode      := NameIsDisplay ;
          END ;

        | "t", "T" :    (* SPTA *)
          GotoXY(1, PmDisp.MenuLine_2) ;
          ClrEol() ;
          IO.WrStr("sorry, SPTA not yet available") ;
          REPEAT UNTIL KEY.Pressed() ;

        | "p", "P" :    (* PARSUM *)
          IF PmProgs.InitParSum() THEN
            ProgramMode   := TRUE ;
            ProgramSelect := PmProgs.P_PARSUM ;
            NameMode      := NameIsDisplay ;
          ELSE
            GotoXY(1, PmDisp.MenuLine_2) ;
            ClrEol() ;
            IO.WrStr("Must run SPA before PARSUM") ;
          END ;
          ch := CHR(KEY.Stroke()) ;
          ClrEol ;

        END ;

        ch := 0C ;
      END ;

      IF Permuto THEN
        CASE ch OF
        | "e", "E" : EdPermuto(TRUE) ;
                     Iteration := 0 ;
        | "m", "M" : (* mask for general collapse, a trial *)
                     (*EdCollapseMask() ;*)
                     Iteration := 0 ;
        END ;  (* case *)

      END ;

      Changed := TRUE ;   (* redraw after any alteration *)
    END ;

  END ;
END StandardProg ;

(* Introduction of a Keyboard-Buffer *)
VAR
  keybuf : ARRAY [0..255] OF CARDINAL ;
  keycount, keybeg, keyend : CARDINAL ;   (* pointers for Keystrokes *)
  keycode : CARDINAL ;

PROCEDURE StoreKey(key : CARDINAL) ;
  (* stores key only if space available. *)
BEGIN
  IF keycount < 256 THEN
    keybuf[keyend] := key ;
    keyend := (keyend+1) MOD 256 ;
    INC(keycount) ;
  END ;
END StoreKey ;

PROCEDURE GetKey() : CARDINAL ;
  (* takes key from buffer, or from keyboard if buffer empty *)
  VAR
    k : CARDINAL ;
BEGIN
  IF keycount > 0 THEN
    k := keybuf[keybeg] ;
    keybeg := (keybeg+1) MOD 256 ;
    DEC(keycount) ;
  ELSE
    k := KEY.Stroke() ;
  END ;
  RETURN k ;
END GetKey ;

PROCEDURE ClearBuf() ;
  VAR
    k : CARDINAL ;
BEGIN
  keycount := 0 ;
  keybeg := 0 ;
  keyend := 0 ;
END ClearBuf ;

PROCEDURE KeyAvail() : BOOLEAN ;
BEGIN
  RETURN keycount > 0 ;
END KeyAvail ;

BEGIN
  Lib.EnableBreakCheck() ;
  FOR i := 1 TO MaxNodesTot DO
    IF Available(SIZE(Nodes[i]^)) THEN
      NEW(Nodes[i]) ;
      Lib.Fill(ADR(Nodes[i]^), SIZE(Nodes[i]^), 0) ;
      MaxNodes := i ;
    END ;
  END ;

  Dimensions := MaxDimen ;
  IntVector.SetDimensions(Dimensions) ;
  Iteration := 0 ;

  Lib.ParamStr(s, 1) ;
  Str.Caps(s) ;
  IF s[0] = "" THEN
    IO.WrStr(
"PolyTop V" + VersionStr +
"        (C) Christian Tismer, Gerhard G. Thomas 1992-95" + nl +
nl +
"PolyTop has one parameter: Either a filename or /PG or /I" + nl +
nl +
"The file must contain pairs of node numbers." + nl +
"That is exactly the description of all edges." + nl +
nl +
"With parameter /PG, the PermutoGraphic mode is invoked." + nl +
"Here you can dynamically build Permutographs and watch their" + nl +
"behavior." + nl +
nl +
"The new feature /I enters Iridium mode. Very special stuff!" + nl +
nl +
"This programme is still prototype state, so I apologize for the too" + nl +
"short description." + nl +
nl +
"Christian Tismer, July 1992" + nl) ;
    HALT ;
  END ;

  ResetNodes() ;

  Permuto := FALSE ;
  Iridium := FALSE ;

  IF s[0] # "/" THEN
    SetupPolytope(s) ;    (* we are in ordinary polytope mode *)
  ELSIF Str.Compare(s, "/I") = 0 THEN
    Iridium := TRUE ;
  ELSE
    (* now we are in Permutographic mode *)
    Permuto := TRUE ;
    NewPermutograph(TRUE) ;  (* start with a default *)
  END ;

  GraphMode() ;
  Active := 0 ;
  Visual := 0 ;
  Graph.GetVideoConfig (Config) ;
  MaxPage := Config.numvideopages-1 ;

  (*%T DEBUG*) MaxPage := 0 ; (*%E*)    (* easier to debug *)

  ScreenPages := ORD(MaxPage>0) +1 ;  (* 1 or 2 *)

  Algorithm := PCalc.a_Rubber ;

  Changed := TRUE ;
  Running := FALSE ;
  Calculating := TRUE ;
  Spinning := TRUE ;
  NameMode := 0 ;
  HurryUp := FALSE ;
  ProgramMode := FALSE ;
  ProgramSelect := PmProgs.P_Idle ;

  (* try to start with page 0 first, to get a picture with that
    clumsy editor. *)

  Active := MaxPage - Graph.SetActivePage (MaxPage - Active) ;
  Visual := MaxPage - Graph.SetVisualPage (MaxPage - Visual) ;

  IF NOT Iridium THEN
    StandardProg()
  ELSE
    (* actual problem is Iridium, so I hacked it in at this point.
       now matter how it look, only that it works.
    *)
    (* first, build the picture.
       we do it incrementally, so it is handled easily by the
       ribbon algorithm to get a nice picture. *)
    ResetNodes() ;
    PmDisp.DrawPicFrame() ;
    DisplayPicture(NameMode, ProgramMode, ProgramSelect) ;
    PmDisp.DrawPicFrame() ;
    Dimensions := 2 ;
    IntVector.SetDimensions(Dimensions) ;

    FOR i := 1 TO 2 DO
      GotoXY(1, PmDisp.MenuLine_1) ;
      IO.WrStr ("SIMONE V" + VersionStr +
                "   press any key to skip the intro and wait a bit...") ;
      IO.WrLn() ;
      DisplayPicture(NameMode, ProgramMode, ProgramSelect) ;
    END ;

    WHILE NOT Iri.Built() DO
      Iri.NewNode() ;
      FOR i := 1 TO 5 DO
        PCalc.Backup() ;
        PCalc.Contract(PCalc.a_New) ;
        PCalc.Normalize() ;
      END ;
      IF NOT KEY.Pressed() THEN
        DisplayPicture(NameMode, ProgramMode, ProgramSelect) ;
      END ;
    END ;

    LOOP
      INC(i) ;
      PCalc.Backup() ;
      PCalc.Contract(PCalc.a_New) ;
      PCalc.Normalize() ;

      IF (i MOD 20 = 0) AND NOT KEY.Pressed() THEN
        DisplayPicture(NameMode, ProgramMode, ProgramSelect) ;
      END ;

      IF i = 180 THEN EXIT END ;
    END ;

    (* now we start to transmit *)
    NameMode := 2 ;  (* Labels *)
    ProgramSelect := PmProgs.P_SPTA ;
    FOR i := 1 TO 2 DO
      GotoXY(1, PmDisp.MenuLine_1) ;
      IO.WrStr ("Kill  Transmit  Step  Repeat  Clear      Quit") ;
      ClrEol() ;
      DisplayPicture(NameMode, ProgramMode, ProgramSelect) ;
    END ;
    ClearBuf() ;
    LOOP
      DisplayPicture(NameMode, ProgramMode, ProgramSelect) ;

      LOOP
        IF NOT KEY.Pressed() THEN EXIT END ;
        keycode := KEY.Stroke() ;
        ch := CHR(keycode) ;
        CASE ch OF
        | "s", "S", " ", "r", "R" : (* collect those keys *)
          StoreKey(keycode) ;
        ELSE
          ClearBuf() ;
          StoreKey(keycode) ;
        END ;
      END ;

      IF KeyAvail() THEN
        ch := CHR(GetKey()) ;
        CASE ch OF
        | CHR(27), "q", "Q" :
          IF UserWantsToExit() THEN EXIT END ;
        | "s", "S", " " :
            Iri.Step() ;
        | "k", "K" :
            GotoXY(1, PmDisp.MenuLine_2) ;
            ClrEol() ;
            IO.WrStr(' Node=') ;
            node := ReadInt(1, 900) ;
            IF NOT EscapePressed() THEN
              Iri.KillNode(Iri.NumToLabel(node)) ;
            END ;

        | "t", "T" :
            GotoXY(1, PmDisp.MenuLine_2) ;
            ClrEol() ;
            IO.WrStr(' Node1=') ;
            node1 := ReadInt(1, 900) ;
            IO.WrStr(' Node2=') ;
            node2 := ReadInt(1, 900) ;
            IO.WrStr(' Repeat count=') ;
            repeat := ReadInt(0, MAX(INTEGER)) ;
            IF NOT EscapePressed() THEN
              Iri.Step() ;
              Iri.Transmit( Iri.NumToLabel(node1),
                            Iri.NumToLabel(node2),
                            repeat) ;
            END ;

        | "r", "R" :
            Iri.Step() ;
            DisplayPicture(NameMode, ProgramMode, ProgramSelect) ;
            Iri.Step() ;
            Iri.Repeat() ;
(* new, replaces
            Iri.Transmit(Iri.NumToLabel(node1), Iri.NumToLabel(node2)) ;
*)
        | "c", "C" :    (* Clear the network *)
            Iri.Reset() ;
        END ;

        ch := 0C ;

      END ;
      GotoXY(1, PmDisp.MenuLine_2) ;
      ClrEol() ;

    END ;
  END ;

  TextMode() ;

END Polytop.
