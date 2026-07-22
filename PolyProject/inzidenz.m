(* Inzidenz
   Berechne Inzidenzmatrizen und deren Potenzen
   *)

machliste[Name_] :=
  ( ReadList[Name, Number] )

machmatrix[x_List] := Block[
  {dim, res, inz} ,
  dim = Max[x] ;
  res = Table[0,{dim},{dim}] ;
  inz = Partition[x,2] ;
  (res[[ First[#],Last[#]] ]=1)& /@ inz ;
  res
]

