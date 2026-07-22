(*# check(stack=>off,
          index=>off,
          range=>off,
          overflow=>off,
          nil_ptr=>off) *)
IMPLEMENTATION MODULE perms;

PROCEDURE NextPerm(n:CARDINAL; VAR s:ARRAY OF BYTE; 
                   VAR wrap:BOOLEAN);
VAR 
  i:CARDINAL; (* s[i-1] is the most significant byte changed *)
  j:CARDINAL; (* s[j] is the byte to be swapped with s[i-1] *)
  tmp:BYTE;



BEGIN
  IF n = 0 THEN
    wrap := TRUE;
    RETURN;
  END;
  i := n - 1;



  LOOP 
    IF i = 0 THEN
      wrap := TRUE;
      EXIT;
    END;



    IF s[i-1] < s[i] THEN
      j := n - 1;
      WHILE s[j] <= s[i-1] DO
        j := j - 1;
      END;
      tmp := s[j]; s[j] := s[i-1]; s[i-1] := tmp; (* swap *)
      wrap := FALSE;
      EXIT;
    END;
    i := i - 1;
  END;
  



  (* s[i]..s[n-1] are in reverse order, reversing them
     yields the minimum permutation we require *)
  j := n - 1;
  WHILE i < j DO
    tmp := s[j]; s[j] := s[i]; s[i] := tmp;
    i := i + 1;
    j := j - 1;
  END;
END NextPerm;

END perms.

