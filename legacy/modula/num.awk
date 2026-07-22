# NUM                             kr0te, 10.10.91
#
# Eine Datei aus Paaren wird in minimale Zahlenpaare gewandelt.
#
# Aufruf:
#    awk -f num.awk
#
# Beispiel:
#    awk -f num.awk  < out.dat > out.nod
#
#    baut aus beliebigen Zahl- oder Wortpaaren eine
#    ab 1 numerierte Knotenliste (besser: Kantenliste) auf.

BEGIN {
  NodeNo = 0   # aber erster wird Node 1
}

{
  if (!($1 in Nodes)) Nodes[$1] = ++NodeNo
  if (!($2 in Nodes)) Nodes[$2] = ++NodeNo
  print Nodes[$1], Nodes[$2]
}
