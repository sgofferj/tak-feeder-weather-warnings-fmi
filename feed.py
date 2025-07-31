import os
import asyncio
import pytak
from configparser import ConfigParser
import func_fmi as fmi
import func_cot as cot
import class_api as api
import func_util as util
from datetime import timezone as tz

VERSION = "0.1"

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
TOKEN = os.getenv("MISSION_TOKEN", "")
FILTER_URGENCY = os.getenv("FILTER_URGENCY", "Expected,Immediate").split(",")
FILTER_EVENTCODE = os.getenv(
    "FILTER_EVENTCODE",
    "forestFireWeather,hotWeather,rain,seaThunderstorm,seaWind,thunderstorm,wind",
).split(",")


class sendWarnings(pytak.QueueWorker):

    async def handle_data(self, data):
        """Handle pre-CoT data, serialize to CoT Event, then puts on queue."""
        event = data
        await self.put_queue(event)

    async def run(self):
        """Weather warning loop"""
        self._logger.setLevel("DEBUG")
        while 1:
            self._logger.info("Getting mission from TAK server...")
            mstatus, mission = takserver.getMission(MISSION_NAME)
            if mstatus == 404:
                self._logger.info("Mission not found.")
            if mstatus == 200:
                self._logger.info("Mission found.")
                data = bytes()
                uids = []
                added = 0
                skipped = 0
                self._logger.info("Getting warning data...")
                caps = fmi.getCap(LANG)
                capList = fmi.cap2List(caps, LANG, FILTER_URGENCY, FILTER_EVENTCODE)
                self._logger.info("Updating mission...")
                missionUids = util.getUidsInMission(mission["data"][0]["uids"])

                for alert in capList:
                    alertDict = {
                        "color": alert["info"]["color"],
                        "event": alert["info"]["event"],
                        "headline": alert["info"]["headline"],
                        "description": alert["info"]["description"],
                        "start": alert["info"]["start"].astimezone(tz.utc),
                        "stale": alert["info"]["stale"].astimezone(tz.utc),
                    }
                    for area in alert["areas"]:
                        alertDict.update(
                            {
                                "uid": area["uid"],
                                "callsign": area["callsign"],
                                "areaDesc": area["areaDesc"],
                                "lat": area["lat"],
                                "lon": area["lon"],
                                "points": area["points"],
                            }
                        )
                        if area["uid"] in missionUids:
                            skipped += 1
                        else:
                            data = cot.cotFromDict(
                                MY_UID, alertDict, LANG, MISSION_NAME
                            )
                            # self._logger.info("%s", data.decode())
                            await self.handle_data(data)
                            uids.append(area["uid"])
                            added += 1
                if len(uids) > 0:
                    status, result = takserver.addMissionContent(
                        MISSION_NAME, uids, MY_UID, TOKEN
                    )
                    if status != 200:
                        self._logger.error("%s %s", status, result)
                self._logger.info(
                    "Update done. Total warnings available: %d, added: %d, skipped: %d."
                    % ((added + skipped), added, skipped)
                )
                await asyncio.sleep(
                    30
                )  # This delay is more for the benefits of clients. ATAK sometimes gets confused is mission changes happen to quickly.
                capUids = fmi.uidsInCap(capList)
                util.cleanupMission(
                    self, takserver, MY_UID, MISSION_NAME, mission, capUids, TOKEN
                )
                await asyncio.sleep(UPDATE_INTERVAL)
            else:
                self._logger.info(
                    "Could neither find nor create mission. Please check the configuration!"
                )


class sendKeepAlive(pytak.QueueWorker):

    async def handle_data(self, data):
        """Handle pre-CoT data, serialize to CoT Event, then puts on queue."""
        event = data
        await self.put_queue(event)

    async def run(self):
        """Keepalive loop, sends a cot for the FMI"""
        while 1:
            data = bytes()
            data = cot.keepAlive(MY_UID, LANG, VERSION)
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


async def main():
    config = ConfigParser()
    config["mycottool"] = {
        "COT_URL": COT_URL,
        "TAK_PROTO": "0",
        "PYTAK_TLS_CLIENT_CERT": CLIENT_CERT,
        "PYTAK_TLS_CLIENT_KEY": CLIENT_KEY,
        "PYTAK_TLS_DONT_VERIFY": PYTAK_TLS_DONT_VERIFY,
        "MAX_OUT_QUEUE": 1000,
    }
    config = config["mycottool"]

    clitool = pytak.CLITool(config)
    await clitool.setup()

    clitool.add_tasks(
        set(
            [
                sendKeepAlive(clitool.tx_queue, config),
                sendWarnings(clitool.tx_queue, config),
                MyReceiver(clitool.rx_queue, config),
            ]
        )
    )

    await clitool.run()


if __name__ == "__main__":
    takserver = api.server(API_HOST, CLIENT_CERT, CLIENT_KEY)

    status, mission = takserver.createMission(
        "testmission5",
        MY_UID,
        defaultrole="MISSION_READONLY_SUBSCRIBER",
        classification="unclassified",
    )
    print(status, mission)
    print()
    exit()

    if TOKEN == "":
        print("Trying to create subscription...")
        status, subscription = takserver.createMissionSubscription(MISSION_NAME, MY_UID)
        if status == 201:
            TOKEN = subscription["data"]["token"]
            role = subscription["data"]["role"]["type"]
            print(f"Subscription sucessful\nRole: {role}\ntoken: {TOKEN}")
        if status == 404:
            print("Mission does not exist, creating...")
            status, mission = takserver.createMission(
                MISSION_NAME,
                MY_UID,
                defaultrole="MISSION_READONLY_SUBSCRIBER",
                classification="unclassified",
            )
            if status < 400:
                TOKEN = mission["data"][0]["token"]
                print(f"Mission created, token: {TOKEN}")
            if status > 400:
                print("%s %s", status, mission)
                print("Can neither subscribe to nor create mission. Exiting...")
                exit()

    asyncio.run(main())
