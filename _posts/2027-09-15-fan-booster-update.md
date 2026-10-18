---
layout: post
title: 'Rebuilding (a New) Vent Booster to Balance My Bedroom Temperature'
date: '2027-09-15 08:08'
#date: '2027-09-15 08:08'
comments: true
image:
  path: /assets/img/2027/09/vent-booster-installed.jpg
  height: 600
  width: 800
alt: Custom vent booster housing and fans installed
published: true
tag: "medium project"
description: "Results from my second attempt and creating my own vent booster fan setup"
---

In 2026, I [built a vent booster fan](/blog/2026/10/bedroom-temperature-improvements/) in an effort balance some of the temperature fluctuations in my bedroom. After testing my old design that summer, I came to to the conclusion that the experiment had failed. The data showed no statistically significant difference in balancing my bedroom temperature compared to previous years. At the end, I was disappointed, but convinced I had gone wrong somewhere. I had some ideas, and I wanted to try it again. This is attempt #2 at building a duct booster fan to balance my bedroom temperature.

<!-- ## Table of Contents -->

{% include toc.html %}

<!-- If an HTML tag has an attribute markdown="block", then the content of the tag is parsed as block level elements. -->
<!-- https://kramdown.gettalong.org/syntax.html#html-blocks -->
<details markdown="block">

<summary>Changelog</summary>

> - 2026-07-13: Changelog Entry #1
> - 2026-07-14: Changelog Entry #2
> - 2026-07-15: Changelog Entry #3

</details>

## Recap

Let's get this out of the way in case you didn't read [last year's entry](/blog/2026/10/bedroom-temperature-improvements/).

I couldn't find a pre-existing baseboard compatible vent booster fan system. So I built my own and made sure it would work with [Home Assistant](https://www.home-assistant.io/) for managing it. And then I did it a second time.   

1. Booster fans are a band-aid

    HVAC booster fans are often a band-aid to a bigger problem. There could be broken ducts or poorly sealed gaps in the system. The HVAC design could be flawed. It could interfere with dampers. If it's a newer system, it could damage the motor.

    However, mine are none of those. I have no zoning (only manual registers or dampers that I can close). My HVAC blower goes at one speed. My ducts are intact. I just have a poor design from the 1970s.

2. In-line duct booster fans are superior

    I wish I could have installed an inline booster fan and called it a day. Those things easily put out 400 CFM. Unfortunately, there aren't any suitable locations to install one since the giant trunk line is only 8 ft. away from the final branch supply in our bedroom. 
    
    I'd have to rip up flooring or a ceiling, and run additional electrical through finished spaces. 

    It's a better solution on paper, but doesn't apply very well to my specific room.

## Solutioning

After last year's poor results, I wanted to target my main findings.

1. Improve air flow
2. Fix turbulence
3. Sealing

As I was already at the limit on how many fans I could shove inside my ducting, I decided my next approach would need to relocate them somewhere else. Like the on the vent itself.

I started with [this model](https://www.thingiverse.com/thing:7167605) from `inquiz`. They provided a few different baseboard vent designs for commercial vent booster inserts. Notably a 15" one. 

But instead of using a commercial vent booster, my plan was to modify the design to fit larger computer fans. 

The computer fans would plug into an [ESP32-S2 WiFi Fan Controller](https://github.com/zeroflow/wifi-fancontroller). I would then manage and track them inside Home Assistant. 
 
### Modifications

The first thing I did to inquiz's model was change the front plate to my fully removable. 

![CAD overview of custom vent booster fan](/assets/img/2027/09/vent-cad.png)*CAD overview of the custom vent booster fan*

Since this would all be hidden under my bed, I didn't need it to be pretty--just functional.

I wanted to install computer fans on it. If I did that, I wouldn't be able to easily hold the fans in place while screwing into them. 

I popped in some support holes in the back of the unit to fit M3 heat set inserts. This would allow me to bolt the front plate on repeatedly without tearing away the material using a screw.

Next, I added 3 larger holes in the new faceplate to mount 92mm fans. My plan was to go with Noctua NF-A9 PWM fans along with some concentric wire fan guards to protect the fingers of curious toddlers.

After that, I continued the idea of mounting the fan controller on the outside of the vent for any future maintenance. I added a hole in the side for a 1" hole-sized closed rubber grommet.

Last, I put holes in the back corner of the vent body so it could be attached to the floor. All of the baseboard vents in my house require me to screw them in on an angle, so I added an angled strain relief so the screws wouldn't snap the filament as easily.

Here's my model: <https://www.thingiverse.com/thing:7413541>

## Ordering

I still don't own a 3D printer. I didn't really want to buy one yet either (even though I have many things I'd want to print). Also, I didn't want to spend all of the time researching which one to get, and then spend longer deciding between slicing my model up or buying a large format printer.

So I used one of those [commercial 3D printing sites](https://craftcloud3d.com/) that let you see bids from other companies. 

I chose to print my design in PETG. Since my duct was really far away from the furnace, I didn't feel like I had to worry about any hot temperatures warping the piece over time. By the time the air would get to my vent, it would be much colder. 

$170 💸 and 15 days later, I had the print in my hands. Yea, that cost more than I expected. I wasn't willing to entertain to other option of buying or building my own large-format 3D printer. (and then I have to take care of my filament in a dry box, ensure my prints don't fail, keep the environment stable, etc.). So I chose to spend money on this one-off.


## Assembly


The part arrived and I goofed. The holes in the front plate didn't align with the base box. 

Easy thing to fix though. I covered a toothpick in sharpie and was able to trace the holes from the back and drill new ones into the faceplate. (This is fixed in my final design)


I used my soldering iron to melt in some M3 threaded inserts into the vent body.

![Soldering iron melting threaded inserts into a PETG model](/assets/img/2027/09/vent-melting-threaded-insert-in.jpg)*Melting M3 threaded inserts into my 3D print with a soldering iron*

The fans (and their concentric wire fan guards) all fit. But the spacing between each fan was a little too tight for my comfort. I ended adding 1mm of spacing between those in my final design if someone else wants to print it.

The black wire grommet popped right into the side without any issues.

I put the front plate on the vent body to perform a test fit and to see how the wires would be routed out the side. 

![3D-printed vest booster fan shown from the front after first assembly](/assets/img/2027/09/vent-test-fit-fans-front.jpg)*Test fitting hardware and verifying spacing*

![3D-printed vest booster fan shown from the bottom with spacing behind the fans](/assets/img/2027/09/vent-test-fit-fans-underneath.jpg)*Test fitting showing plenty of room for the fans behind them*

## Install

With everything fitting perfectly, I proceeded to the install. As I mentioned before there were some air-leak gaps that I was concerned would lower the efficiency of the fans. I had some Nashua 324A foil tape from previous HVAC projects so I used that the seal the gaps between the duct and the flooring.

![Baseboard duct edges sealed with Nashua 324A foil tape](/assets/img/2027/09/vent-duct-tape.jpg)*Sealing the baseboard duct edges with Nashua 324A foil tape*

The angled screw reliefs in the back of the vent body were perfect. I was able to tuck this into the baseboard corner with easy. After that, I bolted the front plate on and plugged the new fans into my controller.

![Custom 3D-printed vent booster fan installed over baseboard duct](/assets/img/2027/09/vent-booster-installed.jpg)*Final installation of the 3D-printed vent booster fan*

What a beauty! 😍

## Initial Impression

This is _way_ better than my previous attempt. Last year, I had to put a tissue paper in front of the vent and watch it sway, otherwise I couldn't tell if the fans were actually moving air.

This time, I could feel the air over my hand from a few feet away. Clearly we're off to a better start. 

## Results

This is what you're all here for. You want to see if my experiment has failed for a second year in a row, or if it's finally a success. 

I'm proud/ashamed to announce that it is a success/failure. 🎉



## Additional Thoughts

You could probably fit larger fans into the case. Luckily, you only need to make modifications to the front plate piece. It's super easy to do in OpenSCAD if you decide to proceed. This would give to the benefit of even _more_ air flow.

## Final Thoughts

TBD





## Remove Metadata

```bash
exiftool -all= -overwrite_original -r .

exiftool -gpslatitude .
```

