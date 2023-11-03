from monads import Result, Ok, Err, Try


def my_function(i: int) -> Result[str, Exception]:
    if i:
        return Ok("hello")
    else:
        return Err(Exception("i is zero"))


def my_function2(i: int) -> str:
    if i:
        return "hello"
    else:
        raise Exception("i is zero")


my_function(1).or_else("somthing wrong").flat_map(print)
my_function(0).or_else("somthing wrong").flat_map(print)

Try(my_function2, 1).or_else("somthing wrong").flat_map(print)
Try(my_function2, 0).or_else("somthing wrong").flat_map(print)

Ok(1).try_apply(my_function2).or_else("somthing wrong").flat_map(print)
Ok(0).try_apply(my_function2).or_else("somthing wrong").flat_map(print)