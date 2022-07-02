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

In the last year I've been retrofitting tech into our home. 
Our house is the epitome of luxury featuring such things as a ragged sound deadening from our rad carpeted stairwell. Due to this ingenious addition, it's difficult to hear things like the doorbell while we're watching TV or in a meeting.

How do we solve this? ~~Take out the carpeted wall and make the doorbell louder~~. **NO**. We make the doorbell _smart_ 🧠! 

> This is going to be a pretty high level overview at getting Shelly 1 relays to intercept my doorbell signals. It will skip over things like "Flashing ESPHome onto the Shelly relay". 
> 
> It's really to allow users near this ecosystem to steal and benefit from my project.

## Goals

- Get alerts on our devices when the doorbell rings
- Ability to discern our different doorbells
- Avoid subscription costs (Except to [Nabu Casa](https://www.nabucasa.com/) ❤️)
- Ability to disable the doorbell chime like when we're sleeping
- Create a fun repeating doorbell alarm for no good reason

## Requirements

### Hardware Requirements

Here's an approximation for the hardware costs involved with the project.

- $35: 2x Shelly 1 (one for each doorbell)
- $15: Low voltage power supply (couldn't run it off of transformer in my case)
- $10: Low voltage wire to power Shelly 1
- $20: (Optional) Waterproof junction box so wires weren't hanging everywhere

> I used a waterproof junction box because the doorbell wiring was too close to the main water line for my comfort. It just helps me sleep better.

![Two Shelly 1 inside of a conduit box wired up to each doorbell](/assets/img/2022/07/doorbell_wiring.jpg)*Wiring a Shelly 1 for each doorbell*

### Software Requirements

This guide is going to assume the user is familiar with Home Assistant and ESPHome. If they are not, check them out! They're _great_ projects.

- [Home Assistant](https://www.home-assistant.io/) (I'm running the `2022.6` release at the time of writing)
- [ESPHome](https://esphome.io/) flashed onto Shelly 1

## Setup

### Two Shelly Relays?

If you've read the hardware above, you might be asking yourself "Why are there two Shelly 1s? Surely you don't need that. 

You'd be right! However, did you know some homes have _two_ doorbells? I guess the thought is that you put the second doorbell by your back door in case a neighbor is stopping by. 

When this happens, a chime box can be wired to give each doorbell a different chime (`Ding` vs `Ding Dong`) allowing the homeowner to know which door their visitor is at. _Neat!_

Except our second doorbell is _also_ in the front.. just 15 steps from the first doorbell. We've had people ring our second doorbell before, so we're just going to proceed supporting it because I think it's bougie. 😎

### Shelly 1 Configuration

Mentioned earlier, we're going to use ESPHome to configure our Shelly 1 relays.

The Shelly 1 relay will be powered from our low voltage wires (or really, whatever you can find). The doorbell wires will travel through the I/O connectors. Finally, the doorbell button wire will become captured by the Shelly 1 `switch` input. We pass along that original doorbell signal via the Shelly relay to our doorbell chime and set it off. 

This accomplishes two things. First, we now _know_ via software that the doorbell was pressed since we triggered it via the Shelly `switch` input. Second, because we're choosing to pass the signal onto our doorbell chime, we can also choose _not_ to pass the signal along like while the baby is sleeping. I've added functionality to mute the doorbell chime via an exposed input boolean below (Helpful to pair with home bedtime automations).

> Achievement unlocked: Muting a doorbell

But we can take that a step further. Since we're _also_ in control of when our doorbell chimes, why not control it further? In the ESPHome config below, I've also included a little `script` that will repeatedly trigger the doorbell chime for 30s when toggled on. _DING-DONG Ding-Dong ding-dong..._ After 30s, the relay _should_ turn off the toggle, stopping the script execution.

_Why?_ I'm not really sure. It just seemed like a fun idea. Maybe you enjoy making dogs bark, annoying your significant other, or pretending to have a high-tech burglar alarm to annoy them away.

It's probably a bad idea. But don't let that stop you! Just be careful of burning our your relay or doorbell chime. I'm _at least_ 20% sure it's not meant to operate like that (hence the 30s cap).

> Achievement unlocked: Annoying as bell


```yaml
#{% raw %}
# Basic Config
# shelly-one-01
# Front Door Doorbell

substitutions:
  devicename: Front Door Doorbell
  deviceid: front_door_doorbell

esphome:
  name: shelly-one-01
  comment: ${devicename}
  platform: ESP8266
  board: esp01_1m

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

  # Enable fallback hotspot (captive portal) in case wifi connection fails
  ap:
    ssid: "${plugtag} Hotspot"
    password: !secret ap_hotspot_password


# Enable captive portal if wifi ever changes
captive_portal:

# Enable Home Assistant API
api:
  password: !secret api_password
  encryption:
    key: !secret encryption_pre_shared_key

ota:
  password: !secret ota_password

# Global to store the on/off state of the chime
globals:
  - id: chime_var
    type: bool
    restore_value: true
    initial_value: 'true'
  - id: chime_alarm_var
    type: bool
    restore_value: false
    initial_value: 'false'  

# Enable logging
logger:

time:
  - platform: homeassistant
    id: my_time

# Sensors that the ESPhome unit is capable of reporting
sensor:
  - platform: wifi_signal
    name: "${devicename} WiFi Signal"
    update_interval: 300s

binary_sensor:
  - platform: gpio
    pin:
      number: GPIO5
    name: ${devicename}
    filters:
      - delayed_on: 100ms
      - delayed_off: 25ms
    on_press:
      # Only turn on the chime when it is active.
      then:
        if:
          condition:
            - switch.is_on: chime_is_enabled
          then:
            - switch.turn_on: relay
    on_release:
      # On release, turn of the chime.
      - switch.turn_off: relay

switch:
  # Switch to enable/disable chime when
  # doorbell button is pushed.
  - platform: template
    id: chime_is_enabled
    name: ${devicename} Chime
    icon: mdi:power-settings
    restore_state: false
    turn_on_action:
      - globals.set:
          id: chime_var
          value: 'true'
    turn_off_action:
      - globals.set:
          id: chime_var
          value: 'false'
    lambda: |-
      return id(chime_var);
  - platform: template
    id: chime_alarm
    name: ${devicename} Alarm
    icon: mdi:alarm-bell
    restore_state: false
    turn_on_action:
      - globals.set:
          id: chime_alarm_var
          value: 'true'
      - script.execute: alarm_script
      - delay: 30s
      - switch.turn_off: chime_alarm
    turn_off_action:
      - globals.set:
          id: chime_alarm_var
          value: 'false'
    lambda: |-
      return id(chime_alarm_var);
  - platform: gpio
    id: relay
    internal: true
    name: ${devicename} Doorbell Switch
    pin: GPIO4
    restore_mode: RESTORE_DEFAULT_OFF
    
script:
  - id: alarm_script
    then:
    - while:
        condition:
          lambda: |-
            return id(chime_alarm_var);
        then:    
        - switch.turn_on: relay
        - delay: 500ms
        - switch.turn_off: relay
        - delay: 500ms
#{% endraw %}
```

## Alerts for All

Great, we have a chime and it's added into Home Assistant. That's not very useful yet. So let's add notifications!

> I also _happen_ to have a camera by the doorbell, so I include a camera snapshot in my notifications.

Using the Home Assistant app on our phone, we can send out notifications with the following Home Assistant automation.

![Simulated phone doorbell notification](/assets/img/2022/07/phone_notification.jpg)*Simulated phone notification from a doorbell press*

If we use an Android TV, we can also use the [`nfandroidtv`](https://www.home-assistant.io/integrations/nfandroidtv/) integration in order to display alerts on our TV.

![Simulated Android TV doorbell notification](/assets/img/2022/07/tv_notification.jpg)*Simulated Android TV notification from a doorbell press*

Here's a useful Home Assistant automation blueprint that I use to configure my doorbells.

```yaml
#{% raw %}
blueprint:
  name: Doorbell Alert Notifications
  description: >
    This automation blueprint creates a camera snapshot if doorbell is detected 
    and sends a notification to your device with the picture.
    
    Requirements:
      - Add `- /tmp` to `allowlist_external_dirs:` in the `configuration.yaml`
    
    Required entities:
      - Doorbell sensor (binary_sensor in None class)
      - Camera entity
      - Notify device entity    
 
  domain: automation

  input:
    doorbell_sensor:
      name: Doorbell sensor
      description: The sensor wich triggers the snapshot creation (domain binary_sensor, class motion).
      selector:
          entity:
            domain: binary_sensor

    camera:
      name: Camera
      description: The camera to create the snapshot (domain camera).
      selector:
        entity:
          domain: camera
          
    notifications_enabled:
      name: Notifications State
      description: Input Boolean to control all notifications across all automations (excluding overrides)
      selector:
        entity:
          domain: input_boolean

    sleeping_mode_enabled:
      name: Sleeping Mode State
      description: Input Boolean to describe the state of the home sleeping mode
      selector:
        entity:
          domain: input_boolean
          
    camera_delay:
      name: (Optional) Camera Delay
      description: Delay after doorbell before taking a snapshot from the camera. Useful when your camera stream has a bit of lag.
      default: 1
      selector:
        number:
            min: 0
            max: 15
            unit_of_measurement: seconds
            mode: slider             

    snapshot_delay:
      name: (Optional) Snapshot Delay
      description: Delay before sending the notification after writing the camera snapshot to disk.
      default: 1
      selector:
        number:
            min: 0
            max: 15
            unit_of_measurement: seconds
            mode: slider            
            
    rate_limit:
      name: (Optional) Rate Limit
      description: How many seconds to wait before we can send another notification.
      default: 10
      selector:
        number:
            min: 0
            max: 60
            unit_of_measurement: seconds
            mode: slider             

    notification_title:
      name: (Optional) Notification title
      description: 'Default: "🔔 {{doorbell_sensor_name}}"'
      default: "🔔 {{doorbell_sensor_name}}"
      
    notification_message_standard:
      name: (Optional) Notification Standard message
      description: 'Default: "{{ doorbell_sensor_name }} triggered."'
      default: "{{ doorbell_sensor_name }} triggered."      

trigger:
  platform: state
  entity_id: !input doorbell_sensor
  from: "off"
  to: "on"

variables:
  doorbell_sensor: !input doorbell_sensor
  doorbell_sensor_name: "{{ states[doorbell_sensor].name }}"
  camera: !input camera
  notification_title: !input notification_title
  snapshot_delay: !input snapshot_delay
  camera_delay: !input camera_delay  
  rate_limit: !input rate_limit
  snapshot_file_path: "/config/www/tmp/snapshot_{{ states[camera].object_id }}.jpg"
  snapshot_image_path: "/local/tmp/snapshot_{{ states[camera].object_id }}.jpg"
  notifications_enabled: !input notifications_enabled
  sleeping_mode_enabled: !input sleeping_mode_enabled
  notification_message_standard: !input notification_message_standard

condition:
  - condition: template
    value_template: >-
      {% if (states[notifications_enabled].state == 'on') %}
        true
      {% else %}
        false
      {%- endif %}  
action:
  - delay: "{{ camera_delay }}"   
  
  - service: camera.snapshot
    entity_id: !input camera
    data:
      filename: "{{ snapshot_file_path }}"
      
  - delay: "{{ snapshot_delay }}"      

  - service: notify.family
    data:
      title: "{{ notification_title }}"
      message: "{{ notification_message_standard }}"        
      data:
        notification_icon: mdi:bell
        group: doorbell
        channel: doorbell
        data:
          ttl: '0'
          priority: high
        push:
          interruption-level: time-sensitive
        actions:
          - action: SIMULATE_PRESENCE
            title: Fake presence
          - action: TEMP_DOORBELL_NOTIFICATION_MUTE
            title: Mute (15m)
        image: "{{ snapshot_image_path }}"

  - service: notify.screens
    data:
      title: "{{ notification_title }}"
      message: "{{ notification_message_standard }}"
      data:
        duration: 10
        image:
          path: "{{ snapshot_file_path }}" 

  - delay: "{{ rate_limit }}"

mode: single
max_exceeded: silent     

#{% endraw %}
```

## Final Thoughts

I don't think I'm a luddite, but sometimes I really appreciate older things. Who knows, maybe I'll come around to a video doorbell once there are better looking options. 

It's super useful to get alerts when I'm busy, away from home, or mute alerts while the baby naps.

I had an existing doorbell, existing camera, and accessible wiring. With a little bit of fun, I was able to transform (pun intended) our doorbell setup into something I'd seen advertised by other smart doorbells. But doing it myself makes me happy.
