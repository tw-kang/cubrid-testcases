--+ holdcas on;
set names iso88591;

--compare with constant
prepare st1 from 'select nullif(?, ?)';
execute st1 using 'a', 'A';
set names iso88591 collate iso88591_en_ci;
execute st1 using 'A', 'a';
set names utf8 collate utf8_en_cs;
execute st1 using 'A', 'a';

execute st1 using _iso88591'a', 'A';
execute st1 using 'a', _euckr'A';



drop table if exists t;
create table t(s1 varchar(10) collate utf8_en_ci, s2 enum('a', 'A', 'b', 'B') collate iso88591_en_cs);
insert into t values('a', 1);
insert into t values('A', 'B');


--compare with s1
prepare st2 from 'select s1, nullif(s1, ?) from t where exists (select s2=? from t) order by 1, 2';
execute st2 using 'a', 'b';
set names utf8 collate utf8_en_ci;
execute st2 using 'A', 'B';
set names utf8 collate utf8_en_cs;
execute st2 using 'A', 'b';
set names euckr;
execute st2 using 'a', 'B';

execute st2 using _iso88591'a', 'b';
execute st2 using _euckr'A', _utf8'b';


--compare with s2
prepare st3 from 'select s2, nullif(?, s2) from t where s1 = any(select ? from t) order by 1, 2';
--BUG CUBRIDSUS-13652 resolved
execute st3 using 'b', 'a';
set names utf8 collate utf8_en_ci;
execute st3 using 'B', 'A';
set names utf8 collate utf8_en_cs;
execute st3 using 'b', 'A';
set names euckr;
execute st3 using 'B', 'a';

execute st3 using _iso88591'b', 'a';
execute st3 using _euckr'B', _utf8'A';


--session variable
set @a1='a' collate utf8_en_cs;
set @a2='A' collate utf8_en_ci;
set @b1='b' collate utf8_en_cs;
set @b2='B' collate iso88591_en_ci;

set names iso88591;
execute st1 using 'a', @b1;
execute st1 using @b2, @a2;
execute st1 using @b2, 'A';

set names utf8;
execute st2 using @a1, @b2;
execute st2 using @a2, @b1;

set names euckr;
execute st3 using @b1, @a2;
execute st3 using @b2, @a1;


drop variable @a1, @a2, @b1, @b2;
deallocate prepare st1;
deallocate prepare st2;
deallocate prepare st3;

drop table t;

set names iso88591;

--+ holdcas off;
