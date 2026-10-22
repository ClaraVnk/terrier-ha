# Screenshots

Taken from a real Home Assistant 2026.10 driving a real Nabaztag:tag v2, not
mocked up. The only thing altered is the MAC address, replaced in the DOM
before the shutter — it is a real device identifier in somebody's house and
these pictures are in a public README.

| file | what it shows |
|---|---|
| `device.png` | the rabbit's device page: controls, sensors, and the link back to its warren |
| `dashboard.png` | a dashboard somebody would actually put on a wall tablet |
| `schedule.png` | the settings as entities — the morning weather, the alarm, night mode, personality |
| `integration.png` | one bridge, one device, 53 entities |
| `config-flow.png` | the setup dialog asking for a warren address and a token |

## How they were taken

Neither the Home Assistant nor the browser is installed anywhere permanent:
both are containers on a build machine, so this is repeatable by anyone with
a warren and a token.

```sh
podman network create shots
podman run -d --name ha-shots --network shots -p 8123:8123 \
  -v ./config:/config:Z ghcr.io/home-assistant/home-assistant:stable
# onboard through /api/onboarding/users, drop custom_components/terrier into
# ./config, restart, then add the integration through the config-flow API.
podman run --rm --network shots -v ./out:/out:Z -v ./shots.py:/shots.py:ro \
  -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
  mcr.microsoft.com/playwright/python:v1.49.0-noble \
  bash -lc "pip install -q playwright==1.49.0 && python /shots.py"
```

Two things worth knowing if you redo this:

**Set the language before the first setup, not after.** An entity's name is
resolved from the translations when it is first registered and stored in the
entity registry; changing the language afterwards leaves every name in the
old one. Delete the config entry, purge the registry, add it again.

**`entities.svg` is generated**, from `custom_components/terrier/settings.py`
and `icons.json`, so it cannot come to describe a version that no longer
exists. Regenerate it rather than editing it.
