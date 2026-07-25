import os
import asyncio
from configparser import ConfigParser
from datetime import timezone as tz
from typing import Any

import pytak
from python_takserver_api import Server, build_mission_package  # type: ignore[attr-defined]

import func_fmi as fmi
import func_cot as cot
import func_util as util

VERSION = "0.1"

# pylint: disable=invalid-name
takserver: Any = None
# pylint: enable=invalid-name

COT_URL = os.getenv("COT_URL")
CLIENT_CERT = os.getenv("CLIENT_CERT")
CLIENT_KEY = os.getenv("CLIENT_KEY")
PYTAK_TLS_DONT_VERIFY = os.getenv("PYTAK_TLS_DONT_VERIFY", "1")
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "3600"))
MY_UID = os.getenv("MY_UID", "fmi.0001")
LANG = os.getenv("FMI_LANG", "en-GB")
API_HOST = os.getenv("API_HOST")
API_PORT = int(os.getenv("API_PORT", 8443))
MISSION_NAME = os.getenv("MISSION_NAME", "Weatherwarnings")
MISSION_GROUP = os.getenv("MISSION_GROUP", "")
token = os.getenv("MISSION_TOKEN", "")
FILTER_URGENCY = os.getenv("FILTER_URGENCY", "Expected,Immediate").split(",")
FILTER_EVENTCODE = os.getenv(
    "FILTER_EVENTCODE",
    "forestFireWeather,hotWeather,rain,seaThunderstorm,seaWind,thunderstorm,wind",
).split(",")

HEALTH_FILE = os.getenv("HEALTH_FILE", "/tmp/tak-feeder-healthy")
HEALTH_MAX_ERRORS = int(os.getenv("HEALTH_MAX_ERRORS", "3"))


def _report_health(ok: bool) -> None:
    """Write health status file. No file = healthy."""
    if ok:
        try:
            os.unlink(HEALTH_FILE)
        except FileNotFoundError:
            pass
    else:
        with open(HEALTH_FILE, "w") as f:
            f.write("unhealthy")


class SendWarnings(pytak.QueueWorker):
    async def handle_data(self, data):
        """No-op: CoTs delivered via mission package, not CoT stream."""

    async def run(self):
        """Weather warning loop"""
        self._logger.setLevel("DEBUG")
        global token
        consecutive_errors = 0
        while 1:
            self._logger.info("Getting mission from TAK server...")
            m_status, mission = await takserver.mission.get_mission(MISSION_NAME)
            if m_status == 404:
                status, new_mission = await takserver.mission.create_mission(
                    MISSION_NAME,
                    MY_UID,
                    group=MISSION_GROUP,
                    default_role="MISSION_READONLY_SUBSCRIBER",
                    classification="unclassified",
                )
                if status < 400:
                    token = new_mission["data"][0]["token"]
                    self._logger.info("Mission recreated, new token obtained.")
                    consecutive_errors = 0
                    _report_health(True)
                else:
                    self._logger.error(
                        "Failed to recreate mission: %s %s", status, new_mission
                    )
                    consecutive_errors += 1
            elif m_status == 200:
                self._logger.info("Mission found.")
                self._logger.info("Getting warning data...")
                caps = fmi.get_cap(LANG)
                cap_list = fmi.cap_to_list(caps, LANG, FILTER_URGENCY, FILTER_EVENTCODE)
                cap_uids = fmi.uids_in_cap(cap_list)
                mission_uids = set(util.get_uids_in_mission(mission["data"][0]["uids"]))

                # Remove stale UIDs that are no longer in the CAP feed
                stale_uids = mission_uids - set(cap_uids)
                for stale_uid in stale_uids:
                    self._logger.info("Removing stale content: %s", stale_uid)
                    s, r = await takserver.mission.remove_mission_content(
                        MISSION_NAME, stale_uid, MY_UID, token
                    )
                    if s != 200:
                        self._logger.error(
                            "Failed to remove %s: %s %s", stale_uid, s, r
                        )

                if set(cap_uids) == mission_uids:
                    self._logger.info("No changes detected, skipping package upload.")
                    consecutive_errors = 0
                    _report_health(True)
                else:
                    self._logger.info("Changes detected, building mission package...")
                    cot_files: dict[str, bytes | str] = {}
                    for alert in cap_list:
                        alert_dict = {
                            "color": alert["info"]["color"],
                            "event": alert["info"]["event"],
                            "headline": alert["info"]["headline"],
                            "description": alert["info"]["description"],
                            "start": alert["info"]["start"].astimezone(tz.utc),
                            "stale": alert["info"]["stale"].astimezone(tz.utc),
                        }
                        for area in alert["areas"]:
                            alert_dict.update(
                                {
                                    "uid": area["uid"],
                                    "callsign": area["callsign"],
                                    "areaDesc": area["areaDesc"],
                                    "lat": area["lat"],
                                    "lon": area["lon"],
                                    "points": area["points"],
                                }
                            )
                            cot_data = cot.cot_from_dict(
                                MY_UID, alert_dict, LANG, MISSION_NAME
                            )
                            cot_files[area["uid"]] = cot_data

                    mission_server = f"{API_HOST}:{API_PORT}:ssl"
                    pkg = build_mission_package(
                        name=MISSION_NAME,
                        mission_name=MISSION_NAME,
                        mission_server=mission_server,
                        creator_uid=MY_UID,
                        cot_files=cot_files,
                    )
                    self._logger.info(
                        "Uploading mission package with %d CoTs...", len(cot_files)
                    )
                    status, result = await takserver.mission.add_mission_package(
                        MISSION_NAME, MY_UID, token, pkg
                    )
                    if status != 200:
                        self._logger.error("%s %s", status, result)
                        consecutive_errors += 1
                    else:
                        self._logger.info("Mission package added successfully")
                        consecutive_errors = 0
                        _report_health(True)
                self._logger.info("Update done.")
                await asyncio.sleep(
                    30
                )  # This delay is more for the benefits of clients. ATAK sometimes gets confused is mission changes happen to quickly.
                await asyncio.sleep(UPDATE_INTERVAL)
            else:
                self._logger.info(
                    "Could neither find nor create mission. Please check the configuration!"
                )
                consecutive_errors += 1

            if consecutive_errors >= HEALTH_MAX_ERRORS:
                _report_health(False)


class SendKeepAlive(pytak.QueueWorker):

    async def handle_data(self, data):
        """Handle pre-CoT data, serialize to CoT Event, then puts on queue."""
        event = data
        await self.put_queue(event)

    async def run(self):
        """Keepalive loop, sends a cot for the FMI"""
        while 1:
            data = cot.keep_alive(MY_UID, LANG, VERSION)
            # self._logger.info("Sent:\n%s\n", data.decode())
            await self.handle_data(data)
            await asyncio.sleep(30)


class MyReceiver(pytak.QueueWorker):
    """Defines how you will handle events from RX Queue."""

    async def handle_data(self, data):
        """Handle data from the receive queue."""
        text = data.decode()
        if "t-x" in text:
            self._logger.info("Received:\n%s\n", text)

    async def run(self):
        """Read from the receive queue, put data onto handler."""
        while True:
            data = await self.queue.get()
            await self.handle_data(data)


async def async_main():
    global takserver
    global token
    takserver = Server(API_HOST, CLIENT_CERT, CLIENT_KEY)
    try:
        token_val = token
        if token_val == "":
            print("Trying to create subscription...")
            status, subscription = await takserver.mission.create_mission_subscription(
                MISSION_NAME, MY_UID
            )
            if status == 201:
                token = subscription["data"]["token"]
                role = subscription["data"]["role"]["type"]
                print(f"Subscription sucessful\nRole: {role}\ntoken: {token}")
            if status == 404:
                print("Mission does not exist, creating...")
                status, mission = await takserver.mission.create_mission(
                    MISSION_NAME,
                    MY_UID,
                    group=MISSION_GROUP,
                    default_role="MISSION_READONLY_SUBSCRIBER",
                    classification="unclassified",
                )
                if status < 400:
                    token = mission["data"][0]["token"]
                    print(f"Mission created, token: {token}")
                if status > 400:
                    print("%s %s", status, mission)
                    print("Can neither subscribe to nor create mission. Exiting...")
                    return

        config = ConfigParser()
        config["mycottool"] = {
            "COT_URL": COT_URL,
            "TAK_PROTO": "0",
            "PYTAK_TLS_CLIENT_CERT": CLIENT_CERT,
            "PYTAK_TLS_CLIENT_KEY": CLIENT_KEY,
            "PYTAK_TLS_DONT_VERIFY": PYTAK_TLS_DONT_VERIFY,
            "MAX_OUT_QUEUE": 1500,
        }
        config = config["mycottool"]

        clitool = pytak.CLITool(config)
        await clitool.setup()

        clitool.add_tasks(
            set(
                [
                    SendKeepAlive(clitool.tx_queue, config),
                    SendWarnings(clitool.tx_queue, config),
                    MyReceiver(clitool.rx_queue, config),
                ]
            )
        )

        await clitool.run()
    finally:
        await takserver.close()


if __name__ == "__main__":
    asyncio.run(async_main())
