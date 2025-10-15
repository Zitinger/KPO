import random
from domain.i_health_policy import IHealthPolicy
from domain.animal import Animal

class RandomHealthPolicy(IHealthPolicy):
    def __init__(self, healthy_prob=0.9):
        if not (0.0 <= healthy_prob <= 1.0):
            raise ValueError("Вероятность должна быть в диапазоне [0.0, 1.0]")
        self._p = healthy_prob
        self._rngs = {}

    def is_healthy(self, animal: Animal):
        rng = self._rngs.get(animal)
        if rng is None:
            rng = random.Random()
            self._rngs[animal] = rng
        return rng.random() < self._p
