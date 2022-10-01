---
title: Surfacing Scenes to All Google Home Household Members
date: '2022-10-01 17:49'
comments: true
image:
  path: /assets/img/2022/10/google_home_scenes_banner.jpg
  height: 578
  width: 800
alt: Locating synced scenes inside of the Google Home app
published: true
tag: "guide"
description: "Members of a household who try to invoke Home Assistant scenes in Google Home cannot always access them. Here's how to fix it."
---

Google Home [supports the concept activating scenes](https://support.google.com/googlenest/answer/9155535) to simplify common room configurations. This trait allows users to group devices under the same service and update them simultaneously. It's very similar to the `routines` control inside Google Home, but instead, the scene handling is done by the respective linked service. 

For example, a user could activate a scene to lower each curtain in a room when taking a nap. Or a scene could arrange holiday lights to specific colors configured in the Philips Hue app.

Instead of sending 15 requests to adjust every light bulb with a linked service, we can instead send a single scene request. If you've ever had reliability issues with Google Home adjusting too many devices at once, this could help.


## The Flaw

Google Home has this concept called [Household](https://support.google.com/googlenest/answer/9155535). It allows a user to invite other members in their house into the same Google Home instance. Anyone in the household can control the smart devices and even link their own services to the Google Home.

Scenes are a bit trickier though. Google seems to be doing a very poor job of surfacing them to the user.

Scenes are difficult to locate in the Google Home app. The only reliable place I could find scenes are when I am editing a routine... under home controls... under the scene adjustment option. So _really straight forward_, yea? Or if I know the "✨magic phrase✨", I can say something like "Hey Google, activate the monthly driveway lights". The scene support is tragic. 

## I Still Want Scenes

Ok, but I _still_ want to use scenes.

![Google Home scene menu](/assets/img/2022/10/google_home_scenes_banner.jpg)*The closest we have to locating scenes in Google Home*

Here I can see the scenes in Google Home that I added through Home Assistant. I spot 7 scenes available to me.

That's great! Let me use my magic phrase that I mentioned earlier.

If I say "Hey Google, activate the monthly driveway lights", the lights adjust and everything looks great.

But if my wife says "Hey Google, activate the monthly driveway lights", the Google Home apologizes as it can't find that device.

## What Gives?

Remember how scenes are notoriously difficult to trigger without the magic phrases? Scenes also have magically awful support.

If a `scene` is added to the Google Home, and the `scene` is not assigned to a room, then _only_ the user who linked that service to Google Home can activate it. Like... what?

Here is what my wife sees on her phone under scene control. Notice how she's missing a few scenes that are available to me? Isn't that just peachy?

![Google Home scenes missing](/assets/img/2022/10/scenes_3_missing.jpg)*Where did the other scenes go?*

However, if the service provider assigns a room to the `scene`, that entity will get "properly linked" to the Google Home. Then _everyone_ in the household can activate the `scene`.

I haven't been able to figure out how to assign a `scene` to a rooms _inside_ the Google Home app. The Google Home app doesn't appear to have an area to view/rename/modify scenes. To assign a `scene` to a room, it appears that it _must_ be set from the service which is providing it to the Google Home. _How intuitive_.

> tl;dr Assign rooms/areas to your scenes so other household members can use them.

## How To Assign Areas in Home Assistant

> Did you know `scripts` in Home Assistant are added to the Google Home in [the same way `scenes` are](https://github.com/home-assistant/core/blob/dd7a06b9dca8a04152f6c4ef4828c8e214260393/homeassistant/components/google_assistant/trait.py#L522-L530)?

How do we fix this? Let's jump back into Home Assistant to take a look at our scripts or scenes.

![Assigning a script to an area in Home Assistant](/assets/img/2022/10/home_assistant_scene_settings.jpg)*Assigning a script to an area in Home Assistant*

Here I've selected a script that we're syncing with Google Home. It hasn't been assigned to an area yet. That means it won't belong to a room in Google Home. 

If I update this script and assign it to an area, the next time we sync with the Google Home, Home Assistant will be able to provide a _hint_ at which respective room it should be assigned to. 

If the room hint from Home Assistant was successful, then Google Home will have assigned the `scene` to a room. Now the `scene` should be available to all users in the Google Home household.

> I [submitted a pull request](https://github.com/home-assistant/home-assistant.io/pull/24310) to update the Home Assistant documentation and mention this scene/script limitation so others don't sink the same time that I did.

## Why Does This Happen?

In order for devices to be used by Google Home, they need to be set up _completely_. Linking devices to your account in Google Home is not enough. Devices and scenes need to be assigned to a room in order to become part of the household.

Here is an example of an entity that I added from Home Assistant which was never assigned to an area. When Google Home sees this entity, it doesn't know where to place it. Without a placement, the rest of my Google Home household cannot see that entity.

![An entity has not assigned a room or added to the household in Google Home](/assets/img/2022/10/google_home_not_linked.jpg)*This entity has not assigned a room or added to the household in Google Home*

I believe the exact same thing is happening to the `scene` and `script` entities. Except in our case, scenes do not have a standard view in the Google Home app so we're unable to move them into a room from inside the app. 

> One _might_ be able to trigger a view to move existing scenes if they completely unlink and then relink their service to the Google Home. The opportunity may be present upon "first setup". But that's not a very friendly solution.

## Conclusion

I'm not the first user who is bewildered with their Google Home when it accepts my command, but then rejects the same command from my wife. Why would a family trust the reliability of their smart home if every other command failed?

It would be great if Google added a UI to manage scenes, or increased their visibility in the Google Home app. At the very least, Google Home should be able to recognize when a scene is only available for the linking user and raise that error. 

I hope Google cares about their Google Home product and continues to make improvements. If they don't grow this feature, I fear that scene support is destined to be [killed by Google](https://killedbygoogle.com/).
