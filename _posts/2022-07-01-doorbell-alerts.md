---
title: Smart Doorbell Retrofit in Home Assistant
date: '2022-07-01 12:22'
comments: true
image:
  path: /assets/img/2022/07/banner.jpg
  height: 600
  width: 800
alt: Original doorbell to the house
published: true
tag: "small project"
description: "Retrofitting our existing doorbells to send useful alerts in Home Assistant when someone rings."
---

INTRO: 

- House hides loud noises and makes it hard to hear
- Doorbell isn't heard if things like TV are on

## Goals

- Maintain existing doorbell (fits our house better)
- Just like the chime, identify which doorbell is which
- Alerts on TV/phone so we know if we want to get up (salesperson with iPad), or if we're in a meeting

## Requirements

### Hardware

Here's a list of the hardware I use and the prices I bought them at. It should help give a good idea on how much everything costs.

- $35: 2x Shelly 1 (one for each doorbell)
- $15: Low voltage power supply (couldn't run it off of transformer)
- $10: Low voltage wire to power Shelly 1
- $20: (Optional) Waterproof junction box so wires weren't hanging everywhere

### Software

- [Home Assistant](https://www.home-assistant.io/) (I'm running the `2022.6` release at the time of writing)
- [ESPHome](https://esphome.io/)

## Setup

```yaml
#{% raw %}
# Your sensor ID will vary. I've put in a placeholder of 88888 below.
INSERT YAML HERE
#{% endraw %}
```

## Alerts for All

### TV Alerts

### Phone Alerts

## Extras

House alert if I want to get someone's attention. Not a great idea to use this a lot as I'm sure the doorbell transformer isn't meant for repeated use. But for super infrequent 30s bursts, it works great. 

```yaml
#{% raw %}
# Your sensor ID will vary. I've put in a placeholder of 88888 below.
INSERT ALARM YAML HERE
#{% endraw %}
```

## Final Thoughts

