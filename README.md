
[![Build and publish the container image](https://github.com/sgofferj/tak-feeder-weather-warnings-fmi/actions/workflows/actions.yml/badge.svg)](https://github.com/sgofferj/tak-feeder-weather-warnings-fmi/actions/workflows/actions.yml)

# tak-feeder-weather-warnings-fmi

(C) 2025 Stefan Gofferje

Licensed under the GNU General Public License V3 or later.

<strong style="color: red;">WARNING - STILL TESTING - DO NOT USE YET</strong>

## Description
The Finnish Meteorological Institute provides free API access to the weather data from their sensor network. This feeder gets
weather warning data from the Finnish Meteorological Institute, processes them and adds them to a TAK server mission. Outdated
warning areas are automatically removed from the mission.


## Notes
Because the feeder uses the mission API, the Datasync plugin is required on the client side. The EUDs should also be reasonably
new because depending on the filter configuration, the mission can contain A LOT (hundreds) of polygon objects which will bring
older EUDs quickly down to their knees.
For the same reason, this feeder can cause quite a lot of traffic. Be smart when configuring update UPDATE_INTERVAL and filters!

## Configuration
The following values are supported and can be provided either as environment variables or through an .env-file.

| Variable | Default | Use | Purpose |
|----------|---------|-----|---------|
| COT_URL | empty | mandatory | TAK server full URL, e.g. ssl://takserver:8089 |
| UPDATE_INTERVAL | 3600 | optional | Interval between data updates in seconds - how often should we get data? |
| CLIENT_CERT | empty | mandatory | User certificate in PEM format |
| CLIENT_KEY | empty | mandatory | User certificate key file in PEM format |
| API_HOST | empty | mandatory | host or IP for the TAK server API |
| API_PORT | 8443 | optional | TAK server API port |
| MY_UID | fmi-0001-0001-0001-0001 | optional | Sets the UID used by the feeder |
| LANG | en-GB | optional | Feed language to be fetched |
| MISSION | Weatherwarnings | optional | Name of the mission |
| FILTER_URGENCY | Expected,Immediate | optional | Case-sensitive, comma-separated list of urgency codes filter for. Available codes: Immediate, Expected, Future. |
| FILTER_EVENTCODE | forestFireWeather,hotWeather,rain,<br>seaThunderstorm,seaWind,<br>thunderstorm,wind | optional | Case-sensitive, comma-separated list of event codes to filter for. Default includes all known. |


## Certificates
These are the server-issued certificate and key files. Before using, the password needs to be removed from the key file with `openssl rsa -in cert.key -out cert-nopw.key`. OpenSSL will ask for the key password which usually is "atakatak".

## Container use
First, get your certificate and key and copy them to a suitable folder which needs to be added as a volume to the container.

### Image
The image is built for AMD64 and ARM64 and pushed to ghcr.io: *ghcr.io/sgofferj/tak-feeder-weather-warnings-fmi:latest*

### Docker compose
Here is an example for a docker-compose.yml file:
```
version: '2.0'

services:
  weather-fmi:
    image: ghcr.io/sgofferj/tak-feeder-weather-warnings-fmi:latest
    restart: always
    networks:
      - default
    volumes:
      - <path to data-directory>:/data:ro
    environment:
      - COT_URL=ssl://tak-server.domain.tld:8089
      - CLIENT_CERT=/data/cert.pem
      - CLIENT_KEY=/data/key.pem
      - API_HOST=takserver.domain.tld
networks:
  default:
