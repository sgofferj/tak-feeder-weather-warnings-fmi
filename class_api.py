import requests as req

req.packages.urllib3.disable_warnings()


class server:
    """Takserver API helper class"""

    def __init__(self, host, cert, key):
        """Initialize a server instance."""
        self.crt = (cert, key)
        self.apiBaseURL = f"https://{host}:8443"

    def getMission(self, name):
        """Returns a mission"""
        path = f"/Marti/api/missions/{name}"
        url = self.apiBaseURL + path
        r = req.get(url, cert=self.crt, verify=False)
        if r.status_code != 200:
            return r.status_code, r.text
        else:
            return r.status_code, r.json()

    def getMissionRole(self, name):
        """Returns role in the mission"""
        path = f"/Marti/api/missions/{name}/role"
        url = self.apiBaseURL + path
        r = req.get(url, cert=self.crt, verify=False)
        if r.status_code != 200:
            return r.status_code, r.text
        else:
            return r.status_code, r.json()

    def getMissionSubscriptions(self, name):
        """Returns subscribtions to the mission"""
        path = f"/Marti/api/missions/{name}/subscriptions"
        url = self.apiBaseURL + path
        r = req.get(url, cert=self.crt, verify=False)
        if r.status_code != 200:
            return r.status_code, r.text
        else:
            return r.status_code, r.json()

    def getMissionSubscriptionRoles(self, name):
        """Returns subscribtions to the mission"""
        path = f"/Marti/api/missions/{name}/subscriptions/roles"
        url = self.apiBaseURL + path
        r = req.get(url, cert=self.crt, verify=False)
        if r.status_code != 200:
            return r.status_code, r.text
        else:
            return r.status_code, r.json()

    def createMission(
        self, name, creatorUid, group="", defaultrole="", classification=""
    ):
        """Creates a mission"""
        path = f"/Marti/api/missions/{name}?creatorUid={creatorUid}"
        if group != "":
            path += f"&group={group}"
        if defaultrole != "":
            path += f"&defaultRole={defaultrole}"
        if classification != "":
            path += f"&classification={classification}"
        url = self.apiBaseURL + path
        r = req.put(url, cert=self.crt, verify=False)
        if r.status_code != 200:
            return r.status_code, r.text
        else:
            return r.status_code, r.json()

    def setMissionRole(self, name, clientUid, userName, role):
        """Sets the role for a subscriber"""
        path = f"/Marti/api/missions/{name}/role"
        data = {"clientUid": clientUid, "username": userName, "role": role}
        url = self.apiBaseURL + path
        r = req.put(url, cert=self.crt, verify=False)
        if r.status_code != 200:
            return r.status_code, r.text
        else:
            return r.status_code, r.json()

    def addMissionContent(self, name, uids, MY_UID):
        path = f"/Marti/api/missions/{name}/contents?creatorUid={MY_UID}"
        url = self.apiBaseURL + path
        data = {"uids": uids}
        r = req.put(url, json=data, cert=self.crt, verify=False)
        if r.status_code != 200:
            return r.status_code, r.text
        else:
            return r.status_code, r.json()

    def removeMissionContent(self, name, uid, MY_UID):
        path = f"/Marti/api/missions/{name}/contents?creatorUid={MY_UID}&uid={uid}"
        url = self.apiBaseURL + path
        r = req.delete(url, cert=self.crt, verify=False)
        if r.status_code != 200:
            return r.status_code, r.text
        else:
            return r.status_code, r.json()
