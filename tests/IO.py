import unittest
from monads.IO import IO
from typing import Any


class TestIO(unittest.TestCase):
    _call: int = 0
    _call_with: Any = None

    def setUp(self) -> None:
        self._call = 0
        self._call_with = None

    def _some_side_effect(self):
        self._call += 1

    def _some_side_effect_with_parameter(self, *args):
        self._call_with = args
        return IO.eval(self._some_side_effect)

    def some_side_effect(self) -> IO[None]:
        return IO.eval(self._some_side_effect)

    def some_side_effect_with_parameter(self) -> IO[Any]:
        return IO.eval(self._some_side_effect)

    def test_referential_transparency_and_operator(self):
        effect = self.some_side_effect()
        (effect & effect & effect & effect).unsafe_run()
        self.assertEqual(self._call, 4)
        a = effect & effect
        (a & a).unsafe_run()
        self.assertEqual(self._call, 8)

    def test_referential_transparency_plus_operator(self):
        effect = self.some_side_effect()
        (effect + effect + effect + effect).unsafe_run()
        self.assertEqual(self._call, 4)
        a = effect + effect
        (a + a).unsafe_run()
        self.assertEqual(self._call, 8)


    def test_lazy(self):
        self.some_side_effect()
        self.assertEqual(self._call, 0)
        _ = self.some_side_effect() >> self.some_side_effect >> self.some_side_effect
        self.assertEqual(self._call, 0)

    def test_passing_results(self):
        io = IO.pure("value") >> self._some_side_effect_with_parameter
        self.assertIsNone(self._call_with)
        io.unsafe_run()
        self.assertEqual(self._call_with, ("value",))


    def test_repeat(self):
        self.some_side_effect().repeat(4).unsafe_run()
        self.assertEqual(self._call, 4)

        (self.some_side_effect() * 6).unsafe_run()
        self.assertEqual(self._call, 10)

    def test_gather(self):
        (
            (IO.pure("test") & IO.pure(123)) >> self._some_side_effect_with_parameter
        ).unsafe_run()
        self.assertEqual(self._call_with, (("test", 123),))


if __name__ == "__main__":
    unittest.main()
