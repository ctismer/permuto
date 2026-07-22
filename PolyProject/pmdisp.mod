(*************************************************************

   Graphic Output

   still with fixed parameters, but will be generalized
   when multiple displays become urgent...

*************************************************************)

IMPLEMENTATION MODULE PmDisp ;

IMPORT Graph, Str ;

IMPORT TextPlot ;

FROM NodeMgr IMPORT nnodes, LineStatus, Dimensions, PermStr ;

FROM IntVector IMPORT Scale, Norm ;

PROCEDURE DrawPicFrame() ;
BEGIN
  Graph.Rectangle(_box_x1, _box_y1, _box_x2, _box_y2, FrameColor, FALSE) ;
END DrawPicFrame ;

PROCEDURE WipeOldPicture() ;
BEGIN
  Graph.Rectangle(_pic_x1, _pic_y1, _pic_x2, _pic_y2, BackColor, TRUE) ;
END WipeOldPicture ;

PROCEDURE SetPicClipping() ;
BEGIN
  Graph.SetClipRgn(_pic_x1, _pic_y1, _pic_x2, _pic_y2) ;
END SetPicClipping ;

PROCEDURE ResetClipping() ;
BEGIN
  Graph.SetClipRgn(0, 0, Graph.Width, Graph.Depth) ;
END ResetClipping ;



PROCEDURE DrawEdges (VAR Nodes : NodeTable ; names : CARDINAL;
                     progsel : PmProgs.ProgramType ) ;
  VAR i, j, farbe : CARDINAL ;
      x,y,z, xx,yy,zz : INTEGER ;
      px, py, pxx, pyy : INTEGER ;
      qx, qy : INTEGER ;  (* pos. pfeil *)

BEGIN
  SetPicClipping() ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    x := pos[1] ; y := pos[2] ; z := pos[3] ;

    FOR j := 1 TO nlink DO
      IF num < Nodes[links[j]]^.num THEN
        (* otherwise we get it all doubly painted *)
        WITH Nodes[links[j]]^ DO
          xx := pos[1] ; yy := pos[2] ; zz := pos[3]
        END ;
        farbe := ORD(Window.LightGray);
        IF (state.lines[j] = L_input)
        OR (state.lines[j] = L_output) THEN
          farbe := ORD(Window.Green) ;
        ELSIF state.lines[j] = L_locked THEN
          farbe := ORD(Window.Red) ;
        END ;
        IF (Dimensions >= 3) AND (z+zz > 0)  (* are we in the front? *)
        THEN
          farbe := farbe + 8 ;
        END ;

        IF j IN state.broken THEN farbe := 0 END ;
        px  := Scale(  x, Scale_X, Norm) +_pic_x0 ;
        py  := Scale( -y, Scale_Y, Norm) +_pic_y0 ;
        pxx := Scale( xx, Scale_X, Norm) +_pic_x0 ;
        pyy := Scale(-yy, Scale_Y, Norm) +_pic_y0 ;
        Graph.Line (px, py, pxx, pyy, farbe) ;

        IF (state.lines[j] = L_input)
        OR (state.lines[j] = L_output) THEN
          IF state.lines[j] = L_input THEN
            qx := (5*px+pxx) DIV 6 ;
            qy := (5*py+pyy) DIV 6 ;
          ELSE
            qx := (5*pxx+px) DIV 6 ;
            qy := (5*pyy+py) DIV 6 ;
          END ;
(* looks ugly:
          Graph.Rectangle (qx-3, qy-3, qx+3, qy+3, farbe, TRUE) ;
*)
          Graph.TrueDisc (qx, qy, 3, farbe) ;
        END ;

        IF (names>0) & (progsel # PmProgs.P_SPTA) THEN
          px := (px+pxx) DIV 2 ;
          py := (py+pyy) DIV 2 ;
          Graph.Rectangle (px-4, py-5, px+4, py+5, BackColor , TRUE) ;
          TextPlot.PlotCenteredStr(px, py, CHAR(opno[j]+ORD('0')), farbe);
        END ;
      END ;
    END ;
  END END ;
  ResetClipping() ;
END DrawEdges ;

PROCEDURE DrawNodes (VAR Nodes : NodeTable ; names : CARDINAL;
                     displ: BOOLEAN ; progsel : PmProgs.ProgramType) ;
  (* if displ, the value in field display of node.state is the node label.
     otherwise, the label is built of node number or node perm,
     depending on 'names' . *)
  VAR i, farbe : CARDINAL ;
      x,y,z : INTEGER ;
      str : PermStr ;
      px, py : INTEGER ;
      ign : BOOLEAN ;
      diam : INTEGER ;
BEGIN
  SetPicClipping() ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    x := pos[1] ; y := pos[2] ; z := pos[3] ;
    farbe := color ;
    IF (Dimensions >= 3) AND (z >= 0)   (* in the front ? *)
    THEN
      farbe := (color + 8) MOD 16 ;
    END ;
    px := Scale( x, Scale_X, Norm) +_pic_x0 ;
    py := Scale(-y, Scale_Y, Norm) +_pic_y0 ;

    CASE names OF
    | 0 : diam := 5 ;    (* nothing *)
    | 1 : diam := 9 ;    (* node numbers *)
    | 2 : diam := 12 ;   (* perm strings *)
    | 3 : diam := 9 ;    (* prog display *)
    END ;

    IF progsel = PmProgs.P_SPTA THEN   (* Iridium *)
      diam := Scale (11, iri.avail+1500, 10000) ;
    END ;

    IF state.dead THEN
      Graph.TrueDisc (px, py, diam, BackColor) ;
      Graph.TrueCircle (px, py, diam, ORD(Window.Black)) ;
    ELSE
      Graph.TrueDisc (px, py, diam, farbe) ;
    END ;
    IF state.active THEN
      Graph.TrueCircle (px, py, diam+1, ORD(Window.White)) ;
    END ;

    IF names>0 THEN
      (* we plot text inside the balls, therefore black is a good
         choice.
      *)
      str := "" ;
      CASE names OF
      | 1 : Str.CardToStr(LONGCARD(i), str, 10, ign) ;
      | 2 : Str.Copy(str, perm) ;
      | 3 : Str.IntToStr(LONGINT(state.display), str, 10, ign) ;
      END ;
    (* really hacked in for Iridium... *)
      IF progsel = PmProgs.P_SPTA THEN   (* Iridium *)
        IF color # ORD(Window.Yellow) THEN  (* hate! *)
          Str.IntToStr(LONGINT(iri.message.num), str, 10, ign) ;
        END ;
      END ;
      TextPlot.PlotCenteredStr(px, py, str, 0);
    END ;
  END END ;
  ResetClipping() ;
END DrawNodes ;

END PmDisp.
