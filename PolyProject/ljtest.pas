var i,j,k : integer ;
f : text ;

procedure p(s : string) ;
  begin
    write(f,s) ;
  end ;


begin assign(f,'lj') ;
rewrite(f) ;
p(#27'*p300x400Y') ;
p(#27'*t75R') ;
p(#27'*r1A') ;
for i := 1 to 20 do begin
  p(#27'*b8W') ;
  for j := 1 to 8 do
    p(chr(i+j)) ;
end ;
p(#27'*rB') ;

p(#27'*p300x600Y') ;
p(#27'*t100R') ;
p(#27'*r1A') ;
for i := 1 to 20 do begin
  p(#27'*b8W') ;
  for j := 1 to 8 do
    p(chr(i+j)) ;
end ;
p(#27'*rB') ;

p(#27'*p300x900Y') ;
p(#27'*t150R') ;
p(#27'*r1A') ;
for i := 1 to 20 do begin
  p(#27'*b8W') ;
  for j := 1 to 8 do
    p(chr(i+j)) ;
end ;
p(#27'*rB') ;

p(#27'*p300x1200Y') ;
p(#27'*t300R') ;
p(#27'*r1A') ;
for i := 1 to 20 do begin
  p(#27'*b8W') ;
  for j := 1 to 8 do
    p(chr(i+j)) ;
end ;
p(#27'*rB') ;

close(f) ;
end.
