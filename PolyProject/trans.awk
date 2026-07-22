BEGIN {
  SEARCHING=1
  LEARNING=2
  state=SEARCHING
}


state==SEARCHING { arg = $0
                   if (arg in WORDS) print arg, "->", WORDS[arg]
                   else {
                     print "dunno " arg ", gimme result"
                     state=LEARNING
                   }
                   next
                 }

state==LEARNING  { WORDS[arg] = $0
                   WORDS[$0] = arg
                   state=SEARCHING
                 }
