# trunc                   kr0te, 29.05.92
#
# VerkÅrzen jedes Wertes auf n stellen.
#
# Parameter 1 : n
#
# Weitere, oder stdin = Input
#
# Default, oder wenn Param 1 keine Zahl: n=2
#
# Beispiel : trunc 2 pgl6.pg
# Dadurch wird pgl6 nach pgl6-4 faktorisiert.

BEGIN {
  n = ARGV[1]+0
  if (n != 0) ARGV[1] = ""
  else n = 2
}

{ for (i=1 ; i<=NF ; i++) printf " %s", substr($i, 1, n)
  print ""
}


