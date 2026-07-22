# wandle RNA-Sequenz in Permutograph.
# Zeichen aus UCAG werden in 1234 gewandelt.

BEGIN {
  for (i=1;i<=4;i++) char[i] = substr("UCAG",i,1)
  for (i=1;i<=4;i++) for (j=1;j<=4;j++) for (k=1;k<=4;k++) {
    arg = char[i] char[j] char[k]
    map[arg] = i j k
  }
}

{ for (i=1;i<=NF;i++) if ($i ~ /^[UCAG][UCAG][UCAG]$/) {
  last = act
  act = map[$i]
  if (last != "") print last, act    # von nach
  }
}
