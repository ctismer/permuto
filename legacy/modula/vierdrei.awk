# VierDrei             kr0te, 10.11.90
#
# Vier Werte, 3 PlÑtze.
#
# Wir haben also 4^3 Werte, von 111 bis 444
# und wollen die Namen auch so lassen.
#
# Der Graph hat in jedem Knoten 9 Kanten, nÑmlich fÅr
# jeden Platz die drei anderen mîglichen Werte.

# Der Graph sieht sehr merkwÅrdig aus. Wir bilden daher Teilgraphen
# um Struktur sehen zu kînnen.
# Parameter: Mode
#
# Mode = 0        Alles ausgeben
# Mode = 1        Alles au·er den ganz gleichen
# Mode = 2        Alles au·er den ganz verschiedenen
# Mode = 3        wie 1 & 2


BEGIN {

  Mode = ARGV[1]+0

  delEQU = (Mode==1) || (Mode == 3)
  delDIF = (Mode==2) || (Mode == 3)

  # Aufbau der Ecken brauchen wir nicht.
  # for (i=1;i<=4;i++) for (j=1;j<=4;j++) for (k=1;k<=4;k++) Nodes[i j k] = 0

  # Aufbau der Kanten
  # jeder Wertwechsel an einem Platz ist Kante
  for (a=1;a<4;a++) for (b=a+1;b<=4;b++) {
    for (j=1;j<=4;j++) for (k=1;k<=4;k++) {
      take = 1
      if (delEQU) {    # keine Knoten, bei denen alles gleich ist
        take = take && !((a==j)&&(j==k)||(b==j)&&(j==k))
      }
      if (delDIF) {    # keine Knoten, bei denen alles verschieden ist
        take = take && ((a==j)||(j==k)||(k==a))&&((b==j)||(j==k)||(k==b))
      }
      if (take) {
        Edges[a j k, b j k] = 0
        Edges[j a k, j b k] = 0
        Edges[j k a, j k b] = 0
      }
    }
  }

  # Ausgabe der Kantenliste
  for (i in Edges) {
    split (i, x, SUBSEP)
    print x[1],x[2]
  }

###  for (i in Edges) print i
}
