# OPERATE                  kr0te, 10.10.91
#
# Kleine Žnderung: "-" intern als Parameter n”tig,
# imkompatibler neuer AWK...
# Kein anderer Aufruf n”tig.
#
# Ein Operator wird durch Kommandozeilenparameter angegeben.
# Es werden zyklisch Pl„tze getauscht.
# Jeder Parameter ist ein Zyklus. Die Zyklen werden nacheinander
# angewandt.
#
# Wichtiger Sonderfall: ein Plus (+) trennt mehrere Operatoren.
# Jeder Operator wird auf jede Inputzeile angewandt.
#
# Bearbeitet wird standardinput.
#
# Zyklische Vertauschung, der Pl„tze.
#
# Aufruf:
#    awk -f operate.awk  zyk1 zyk2 ...
#
# Beispiel:
#    awk -f operate.awk  123 56 345  < in.dat > out.dat
#
#    fhrt auf jeder Zeile von in.dat nacheinander die Platzwechsel durch.
#    Prinzipiell geht es nur mit maximal 9 Spalten.
#
# Linienpermutograph, vollst. Beispiel:
#    genperm 1234 > in.dat
#    awk -f operate.awk  12 + 23 + 34  < in.dat > out.dat
#    awk -f num.awk < out.dat > linienpm.nod
#
#
# Syntax: Zyklus   ::= String aus Ziffern.
#         Operator ::= Zyklus  [ blank Operator ]
#         Oplist   ::= Operator [ " + " Oplist ]
#
# Alle Zeilen werden damit bearbeitet.

BEGIN {    # Parameter sind Zyklen des Operators.
        Nzyk = ARGC-1
        for (i=1;i<=Nzyk;i++) {
          zyk[i] = ARGV[i] ; ARGV[i] = ""
        }
        ARGV[1] = "-"   # neuer AWK liest sonst nichts
      }

{     # Anwenden des Operators

  arg = $0
  res = arg
  str = ""
  for (i=1;i<=Nzyk;i++) {
    z = zyk[i]
    if (z == "+") {       # ende eines Operators, ausgeben, reset
      str = str" "arg" "res
      res = arg
    } else {              # alle Zyklen eines Operators abarbeiten
      wrk = res
      for (j=1;j<=length(z);j++) {
        from = substr(z,1,1)
        z = substr(z,2) from
        to = substr(z,1,1)
        # jetzt hab ich die Indizes und wende sie an.
        ch = substr(wrk,from,1)
        res = substr(res,1,to-1) ch substr(res,to+1)
      }
    }
  }
  str = str" "arg" "res
  print substr(str,2)
}
