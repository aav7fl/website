---
title: Upgrading My Logitech MX Ergo Trackball with USB-C
date: '2024-05-07 20:51'
updated: 2025-06-21
comments: true
image:
  path: /assets/img/2024/05/mx_ergo_trackball_usb_c.jpg
  height: 600
  width: 800
alt: Logitech MX Ergo trackball with USB-C port
published: true
tag: "small project"
description: "Upgrading the charging port on my Logitech MX Ergo trackball with a USB-C mod."
---

Trackballs are a fine alternative input device for driving computers. They excel with slinging the cursor across multi-monitor setups. When used correctly, they can help reduce wrist strain. I started taking trackballs seriously over a decade ago as part of a package solution to mix in a variety of inputs with daily computer usage. In 2013, for less than $20, I picked up a Logitech M570 entry-level trackball. Pairing the trackball, an external trackpad, and a split keyboard together helped break up the repetitive movements that were giving me trouble 🧘. 

> 2024-11-15: Babalooi in the comments informed me that Logitech has released an updated MX Ergo model — the MX Ergo S. The major changes I've identified include a USB-C port, silent switches, and supporting the Bolt receiver.

## Throwback

When 2017 _rolled_ around, I was ready to upgrade. Don't get me wrong, the M570 still functioned just fine, but the Logitech MX Ergo trackball was a solid upgrade. The MX Ergo featured a rechargeable 4-month battery, Bluetooth, and it allowed switching between 2 computer profiles without pairing it again. These features meant I could go dongle-free on my work laptop. I also wouldn't need to pair the MX Ergo to my desktop every time I brought it home. With my future looking bright, I ordered it the first day it was available from Logitech's website; September 6, 2017.

The MX Ergo did everything that I wanted. But Logitech made the insane decision to ship a product in their premium MX line with a Micro USB port 🙁. Unfortunately, USB-C wouldn't trickle into the Logitech lineup until a year later in 2018 with the MX Vertical. While all of my other devices were making the transition into the USB-C world, this device was left behind.

## Trapped in the Past

It's a first-world tragedy when all I want is to carry one charging cable in my bag without giving it a second though. I only have a handful of devices that I regularly use which don't have USB-C ports.

- ~~2016 Bose QuietComfort 35 Headphones (Has a proper USB-C successor ✅)~~
<details markdown="block">

<summary>Bose QuietComfort 35 USB-C Mod</summary>

In 2025, I decided look for USB-C mods available on the Bose QC 35 headphones. My headphones were solid, I used them daily, wanted the convenience of a single charging cable, but I wasn't interested in replacing them with a newer model.

Others have tried using the Bose QC 45 USB-C daughter boards as drop-in replacements in the Bose QC 35. They work, but I've heard of some users mention that the Bluetooth light will stay illuminated all of the time. So it's not 100% backwards compatible with the QC 35.

But I found a project on GitHub that seemed promising.

- [jamesturton/bose-qc35-usb-c](https://github.com/jamesturton/bose-qc35-usb-c)

The project includes designs for a daughter board design with USB-C that is compatible with Bose QC 35 headphones. However, they do not sell any assembled boards. Users are welcome order pre-assembled boards from a PCB manufacturer, but it's not cheap.

I found a user on Reddit ([/u/starkdrive](https://www.reddit.com/user/starkdrive/)) who was offering assembled boards that _might_ be using the same design. They were available at a reasonable price, so I went this route.

It worked out great! No blue light issue and they fit perfectly in my Bose QC 35 headphones.

Here's a picture of the assembled red daughter board in my Bose QC 35 headphones:

![Bose QuietComfort 35 with USB-C daughter board installed](/assets/img/2024/05/bose_quietcomfort_35_usb_c_daughter_board.jpg)*Bose QuietComfort 35 with a red USB-C daughter board installed*

With everything fully assembled:

![Bose QuietComfort 35 with USB-C mod installed](/assets/img/2024/05/bose_quietcomfort_35_usb_c.jpg)*Bose QuietComfort 35 with the USB-C mod fully installed*

_Perfection 👌🧼_

</details>

- ~~DualShock 4~~
<details markdown="block">

<summary>Sony DualShock USB-C Mod</summary>

I was already on a roll with the Bose QuietComfort 35 USB-C mod, so I decided to tackle my DualShock 4 next. My DualShock 4 controller is the primary controller that I use on my PC for gaming. I find it super comfortable and it works well with my original USB Wireless Adapter.

I don't even own a PS4. 😂

Just like my other devices, I wanted the convenience of a single cable to charge my DualShock 4.

Originally, I was going to get the USB-C daughter board from a seller on Tindie, but they were out of stock. So I went with a kit from ElecGear that I picked up on Amazon. The kit was only $15 and included two boards, so it seemed like a good deal.

One super-short install later and we were good to go! The install wasn't nearly as clean as my Bose QC 35 headphones, but it was still a success.

![Sony DualShock 4 with USB-C mod installed](/assets/img/2024/05/dualshock_4_usb_c.jpg)*Sony DualShock 4 with USB-C mod installed*

</details>

- ~~2017 iPad Pro (Has a proper USB-C successor ✅)~~ Upgraded to newer iPad model with USB-C
- 2017 Logitech MX Ergo (No USB-C successor ❌)

Looking back, 2017 was quite the year for me 😅.

## Woe is Me

Whenever I want to charge my (or my wife's) trackball, I have to hunt down another Micro USB cable. My wife doesn't have _any_ other Micro USB devices, so she always has to bring it to my basement office for charging. It's not _that_ big of a deal because it only requires a charge every few months. But it's still annoying that if I'm going to be away, I need to either pack a Micro USB cable or remember to charge it ahead of time.

## Onward

Almost every year I make a casual search to see if Logitech released a USB-C successor for the MX Ergo, but so far they haven't. This year, my search returned a result. The Reddit user, [Solderking](https://www.reddit.com/user/TheSolderking/), [reverse engineered the charging PCB for the MX Ergo](https://www.reddit.com/r/Trackballs/comments/1azxzpo/mx_ergo_usb_c_mod_concluded_dump/). They recreated the board and added a USB-C port. They even went a step further and figured out all the components to redevelop a fully assembled board.

I was so excited to see this. I had been waiting years to banish Micro USB from my regular life (I'm almost there!).  

Solderking [shared their project on PCBWay](https://www.pcbway.com/project/shareproject/Logitech_MX_Ergo_USB_C_PCB_replacement_89459dce.html) along with the Gerber files where anyone can order it bare or fully assembled. PCBWay shows me some promotional quotes for ~$35 for any quantity under 20. I have no idea if that quote is accurate. 

I decided to cut out the middleman and ended up ordering 3 boards directly from Solderking. One for my MX Ergo, my wife's MX Ergo, and a spare.

> If you want to reach out to them as well, [Solderking has a Linktree](https://linktr.ee/solderking) with all their social media links.

## Installation

![A pair of USB-C boards for the Logitech MX Ergo](/assets/img/2024/05/usb_c_boards.jpg)*A pair of USB-C boards for the Logitech MX Ergo from [Solderking](https://linktr.ee/solderking)*

A few days after ordering, the new USB-C boards arrived fully assembled and tested ✅. I know it's not important, since they'll never be seen, but white PCBs are my jam! 

To prepare for my work, I pulled out my trusty iFixit driver, a few bits, some mini files, and flush cutters. I followed their [Instructables directions](https://www.instructables.com/Converting-the-Logitech-MXERGO-Trackball-Mouse-to-/) and disassembled my MX Ergo. 

![iFixit driver, 3 mini files, flush cutters, and the Logitech MX Ergo](/assets/img/2024/05/tools.jpg)*iFixit driver, 3 mini files, flush cutters, and patience were all used to install the new USB-C board*

Using the flush cutters, I trimmed away some plastic to make room for the larger USB-C port housing. With some patience, I used a number of mini files to shave away the edges in the old Micro USB port hole and enlarged it for the new USB-C port.

![Logitech MX Ergo shell bottom with the new USB-C board inserted](/assets/img/2024/05/usb_c_board_installed.jpg)*Logitech MX Ergo bottom shell with the USB-C board freshly fitted*

After validating the new connections, I began reassembly. All I did was follow the original directions, but in reverse 🔄. The grand result; A Logitech MX Ergo with a USB-C port for charging!

![Logitech MX Ergo with a USB-C port](/assets/img/2024/05/mx_ergo_installed.jpg)*Logitech MX Ergo with the USB-C board installed under a magnifying glass*

## Conclusion

My only feedback is that I wish the power switch on the board was clickier to prevent the MX Ergo from getting accidentally toggled-on in my bag. The power switch on the new board seems to slide rather than click into the 'on' position. 

I reached out to Solderking with this feedback. They let me know that this specific power switch was chosen due to availability of parts. They have a few other switches that they are going to try out, but they went with one that was easy to obtain.

If it's really that big of a deal to me, I'll figure out how to transplant the power switch from the old board in the future. I know I have some ChipQuik around here somewhere.. (or maybe that will give me an excuse to finally buy a hot air gun).

![Logitech MX Ergo with the USB-C board installed and fully reassembled](/assets/img/2024/05/mx_ergo_trackball_usb_c.jpg)*Logitech MX Ergo with the USB-C board fully installed and reassembled*

I intend to keep these trackballs operating for a long time. The one in the picture above is from my original order back in 2017. I'm glad that I can keep it going with a modern charging port. Here's to another 7 years of use, and death to Micro USB! 🖲️
