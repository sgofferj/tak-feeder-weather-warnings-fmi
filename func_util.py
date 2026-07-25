def centroid(points):
    vertices = []
    for pts in points:
        lat, lon = pts.split(",")
        vertices.append((float(lat), float(lon)))

    x, y = 0, 0
    n = len(vertices)
    signed_area = 0
    for i in range(len(vertices)):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % n]
        # shoelace formula
        area = (x0 * y1) - (x1 * y0)
        signed_area += area
        x += (x0 + x1) * area
        y += (y0 + y1) * area
    signed_area *= 0.5
    x /= 6 * signed_area
    y /= 6 * signed_area
    return x, y


def get_uids_in_mission(cots):
    tmp_list = []
    for cot in cots:
        uid = cot["data"]
        tmp_list.append(uid)
    return tmp_list
