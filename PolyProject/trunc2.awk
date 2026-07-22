# trunc2
#
# Verkrzen jedes Wertes auf 2 stellen.
# Dadurch wird pgl6 nach pgl4 faktorisiert.

{ for (i=1 ; i<=NF ; i++) printf " %s", substr($i, 1, 2)
  print ""
}

