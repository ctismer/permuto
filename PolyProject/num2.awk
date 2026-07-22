# NUM2                            kr0te, 28.11.91
#
# Numerieren einer Datei aus Permutationen.
# Die Erste Spalte wird als Namensspalte interpretiert.
# Nach dem Einlesen wird jedes Wort durch eine Nummer ersetzt.
#
# Aufruf:
#    awk -f num2.awk
#
# Beispiel:
#    awk -f num2.awk  < out.dat > out.nod
#
#    baut aus beliebigen Zahl- oder Wortpaaren eine
#    ab 1 numerierte Knotenliste (besser: Kantenliste) auf.

BEGIN {
  NodeNo = 0   # aber erster wird Node 1
  LineNo = 0
}

{
  if (!($1 in Nodes)) Nodes[$1] = ++NodeNo
  Lines[++LineNo] = $0
}

END {
  for (i=1;i<=LineNo;i++) {
    $0 = Lines[i]
    for (j=1;j<=NF;j++) if ($j in Nodes) $j = Nodes[$j]
    print
  }
}
