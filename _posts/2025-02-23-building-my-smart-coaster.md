---
title: "The Smart Coaster That Keeps Me Hydrated"
date: '2025-02-23 20:01'
updated: '2025-05-05 06:22'
comments: true
image:
  path: /assets/img/2025/02/smart_coaster_front.jpg
  height: 603
  width: 800
alt: Smart coaster build from the front
published: true
tag: "small project"
description: "Forget smart water bottles! I created a 'temporarily permanent' smart coaster to solve my dehydration woes. If I've lost track, my coaster nudges me to drink water, and refrains when I've kept up."
amp:
  - video
---

I keep forgetting to drink water. Between the consecutive meetings and blocks of coding, my water intake has slipped. In the mere blink of an eye, my afternoon passes by, and I end up in a dehydrated wasteland. The solution seems so easy. Drink more water! But it's a recurring battle. My tendency to hyper-focus leaves me parched. So how do I fix this?

Do I set a timer? Should I buy a luxurious smart water bottle? Should I research the best water tracking app for my phone?

Or should I throw a bunch of glue, wood, and my favorite electronics together to construct something new? ✨

In an effort to quickly deliver value, join me on my self-imposed 48-hour project.

{% include toc.html %}

## Possible Solutions

Let's start with the easiest way to fix my problem. Buying someone else's solution. 💸

> I barely spent any time researching these solutions before I pivoted to my own. If I missed a good option, it was in the name of "getting something done". 🤷‍♂️

### Water Tracking Apps

The first possible solution I came across was a water tracking app. The idea is that you buy (or subscribe to) an app that reminds you to drink water. It's a simple concept. You drink water; you log it in the app. When you fall behind, the app reminds you to drink more water.

But I _loathe_ this idea. It's so... _manual_. I suppose some apps lessen the work by adding a widget to your phone's home screen. Or others add a tappable action in the notification. But it sounds so _tedious_. I want to touch my phone _less_. Not _more_. Let's not feed the attention monster  more than we have to. 📱👾

### Smart Water Bottles

This one is kinda cool. A Bluetooth smart water bottle that tracks your water intake. The one example I looked at [uses an internal load cell sensor](https://fcc.report/FCC-ID/2AURK006/) to measure the liquid (remember this for later). 

When the measured weight of the liquid goes down, the bottle assumes you drank water. If you're not drinking enough, you'll get a notification on your phone. Ignoring the price, it's a neat idea. 

![Two C-batteries taped to a water bottle with an antenna loosely attached.](/assets/img/2025/02/smart_water_bottle.jpg)*My rendition of what a smart water bottle could look like.*

But how do we power such a magical device? 

_Batteries_. 

Do you know what happens to devices that run on batteries? 

They run out. And then you have to charge them. And then you forget to charge them. And then you forget to drink water. 🪫 So the whole thing works great as long as you remember to keep it charged.

Ignoring that hyper-dramatic scenario for a moment, let's dream about how we could fix this for our situation.

What if we could take one of those magic battery-powered water bottles and build some kind of smart coaster to dock into? This smart coaster would live on your desk and could keep the smart bottle charged. I bet such a device could even offer pass-through charging to keep the battery in a healthy state.

_Wait_. 

That's a great idea. 

Let's build a smart _coaster_.

### A Smart Coaster?

What if I took the components of a smart bottle and put them in a coaster? I could leave the coaster plugged in, and now there are no more battery problems!

Does anyone sell such a magical device? 🧙‍♂ 

Not that I could find! So let’s build one.

![A pair of glasses with a coaster behind the eye pieces](/assets/img/2025/02/a_really_smart_coaster.jpg)*A really smart coaster*

## Researching the Build

If I'm going to build a smart coaster, I want it to:

1. Intelligently remind me to drink water
2. Integrate with my existing smart home setup (preferably using [Home Assistant](https://www.home-assistant.io/) and [ESPHome](https://esphome.io/))

### Load Cells

Playing off of the idea above, what if I use a load cell to measure the weight of the water bottle? I could then track the volume of liquid consumed and notify me if I've fallen behind on my goal. 

From my 5 minutes of research, I found that load cells come in a variety of form factors. But if I wanted a nice flat coaster, I'd need a flat or low-profile load cell. 

Pretending for a moment that I could find the perfect small flat load cell (at an affordable price), I'd still need to find a way to integrate it with ESPHome. 

But there's more. I'd have to calibrate the load cell to the bottle. And what if I switch bottles? Or cups? Or mugs? 🤯

### Refocusing on the Problem

We've gone off course. All of the solutions we've looked at so far are trying to solve _how much_ water I drink. But that's not the _root_ problem. 

**I _really_ have an attention problem.**

_If_ I remember to drink water, I have no problem consuming it. I just need that little nudge to think about it.

Instead of trying to detect _how much_ liquid is in a bottle, let's just try to detect if a bottle is present.

> Full disclosure: A load cell can excel at detecting if _something_ is present. But I don't _think_ the load cell would have been as compact as my final solution, and it would cost a bit more.

### Ultrasonic 🔵🦔 Sensor 

The first sensor that came to my mind for presence detection was the trusty [ultrasonic sensor](https://en.wikipedia.org/wiki/Ultrasonic_transducer). It's a sensor that shoots out a sound wave and listens for the echo. If it hears the echo, it knows something is there (and can also determine the distance).

But most of these sensors are a bit bulky and might not fit into my design. There's also the chance of noise interferences with sound waves bouncing off other objects.

Want to know what's cooler than bouncing sound waves off objects? Bouncing light waves off objects. 🌈🦄

### Lasers 

Meet the VL53L0X. This range sensor utilizes a laser and a detector to precisely measure the time it takes for light to reflect off an object. In most board designs, the VL53L0X achieves remarkable compactness, enabling its use in space-constrained applications.

![VL53L0X Time of Flight sensor board screwed into wood](/assets/img/2025/02/VL53L0X.jpg)*VL53L0X ToF sensor*

The VL53L0X is _also_ [supported by ESPHome](https://esphome.io/components/sensor/vl53l0x.html), which makes it a perfect candidate for my smart coaster. 🥇

## Planning the Build 🗺️

My plan is to mount a VL53L0X ToF (Time of Flight) sensor facing the water bottle to detect if anything is present.

(Simplified) Rules:

- If the bottle is present, a timer will start. 
- If I pick up the bottle, the timer will start over.
- If the timer runs out, I'll get a notification to drink water.

I'll plug the sensor into a (Seeed Studio XIAO) ESP32-S3 that I had lying around, program it using [ESPHome](https://esphome.io/), and handle any automations in [Home Assistant](https://www.home-assistant.io/).

Let's build it.

## Building It 🛠️

### First Attempt

My first attempt to build my smart coaster didn't work. In my head, I thought I could make this as compact as possible by mounting the VL53L0X sensor at a 90° angle to the coaster and hiding my ESP32 chip behind it.

![Wood boards glued and clamped together to make a coaster prototype](/assets/img/2025/02/smart_coaster_first_design.jpg)*My first attempt to build the smart coaster. I later decided mounting the sensor at 90° would make the sensor too close to the bottle.*

This approach was a bad idea. Because I was speedrunning this project, I didn't take the time to read any of the specifications on the VL53L0X sensor I had just purchased online. It turns out there is a minimum distance the sensor needs to be from an object to work properly (30-40 mm). 

> Alternatively, I could have used a different sensor such as the VL53L4CD, with a near 0 mm minimum range. At the time of ordering my parts, it wasn't yet supported by ESPHome. Only later did I learn that a [mrtoy-me](https://github.com/mrtoy-me) had been working on a [custom component](https://github.com/mrtoy-me/esphome-my-components) for it. I have not tested it.

If I were to mount the sensor to the board shown above, the sensor would be too close to the bottle to work properly. This might create a false reading, which could lead to a lot of incorrect notifications. 🚨

But then I had a brilliant idea. Rather than increasing the length of my coaster plate and pushing the sensor further back, what if I leaned the mounting board back at a 45° angle? 📐

Since the sensor would be further away and pointing up at an angle, this would greatly increase the distance between the sensor and the closest  point on the water bottle.

Not only that, leaning the board back would shrink the overall footprint by lowering the height. 

It would also make the coaster look _cool_. 😎

So I took a hammer and chiseled the two boards apart. 🔨 _I wasn't going to throw them away!_

### Second Attempt

Not wanting to make the same mistake twice, I tested mounting the sensor at a new 45° angle with _mounting tape_ (not wood glue). Funny how my arrogance got the best of me last time around. 🤦

![Wood boards mounted together at an angle with tape](/assets/img/2025/02/smart_coaster_taped.jpg)*First assembled prototype. Instead of using wood glue, I learned from my past mistake and assembled this one with mounting tape.*

And you know what? It just worked! 📽️

{% include video.html
  src="/assets/files/2025/02/drink_water.mp4"
  poster="/assets/files/2025/02/drink_water_poster.png"
  controls="autoplay loop"
%}

Let's finish this thing.

### Finishing Touches

Feeling proud of my work, I gathered my materials and tools for final assembly.

I took some wood glue and adhered the angled boards together. I found some extra screws that fit the holes in the VL53L0X sensor board and screwed it into place.

Obviously, I needed some kind of coaster to complete the coaster build. I took one of my old rubber(?) coasters and fastened it to the coaster plate with some mounting tape. 👌

![Smart coaster build from the front](/assets/img/2025/02/smart_coaster_front.jpg)*Final smart coaster from the front.*

Behind the wedge in the back, I used hot glue to secure my super-compact Seeed Studio XIAO ESP32-S3 chip. _Seriously, this thing is tiny._

![Smart coaster build from the rear; showing wiring](/assets/img/2025/02/smart_coaster_rear_wiring.jpg)*Final smart coaster with the Seeed Studio XIAO ESP32-S3 hot glued down.*

Early testing revealed that I needed to figure out how to keep my smart coaster from sliding around my desk. 

Last year, I encountered a material that I thought would work perfectly for my situation. I had previously purchased a watch stand from Spigen. It had an interesting material at the bottom that they named "NanoTac". This material kept the watch stand upright on the desk and resisted being knocked over, but it wasn't _sticky_. 

It's somewhat similar to those sticky hands you'd get from the quarter machines as a kid, but in a much thinner layer. It's pretty close to what I would describe as a silicone gel pad with some light textured etching on it. But I don't think it was actually silicone.

> If you're trying to find a similar material, I'd recommend looking for "Car Dashboard Non Slip Mat" or "Anti Slip Gel Pads" online.

After a bit of searching, I ended up finding some textured car dashboard pads that fit this description. I cut them to size and slapped them to the bottom of the coaster. They just kinda stay without any glue. The feet also dampen the sound when I set my water bottle down. It's pretty neat!

This isn't going anywhere! 🚫🕺

![Underside of smart coaster with 3 gel pads stuck to it](/assets/img/2025/02/gel_pads.jpg)*"Gel" pads installed underneath the coaster so it doesn't slide around my desk.*

### Final Parts Breakdown

Here is the parts list for my smart coaster and the (approximate) cost of each item:

- Existing rubber coaster ($1)
- Scrap wood ($1)
- Seeed Studio XIAO ESP32-S3 ($8)
- VL53L0X ToF sensor ($7)
- "Gel" pads ($6)
- Screws and mounting tape ($1-$5)
- Wood glue and hot glue ($1-$5)

Total cost: **$25-$33**

> I actually had all of these parts laying around except the VL53L0X sensor and the "gel" pads. So _my_ actual cost was closer to $15. 🤑

Physically, the smart coaster is complete. But how does it work?

## How the Smart Coaster Works 🤖

Assembling the hardware is satisfying, but the real intelligence lies in the automations that connect it all.

As I mentioned before, I'm using a VL53L0X ToF sensor to detect if a water bottle is present on the coaster. It is connected to a Seeed Studio XIAO ESP32-S3 chip, which is programmed using [ESPHome](https://esphome.io/). I connect the ESP32-S3 to my [Home Assistant](https://www.home-assistant.io/) instance to handle the automations.

### High-Level Rules

During my workday, if 45 minutes pass and I haven't picked up my water bottle, I'll receive a notification on my devices suggesting that I should take a drink. ⌛️

When I pick up the water bottle, the timer will reset back to 45 minutes, and any pre-existing drink notifications on my devices will be automatically dismissed. 🚰

After the timer ends, if I _don't_ pick up my water bottle, I will continue to receive notifications every 5 minutes until I pick up the water bottle. ♻️

#### Prerequisites

##### Required
1. Create a timer for the desired duration between drink reminders (I use 45 minutes). This will be used in the automations.
   - <https://www.home-assistant.io/integrations/timer/>


##### Optional
1. Create a counter that will increment every time I pick up my water bottle.
   - Useful for historical tracking.
   - <https://www.home-assistant.io/integrations/counter/>
2. Create a template sensor of the counter's state.
   - Necessary to use it with the `utility_meter` integration below.
   - `{%raw%}{{states('counter.drink_counter')}}{%endraw%}`
   - <https://www.home-assistant.io/integrations/template/>
3. Create a utility meter of the template sensor above.
   - Have the utility meter "reset daily".
   - Useful for tracking daily water intake.
   - <https://www.home-assistant.io/integrations/utility_meter/>


#### Automation Triggers

My timer automatically kicks off during the workday (weekdays) at:
- 8:00 AM
- 1:00 PM
- Whenever my laptop screen turns on (assuming the timer is not already running). This is more of a fallback in case I'm starting later than usual.

> `Screen Off` is an attribute exposed on the `binary_sensor.mac_device_active` in the Home Assistant companion app on MacOS.

#### Automation Actions

If the timer runs out naturally:
- I get an alert
- The timer gets set back to 5 minutes (which will keep looping)

If I pick up the water bottle: 
- The timer gets reset to 45 minutes
- **Any drink notifications on my devices get automatically dismissed** (thank goodness; less notification spam)

> The `clear_notification` is a message that can be sent to clear Home Assistant notifications on a device that has a matching `data.tag`.
> 
> <https://companion.home-assistant.io/docs/notifications/notifications-basic#clearing>

#### Notification Conditions

Notifications will only be sent if the following conditions are met:
- The timer runs out
- During normal working hours (excludes lunch hour)
- My laptop screen is on (which means I'm at my computer next to my smart coaster)


<details markdown="block">

<summary>[Yaml] Home Assistant Automation</summary>

{% raw %}
```yaml
# Written for Home Assistant 2025.2.0
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
    alias: Kick Off Timer (Morning)
  - trigger: time
    at: "13:00:00"
    alias: Kick Off Timer (Afternoon)
    id: start-timer
  - trigger: state
    entity_id:
      - binary_sensor.mac_device_active
    attribute: Screen Off
    to: "false"
    from: "true"
    alias: When screen turns on (backup condition)
    id: screen-on
conditions:
  - alias: During standard working hours
    condition: time
    after: "07:55:00"
    before: "16:55:00"
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
          # By cancelling the timer and starting it again, we can have it return to its original value at without needing to pass the duration in.
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
          # By cancelling the timer and starting it again, we can have it return to its original value at without needing to pass the duration in.
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
                    tag: water-drink-alert
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
        sequence:
          - parallel:
              - data:
                  # My cheater way to convert the timer's original duration into minutes for my notification. It will work for any _sane_ duration.
                  title: 🥤 Drink some water
                  message: >-
                    You haven't had anything to drink in the last {% set
                    remaining_time = state_attr('timer.water_bottle_timer',
                    'duration').split(':') %}{{remaining_time[0] | int * 60 +
                    remaining_time[1] | int }} minutes.
                  data:
                    ttl: 0
                    priority: high  
                  data:
                    notification_icon: mdi:beer
                    group: water-drink-alert
                    channel: water-drink-alert
                    tag: water-drink-alert
                    push:
                      interruption-level: time-sensitive
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
          # By cancelling the timer and starting it again, we can have it return to its original value at without needing to pass the duration in.
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


## ESPHome Configuration

Here is a breakdown of the hardware and ESPHome configuration I used for my smart coaster:

- Board:
  - Seeed Studio XIAO ESP32-S3
    - Super small form factor
    - (I have a few lying around from Christmas 🎄)
- Sensor:
  - VL53L0X ToF sensor to detect the presence of a water bottle on the coaster
    - Super compact
    - Easy to find online
  - The component already exists in ESPHome
    - <https://esphome.io/components/sensor/vl53l0x.html>


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

## What Would I Do Differently?

If I had the gumption and endless free time for this project, I would:

- Use a dark walnut wood stain on the coaster plate
- Carve out a small channel or hole in the coaster plate to hide the sensor wiring
- Figure out how to recess the sensor to the coaster plate
- Cover the sensor with a thin layer of acrylic to better hide and protect it
- Solder wires between the boards
- Enclose the back wedge with a thin layer of wood or black acrylic

## Conclusion

![Smart coaster build with Home Assistant dashboard showing data in the back](/assets/img/2025/02/smart_coaster_integration.jpg)*Smart coaster with its data being displayed on my Home Assistant dashboard as a notification nudges me to drink water*

I want to make sure I remember to drink water. I think I've figured out a good approach that avoids any feedback loop from tracking and interacting with my phone. I think my solution reduces any additional cognitive load by only nudging me when appropriate and automatically dismissing all notifications when I pick up my water bottle. 

From conception to completion, this project only took 2 days—a record for me. 🏃

The final result is a smart coaster that is delicately reminding me to drink water and staying out of my way if I drink water naturally. 

All of this to say, **my temporary prototype solution is good enough to be permanent**. 🥤🖖
