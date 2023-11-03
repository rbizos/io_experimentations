from monads import IO

io = (IO.input("hello who?:").map(lambda x: f"HELLO: {x.upper()} !!!") >> IO.print) * 2

io.run()
