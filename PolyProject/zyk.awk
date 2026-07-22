# ZYK
#
# Zyklische Vertauschung, der Pl„tze.
#
# Eingabe:
#   Erste Zeile: der Operator "u" als Kette von Zyklen.
#                Syntax: Zyklus ::= String aus Ziffern.
#                        Operator ::= Zyklus  [ blank Operator ]
#   Alle weiteren Zeilen werden damit bearbeitet.

NR==1 {    # erste Zeile ist der Operator
        Nzyk = NF
        for (i=1;i<=NF;i++) {
          zyk[i] = $i
        }
        next
      }

{     # Anwenden des Operators

  arg = $0
  res = arg
  for (i=1;i<=Nzyk;i++) {
    z = zyk[i]
    for (j=1;j<=length(z);j++) {
      from = substr(z,1,1)
      z = substr(z,2) from
      to = substr(z,1,1)
      # jetzt hab ich die Indizes und wende sie ans.
      ch = substr(arg,from,1)
      res = substr(res,1,to-1) ch substr(res,to+1)
    }
  }
  print "u(" arg ") = " res
}

END  {
   for (i=1;i<=Nzyk;i++) print zyk[i]
}
