# from typing import Callable, Any
# # from dataclasses import dataclass
# #
# # @dataclass
# # class UntypedIO:
# #     _func: Callable
# #     def bind(self, function):
# #         return function(self._func())
# #
# #     @classmethod
# #     def lift(cls, a):
# #         return UntypedIO(lambda: a)
# #
# #
# # def t(a):
# #     def tot():
# #         print('lol')
# #         return 2 * a
# #
# #     return UntypedIO(tot)
# #
# #
# # MyIO = UntypedIO.lift("bonjourt").bind(t).bind(t).bind(print)
# import dataclasses
# from typing import Callable
#
#
# @dataclasses.dataclass
# class IO:
#     action: Callable
#
#     def __rshift__(self, func):
#         return self.flat_map(func)
#     def flat_map(self, func):
#         return IO(
#             lambda: func(self.action())
#         )
#
#     def map(self, f):
#         return IO(lambda: f(self.action()))
#
#     @staticmethod
#     def pure(v):
#         return IO(lambda: v)
#
#     @staticmethod
#     def eval(v):
#         return IO(lambda: v())
#     @staticmethod
#     def putStrLn(text):
#         return IO(lambda: print(text))
#
#     def __call__(self, *args, **kwargs):
#         return self.action()
#
#     def unsafe_run(self):
#         call = self.action
#         while True:
#             match call:
#                 case IO():
#                     return call.unsafe_run()
#                 case _ if callable(call):
#                     call = call()
#                 case _:
#                     return
#
# IO.getLine = IO(lambda: input())
#
# main = IO.putStrLn("hello") >> IO.eval(input).map(lambda x: x.upper()).flat_map(IO.putStrLn)
#
# main.unsafe_run()
# main.unsafe_run()
