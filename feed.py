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
MY_UID = os.getenv("MY_UID", "fmi-0001-0001-0001-0001")
LANG = os.getenv("FMI_LANG", "en-GB")
API_HOST = os.getenv("API_HOST")
API_PORT = int(os.getenv("API_PORT", 8443))
MISSION = os.getenv("MISSION_NAME", "Weatherwarnings")
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
        """Run the loop for processing or generating pre-CoT data."""
        while 1:
            status, mission = takserver.getMission(MISSION)
            if status == 404:
                print("Mission does not exist, creating...")
                status, mission = takserver.createMission(
                    MISSION, MY_UID
                )
            if status == 200:
                print("Updating mission...")
                uids = []
                data = bytes()
                added = 0
                skipped = 0
                caps = fmi.getCap(LANG)
                capList = fmi.cap2List(caps, LANG, FILTER_URGENCY, FILTER_EVENTCODE)
                capUids = fmi.uidsInCap(capList)
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
                                "areaDesc": area["areaDesc"],
                                "points": area["points"],
                            }
                        )
                        if area["uid"] in missionUids:
                            skipped += 1
                        else:
                            data = cot.cotFromDict(MY_UID, alertDict, LANG, MISSION)
                            #self._logger.info("Sent:\n%s\n", data.decode())
                            await self.handle_data(data)
                            uids.append(area["uid"])
                            added += 1
                            print(alert["info"]["color"],alert["info"]["event"],area["areaDesc"],len(area["points"]))
                takserver.addMissionContent(MISSION, uids, MY_UID)
                print(
                    "Update done. Total warnings available: %d, added: %d, skipped: %d."
                    % ((added + skipped), added, skipped)
                )
                await asyncio.sleep(15)
                util.cleanupMission(takserver, MY_UID, MISSION, mission, capUids)
                await asyncio.sleep(UPDATE_INTERVAL)
            else:
                print(
                    "Could neither find nor create mission. Please check the configuration!"
                )


class sendKeepAlive(pytak.QueueWorker):

    async def handle_data(self, data):
        """Handle pre-CoT data, serialize to CoT Event, then puts on queue."""
        event = data
        await self.put_queue(event)

    async def run(self):
        """Run the loop for processing or generating pre-CoT data."""
        while 1:
            data = bytes()
            data = cot.keepAlive(MY_UID, LANG, VERSION, MISSION)
            # self._logger.info("Sent:\n%s\n", data.decode())
            await self.handle_data(data)
            await asyncio.sleep(30)


class cotReceiver(pytak.QueueWorker):
    """Defines how you will handle events from RX Queue."""

    async def handle_data(self, data):
        """Handle data from the receive queue."""
        rx = data.decode()
        if "b-t-f" in rx:
            self._logger.info("Received:\n%s\n", rx)

    async def run(self):
        """Read from the receive queue, put data onto handler."""
        while True:
            data = (
                await self.queue.get()
            )  # this is how we get the received CoT from rx_queue
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
                sendWarnings(clitool.tx_queue, config),
                sendKeepAlive(clitool.tx_queue, config),
                cotReceiver(clitool.rx_queue, config),
            ]
        )
    )

    await clitool.run()


if __name__ == "__main__":
    takserver = api.server(API_HOST, CLIENT_CERT, CLIENT_KEY)
    asyncio.run(main())
