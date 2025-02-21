---
title: "Smart Coaster: Drink More Water"
date: '2025-02-21 8:00'
comments: true
image:
  path: /assets/img/2025/02/smart_coaster_00.jpg
  height: 602
  width: 800
alt: TODO
published: true
tag: "small project"
description: "TODO Make a smart coaster to remind me to drink more water."
amp:
  - video
---

Intro

Smart Coaster WIP

- Explain need
- Explain solution
- Video
- Explain how it works
- Include code
- Include automations
- Show permanent prototype


<details markdown="block">

<summary>[Yaml] ESPHome Configuration</summary>

```yaml
WIP:
```
</details>

<details markdown="block">

<summary>[Yaml] Home Assistant Action</summary>

```yaml
WIP:
```
</details>

{% include video.html
  src="/assets/files/2025/02/drink_water.mp4"
  poster="/assets/files/2025/02/drink_water_poster.png"
  controls="autoplay loop"
%}

I'm prototyping a smart coaster. But if we're being real, I'm just going to throw some glue on it, attach some rubber feet, and it's going to magically turn into temporarily permanent. 

Goal: remind me to drink water.

Reason: I often forget to drink water during the day (like all afternoon) when I get deep into coding or during really long meetings. (Attention issues) If I haven't removed my water bottle from the coaster after a set amount of time, I'll receive a notification on my devices and laptop to take a drink.

I originally thought about tracking the volume of liquid. I looked into load sensors, but those are so expensive and can be finicky if I change bottles/cups. Instead, I'm using a time of flight sensor. It shoots and laser and reads it back to determine the distance. In my case, if anything is close, I assume it's the water bottle. They're also super compact.

The timer is automatically kicked off during the workday (weekdays) at:
- 8:00 AM
- 1:00 PM
- Whenever my laptop screen turns on (assuming the timer is not already running)

If the timer runs out naturally:
- I get an alert
- The timer gets set back to 5 minutes (which will keep looping)

If I pick up the water bottle: 
- The timer gets reset to 45 minutes
- Any drink notifications on my devices get dismissed

Notifications will only be sent if the following conditions are met:
- When the timer runs out
- During normal working hours (excludes lunch hour)
- If I'm home
- If my laptop screen is on (which means I'm at my computer)
- If my global notification channel is on (added to every notification automation)
- If my "water bottle timer" notification channel is on

![ALT](/assets/img/2025/02/smart_coaster_00.jpg)*Caption*

Conclusion
