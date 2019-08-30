---
title: "Reviving a Game Because of Nostalgia"
date: "2019-08-30 17:36"
comments: true
image:
  path: /assets/img/2019/08/star_wars_obi_wan_banner.jpg
  height: 487
  width: 800
alt: "Star Wars: Obi-Wan custom game banner"
published: true
tag: "medium project"
description: "My dive into how I solved the bug that revived Star Wars: Obi-Wan on the Cxbx-Reloaded Xbox emulator. The process involved stepping through the disassembled game code and working backwards."
amp:
  - video
---


When I dive into a project, I generally have some inkling how I am going to work through it. I have a pretty high confidence on how long it will take or what the outcome will be. For whatever reason, last weekend I had the urge to play my favorite childhood Xbox game, `Star Wars: Obi-Wan`.

Running games on the original hardware is always the best option, but I’m adamant about being able to preserve my content in the distant future. Besides, I can’t always have every console hooked up to the TV; some need to live in storage. I like the idea of having the option of emulation to preserve my games and saves for their future. In fact, that’s what my whole [Nintendo 64 backup project](/blog/2015/04/transferring-n64-saves/) was about a few years ago.

## Growing up on the Xbox

The original Xbox was integral to my upbringing. I remember my parents taking my sister and I to Blockbuster on the weekend. _Sometimes_ they would allow us to rent or even _buy_ a used game; but only if it was under $20.

![Childhood collection of Xbox games](/assets/img/2019/08/games.jpg)*My humble Xbox collection from my childhood*

My dad had a neat deal with his friend. They shared an Official Xbox Magazine. Each issue would come with a demo disc full of playable demos for upcoming games. When a new issue came out, his friend would play with it for a month before passing it along to us. Because we were receiving it last, we could keep it! Every month, my collection of barely playable games increased. It was a thrill be able to pop in a new disc and find out which game demos were on the disc. I didn’t care that they weren’t the full game. It was a blast.

![Collection of Official Xbox Magazine demo discs](/assets/img/2019/08/demos.jpg)*The Xbox demo discs I looked forward to each month*

What I’m really trying to say is that *nostalgia really hits me with the original Xbox*. I have a lot of fond memories with the system. But the cherry on top was `Star Wars: Obi-Wan`.

## My History with Star Wars: Obi-Wan

As a kid, I would spend endless hours exploring each level. I distinctly remember how I would try to complete the training level as fast as possible every time I booted the game (before I knew that speedrunning was a thing). So, if we can get enough interest on a `training level` speedrun category for this game, I’d love to submit an entry.

> For those that want some speedrunning tips on the `training level`, listen up. After the first door, you’re required to crawl through a tunnel. Crawl backwards if you want to go faster. Also, the doors _don’t block force powers_. Sections that involve force pushing droids off ledges or pushing bins to climb on can be triggered before the room even opens.

`Star Wars: Obi-Wan` has a unique functionality where the right thumb stick was completely dedicated to the swinging lightsaber. If you push left, it swings from the left. If you push right, it swings from the right. I think you get where I’m going with this.

{% include video.html
  src="/assets/files/2019/08/saber_swing.mp4"
  poster="/assets/files/2019/08/saber_swing_thumb.png"
  controls="autoplay loop"
%}

The controllable lightsaber added complexity to the game over the traditional single button attack. The player needed to plan each swing of their lightsaber to counter an enemy or avoid getting hit. It’s a cool concept that I wish they would bring back.

Unfortunately, many people find this game to be terrible. Looking online, the reviews for the game average around `6/10`. Obi-Wan controls like a tank, the camera movement is rigid, it’s not obvious how each level should be routed, and the enemies don’t give the player a chance to recover if they falter.

This Star Wars game was exclusive to the original Xbox. Since the reception for the game wasn’t astounding, publishers probably weren’t interested in porting it to later generations. This also meant that gamers weren’t _too_ attracted to getting it running on an emulator.

_But I was._

## Surrendering to Nostalgia

Last weekend while I was relaxing, a thought in the back of my head was imploring me to check the latest compatibility of `Star Wars: Obi-Wan` on [Cxbx-Reloaded]( https://github.com/Cxbx-Reloaded/Cxbx-Reloaded). Cxbx-Reloaded is an emulator for running original Xbox games. The project is doing quite well, and every month they are adding new playable games to their compatibility list.

I went to the GitHub project to check on the latest status of the Star Wars game. I had remembered that a year ago, the game wouldn’t boot in the emulator. But progress had been made and it would now boot to the start screen!

As I read through the compatibility notes, I came across two findings:

1. If the game was left idle, an in-game engine rendered demo would play a prerecorded gameplay script. This demo showed working sound, some glitched graphics, and actions without crashing the game.
2. The game wasn’t accepting input from a controller.

The comment about controller input was several months old, so I was hopeful that maybe it was fixed? I downloaded the latest `Cxbx-Reloaded` build, loaded up my `Star Wars: Obi-Wan` backup, and _anticipated_ that the controller issue had been fixed. But to my dismay, the game still wasn’t accepting controller input.

> [Cxbx-Reloaded/game-compatibility/Star Wars Obi-Wan [4C410001]](https://github.com/Cxbx-Reloaded/game-compatibility/issues/666)

Unsure of what I could do with this project, I navigated to their Discord channel and asked if anyone had any idea what to do. I even toyed around with the idea of offering a bounty if someone else could fix the issue. In the end, the friendly developers suggested running `Cxbx-Reloaded` with the logs turned on for `Xapi` (logging controller input).

```
[0x2C3C] XAPI    XInputOpen(
   DeviceType           : 0x003B41A0
   dwPort               : 0
   dwSlot               : 0
   pPollingParameters   : 0x00000000
);
[0x2C3C] XAPI    XInputGetCapabilities(
   hDevice              : 0x045170C0
 OUT pCapabilities      : 0x096BED70
);
[0x2C3C] XAPI    XInputGetCapabilities returns 0
[0x2C3C] XAPI    XInputClose(
   hDevice              : 0x045170C0
);
```

That’s exactly what I did. Almost immediately after I posted my log, they spotted an irregularity where the Star Wars game was closing the controller almost instantly after connecting with it. They suggested I crack open a debugger, place breakpoints in certain methods, and see if anything returned was out of place.

I wasn’t exactly thrilled to dig into this. The whole project was unfamiliar, I hadn’t touched C++ in several years, and setting up a dev environment on Windows is never fun.

![Star Wars Obi-Wan facing Darth Maul in-game](/assets/img/2019/08/darth_maul_battle.png)*Darth Maul Battle (Shaders are a bit off on the emulator)*

## Building the Code

After debating with myself internally for an hour, I decided that my love for `Star Wars: Obi-Wan` was greater than my discomfort for a project I understood nothing about. I forked `Cxbx-Reloaded`, cloned the source code, and began working through the `README` to set up my environment.

Setting up the project on my machine was nothing but frustrating. When I first installed Visual Studio 2019, I missed a step to install the `.NET 4.5 Developer Pack`. For whatever reason, I was unable to find this exact developer pack version online. I could only find the `.NET 4.5.1 Developer Pack`.

This really shouldn’t have been a big deal. But because the framework wasn’t an exact match, every time I opened the project, it complained that I didn’t have the correct .NET framework installed and it wanted me to find the correct version. To fix this, I had to uninstall Visual Studio 2019 and reinstall it again (but this time making sure to select `.NET 4.5 Developer Pack` during the installation steps).

Another bump that I hit was that the `Cxbx-Reloaded Debugger` companion project would not compile. That meant that it kept breaking my build for `Cxbx-Reloaded`. With some help from another developer on the Discord channel, they suggested that I simply unload the `Cxbx-Reloaded Debugger` to continue developing. Who knew it was that easy?

I followed their directions and eventually I was able compile `Cxbx-Reloaded`; it only took my whole day to setup.

## Tracing Through

Before I had even started debugging the code, I felt like giving up because how difficult it was to _build_ a _working version_ of the code. But my nostalgia kicked my drive back in gear and I dove in.

I started by debugging the `XInputGetCapabilities`. The developers on Discord figured that whatever the Star Wars game was requesting for controller capabilities wasn’t matching what the emulator was giving it. Through a lot of debugging and comparisons with other games in my library, I was able to support their assumption. I noticed that as soon as the Xbox polled for new controller changes, it would request the controller capabilities. Almost immediately after, the game code would run and then something would magically call the emulator method to close the controller.

I thought it was incredibly odd and for an entire day I believed the emulator code was closing off the controller. Of course, knowing nothing about how this emulator or the Xbox worked, my assumption was incorrect. After speaking with the Discord channel once again, they were able to direct me to the call stack that contained the disassembled game code. _This is where the fun begins._

## Into the Disassembler

It never really occurred to me that I would be able to debug the game code through the emulator. I knew I wouldn’t be able to debug the emulator source code, but the thought never crossed my mind that I would be able to step through the disassembled game code. What felt like a tribute to my computer architecture classes in college, I was once again facing x86 assembly code.

I’m not sure if you know about this but debugging machine code is like time traveling. As soon as you start stepping through instruction sets, time around you will warp and you will lose an entire evening to the `next line` button in your debugger.

Debugging the disassembled game was awfully tedious. For the first couple hours I had no idea what I was looking for other than the fact that 40_ish_ instructions would run and then close the controller. Eventually, I had the brilliant idea of opening the memory of the emulated console to see how each instruction was affecting active data. Once I figured out how to use the memory map with my debugger, everything started to get easier.

![Star Wars: Obi-Wan Battle Royale mode](/assets/img/2019/08/battle_royale.jpg)*Playing battle royale in Star Wars: Obi-Wan (Shaders are a bit off on the emulator)*

With a second monitor dedicated to x86 instruction definitions and bit calculators, I started from the last call before the controller was closed and began working my way up through the instruction set. Eventually, I started to feel like I had a pattern. There was a certain memory address that I knew of and any instruction pointing to it was going to call the method to close the controller. After a while I noticed a _single instruction_ around the same area that would send the user to a _different_ memory location. I assumed this was the condition that would _not_ close the controller.

It felt a little bit strange. I was naming groups of disassembled code and attaching negative emotions to certain jump instructions if the program ran into them. Programming is weird.

Since I had identified a `jump` instruction of interest, I had to discover what values each register needed leading up to it. Each time an instruction pulled from memory, I had to figure out what values were needed to give the correct register result. Each time I passed the active instruction in my debugger, I had to restart the process so I could confirm that a change in memory didn’t affect any other instructions leading up to that point.

After a couple hours, I had finished working all the way up the chain. I finally figured out what bytes in memory were necessary in order to hit the _one_ `jump` instruction that didn’t close the controller. I was excited. As soon as had my result, I detached the debugger from the emulator and tried to play my game. This time, the controller worked! I shouted with joy that modifying these silly bytes on my machine could result in functional gameplay.

## 0xFF

After it was all done, the result was that I needed to change a single byte to `0xFF` in order to pass the controller capabilities check. What a silly change. I made the change in code to modify the single byte and ran it again. This time when I looked at the memory map, I noticed that the controller capabilities were 23 bytes of `0xFF`, and they immediately followed the one byte that I needed to change to `0xFF`.

![Visual Studio 2019 Debugging Disassembled Game Code](/assets/img/2019/08/debug.png)*Finding the relationship between controller capabilities, memory, and disassembled game code*

If you’re like me, you’re probably noticing something here. Everything looks like it’s shifted over too far. My original theory was that the offset was incorrect by 1-3 bytes. I brought my findings to the Discord channel with a lengthy explanation to my findings. Within 10 minutes, another developer concluded that the compiler was adding an extra byte into the controller capabilities header in order to align it to a normal 4 bytes. Since the controller capabilities header only needed three bytes, there was an extra byte that wasn’t supposed to be used, which caused the controller capabilities to be shifted over by one byte.

After a quick discussion on how they should resolve it, they offered me the opportunity to create the PR to implement the fix. The fix was to include a different header with the controller capabilities header `struct` that prevented it from adding an unused byte in the memory layout.

> [Cxbx-Reloaded Pull Request #1708](https://github.com/Cxbx-Reloaded/Cxbx-Reloaded/pull/1708)

About an hour later, the pull request was merged. As a bonus side effect, the community has begun discovering other games with controller input issues that were solved with this fix.

Solving this issue had a very high risk but was extremely rewarding.

1. There was no guarantee that a reasonable solution existed.
2. Debugging through disassembled code is quite tedious and can lead to easy mistakes.
3. If a solution existed to solve the controller input, did I have the skill to implement it?
4. If I had the skill to implement it, would it break compatibility with other games?
5. If a solution existed, was it specific to this game, or did it apply to other games? (The spirit of the project was to avoid game specific patches unless it affected them all)
6. If I managed to find a fix and implement it, would the game even get beyond the start menu or crash right away?

Lucky for me, everything worked out. But due to many of the reasons above, it could have gone nowhere fast.

## Final Thoughts

I’m proud of the work that I did to solve the controller input issue with this game. It is great to step back and enjoy some work you’ve done on a project. It’s healthy to be proud of code that helped you grow, even if the solution is simple. Everything that was learned along the way, and the result of that change can have a larger impact than what was ever intended.

Sure, this fix means that a few _other_ (less exciting) games have working input now as a result. But really, I did this so _everyone_ can have fun playing `Star Wars: Obi-Wan`. ¯\\\_(ツ)\_/¯

_Why am I obsessed with this game?_
