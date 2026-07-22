# RNA.AWK  Auswerten der RNA-Datei.
# mG wird abgebissen.
# ACGU
# Strings aus mindestens 10 groáen ACGU-Zeichen werden erkannt und
# konkateniert. Das erste Auftreten eines Start-Codons (AUG) wird
# durch Stringmatch gesucht. Ab dort werden alle Triplets bis zum
# ersten Stop-Codon (UAA) ausgegeben.

BEGIN { buf = "" ; Inside = 0 }
# Inside = 0 : noch vor Start.
#        = 1 : in der Sequenz

/[ACGU][ACGU][ACGU][ACGU][ACGU]/ {
  for (i=1;i<=NF;i++) {
    par = $i
    if (par ~ /^(mG)?[ACGU]+$/) {
      sub (/^mG/,"",par)
      buf = buf par
      if (inside == 0) {    # suche Start-Codon
        start = index(buf, "AUG")
        if (start > 0) {    # found
          buf = substr(buf,start)
          inside = 1
        }
      }
      if (inside == 1) {    # gib aus, suche Stop-Codon
        while (length(buf)>=3) {
          rna[++codons] = code = substr(buf,1,3)
          buf = substr(buf,4)
          if (code == "UAA") exit    #   stop gefunden
        }
      }
    }
  }
}

END {
  for (i=1;i<=codons;i++) {
    print rna[i]
  }
}
