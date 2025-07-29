from io import StringIO
import xml.etree.ElementTree as ET
import requests as req
import hashlib
import uuid
from datetime import datetime as dt
import func_util as util

# req.packages.urllib3.disable_warnings()

uid_prefix = ""
dateformat = "%Y-%m-%dT%H:%M:%S%z"
special_char_map = {ord("ä"): "ae", ord("ü"): "ue", ord("ö"): "oe", ord("å"): "a"}


def getCap(lang):
    """Download the CAP XML and get rid of all namespaces"""
    url = f"https://alerts.fmi.fi/cap/feed/atom_{lang}.xml"
    r = req.get(url)
    it = ET.iterparse(StringIO(r.text))
    for _, el in it:
        _, _, el.tag = el.tag.rpartition("}")  # strip ns
    root = it.root
    return root


def cap2List(capxml, lang, filter_urgency, filter_eventcode):
    """Extract the relevant data from the CAP XML and create an object for further processing"""
    tmp_object = []
    for child in capxml.findall("entry"):
        published = child.find("published").text
        updated = child.find("updated").text
        alert = child.find("content").find("alert")
        identifier = alert.find("identifier").text
        identifier = "fmi-warning-" + identifier[8:]
        if alert.find("msgType").text != "Cancel":
            infos = alert.findall("info")
            tmp_infos = {}
            for info in infos:
                lng = info.find("language").text
                if lng == lang:
                    urgency = info.find("urgency").text
                    eventcode = info.find("eventCode").find("value").text
                    if (urgency in filter_urgency) and (eventcode in filter_eventcode):
                        event = info.find("event").text
                        onset = info.find("onset").text
                        expires = info.find("expires").text
                        headline = info.find("headline").text
                        description = info.find("description").text
                        parameters = info.findall("parameter")
                        for parameter in parameters:
                            if parameter.find("valueName").text == "color":
                                color = parameter.find("value").text
                        tmp_infos.update(
                            {
                                "event": event,
                                "eventcode": eventcode,
                                "color": color,
                                "headline": headline,
                                "description": description,
                                "published": dt.strptime(published, dateformat),
                                "updated": dt.strptime(updated, dateformat),
                                "start": dt.strptime(onset, dateformat),
                                "stale": dt.strptime(expires, dateformat),
                            }
                        )
                        areas = info.findall("area")
                        tmp_areas = []
                        for area in areas:
                            areaDesc = area.find("areaDesc").text
                            geocode = (
                                areaDesc.replace(" ", "_")
                                .lower()
                                .translate(special_char_map)
                            )
                            uid = identifier + "-" + geocode + "-" + updated
                            urnhash = hashlib.md5(uid.encode("UTF-8")).hexdigest()
                            uid = str(uuid.UUID(hex=urnhash))
                            uid = uid_prefix + uid
                            callsign = event + " " + areaDesc  # "WW." + urnhash
                            polygon = area.find("polygon").text
                            points = polygon.split(" ")
                            lat, lon = util.centroid(points)
                            lat = round(lat, 6)
                            lon = round(lon, 6)

                            tmp_areas.append(
                                {
                                    "uid": uid,
                                    "callsign": callsign,
                                    "areaDesc": areaDesc,
                                    "lat": lat,
                                    "lon": lon,
                                    "points": points,
                                }
                            )
                        tmp_object.append(
                            {"uid": identifier, "info": tmp_infos, "areas": tmp_areas}
                        )
    return tmp_object


def uidsInCap(capList):
    uids = []
    for alert in capList:
        for area in alert["areas"]:
            uid = area["uid"]
            uids.append(uid)
    return uids
