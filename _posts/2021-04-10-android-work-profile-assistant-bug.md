---
title: Fixing the Google Assistant on My Android Work Profile
date: '2021-04-10 17:13'
comments: true
image:
  path: /assets/img/2021/04/banner.png
  height: 600
  width: 800
alt: Launching the Google Assistant in the Android work profile
published: true
tag: "guide"
description: "How to bypass a bug and set the default assistant app to the Google Assistant on an Android work profile."
amp:
  - video
---

One of the products I develop for at work is a digital assistant for food service operations. Our voice component of the digital assistant is deployed to Google Assistant compatible devices through Actions on Google. To aid in my work I use a personal Android device to test our product. 

In the last few months I have run into conflicts using the Google Assistant on my device's work profile. For the uninitiated, the Android work profile is a separate space on the device dedicated to walling off the areas between personal apps and work apps. Since my work developer account is tied to the company organization, it encourages me to use a work profile when using the account on my device.

## Problematic Assistant

The problem is that while using the work profile, the `Default digital assistant app` can't be set. Worse, the `Voice input` can't be changed back to `Google` if accidentally switched away since it's "un-selectable". 

![Screen showing how the user is unable to change the Default Assistant voice input after changing it in the work profile](/assets/img/2021/04/SelectDigitalAssistantApp.png)*Unable to revert the voice input after changed*

If the `Voice input` isn't set to `Google` in the screenshot above, the work profile will fail to launch the Google Assistant. 

Even worse, if the user tries to tap on `Default digital assistant app` to switch it from `None`, the screen will quickly navigate the user to `com.google.android.permissioncontroller`/`Permission Controller` and immediately return.

{% include video.html
  src="/assets/files/2021/04/UnableToSetAssistant.mp4"
  poster="/assets/files/2021/04/UnableToSetAssistant.png"
  width="300"
  height="650"
  controls="autoplay loop"
%}

My theory is that there is a permission that can't be prompted to the user under the work profile causing it to crash.

## Secondary Bug

On a side note, sometimes while using the work profile the user will be shown `The Google App isn't your default Assist App.` on certain screens. I believe this bug can be resolved by disconnecting the Google app between the work profile and personal profile as shown below. This can be found under the `Advanced settings` section of the work profile Google app info page.

![Screen showing an error about the default digital assistant when trying to train their voice in the work profile](/assets/img/2021/04/DefaultAssistApp.png)*The Google App isn't your default Assist App*

## Solution

Luckily, there's a solution to launching the Google Assistant in the work profile. We do this by manually changing the secure settings on our device's work profile to use `Google` as the `Voice input` for the digital assistant.

### Requirements (that I know of?):

- [Google Assistant](https://play.google.com/store/apps/details?id=com.google.android.apps.googleassistant) is installed on the Android work profile
- ADB (Android Debug Bridge) is setup and connected to the device
- The `Default Assistant App` on your _personal_ profile is the Google Assistant. We need this set to extract the correct `voice_interaction_service` from our personal profile. 

> It probably doesn't hurt to keep the assistant the same between the personal and work profiles to reduce complications between the two spaces. But it's not clear if that's a requirement going forward.

### Steps

1. First we find out the `user` id of the work profile. Here I can see that it's `10`.

    ```bash
    ➜  ~ adb shell pm list users

    Users:
      UserInfo{0:Kyle:c13} running
      UserInfo{10:Work profile:1030} running
    ```

2. Next grab the value for the `voice_interaction_service` from the _personal_ profile. I included this step in the event Google changes the value in the future.

    ```bash
    ➜  ~ adb shell settings get --user 0 secure voice_interaction_service

    com.google.android.googlequicksearchbox/com.google.android.voiceinteraction.GsaVoiceInteractionService
    ```

    > If I try to grab the `voice_interaction_service` value from my work profile, I can't see anything because `shell` access is forbidden.

    ```bash
    ➜  ~ adb shell settings get --user 10 secure voice_interaction_service

    Exception occurred while executing 'get':
    java.lang.SecurityException: Shell does not have permission to access user 10
    com.android.server.am.ActivityManagerService.handleIncomingUser:15083 android.app.ActivityManager.handleIncomingUser:4290 com.android.providers.settings.SettingsProvider.resolveCallingUserIdEnforcingPermissionsLocked:2162
    ```

    Now that we have the value for `voice_interaction_service`, we need to write it back to our work profile. 

    Since the work profile on my device restricts sideloading APKs and shell access, I need an app that can edit the `Settings Database` on my behalf. I chose [SetEdit](https://play.google.com/store/apps/details?id=by4a.setedit22).

    > Make sure you install the app to your device using your _work profile_ or you won't be able to change the correct setting.

3. Grant `WRITE_SECURE_SETTINGS` permissions to the app.

    ```bash
     ➜  ~ pm grant by4a.setedit22 android.permission.WRITE_SECURE_SETTINGS
    ```

4. Open up the `SetEdit` app on the device.

5. Under the `Secure Table`, find the `voice_interaction_service` key and update the value grabbed by the personal profile earlier. In my case it is:

    ```
    com.google.android.googlequicksearchbox/com.google.android.voiceinteraction.GsaVoiceInteractionService
    ```

    ![Updating the voice_interaction_service value with SetEdit](/assets/img/2021/04/SetEditVoiceInput.png)*Updating the `voice_interaction_service` with SetEdit*

6. The result should be instantaneous. Go ahead and open up the Google Assistant app in the work profile via its app icon. It should now load! 

    ![Google Assistant launching on the work profile](/assets/img/2021/04/GoogleAssistantWorkProfile.png)*Google Assistant launching on the work profile*

## Conclusion

The work profile on Android is a neat idea. Separating the user spaces to keep data apart is a cool concept to protect a user's privacy. However, sometimes the system level apps have trouble in this separate space. Especially when they rely on API/Screen calls that aren't _quite_ available.

I hope Google resolves this issue in the future as it's a very annoying bug. Until then, this should serve as a guide to help other users fix their Google Assistant in the work profile.
