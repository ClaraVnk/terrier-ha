<p align="center">
  <img src="https://raw.githubusercontent.com/ClaraVnk/nabaztag/main/images/nabaztag.jpg" alt="Nabaztag" height="150">
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/ClaraVnk/nabaztag/main/images/home-assistant.png" alt="Home Assistant" height="48">
</p>

<h1 align="center">Le&nbsp;Terrier&nbsp;&nbsp;×&nbsp;&nbsp;Home&nbsp;Assistant</h1>

<p align="center">
  <strong>A 2006 Wi-Fi rabbit, as proper Home Assistant devices.</strong><br>
  <sub>Entities, not REST calls. Works against the hosted warren or one you run yourself.</sub>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-custom-41BDF5?style=flat-square&logo=home-assistant&logoColor=white" alt="HACS custom repository"></a>
  <a href="https://github.com/ClaraVnk/terrier-ha/releases"><img src="https://img.shields.io/github/v/release/ClaraVnk/terrier-ha?style=flat-square&color=41BDF5&display_name=tag&sort=semver" alt="Latest release"></a>
  <a href="https://github.com/ClaraVnk/terrier-ha/actions"><img src="https://img.shields.io/github/actions/workflow/status/ClaraVnk/terrier-ha/validate.yml?style=flat-square&label=checks" alt="Checks"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square" alt="License: Apache 2.0"></a>
  <img src="https://img.shields.io/badge/hardware-Nabaztag%3Atag%20v2-orange?style=flat-square" alt="Nabaztag:tag v2">
  <img src="https://img.shields.io/badge/protocol-Violet-6f42c1?style=flat-square" alt="Violet protocol">
  <img src="https://img.shields.io/badge/config-UI%20only-44cc11?style=flat-square" alt="UI configuration">
  <img src="https://img.shields.io/badge/dependencies-none-3776AB?style=flat-square&logo=python&logoColor=white" alt="No extra dependencies">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/breathes-live-success?style=flat-square" alt="breathes">
  <img src="https://img.shields.io/badge/speaks-live-success?style=flat-square" alt="speaks">
  <img src="https://img.shields.io/badge/belly%20%26%20nose-live-success?style=flat-square" alt="belly and nose">
  <img src="https://img.shields.io/badge/podcasts-live-success?style=flat-square" alt="podcasts">
  <img src="https://img.shields.io/badge/rabbit%20mail-live-success?style=flat-square" alt="rabbit to rabbit mail">
  <img src="https://img.shields.io/badge/push--to--talk-live-success?style=flat-square" alt="push to talk">
  <img src="https://img.shields.io/badge/asks%20a%20model-live-success?style=flat-square" alt="asks a model">
  <br><sub>every capability above verified against a real Nabaztag:tag&nbsp;v2 🐰</sub>
</p>

---

The **Nabaztag** is a Wi-Fi rabbit from 2005–2006 by Violet. It has ears that
turn, five belly LEDs, a nose, a speaker and a microphone, and it speaks a
protocol that nobody has run a server for since the company died around 2011.

**[Le Terrier](https://terrier.cyberloutre.fr)** is that server, brought back.
This integration is how Home Assistant talks to it.

> **Why not talk to the rabbit directly?** Because you cannot. The hardware
> speaks plain HTTP and XMPP from 2006 — no TLS, ever — and it expects a
> server to hold an open XMPP session and answer `violet:iq:sources` before it
> will accept a single command. A Terrier holds that session. This integration
> talks to the Terrier.

### 👀 What it looks like

<p align="center">
  <img src="docs/dashboard.png" alt="A dashboard with the nightlight, sleep, the morning weather and the schedule" width="860">
</p>
<p align="center">
  <img src="docs/device.png" alt="The rabbit's device page in Home Assistant: controls, sensors, and a link back to its warren" width="560">
  <img src="docs/schedule.png" alt="The rabbit's settings as entities: morning weather, alarm, night mode, personality" width="290">
</p>
<p align="center">
  <img src="docs/integration.png" alt="The integration page: one bridge, one device, 53 entities" width="500">
  <img src="docs/config-flow.png" alt="The setup dialog asking for a warren address and an API token" width="350">
</p>

<sub>A real Home Assistant against a real Nabaztag:tag&nbsp;v2 — only the MAC address is masked. Shown in French; the integration ships English and French.</sub>

### ✨ What you get

- 🐰 **One device per rabbit**, with its firmware version and serial where
  Home Assistant expects them
- 💡 **The belly as a light** — on, off, colour, brightness
- 🔴 **The nose, the ears and a counter** you can point at anything: parcels
  in transit, open tickets, days until the holidays
- 😴 **Sleep as a switch** — real hardware sleep, not a software mute
- ⏰ **Its whole schedule as entities** — morning weather, alarm, hourly
  chime, night mode, nightlight, daily podcast
- 🎚️ **Its settings as selects and numbers** — personality, speaking speed,
  nightlight colour and brightness
- 🗣️ **It speaks** — `terrier.speak`, `terrier.notify` (belly, nose, counter,
  jingle and a sentence in one call), radio, podcasts, jingles, and mail to
  other rabbits
- 🤖 **It answers** — `terrier.ask` puts a question to a model with your own
  key, and `terrier.listen` is push-to-talk: one sentence, transcribed,
  answered out loud
- 📊 **Diagnostics that explain a flaky rabbit** — availability, disconnects,
  session length, round-trip time

> **API keys are the one thing this cannot set.** Home Assistant would have to
> hold one to send it, and a key pasted into an automation ends up in a YAML
> backup. They stay on the warren's own settings page.

### 🗺️ What one rabbit becomes

<p align="center">
  <img src="docs/entities.svg" alt="One rabbit becomes one device, 8 sensors, 19 switches, 11 times, 8 selects, 3 numbers, a light, 3 buttons, a binary sensor and 14 services." width="860">
</p>

<sub>Most of the schedule entities ship disabled — enable the ones you want from the device page, rather than meeting thirty-seven at once.</sub>

### 📦 Install

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=ClaraVnk&repository=terrier-ha&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open this repository inside HACS."></a>
&nbsp;
<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=terrier"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Open your Home Assistant instance and start setting up a new integration."></a>

**Through HACS** (recommended)

1. HACS → ⋮ → **Custom repositories**
2. Repository: `https://github.com/ClaraVnk/terrier-ha` — Category: **Integration**
3. Install **Le Terrier (Nabaztag)**, then restart Home Assistant.
4. **Settings → Devices & services → Add integration → Le Terrier**

**By hand**

Copy `custom_components/terrier/` into your `config/custom_components/` and
restart.

### 🔑 Setting it up

You need two things, and the form asks for exactly those two:

| | |
|---|---|
| **Terrier address** | `https://terrier.cyberloutre.fr`, or your own instance |
| **API token** | From the Terrier's **Integration** page. Starts with `trr_`, shown once |

The token is checked before the entry is created — an integration that sets up
cleanly and then fails forever is worse than one that refuses at the door. If
the token is later revoked, Home Assistant asks for a new one rather than
going quiet.

### 🤖 Examples

Something arrived:

```yaml
action: terrier.notify
target:
  device_id: !input rabbit
data:
  colour: blue
  jingle: ears
  counter: 1
  text: "Un colis est arrivé."
```

Wake the house with the rabbit, not a buzzer:

```yaml
action: terrier.ears
target: { device_id: !input rabbit }
data: { left: 0, right: 0 }
```

Keep a parcel count on the nose, from anything:

```yaml
action: number.set_value
target: { entity_id: number.nabazprout_counter }
data: { value: "{{ states('sensor.parcels_in_transit') | int }}" }
```

> **No automation needed at all?** The Terrier also mints a plain URL that sets
> the counter — for anything that can call a URL but cannot send an
> authorization header. It is on the rabbit's page.

### 📝 Notes

#### Why the schedule is entities and not a settings page

Turning the morning weather on at 07:30 is the half of a rabbit an
automation most wants to reach, and until v0.2.0 it needed a browser. Most
of those entities ship disabled — enable the ones you want from the device
page, rather than meeting thirty-seven at once.

#### Why the nose has three states

The bytecode lights the nose violet from a count of waiting messages: one blink
at one, two blinks at two and above (`info.mtl:173`). The "nose" and the
"unread counter" are **one register on the hardware**, not two features — which
is also why setting the counter changes the nose, and why there is no digit
display anywhere on a Nabaztag.

#### Why the belly light has seven colours

Because the rabbit does. Exposing a full colour wheel would let Home Assistant
ask for a teal the hardware cannot produce; this snaps to the nearest real
colour and reports back what it actually used.

#### Why podcasts sometimes refuse an episode

The audio decoder is a **VS1003**: MP3, WMA, MIDI, WAV — and *not* AAC. Several
podcasts, Radio France among them, now serve `audio/mp4` exclusively. The
Terrier greys those out rather than streaming silence at you.

#### Availability

An entity stays **available** when the rabbit is unplugged. Its mood, its
counter and its schedule are still worth showing, and the diagnostics that
explain *why* it went away are exactly what you want at that moment. The
**Breathing** sensor is what tells you whether it is there.

### 🧩 The rest of the project

| | |
|---|---|
| [**ClaraVnk/nabaztag**](https://github.com/ClaraVnk/nabaztag) | The Home Assistant **add-on** (a fully local Violet server) and **Naboot**, the signed custom firmware |
| [**Le Terrier**](https://terrier.cyberloutre.fr) | The hosted warren — weather, alarm, air quality, podcasts, mail between rabbits |

Running your own Terrier keeps everything on your network and still gives you
this integration: it is the same API either way.

### 🤝 Contributing

Issues and pull requests are welcome, especially from anybody with a rabbit
and a network that misbehaves — that is where the interesting bugs live. If
you are reporting one, the **diagnostics** sensors are the useful thing to
include.

### 📄 Licence

Apache 2.0. Nabaztag and Violet are trademarks of their respective owners; this
project is not affiliated with them.
