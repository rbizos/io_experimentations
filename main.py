# example usage
# Option
from monads import Option, Null, Some

Some("str").or_else("lol").map(print)
Null[str]().or_else("lol").map(print)
