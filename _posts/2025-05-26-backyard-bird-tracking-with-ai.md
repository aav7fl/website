---
title: Backyard Bird Tracking With AI-Powered BirdNET-Go
date: '2025-05-26 21:58'
updated: '2025-10-16 12:00'
comments: true
image:
  path: /assets/img/2025/05/birdwatching_0.jpg
  height: 600
  width: 800
alt: Kyle looking through binoculars for birds at a lake on an early fall morning
published: true
tag: "large project"
description: "Turning security cameras into AI bird detectives! How I use BirdNET-Go & Home Assistant for 24/7 bird detections & alerts. Identify every chirp!"
amp:
  - video
---

How many different birds do you think visit your house each day? How many do you hear on your walks? Are there birds you remember hearing as a kid, but you couldn't remember how to identify them?

Back in early 2023, some of my friends introduced me to the board game, [Wingspan](https://boardgamegeek.com/boardgame/266192/wingspan). Before that, I hadn't thought about the diversity of bird species around me. Sure, I thought it was cool to see an owl or a hawk fly over. Occasionally I would use my phone to ID a bird sound. But I never dwelled on those thoughts for more than a few minutes. 

If you're unfamiliar, Wingspan is a resource management turn-based game. It heavily involves synergy between different bird species and their traits. It includes cards that contain information about a variety of bird species. Seriously, did you realize how many different species there are??

This awakened a new interest in me and I was hooked 🪝. I started to pay attention to the birds around me and was identifying bird sounds more frequently with the [Merlin app](https://merlin.allaboutbirds.org/) on my phone (highly recommended). 

There was an itch I wanted to scratch though. What if I were able to detect birds around my house _all of the time_? 

> Are you only here for the BirdNET-Go Home Assistant sensors and cards? Skip ahead to the [Home Assistant Sensors](#home-assistant-sensors) or the [Home Assistant Cards](#home-assistant-cards) sections below.

{% include toc.html %}

> Changelog:
> - 2025-06-04: Tweaked the `command_line` sensors to use `curl` retry logic for fewer Home Assistant warning logs.
> - 2025-07-09: Tweaked the `notify` conditions to filter out an `unavailable` `from_state` which could occur when manually reloading all template entities in Home Assistant.
> - 2025-08-28: Tweaked the "rare species" automation to skip sending an alert when the species list changes. This avoids an issue where timestamps are sometimes wrong when a new species is added to the list by the BirdNET-Go API.
> - 2025-09-02: Removed the `notify` condition after the 'race condition' was resolved via [tphakala/birdnet-go#1242](https://github.com/tphakala/birdnet-go/pull/1242).
> - 2025-10-16: Updated the `BirdNET Species Summary` command line sensor, `BirdNET Species Summary Persisted Data` template sensor, and `Notify rare bird detection` automation to work correctly. After dropping the attribute changes from history, the state detection changes were only being triggered when the species count increased. Instead, we now set the timestamp of the most recent change.

## Continuous Bird Detection

I thought it would be so cool if I could continuously record and detect all of the bird species around my house. This would provide additional information about which birds were in the area, and when I should look out for them.

My early research led me to a few projects that I could use. 

One of the first products I found was [Haikubox](https://haikubox.com/). It's a full hardware and software solution for detecting bird sounds around your house. It requires dedicated power and is a bit pricey. While their subscription cost for ongoing support and development is justified, I wasn't quite ready to open up my wallet.

(The original) [BirdNET-Pi](https://github.com/mcguirepr89/BirdNET-Pi) was another solution. When I first looked into this, BirdNET-Pi was a brand new project to run BirdNET on a Raspberry Pi. It would require my own waterproof hardware and microphone. If you're not aware, I _strongly prefer_ when my devices can operate without the internet as much as possible. This project instantly became a front-runner.

No matter the solution though, they all seemed to require dedicated power.

I didn't have an accessible outdoor outlet, so getting power to any device was going to take additional effort. I ended up making a soft plan for all of the hardware, trench placement,  conduit, wiring, and permit research. But in the end, life became too busy and I never got around to it.

Until...

A few years later, while pushing my kids on the swing, I heard a bird sound I didn't recognize. I quickly pulled out my phone and raced to open the Merlin app. But I was too slow and the bird flew away. I suddenly caught myself daydreaming of the continuous bird detections in BirdNET-Pi again. But that dream was immediately followed by the dread of figuring out when I could possibly complete an outdoor installation.

_The next day_, I was reading through a thread on Reddit discussing lesser-known integrations with Home Assistant. I came across [this golden reply](https://www.reddit.com/r/homeassistant/comments/1jiqumn/comment/mjh7y6i/) by [bkw_17](https://www.reddit.com/user/bkw_17/). They mentioned there was a newer BirdNET-based project that supported audio through an RTSP stream (a common way IP cameras stream video and audio). The project was called BirdNET-Go.

## The Perfect Solution: BirdNET-Go

![BirdNET-Go main dashboard](/assets/img/2025/05/birdnet-go_main_dashboard.png)*My main dashboard on BirdNET-Go*

[BirdNET-Go](https://github.com/tphakala/birdnet-go/) is a real-time BirdNET soundscape analyzer and classification tool for bird sounds. It is built on top of the work of the [BirdNET project](https://github.com/birdnet-team/BirdNET-Analyzer), and influenced by the original [BirdNET-Pi project](https://github.com/mcguirepr89/BirdNET-Pi).

BirdNET-Go includes a nice web interface for viewing detected birds, their frequencies, and playing back recordings. The project recently added an analytics dashboard in the nightly releases.

![BirdNET-Go analytics dashboard](/assets/img/2025/05/birdnet-go_analytics_dashboard.png)*My last 30 days of analytics in BirdNET-Go*

But the killer feature is that **BirdNET-Go can use the microphone audio from IP cameras**! BirdNET-Go accepts the [RTSP](https://en.wikipedia.org/wiki/Real-Time_Streaming_Protocol) stream from a network camera feed, splits out the audio, and uses that for detections. How had I never thought of this as a solution before?? I already have cameras outside, and they all have microphones. 🎤

Other than fidelity and detection accuracy, why would I need to use dedicated microphones in a new hardware box? It's not like I was going to be using this for a professional recording studio. **This is all a hobby** and I bet this does the job just fine.

So everything was set into motion. If this worked, I no longer needed to run additional wiring or purchase new hardware. I could tap into the existing cameras I already had.

![BirdNET-Go search dashboard](/assets/img/2025/05/birdnet-go_search_dashboard.png)*The search dashboard on BirdNET-Go shows some of my favorite locked detections*

## Did It Work?

Yeah, it did! In a little over an hour, I was able to deploy a BirdNET-Go container on my server, connect the cameras as an audio source, and start detecting birds at my house.

My setup uses a variety of Amcrest cameras, so your mileage may vary when it comes to audio configuration and quality.

But I have some tips if you're trying this at home on an existing camera.

### Tweak Camera Audio Settings

Almost immediately, I had issues with the camera audio sounding awful. I didn't realize it, but the default camera audio settings had a "Noise Suppression" feature enabled. This ended up removing a lot of the bird sounds from my recordings. Once I turned that feature off, it began to record more ambient sounds. 

Another tweak is that the default audio sampling frequency was far too low. It could barely provide usable bird audio. Increasing that from `8,000 Hz` to `48,000 Hz` did wonders for the audio quality.

I don't know what the exact specifications are for the microphone in my cameras, but they sound good enough for me. In fact, the specifications document for the camera lists the microphone information as "supported". 😆

I've included a few of my favorite recordings [toward the bottom of this post](#favorite-bird-recordings). 

### Wind Noise

Outdoor cameras positioned high up are prone to wind noise. I had a lot of wind noise in my early detection recordings, and the muffles made it painful to play back the clips.

What's the easiest way to fix this? I had known about action cameras and drones using windscreens over the microphones to help reduce wind noise. I figured that should easily apply to a stationary security camera microphone too.

I ended up going with the [Insta360 X4 Mic Wind Muff](https://www.amazon.com/dp/B0CYGGTJHY) because it was coming from a name-brand company, its adhesive velcro pad was much larger than its competitors, and the velcro pad cutout looked large enough to fit around my camera's microphone hole. It was only $9 for 6 of them. I had so little to lose and so much to gain.

![An Amcrest security camera with a black action-camera windscreen installed.](/assets/img/2025/05/camera_windscreen.jpg)*Outdoor Amcrest security camera with an "Insta360 X4 Mic Wind Muff" installed over the mic to reduce wind noise (above a 😮 face)*

Luckily, all of my cameras were out of direct rain and snow. This meant that I didn't have to worry about the foam getting wet and staying saturated.

After I installed it, I didn't know if it was working until I noticed some pretty faint wind chimes alongside a recording of an American Robin. But they weren't my wind chimes. Instead, they were from my neighbor's porch. 🤣 

I went into this only expecting a 50% reduction in wind noise. But this removed almost all but the _highest winds_, and even those were _significantly_ quieter. So yeah, this seems to work perfectly for any normal amount of wind. 

I've only had them installed for 2 months, so I'm not sure how well the adhesive will hold up over time. But so far, they're working significantly better than I anticipated.

## BirdNET-Go Usage

I've now been using BirdNET-Go for 2 months. My usage can be broken down into 2 primary categories:

### Educational

I have an activity with my 2-year-old where we scroll through yesterday's dashboard and try to name each bird (by its picture) and listen to their calls. This kid is like a sponge and he is getting shockingly good at recognizing birds by their appearance or calls. 🧽

Then as we go on our walks, we try to match what we've learned with what we see and hear. It's a fun way to spend time together and learn about the world around us. 

### Tracking

I use BirdNET-Go to track birds and to get a general idea about what's around my house. It has allowed me to be more aware of the birds that stick around and which ones are migrating through the area.

To support my tracking, I combine BirdNET-Go with a few automations set up in Home Assistant that notify me of certain conditions--like when specific species are detected. This encourages me to step outside, locate them, and cross them off of my "Species observed" list. 

_Huge_ shout out to [Tomi P. Hakala](https://github.com/tphakala) who built the BirdNET-Go software layer on top of the BirdNET project and [mcguirepr89](https://github.com/mcguirepr89) for his original BirdNET-Pi project. Without the work from either of those two developers (and countless others!), there is no chance I would have been able to get this project off the ground.

> Shameless plug; I've made a few [very minor contributions](https://github.com/tphakala/birdnet-go/pulls?q=is%3Apr+is%3Amerged+author%3Aaav7fl) to the BirdNET-Go project because I think it's so awesome, and I think you should too.

Let's dig into how I consume the data from BirdNET-Go, the cards I created in Home Assistant, and the automations to make it all work.

## Home Assistant Sensors

![An American Robin fledgling on the railing of a deck.](/assets/img/2025/05/amerob.jpg)*An American Robin fledgling on our back deck railing.*

> A lot of these sensors are dependent on using any release on or after [Nightly Build 20250427](https://github.com/tphakala/birdnet-go/releases/tag/nightly-20250427) which adds the analytics dashboard and my change to the BirdNET-Go API to return the species code in the daily summary API endpoint (used for the eBird links).

If it wasn't already clear, we're going to be using [Home Assistant](https://www.home-assistant.io/) to consume the data from BirdNET-Go and to send notifications to the user. Home Assistant is a great home automation platform that can be used to integrate with a variety of devices and services.

Here are two `command_line` sensors I created to pull data from the BirdNET-Go API and include the data in Home Assistant.

Each of the `command_line` sensors has a _matching_ `template` sensor. It is used to persist data even when the BirdNET-Go API isn't available (like when the machine first boots up). **This is important!** 

If the BirdNET-Go API is down, the `command_line` sensors will fail and the sensor will resolve to `unknown`. 

Normally this would not be a problem. But my notification automations work by comparing the previous and current state of each sensor. When the API comes back up, if the previous `command_line` sensor state was `unknown`, we will not be able to accurately compare the changes to _now_. This is most likely to occur when Home Assistant and BirdNET-Go are restarted on the host machine. 

We can work around these edge cases by persisting the data we last _knew_ about. I chose to do this by creating an additional `template` sensor for each `command_line` sensor and ignoring any `unknown` and `unavailable` states. The result is a `template` sensor that will always have the last _known_ state of the `command_line` sensor.

Below, I chose to only use the persisted_data `template` sensors in the _automations_, while continuing to use the non-persisted `command_line` sensors for the _dashboard cards_. I prefer that the dashboard cards always represent the current _live_ state from BirdNET-Go (even if it's not working). While on the other hand, the automations are all about comparing the current state with the last state _we knew about_.

**⚠️ NOTE:** Since the `template` sensor ignores `unknown` and `unavailable` states (which is what happens when Home Assistant starts), you'll likely need to wait for the first successful _change_ of the non-persisted `command_line` sensor **state** before the persisted_data `template` sensor will update and work correctly. If you're impatient, you can always force the `command_line` sensor `state` to change to _any other value_ in Home Assistant by using the [states tab](https://www.home-assistant.io/docs/tools/dev-tools/#states-tab) under the dev tools. Don't worry, it will always revert to the correct value when the `command_line` sensor updates again.

### Sensor for Daily Species Summary

This command line sensor fetches the _daily summary_ of bird species detected by BirdNET-Go using the `/api/v2/analytics/species/daily` endpoint. It uses `jq` to extract the `species_list`. The sensor's state is the count of unique species detected, and it stores the full list of species as an attribute.

<details markdown="block">

<summary>[Yaml] Home Assistant Sensor - Daily Summary</summary>

{% raw %}
```yaml
# configuration.yaml
command_line: !include command_line.yaml
template: !include template.yaml
```
{% endraw %}

{% raw %}
```yaml
# command_line.yaml
# version 1.1
- sensor:
    name: "BirdNET Daily Summary"
    unique_id: "birdnet_daily_summary"
    # Updated command uses jq to check input type and provide a default empty list
    command: >
      curl --connect-timeout 5 --max-time 10 --retry 3 --retry-delay 0 --retry-max-time 30 -s 'http://YOUR_BIRDNET_ENDPOINT:YOUR_BIRDNET_PORT/api/v2/analytics/species/daily' |
      jq 'if type == "array" then {species_list: .} end'
    value_template: >
      {% if value_json is defined and value_json.species_list is iterable and value_json.species_list is not string %}
        {{ value_json.species_list | length }}
      {% endif %}
    unit_of_measurement: "species"
    json_attributes:
      - species_list
    scan_interval: 60 # Or adjust as needed
    command_timeout: 35
```
{% endraw %}

> The specific `template` sensor below is **optional** as it's not used in any of my automations. However, I've included it as you may find it useful for writing your own automations that use the daily counts and frequencies.

{% raw %}
```yaml
# template.yaml
# version 1.0
# The data in this sensor won't be populated for the first time until the command_line sensor _changes_ to a _different_ state. This can be forced manually in the dev tools states tab.
- trigger:
   - platform: state
     entity_id: sensor.birdnet_daily_summary
     not_to:
       - unknown
       - unavailable
  sensor:
   - name: BirdNET Daily Summary Persisted Data
     unique_id: birdnet_daily_summary_persisted_data
     state: '{{ trigger.to_state.state }}'
     attributes:
       species_list: '{{ trigger.to_state.attributes.species_list }}'
     unit_of_measurement: "species"
```
{% endraw %}

</details>

### Sensor for Overall Species Summary

This command line sensor fetches the _overall species summary_ from BirdNET-Go using the `/api/v2/analytics/species/summary` endpoint. This means it gets the species summary for not only today but also when data was first recorded by BirdNET-Go. 

Just like the previous sensor, it uses `jq` to extract the `species_list`. The sensor's state is the count of unique species detected, and it stores the full list of species as an attribute.

<details markdown="block">

<summary>[Yaml] Home Assistant Sensor - Species Summary</summary>

{% raw %}
```yaml
# configuration.yaml
command_line: !include command_line.yaml
template: !include template.yaml
```
{% endraw %}

{% raw %}
```yaml
# command_line.yaml
# version 1.2
- sensor:
    name: "BirdNET Species Summary"
    unique_id: "birdnet_species_summary"
    # Uses jq to check input type and provide a default empty list
    command: >
      curl --connect-timeout 5 --max-time 10 --retry 3 --retry-delay 0 --retry-max-time 30 -s 'http://YOUR_BIRDNET_ENDPOINT:YOUR_BIRDNET_PORT/api/v2/analytics/species/summary' |
      jq 'if type == "array" then {species_list: .} end'
    # Value_template calculates the number of species in the list
    value_template: >
      {% if value_json is defined and value_json.species_list is iterable and (value_json.species_list | length) > 0 %}
        {{ (value_json.species_list | map(attribute='last_heard') | max | as_datetime | as_local) }}
      {% endif %}
    device_class: timestamp
    json_attributes:
      - species_list
    scan_interval: 60 # Or adjust as needed
    command_timeout: 25
```
{% endraw %}

{% raw %}
```yaml
# template.yaml
# version 1.1
# The data in this sensor won't be populated for the first time until the command_line sensor _changes_ to a _different_ state. This can be forced manually in the dev tools states tab.
- trigger:
   - platform: state
     entity_id: sensor.birdnet_species_summary
     not_to:
       - unknown
       - unavailable
  sensor:
   - name: BirdNET Species Summary Persisted Data
     unique_id: birdnet_species_summary_persisted_data
     state: '{{ trigger.to_state.state }}'
     attributes:
       species_list: '{{ trigger.to_state.attributes.species_list }}'
     device_class: timestamp
```
{% endraw %}

</details>

### Notes

Here are some additional notes and tips regarding the sensors and their configuration.

#### Recorder

If you have a large number of birds detected, you may run into issues where the attributes are too large to be reasonably recorded in the Home Assistant history database. You might get a log message like this:

```
State attributes for sensor.birdnet_* exceed maximum size of * bytes. 
This can cause database performance issues; Attributes will not be stored
```

The easiest solution is to exclude the sensors from being recorded in the database. In my testing, this still allowed the latest value to persist through a reboot while preventing history from being recorded. You can do this by adding the following to your `configuration.yaml` file:

```yaml
# configuration.yaml
# version 1.0
recorder:
  exclude:
    entities:
      - sensor.birdnet
      - sensor.birdnet_daily_summary
      - sensor.birdnet_daily_summary_persisted_data
      - sensor.birdnet_species_summary
      - sensor.birdnet_species_summary_persisted_data
```

#### Faster Responsiveness

In addition to the polling from the `command_line` sensors, you can also set up a simple automation that forces a new fetch from each of the endpoints by using the MQTT topic `birdnet` as a trigger. 

The only requirement is that you set up the MQTT integration in BirdNET-Go and have it publish to the same MQTT broker that Home Assistant is listening to.

We treat the incoming MQTT update like a push trigger to fetch updates for the `command_line` sensors before their next `scan_interval` starts. This cuts down on the time it takes to get updates for the sensors, and makes our notifications react as quickly as possible.

We don't care about the MQTT payload, instead, we only care if _something_ changes in BirdNET-Go. 

Below is a template sensor that listens to the BirdNET-Go MQTT topic.

<details markdown="block">

<summary>[Yaml] Home Assistant Sensor - BirdNET-Go MQTT</summary>

{% raw %}
```yaml
# configuration.yaml
template: !include template.yaml
```
{% endraw %}

{% raw %}
```yaml
# template.yaml
# version 1.0
- trigger:
    - platform: mqtt
      topic: birdnet
    # Reset at midnight to align with "a new daily summary"
    - platform: time_pattern
      hours: 0
      minutes: 0
      id: reset
  sensor:
    - name: BirdNET
      unique_id: birdnet
      state: >-
        {% if trigger.id == 'reset' %}
          unavailable
        {% elif trigger.payload_json is defined %}
          {{ today_at(trigger.payload_json.Time) }}
        {% else %}
          unknown
        {% endif %}
      icon: mdi:bird
```
{% endraw %}
</details>

Below is the automation portion which forces the `command_line` sensors to update each time the BirdNET-Go MQTT sensor changes.

<details markdown="block">

<summary>[Yaml] Home Assistant Automation - Command Line Sensor Manual Updates</summary>

<a href="https://my.home-assistant.io/redirect/automations/" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/automations.svg" alt="Open your Home Assistant instance and show your automations." style="margin-left: unset"/></a> <!-- https://my.home-assistant.io/create-link/ -->

{% raw %}
```yaml
# Automation
# version 1.0
alias: Trigger BirdNET-Go API fetch
description: ""
triggers:
  - trigger: state
    entity_id:
      - sensor.birdnet
conditions: []
actions:
  - parallel:
      - action: homeassistant.update_entity
        metadata: {}
        data:
          entity_id:
            - sensor.birdnet_daily_summary
      - action: homeassistant.update_entity
        metadata: {}
        data:
          entity_id:
            - sensor.birdnet_species_summary  
mode: queued
max: 5
```
{% endraw %}
</details>

## Home Assistant Cards

![A Ruby-throated Hummingbird eating from a hanging fuchsia basket](/assets/img/2025/05/rthhum.jpg)*A Ruby-throated Hummingbird visiting our fuchsia basket.*

Below I've created a few `markdown` cards in Home Assistant to display the data from the BirdNET-Go sensors. I liked having all the information in one place and using markdown tables was the quickest way to get something out there.

Could there be improvements or optimizations to these Home Assistant dashboard cards below? Absolutely. But unless you're running on a [Zilog Z80](https://en.wikipedia.org/wiki/TI-84_Plus_series), I don't think you're going to notice a faster loop speed in a home setting. I won't let perfection be the enemy of good enough.

### Card: Daily Species Summary With Sparklines

![Home Assistant dashboard showing today's BirdNET detections frequencies being represented by a sparkline chart](/assets/img/2025/05/home_assistant_birdnet_sparkline_card.png)*Today's BirdNET detections and frequencies are represented by a sparkline chart*

> Requires: [Sensor for Daily Species Summary](#sensor-for-daily-species-summary)

This is my favorite card and the one I find myself looking at the most. This card closely matches what one would find on their BirdNET-Go dashboard. It shows today's detected species, their overall count, and a fun sparkline chart that represents the frequency of detections throughout the day.

I first got the idea for the sparklines from this [GitHub issue](https://github.com/tphakala/birdnet-go/issues/587) where someone wanted to add them to the daily summary dashboard in _BirdNET-Go_. Thanks!

Since there isn't an easy way to fit a full sparkline chart on mobile in the markdown card, I decided to "combine" all the counts from the quietest hours into a single bar. 

- `Bar 1` = Combined counts from 12:00 AM - 06:00 AM
- `Bar 2..13` = Hourly counts from 06:00 AM - 06:00 PM
- `Bar 14` = Combined counts from 06:00 PM - 12:00 AM

An alternative idea would be to combine every 2 hours into a bar, giving an even distribution of data. However as most of my data was during the daytime, I decided to keep the precision from 06:00 AM - 06:00 PM.

I also included another idea from [Alexandre](https://community.home-assistant.io/t/displaying-birdnet-go-detections/713611/24) who suggested using the species code from BirdNET-Go and linking to the eBird website with it. 👏 This way you can quickly look up the species and see more information about them from your dashboard card. 

<details markdown="block">

<summary>[Yaml] Home Assistant Card - Daily Summary with Sparklines</summary>

{% raw %}
```yaml
# version 1.0
type: markdown
content: >-
  {% if has_value('sensor.birdnet_daily_summary') %}  

  {% set species_data = state_attr('sensor.birdnet_daily_summary',
  'species_list') %}

  {% if species_data and species_data | count > 0 %}

  Last Heard | Species | Count | Sparkline (6AM-6PM)

  :-- | :-- | :-- | --

  {% for bird in species_data | sort(attribute='latest_heard', reverse=true) |
  sort(attribute='count', reverse=true) %}

  {#- Basic Info -#}

  {%- set time = bird.latest_heard -%}

  {%- set name = bird.common_name -%}

  {%- set count = bird.count -%}

  {%- set species_code = bird.species_code %}

  {%- set ebird_url = "https://ebird.org/species/" ~ species_code %}

  {#--- Sparkline Calculation (Full Day Aggregated - 14 slots) ---#}

  {%- set hourly = bird.hourly_counts -%}

  {%- set sparkline_str = "N/A" -%} {#- Default value -#}

  {%- if hourly is defined and hourly is iterable and hourly | count == 24 -%}
    {#- Aggregate counts: [0-6], 6..18, [18-24] (14 slots total, safe concatenation) -#}
    {%- set early_sum = hourly[0:6] | sum -%}
    {%- set middle_part = hourly[6:18] -%}
    {%- set late_sum = hourly[18:24] | sum -%}
    {%- set aggregated_counts = [early_sum] + middle_part + [late_sum] -%}

    {# Check if list has expected count before finding max #}
    {%- if aggregated_counts | count == 14 -%}
      {#- Find Max for Scaling -#}
      {%- set max_val = aggregated_counts | max -%}

      {#- Define Sparkline Characters (7 levels, U+2581 to U+2587) -#}
      {%- set spark_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇'] -%}
      {%- set sparkline = namespace(text="") -%}

      {%- for v in aggregated_counts -%}
        {#- Map value to character index (0-6), scale factor 7, max index 6 -#}
        {%- set char_index = ([0, (v * 7 / max_val)|int , 6] | sort)[1] if max_val > 0 else 0 -%} {#<-- 2. Use 7 levels for scaling/clamping #}
        {#- Append character -#}
        {%- set sparkline.text = sparkline.text ~ spark_chars[char_index] -%}
      {%- endfor -%}
      {%- set sparkline_str = sparkline.text -%}
    {%- else -%}
       {% set sparkline_str = "?" * 12 %}
    {%- endif -%}
  {%- endif -%}

  {#--- End Sparkline Calculation ---#}


  {#- Output Row -#}

  {{ today_at(time) | as_timestamp  | timestamp_custom('%H:%M', true)}} | [{{
  name }}]({{ ebird_url }}) | {{ count }} | {{ sparkline_str }}

  {% endfor %}


  ---

  {{ species_data | sum(attribute='count') | int }} Detections

  {{ species_data | count }} Species

  {% else %}

  No bird species data available or list is empty.

  {% endif %}

  {% else %}

  BirdNET-Go API is not available.

  {% endif %}
```
{% endraw %}

</details>

### Card: Latest Species Detections

![Home Assistant dashboard showing BirdNET's the most recent species detected](/assets/img/2025/05/home_assistant_birdnet_latest_detections.png)*BirdNET's latest species detections sorted by most recent*

> Requires: [Sensor for Overall Species Summary](#sensor-for-overall-species-summary)

It's a fun problem to have, but sometimes it's challenging to scan through the daily detection summary to see what the most recent detections are. This card solves that problem by showing the most recent detections in a simple markdown table sorted by the last heard time in a human-readable format.

Unlike the daily summary card, this card does not reset after midnight. It's helpful for scanning for detected birds from the prior night.

<details markdown="block">

<summary>[Yaml] Home Assistant Card - Latest Detections</summary>

{% raw %}
```yaml
# version 1.0
type: markdown
content: >-
  {% if has_value('sensor.birdnet_species_summary') %}  
  {% set species_data = state_attr('sensor.birdnet_species_summary', 'species_list') %} 
  {% if species_data and species_data | count > 0 %}
    Latest Detections | &nbsp;&nbsp;&nbsp;Last Heard 
    :-- | :-- 
    {% for bird in (species_data | sort(attribute='last_heard', reverse=true))[0:11] %}
      {%- set time = bird.last_heard -%}
      {%- set name = bird.common_name -%}
      {%- set species_code = bird.species_code %}
      {%- set ebird_url = "https://ebird.org/species/" ~ species_code %}
      {%- set last_heard_datetime = strptime(time, '%Y-%m-%d %H:%M:%S') %}[{{ name }}]({{ ebird_url }}) | &nbsp;&nbsp;&nbsp;{{ relative_time(last_heard_datetime) }} ago 
    {% endfor %}
  {% else %} 
    No recent bird data available. 
  {% endif %}
  {% else %}
    BirdNET-Go API is not available.
  {% endif %}
```
{% endraw %}

</details>

### Card: Birds of Interest

![Home Assistant dashboard showing a filtered list of birds I'm interested in tracking](/assets/img/2025/05/home_assistant_birdnet_birds_of_interest.png)*A filtered list of birds I'm interested in tracking*

> Requires: [Sensor for Overall Species Summary](#sensor-for-overall-species-summary)

While the two summary cards have been great, I also found myself searching the card for birds I was interested in keeping an eye out for. To solve this problem, I created _another_ card that takes in a case-*insensitive* list of birds and matches their common name with the list in the species summary sensor. 

This is helpful for birds I might not see every day, but I want to know when they're back in the area without opening up the BirdNET-Go dashboard and flipping through the last few days.

It's a pretty manual process to add the birds to the list, but I change this so infrequently that it wasn't worth the effort to engineer any further.

<details markdown="block">

<summary>[Yaml] Home Assistant Card - Birds of Interest</summary>

{% raw %}
```yaml
# version 1.0
type: markdown
content: >-
  {% if has_value('sensor.birdnet_species_summary') %}  
  {% set birds_of_interest = [
    'white-crowned sparrow',
    'baltimore oriole',
    'black-capped chickadee',
    'tufted titmouse',
    'osprey',
    'yellow-rumped warbler',
    'nashville warbler',
    '',
    '',
    '',
    ''] %} 
  {% set birds_pattern = '(?i)^(' ~ birds_of_interest | join('|') ~ ')$' %}
  {% set species_data_all = state_attr('sensor.birdnet_species_summary', 'species_list') %}
  {% set species_data_filtered = [] %} 
  {% if species_data_all %}
    {% set species_data_filtered = species_data_all | selectattr('common_name', 'match', birds_pattern) | list %} 
  {% endif %} 
  {% if species_data_filtered and species_data_filtered | count > 0 %}
    Latest Detections | &nbsp;&nbsp;&nbsp;Last Heard
    :-- | :-- 
    {% for bird in (species_data_filtered | sort(attribute='last_heard', reverse=true)) %}
      {%- set time = bird.last_heard -%}   
      {%- set name = bird.common_name -%}   
      {%- set species_code = bird.species_code %}   
      {%- set ebird_url = "https://ebird.org/species/" ~ species_code %}   
      {%- set last_heard_datetime = strptime(time, '%Y-%m-%d %H:%M:%S') %}[{{ name }}]({{ ebird_url }}) | &nbsp;&nbsp;&nbsp;{{ relative_time(last_heard_datetime) }} ago 
    {% endfor %}
  {% else %} 
    No recent detections of specified birds. 
  {% endif %}
  {% else %}
    BirdNET-Go API is not available.
  {% endif %}
```
{% endraw %}

</details>

### Card: Brand New Detections

![Home Assistant dashboard showing BirdNET's birds that have been detected for the first time](/assets/img/2025/05/home_assistant_birdnet_newest_birds.png)*A list of birds that have been detected for the very first time*

> Requires: [Sensor for Overall Species Summary](#sensor-for-overall-species-summary)

Last, this fun card shows the birds that have been detected for the very first time. This is a great way to see what _new_ birds are in the area and if I should be on the lookout for them. 

_However_, once a bird makes this list and rolls off, it will never be on this list again. So it is a bit of a one-time use card, but still fun to track as I'm new to birding this year.

<details markdown="block">

<summary>[Yaml] Home Assistant Card - Brand New Detections</summary>

{% raw %}
```yaml
# version 1.0
type: markdown
content: >-
  {% if has_value('sensor.birdnet_species_summary') %}  
  {% set species_data = state_attr('sensor.birdnet_species_summary', 'species_list') %} 
  {% if species_data and species_data | count > 0 %}
    Latest Detections | &nbsp;&nbsp;&nbsp;Count | &nbsp;&nbsp;&nbsp;First Heard 
    :-- | :-- | :--
    {% for bird in (species_data | sort(attribute='first_heard', reverse=true))[0:11] %}
      {%- set time = bird.first_heard -%}
      {%- set name = bird.common_name -%}
      {%- set count = bird.count -%}
      {%- set species_code = bird.species_code %}
      {%- set ebird_url = "https://ebird.org/species/" ~ species_code %}
      {%- set first_heard_datetime = strptime(time, '%Y-%m-%d %H:%M:%S') %}[{{ name }}]({{ ebird_url }}) | &nbsp;&nbsp;&nbsp;{{ count }} | &nbsp;&nbsp;&nbsp;{{ relative_time(first_heard_datetime) }} ago 
    {% endfor %}
  {% else %} 
    No recent bird data available. 
  {% endif %}
  {% else %}
    BirdNET-Go API is not available.
  {% endif %}
```
{% endraw %}

</details>

## Notifications

![A Pileated Woodpecker searching for food in a dead tree.](/assets/img/2025/05/pilwoo.jpg)*A Pileated Woodpecker pecking away at a dead tree in my backyard.*

Here is where the fun begins. Below are my collections of notifications that I've set up in Home Assistant based on the created sensors above. 

I've simplified some of the notifications from my personal setup. But here are some ideas that you could implement on your own:

- Only send notifications when you're home
- Only send notifications when you're not working or sleeping
- Add a separate notification channel or webhooks for your spouse or family members (allowing for different conditions)
- Add a notification cooldown timer to prevent spamming (demonstrated below)
- Add a [custom notification sound](https://companion.home-assistant.io/docs/notifications/notification-sounds/) like this one (⚠️ Light _Severance_ Spoiler!):
  - [Bird.wav 🔊](/assets/files/2025/05/Bird.wav) 
  - [Bird.ogg 🔊](/assets/files/2025/05/Bird.ogg) 

### Notify for Custom Species Detection

This first automation is a simple one that notifies me when a specific bird species is detected. 

In BirdNET-Go, you can set up custom actions to run when a specific bird species is detected. I leverage this feature to execute a custom script. My script sends the detection information from BirdNET-Go to Home Assistant via a webhook.

On the Home Assistant side, I have an automation triggered by this webhook. It parses the incoming data payload and sends a notification to my phone.

By leveraging the custom species action in BirdNET-Go, I can get better real-time push notifications for specific bird species without polling the API and checking for changes. Although, I _am_ already doing that for some of the cards... 🤷‍♂️ but I wrote this one first.

#### Custom Action in BirdNET-Go

This is the custom action that BirdNET-Go will execute when a specific bird species is detected.

Whenever you want to get notified for a bird detection, add a custom action under the `Settings > Species` in BirdNET-Go that points to the script below. Then match it with the Home Assistant notification automation's webhook further down.

Make sure to include the `CommonName`, `Confidence`, `Time`, and `Source` parameters in the custom action (any order will do).

> Note: I've found that I need to restart my BirdNET-Go instance whenever I change the species settings (like adding a custom action).

![BirdNET-Go Custom Action for the White-crowned Sparrow](/assets/img/2025/05/birdnet-go-custom-action.png)*BirdNET-Go Custom Action for the White-crowned Sparrow*

<details markdown="block">

<summary>[Shell script] BirdNET-Go Custom Action (notify Home Assistant)</summary>

{% raw %}
```bash
#!/bin/bash
# version 1.0

# === Debug: Log Raw Input Arguments ===
echo "--- Raw Script Arguments Received ---" >&2
arg_count=0
for raw_arg in "$@"; do
  arg_count=$((arg_count + 1))
  echo "Arg ${arg_count}: ${raw_arg}" >&2 # Print each argument exactly as received
done
echo "Total arguments received: ${arg_count}" >&2
echo "-------------------------------------" >&2
# === End Debug ===


# === Configuration ===
HA_WEBHOOK_URL="http://HOME_ASSISTANT_URL:8123/api/webhook/notify-bird-detection-123456789" # Replace with your actual webhook URL

# === Argument Parsing ===
# Initialize variables to store argument values
COMMON_NAME_VAL=""
CONFIDENCE_VAL=""
SOURCE_VAL=""
TIME_VAL=""
MISSING_ARGS="" # Keep track of missing arguments

# Loop through all provided arguments
for arg in "$@"; do
  case $arg in
    --CommonName=*)
      COMMON_NAME_VAL="${arg#*=}" # Extract value after '='
      # *** BUG FIX: Remove potential surrounding quotes from the value ***
      COMMON_NAME_VAL=$(echo "$COMMON_NAME_VAL" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
      ;;
    --Confidence=*)
      CONFIDENCE_VAL="${arg#*=}"
      # Optional: Remove quotes if confidence could ever be quoted
      # CONFIDENCE_VAL=$(echo "$CONFIDENCE_VAL" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
      ;;
    --Source=*)
      SOURCE_VAL="${arg#*=}"
      # Optional: Remove quotes if source could ever be quoted
      # SOURCE_VAL=$(echo "$SOURCE_VAL" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
      ;;
    --Time=*)
      TIME_VAL="${arg#*=}"
      # Optional: Remove quotes if time could ever be quoted
      # TIME_VAL=$(echo "$TIME_VAL" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
      ;;
    *)
      echo "WARNING: Ignoring unrecognized argument: $arg" >&2
      ;;
  esac
done

# === Validation ===
# Check if all required arguments were found
if [ -z "$COMMON_NAME_VAL" ]; then MISSING_ARGS="${MISSING_ARGS} --CommonName"; fi
if [ -z "$CONFIDENCE_VAL" ]; then MISSING_ARGS="${MISSING_ARGS} --Confidence"; fi
if [ -z "$SOURCE_VAL" ]; then MISSING_ARGS="${MISSING_ARGS} --Source"; fi
if [ -z "$TIME_VAL" ]; then MISSING_ARGS="${MISSING_ARGS} --Time"; fi

# If any arguments are missing...
if [ -n "$MISSING_ARGS" ]; then
    # --- Debug Fallback ---
    ERROR_REASON="Missing required arguments"
    echo "ERROR: ${ERROR_REASON}: ${MISSING_ARGS}" >&2

    # Construct a debug JSON payload for Home Assistant
    DEBUG_JSON=$(printf '{"type": "script_error", "reason": "%s", "missing_args": "%s"}' \
        "$ERROR_REASON" \
        "${MISSING_ARGS# }" ) # Remove leading space from MISSING_ARGS

    echo "Sending error details to Home Assistant webhook..." >&2

    # Attempt to send the error notification via curl to the HA webhook
    curl --silent --show-error --fail \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$DEBUG_JSON" \
        "${HA_WEBHOOK_URL}"

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to send *debug* JSON to Home Assistant webhook." >&2
        # Even if sending debug fails, we continue to exit 0 below
    fi

    # Print standard usage instructions to console for the user
    echo "Usage: $0 --Time=\"<value>\" --CommonName=\"<value>\" --Confidence=\"<value>\" --Source=\"<value>\""
    echo "Arguments can be in any order."
    echo "Example: $0 --Time=\"07:53:30\" --CommonName=\"White-crowned Sparrow\" --Confidence=\"0.54\" --Source=\"rtsp://user@10.0.0.1/stream\""

    # Exit with a success status code, even though curl failed, that way nothing downstream breaks
    echo "Exiting with status 0 despite missing arguments." >&2
    exit 0
fi

# === Normal Operation (if all arguments are present) ===

# --- Source Mapping ---
# Use a temporary variable for the source before mapping
# This remaps and source that contains the IP and replaces the entire source with a friendly name
SOURCE_MAPPED="$SOURCE_VAL"
# Check if the source value CONTAINS a known IP using pattern matching (*)
case "$SOURCE_VAL" in
    *"10.0.0.1"*) SOURCE_MAPPED="Pool Camera" ;;
    *"10.0.0.2"*) SOURCE_MAPPED="Tree Camera" ;;
    *"10.0.0.3"*) SOURCE_MAPPED="Spy Camera" ;;
esac
# --- End Source Mapping ---

# --- Confidence Formatting ---
# Convert decimal confidence to percentage string
CONFIDENCE_DISPLAY=$(awk -v conf="$CONFIDENCE_VAL" 'BEGIN { printf "%.0f%%", conf * 100 }')
# --- End Confidence Formatting ---

# === JSON Construction ===
# Create the JSON payload for Home Assistant
JSON_PAYLOAD=$(printf '{"type": "bird_detection", "time": "%s", "common_name": "%s", "confidence_pct": "%s", "confidence_raw": "%s", "source_camera": "%s"}' \
    "$TIME_VAL" \
    "$COMMON_NAME_VAL" \
    "$CONFIDENCE_DISPLAY" \
    "$CONFIDENCE_VAL" \
    "$SOURCE_MAPPED" )

# === Send Data to Home Assistant ===
echo "Sending data to Home Assistant webhook..."

# --- Debug: Show Final Values Before Sending ---
echo "--- Values used in JSON ---" >&2
echo "Time:           $TIME_VAL" >&2
echo "Common Name:    $COMMON_NAME_VAL" >&2
echo "Confidence Pct: $CONFIDENCE_DISPLAY" >&2
echo "Confidence Raw: $CONFIDENCE_VAL" >&2
echo "Source Mapped:  $SOURCE_MAPPED" >&2
echo "---------------------------" >&2
echo "JSON Payload: $JSON_PAYLOAD" # Print the final JSON
# --- End Debug ---


# Use curl to send the JSON payload via POST
curl --silent --show-error --fail \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD" \
    "${HA_WEBHOOK_URL}"

# === Check Result ===
CURL_EXIT_CODE=$? # Capture the exit code of curl
if [ $CURL_EXIT_CODE -eq 0 ]; then
    echo "Data sent successfully to Home Assistant webhook."
    exit 0 # Success exit code
else
    echo "ERROR: Failed to send data to Home Assistant webhook (curl exit code: $CURL_EXIT_CODE)." >&2
    # Exit with a success status code, even though curl failed, that way nothing downstream breaks
    echo "Exiting with status 0 despite webhook send failure." >&2
    exit 0
fi
```
{% endraw %}
</details>

#### Notification: For A Bird Triggered by BirdNET-Go Script

![Home Assistant notification showing a notification for a detection of a tracked bird](/assets/img/2025/05/home_assistant_notification_tracked_bird_detected.png)*Home Assistant notification for the detection of a tracked bird*

This is the code for the Home Assistant automation that listens for the webhook from BirdNET-Go and sends a notification to my phone.

For the automation below, I created a timer to prevent multiple notifications from being sent in a short period. I personally use a 15-minute cooldown between new notifications _unless_ I press the `Reset` button in the notification. That button will trigger a reset of the notification cooldown timer.

This is useful if you have multiple cameras and they all detect the same bird at the same time, or if you want to get an additional notification while you're trying to spot the bird with your binoculars up.

If you want to include the timer:
- Create a new timer in the Helpers UI:
    - <a href="https://my.home-assistant.io/redirect/helpers/" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/helpers.svg" alt="Open your Home Assistant instance and show your helper entities." style="margin-left: unset"/></a> <!-- https://my.home-assistant.io/create-link/ -->
    - I set the timer duration to 15 minutes
- Add the `Notify Bird Detection` automation below
    - Update the `timer.kyle_bird_notification_cooldown` to _your_ new timer `entity_id`
- Add the `Reset Bird Detection Timer` automation below
    - Update the `timer.kyle_bird_notification_cooldown` to _your_ new timer `entity_id`

**⚠️ Known downside:** Since this script is intended for _any_ trigger by BirdNET-Go, all bird species that hit my webhook endpoint end up grouped together. So if BirdNET-Go hits my automation webhook endpoint for two different birds _during_ the timer cooldown, I'll miss the notification for the second bird. I've accepted this as a drawback because the tradeoff for having a single automation for multiple birds is worth it to me. 

Here are a few ideas to work around this limitation:

- Ignore the timer cooldown
- Create a separate automation for each bird species you want to track
- Create a managed filter entity inside Home Assistant that uses state triggers and records the species

But I didn't bother with any of that because the chances of two different birds that I'm tracking being detected at the same time are low, and I'm probably already outside listening for the first bird.

<details markdown="block">

<summary>[Yaml] Home Assistant Automation - Notify Bird Detection</summary>

<a href="https://my.home-assistant.io/redirect/automations/" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/automations.svg" alt="Open your Home Assistant instance and show your automations." style="margin-left: unset"/></a> <!-- https://my.home-assistant.io/create-link/ -->

{% raw %}
```yaml
# version 1.0
alias: Notify Bird Detection
description: >-
  Sends a notification to Kyle when the bird detection script calls the webhook,
  handling success and error cases.
triggers:
  - trigger: webhook
    allowed_methods:
      - POST
      - PUT
    local_only: true
    webhook_id: notify-bird-detection-123456789
conditions: []
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.type == 'bird_detection' }}"
            alias: Bird Detection
          - condition: not
            conditions:
              - condition: state
                entity_id: timer.kyle_bird_notification_cooldown
                state: active
        sequence:
          - parallel:
              - data:
                  title: 🦜 {{ trigger.json.common_name }} Detected!
                  message: |
                    Time: {{ trigger.json.time }}   
                    Camera: {{ trigger.json.source_camera }}  
                    Confidence: {{ trigger.json.confidence_pct }}
                  data:
                    notification_icon: mdi:bird
                    group: birdnet-alert
                    channel: birdnet-alert
                    tag: birdnet-alert
                    ttl: 0
                    priority: high
                    push:
                      interruption-level: time-sensitive
                      sound: bert.wav
                    actions:
                      - action: BIRD_NOTIFICATION_COOLDOWN_RESET
                        title: Reset
                action: notify.kyle
              - action: timer.start
                metadata: {}
                data: {}
                target:
                  entity_id: timer.kyle_bird_notification_cooldown
              - action: input_text.set_value
                metadata: {}
                data:
                  value: >-
                    {{ trigger.json.time }}: {{ trigger.json.common_name }}, {{
                    trigger.json.source_camera }}, {{
                    trigger.json.confidence_pct }}
                target:
                  entity_id: input_text.kyle_last_bird_notification
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.type == 'script_error' }}"
            alias: Script Error
        sequence:
          - data:
              message: >-
                Received unexpected payload type from bird script webhook: {{
                trigger.json | tojson }}
              level: warning
            action: system_log.write
            enabled: true
          - data:
              title: Bird Script Error Reported
              message: >
                Reason: {{ trigger.json.reason }}   

                Missing Args: {{ trigger.json.missing_args | default('None
                specified') }}
              data:
                notification_icon: mdi:bird
                group: birdnet-alert
                channel: birdnet-alert
                tag: birdnet-alert
                ttl: 0
                priority: high
                push:
                  interruption-level: time-sensitive
            action: notify.kyle
mode: single
```
{% endraw %}

</details>

<details markdown="block">

<summary>[Yaml] Home Assistant Automation - Reset Bird Detection Timer</summary>

<a href="https://my.home-assistant.io/redirect/automations/" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/automations.svg" alt="Open your Home Assistant instance and show your automations." style="margin-left: unset"/></a> <!-- https://my.home-assistant.io/create-link/ -->

{% raw %}
```yaml
# version 1.0
alias: Kyle Bird Notification Cooldown Timer Reset
description: >-
  Resets the Bird Notification Cooldown Timer so I can get another bird
  notification.
triggers:
  - event_type: mobile_app_notification_action
    event_data:
      action: BIRD_NOTIFICATION_COOLDOWN_RESET
    trigger: event
conditions: []
actions:
  - action: timer.cancel
    metadata: {}
    data: {}
    target:
      entity_id:
        - timer.kyle_bird_notification_cooldown
mode: single

```
{% endraw %}

</details>

### Notify for a Bird Species Never Detected Before

![Home Assistant notification showing a notification for a bird species that is new](/assets/img/2025/05/home_assistant_notification_new_detection.png)*Home Assistant notification for a bird species that has been detected for the first time*

> Requires: [Sensor for Overall Species Summary](#sensor-for-overall-species-summary)

This automation will send a notification for each bird species the _first time_ that BirdNET-Go detects it. This is just a neat little gimmick to know if there is a brand new bird species in the area that I haven't seen before, or if I need to remove a false positive.

The downside is that this will only send a notification for each bird species _once_ (as once it has been detected, it's no longer _new_ again). But it will certainly be a fun little treat when a new bird species is detected during the first year of running BirdNET-Go.

<details markdown="block">

<summary>[Yaml] Home Assistant Automation - Notify First-Time Detection</summary>

{% raw %}
```yaml
# version 1.1
alias: Notify on First Detection of New BirdNET Bird Species
description: >-
  Send a notification to kyle when a new bird species is detected that
  we've never heard before.
triggers:
  - trigger: state
    entity_id:
      - sensor.birdnet_species_summary_persisted_data
    attribute: species_list
conditions:
  - condition: template
    value_template: >-
      {{ trigger.to_state.attributes.species_list is defined and
      trigger.to_state.attributes.species_list is iterable and
      trigger.to_state.attributes.species_list is not string and
      trigger.from_state.state != 'unavailable' }}
actions:
  - variables:
      current_species_list: >-
        {% set csl = trigger.to_state.attributes.get('species_list') if
        trigger.to_state and trigger.to_state.attributes else none %} {% if csl
        is iterable and csl is not string %}
          {{ csl }}
        {% else %}
          []
        {% endif %}
      previous_species_list: >-
        {% set psl = trigger.from_state.attributes.get('species_list') if
        trigger.from_state and trigger.from_state.attributes else none %} {% if
        psl is iterable and psl is not string %}
          {{ psl }}
        {% else %}
          []
        {% endif %}
      current_common_names: "{{ current_species_list | map(attribute='common_name') | list }}"
      previous_common_names: "{{ previous_species_list | map(attribute='common_name') | list }}"
  - repeat:
      for_each: "{{ current_species_list }}"
      sequence:
        - sequence:
            - condition: template
              value_template: "{{ repeat.item.common_name not in previous_common_names }}"
            - action: notify.kyle
              metadata: {}
              data:
                title: 🐦 New Bird Species Alert!
                message: >-
                  The {{repeat.item.common_name}} has been detected for the
                  first time!
                data:
                  notification_icon: mdi:bird
                  group: birdnet-alert
                  channel: birdnet-alert
                  tag: birdnet-alert
                  ttl: 0
                  priority: high
                  push:
                    interruption-level: time-sensitive
mode: single
```
{% endraw %}
</details>

### Notify for a Bird That Hasn’t Been Detected in a While

![Home Assistant notification showing a notification for a bird that hasn't been detected in a while](/assets/img/2025/05/home_assistant_notification_bird_returned.png)*Home Assistant notification for any bird that hasn't been detected for a while*

> Requires: [Sensor for Overall Species Summary](#sensor-for-overall-species-summary)

Over time, the BirdNET-Go instance will stop accumulating _brand new_ birds as it detects more and more species. But I still want to know when a bird that hasn't been detected in a while is detected again.

To solve this problem, I created an automation that notifies me when a bird that hasn't been detected in a while is detected again. Think of it like the first time you see a yellow-rumped warbler in the spring after not seeing it all winter. It's neat to be notified when any bird is back in the area after a long absence.

By default, the automation sets a window of 60 days. As I've only had my BirdNET-Go instance running for a couple of months, I have no idea if this is a sane number or not. But I'll find out!

This can easily be adjusted in the automation below on the {% raw %}`{{ difference_in_days > 60 }}`{% endraw %} line.

<details markdown="block">

<summary>[Yaml] Home Assistant Automation - Notify Uncommon Detection</summary>

{% raw %}
```yaml
# version 1.4
alias: Notify rare bird detection
description: >-
  Notify the family when a bird that hasn't been detected for a large number of days
  is detected again.
triggers:
  - trigger: state
    entity_id:
      - sensor.birdnet_species_summary_persisted_data
    attribute: species_list
conditions:
  - condition: template
    value_template: >-
      {{ trigger.to_state.attributes.species_list is defined and
      trigger.to_state.attributes.species_list is iterable and
      trigger.to_state.attributes.species_list is not string and
      trigger.from_state.state != 'unavailable' }}
    alias: Is a valid list
actions:
  - variables:
      current_species_list: >-
        {% set csl = trigger.to_state.attributes.get('species_list') if
        trigger.to_state and trigger.to_state.attributes else none %} {% if csl
        is iterable and csl is not string %}
          {{ csl }}
        {% else %}
          []
        {% endif %}
      previous_species_list: >-
        {% set psl = trigger.from_state.attributes.get('species_list') if
        trigger.from_state and trigger.from_state.attributes else none %} {% if
        psl is iterable and psl is not string %}
          {{ psl }}
        {% else %}
          []
        {% endif %}
      current_common_names: "{{ current_species_list | map(attribute='common_name') | list }}"
      previous_common_names: "{{ previous_species_list | map(attribute='common_name') | list }}"
  - repeat:
      for_each: "{{ current_species_list }}"
      sequence:
        - condition: template
          value_template: >-
            {{ previous_species_list | selectattr('species_code', 'eq',
            repeat.item.species_code) | list | length > 0 }}
        - condition: template
          value_template: >-
            {% set current_bird = repeat.item %}

            {% set previous_bird_data_list = previous_species_list |
            selectattr('species_code', 'eq', current_bird.species_code) | list
            %}

            {% if previous_bird_data_list | length > 0 %}
              {% set previous_bird = previous_bird_data_list[0] %}

              {% if current_bird.last_heard is defined and current_bird.last_heard is string and 
                    previous_bird.last_heard is defined and previous_bird.last_heard is string %}
                
                {% set current_last_heard_dt = strptime(current_bird.last_heard, '%Y-%m-%d %H:%M:%S') %}
                {% set previous_last_heard_dt = strptime(previous_bird.last_heard, '%Y-%m-%d %H:%M:%S') %}

                {% if current_last_heard_dt > previous_last_heard_dt %}
                  {% set difference_in_seconds = (current_last_heard_dt - previous_last_heard_dt).total_seconds() %}
                  {% set difference_in_days = difference_in_seconds / (60*60*24) %}
                  {{ difference_in_days > 180 }}
                {% else %}
                  {# current_last_heard is not more recent than previous_last_heard #}
                  false
                {% endif %}
              {% else %}
                false
              {% endif %}
            {% else %}
              false
            {% endif %}
        - variables:
            bird_last_heard: >-
              {{ (previous_species_list | selectattr('species_code', 'eq',
              repeat.item.species_code) | list)[0].last_heard }}
            bird_recently_heard: "{{ repeat.item.last_heard }}"
            days_between_detection: >-
              {{ (bird_recently_heard | as_datetime - bird_last_heard |
              as_datetime).days }}
        - data:
            title: >-
              🐦 {{ repeat.item.common_name }} is back
              ({{days_between_detection}} days)!
            message: |
              {{ repeat.item.common_name }} has been heard again!
              Previously heard: {{ bird_last_heard | as_timestamp |
              timestamp_custom('%b %d, %Y') }}
              That's a gap of {{ days_between_detection }} days!
            data:
              notification_icon: mdi:bird
              group: birdnet-alert
              channel: birdnet-alert
              tag: birdnet-alert
              ttl: 0
              priority: high
              push:
                interruption-level: time-sensitive
          action: notify.kyle
# Queued as we might be running slow with our timestamp
mode: queued
max: 10
```
{% endraw %}
</details>


## Bonus: Generate Shareable Videos From Sound Detections

I've recorded some pretty cool bird sounds with BirdNET-Go, and I wanted to share them with my family and friends. Since it's difficult to share raw audio files, I created a script that generates a video from the audio file, adds some metadata, and overlays some of the information.

Just so you're aware, the audio download process from BirdNET-Go seems to be in flux at the moment depending on which page you download the audio from.

If you download the bird sounds from the audio player in the `Main Dashboard` or the `Search Bar` at the top of BirdNET-Go, it appears to download the _original_ audio file from the `/api/v1/media/audio` endpoint. That audio file will follow a naming scheme close to `<scientific_name>_<confidence>_<timestamp>.<original_extension>`. 

However, if you use the newer `Search Dashboard` (from the left-hand side of BirdNET-Go), you'll be presented with a much more advanced search interface. This is what I'm using at the moment.

I've included both scripts below, but I commonly use the `Search Dashboard` one.

### New Search Dashboard Audio Files

Filenames that match the `######.mp4` pattern and use the `/api/v2/audio/#####` endpoint.

<details markdown="block">

<summary>[Shell script] BirdNET-Go Video Generator (New Search Dashboard)</summary>

{% raw %}
```bash
#!/bin/bash
# version 1.0

# Default values
duration=15
location="YOUR_OWN_LOCATION"
weather="Partly Cloudy"
input_file="$(ls -t ~/Downloads/*.mp4 2>/dev/null | head -n 1)"suppression
boost_sound=false
species_override=""
subtitle=""
start_offset="0" # Default start offset in seconds
api_detections_endpoint="http://YOUR_OWN_BIRDNET_ENDPOINT/api/v2/detections/"

# === Dependency Check ===
for cmd in curl jq ffmpeg awk; do
  if ! command -v $cmd &> /dev/null; then
    echo "ERROR: Required command '$cmd' not found. Please install it."
    exit 1
  fi
done
# === END Dependency Check ===

# === Temp Directory and Cleanup ===
TMPDIR=$(mktemp -d)
if [ ! -d "$TMPDIR" ]; then
    echo "ERROR: Failed to create temporary directory."
    exit 1
fi
trap 'echo "DEBUG: Cleaning up temp dir: $TMPDIR"; rm -rf "$TMPDIR"' EXIT
echo "DEBUG: Created temp directory: $TMPDIR"
# === END Temp Directory ===

# Help function
help_function() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -d <duration>       Duration of the video in seconds (default: 15)"
  echo "  -l <location>       Location (default: YOUR_OWN_LOCATION)"
  echo "  -w <weather>        Weather (default: Partly Cloudy)"
  echo "  -i <input_file>     Input audio/video file (default: newest .mp4 in ~/Downloads/)"
  echo "  -b <boost_sound>    Boost audio (true or false, default: false)"
  echo "  -s <species_text>   Override the species text displayed in the video"
  echo "  -u <subtitle>       Optional subtitle text below species name"
  echo "  -m <start_offset>   Start the clip at this many seconds into the input file (default: 0)"
  echo "  --help              Display this help message"
  exit 0
}

# Parse command-line arguments
while getopts "d:l:w:i:b:s:u:m:" opt; do
  case "$opt" in
  d) duration="$OPTARG" ;;
  l) location="$OPTARG" ;;
  w) weather="$OPTARG" ;;
  i) input_file="$OPTARG" ;;
  b) boost_sound="$OPTARG" ;;
  s) species_override="$OPTARG" ;;
  u) subtitle="$OPTARG" ;;
  m) start_offset="$OPTARG" ;;
  \?|: | *) help_function ;;
  esac
done
shift $((OPTIND - 1))

# Validate start_offset
if ! [[ "$start_offset" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "ERROR: Invalid start offset '$start_offset'. Must be a non-negative number."
    exit 1
fi
echo "DEBUG: Start offset set to: $start_offset seconds"

# --- Input File and API Data Processing ---
if [ -z "$input_file" ]; then
    echo "Error: No input file specified and couldn't find a default .mp4 file in ~/Downloads/."
    exit 1
fi
if [ ! -f "$input_file" ]; then echo "Error: Input file '$input_file' not found."; exit 1; fi

filename=$(basename "$input_file")
echo "DEBUG: Processing filename: $filename"
file_id="${filename%.*}" # Get filename without extension

if ! [[ "$file_id" =~ ^[0-9]+$ ]]; then
    echo "ERROR: Filename (without extension) '$file_id' is not a valid numeric ID."
    exit 1
fi
echo "DEBUG: Extracted File ID: $file_id"

API_URL="$api_detections_endpoint$file_id"
echo "DEBUG: Fetching data from API: $API_URL"

api_response=$(curl -s -L "$API_URL") # -L to follow redirects
curl_exit_status=$?

if [ $curl_exit_status -ne 0 ]; then
    echo "ERROR: curl command failed with exit status $curl_exit_status when fetching data for ID $file_id."
    exit 1
fi

if [ -z "$api_response" ] || [ "$(echo "$api_response" | jq '.id')" = "null" ]; then
    echo "ERROR: API did not return valid data for ID $file_id. Response: $api_response"
    exit 1
fi

# Extract data using jq
api_common_name=$(echo "$api_response" | jq -r '.commonName')
api_begin_time=$(echo "$api_response" | jq -r '.beginTime')
api_confidence_float=$(echo "$api_response" | jq -r '.confidence')

if [ "$api_common_name" = "null" ] || [ -z "$api_common_name" ]; then
    echo "ERROR: Could not extract commonName from API response."
    exit 1
fi
if [ "$api_begin_time" = "null" ] || [ -z "$api_begin_time" ]; then
    echo "ERROR: Could not extract beginTime from API response."
    exit 1
fi
if [ "$api_confidence_float" = "null" ] || [ -z "$api_confidence_float" ]; then
    echo "ERROR: Could not extract confidence from API response."
    exit 1
fi

echo "DEBUG: API Common Name: $api_common_name"
echo "DEBUG: API Begin Time: $api_begin_time"
echo "DEBUG: API Confidence (float): $api_confidence_float"

# Format timestamp (e.g., YYYY-MM-DDTHH:MM:SS-04:00 -> YYYY-MM-DD HH:MM:SS)
timestamp=$(echo "$api_begin_time" | sed 's/T/ /; s/\([-+][0-9][0-9]:[0-9][0-9]Z\{0,1\}\)$//')
if [ -z "$timestamp" ]; then
    echo "ERROR: Failed to format timestamp from API beginTime '$api_begin_time'."
    exit 1
fi
echo "DEBUG: Formatted Timestamp: $timestamp"

# Format confidence (e.g., 0.96 -> 96% Confidence)
confidence_percentage=$(awk -v conf="$api_confidence_float" 'BEGIN { printf "%.0f", conf * 100 }')
if [ -z "$confidence_percentage" ]; then
    echo "ERROR: Failed to calculate confidence percentage from '$api_confidence_float'."
    exit 1
fi
confidence_text_unescaped="${confidence_percentage}% Confidence"
echo "DEBUG: Confidence Text (unescaped): $confidence_text_unescaped"
# --- End API Data Processing ---

# Determine final species text
species_from_api="$api_common_name" # Use common name from API

if [ -n "$species_override" ]; then
  echo "INFO: Using species override text: '$species_override'"
  final_species_text="$species_override"
else
  echo "INFO: Using API-derived species text: '$species_from_api'"
  final_species_text="$species_from_api"
fi
if [ -z "$final_species_text" ]; then echo "ERROR: Species text is empty."; exit 1; fi

# Prepare other display text (unescaped) for textfile method
timestamp_display=$(echo "$timestamp" | sed 's/Z//g')
weather_display="Weather: $weather"

# --- Write text to temporary files (Using \% escape for files) ---
species_file="$TMPDIR/species.txt"
subtitle_file_path=""
confidence_file="$TMPDIR/confidence.txt"
location_file="$TMPDIR/location.txt"
timestamp_file="$TMPDIR/timestamp.txt"
weather_file="$TMPDIR/weather.txt"

echo "DEBUG: Writing text to temp files..."
printf "%s" "$final_species_text" > "$species_file"
printf "%s" "$location" > "$location_file"
printf "%s" "$timestamp_display" > "$timestamp_file"
printf "%s" "$weather_display" > "$weather_file"

confidence_text_for_file=$(echo "$confidence_text_unescaped" | sed 's/%/\\%/g')
printf "%s" "$confidence_text_for_file" > "$confidence_file"
echo "DEBUG: Confidence text written to $confidence_file (using \% escape)"

if [ -n "$subtitle" ]; then
    subtitle_file_path=$(mktemp "$TMPDIR/subtitle_XXXXXX.txt")
    if [ -z "$subtitle_file_path" ] || [ ! -w "$(dirname "$subtitle_file_path")" ]; then
        echo "ERROR: Failed to create subtitle temp file in $TMPDIR."
        subtitle_file_path=""
    else
        subtitle_text_for_file=$(echo "$subtitle" | sed 's/%/\\%/g')
        printf "%s" "$subtitle_text_for_file" > "$subtitle_file_path"
        echo "DEBUG: Subtitle text written to $subtitle_file_path (using \% escape)"
    fi
fi
# --- End Write text ---


# <<< Calculate Y Positions >>>
y_offset_species=-200; y_offset_confidence=-115; y_offset_location=-35; y_offset_timestamp=45; y_offset_weather=125; line_spacing=85
calc_y_pos() { local offset=$1; echo "(h/2)-text_h/2+($offset)"; }
y_pos_species=$(calc_y_pos $y_offset_species); y_pos_confidence=$(calc_y_pos $y_offset_confidence); y_pos_location=$(calc_y_pos $y_offset_location); y_pos_timestamp=$(calc_y_pos $y_offset_timestamp); y_pos_weather=$(calc_y_pos $y_offset_weather)
y_pos_subtitle=""
if [ -n "$subtitle_file_path" ] ; then
    y_pos_subtitle=$(calc_y_pos $((y_offset_species + line_spacing)))
    y_pos_confidence=$(calc_y_pos $((y_offset_confidence + line_spacing)))
    y_pos_location=$(calc_y_pos $((y_offset_location + line_spacing)))
    y_pos_timestamp=$(calc_y_pos $((y_offset_timestamp + line_spacing)))
    y_pos_weather=$(calc_y_pos $((y_offset_weather + line_spacing)))
fi
# <<< END Calculate Y Positions >>>


# <<< Build Filter Complex using textfile= for ALL lines >>>
filter_complex="\
[0:v]drawtext=textfile='$species_file':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=${y_pos_species}"
if [ -n "$subtitle_file_path" ] ; then
    filter_complex="$filter_complex,\
drawtext=textfile='$subtitle_file_path':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_subtitle}"
fi
filter_complex="$filter_complex,\
drawtext=textfile='$confidence_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_confidence},\
drawtext=textfile='$location_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_location},\
drawtext=textfile='$timestamp_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_timestamp},\
drawtext=textfile='$weather_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_weather}[v]"
if [ "$boost_sound" = true ]; then filter_complex="$filter_complex;[1:a]volume=15dB,compand=attacks=0:points=-80/-80|-12/-10|0/-2|20/25[a]"; else filter_complex="$filter_complex;[1:a]anull[a]"; fi
# <<< END Build Filter Complex >>>


# ============================================================
# --- Construct the output path ---
input_dir=$(dirname "$input_file")
filename_species_part="$final_species_text"
safe_species_name=$(echo "$filename_species_part" | sed 's/[^a-zA-Z0-9_ -]//g' | tr ' ' '_')
timestamp_filename=$(echo "$timestamp" | sed 's/ /_/g; s/:/-/g')
output_filename_base="${timestamp_filename}_${safe_species_name}.mp4"
output_file="$input_dir/$output_filename_base"
echo "INFO: Output file path: $output_file"
# ============================================================

# Construct the ffmpeg command string for eval
ffmpeg_input_options=""
# Check if start_offset is greater than 0 using awk for float comparison
is_offset_positive=$(awk -v offset="$start_offset" 'BEGIN { print (offset > 0) }')

if [ "$is_offset_positive" -eq 1 ]; then
  ffmpeg_input_options="-ss $start_offset"
  echo "INFO: Applying start offset of $start_offset seconds to input file."
fi

ffmpeg_command="ffmpeg -f lavfi -i \"color=c=black:s=1280x700\" $ffmpeg_input_options -i \"$input_file\" \
-filter_complex \"$filter_complex\" \
-map \"[v]\" -map \"[a]\" -c:v libx264 -c:a aac -t $duration -y \"$output_file\""
echo "DEBUG: FFmpeg command string built for eval: $ffmpeg_command"

# Execute the command using eval
echo "INFO: Executing ffmpeg command..."
eval "$ffmpeg_command"

exit_status=$?
if [ $exit_status -ne 0 ]; then
    echo "ERROR: ffmpeg command failed with exit status $exit_status"
    exit $exit_status
else
    echo "SUCCESS: Successfully created video: $output_file"
fi

exit 0
```
{% endraw %}

</details>

### Legacy Search Dashboard Audio Files

Filenames that match the `<scientific_name>_<confidence>_<timestamp>.<original_extension>` pattern and use the `/api/v1/media/audio` endpoint.

> This script requires a matching labels file in the same directory as the script. The labels file is used to translate the scientific name to a common name. Download the labels file from the [BirdNET-Go repository](https://github.com/birdnet-team/BirdNET-Analyzer/tree/v2.0.0/birdnet_analyzer/labels/V2.4). 
> 
> Or download their `BirdNET_GLOBAL_6K_V2.4_Labels_en_us.txt` file [here](/assets/files/2025/05/BirdNET_GLOBAL_6K_V2.4_Labels_us_us.txt).

<details markdown="block">

<summary>[Shell script] BirdNET-Go Video Generator (Legacy Search)</summary>

{% raw %}
```bash
#!/bin/bash
# version 1.0

# Default values
duration=15
location="Jenison, MI"
weather="Partly Cloudy"
input_file="$(ls -t ~/Downloads/*.m4a | head -n 1)" # The default input file grabs the newest .m4a file in your Downloads folder
boost_sound=false
label_filename="BirdNET_GLOBAL_6K_V2.4_Labels_us_us.txt" # Base filename
species_override=""
subtitle=""
start_offset="0" # Default start offset in seconds

# === Dependency Check ===
for cmd in curl jq ffmpeg awk; do
  if ! command -v $cmd &> /dev/null; then
    echo "ERROR: Required command '$cmd' not found. Please install it."
    exit 1
  fi
done
# === END Dependency Check ===

# === Temp Directory and Cleanup ===
TMPDIR=$(mktemp -d)
if [ ! -d "$TMPDIR" ]; then
    echo "ERROR: Failed to create temporary directory."
    exit 1
fi
trap 'echo "DEBUG: Cleaning up temp dir: $TMPDIR"; rm -rf "$TMPDIR"' EXIT
echo "DEBUG: Created temp directory: $TMPDIR"
# === END Temp Directory ===


# Determine script directory and build full label file path
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
label_file="$SCRIPT_DIR/$label_filename"
echo "DEBUG: Using label file path: $label_file"


# Help function
help_function() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -d <duration>      Duration of the video in seconds (default: 15)"
  echo "  -l <location>      Location (default: Jenison, MI)"
  echo "  -w <weather>       Weather (default: Partly Cloudy)"
  echo "  -i <input_file>    Input audio file (default: newest .m4a in ~/Downloads/)"
  echo "  -b <boost_sound>   Boost audio (true or false, default: false)"
  echo "  -s <species_text>  Override the species text displayed in the video"
  echo "  -m <start_offset>  Start the clip at this many seconds into the input file (default: 0)"
  echo "  -u <subtitle>      Optional subtitle text below species name"
  echo "  --help             Display this help message"
  exit 0
}

# Parse command-line arguments
while getopts "d:l:w:i:b:s:u:m:" opt; do
  case "$opt" in
  d) duration="$OPTARG" ;;
  l) location="$OPTARG" ;;
  w) weather="$OPTARG" ;;
  i) input_file="$OPTARG" ;;
  b) boost_sound="$OPTARG" ;;
  s) species_override="$OPTARG" ;;
  u) subtitle="$OPTARG" ;;
  m) start_offset="$OPTARG" ;;
  \?|: | *) help_function ;;
  esac
done
shift $((OPTIND - 1))

# Validate start_offset
if ! [[ "$start_offset" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "ERROR: Invalid start offset '$start_offset'. Must be a non-negative number."
    exit 1
fi
echo "DEBUG: Start offset set to: $start_offset seconds"

# --- Filename Processing & Extraction ---
if [ ! -f "$input_file" ]; then echo "Error: Input file '$input_file' not found."; exit 1; fi
filename=$(basename "$input_file"); echo "Filename: $filename"
if [ -z "$filename" ]; then echo "ERROR: Could not get basename from '$input_file'"; exit 1; fi
filename_parts=($(echo "$filename" | tr '_' '\n')); if [ ${#filename_parts[@]} -lt 2 ]; then echo "ERROR: Not enough parts in filename '$filename'"; exit 1; fi

timestamp_with_extension="${filename_parts[$((${#filename_parts[@]} - 1))]}"; timestamp_raw="${timestamp_with_extension%.*}"
if [ -z "$timestamp_raw" ]; then echo "ERROR: Could not extract raw timestamp"; exit 1; fi
echo "Timestamp raw: $timestamp_raw"; timestamp=$(echo "$timestamp_raw" | sed 's/T/ /g' | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\) \([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/'); echo "Timestamp: $timestamp"

first_part="${filename_parts[0]}"; num_parts=${#filename_parts[@]}; confidence_index=$((num_parts - 2))
if [[ "$first_part" =~ ^[0-9]{4}$ && $num_parts -ge 6 ]]; then echo "DEBUG: Detected SCRIPTDIR/_MM_ format."; start_index=2; length=$((confidence_index - start_index)); else echo "DEBUG: Assuming direct Genus_species_ format."; start_index=0; length=$((confidence_index - start_index)); fi
if [[ $length -lt 1 ]]; then scientific_name_parts=(); else scientific_name_parts=("${filename_parts[@]:$start_index:$length}"); fi
if [ ${#scientific_name_parts[@]} -eq 0 ]; then echo "ERROR: Failed to extract scientific name parts."; exit 1; fi
scientific_name_underscores=$(IFS='_'; echo "${scientific_name_parts[*]}")
scientific_name=$(echo "$scientific_name_underscores" | tr '_' ' '); echo "Scientific name (underscores): $scientific_name_underscores"; echo "Scientific name (spaces): $scientific_name"

# Get numeric confidence and prepare UNESCAPED display string
confidence_part="${filename_parts[$confidence_index]}"; confidence_num_str=$(echo "$confidence_part" | sed 's/p//gi' 2>/dev/null)
if [ -z "$confidence_num_str" ] || ! [[ "$confidence_num_str" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Warning: Confidence value '$confidence_part' invalid. Setting Unknown."
    confidence_text_unescaped="Unknown confidence"
else
    confidence_text_unescaped="${confidence_num_str}% Confidence" # Literal text with single %
fi;
echo "Confidence Text (unescaped): $confidence_text_unescaped"
# --- End Filename Processing ---


# Function to get common name from labels file
get_common_name() {
  local scientific_name_key="$1"
  echo "Starting get_common_name with scientific name key: $scientific_name_key" >&2
  if [ ! -r "$label_file" ]; then echo "Warning: Label file '$label_file' not found or not readable." >&2; echo "$scientific_name"; return; fi
  local common_name=$(grep -i "^${scientific_name_key}_" "$label_file" | head -n 1 | cut -d '_' -f 2)
  if [ -n "$common_name" ]; then echo "Match found: $common_name" >&2; echo "$common_name"; else echo "Species not found for key '$scientific_name_key'" >&2; echo "$scientific_name"; fi
}

# Get common name
species=$(get_common_name "$scientific_name")
echo "Species determined from file/lookup: $species"

# Determine final species text
if [ -n "$species_override" ]; then
  echo "INFO: Using species override text: '$species_override'"
  final_species_text="$species_override"
else
  echo "INFO: Using determined/fallback species text: '$species'"
  final_species_text="$species"
fi
if [ -z "$final_species_text" ]; then echo "ERROR: Species text is empty."; exit 1; fi

# Prepare other display text (unescaped) for textfile method
timestamp_display=$(echo "$timestamp" | sed 's/Z//g')
weather_display="Weather: $weather"

# --- Write text to temporary files (Using \% escape for files) ---
species_file="$TMPDIR/species.txt"
subtitle_file="" # Initialize
confidence_file="$TMPDIR/confidence.txt"
location_file="$TMPDIR/location.txt"
timestamp_file="$TMPDIR/timestamp.txt"
weather_file="$TMPDIR/weather.txt"

echo "DEBUG: Writing text to temp files..."
# Species, Location, Timestamp, Weather written as is (apostrophes are OK here)
printf "%s" "$final_species_text" > "$species_file"
printf "%s" "$location" > "$location_file"
printf "%s" "$timestamp_display" > "$timestamp_file"
printf "%s" "$weather_display" > "$weather_file"

# Replace single % with literal backslash + %
confidence_text_for_file=$(echo "$confidence_text_unescaped" | sed 's/%/\\%/g')
printf "%s" "$confidence_text_for_file" > "$confidence_file"
echo "DEBUG: Confidence text written to $confidence_file (using \% escape)"

# Conditionally create subtitle file
if [ -n "$subtitle" ]; then
    subtitle_file=$(mktemp "$TMPDIR/subtitle_XXXXXX.txt")
    if [ -z "$subtitle_file" ] || [ ! -w $(dirname "$subtitle_file") ]; then
         echo "ERROR: Failed to create subtitle temp file in $TMPDIR."
         subtitle_file=""
    else
        subtitle_text_for_file=$(echo "$subtitle" | sed 's/%/\\%/g') # Use \%
        printf "%s" "$subtitle_text_for_file" > "$subtitle_file"
        echo "DEBUG: Subtitle text written to $subtitle_file (using \% escape)"
    fi
fi
# --- End Write text ---


# <<< Calculate Y Positions >>>
y_offset_species=-200; y_offset_confidence=-115; y_offset_location=-35; y_offset_timestamp=45; y_offset_weather=125; line_spacing=85
calc_y_pos() { local offset=$1; echo "(h/2)-text_h/2+($offset)"; }
y_pos_species=$(calc_y_pos $y_offset_species); y_pos_confidence=$(calc_y_pos $y_offset_confidence); y_pos_location=$(calc_y_pos $y_offset_location); y_pos_timestamp=$(calc_y_pos $y_offset_timestamp); y_pos_weather=$(calc_y_pos $y_offset_weather)
y_pos_subtitle=""
if [ -n "$subtitle_file" ] ; then # Check if the subtitle file was successfully created
    y_pos_subtitle=$(calc_y_pos $((y_offset_species + line_spacing)))
    y_pos_confidence=$(calc_y_pos $((y_offset_confidence + line_spacing)))
    y_pos_location=$(calc_y_pos $((y_offset_location + line_spacing)))
    y_pos_timestamp=$(calc_y_pos $((y_offset_timestamp + line_spacing)))
    y_pos_weather=$(calc_y_pos $((y_offset_weather + line_spacing)))
fi
# <<< END Calculate Y Positions >>>


# <<< Build Filter Complex using textfile= for ALL lines >>>
filter_complex="\
[0:v]drawtext=textfile='$species_file':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=${y_pos_species}"
if [ -n "$subtitle_file" ] ; then
    filter_complex="$filter_complex,\
drawtext=textfile='$subtitle_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_subtitle}"
fi
filter_complex="$filter_complex,\
drawtext=textfile='$confidence_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_confidence},\
drawtext=textfile='$location_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_location},\
drawtext=textfile='$timestamp_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_timestamp},\
drawtext=textfile='$weather_file':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=${y_pos_weather}[v]"
if [ "$boost_sound" = true ]; then filter_complex="$filter_complex;[1:a]volume=15dB,compand=attacks=0:points=-80/-80|-12/-10|0/-2|20/25[a]"; else filter_complex="$filter_complex;[1:a]anull[a]"; fi
# <<< END Build Filter Complex >>>


# ============================================================
# --- Construct the output path ---
input_dir=$(dirname "$input_file")
filename_species_part="$final_species_text"
safe_species_name=$(echo "$filename_species_part" | sed 's/[^a-zA-Z0-9_ -]//g' | tr ' ' '_')
timestamp_filename=$(echo "$timestamp" | sed 's/ /_/g; s/:/-/g; s/Z//g')
output_filename_base="${timestamp_filename}_${safe_species_name}.mp4"
output_file="$input_dir/$output_filename_base"
echo "Output file path: $output_file"
# ============================================================

# Construct the ffmpeg command string for eval
ffmpeg_input_options=""
# Check if start_offset is greater than 0 using awk for float comparison
is_offset_positive=$(awk -v offset="$start_offset" 'BEGIN { print (offset > 0) }')

if [ "$is_offset_positive" -eq 1 ]; then
  ffmpeg_input_options="-ss $start_offset"
  echo "INFO: Applying start offset of $start_offset seconds to input file."
fi

ffmpeg_command="ffmpeg -f lavfi -i \"color=c=black:s=1280x700\" $ffmpeg_input_options -i \"$input_file\" \
-filter_complex \"$filter_complex\" \
-map \"[v]\" -map \"[a]\" -c:v libx264 -c:a aac -t $duration -y \"$output_file\""
echo "FFmpeg command string built for eval: $ffmpeg_command"

# Execute the command using eval
echo "Executing via eval:"
eval "$ffmpeg_command"

exit_status=$?
# Trap will clean up $TMPDIR regardless of exit status
if [ $exit_status -ne 0 ]; then
    echo "Error: ffmpeg command failed with exit status $exit_status"
    exit $exit_status
else
    echo "Successfully created video: $output_file"
fi

exit 0
```
{% endraw %}
</details>

## Favorite Bird Recordings

Here are some of my favorite bird recordings I've captured on BirdNET-Go using my camera's microphones _so far_.

### White-crowned Sparrow 🔊

[eBird species page](https://ebird.org/species/whcspa)

This small sparrow sings a beautiful song. In my region, I frequently hear it sing this earworm of a melody:

🎶 _Do-Do-Mi-Mi-Sol-Sol-La_ 🎶

{% include video.html
  src="/assets/files/2025/05/2025-04-14_07-05-46_White-crowned_Sparrow.mp4"
  poster="/assets/files/2025/05/2025-04-14_07-05-46_White-crowned_Sparrow.png"
  controls=""
%}
`bird-video.sh -i ~/Downloads/29722.mp4 -b true -d 3 -w "Cloudy"`

### Ruby-throated Hummingbird 🔊

[eBird species page](https://ebird.org/species/rthhum)

While looking out the window at a bunny with my daughter, this hummingbird flew right to the fuchsia baskets above us. As soon as my brain registered what this was, my phone alerted me of its first hummingbird detection!

In this clip, you can hear the hummingbird's fast chirping and wings buzzing around the 00:09 mark. 🪽

{% include video.html
  src="/assets/files/2025/05/2025-05-24_07-50-42_Ruby-throated_Hummingbird.mp4"
  poster="/assets/files/2025/05/2025-05-24_07-50-42_Ruby-throated_Hummingbird.png"
  controls=""
%}

`bird-video.sh -i ~/Downloads/91238.mp4 -b true -d 11 -w "Clear Sky"`

### Black-throated Green Warbler 🔊

[eBird species page](https://ebird.org/species/btnwar)

This crazy bird has such a unique advertising song. It sounds quite robotic. 🤖

{% include video.html
  src="/assets/files/2025/05/2025-05-07_07-18-50_Black-throated_Green_Warbler.mp4"
  poster="/assets/files/2025/05/2025-05-07_07-18-50_Black-throated_Green_Warbler.png"
  controls=""
%}

`bird-video.sh -i ~/Downloads/66671.mp4 -b true -m 4 -d 4 -w "Cloudy"`

### Red-tailed Hawk 🔊

[eBird species page](https://ebird.org/species/rethaw)

The iconic red-tailed hawk. This call is infamous in movies and TV shows. Often misrepresented as an eagle. 🦅

{% include video.html
  src="/assets/files/2025/05/2025-04-10_14-23-48_Red-tailed_Hawk.mp4"
  poster="/assets/files/2025/05/2025-04-10_14-23-48_Red-tailed_Hawk.png"
  controls=""
%}

`bird-video.sh -i ~/Downloads/24112.mp4 -b true -d 7 -w "Cloudy"`

### Osprey Duet 🔊

[eBird species page](https://ebird.org/species/osprey)

While pushing my kids on the swing, I had these two Ospreys fly over me, calling back and forth. 🔊

{% include video.html
  src="/assets/files/2025/05/2025-03-29_11-07-07_Osprey.mp4"
  poster="/assets/files/2025/05/2025-03-29_11-07-07_Osprey.png"
  controls=""
%}

`bird-video.sh -i ~/Downloads/7045.mp4 -b true -m 5 -d 6 -w "Clear Sky" -s "Osprey" -u "Duet"`

## Cool Encounters

I wanted to share some extra pictures of birds I have encountered. Two of them owe credit to BirdNET-Go!

The yellow-rumped warbler was the first bird detection in BirdNET-Go that I didn't recognize as they only show up here during their migration. BirdNET-Go helped me figure out when I might hear them based on my previous detections. With a little bit of patience, I was able to spot one in my backyard. These little guys are fun to watch flit around the trees when the sun peeks through the clouds.

![Yellow-rumped warbler](/assets/img/2025/05/yerwar.jpg)*A [Yellow-rumped warbler](https://ebird.org/species/yerwar) in my backyard. Any guesses as to why it's called that?*

Next, I wasn't expecting to see a mature male wild turkey in my backyard this spring. We've seen a few flocks over the years, but they always seem to be missing a mature male. Anyway, BirdNET-Go keyed me in that a wild turkey had been detected two days in a row. On the third day, I kept my eyes peeled and was rewarded with this lovely shot of its iridescent feathers. That was the last time I detected one. 

![Wild turkey](/assets/img/2025/05/wiltur.jpg)*A [Wild turkey](https://ebird.org/species/wiltur) in my backyard. The sun hit this bird's iridescent feathers perfectly.*

Last, there was a pair of Barred Owls that would nest around my parents' house growing up circa 2009. Obviously, BirdNET-Go didn't detect this one. But it was really cool hearing them at dusk and throughout the night. It was a fun memory I wanted to share.

![Barred owl](/assets/img/2025/05/brdowl.jpg)*A [Barred owl](https://ebird.org/species/brdowl) in my parents' backyard circa 2009.*

## Future Plans

A cool idea that won't leave my head is that someday I'd like to be able to recreate a real-time ambient bird soundscape based on my detections in BirdNET-Go. 

The thought is that maybe I've moved away from my current home, or I want to relive the experience of hearing the birds in my area. I can pair the timestamped database detections with random regional audio submissions on a site like [eBird](https://ebird.org/). Together, they could be used to recreate a _similar_ real-time ambient bird soundscape that I've already experienced.

It will be interesting to see how my memories of birds change, and if I can use that to anchor me back to a time like this. I think it would be a fun project to work on in the distant future.

## Conclusion

Listening to birds is fun. Birdwatching is a joy. Tune in to the sounds around you and it might make things a little brighter. 🐦‍🔥

![Libbie and Kyle spotting an Eastern Bluebird at the park](/assets/img/2025/05/birdwatching_1.jpg)*Libbie and Kyle spotting an [Eastern Bluebird](https://ebird.org/species/easblu) at the park*
