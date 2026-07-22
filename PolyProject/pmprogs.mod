(*************************************************************

   Permutographic Programs

*************************************************************)

IMPLEMENTATION MODULE PmProgs ;

FROM NodeMgr IMPORT nnodes, Nodes, NodePtr, LineStatus, MaxNodes, MaxNodesTot ;

FROM Utilities IMPORT SetZero ;

PROCEDURE ResetMachine() ;
  (* erases all program-specific machine states *)
  VAR i : INTEGER ;
BEGIN
  FOR i := 1 TO nnodes DO WITH Nodes[i]^.state DO
    SetZero(lines) ;   (* all lines = L_free *)
    step := 0 ;
    active := FALSE ;
  END END ;
END ResetMachine ;

PROCEDURE _update_linestates() ;
  (* the line states are updated according to the step values *)
  VAR i, link : CARDINAL ; other : NodePtr ;
BEGIN
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    FOR link := 1 TO nlink DO
      other := Nodes[links[link]] ;
      IF    state.dead OR other^.state.dead         THEN
        state.lines[link] := L_locked
      ELSIF link IN state.broken                    THEN
        state.lines[link] := L_free
      ELSIF (state.step=0) OR (other^.state.step=0) THEN
        state.lines[link] := L_free
      ELSIF state.step < other^.state.step          THEN
        state.lines[link] := L_output
      ELSIF state.step = other^.state.step          THEN
        state.lines[link] := L_locked
      ELSIF state.step > other^.state.step          THEN
        state.lines[link] := L_input
      END ;
    END ;
  END END ;
END _update_linestates ;

PROCEDURE _activate_maxstep() : CARDINAL ;
  (* finds max step, activates those, and returns step *)
  VAR i, max : INTEGER ;
BEGIN
  max := 0 ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^.state DO
    IF NOT dead AND (step > max) THEN max := step END ;
  END END ;
  IF max=0 THEN RETURN 0 END ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^.state DO
    IF NOT dead AND (step = max) THEN
      active := TRUE ;
      display := sum ;
    END ;
  END END ;
  RETURN max ;
END _activate_maxstep ;

PROCEDURE InitSPA(StartNode : CARDINAL) ;
  VAR i : CARDINAL ;
BEGIN
  ResetMachine() ;
  Nodes[StartNode]^.state.active := TRUE ;
  Nodes[StartNode]^.state.step   := 1 ;

  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    state.display := num ;
  END END ;
  WITH Nodes[StartNode]^.state DO
    display := step-1 ;
  END ;

END InitSPA ;

  (* ShortestPath performs one parallel step each time
     it is called. So, it can be watched easily.
  *)

PROCEDURE ShortestPath() : BOOLEAN ;
  VAR i, j : CARDINAL ;
      act : SET OF [1..MaxNodesTot] ;
      link : CARDINAL ;
      phase : CARDINAL ;  (* other word for step *)
      found : CARDINAL ;
      this : CARDINAL ;
BEGIN
  (* find active nodes, set them inactive and save Flags *)
  SetZero(act) ;
  found := 0 ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IF state.active THEN
      state.active := FALSE ;
      IF NOT state.dead THEN
        INCL(act, i) ;
        INC(found) ;
        this := i ;
      END ;
    END ;
  END END ;

  (* did we find something? *)
  IF found = 0 THEN RETURN FALSE END ;

  (* now do the calculations, depending on step *)
  FOR i := 1 TO nnodes DO IF i IN act THEN WITH Nodes[i]^ DO
    phase := state.step ;
    FOR link := 1 TO nlink DO
      j := links[link] ;
      IF NOT (link IN state.broken)            (* line works *)
      AND NOT Nodes[j]^.state.dead   (* colleague answers *)
      THEN WITH Nodes[j]^.state DO
        IF step = 0 THEN        (* empty node, is receiver *)
          step := phase+1 ;
          active := TRUE ;      (* pass handle *)
          display := step-1 ;   (* show path length *)
        END ;
      END END ;
    END ;
  END END END ;

  _update_linestates() ;

  RETURN TRUE ;

END ShortestPath ;

PROCEDURE InitParSum() : BOOLEAN ;
  (* we require SPA to run first. Here, we seek for the sinks, the nodes
     with largest "step" from SPA and make them active.
     Also, all 'sum' fields are initialized to 1
  *)
  VAR i : CARDINAL ; ok : BOOLEAN ;
BEGIN
  FOR i := 1 TO nnodes DO WITH Nodes[i]^.state DO
    sum := 1 ;
  END END ;
  ok := _activate_maxstep() > 0 ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^.state DO
    IF active THEN display := sum END ;
  END END ;
  RETURN ok ;
END InitParSum ;

  (* ParSum simply uses the paths found by SPA. Starting with the nodes
     with highest stepnumber, the found paths are walked backwards.
     So, each active node first reverses it's inputs and outputs.
     Each node initially gets a 1 as value (again, step is used).
     It sums up, whatever comes in, and transmits it over one of its
     output lines. On the other lines, it sends a 0 to trigger all nodes
     for this action.
  *)
PROCEDURE ParSum() : BOOLEAN ;
  VAR i, j : CARDINAL ;
      act : SET OF [1..MaxNodesTot] ;
      link : CARDINAL ;
      found : CARDINAL ;
      this : CARDINAL ;
      message : CARDINAL ;
BEGIN
  (* find active nodes, set them inactive and save Flags *)
  SetZero(act) ;
  found := 0 ;
  FOR i := 1 TO nnodes DO WITH Nodes[i]^ DO
    IF state.active THEN
      state.active := FALSE ;
      IF NOT state.dead THEN
        INCL(act, i) ;
        INC(found) ;
        this := i ;
      END ;
    END ;
  END END ;

  (* did we find something? *)
  IF found = 0 THEN RETURN FALSE END ;

  (* now do the ParSum, together with change of link direction. Observe,
     that we may not change directions for links from where we
     received a message. *)
  FOR i := 1 TO nnodes DO IF i IN act THEN WITH Nodes[i]^ DO
    message := state.sum ;       (* to transfer once *)
    state.step := -state.step ;  (* clear to avoid becoming active again *)
    FOR link := 1 TO nlink DO
      j := links[link] ;
      IF NOT (link IN state.broken)            (* line works *)
      AND NOT Nodes[j]^.state.dead             (* colleague answers *)
      AND (Nodes[j]^.state.sum # 0)
      (* 0 means, that node has sent already. otherwise, we have a 1 from
         the parsum init *)
      THEN
        message := state.sum ;
        state.sum := 0 ;
        state.display := state.sum ;
        WITH Nodes[j]^.state DO
          sum := sum + message ;
          display := sum ;
        END ;
      END ;
    END ;
  END END END ;

  _update_linestates() ;
  RETURN _activate_maxstep() > 0 ;

END ParSum ;

END PmProgs.
