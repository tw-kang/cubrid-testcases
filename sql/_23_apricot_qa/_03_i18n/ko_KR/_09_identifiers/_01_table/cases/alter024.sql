set system parameters 'alter_table_change_type_strict=yes';
CREATE TABLE 테이블(칼럼1 int);
INSERT INTO 테이블 VALUES (1),(-2147483648),(2147483647); 
ALTER TABLE 테이블 CHANGE 칼럼1 칼럼2 CHAR VARYING(4);
drop class  테이블;
set system parameters 'alter_table_change_type_strict=no';
CREATE TABLE 테이블(칼럼1 INT);
INSERT INTO 테이블 VALUES (1),(-2147483648),(2147483647); 
ALTER TABLE 테이블 CHANGE 칼럼1 칼럼2 CHAR VARYING(4); 
SELECT * FROM 테이블  order by 1;
drop class  테이블;