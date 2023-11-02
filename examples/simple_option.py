# example usage
# Option
from monads import Option, Null, Some

Some("str").or_else("lol").map(print)
Null[str]().or_else("lol").map(print)


(Null[str]().flat_map(lambda x: Some(x.upper())).or_else("kek").map(print))
Some("bonjour").flat_map(lambda x: Some(x.upper())).map(print)
