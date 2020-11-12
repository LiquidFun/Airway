import numpy as np


def adjacent(coord, moore_neighborhood=False):
    """ Returns a numpy array of adjacent coordinates to the given coordinate

    By default von Neumann neighborhood which returns only coordinates sharing a face (6 coordinates)
    Moore neighborhood returns all adjacent coordinates sharing a at least a vertex (26 coordinates)
    """
    d = [-1, 0, 1]

    def condition(manhattan_dist):
        if moore_neighborhood:
            return manhattan_dist != 0
        else:
            return manhattan_dist == 1

    directions = [np.array([x, y, z]) for x in d for y in d for z in d if condition(np.sum(np.abs([x, y, z])))]
    return [coord + direction for direction in directions]
