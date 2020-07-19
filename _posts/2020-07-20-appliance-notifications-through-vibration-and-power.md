---
title: "Using Vibrations and Power to Notify Washing Machine and Dryer Completions"
date: "2020-07-19 10:59"
comments: true
image:
  path: /assets/img/2020/07/dryer_vibration_monitor.jpg
  height: 600
  width: 800
alt: "NodeMCU board with SW-420 vibration sensor attached"
published: true
tag: "small project"
description: "How I notify and detect the completion of my washing machine and dryer through the use of a vibration sensor, NodeMCU, smart plug, and ESPHome."
---

Our washing machine and dryer do not have an audible notification upon completion. When they finish they go silent. Because we live in a small space, we generally shut the door to the laundry room to reduce noise leakage in the rest of our living areas. On more than one occasion we have missed the end of the washer/dryer cycle because of other ambient noise was masking it. Rather than letting our clothes wrinkle up in the dryer or stay forgotten overnight in the washer, I would rather receive an audible alert upon a cycle completion.

The process of detecting the completion state of each appliance was its own task.

## 🧼 Identifying Washing Machine State

This one was easy. To detect the running state of our washing machine, I only need to monitor the power consumption on the standard wall plug. 

In my last blog post I wrote about how I [deployed a handful of ESPHome smart plugs](/blog/2020/07/replacing-z-wave-with-esphome/). One of those plugs became a dedicated device to monitoring the power consumption of our washing machine. After running one cycle to see a baseline power usage, I was able to determine that at no point during does the washing machine drop below 3 W of power consumption.

Since my plug was running ESPHome, I just needed to add a new binary sensor to the device based on the plug's power consumption.

```yaml
binary_sensor:
  - platform: gpio
    pin:
      number: GPIO0
      mode: INPUT_PULLUP
      inverted: True
    name: "${devicename} Button"
    on_press:
      - switch.toggle: relay  
  - platform: status
    name: "${devicename} Status"
  - platform: template
    name: "${devicename} Running"
    filters:
      - delayed_off: 15s
    lambda: |-
      if (isnan(id(power).state)) {
        return {};
      } else if (id(power).state >= 2) {
        // Running
        return true;
      } else {
        // Not running
        return false;
      }    
```

## ♨️Identifying Dryer State

Tracking the state of the dryer was a bit trickier. Since our dryer is connected to a 240 V outlet, it essentially eliminated any reasonably priced smart plug.

This left me with four options (that I could come up with):

1. Open the dryer and hook up a CT clamp (magnetic induction sensor) to a specific wire
2. Open the dryer and connect a NodeMCU to a nonlethal connector on the main circuit board
3. Throw a wireless sensor on the drum and track when it stops moving
4. Mount a vibration sensor to the side of the dryer and detect when it stops shaking

### Reviewing Dryer Status Options

Let us walk through each idea above to figure out why I chose to use the vibration sensor.

#### 1. Opening the Dryer and Using a CT clamp

Originally I thought using a CT clamp was going to be a good idea but in the end, I opted against it. I am not comfortable working around devices that are moving 240 V. I am sure everything would have been fine considering the CT clamp is a passive sensor, but I really did not want to have to deal with the planning and cost of adding an additional boards to interpret the signal of a CT sensor.

#### 2. Connecting a NodeMCU to the Dryer Main Circuit Board

This was another reasonable idea but because it is very device specific and I am not as comfortable running a sensor to the internal board of the dryer, I ruled this one out early on. 

Our dryer does not have a digital display. In fact, it does not even have a light for the inside drum when you open the door. It is quite lacking with few features. Our dryer strongly follows the "keep it stupid simple" policy. 

If I were to connect a NodeMCU to the main circuit board, I would have to spend time figuring out which leads to run a sensor to. This is probably the cleanest approach, but I wanted to avoid a solution that was device specific. Whatever solution I came up with needed to be generic for anyone to replicate in the future. 

Keeping it generic also reduces the "re-factoring in real life" when the dryer gets replaced someday.

#### 3. Use a Wireless Sensor on the Drum to Track Movement

Truthfully, I am not that interested in using a low powered wireless sensor. This just another device that I need to charge and keep track of. If I have something hardwired, it is one less thing I need to think about.

#### 4. Using a Vibration Sensor

The last solution I am going to describe is using a vibration sensor to track the completion of our dryer. While researching ways that people have tracked their dryer status, one of the fun ways mentioned has been using a vibration sensor.

It is a simple concept. You connect a vibration sensor to a NodeMCU. When the vibration sensor detects no more movement the sensor will change the signal being sent to the NodeMCU. If vibration is stopped for long enough, one can infer that the dryer has completed its cycle.

I really like this idea because it is extremely cheap and generic enough to work on most dryers. The only exception I can think of is for stacked units or a room that shakes a lot.

The sensor that most people use for their dryer detection is the SW-420 vibration sensor. I ended up getting a 5-pack for $7.

![NodeMCU board with SW-420 vibration sensor attached](/assets/img/2020/07/dryer_vibration_monitor.jpg)*NodeMCU with SW-420 vibration sensor attached*

### Configuring ESPHome with the Vibration Sensor

When I see most people use a vibration sensor to track the dryer status, they consider the dryer as running the first time the vibration sensor is triggered. After 15s without any re-triggers, they mark the dryer status as done.

This might be fine for people that have their dryer in a closet hidden in the back room. For me, the dryer is in a high traffic room. This means it is easy to bump the dryer sensor and create a false positive event. Other concerns include large thunder strikes and nearby semi-trucks from a busy road (known to set off car alarms).

To avoid false positives, I decided to treat the vibration sensor like a pulse counter. Then take a moving median window of the pulse counter rate to eliminate any outliers that are not producing consistent vibration. 

Adding a moving median window does decrease the reactivity of the dryer status by approximately 10-15s. In turn it eliminates all false positives from inconsistent vibrations.

Here are the relevant changes in ESPHome made to my NodeMCU chip that allow it to interpret the vibrations with a moving median. I then create a `binary_sensor` from the `pulse_counter` sensor expose it to Home Assistant. The binary sensor obfuscates the of the raw values that I do not need to send over the network. It also reduces refactoring needed downstream since it the state will determined entirely on the NodeMCU device.

```yaml
# Sensors that the ESPHome unit is capable of reporting
sensor:
  - platform: wifi_signal
    name: "${devicename} WiFi Signal"
    update_interval: 60s
  - platform: uptime
    name: "${devicename} Uptime"
    update_interval: 60s
    # Handle a moving average of vibrations 
    # Avoids `turning on` when bumping the dryer
  - platform: pulse_counter
    name: "${devicename} Vibration Pulse Rate"
    id: vibration_pulse_rate
    icon: mdi:vibrate
    update_interval: 250ms # 4x a second
    pin:
      number: GPIO15
      mode: INPUT
    filters:
    - median:
        window_size: 61 # ~15 second moving window
        send_every: 4 # Every 1 second
        send_first_at: 3 

# SW-420 Vibration Sensor
binary_sensor:  
  - platform: template
    name: "${devicename} Running"
    device_class: vibration
    filters:
      - delayed_on_off: 3s # Avoid debounce when crossing threshold
    lambda: |-
      if (id(vibration_pulse_rate).state > 500) {
        // Dryer is running
        return true;
      } else {
        // Dryer is off
        return false;
      }    
```

![Monitoring contraption attached to the side of a dryer](/assets/img/2020/07/dryer_monitor_installed.jpg)*Dryer monitoring contraption installed*

## Notifications

Finally, once I have captured the states of the washer and dryer inside Home Assistant, I can determine how I want to broadcast the notification upon complete of the washing machine and dryer.

![Node-RED dashboard showing flow for washer and dryer notifications](/assets/img/2020/07/node_red_cleaning_notifications.png)*Node-RED washer/dryer notification flow*

In the flow above I am using Node-RED to create the automations handling the notification alert. 

The top flow checks if the washing machine state changes from `on` -> `off`. 

The bottom flow checks if the dryer state changes from `on` -> `off`. 

If either of those two devices are complete, it will call service within home assistant to broadcast a notification to all Google Homes that the respective appliance is done running.

The catch is that I do not want any alerts to be sent out unless they are _actionable_. What I mean is that I do not wish to be notified if the washer is done but the dryer is still running. That is because there is nothing I can do. There is nowhere to put the wet clothes yet. You can see this modification in the top flow where I restrict notifications from being sent if the dryer is still running.

## Conclusion

This is an automation that I have been wishing on for a while but had not spent the time to examine all approaches until recently.

I feel content with my low-cost approach on each appliance and I admire the fact that they are mostly generic. This will allow me to continue using these methods in the future unless there are unforeseen changes.

We now have a smart way to monitor the state of the washing machine and dryer. It sends alerts only when they are actionable and reduces the downtime between each load. An automation that increases efficiency is a pleasant one.

