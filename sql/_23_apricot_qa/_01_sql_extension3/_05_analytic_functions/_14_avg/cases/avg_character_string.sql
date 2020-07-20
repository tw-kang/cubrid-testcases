--TEST: test with character string data types and normal syntax 


create table avg_string(
	col1 char(20),
	col2 varchar(100), 
	col3 nchar(20),
	col4 nchar varying,
	col5 string,
	col6 int
);


insert into avg_string values('aaaaa', 'This is a dog.', n'1990-1-1 11:11:11', n'1234', 'character', 1234);
insert into avg_string values('aaaaa', 'This is a cat.', n'1991-1-1 11:11:11', n'22222', 'character', 2345) ;
insert into avg_string values('aaaaa', 'This is a dog.', n'1992-1-1 11:11:11', n'87', 'character', 1111);
insert into avg_string values('aaaaa', 'This is a cat.', n'1993-1-1 11:11:11', n'888', 'character', 9999);
insert into avg_string values('aaaaa', 'This is a dog.', n'1994-1-1 11:11:11', n'999', 'character', 2345);
insert into avg_string values('eeeee', 'This is a cat.', n'1995-1-1 11:11:11', n'1222', 'character', 5678);
insert into avg_string values('eeeee', 'This is a dog.', n'1996-1-1 11:11:11', n'1234', 'character', 2345);
insert into avg_string values('eeeee', 'This is a dog.', n'1997-1-1 11:11:11', n'563', 'character', 1111);
insert into avg_string values('eeeee', 'This is a rabbit.', n'1998-1-1 11:11:11', n'111', 'character', 9999);
insert into avg_string values('ccccc', 'This is a dog.', n'1999-1-1 11:11:11', n'777', 'character', 5676);
insert into avg_string values('ccccc', 'This is a dog.', n'2000-1-1 11:11:11', n'9898', 'string', 5678);
insert into avg_string values('ccccc', 'This is a rabbit.', n'2001-1-1 11:11:11', n'1234', 'string', 2345);
insert into avg_string values('zzzzz', 'This is a dog.', n'2002-1-1 11:11:11', n'111', 'string', 1111);
insert into avg_string values('bbbbb', 'This is a dog.', n'2003-1-1 11:11:11', n'87', 'string', 9999);
insert into avg_string values('bbbbb', 'This is a cat.', n'2004-1-1 11:11:11', n'12356', 'string', 3333);
insert into avg_string values('bbbbb', 'This is a dog.', n'2005-1-1 11:11:11', n'3232', 'string', 1234);
insert into avg_string values('bbbbb', 'This is a dog.', n'2006-1-1 11:11:11', n'22222', 'string', 9999);
insert into avg_string values('bbbbb', 'This is a rabbit.', n'2007-1-1 11:11:11', n'999', 'string', 2345);
insert into avg_string values('bbbbb', 'This is a dog.', n'2008-1-1 11:11:11', n'87', 'string', 3456);
insert into avg_string values('bbbbb', 'This is a dog.', n'2009-1-1 11:11:11', n'111', 'string', 1818);


--TEST: OVER() clause
--TEST: char(n) 
select col1, col2, avg(col6) over() from avg_string order by 1, 2;
--TEST: varchar(n), with alias+all
select col2, col3, avg(all col4) over() average from avg_string order by 1, 2;
--TEST: nchar(n), with where clause
select col3, col4, avg(unique col6) over() average from avg_string where col1 > 'aaaaa' order by col3, col4;
--TEST: nchar varying, distinct
select col4, col1, avg(distinct col4) over() average from avg_string order by 1, 2;
--TEST: string
select col5, col3, avg(all col4) over() average from avg_string order by 1, 2;
--TEST: syntax error
select col1, col3, col4, avg(col5) over average from avg_string;
select col1, col3, col2, avg(col6) over(1) average from avg_string;



--TEST: OVER(PARTITION BY) clause
--TEST: partition by char(n)
select col1, col2, col3, col4, col5, avg(col6) over(partition by col1) average from avg_string order by 1, 2, 3, 4, 5;
--TEST: partition by varchar(n)
select col1, col2, col3, col4, col5, avg(distinctrow col4) over(partition by col2) average from avg_string order by 2, 1, 3, 4, 5;
--TEST: partition by nchar(n)
select col1, col2, col3, col4, col5, avg(col4) over(partition by col3) average from avg_string order by 3, 1, 2, 4, 5;
--TEST: partition by nchar varying
select col1, col2, col3, col4, col5, avg(all col6) over(partition by col4) average from avg_string order by 4, 1, 2, 3, 5;
--TEST: partition by string
select col1, col2, col3, col4, col5, avg(unique col4) over(partition by col5) average from avg_string order by 4, 1, 2, 3, 5;



--TEST: OVER(ORDER BY) clause
--TEST: order by 1 column name
select col1, avg(col6) over(order by col1) average from avg_string;
--TEST: order by 2 column names
select col2, col3, avg(all col4) over(order by col2, col3 asc) average from avg_string;
--TEST: order by more than 2 column names
select col1, col2, col3, col4, col5, avg(unique col6) over(order by col1, col2 desc, col3, col4 asc, col5) average from avg_string;
--TEST: order by columns not selected
select col3, avg(distinct col4) over(order by col4 desc, col2, col1 asc) average from avg_string;
--TEST: order by 1 position
select col4, avg(all col6) over(order by 1) average from avg_string;
--TEST: order by 3 positions
select col3, col2, avg(distinctrow col4) over(order by 1, 2 desc, 3 asc) average from avg_string;
--TEST: order by more than 3 positions
select col1, col2, col3, col4, col5, avg(unique col6) over(order by 3, 2 asc, 5 desc, 1 desc, 4) average from avg_string;
--TEST: order by positions not existed
select col2, avg(distinct col4) over(order by 2) average from avg_string;
select col1, avg(all col6) over(order by 3, 4, 1 desc) average, col2, col4 from avg_string;
select col3, col4, avg(col4) over(order by 5) average from avg_string;
select col3, col1, avg(col6) over(order by 100) average from avg_string;
--TEST: order by column names and positions
select col1, col2, col3, col4, col5, avg(all col4) over(order by 1, col2 desc, 3, col4 asc, 5 desc) average from avg_string;




--TEST: OVER(PARTITION BY ORDER BY) clause
--TEST: partition by char(n)
select col1, col2, col3, avg(distinct col6) over(partition by col1 order by 1, 2, 3) from avg_string;
--TEST: partition by varchar(n)
select col2, col4, col1, avg(col6) over(partition by col2 order by col2, col4, col1 desc) from avg_string;
--TEST: partition by nchar(n)
select col3, avg(all col4) over(partition by col3 order by 1, 3) average, col2 from avg_string;
--TEST: partition by nchar varying
select col4, col1, avg(unique col6) over(partition by col4 order by 1, 2 desc) average from avg_string;
--TEST: partition by string
select col5, col2, col4, avg(all col4) over(partition by col5 order by col4, 1, 2 asc) from avg_string;
--TEST: syntax error
select col1, col2, avg(distinct col6) over(order by col1, col2 partition by col2) from avg_string;



drop table avg_string; 















