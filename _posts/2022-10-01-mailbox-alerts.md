---
title: Instantaneous Mail Notifications
date: '2022-10-01 11:33'
comments: true
image:
  path: /assets/img/2022/10/mailbox_banner.jpg
  height: 600
  width: 800
alt: Ring Alarm Outdoor Contact Sensor installed in a mailbox for mail notifications
published: true
tag: "medium project"
description: "Dealing with my impatient inner child by getting notified the moment we receive our mail through Home Assistant"
---

We have an unpredictable mail schedule and I'm an impatient child. I'm convinced that when the post office knows they're delivering a box of parts, they shuffle our route for a late-night delivery. Rather than hawking around the mailbox or listening for the phantom muffler of a Grumman LLV, I want unequivocal evidence when our mailbox had been opened for delivery. 

> Alt: How I cured my Pavlovian response to hearing a Grumman LLV come down the road

My solution was to use an outdoor rated Z-Wave contact sensor to detect when the mailbox was opened and then notify my family over Home Assistant. Here's how I got there.

## Detecting Mail

### Option 1 👎 

Before anyone asks, the yellow indicator flag on some mailboxes _can_ let a user know that the mail has arrived. It's a small yellow flag that raises when the mailbox door is opened, but remains upright when the mailbox door is closed. This simple mechanism can indicate that the mailbox has been opened. 

But using an indicator flag is more like polling the status of mail delivery. I'd rather be _told_ when mail arrives instead of checking in on it. 

### Option 2 👎

One residential option for mailbox notifications is something called a `Mail Chime`. They are usually gyroscopic (or contact) sensors that send RF signals to a chime unit back inside the house. When triggered, the indoor station sets off a ring. This is similar to a wireless doorbell.

These are _okay_. But I found two big deficiencies with this option. 

1. There's usually no battery indicator on the sensor (so I don't know when it stops working)
2. If I want to make it smarter, I need to hack something into the chime box or retransmit signals.

### Option 3 🤷

The next option for consideration is a product made by Ring for this exact purpose. It's called the `Ring Mailbox Sensor`. It's a motion sensor connected to an external antenna that mounts outside of the mailbox. The devices connects to the Ring bridge. 

However, it feels a little user-hostile since it uses a proprietary protocol with their special bridge. Even though it's purpose built for my situation, the vendor lock-in pushed me to look for other solutions. 

### Option 4 👍

The last solution I looked into was adding a contact sensor to the mailbox door to detect when it opens. Luckily I have a plastic mailbox so I didn't need to worry about a metal box impeding the signal.

I ended up going with the `Ring Alarm Outdoor Contact Sensor`. It seems to have a handful of great features.

- ✅ IP66 weather resistant (Protected against dust and strong jets of water)
- ✅ Supports Z-Wave Long Range (Using a compatible controller, the signal can reach up to 1 mile with direct line-of-sight)
- ✅ 5 year battery life
- ✅ Standard batteries (2x AA)
- ✅ Heartbeat signals to ensure it's still alive and connected
- ✅ Battery updates
- ✅ Works with Z-Wave JS

That's a pretty impressive list. If I had a proper Z-Wave Long Range controller, I could leverage the full long-range capabilities. But I don't have a controller with the newer standard, so I'm getting by with my Aeotec range extenders _for now_. 

> Avoid using this contact sensor with a metal mailbox since a metal mailbox will act as a faraday cage and inhibit the signal. 

## How Do I Implement This?

At the time of writing, I'm using

- [Home Assistant](https://www.home-assistant.io/) (2022.9.6) as the brains to this operation
- [Z-Wave JS](https://github.com/zwave-js) (10.2.0) to manage my Z-Wave network
- [Aeotec Range Extender 7](https://aeotec.com/products/aeotec-range-extender-7/) to extend my Z-Wave network out to the mailbox

First, I install the `Ring Alarm Outdoor Contact Sensor` to our mailbox lid with some stainless steel hardware.

![Ring Alarm Outdoor Contact Sensor installed in a mailbox for mail notifications](/assets/img/2022/10/mailbox_banner.jpg)*Contact sensor installed in mailbox*

Next I include the contact sensor into the Z-Wave network inside Z-Wave JS.

Since my Home Assistant already integrates with my Z-Wave network, any new devices in Z-Wave JS will automatically populate new entities in Home Assistant.

After the contact sensor entity is created in Home Assistant, I wait for the contact sensor to update its values upon state changes. When the contact sensor sends the update that it was opened, my Home Assistant automations will trigger and notifications are sent out. 

## Automations

Here are the automations I wrote to help notify and track states of when I _think_ mail has arrived, or when it was picked up.

> The notification setup works best if you're not frequently sending outgoing mail. But if you are, I added a small action further down to help mitigate that behavior.

The first thing we need to set up is an `input_boolean` helper that we'll toggle `on` or `off` depending on if we think mail has arrived. 

![Mail Present input boolean](/assets/img/2022/10/mail_present_input.jpg)*Mail Present input boolean*

In my examples, I call it `input_boolean.mail_present`.

As a bonus, we can show this `input_boolean` on the dashboard for a quick glance.

![Mail Present in the dashboard](/assets/img/2022/10/mail_present_dashboard.jpg)*Mail Present in the dashboard*

### Mail Arrived

![Mail Arrived notification](/assets/img/2022/10/notification.png)*Mail Arrived notification*

When the contact sensor's intrusion sensor flips to `on`, it indicates that the mailbox is "open". When the contact sensor's intrusion sensor flips to `off`, it indicates that the mailbox has been "closed".

Here's our happy path. When we open the mailbox for the first time, we turn on the `input_boolean.mail_present` to show that the mail is (probably) present in the mailbox. If we open the mailbox again later, we turn the `input_boolean.mail_present` off. This indicates that mail has been retrieved.

But not everything in the world follows the happy path. 

I've added a conditional that the mailbox intrusion sensor must be `off` (closed) for at least 15s before we consider 'opening the mailbox' a new event. This helps in situations where the mail carrier closes the mailbox, realizes they have more mail, and then opens it back up again. If we don't account for this, we would otherwise incorrectly mark the mail as "retrieved".

If every condition is met, our automation fires off a notification to the family that mail has (probably) arrived.

```yaml
alias: Alert - Mail arrived
description: Automation to control actions when mailbox is opened
trigger:
  - platform: state
    entity_id:
      - binary_sensor.mailbox_home_security_intrusion
    to: "on"
condition:
  - condition: state
    entity_id: input_boolean.mail_present
    state: "off"
    for:
      hours: 0
      minutes: 0
      seconds: 15
action:
  - service: input_boolean.turn_on
    data: {}
    target:
      entity_id: input_boolean.mail_present
  - service: notify.family
    data:
      title: 📬 You've got mail!
      data:
        notification_icon: mdi:mailbox-open-up
        group: mail-alert
        channel: mail-alert
        data:
          ttl: "0"
          priority: high
        push:
          interruption-level: time-sensitive
        actions: # More on this action later!
          - action: TURN_OFF_MAIL_PRESENT
            title: That was me
      message: The mailbox has been opened. Maybe you have mail?
mode: single
```

### Mail Retrieved

Next, we consider mail retrieved if:

- **Scenario 1**: The contact sensor changes from `off` (mailbox _**closed**_) to `on` (mailbox _**open**_), but only after being closed for `15s`. This indicates that the mailbox was likely opened a second time to retrieve mail.
- **Scenario 2**: The contact sensor changes from `on` (mailbox _**open**_) to `off` (mailbox _**closed**_), but only after being left open for `60s`. This usually indicates that there was a package sticking out of the mailbox so the door was never closed. 

The automation turns off the `input_boolean.mail_present` so we can show on our dashboard that the mail has been (likely) picked up.

```yaml
alias: Alert - Mail retrieved
description: Automation to control actions when mailbox is opened (for the second time)
trigger:
  - platform: state
    entity_id:
      - binary_sensor.mailbox_home_security_intrusion
    to: "off"
    for:
      hours: 0
      minutes: 0
      seconds: 0
    id: mail-retrieved-1
    from: "on"
  - platform: state
    entity_id:
      - binary_sensor.mailbox_home_security_intrusion
    to: "on"
    id: mail-retrieved-2
    from: "off"
condition: []
action:
  - choose:
      - conditions:
          - condition: trigger
            id: mail-retrieved-1
          - condition: state
            entity_id: input_boolean.mail_present
            state: "on"
            for:
              hours: 0
              minutes: 0
              seconds: 15
        sequence:
          - service: input_boolean.turn_off
            data: {}
            target:
              entity_id: input_boolean.mail_present  
      - conditions:
          - condition: trigger
            id: mail-retrieved-2
          - condition: state
            entity_id: input_boolean.mail_present
            state: "on"
            for:
              hours: 0
              minutes: 0
              seconds: 60
        sequence:
          - service: input_boolean.turn_off
            data: {}
            target:
              entity_id: input_boolean.mail_present
    default: []
mode: single
```

### Outgoing Mail Action

![Mail Arrived notification with action](/assets/img/2022/10/notification_action.png)*Mail Arrived notification with an action*

This is a quick helper action if a user is putting mail in the mailbox at the start of the day. 

Whenever mail "arrives", our earlier automation sends a notification to the family with additional actions. One of those actions has a button that says "It was me". 

If a user presses that button, the notification will send `TURN_OFF_MAIL_PRESENT` in an event back to Home Assistant which will get picked up by the following automation. This automation will then turn _off_ the `input_boolean.mail_present` which will then allow a notification to occur again the next time the mailbox is opened.

```yaml
alias: Action - Outgoing mail ID
description: Button to turn off "mail present" when opening the mailbox for outgoing mail
trigger:
  - platform: event
    event_type: mobile_app_notification_action
    event_data:
      action: TURN_OFF_MAIL_PRESENT
condition: []
action:
  - service: input_boolean.turn_off
    data: {}
    target:
      entity_id: input_boolean.mail_present
mode: single
```

### Daily Reset

At the start of each day, reset the `input_boolean.mail_present` state to fix any possible edge cases that were missed. 

```yaml
description: ""
mode: single
trigger:
  - platform: time
    at: "06:00:00"
condition: []
action:
  - service: input_boolean.turn_off
    data: {}
    target:
      entity_id: input_boolean.mail_present
```

## Conclusion

I've been using my mailbox alert setup for the last 3 months. It hasn't missed a delivery yet. The alerts have been super convenient since we don't get mail regularly, and sometimes we'll have a late (or second) delivery at 7PM. The sound of something similar to a Grumman LLV chugging down the road no longer brings me to the front window to check. I am at peace.
