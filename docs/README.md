# Screenshots

The README has a gallery that needs four pictures. They have to come off a
real Home Assistant with a real rabbit paired, which is the one thing that
cannot be generated — a mocked-up Home Assistant screenshot would be a
picture of software that does not exist.

Drop them here under these exact names and the README picks them up:

| file | what to capture |
|---|---|
| `device.png` | the rabbit's device page: **Settings → Devices → Le Terrier → the rabbit**. The whole card, controls and sensors visible. |
| `dashboard.png` | a dashboard card with the belly light, the sleep switch, the counter and two or three sensors — what somebody would actually put on a wall tablet. |
| `services.png` | **Developer tools → Actions**, `terrier.notify` or `terrier.ask` picked, with the form expanded so the fields show. |
| `config-flow.png` | the setup dialog: **Settings → Devices & services → Add integration → Le Terrier**, with the URL and token fields. |

Light theme, browser zoom at 100%, and crop to the panel rather than the
whole screen. 1200 px wide or more; GitHub scales them down.

`entities.svg` is generated from `custom_components/terrier/settings.py` and
`icons.json` by the snippet in the pull request that added it — regenerate
it rather than editing it by hand, so it can never describe a version of the
integration that no longer exists.
