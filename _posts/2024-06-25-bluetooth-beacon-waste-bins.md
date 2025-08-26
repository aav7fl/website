---
title: 'Making Bluetooth the Beacon of Trash Day'
date: '2024-06-25 21:07'
updated: '2025-08-26 12:10'
comments: true
image:
  path: /assets/img/2024/06/waste_pickup.jpg
  height: 600
  width: 800
alt: A Blue Charm Bluetooth beacon strapped to my trash bin handle
published: true
tag: "large project"
description: "Bluetooth beacons + Home Assistant = Smarter Waste Management. Learn how I track pickups, automate reminders, and revolutionize my waste management routine to never miss a pickup day."
---

If you're anything like me, you've probably experienced the frustration of dragging your trash bins to the curb only to realize it wasn't trash day... or worse, mixing up the recycling week and missing the pickup entirely. Well, not anymore! I've integrated some affordable Bluetooth beacons with my Home Assistant setup to create a smart trash system that not only notifies me when to take out the bins but also tells me when they've been emptied.

<details markdown="block">

<summary>Post Changelog</summary>

- **2025-08-26**: Add `device:` blocks to MQTT sensors to tie entities under a single device.

</details>

{% include toc.html %}

## The Beacon of Trash Day

The heart of this system is a set of Bluetooth beacons. These aren't just any beacons though; they're multi-talented. Let me introduce you to the [Blue Charm BC04P MultiBeacon](https://bluecharmbeacons.com/product/bluetooth-ble-ibeacon-bc04p-multibeacon-water-resistant-with-motion-sensor/).

- Affordable: ~$20 each.
- IP67 Water-resistant: Perfect for withstanding the elements.
- Long Battery Life: ~4 years on a single CR2477 battery.
- Vibration Sensor: When triggered, these beacons can swap to broadcasting a different UUID.
- Different Bluetooth beacon formats: Like iBeacon or Eddystone TLM.
- Endless Configurability: Seriously, you can tweak almost everything about these beacons from signal format, broadcast strength, patterns, UUIDs, and more!

I capture data from the beacons using Blue Charm's [Beacon Scanner Gateway (BCG04)](https://bluecharmbeacons.com/product/bcg04-ble-gateway-beacon-scanner/). This device listens for the beacons and sends the data over wifi to my Home Assistant instance via MQTT. I could have rolled my own gateway, but I wanted to keep things simple and reliable. Time isn't exactly a luxury for me right now. 

> I was motivated by the fact that I kept forgetting to bring my bins back inside after they were emptied. This whole project was heavily inspired by [Blue Charm's blog post](https://bluecharmbeacons.com/beacon-powered-reminder-to-take-out-the-trash/). I've made a bunch of tweaks and I'm stoked with how this turned out.

## What's My Stack?

### Hardware

- Trash or recycling bin (hopefully provided by your waste removal provider)
- [Blue Charm BC04P Bluetooth beacon](https://bluecharmbeacons.com/product/bluetooth-ble-ibeacon-bc04p-multibeacon-water-resistant-with-motion-sensor/)
- [Blue Charm Beacon Scanner Gateway (BCG04)](https://bluecharmbeacons.com/product/bcg04-ble-gateway-beacon-scanner/)

### Software

- [Home Assistant](https://www.home-assistant.io/) (I'm using `2024.6.2` at the time of writing)
- MQTT broker (I use the [eclipse-mosquitto docker official image](https://hub.docker.com/_/eclipse-mosquitto))
- KBeacon Pro app (by KKM Co., Ltd)

## How Does This Work?

Ready to revolutionize your waste management routine? Let's dive into how I've set up these beacons to work with Home Assistant.

The basic concept is simple. 

- Zip-tie Bluetooth beacons to my bins.
- Program and track the UUID of the Bluetooth beacons.
- Program the beacons to broadcast a _different_ UUID when the vibration sensor is triggered.
- Use Home Assistant to track the signal strength and vibration events.
- Set up automations to send me notifications based on the data.

![Bluetooth beacon installed on a recycling bin handle](/assets/img/2024/06/bluetooth_beacon_on_bin.png)*Blue Charm BC04P Bluetooth beacon strapped to the handle of my recycling bin*

### How do I know where the bins are?

**Signal Strength**. Each bin has a Bluetooth beacon strapped to it. When the beacon signal is strong, the bin is in the garage. When the signal is weak (or missing entirely), the bin is at the curb. Notice that giant chasm in the signal strength? The signal is always above or below that threshold. I can safely assume that if it's below that threshold, the bin is outside.

![Filtered beacon signal strength](/assets/img/2024/06/filtered_beacon_signals.png)*Filtered beacon signal strength with a clear separation that is never crossed*

### How do I know when the bins are picked up?

**Vibration Detection**. These beacons include a configurable vibration sensor. On trash or recycling day, the beacon's vibration sensor will trigger when the bin is lifted by the truck. This trigger will cause the beacon to emit a different signal. By listening for the modified signal, I know when the bins have been emptied (or hit by a car 🗑️💥🚗).

![Inside the Blue Charm Bluetooth beacon case](/assets/img/2024/06/bluetooth_beacon_open.jpg)*Inside the Blue Charm BC04P Bluetooth beacon case*

### Did you say something about notifications?

Since I'm tracking if the bins are inside or outside, I get a friendly reminder the night before pickup day if I haven't taken the bins out yet. More on these automations later.

## Bluetooth Beacon Configuration

Let's start at the top and _lightly_ work our way through the steps of configuring the beacons.

Each beacon has a few slots available to broadcast using different formats. I use 2 out of the 4 available slots. The first slot is for the bin's presence and vibration detection (iBeacon), and the second slot is for the battery readings (Eddystone TLM). Ahead is the configuration overview for each beacon format.

But first, below is a grid of screenshots showing how I've configured my `Recycling bin beacon` in the KBeacon Pro app. This includes broadcasting in each of the different formats, and the triggers used. Your situation may vary, but this should offer a good starting place. You'll need to tweak these settings, such as the vibration trigger strength, to fit your needs.

![KBeacon Pro Settings](/assets/img/2024/06/collage.jpg)*KBeacon Pro Settings. UUIDs have been redacted.*

> If you need a more detailed quick-start guide for these beacons, Blue Charms has a [great one here](https://bluecharmbeacons.com/quick-start-guide-bc04p-ibeacon-ble-multibeacon/).

### Slot0 (iBeacon)

`Slot0` is the first configuration slot for the beacon. I've configured this slot to broadcast an iBeacon formatted signal every 1 second. There's nothing special about this signal. It broadcasts a pre-programmed UUID that I know to listen for. When I hear it, I record how strong or weak the signal is. The signal strength allows me to calculate if the bin is nearby, or far away.

Here's the twist. The iBeacon configuration has a trigger option for `motion` (or `vibration`) as one of the options. While this sensor is triggered, the beacon will swap broadcasting its original UUID for a _different_ pre-configured "triggered UUID". When I hear "triggered UUID", I know the beacon's vibration sensor has been tripped. 

Roughly 30 seconds after the vibration sensor is triggered, it will reset and the beacon will swap back to broadcasting its original UUID.

Everything about these is super configurable from the broadcast strength to the message types. The iBeacon normally broadcasts at 0+ dBm to save on battery life. But when the vibration sensor is triggered, it can temporarily increase the transmission level for the vibration event broadcast to 8+ dBm. This can help ensure that the beacon gateway receives important vibration events. 

> This can be useful when the beacon is placed at the end of a driveway, where it might be on the edge of the broadcast range. By increasing the broadcast strength for the vibration trigger, it increases the chances that the event will be heard. After the trigger resets, the beacon can return to broadcasting its standard event at 0+ dBm and continue to save on battery life.
> 
> For what it's worth, I never needed to increase the broadcast strength on my setup. But it's good to know that I have options.

### Slot1 (Eddystone TLM)

`Slot1` of my beacon is used to broadcast the current battery voltage of the beacon's battery. I'm able to do this by using the [Eddystone TLM](https://github.com/google/eddystone/blob/bb8738d7ddac0ddd3dfa70e594d011a0475e763d/eddystone-tlm/README.md) broadcast format instead of iBeacon. This is because an Eddystone TLM encoded frame supports including a field for battery voltage in mV. The Blue Charm BC04P supports this feature. 

> To save on battery life, I configured the beacon to only broadcast the Eddystone TLM every 40 seconds; the slowest period I was able to set from the app.

Knowledge of the battery voltage alone doesn't provide enough information to estimate the remaining battery life. That's because we don't know where the voltage cutoff is before the beacon stops working. I _could_ test it by using an external power supply, and slowly lowering the voltage until it cuts out. But I went the easier route. I asked support.

I reached out to [Thomas](https://www.linkedin.com/in/thomas-wetherell-3b10991/) at Blue Charm Beacons (who makes the beacon) and asked if they could share information about the power requirements for the beacon. They generously returned my request with the exact power levels that they use to detect an empty battery in their app, 2500 mV. Thomas also let me know that they found the beacon usually continues to work until _roughly_ 2400 mV, but we're going to stick with the 2500 mV for our calculations.

I took this information and created a sensor in Home Assistant that provides a rough estimate of the beacon's remaining battery percentage. I'll cover this later in the post.

### Bluetooth Beacon Scanner Gateway

The setup of the Bluetooth beacon scanner gateway is pretty straightforward. You just need to:

1. Download the KGateway app (by KKM Co., Ltd).
2. Connect the scanner gateway to your 2.4 GHz Wi-Fi network (5 GHz won't work here).
3. Enter the MQTT server details and the topic you want to publish to.
4. (Optional but recommended) Reduce network traffic from the beacon scanner by adjusting the filter settings to ignore all beacon MACs except the ones you're setting up.

> The [Blue Charm BCG04 Beacon Gateway starter guide](https://bluecharmbeacons.com/quick-start-guide-bcg04-usb-powered-ble-mini-gateway/) is pretty good at walking you through any additional setup process, but I think it's self-explanatory.

## Home Assistant Configuration

---

### Calendar Sensor

My waste pickup provider is lame because they don't provide an API for their pickup dates. 👎 Instead, they cram the schedule for all users and groups into a PDF calendar highlighting their holidays for the entire year.

I used to set up a Google Task/Reminder for each pickup day, but that was a pain to maintain. It seems like repeating tasks only show up on a rolling ~6-month window on my Google Calendar. This means I have to check back every few months to adjust the tasks around holidays as they appear on my calendar.

Instead, I created a separate Google Calendar that exclusively holds pickup dates for my trash and recycling. The benefit is that when my waste pickup provider releases their yearly calendar, I can update all pickup dates on my calendar _once_.

![Calendar view in Home Assistant showing the trash and recycling pickup dates for June, 2024.](/assets/img/2024/06/waste_pickup_calendar.png)*Waste collection calendar in Home Assistant*

I've connected this calendar to Home Assistant using the [Google Calendar integration](https://www.home-assistant.io/integrations/google/). I created some sensors around the calendar events to track future/current pickup days. This way, I can easily build automations and notifications around these events.

* Trash Tomorrow
* Recycling Tomorrow
* Trash Today
* Recycling Today

![Quick glance showing upcoming waste collection for each pickup type.](/assets/img/2024/06/pickup_quick_glance.png)*Waste collection quick-glance showing both bins will be picked up tomorrow, and both bins are still at the house.*

The template sensors below check the `waste_collection` Google Calendar for events `today` and `tomorrow` that contain the words `Trash` or `Recycling`. If it finds a matching event, it sets the sensor to `on`. If it doesn't find an event, the sensor stays `off`.

<!-- If an HTML tag has an attribute markdown="block", then the content of the tag is parsed as block level elements. -->
<!-- https://kramdown.gettalong.org/syntax.html#html-blocks -->
<details markdown="block">

<summary>[YAML] Calendar event sensors</summary>

```yaml
{% raw %}
template:
  - trigger:
      - platform: time_pattern
        # Let's be honest, we don't need to check often. 
        # But 5 minutes should be reactive enough if I need to correct an event date.
        minutes: "/5" 
    action:
      - service: calendar.get_events
        data:
          start_date_time: "{{ today_at() }}"
          end_date_time: "{{ today_at('23:59:59') }}"
        target:
          entity_id: calendar.waste_collection
        response_variable: agenda_today
      - service: calendar.get_events
        data:
          start_date_time: "{{ today_at() + timedelta(days=1) }}"
          end_date_time: "{{ today_at('23:59:59') + timedelta(days=1) }}"
        target:
          entity_id: calendar.waste_collection
        response_variable: agenda_tomorrow
    binary_sensor:
      - name: Trash Today
        unique_id: trash_today
        state: |-
          {% set search_term = "Trash" %}
          {{ agenda_today['calendar.waste_collection'].events
          | selectattr('summary', 'search', search_term) | list | count > 0 }}
      - name: Recycling Today
        unique_id: recycling_today
        state: |-
          {% set search_term = "Recycling" %}
          {{ agenda_today['calendar.waste_collection'].events
          | selectattr('summary', 'search', search_term) | list | count > 0 }}
      - name: Trash Tomorrow
        unique_id: trash_tomorrow
        state: |-
          {% set search_term = "Trash" %}
          {{ agenda_tomorrow['calendar.waste_collection'].events
          | selectattr('summary', 'search', search_term) | list | count > 0 }}
      - name: Recycling Tomorrow
        unique_id: recycling_tomorrow
        state: |-
          {% set search_term = "Recycling" %}
          {{ agenda_tomorrow['calendar.waste_collection'].events
          | selectattr('summary', 'search', search_term) | list | count > 0 }}
{% endraw %}
```
</details>

---

### RSSI and Battery Sensors

Next, we have the RSSI and battery sensors. These sensors are used to track the signal strength of the Bluetooth beacons and the estimated remaining battery life.

* Trash Bin RSSI
* Trash Bin Battery
* Recycling Bin RSSI
* Recycling Bin Battery

The MQTT messages from the Blue Charm BCG04 gateway can be ingested by Home Assistant through MQTT sensors. I realllly wish that the gateway assigned to each beacon had a different MQTT topic, like the [rtl_433 project](https://github.com/merbanan/rtl_433). Instead, the beacon gateway groups all beacon data into a JSON array which is published to a single MQTT topic. It does this because the beacon gateway batches all events before publishing them at each 'send interval' to reduce overhead. This requires the user to loop through and filter the incoming data to find the information that they want from it.

If the beacon gateway was sending events using different topics, it would have been _much_ easier to persist the beacon state between reboots or identify when a beacon had last sent a signal. But I _understand_ it's a lot easier to manage a single MQTT topic for all beacons when the beacon gateway is batching the events together. Especially on lower-powered hardware.

I've worked around these limitations in the sensors below.

<details markdown="block">

<summary>[YAML] MQTT RSSI and battery sensors</summary>

```yaml
{% raw %}
mqtt:
  sensor:
  # REPLACE: BEACON_GATEWAY_ID with the actual ID of your beacon gateway
  # REPLACE: TRASH_BEACON_UUID with the UUID of your trash bin beacon
  # REPLACE: RECYCLING_BEACON_UUID with the UUID of your recycling bin beacon
  # REPLACE: TRASH_BIN_DMAC with the DMAC of the trash bin Eddystone beacon
  # REPLACE: RECYCLING_BIN_DMAC with the DMAC of the recycling bin Eddystone beacon
  ##
  # Trash Bin
  ##
  - state_topic: "bluecharm/publish/BEACON_GATEWAY_ID"
    name: "Trash bin RSSI"
    unique_id: "trash_bin_rssi"
    device_class: signal_strength
    # Assume the sensor is too far away after 300 seconds of no updates
    expire_after: 300
    unit_of_measurement: "dBm"
    # Home Assistant ignores an empty value ('') and will not update the state of the entity.
    value_template: >-
      {% set targetUuidFound = namespace(found=False) %}
          {% for i in range(value_json.obj|count) -%}
              {% if value_json.obj[i].uuid == "TRASH_BEACON_UUID" and targetUuidFound.found == False %}
                  {{ value_json.obj[i].rssi }}
                  {% set targetUuidFound.found = True %}
              {%- endif %}
          {%- endfor %}
      {% set targetUuidFound = namespace(found=False) %}
    device:
      identifiers: ["trash_bin"]
      name: "Trash Bin"
      manufacturer: "Blue Charm"
      model: "BCG04"
      suggested_area: "Garage"
  - state_topic: "bluecharm/publish/BEACON_GATEWAY_ID"
    name: "Trash bin battery"
    unique_id: "trash_bin_battery"
    device_class: battery
    state_class: measurement
    unit_of_measurement: "%"
    # Home Assistant ignores an empty value ('') and will not update the state of the entity.
    # Sensor with CR2477 stops operating around is 2450 mV
    # Battery starts at 3.3V. Anything over 3.0V is considered 100%.
    # Assumes discharge curve is linear
    # Type 8 message is (Eddystone) TLM, which contains the battery information as mV
    value_template: >-
      {% set targetDmacFound = namespace(found=False) %}
          {% for i in range(value_json.obj|count) -%}
              {% if value_json.obj[i].dmac == "TRASH_BIN_DMAC" and value_json.obj[i].type == 8 and targetDmacFound.found == False %}
                  {% set stock_voltage = 3000 %}
                  {% set voltage_range = 550 %}
                  {% set current_voltage = value_json.obj[i].vbatt %}
                  {% set remaining_life = 0 %}

                  {% if current_voltage >= stock_voltage %}
                    {% set remaining_life = 100 %}
                  {% elif current_voltage > (stock_voltage - voltage_range) %}
                    {% set remaining_life = int((current_voltage - (stock_voltage - voltage_range)) / voltage_range * 100) %}
                  {% else %}
                    {% set remaining_life = 0 %}
                  {% endif %}
                  {{ remaining_life | int }}
                  {% set targetDmacFound.found = True %}
              {%- endif %}
          {%- endfor %}
      {% set targetDmacFound = namespace(found=False) %}
    device:
      identifiers: ["trash_bin"]
      name: "Trash Bin"
      manufacturer: "Blue Charm"
      model: "BCG04"
      suggested_area: "Garage"
  ##
  # Recycling Bin
  ##
  - state_topic: "bluecharm/publish/BEACON_GATEWAY_ID"
    name: "Recycling bin RSSI"
    unique_id: "recycling_bin_rssi"
    device_class: signal_strength
    # Assume the sensor is too far away after 300 seconds of no updates
    expire_after: 300
    unit_of_measurement: "dBm"
    # Home Assistant ignores an empty value ('') and will not update the state of the entity.
    value_template: >-
      {% set targetUuidFound = namespace(found=False) %}
          {% for i in range(value_json.obj|count) -%}
              {% if value_json.obj[i].uuid == "RECYCLING_BEACON_UUID" and targetUuidFound.found == False %}
                  {{ value_json.obj[i].rssi }}
                  {% set targetUuidFound.found = True %}
              {%- endif %}
          {%- endfor %}
      {% set targetUuidFound = namespace(found=False) %}
    device:
      identifiers: ["recycling_bin"]
      name: "Recycling Bin"
      manufacturer: "Blue Charm"
      model: "BCG04"
      suggested_area: "Garage"
  - state_topic: "bluecharm/publish/BEACON_GATEWAY_ID"
    name: "Recycling bin battery"
    unique_id: "recycling_bin_battery"
    device_class: battery
    state_class: measurement
    unit_of_measurement: "%"
    # Home Assistant ignores an empty value ('') and will not update the state of the entity.
    # Sensor with CR2477 stops operating around is 2450 mV
    # Battery starts at 3.3V. Anything over 3.0V is considered 100%.
    # Assumes discharge curve is linear
    # Type 8 message is (Eddystone) TLM, which contains the battery information as mV
    value_template: >-
      {% set targetDmacFound = namespace(found=False) %}
          {% for i in range(value_json.obj|count) -%}
              {% if value_json.obj[i].dmac == "RECYCLING_BIN_DMAC" and value_json.obj[i].type == 8 and targetDmacFound.found == False %}
                  {% set stock_voltage = 3000 %}
                  {% set voltage_range = 550 %}
                  {% set current_voltage = value_json.obj[i].vbatt %}
                  {% set remaining_life = 0 %}

                  {% if current_voltage >= stock_voltage %}
                    {% set remaining_life = 100 %}
                  {% elif current_voltage > (stock_voltage - voltage_range) %}
                    {% set remaining_life = int((current_voltage - (stock_voltage - voltage_range)) / voltage_range * 100) %}
                  {% else %}
                    {% set remaining_life = 0 %}
                  {% endif %}
                  {{ remaining_life | int }}
                  {% set targetDmacFound.found = True %}
              {%- endif %}
          {%- endfor %}
      {% set targetDmacFound = namespace(found=False) %}
    device:
      identifiers: ["recycling_bin"]
      name: "Recycling Bin"
      manufacturer: "Blue Charm"
      model: "BCG04"
      suggested_area: "Garage"
{% endraw %}
```
</details>

---

### Data Filters

The primary use of the [filter integration](https://www.home-assistant.io/integrations/filter/) is to smooth out the RSSI data from the Bluetooth beacons.

If you check out the graph below, you'll notice that the RSSI is more like a drunken hummingbird than a steady signal. But if you apply a smoothing filter, the RSSI values are pretty flat.

If I were to rely _only_ on the raw RSSI signals, my presence detections would be flipping back and forth multiple times per minute. The filtered values help reduce these false positives.

The filters I use are:

* Filtered trash bin RSSI
* Filtered recycling bin RSSI

![5-minute graph showing the raw RSSI values vs the filtered view](/assets/img/2024/06/trash_rssi_vs_filtered.png)*Trash Bin RSSI vs a smoother filtered RSSI view*

<details markdown="block">

<summary>[YAML] Filtered RSSI sensors</summary>

```yaml
{% raw %}
sensor:
  - platform: filter
    name: "Filtered trash bin RSSI"
    unique_id: filtered_trash_bin_rssi
    entity_id: sensor.trash_bin_rssi
    filters:
      - filter: outlier
        window_size: 5
        radius: 5.0
      - filter: lowpass
        time_constant: 10
        precision: 2
      - filter: time_simple_moving_average
        window_size: "00:01"
        precision: 2
  - platform: filter
    name: "Filtered recycling bin RSSI"
    unique_id: filtered_recycling_bin_rssi
    entity_id: sensor.recycling_bin_rssi
    filters:
      - filter: outlier
        window_size: 5
        radius: 5.0
      - filter: lowpass
        time_constant: 10
        precision: 2
      - filter: time_simple_moving_average
        window_size: "00:01"
        precision: 2
{% endraw %}
```
</details>

---

### Vibration Sensors

Next, we have our vibration sensors. This is what we use to detect when the bins have been picked up/emptied.

* Trash Bin Vibration
* Recycling Bin Vibration

![Home Assistant history graph showing the vibration sensor state for the trash and recycling bin Bluetooth beacons](/assets/img/2024/06/waste_vibration.png)*Vibration sensor states for the trash and recycling bins around morning pickup.*

Below are these sensors, created from the MQTT data that the Blue Charm BCG04 beacon gateway sends over. 

<details markdown="block">

<summary>[YAML] MQTT vibration binary sensors</summary>

```yaml
{% raw %}
mqtt:
  binary_sensor:
  # REPLACE: BEACON_GATEWAY_ID with the actual ID of your beacon gateway
  # REPLACE: TRASH_BIN_VIBRATION_UUID with the UUID of your trash bin vibration UUID
  # REPLACE: RECYCLING_BIN_VIBRATION_UUID with the UUID of your recycling bin vibration UUID
  ##
  # Trash bin
  ##
  - state_topic: "bluecharm/publish/BEACON_GATEWAY_ID"
    name: "Trash bin vibration"
    unique_id: "trash_bin_vibration"
    # off_delay of 30s so we don't get spammed with the vibration state changing
    off_delay: 30
    device_class: vibration
    # Home Assistant ignores an empty value ('') and will not update the state of the entity.
    value_template: >-
      {% set targetUuidFound = namespace(found=False) %}
          {% for i in range(value_json.obj|count) -%}
              {% if value_json.obj[i].uuid == "TRASH_BIN_VIBRATION_UUID" and targetUuidFound.found == False %}
                  ON
                  {% set targetUuidFound.found = True %}
              {%- endif %}
          {%- endfor %}
      {% set targetUuidFound = namespace(found=False) %}
    device:
      identifiers: ["trash_bin"]
      name: "Trash Bin"
      manufacturer: "Blue Charm"
      model: "BCG04"
      suggested_area: "Garage"
  ##
  # Recycling Bin
  ##
  - state_topic: "bluecharm/publish/BEACON_GATEWAY_ID"
    name: "Recycling bin vibration"
    unique_id: "recycling_bin_vibration"
    # off_delay of 30s so we don't get spammed with the vibration state changing
    off_delay: 30
    device_class: vibration
    # Home Assistant ignores an empty value ('') and will not update the state of the entity.
    value_template: >-
      {% set targetUuidFound = namespace(found=False) %}
          {% for i in range(value_json.obj|count) -%}
              {% if value_json.obj[i].uuid == "RECYCLING_BIN_VIBRATION_UUID" and targetUuidFound.found == False %}
                  ON
                  {% set targetUuidFound.found = True %}
              {%- endif %}
          {%- endfor %}
      {% set targetUuidFound = namespace(found=False) %}
    device:
      identifiers: ["recycling_bin"]
      name: "Recycling Bin"
      manufacturer: "Blue Charm"
      model: "BCG04"
      suggested_area: "Garage"
{% endraw %}
```
</details>

---

### Presence Sensors

Before I dive into the presence sensors, let's cover some new [`Input number`](https://www.home-assistant.io/integrations/input_number/) helper sensors that I created in the UI. 

<details>
<summary>input_number threshold sensor UI</summary>

{{ "![Home Assistant UI showing the creation of an input_number threshold sensor](/assets/img/2024/06/rssi_threshold_ui.png)*Home Assistant UI showing the creation of an `input_number` threshold sensor.*" | markdownify }}

</details>

* Trash bin RSSI threshold (Number): `input_number.trash_bin_rssi_threshold`
* Recycling bin RSSI threshold (Number): `input_number.recycling_bin_rssi_threshold`

These `input_number` sensors set the RSSI thresholds that we use to determine if the bins are `home` or `away`. These are not strictly required but make configuration a lot easier. 

![Home Assistant card showing the input_number threshold sensors](/assets/img/2024/06/threshold_sensors.png)*Home Assistant card showing the input_number threshold sensors.*

> In the binary presence sensors below, we'll use our newly created threshold sensor to set and adjust the `home`/`away` threshold for the filtered RSSI value. Any future adjustments can be made in the Home Assistant UI dashboard _without_ needing to edit a YAML file. 

Let's continue onto the presence sensors. These sensors use the _filtered_ RSSI sensors that we created earlier to determine if the bins are still at the house or down by the curb.

* Trash Bin Present
* Recycling Bin Present

![Home Assistant history graph showing the presence state for the trash and recycling bin Bluetooth beacons](/assets/img/2024/06/waste_presence.png)*Presence states for the trash and recycling bins as I roll them down to the curb. If the bins are "Home", they're up at the house. If the bins are "Away", they're at the curb.*

Here are the unconventional things I'm doing with the presence sensors. 

* The presence sensor will not update if the beacon is too far away from our gateway. This is why I have a 5-minute expiry time on the presence sensors. If we haven't heard a signal from the beacon in 5 minutes, the sensor value expires and defaults to `away`. This is a good way to handle the case where the beacon moves out of range before we consider the signal "weak".
* The sensor is getting updated inefficiently. I use the MQTT payload as the _trigger_ to update the presence sensor state. It's easier to read and understand when things are located near each other in the code. The more efficient route would be to set up _another_ template sensor elsewhere that is triggered by updates to the filtered RSSI values.
* If we reboot, the presence sensor will temporarily be `unknown`. This is because our presence sensor is comparing the "RSSI threshold" against the "_filtered_ RSSI value". On a fresh boot, our "filtered RSSI value" won't have any data yet. So we need to wait until we receive a few messages from the Bluetooth beacon before it starts generating values.

<details markdown="block">

<summary>[YAML] MQTT presence binary sensors</summary>

```yaml
{% raw %}
mqtt:
  binary_sensor:
  # REPLACE: BEACON_GATEWAY_ID with the actual ID of your beacon gateway
  # REPLACE: TRASH_BEACON_UUID with the UUID of your trash bin beacon
  # REPLACE: RECYCLING_BEACON_UUID with the UUID of your recycling bin beacon
  ##
  # Trash bin
  ##
  - state_topic: "bluecharm/publish/BEACON_GATEWAY_ID"
    name: "Trash bin present"
    unique_id: "trash_bin_present"
    device_class: presence
    # Assume the sensor is too far away after 300 seconds of no updates
    off_delay: 300
    # Home Assistant ignores an empty value ('') and will not update the state of the entity.
    # Since this is using a filter that gets generated _after_ the RSSI sensor populates it, the
    # very first message (and possibly 2nd message) would not have populated the filter yet.
    # This is probably ok since the sensor should be updating ~every second and should resolve
    # itself in only a few seconds.
    # We also set this to expire after 300 seconds as the only other trigger is if we see message
    # that matches the UUID for this sensor.
    # We check if it's a number before we set the away status to fix a bug where the filtered RSSI is unknown on boot
    value_template: >-
      {% set targetUuidFound = namespace(found=False) %}
          {% for i in range(value_json.obj|count) -%}
              {% if value_json.obj[i].uuid == "TRASH_BEACON_UUID" and targetUuidFound.found == False %}
                  {% if states('sensor.filtered_trash_bin_rssi') | is_number and states('input_number.trash_bin_rssi_threshold') | is_number %}
                      {{ 'ON' if states('sensor.filtered_trash_bin_rssi') | float > states('input_number.trash_bin_rssi_threshold') | float else 'OFF' }}
                      {% set targetUuidFound.found = True %}
                  {%- endif %}
              {%- endif %}
          {%- endfor %}
      {% set targetUuidFound = namespace(found=False) %}
    device:
      identifiers: ["trash_bin"]
      name: "Trash Bin"
      manufacturer: "Blue Charm"
      model: "BCG04"
      suggested_area: "Garage"
  ##
  # Recycling Bin
  ##
  - state_topic: "bluecharm/publish/BEACON_GATEWAY_ID"
    name: "Recycling bin present"
    unique_id: "recycling_bin_present"
    device_class: presence
    # Assume the sensor is too far away after 300 seconds of no updates
    off_delay: 300
    # Home Assistant ignores an empty value ('') and will not update the state of the entity.
    # Since this is using a filter that gets generated _after_ the RSSI sensor populates it, the
    # very first message (and possibly 2nd message) would not have populated the filter yet.
    # This is probably ok since the sensor should be updating ~every second and should resolve
    # itself in only a few seconds.
    # We also set this to expire after 300 seconds as the only other trigger is if we see message
    # that matches the UUID for this sensor.
    # We check if it's a number before we set the away status to fix a bug where the filtered RSSI is unknown on boot
    value_template: >-
      {% set targetUuidFound = namespace(found=False) %}
          {% for i in range(value_json.obj|count) -%}
              {% if value_json.obj[i].uuid == "RECYCLING_BEACON_UUID" and targetUuidFound.found == False %}
                  {% if states('sensor.filtered_recycling_bin_rssi') | is_number and states('input_number.recycling_bin_rssi_threshold') | is_number %}
                      {{ 'ON' if states('sensor.filtered_recycling_bin_rssi') | float > states('input_number.recycling_bin_rssi_threshold') | float else 'OFF' }}
                      {% set targetUuidFound.found = True %}
                  {%- endif %}
              {%- endif %}
          {%- endfor %}
      {% set targetUuidFound = namespace(found=False) %}
    device:
      identifiers: ["recycling_bin"]
      name: "Recycling Bin"
      manufacturer: "Blue Charm"
      model: "BCG04"
      suggested_area: "Garage"
{% endraw %}
```
</details>

---

## Automations

High-level: I have 3 automations here.

1. Send a notification to the family to take out the bins on the night before trash or recycling pickup.
2. Set or reset the "picked up" helper entities.
3. Send a notification to the family if the trash or recycling has been picked up.

I created the following helper entities in the UI to make managing the automations easier:

* Trash picked up (Toggle): `input_boolean.trash_picked_up`
* Recycling picked up (Toggle): `input_boolean.recycling_picked_up`

The input booleans (type: toggle) are used to track if the trash or recycling has been picked up. By breaking the events into these toggle switches, I can easily track what happens. This helps avoid cramming _everything_ in an already busy automation.

> Pro tip: If you want to automate low-battery alerts for the beacons, consider using one of the community-created [blueprints for battery sensors](https://community.home-assistant.io/t/low-battery-notifications-actions/653754).

Let's dive into the first automation.

---

### [Notification] Recycling or Trash removal tomorrow

This automation sends a notification the night before a scheduled pickup for either recycling or trash. 

- It reminds the family if the bins are still at the house
- It sends a confirmation if the bins are already at the curb (just in case the beacons somehow are stuck in `away` mode)
- It leverages an unnecessarily complicated flow to send a _different_ message if _both_ bins are scheduled for pickup tomorrow. Why send two notifications when you can send one? 🤔
- My automations don't listen for `home` and `away`. Instead, they check for `home` and `not home` because `not home` can include `away`, `unknown`, or `unavailable`. As we mentioned earlier, the presence state may be `unknown` when the server restarts. The automation is meant to fail gracefully if the sensor is in a bad state.

![Recycling and trash pickup tomorrow notification](/assets/img/2024/06/pickup_tomorrow_notification.jpg)*Recycling and trash bin pickup tomorrow notification*

<details markdown="block">

<summary>[Automation] Recycling or Trash removal tomorrow notification</summary>

```yaml
{% raw %}
alias: Recycling or Trash removal tomorrow notification
description: "Sends a notification if the recycling or trash is scheduled to be picked up tomorrow. But only if I haven't already taken the bins out.
"
trigger:
  - platform: time
    at: "16:30:00"
    id: trash
  - platform: time
    at: "16:30:00"
    id: recycling
action:
  - choose:
      - conditions:
          - condition: trigger
            id:
              - trash
          - condition: state
            entity_id: binary_sensor.trash_tomorrow
            state: "on"
          - condition: state
            entity_id: binary_sensor.recycling_tomorrow
            state: "off"
          - condition: or
            conditions:
              - condition: not
                conditions:
                  - condition: state
                    entity_id: binary_sensor.trash_bin_present
                    state: "off"
                alias: Test if trash is Home, Unavailable, or Unknown
            alias: Test if bin is at home
        sequence:
          - service: notify.family
            data:
              title: 🗑️ Trash!
              message: The trash has not been taken out yet. Pickup is tomorrow.
              data:
                ttl: 0
                priority: high
              data:
                notification_icon: mdi:dump-truck
                group: waste-removal-alert
                channel: waste-removal-alert
                push:
                  interruption-level: time-sensitive
      - conditions:
          - condition: trigger
            id:
              - recycling
          - condition: state
            entity_id: binary_sensor.recycling_tomorrow
            state: "on"
          - condition: or
            conditions:
              - condition: not
                conditions:
                  - condition: state
                    entity_id: binary_sensor.trash_bin_present
                    state: "off"
                alias: Test if trash is Home, Unavailable, or Unknown
              - condition: not
                conditions:
                  - condition: state
                    entity_id: binary_sensor.recycling_bin_present
                    state: "off"
                alias: Test if recycling is Home, Unavailable, or Unknown
            alias: Test if bins are at home
        sequence:
          - service: notify.family
            data:
              title: ♻️ Recycling & Trash!
              message: >-
                The recycling or trash have not been taken out yet. Pickup
                is tomorrow.
              data:
                ttl: 0
                priority: high  
              data:
                notification_icon: mdi:recycle
                group: waste-removal-alert
                channel: waste-removal-alert
                push:
                  interruption-level: time-sensitive
      - conditions:
          - condition: trigger
            id:
              - trash
          - condition: state
            entity_id: binary_sensor.trash_tomorrow
            state: "on"
          - condition: state
            entity_id: binary_sensor.recycling_tomorrow
            state: "off"
          - alias: Test if bin is not at home
            condition: or
            conditions:
              - alias: Test if trash is not at Home
                condition: not
                conditions:
                  - condition: state
                    entity_id: binary_sensor.trash_bin_present
                    state: "on"
        sequence:
          - service: notify.family
            data:
              title: 🗑️ Trash!
              message: The trash was already taken down. Was that you?
              data:
                ttl: 0
                priority: high  
              data:
                notification_icon: mdi:dump-truck
                group: waste-removal-alert
                channel: waste-removal-alert
                push:
                  interruption-level: time-sensitive
        alias: Trash tomorrow (bin not home)
      - conditions:
          - condition: trigger
            id:
              - recycling
          - condition: state
            entity_id: binary_sensor.recycling_tomorrow
            state: "on"
          - alias: Test if bin not at home
            condition: or
            conditions:
              - alias: Test if trash is not Home
                condition: not
                conditions:
                  - condition: state
                    entity_id: binary_sensor.trash_bin_present
                    state: "on"
              - alias: Test if recycling is not Home
                condition: not
                conditions:
                  - condition: state
                    entity_id: binary_sensor.recycling_bin_present
                    state: "on"
        sequence:
          - service: notify.family
            data:
              title: ♻️ Recycling & Trash?
              message: >-
                The recycling or trash were already taken down. Was that
                you?
              data:
                ttl: 0
                priority: high  
              data:
                notification_icon: mdi:recycle
                group: waste-removal-alert
                channel: waste-removal-alert
                push:
                  interruption-level: time-sensitive
        alias: Trash/Recycling tomorrow (bin not home)
mode: parallel
max: 2
{% endraw %}
```
</details>

---

### [State Helper] Recycling or Trash picked up

This automation controls the helper entities that indicate whether recycling or trash has been picked up. It helps simplify our automations and gives us a good idea what the current state of the bins are from the dashboard.

- When the `input_boolean.*_picked_up` helper is `on`, it means the bin has been picked up.
- When the `input_boolean.*_picked_up` helper is `off`, it means the bin has been returned to the house.

> There is a possibility that the notification could go off by mistake if the vibration sensor is triggered by something else _before_ the pickup. But I haven't had a car hit my bins yet... 🤞

This automation starts when either the vibration sensor is triggered (waste picked up) or the presence sensor switches to `home` (bin returned home).

The helper entities are only turned `on` if the following conditions are met:

1. The vibration sensor is triggered (waste picked up)
2. The bin is currently `away` (by the curb)
3. The bin is scheduled for pickup that day

The helper entities are only turned `off` if the following conditions are met:

1. The bin returns to the house for at least 1 minute (to prevent false positives)
2. The bin is scheduled for pickup that day

> I guess if I forget to bring the bins back up on pickup day, it won't reset the helper. But I'm usually pretty good at being a responsible adult and retrieving them on the same day. I could always remove that `return` condition if this becomes a problem.

<details markdown="block">

<summary>[Automation] Recycling or Trash picked up - state helper</summary>

```yaml
{% raw %}
alias: Recycling or Trash picked up helper
description: >-
  Update the helpers that indicate whether recycling or trash has been picked
  up, but not brought back up
trigger:
  - platform: state
    entity_id:
      - binary_sensor.trash_bin_vibration
    to: "on"
    id: trash-picked-up
  - platform: state
    entity_id:
      - binary_sensor.trash_bin_present
    to: "on"
    id: trash-brought-in
    for:
      hours: 0
      minutes: 1
      seconds: 0
  - platform: state
    entity_id:
      - binary_sensor.recycling_bin_vibration
    to: "on"
    id: recycling-picked-up
  - platform: state
    entity_id:
      - binary_sensor.recycling_bin_present
    to: "on"
    id: recycling-brought-in
    for:
      hours: 0
      minutes: 1
      seconds: 0
condition: []
action:
  - choose:
      - conditions:
          - condition: trigger
            id:
              - trash-picked-up
          - condition: state
            entity_id: binary_sensor.trash_today
            state: "on"
          - condition: state
            entity_id: binary_sensor.trash_bin_present
            state: "off"
        sequence:
          - service: input_boolean.turn_on
            metadata: {}
            data: {}
            target:
              entity_id: input_boolean.trash_picked_up
      - conditions:
          - condition: trigger
            id:
              - trash-brought-in
          - condition: state
            entity_id: binary_sensor.trash_today
            state: "on"
        sequence:
          - service: input_boolean.turn_off
            target:
              entity_id: input_boolean.trash_picked_up
            data: {}
      - conditions:
          - condition: trigger
            id:
              - recycling-picked-up
          - condition: state
            entity_id: binary_sensor.recycling_today
            state: "on"
          - condition: state
            entity_id: binary_sensor.recycling_bin_present
            enabled: true
            state: "off"
        sequence:
          - service: input_boolean.turn_on
            metadata: {}
            data: {}
            target:
              entity_id: input_boolean.recycling_picked_up
      - conditions:
          - condition: trigger
            id:
              - recycling-brought-in
          - condition: state
            entity_id: binary_sensor.recycling_today
            state: "on"
        sequence:
          - service: input_boolean.turn_off
            metadata: {}
            data: {}
            target:
              entity_id: input_boolean.recycling_picked_up
mode: parallel
max: 2
{% endraw %}
```
</details>

---

### [Notification] Recycling or Trash picked up

This automation sends a notification to the family when the recycling or trash bins have been picked up. If either bin has not been returned by 5 PM, another reminder is sent to the family.

> My automation includes a camera snapshot in the notification. This allows me to quickly verify that the bin was picked up by the truck, and not just bumped by a car. Feel free to remove that from the automation below since it's super specific to my setup.

![Recycling and trash bin pickup notification](/assets/img/2024/06/pickup_notification.jpg)*Recycling and trash bin pickup notification*

This automation starts from either of the following conditions: 

- Either of the `input_boolean.*_picked_up` helpers are turned `on`
- The time is 5 PM (and the bins haven't been brought back up)

I did a silly complex thing in my automation where I gate my pickup notifications. If it's a trash-only day, I send the notification as soon as the trash is picked up. 

However, if it's a trash _and_ recycling day, then I wait for _both_ bins to be picked up before sending a notification... also, I change the notification text depending on if it's trash-only, or trash _and_ recycling. ✨

<details markdown="block">

<summary>[Automation] Recycling or Trash picked up notification</summary>

```yaml
{% raw %}
alias: Recycling or Trash picked up notification
description: >-
  Change helper boolean and send notification when one (or waiting for both)
  trash and recycling have been picked up
trigger:
  - platform: state
    entity_id:
      - input_boolean.trash_picked_up
    to: "on"
    from: "off"
    id: trash
  - platform: state
    entity_id:
      - input_boolean.recycling_picked_up
    to: "on"
    from: "off"
    id: recycling
  - platform: time
    at: "17:00:00"
    id: bin-reminder
action:
  - choose:
      - conditions:
          - condition: trigger
            id:
              - trash
          - condition: state
            entity_id: binary_sensor.recycling_today
            state: "off"
            alias: Only send this alert if it's not a recycling day
        sequence:
          - service: camera.snapshot
            data:
              # I place my camera snapshot here because I have another notification channel elsewhere 
              #  that shows the image on my TV using "Notifications for Android TV"
              #  https://www.home-assistant.io/integrations/nfandroidtv/
              # I gate (and duplicate) this snapshot sequence a few more times that way I take a snapshot 
              #  only when I'm about to send one. 
              # That's because I like to see the last pickup image on my dashboard.
              filename: /config/www/tmp/snapshot_camera_proxy_driveway_wide.jpg
            target:
              entity_id:
                # I use a proxy camera to create a cropped view of the driveway for a zoomed-in picture
                #  https://www.home-assistant.io/integrations/proxy/
                - camera.driveway_proxy
          - delay:
              hours: 0
              minutes: 0
              seconds: 1
              milliseconds: 0
          - service: notify.family
            data:
              title: 🗑️ Trash picked up
              message: The trash bin has been picked up.
              data:
                ttl: 0
                priority: high  
              data:
                notification_icon: mdi:dump-truck
                group: waste-removal-alert
                channel: waste-removal-alert
                image: /local/tmp/snapshot_camera_proxy_driveway_wide.jpg
                push:
                  interruption-level: time-sensitive
      - conditions:
          - condition: trigger
            id:
              - trash
              - recycling
          - condition: or
            conditions:
              - condition: state
                entity_id: input_boolean.recycling_picked_up
                state: "on"
              - condition: state
                entity_id: binary_sensor.recycling_bin_present
                state: "on"
            alias: Recycling has been picked up, or taken inside
          - condition: or
            conditions:
              - condition: state
                entity_id: input_boolean.trash_picked_up
                state: "on"
              - condition: state
                entity_id: binary_sensor.trash_bin_present
                state: "on"
            alias: Trash has been picked up, or taken inside
        sequence:
          - service: camera.snapshot
            data:
              filename: /config/www/tmp/snapshot_camera_proxy_driveway_wide.jpg
            target:
              entity_id:
                - camera.driveway_proxy
          - delay:
              hours: 0
              minutes: 0
              seconds: 1
              milliseconds: 0
          - service: notify.family
            data:
              title: ♻️🗑️ Recycling & trash picked up
              message: The recycling & trash bins have been picked up.
              data:
                ttl: 0
                priority: high  
              data:
                notification_icon: mdi:dump-truck
                group: waste-removal-alert
                channel: waste-removal-alert
                image: /local/tmp/snapshot_camera_proxy_driveway_wide.jpg
                push:
                  interruption-level: time-sensitive
      - conditions:
          - condition: trigger
            id:
              - bin-reminder
          - alias: Recycling or trash hasn't been picked up
            condition: or
            conditions:
              - condition: state
                entity_id: input_boolean.recycling_picked_up
                state: "on"
              - condition: state
                entity_id: input_boolean.trash_picked_up
                state: "on"
        sequence:
          - service: camera.snapshot
            data:
              filename: /config/www/tmp/snapshot_camera_proxy_driveway_wide.jpg
            target:
              entity_id:
                - camera.driveway_proxy
          - delay:
              hours: 0
              minutes: 0
              seconds: 1
              milliseconds: 0
          - service: notify.family
            data:
              title: ♻️🗑️ Recycling or trash picked up
              message: The recycling or trash bins still haven't been picked up.
              data:
                ttl: 0
                priority: high  
              data:
                notification_icon: mdi:dump-truck
                group: waste-removal-alert
                channel: waste-removal-alert
                image: /local/tmp/snapshot_camera_proxy_driveway_wide.jpg
                push:
                  interruption-level: time-sensitive
mode: single
{% endraw %}
```
</details>

---

### [Notification] Health Check for Bluetooth Beacons

I'm a bit of a control freak when it comes to my Bluetooth beacons. Let's just say I have a bat signal set up if one of those little guys starts misbehaving. It's stupidly simple.

Any night before a pickup at 7 PM, I get a notification if:

- The presence sensor for any Bluetooth beacon is `unknown`
  - Like if it didn't recover after my server rebooted
- The RSSI sensor for any beacon hasn't been updated in the last 15 minutes
  - This only works if the beacon is still in range while down at the curb

![Bluetooth beacon health check notification](/assets/img/2024/06/beacon_healthcheck_notification.png)*Bluetooth beacon health check notification*

Since I'm not expecting to see these scenarios happen too often, I didn't template out the notification text. Instead, it's a generic one.

<details markdown="block">

<summary>[Automation] Health check notification for Bluetooth beacons</summary>

```yaml
{% raw %}
alias: Health check for Bluetooth beacons
description: "Send a notification if the presence sensor for the Bluetooth beacons have been unknown for a while."
trigger:
  - platform: time
    at: "19:00:00"
condition:
  - condition: or
    conditions:
      - condition: state
        entity_id: binary_sensor.trash_tomorrow
        state: "on"
      - condition: state
        entity_id: binary_sensor.recycling_tomorrow
        state: "on"
  - condition: or
    conditions:
      - condition: state
        entity_id: binary_sensor.trash_bin_present
        state: unknown
      - condition: state
        entity_id: binary_sensor.recycling_bin_present
        state: unknown
      - condition: template
        alias: Test if Trash Bin RSSI is older than 15 minutes
        value_template: >-
          {{ (as_timestamp(now()) -
          as_timestamp(states.sensor.trash_bin_rssi.last_updated)) > 900 }}
      - condition: template
        alias: Test if Recycling Bin RSSI is older than 15 minutes
        value_template: >-
          {{ (as_timestamp(now()) -
          as_timestamp(states.sensor.recycling_bin_rssi.last_updated)) > 900 }}
action:
  - service: notify.family
    data:
      title: 📡 Bluetooth beacon state unknown
      message: >-
        One of the Bluetooth beacon's presence sensor has been unknown for a while.
        Please investigate.
      data:
        ttl: 0
        priority: high  
      data:
        notification_icon: mdi:radio-tower
        group: bluetooth-beacon-alert
        channel: bluetooth-beacon-alert
        push:
          interruption-level: time-sensitive
mode: single
{% endraw %}
```
</details>

#### Handling 'Unknown' States

You may remember from an earlier configuration that if I reboot the server, the beacon presence sensor will temporarily be `unknown` until the filtered RSSI sensor is populated from data. There's a _small_ window when:

1. Rebooting the server..
2. The night before a pickup..
3. At 7 PM..
4. For only a few seconds.. 
5. While the automation is triggering..

where the Bluetooth beacons _could_ be in an `unknown` state.

This scenario is so small that I just don't care about it. 99.99% is good enough for my home. If it's that big of a deal, I'll add a condition around the [`uptime`](https://www.home-assistant.io/integrations/uptime/) sensor.

#### Handling 'Stuck' States

I hope that if my beacon gets stuck, it will _stay_ stuck. My automation has a condition to check if any of the RSSI sensors have been updated recently. When the weekly check triggers, if the sensor hasn't been updated in the last 15 minutes, I'll get a notification. This check isn't very useful if the beacon normally exits the range of the scanner gateway.

#### Handling 'Away' States

My automations sorta cover the scenario where the beacon presence is stuck in an `away` state. 

> As a reminder, the presence sensor is set to expire to the `off`/`away` state after 5 minutes if there haven't been any updates.

If my beacon is stuck in the `away` state _after_ pickup, I'll _probably_ notice. That's because one of my automations earlier sends an additional reminder if I haven't "returned" the bins to my house by `5 PM`.

If my beacon is stuck in the `away` state _before_ pickup, I'm kinda hosed. I might miss the "Recycling or Trash removal tomorrow" notification if my system thinks that the bin is already down by the curb. 

To cover me, the "Recycling or Trash removal tomorrow" will also notify me if the bins have _already been taken down_. I'm going to get a notification whether I want one or not. 🥊

This allows me to double-check that _I_ took the bin down and that the sensor didn't just spit out some garbage (pun intended).

Possible alternatives:

- **Unpredictable**: Add additional checks to see if the bin was set to `away` at a weird time.
- **Unreliable**: Add additional checks throughout the evening to make sure the bin is _still_ `away` just in case it was temporarily `away` during the first check.
- **Most expensive**: Add biometric tracking with AI on an edge device to verify that a living human took the bins down... but it sounds like fun for [Frigate](https://github.com/blakeblackshear/frigate) and I could _totally_ do this. 📷
- **Easiest**: A confirmation notification saying "The bin was already taken down, was that you?".

## Lessons Learned (So Far)

- Tuning is Key: Adjusting the signal strength thresholds and vibration sensitivity is crucial to getting accurate results.
- Calendars Over Reminders: Using a calendar integration for trash day schedules is more reliable than reminders/tasks.
- Health Checks: A simple automation to check the presence sensor's state weekly helps prevent unexpected issues.

## What's Next?

I'm excited to see how this system performs in the long run. I'm going to watch and tweak it if any problems arise.

If you're interested in creating your smart trash system, feel free to use my configuration as a starting point. If you have any questions or suggestions, drop a comment below!

Happy automating! 🏡📡 🗑️♻️ 🚛 
