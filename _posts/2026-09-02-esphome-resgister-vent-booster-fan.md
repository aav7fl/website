---
layout: post
title: Trying to Cool My Bedroom with ESPHome Vent Booster + Other Ideas
date: '2026-09-03 08:53'
# updated: '2026-09-03 08:53'
comments: false
image:
  path: /assets/img/2026/09/04-register-fans-realignment.jpg
  height: 600
  width: 800
alt: An array of 5 Noctua NF-A6x25 fans stuffed into an HVAC duct pointed diagonally upward into a baseboard vent along a bedroom wall.
published: true
tag: "medium project"
description: "Attempting to cool my bedroom using an ESPHome controller baseboard register booster fan in hopes of balancing out my HVAC flow."
---

Our bedroom is at the end of an HVAC trunk. It gets uncomfortably warm. Not enough to keep us awake, but warmer than we would prefer. The airflow from the supply register in this room isn't spectacular. There isn't a blockage, it's just a suboptimal design from the 1970s.

From testing, we could see the the thermostat in our kitchen had no problem reaching our setpoint temperature. But our bedroom always lagged behind a couple degrees from our setpoint. We were seeking a more even temperature distribution throughout the house. 

<!-- ## Table of Contents -->

{% include toc.html %}

<!-- If an HTML tag has an attribute markdown="block", then the content of the tag is parsed as block level elements. -->
<!-- https://kramdown.gettalong.org/syntax.html#html-blocks -->
<!-- <details markdown="block"> -->

<!-- <summary>Changelog</summary> -->

<!-- > - 2026-07-13: Changelog Entry #1 -->
<!-- </details> -->

## What We Tried First

Over the last 6 years, we've made a few changes to help influence the temperature in our house.

- **2020**
  - Locate and seal gaps using a thermal camera.

![FLIR showing an uninsulated stud bay](/assets/img/2026/09/thermal-camer-reveal.png)*Thermal camera revealing an uninsulated stud bay in our bathroom wall*

- **2021**
  - Replace the roof and add better ventilation through ridge vents and additional soffit vents.
  - Add new attic insulation.

![Before and after new insulation was installed in the attic](/assets/img/2026/09/insulation-before-and-after.png)*Before and after new insulation was installed in the attic*

- **2023**
  - Add window air conditioner. This worked well until wildfire smoke seeped in and ruined our indoor air quality. We don't install it anymore because of that. 🚭

- **2025** 
  - Adjust basement supply registers/dampers to force air to the main floor. This is like creating a our own manual zoning. This helped for sure! But be careful not to burn out the HVAC blower motor.

## What We Tried In 2026

For the summer of 2026, I wanted to try a few more things.

### Lower the Temperature

First, we lowered the thermostat by 1 degree at night. Obviously this helped it feel cooler because it _was_ cooler. But I wasn't satisfied with those inefficiencies since lowering the whole house by ~1 degree at night required an additional ~2.46 kWh of energy from our air conditioner over our nightly baseline. 

That's ~$0.55 at our current pricing spent each night, or ~$50 throughout the summer months. All to cool down a single room while unnecessarily cooling the rest of the house.

I could do better.

### Ceiling Fan

Second, run our ceiling fan on a schedule to make it _feel_ cooler. Running this for 8 hours consumes ~0.32 kWh. That's ~$0.07 a night or $6.50 for the summer months. 

Right off the bat, ceiling fans won't make the temperature in the bedroom cooler. Instead, they create a wind chill effect and help sweat evaporate throughout the night. So if it _feels_ colder, our goal is basically met?

Air that makes it into the room from the vent is supposed to be circulated around instead of trapped on the floor and taken right back out via the return vent.

### Vent Booster

Third, install a single vent booster to help lift the cooler air into a specific bedroom. 

This idea has _so many_ caveats. Like:

- Are there existing problems with the ducts that would prevent this from working?
- Can the return vent handle the increased pressure, or will it create a back-pressure situation in the room?
- Will this draw out air from other nearby rooms instead?
- Will this prevent other rooms on the same main trunk from getting proper airflow?
- Will the fans block air if they're too slow?

And really, I should be mapping out the air pressure and flow from each vent to know how to properly balance it. But I also have an older HVAC blower that only runs at one speed. It wouldn't be easy make adjustments the _correct_ way without an ECM motor.

With all of those aside, I wanted to try the vent booster. 

My catch is that I have a baseboard diffuser supply register. My supply comes out of a rectangle on the floor near the baseboard, then a supply register angles and diffuses it out into the room. 

![Empty baseboard register](/assets/img/2026/09/01-empty-register.jpg)*Empty baseboard register*

I couldn't find any commercial duct booster vents that fit this supply style.

There are some DIY kits that allow you to put standard 4x10" booster fans into a 3D printed adapter housing. But those were pretty expensive ($70-$100+), and they still didn't include the booster fans (💸).

An in-line booster fan would be _great_ in this situation since they can reach a pretty substantial flow. However, there aren't any suitable locations to install one since the giant trunk line is only 8 ft. away from the final branch supply in our bedroom.

Instead, I decided to try my hand at assembling my own vent booster fan.

## My ESPHome Vent Booster Fan

Here are the components to my vent booster fan.

### Fan Controller

Fan Controller: [github.com/zeroflow/wifi-fancontroller](https://github.com/zeroflow/wifi-fancontroller)

As always, I wanted something that could connect to my [Home Assistant](https://www.home-assistant.io/) setup and remain local to my network. I chose to use an existing fan controller project running on [ESPHome](https://esphome.io/). 

This fan controller is mostly meant regulating temperature in enclosures such as server racks, media consoles, or 3D printers. The fan controller is _totally_ an overkill for what I'm doing. But at that price point, the time saved on the complete package was worth it. 

### Fans

Fans: 5 of `Noctua NF-A6x25` (PWM, 4-Pin, 60mm)

The first reason I chose these 60 mm fans is because they fit in my duct. My duct opening is ~300 mm x ~56 mm. The 60 mm fans are about the closest I can get to optimizing my space. 

5 of these strapped together with zip ties are right around the size I need.

![Noctua fans assembled](/assets/img/2026/09/noctua-fans-assembled.jpg)*Noctua fans assembled*

Next, I selected these fans because they have a decent airflow at 17 CFM. With all 5, that's roughly 85 CFM in the _best possible scenario_. But given that I'm fighting duct pressure and louvers in the vent, it is probably half that around 40 CFM.

Importantly, they have a higher static pressure of 2.18 mm H₂O compared to ~1.0 mm H₂O that most other 60 mm computer fans produce (obviously ignoring server fans which can top out over 10 mm H₂O).

Each fan draws 1.44 watts at its maximum speed. The combined array draws around 7.2 watts or 0.0072 kWh. Not too bad.

### Integrating

If you have a keen eye, you'll notice that the fan controller has 4 ports and I have 5 fans.

Since all of my fans are supposed to _roughly_ run at the same speed, I ran a standard PC fan splitter for the 1st and 5th fans. 

It's advised to run the adjacent fans at a different RPM to avoid harmonic resonance caused by overlapping acoustic frequencies. I ignored that wisdom and ran all of mine at full speed anyway since they're tucked away under my bed.

If I decide that the harmonic balance is a problem, I can still run every other fan at a slightly different speed. The only drawback I could come up with is that I'm giving up stall protection for one of my fans.

I flashed ESPHome onto the board using one of the factory configurations in the [zeroflow/wifi-fancontroller](https://github.com/zeroflow/wifi-fancontroller) repo. Then I connected it in Home Assistant to view the sensor data and make modifications.

### Assembly

Last, I needed to assemble everything together. As I mentioned before, I have a baseboard register that I was trying to stuff this into. My idea was to pack the fans into the duct, drill a hole into the side of the baseboard register, add a grommet, and lead the wires to the controller sitting on the outside.

![Baseboard register with wiring grommet installed](/assets/img/2026/09/00-register-with-grommet.jpg)*Baseboard register with wiring grommet installed*

Since my fan array was slightly deeper than my vent opening, I tried placing them on top of the duct opening. I didn't _really_ like that idea because that meant some of my fans were being placed over dead areas, and there were unsealed gaps on the side. That would affect the airflow design, and I don't have a GPU that could possibly run these airflow simulations.

![Baseboard register fan test array test fit](/assets/img/2026/09/02-register-fan-test-fit.jpg)*Lots of air leakage on the sides when fit like this, which reduces static pressure.*

Also, when I tried to close the vent, the fans were slightly too tall for the vent casing and caused the edges to bulge out. I didn't like that.

![Register fans test fit fail](/assets/img/2026/09/03-register-fans-test-fit-fail.jpg)*Baseboard register doesn't reassemble completely with the fans angled like this.*

My next idea was to shove the fans _into_ the vent. Since they were taller than the duct opening, they would have to go in _on an angle_. They would still be moving air upward, but diagonally ♝. This would be slightly more turbulent, but it seemed like a better option than what I had before. I decided to test it.

![Register fans inserted into ductwork at an angle](/assets/img/2026/09/04-register-fans-realignment.jpg)*Register fans fit perfectly when inserted into ductwork at an angle*

They fit inside the duct, that's a good sign!

![Baseboard register closed with fan array inserted perfectly](/assets/img/2026/09/05-register-fans-final-fit.jpg)*Baseboard register closed with fan array inserted perfectly*

And the register closes too!

I turned it on and set the fan array speed to maximum. I grabbed a tissue a held it front of the vent. 

And it moved! ... _barely_.

I set the fans to run at their maximum speed 24/7. My hope is that if there was any data to be gathered, this would make any changes more apparent. Whether it improved temperature, humidity, or CO₂ levels at night. I wanted to see _any_ change.

## Results

### Ceiling Fan

Ceiling fan was a success. My wife said "it feels cooler" when it was on and often made me shut if off🏆. So that worked.

Here's a super relevant Technology Connections video if you want to go down a short rabbit hole: <https://www.youtube.com/watch?v=_KWdCqpXB7A>.

### Vent Booster Fan

After running my vent booster all summer, the results are in...

and I found no statistically significant improvement between the summer of 2025 and 2026. Let's break it down with 2 graphs.

Here is my first graph. It is showing the average temperatures in the summer recorded by the kitchen thermostat and bedroom year-over-year.

![Average temperatures in the summer recorded by my bedroom and kitchen from 2024-2026](/assets/img/2026/09/summer-temperatures.png)*Average temperatures in the summer recorded by my bedroom and kitchen from 2024-2026*

2024 was hot for us (and earlier years were worse). 

In 2025, I adjusted basement supply registers/dampers to force air to the main floor. This showed a statistically significant improvement and really helped!

In 2026 we lowered the thermostat 1 degree, ran the ceiling fan more frequently, and added a vent booster to the bedroom.

This graph alone doesn't really tell me that much because in 2026 I introduced an uncontrolled variable by lowering the thermostat temperature 1 degree in the summer of 2026. So it _looks_ like it was a success, but in reality it's lower because the thermostat setpoint was lower.

Because I lowered the thermostat, my raw readings year-over-year from the first graph are no longer comparable. So instead I attempt to handle this by instead measuring the _delta_ between the kitchen thermostat and bedroom temperatures, and then average the values out over the course of all sleeping hours.

However, if I instead take the temperature _delta_ between the kitchen thermostat and bedroom, I can get a _slightly_ better picture at what's going on.

Here I have a graph showing the year-over-year summer nighttime temperature _delta_ between my kitchen thermostat and the temperature of the bedroom. The idea is to show how much the bedroom lagged behind the kitchen thermostat.

![Year-over-year summer nighttime temperature delta: bedroom vs. kitchen (2024–2026)](/assets/img/2026/09/nightly-bedroom-excess-temperature-over-kitchen.png)*Year-over-year summer nighttime temperature delta: bedroom vs. kitchen (2024–2026)*

There is a _slight_ caveat that because I'm adjusting the temperature I'm _also_ introducing other variables such as heat retention of materials and temperature rate changes (due to it running longer in the evening). But my hope is that they are just noise in my charts that get filtered out with longer observation periods.

Also, running the ceiling fan doesn't make it cooler in the room. It just makes it _feel_ cooler and it _could_ swirl around some of the colder air that sank to the floor.

The big thing that should have changed the graph in 2026 was the vent booster fans.

But it didn't. Is that a failure? Kinda. But there's nothing wrong with that. I either got something wrong, or my premise is wrong.

## Why Didn't This Work?

I came up with a handful of reasons why I don't think it worked this year.

First: The fans have weak airflow. Trying to move air through all of these bends and louvres is difficult. 

Second: The fans were installed at an angle. This creates more turbulence and reduces the velocity of the air.

Third: Leaky edges. I should have used some HVAC tape to seal up the edges around the duct work to both smooth the airflow and to keep it from going between the flooring layers. Even the edges _around_ the fans inside the duct could be considered leaky.

## What Could Make This Better?

If I want to test this again next year and completely rule out whether or not the booster fan idea is junk, these are the areas that I want to improve.

- Increased airflow
- Less turbulence
- Better sealing

## What's Next?

I could take one of the community made booster fan covers (for baseboard registers) and slap on 3 larger fans. Then I could plug those into my fan controller.

Something like this would work nicely as a start.

- <https://www.thingiverse.com/thing:7167605>

I'd need to make modifications to the opening to properly fit common-sized computer fans, put my grommet hole back in the side, and make some other tweaks.

Oh look, did I make a prototype? I wonder what will happen in 2027.. 👀

![Baseboard register vent split into two pieces](/assets/img/2026/09/vent-prototype.jpg)*Baseboard register vent prototype for future testing 👀*

Is that the most effective $ spend? Probably not. Am I going to learn something through this continued experiment? That's the goal!

## Conclusion

I wanted to make my bedroom feel cooler this summer along with fixing some temperature imbalance between this room and the house. 

I'd say I definitely found the ceiling fan helped things feel cooler. But I think there is still more that I want to do to remediate the temperature imbalance and save a bit of money. I want to know if my ideas work and what I can continue to learn from this next year. 🎓
