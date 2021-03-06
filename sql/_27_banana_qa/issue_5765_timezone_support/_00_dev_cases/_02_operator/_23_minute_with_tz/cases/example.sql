--cases from dev

SELECT MINUTE('2008-02-03 10:05:03');

SELECT MINUTE('2008-02-03 10:05:03.1234');

--[er]
SELECT MINUTE('10:05:03');

--[er]
--SELECT MINUTE(current_date);


-- test for valid date time format
select minute(datetimetz'2003-12-31 01:02:03.1234 Asia/Seoul'), if (minute(datetimetz'2003-12-31 01:02:03.1234 Asia/Seoul') = 2, 'ok', 'nok');
select minute(timestamptz'2003-12-31 01:02:03 Asia/Seoul'), if (minute(timestamptz'2003-12-31 01:02:03 Asia/Seoul') = 2, 'ok', 'nok');


-- test for valid date, time string format
select minute('2003-12-31 01:02:03.1234'), if (minute('2003-12-31 01:02:03.1234') = 2, 'ok', 'nok');
select minute('2003-12-31 01:02:03'), if (minute('2003-12-31 01:02:03') = 2, 'ok', 'nok');
select minute('01:02:03'), if (minute('01:02:03') = 2, 'ok', 'nok');


-- test for special case
select minute('23:59:59'), if (minute('23:59:59') = 59, 'ok', 'nok');
select minute('00:00:00'), if (minute('00:00:00') = 0, 'ok', 'nok');
select minute('00:00:00' - 1), if (minute('00:00:00' - 1) = 59, 'ok', 'nok');
select minute('23:59:59' + 1), if (minute('23:59:59' + 1) = 0, 'ok', 'nok');


-- check if ER_TIME_CONVERSION is occured.
select minute('00:61:00');
select minute('00:-10:10');
