import math
from typing import Set
from typing import Tuple

import numpy as np


def _adjacent(coord, moore_neighborhood=False):
    d = [-1, 0, 1]

    def condition(manhattan_dist):
        if moore_neighborhood:
            return manhattan_dist != 0
        else:
            return manhattan_dist == 1

    directions = [np.array([x, y, z]) for x in d for y in d for z in d if condition(np.sum(np.abs([x, y, z])))]
    return np.array([coord + direction for direction in directions])


# Pre-compute for faster operations
adjacent_6 = _adjacent(np.array([0, 0, 0]), False)
adjacent_26 = _adjacent(np.array([0, 0, 0]), True)


def adjacent(coord, moore_neighborhood=False):
    """Returns a numpy array of adjacent coordinates to the given coordinate

    By default von Neumann neighborhood which returns only coordinates sharing a face (6 coordinates)
    Moore neighborhood returns all adjacent coordinates sharing a at least a vertex (26 coordinates)
    """
    return coord + (adjacent_26 if moore_neighborhood else adjacent_6)


def get_numpy_sphere(radius, hollow=False):
    """Returns a numpy 3D bool array with True where the sphere lies and False elsewhere as well as the centre

    If hollow==True then only the outer shell of the sphere will be True

    Suggested use:
        use this to create a sphere, then np.nonzero() to get the coordinates of the points
        which are of interest. Then add the coordinates of the point where circle lies like this:
            sphere_around_point = tuple(map(sum, zip(np.nonzero(sphere), at_point)))
        now you can iterate over this to color in the points or something like that
    """

    shape = ((math.ceil(radius) * 2) + 1,) * 3
    centre = np.array([round(radius)] * 3)
    dist_mat = np.full(shape, 0.0)
    for x in range(len(dist_mat)):
        for y in range(len(dist_mat[x])):
            for z in range(len(dist_mat[x][y])):
                dist_mat[x][y][z] = np.linalg.norm(centre - np.array([x, y, z]))
    sphere = dist_mat <= radius
    if hollow:
        sphere &= radius - 1 < dist_mat
    return sphere, centre


def get_coords_in_sphere_at_point(radius, point, hollow=False):
    sphere, centre = get_numpy_sphere(radius, hollow=hollow)
    coords = np.nonzero(sphere)
    sphere_around_point = tuple(map(sum, zip(coords, point, -centre)))
    return sphere_around_point


def find_radius_via_sphere(at_point: Tuple[int, int, int], allowed_types: Set[int], model: np.ndarray):
    """Returns the maximum radius of a sphere which fits into the model at the given point

    This only considers voxels in the model which have a value in allowed_types (e.g. 1)
    and views everything else as empty.
    """
    max_radius = 50
    for radius in range(1, max_radius):
        sphere_around_point = get_coords_in_sphere_at_point(radius + 0.5, at_point, hollow=True)
        for x, y, z in zip(*sphere_around_point):
            try:
                if model[round(x), round(y), round(z)] not in allowed_types:
                    return radius
            except IndexError:
                pass
    return max_radius
    # TODO
    # raise Exception(f"ERROR: Within radius of {max_radius} no valid voxels found!")


def adjacent_euclidean(coord, dist=2):
    """Returns a numpy array of adjacent coordinates to the given coordinate"""
    d = list(range(-math.floor(dist), math.ceil(dist) + 1))

    def condition(euclidean_dist):
        return euclidean_dist <= dist

    directions = [
        np.array([x, y, z]) for x in d for y in d for z in d if condition(np.sqrt(np.sum(np.power([x, y, z], 2))))
    ]
    return [coord + direction for direction in directions]
