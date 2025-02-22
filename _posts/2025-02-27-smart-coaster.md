---
title: "Smart Coaster: Drink More Water"
date: '2025-02-21 8:00'
comments: true
image:
  path: /assets/img/2025/02/smart_coaster_front.jpg
  height: 603
  width: 800
alt: Smart coaster build from the front
published: true
tag: "small project"
description: "TODO: Building a smart coaster to remind me to drink water."
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

I often forget to drink water. I get pulled deep into my coding or long meetings where an entire afternoon flies by in a blink. It has become a bit of a problem where I'll go the entire day without drinking anything. I wanted to address this in the best way I know how. By building "temporarily permanent"™ prototypes.

## Solutions

Before arriving at my own solution, I looked at what was already available:

- Smart water bottles
  - Expensive
  - Requires some kind of mobile app
  - Need charging
- Water Tracking Apps
  - If I drink water, I have to remember to log it in the app.
  - It's another app..

But I had an idea. What a bout a smart coaster? 

I originally thought about tracking the volume of liquid. I looked into load sensors, but those are so expensive and can be finicky if I change bottles/cups. Instead, I'm using a time of flight sensor. It shoots and laser and reads it back to determine the distance. In my case, if anything is close, I assume it's the water bottle. They're also super compact.

- Load Cells
  - Small flat cells seem a bit more exotic
  - Not many options with ESPHome
  - Could be finicky depending on the bottle or cup being used
- Ultra Sonic Sensor
  - Larger
  - Possible noise issues with signal
- Time of Flight Sensor
  - Tiny
  - Easily available
  - The VL53L0X is [supported by ESPHome](https://esphome.io/components/sensor/vl53l0x.html)
  
This would make my solution more universal.

## Let's Build It

### First Attempt

90° angle
bad for close range with ToF sensor
used wood glue. Had to knock it off with a hammer.

![Wood boards glued and clamped together to make a coaster prototype](/assets/img/2025/02/smart_coaster_first_design.jpg)*My first attempt to build the smart coaster. I later decided mounting the sensor at 90° would make the sensor too close to the bottle.*

### Second Attempt

Tested with mounting tape
glued the boards together after testing
mounted the sensor at 45°
hot glued the ESP32S3 down
added gel pad to keep coaster still on the desk and dampen vibrations
my temporary prototype solution is good enough to be permanent

![Wood boards mounted together at an angle with tape](/assets/img/2025/02/smart_coaster_taped.jpg)*First assembled protoype. Instead of using wood glue, I leared from my past mistake and assembled this one with mounting tape.*

### Finishing Touches

- Seeed Studio XIAO ESP32S3
- VL53L0X
  - Supported by ESPHome: https://esphome.io/components/sensor/vl53l0x.html
- Wood Glue
- Hot Glue
- Coaster
- Mounting tape
- Silicone gel pad to keep the coaster still

![Smart coaster build from the front](/assets/img/2025/02/smart_coaster_front.jpg)*Final smart coaster from the front.*

![Smart coaster build from the rear; showing wiring](/assets/img/2025/02/smart_coaster_rear_wiring.jpg)*Final smart coaster with the Seeed Studio XIAO ESP32S3 hot glued down.*

## Programming

## Build with ESPHome


If I haven't removed my water bottle from the coaster after a set amount of time, I'll receive a notification on my devices and laptop to take a drink.

I'm prototyping a smart coaster. But if we're being real, I'm just going to throw some glue on it, attach some rubber feet, and it's going to magically turn into temporarily permanent. 

## Home Assistant Automations

{% include video.html
  src="/assets/files/2025/02/drink_water.mp4"
  poster="/assets/files/2025/02/drink_water_poster.png"
  controls="autoplay loop"
%}

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

## Required Components
1. Create a timer in the UI that will run for 45 minutes.

## Optional Components
1. Create a counter in the UI that will increment every time I pick up my water bottle.
2. Create a sensor in the UI of the counter's state
3. Create a utility meter of the sensor that resets daily to track how many times I've picked up my water bottle.



## Conclusion

![Smart coaster build with Home Assistant dashboard showing data in the back](/assets/img/2025/02/smart_coaster_integration.jpg)*Smart coaster with its data being displayed on my Home Assistant dashboard.*

My temporary solution is good enough to be permanent. It's helping break my attention to take water breaks. 





<details markdown="block">

<summary>[Yaml] ESPHome Configuration</summary>

{% raw %}
```yaml
# Basic Config
# esp-32-s3-01
# Smart Coaster
# Update for 2025.2.0

substitutions:
  devicename: Smart Coaster
  deviceid: coaster

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

  # Enable fallback hotspot (captive portal) in case wifi connection fails
  ap:
    ssid: "${devicename} Hotspot"
    password: !secret ap_hotspot_password

# Enable captive portal if wifi ever changes
captive_portal:

# Enable Home Assistant API
api:
  encryption:
    key: !secret encryption_pre_shared_key

ota:
  platform: esphome
  password: !secret ota_password

esphome:
  name: ${devicename}
  comment: ${devicename}
  friendly_name: ${devicename}

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: arduino

# Enable logging
logger:

i2c:
  id: bus_a
  sda: GPIO05
  scl: GPIO06
  scan: true

sensor:
  - platform: vl53l0x
    id: vl53l0x_sensor
    name: "VL53L0x Distance"
    update_interval: 500ms
    unit_of_measurement: "mm"
    filters:
      - multiply: 1000

binary_sensor:
  - platform: template
    name: "Water Bottle Present"
    lambda: |-
      if (id(vl53l0x_sensor).has_state()) {
        // 150 mm threshold
        return id(vl53l0x_sensor).state < 150;
      } else {
         // Return false if the sensor has no state yet
        return false;
      }
    device_class: occupancy

# Enables status LED
status_led:
  pin: 
    number: GPIO21
    inverted: true
```
{% endraw %}
</details>

<details markdown="block">

<summary>[Yaml] Home Assistant Action</summary>

{% raw %}
```yaml
alias: Water Bottle Drink Timer & Alerts
description: Automation to notify me when I haven't had anything to drink for a while.
triggers:
  - trigger: event
    event_type: timer.finished
    event_data:
      entity_id: timer.water_bottle_timer
    id: timer-finished
    alias: Water bottle timer finishes
  - alias: Water bottle picked up
    trigger: state
    entity_id:
      - binary_sensor.esp_32_s3_01_water_bottle_present
    to: "off"
    id: reset-timer
    from: "on"
    for:
      hours: 0
      minutes: 0
      seconds: 1
  - trigger: time
    at: "08:00:00"
    id: start-timer
    alias: Start Timer (Morning)
  - trigger: time
    at: "13:00:00"
    alias: Start Timer (Afternoon)
    id: start-timer
  - trigger: state
    entity_id:
      - binary_sensor.mac_device_active
    attribute: Screen Off
    to: "false"
    from: "true"
    alias: Screen turns on
    id: screen-on
conditions:
  - alias: During normal work week
    condition: time
    after: "07:55:00"
    before: "16:30:00"
    weekday:
      - mon
      - tue
      - wed
      - thu
      - fri
actions:
  - choose:
      - conditions:
          - condition: trigger
            id:
              - start-timer
          - condition: state
            entity_id: binary_sensor.esp_32_s3_01_water_bottle_present
            state: "on"
        sequence:
          - action: timer.cancel
            metadata: {}
            data: {}
            target:
              entity_id: timer.water_bottle_timer
          - action: timer.start
            metadata: {}
            data: {}
            target:
              entity_id: timer.water_bottle_timer
      - conditions:
          - condition: trigger
            id:
              - reset-timer
        sequence:
          - action: timer.cancel
            metadata: {}
            data: {}
            target:
              entity_id: timer.water_bottle_timer
          - action: timer.start
            metadata: {}
            data: {}
            target:
              entity_id: timer.water_bottle_timer
          - parallel:
              - action: counter.increment
                metadata: {}
                data: {}
                target:
                  entity_id: counter.drink_counter
              - data:
                  message: clear_notification
                  data:
                    group: water-drink-alert
                    channel: water-drink-alert
                    tag: water-drink-alert
                    data:
                      ttl: "0"
                      priority: high
                    push:
                      interruption-level: time-sensitive
                action: notify.kyle
                alias: Clear notify.kyle
      - conditions:
          - condition: trigger
            id:
              - timer-finished
          - condition: not
            conditions:
              - condition: time
                after: "11:55:00"
                before: "13:05:00"
            alias: Not during lunch
          - alias: Mac screen on
            condition: state
            entity_id: binary_sensor.mac_device_active
            attribute: Screen Off
            state: false
          - condition: state
            entity_id: input_boolean.mobile_notifications
            state: "on"
          - condition: state
            entity_id: input_boolean.water_drink_notifications
            state: "on"
        sequence:
          - parallel:
              - data:
                  # My cheater way to convert the duration into minutes for my notification.
                  message: >-
                    You haven't had anything to drink in the last {% set
                    remaining_time = state_attr('timer.water_bottle_timer',
                    'duration').split(':') %}{{remaining_time[0] | int * 60 +
                    remaining_time[1] | int }} minutes.
                  title: 🥤 Drink some water
                  data:
                    notification_icon: mdi:beer
                    group: water-drink-alert
                    channel: water-drink-alert
                    tag: water-drink-alert
                    data:
                      ttl: "0"
                      priority: high
                    push:
                      interruption-level: time-sensitive
                    actions:
                      - action: TEMP_WATER_DRINK_NOTIFICATION_MUTE
                        title: Mute (Today)
                action: notify.kyle
              - action: timer.start
                metadata: {}
                data:
                  duration: "00:05:00"
                target:
                  entity_id: timer.water_bottle_timer
                alias: Short timer restart (reminder)
      - conditions:
          - condition: trigger
            id:
              - screen-on
          - condition: not
            conditions:
              - condition: state
                entity_id: timer.water_bottle_timer
                state: active
            alias: If timer not running
        sequence:
          - action: timer.cancel
            metadata: {}
            data: {}
            target:
              entity_id: timer.water_bottle_timer
          - action: timer.start
            metadata: {}
            data: {}
            target:
              entity_id: timer.water_bottle_timer
mode: single
```
{% endraw %}
</details>

