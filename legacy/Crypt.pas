{-----------------------------------------------------------------------------}
{                                                                             }
{ CRYPT               VerschlÅsselung von Dateien             kr0te, 25.10.87 }
{                     Version mit Block-E/A                                   }
{ Dateien werden unkenntlich gemacht durch öberlagerung mit pseudo-           }
{ zufÑlligen Bytes. Die Dekodierung geschieht durch nochmaliges VerschlÅsseln }
{ mit dem gleichen Passwort.                                                  }
{                                                                             }
{ Parameter: InpFile OutFile       Passwort von Tastatur                      }
{                                                                             }
{-----------------------------------------------------------------------------}

{$K-}

program Crypt ; uses CRT ;

Type
  FileName = string[66] ;

function UpcaseStr (S: String) : String ;
  var
    i : integer ;
  begin
    for i:=1 to length(S) do UpcaseStr[i] := Upcase(S[i]) ;
    UpcaseStr[0] := S[0] ;
  end ;

function trimme (S: String) : String ;
  begin
    while (S<>'') and (S[1]=' ') do delete (S,1,1) ;
    while (S<>'') and (S[length(S)]=' ') do S[0]:=pred(S[0]) ;
    trimme := S ;
  end ;

function EinSpace (S: String) : String ;
  begin
    while pos ('  ', S) <> 0 do
      delete (S, pos('  ', S), 1) ;
    EinSpace := S ;
  end ;

procedure ErrorExit (Msg: String) ;
  begin
    writeln (Msg) ;
    halt(1) ;
  end ;

const
  BlockSize = 16384 ;

var                  { seed ist leider versionsabhÑngig! }
  seed             : array[0..3] of byte absolute RandSeed ;
  Pass, Pas2       : String ;
  InpFile, OutFile : file ;
  IoBuf            : array[1..BlockSize] of byte ;
  i,j              : integer ;
  x, ign           : char ;
  BytesInBuf       : integer ;
  Counter          : longint ;
  Mod1000          : integer ;

procedure ReadInvisible (var S: String) ;
  var
    C : char ;
  begin S := '' ;
    repeat
      C := ReadKey ;
      if C <> #13 then
        S := S + C ;
    until (C=#13) or (length(S) = pred(sizeof(S))) ;
  end ;

procedure ScreenPlay ;      { zeige ZÑhler an und teste auf Fehler }
  begin
    if IoResult <> 0 then
      ErrorExit (' I/O-Fehler, Konvertierung abgebrochen!') ;
    inc(Counter, Mod1000) ;
    Mod1000 := 0 ;
    gotoXY (1,WhereY) ;
    write (Counter) ;
  end ;

begin
  if ParamCount <> 2 then begin
    writeln ('Crypt braucht 2 Parameter:') ;
    writeln ('InpFile OutFile') ;
    writeln ;
    writeln ('Das Passwort wird zweimal unsichtbar eingetippt.') ;
    writeln ('Es wird dann InpFile in OutFile gewandelt.') ;
    halt (1) ;
  end ;

  assign (InpFile, ParamStr(1)) ;
  assign (OutFile, ParamStr(2)) ;
{$I-}
  reset (InpFile, 1) ;
  if IoResult <> 0 then
    ErrorExit ('Datei nicht gefunden: '+ParamStr(1)) ;
  reset (OutFile, 1) ;
  close (OutFIle) ;
  if IoResult = 0 then begin
    while Keypressed do ign := ReadKey ;
    write ('Datei ',ParamStr(2),' existiert schon. öberschreiben? (J/N):') ;
    repeat
      ign := upcase(ReadKey) ;
    until ign in ['J','N'] ;
    writeln (ign) ;
    if ign = 'N' then
      ErrorExit ('CRYPT storniert.') ;
  end ;
  rewrite (OutFile, 1) ;
  if IoResult <> 0 then
    ErrorExit ('Datei lÑ·t sich nicht einrichten: '+ParamStr(2)) ;

  write ('Gib Password (wird nicht angezeigt) :') ; ReadInvisible (Pass) ;
  writeln ('<invisible>:') ;
  write ('Bitte noch einmal zur Kontrolle     :') ; ReadInvisible (Pas2) ;
  writeln ('<invisible>:') ;

  Pass := UpcaseStr(Trimme(EinSpace(Pass))) ;
  if Pass <> UpcaseStr(Trimme(EinSpace(Pas2))) then
    ErrorExit ('+++ Die Eingaben sind unterschiedlich. Abbruch!') ;
  if Pass = '' then
    ErrorExit ('+++ Leere Eingabe ist unzulÑssig!') ;

{ Startwert des Zufallsgenerators aus Passwort erzeugen: }
  fillchar (seed, sizeof(seed), 0) ;
  for i:=1 to length (Pass) do for j:=0 to 3 do
    seed[j] := random(256) xor ord(Pass[i]) ;

{ die eigentliche Codierung: }
  Mod1000 := 0 ; Counter := 0 ;
  BytesInBuf := 0 ;
  repeat
    if BytesInBuf <> 0 then
      BlockWrite (OutFile, IoBuf, BytesInBuf) ;
    BlockRead (InpFile, IoBuf, BlockSize, BytesInBuf) ;
    for i:=1 to BytesInBuf do begin
      IoBuf[i] := IoBuf[i] xor random(256) ;      { des Pudels Kern }
      Mod1000 := succ(Mod1000) ;
      if Mod1000 = 1000 then ScreenPlay ;
    end ;
  until BytesInBuf = 0 ;

  close (InpFile) ; close (OutFile) ;
  ScreenPlay ; writeln (' Bytes bearbeitet. Ende der Konvertierung.') ;
end.
