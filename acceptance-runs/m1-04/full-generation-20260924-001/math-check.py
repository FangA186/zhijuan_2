"""Independent checks for this run's six answer disagreements; no network."""
from fractions import Fraction
from math import sqrt

assert len({-1, 0, 1, 2} & {x for x in range(-2, 3) if x*x <= 1}) == 3
for a in [Fraction(n, 8) for n in range(-24, 25)]:
    assert (abs(2*a-1) < 1) == (0 < a < 1)
    assert (abs(2*a-1) < abs(a+3)) == (Fraction(-2, 3) < a < 4)
assert 2 ** Fraction(-2) == Fraction(1, 4)  # log2(1/4)=-2; apply f again.
assert 2**2 - 2*2*2 + 3 < 0  # q18 author a<=2 includes an invalid a=2.
assert abs((sqrt(3)**2 + 3)/(2*sqrt(3)) - sqrt(3)) < 1e-12
population = 1000
for day in range(1, 17):
    population = population*2 if population < 4000 else population+2000
    if day == 2:
        assert population == 4000
    if day < 16:
        assert population < 32000
assert population == 32000
print('Six disputed questions independently checked; no model calls.')
