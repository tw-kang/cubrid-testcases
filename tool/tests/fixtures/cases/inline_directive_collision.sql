-- @issue: none
-- @description: verifies inline CTP directives are passed through grammar
-- @expected: normal

select 1;
--@queryplan
select 2;
--@joingraph
select 3;
--@futuredirective
select 4;
