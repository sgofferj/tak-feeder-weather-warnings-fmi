def getUidsInMission(cots):
    tmp_list = []
    for cot in cots:
        uid = cot["data"]
        tmp_list.append(uid)
    return tmp_list


def cleanupMission(takserver, MY_UID, missionName, mission, capUids):
    print("Misison cleanup")
    missionUids = getUidsInMission(mission["data"][0]["uids"])
    valid = 0
    deleted = 0
    for missionUid in missionUids:
        if missionUid in capUids:
            valid += 1
        else:
            takserver.removeMissionContent(missionName, missionUid, MY_UID)
            deleted += 1
    print("Cleanup done. Valid:%d, deleted:%d" % (valid, deleted))
