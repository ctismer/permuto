@%debug% echo off
goto anfang

    PERMUTO.BAT
    Erzeugen und Anzeigen von Permutographen

    Parameter:
      1. Name der Ausgabedatei, max. 8 Zeichen, ohne Endung
      2. Permutationsstring
      3.- 9. Operatoren

:anfang
if "%3"=="" goto syntax

set prog=%0
set name=%1
set perm=%2
set oper=%3

rem collect more than 9 parameters...
shift
shift
shift
:loop
  if "%1%"=="" goto done
  set oper=%oper% %1
  shift
  goto loop
:done

genperm %perm% | awk -f operate.awk %oper% > %name%.pg

awk -f num2.awk < %name%.pg > %name%.nod

echo %prog% %name% %perm% %oper% > %name%.pgd

polytop %name%.nod

echo Der Permutograph "%name%" laesst sich nochmals anzeigen mit
echo   POLYTOP %name%.NOD

goto ende


:syntax
  echo  PERMUTO hat folgende Parameter:
  echo  1.)    Name der Ausgabedatei, max. 8 Zeichen ohne Endung
  echo  2.)    Permutationsstring
  echo  3.-9.  Operatoren.
  echo  Operatoren bitte mit einem einzelnen "+" trennen.
  echo  Beispiel:
  echo    permuto test 1234 12 34 + 234
  echo  erzeugt die Dateien test.pg und test.nod und zeigt dann
  echo  test.nod an.
  echo  Die Eingabe wird in test.pgd nochmals abgelegt.
  echo  Durch umkopieren in eine Batch-Datei laesst sich der
  echo  Aufruf wiederholen.
  echo  Die Ausgabe kann mit   polytop test.nod
  echo  wiederholt werden.
goto ende

:ende
