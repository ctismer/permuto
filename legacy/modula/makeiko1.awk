# Make Ikosaeder        kr0te, 06.11.90

# Ausgehend von einem einfachen Ikosaeder wird ein neues
# aufgebaut mit unterteilten Dreiecken.

function link(from, to     ,x) {
  Nodes[from] = 0
  Nodes[to]   = 0
  if (from > to) { x=from ; from=to ; to=x }  # make unique
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

BEGIN {
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

  # Aufbrechen der alten Verbindungen,
  # Erzeugen der neuen Knoten und Verbindungen
  for (i in Edges) {
    split(i,x,SUBSEP)
    delete Edges[i]
    i = x[1] "*" x[2]
    Nodes[i] = 0
    Edges[x[1],i] = 0
    Edges[i,x[2]] = 0
  }

  # Eintragen der neuen Verbindungen fr die neuen Knoten.
  # Jedes Original-Dreieck enth„lt ein neues.
  for (i in Tri) {
    split(i,x,SUBSEP)
    Edges[x[1]"*"x[2],x[1]"*"x[3]] = 0
    Edges[x[1]"*"x[2],x[2]"*"x[3]] = 0
    Edges[x[1]"*"x[3],x[2]"*"x[3]] = 0
  }

  # Ausgeben der neuen Liste, mit neuen Namen.
  Name = 0
  for (i in Edges) {
    split(i,x,SUBSEP)
    if (Map[x[1]]==0) Map[x[1]] = ++Name
    if (Map[x[2]]==0) Map[x[2]] = ++Name
    print Map[x[1]], Map[x[2]]
  }
}
