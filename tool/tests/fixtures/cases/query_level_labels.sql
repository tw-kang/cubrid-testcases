-- @issue: none
-- @description: verifies query-level labels coexist with metadata header
-- @expected: normal

--1. first scenario - basic select
select 1;

--2. second scenario - arithmetic
evaluate '2. select list contains arithmetic operation (should work) -> mergeable list';
select 1+2;

evaluate 'Error (stack overflow): recursive call';
select 3;
