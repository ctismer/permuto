# Make Ikosaeder        kr0te, 08.11.90
#
# Version fr groáe Frequenzen.
# Die Kanten werden sofort ausgegeben, Knoten werden gel”scht,
# sobald m”glich.

# Make Ikosaeder        kr0te, 06.11.90
#
# Allgemeine Version fr beliebige Teilungsfrequenz.

# Parameter 1 : Frequenz       (Default = 1)

# Ausgehend von einem einfachen Ikosaeder wird ein neues
# aufgebaut mit unterteilten Dreiecken.

# z„hlende Version von Link. Die Knoten wissen, wieviele Kanten
# durch sie hindurch gehen.

function link(from, to     ,x) {
  if (from > to) { x=from ; from=to ; to=x }  # make unique
  if ((from,to) in Edges) return
  Nodes[from] ++
  Nodes[to]   ++
  Edges[from,to] = 0
}

function init_iko() {
  link(1,2) ; link(2,3) ; link(3,1)

  link(1,6) ; link(1,4)
  link(2,4) ; link(2,5)
  link(3,5) ; link(3,6)

  link(1,7) ; link(4,7) ; link(6,7)
  link(2,8) ; link(4,8) ; link(5,8)
  link(3,9) ; link(5,9) ; link(6,9)

  link(4,10) ; link(7,10) ; link(8,10)
  link(5,11) ; link(8,11) ; link(9,11)
  link(6,12) ; link(9,12) ; link(7,12)

  link(10,11) ; link(11,12) ; link(12,10)
}

#
# Problem: Ausfllen eines Dreiecks mit Unterdreiecken.
# Dabei muá eine neue, eindeutige Benennung gefunden werden.
# Wichtig ist vor allem Eindeutigkeit, und! es muá der Randbereich
# der Dreiecke, der ja mehrmals berechnet wird, immer die gleichen
# Namen haben, damit die Dreiecke nachher auch zusammenh„ngen.
# In AWK ist es einfach, mit REAL zu arbeiten.
# Genausogut geht es aber auch mit konkatenierten Strings, die aus den
# Dreiecksknoten gebildet werden. Das Prinzip wird am Beispiel FREQ=3
# und mit Symbolen a,b,c,d fr die Ecken gezeigt:
#
#                   ccc   ccd   cdd   ddd
#
#                acc   bcc   bcd   bdd
#
#             aac   abc   bbc   bbd
#
#          aaa   aab   abb   bbb
#
# Wenn die Benennung immer gleich ist (etwa lexikographisch), passen die
# Dreieckskanten korrekt zusammen.
#

function make_key(a, b, c, na, nb, nc    ,i,res) {
  if (na > 0) res = res "+" a (na==1 ? "" : "*" na)
  if (nb > 0) res = res "+" b (nb==1 ? "" : "*" nb)
  if (nc > 0) res = res "+" c (nc==1 ? "" : "*" nc)
  return substr(res,2)
}

function fill_triangle(a, b, c, freq      ,i,j, k1, k2, k3) {
  for (i=0;i<freq;i++) {
    for (j=0;i+j<freq;j++) {
            k1 = make_key(a, b, c, freq-i-j, i, j)
      i++ ; k2 = make_key(a, b, c, freq-i-j, i, j)  ; i--
      j++ ; k3 = make_key(a, b, c, freq-i-j, i, j)  ; j--
      link(k1, k2) ; link(k2, k3) ; link(k1, k3)
    }
  }
}

BEGIN {

  FREQ = ARGV[1]
  if (FREQ+0==0) FREQ=1

  # Aufbauen des einfachen Ikosaeders
  init_iko()

  # Finden der Dreiecke, damit wir sp„ter leicht die neuen Verbindungen
  # einzeichnen k”nnen.
  for (i in Nodes) {
    for (j in Nodes) {
      for (k in Nodes) {
        if ( ((i,j) in Edges)&&((j,k) in Edges)&&((i,k) in Edges) ) {
          Tri[i,j,k] = 0
  } } } }

  # Aus den Dreiecken k”nnen wir nun alles aufbauen.
  # Daher wird erstmal alles weitere gel”scht.
  delete Nodes
  delete Edges

  # Gemischtes Aufbauen und Ausgeben.
  # Die Dreiecke werden ausgefllt.
  # Die Kanten werden ausgegeben und gel”scht.
  # Die Knoten werden gel”scht, wenn 6 Kanten hindurchgehen,
  # denn dann werden sie nicht weiter benutzt.
  Name = 0
  for (tr in Tri) {
    split(tr,x,SUBSEP)
    fill_triangle(x[1],x[2],x[3], FREQ)     # Dreiecke einzeichnen
    for (i in Edges) {                      # Kanten ausgeben und putzen
      split(i,x,SUBSEP)
      if (Map[x[1]]==0) Map[x[1]] = ++Name
      if (Map[x[2]]==0) Map[x[2]] = ++Name
      delete Edges[i]                       # Stringspeicher freimachen
      print Map[x[1]], Map[x[2]]
    }
    # jetzt darf man auch einige Knoten l”schen.
    # leider weiá ich nicht welche, da nicht alle den gleichen
    # Index haben.
    # Aber jedenfalls die inneren Knoten darf man l”schen.
    # Die haben Anteile von allen drei Ecken, also 2 "+"-Zeichen
    # im Schlssel.
    for (i in Nodes) if (i ~ /\+.*\+/) {
      delete Nodes[i]
      delete Map[i]
    }
  }
  print ""
  print "Dies ist ein Ikosaeder der Frequenz", FREQ

###  for (i in Nodes) print i,"=",Nodes[i]
}
