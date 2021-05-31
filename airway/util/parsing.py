def parse_map_coord_to_distance(file_path):
    """Parses file of type "x, y, z: dist"

    Generally used for map_coord_to_distance.txt in stage-03

    Returns dict of tuples (x, y, z) with values of  dist
    """
    distances = {}
    with open(file_path, "r") as dist_file:
        for line in dist_file.read().split("\n"):
            if line != "":
                coord = tuple([int(a) for a in line.split(":")[0].split(",")])
                dist = int(line.split(":")[1])
                distances[coord] = dist
    return distances
