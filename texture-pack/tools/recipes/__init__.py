"""Recipe modules. Each exposes register(R) and adds its outputs to the registry."""
from . import (terrain, stones, wood, foliage, plants, flora, minerals, colours, copper, liquids, organics, machines,
               special, environment, tuning)

MODULES = [terrain, stones, wood, foliage, plants, flora, minerals, colours, copper, liquids, organics, machines, special,
           environment, tuning]


def register_all(R):
    for m in MODULES:
        m.register(R)
