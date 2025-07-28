import xml.etree.ElementTree as ET
from datetime import datetime as dt, timezone as tz, timedelta
import pytak


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


def cotFromDict(MY_UID, cot, LANG, MISSION):
    lat, lon = centroid(cot["points"])
    uid = cot["uid"]
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("type", "u-d-f")
    root.set("uid", uid)
    root.set("how", "h-e")
    root.set("time", pytak.cot_time())
    root.set("start", cot["start"].strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    root.set("stale", cot["stale"].strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    pt_attr = {
        "lat": str(lat),
        "lon": str(lon),
        "hae": "0",
        "ce": "9999999.0",
        "le": "9999999.0",
    }

    ET.SubElement(root, "point", attrib=pt_attr)

    callsign = cot["event"] + " " + cot["areaDesc"]
    contact = ET.Element("contact")
    contact.set("callsign", callsign)

    remarks = ET.Element("remarks")
    remarks.text = cot["description"]
    if LANG == "fi-FI":
        remarks.text += "\nSäävaroitukset: Ilmatieteenlaitos avoin data, CC-BY 4.0"
    elif LANG == "sv-FI":
        remarks.text += (
            "\nWeather warnings: Finnish Meteorological Institute open data, CC-BY 4.0"
        )
    elif LANG == "en-GB":
        remarks.text += (
            "\nWeather warnings: Finnish Meteorological Institute open data, CC-BY 4.0"
        )
    remarks.text += "\n#weather #warning"

    if LANG == "fi-FI":
        mycallsign = "Ilmatieteenlaitos"
    elif LANG == "sv-FI":
        mycallsign = "Meteorologiska institutet"
    elif LANG == "en-GB":
        mycallsign = "Finnish Meteorological Institute"

    creator = ET.Element("creator")
    creator.set("uid", MY_UID)
    creator.set("callsign", mycallsign)
    creator.set("type", "a-f-G-I-U-R")
    creator.set("time", cot["start"].strftime("%Y-%m-%dT%H:%M:%S.000Z"))

    argb = "-1"
    if cot["color"] == "yellow":
        argb = "1090518784"
    elif cot["color"] == "orange":
        argb = "1090483968"
    elif cot["color"] == "red":
        argb = "1090453504"

    color = ET.Element("color")
    color.set("value", argb)
    scolor = ET.Element("strokeColor")
    scolor.set("value", argb)
    sstyle = ET.Element("strokeStyle")
    sstyle.set("value", "solid")
    sweight = ET.Element("strokeWeight")
    sweight.set("value", "1")
    fcolor = ET.Element("fillColor")
    fcolor.set("value", argb)
    labels = ET.Element("labels_on")
    labels.set("value", "false")

    routing = ET.Element("marti")
    r_dest = ET.Element("dest")
    r_dest.set("mission", MISSION)
    routing.append(r_dest)

    archive = ET.Element("archive")
    detail = ET.Element("detail")

    detail.append(routing)
    detail.append(contact)
    for point in cot["points"]:
        e_point = ET.Element("link")
        e_point.set("point", point)
        detail.append(e_point)
    detail.append(remarks)
    detail.append(creator)
    detail.append(color)
    detail.append(labels)
    detail.append(archive)
    detail.append(scolor)
    detail.append(sweight)
    detail.append(sstyle)
    detail.append(fcolor)

    root.append(detail)

    return ET.tostring(root)


def keepAlive(uid, LANG, VERSION, MISSION):
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("type", "a-f-G-I-U-R")
    root.set("uid", uid)
    root.set("how", "h-e")
    root.set("time", pytak.cot_time())
    root.set("start", pytak.cot_time())
    root.set("stale", pytak.cot_time(3600))
    pt_attr = {
        "lat": "60.203748",
        "lon": "24.961131",
        "hae": "0",
        "ce": "0",
        "le": "0",
    }

    ET.SubElement(root, "point", attrib=pt_attr)

    if LANG == "fi-FI":
        callsign = "Ilmatieteenlaitos"
    elif LANG == "sv-FI":
        callsign = "Meteorologiska institutet"
    elif LANG == "en-GB":
        callsign = "Finnish Meteorological Institute"
    contact = ET.Element("contact")
    contact.set("callsign", callsign)
    # contact.set("endpoint", "*:-1:stcp") #Kept for future use
    contact.set("phone", "+358-29-539-1000")
    contact.set("emailAddress", "kirjaamo@fmi.fi")

    remarks = ET.Element("remarks")
    remarks.text = "#weather"

    e_uid = ET.Element("uid")
    e_uid.set("Droid", callsign)

    routing = ET.Element("marti")
    r_dest = ET.Element("dest")
    r_dest.set("mission", MISSION)
    routing.append(r_dest)

    archive = ET.Element("archive")
    detail = ET.Element("detail")

    detail.append(e_uid)
    # detail.append(routing)
    detail.append(contact)
    detail.append(remarks)
    detail.append(archive)

    root.append(detail)

    return ET.tostring(root)
