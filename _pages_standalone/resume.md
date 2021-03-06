---
layout: no-title
title: Résumé
style: resume.scss
author: "Kyle M. Niewiada"
email: kyle@kyleniewiada.org
description: "Kyle Niewiada's online résumé. This lists his educational background, career, and highlights projects from his blog."
seo:
  type: Website
regenerate: true
permalink: /resume/
---
<header>
<h1>{{ page.author | default: site.author }}</h1>
<a href="mailto:{{ page.email }}">{{ page.email }}</a>
</header>

## Education

### BS, Computer Science; Grand Valley State University

<div class="date">2012 - 2016</div>

- GPA: 3.503

---

## Experience

### Full Stack Developer at Gordon Food Service

<div class="date">Jul 2019 - Present</div>

- Augment support by building a machine learning model to correctly detect chat sentiment and react accordingly
- Manage and upgrade older Terraform/Helm configurations for transient workloads in Kubernetes clusters
- Design and build an asynchronous live chat solution inside of an app to work with a non-asynchronous chat provider
- Build multilingual functionality with Gordon Now Chat to serve customers across the US and Canada

### Associate Software Engineer at Gordon Food Service

<div class="date">Jun 2017 - Jul 2019</div>

- Architected and built a chatbot that switches seamlessly between AI and a human when necessary
- Provided unique digital dialogue opportunities for customers to place orders with an AI agent using only their voice
  - [Product Overview](https://www.youtube.com/watch?v=qekVovXVy5M)
  - [Testimonial #1](https://www.youtube.com/watch?v=C6nYBUw1KJE)
  - [Testimonial #2](https://www.youtube.com/watch?v=svohGSAL0SI)
- Captured customers' interests with a recipe tool enabling food organization and reducing food waste
- Created custom integration jobs between different company platforms 

### Consultant at Hepfer & Associates, PLLC

<div class="date">Sep 2016 - Jun 2017</div>

- Import and investigate raw data from company databases
- Search for behavioral anomalies and trends
- Present data in a meaningful way

### Coach for Grandville RoboDawgs Weather Balloon Program

<div class="date">May 2016 - Jul 2016</div>


- Assisted underclassmen RoboDawg students transitioning to leadership positions in the robotics program
- Directed students to program Python on Raspberry Pi units and collect data from their weather balloon launches

### AP Computer Science Tutor

<div class="date">May 2016 - Jun 2016</div>

- 1 on 1 tutoring in preparation for the AP Computer Science Exam

### Software Developer Intern at Blue Medora, LLC

<div class="date">Summer 2013; Summer 2014</div>

- Developed Oracle Enterprise Manager plugins

### Supervisor for RoboDawgs community camps

<div class="date">Summer 2012</div>

- Instructed up to 40 campers during the busiest week
- Delegated jobs between nine employees
- Conducted new building renovations/repairs

---

## Technical skills

### Jekyll

- Setup, modify, and maintain this Jekyll website
- [Source code](https://github.com/aav7fl/website)

### Experience with:

- Java, Angular, React Native, Kotlin, SQL, HTML, CSS

### Familiar with:

- Ruby, C, C++, C#, Python, Liquid, Markdown, TI-Basic

---

## Honors

### Eagle Scout

<div class="date">2009</div>

- Received silver, gold, and bronze palms
  - Requires an additional five merit badges (beyond the required 21 for Eagle) for each palm, and a three-month observance between each palm. This must occur before a scout's 18th birthday to be eligible.

### Recipient of Grand Valley Music Department Scholarship

<div class="date">2012 - 2014</div>

---

## Projects

### Monitoring Electric Dryer State Using a CT Clamp

- How I now monitor my aging 240V electric dryer with a CT clamp to send a notification when the cycle is complete
- [Blog post](https://www.kyleniewiada.org/blog/2020/09/dryer-notification-addendum/)

### Fixed Controller Input on Xbox Emulator Project

- Traced through machine instructions to discover a compiler was padding an extra byte into memory causing many games to reject controller input
- [Blog post](/blog/2019/08/fixing-star-wars-obi-wan/)
- [GitHub PR](https://github.com/Cxbx-Reloaded/Cxbx-Reloaded/pull/1708)

### Enhanced the Jekyll SEO Tag Plugin

- Contributed to the open source Jekyll SEO Tag plugin introducing new functionality with SEO tags
- [GitHub PR](https://github.com/jekyll/jekyll-seo-tag/pull/151)

### Rebuilt Zelda Save File

- Rebuilt a Zelda Ocarina of Time save file after discovering the checksum algorithm
- Used a GameShark with a parallel port to interface with the N64 cartridge, dump the ram, and recalculate the checksum
- [Open source checksum calculator](https://github.com/Vi1i/OcarinaChecksumChecker)
- [Blog post](/blog/2015/04/transferring-n64-saves/)

### Restoration with 3D Printing

- Restored a vintage amplifier using 3D printing
- An old piece for my 1970s amplifier broke and I used 3D printing to complement my restoration project
- [Blog post](/blog/2013/09/restoring-vintage-with-3d-printing/)


### Reverse Engineered my Desk Remote

- Reverse engineered remote codes to my Steelcase electric desk
- Discovered and documented the remote codes with explanations to each setting
- [Blog post](/blog/2015/08/reverse-engineering-my-steelcase-desk/)

---

## Activities

### University Arts Chorale & Cantate Chamber Ensemble

<div class="date">2012 - 2014</div>

### Grand Valley Computing Club

<div class="date">2012 - 2013</div>

### Piano

<div class="date">2002 - 2013</div>

### Volunteer at Festival of the Arts Screen Printing

<div class="date">Summer 2013 - Summer 2016</div>

---

<p style="text-align:right;">Updated {{ page.last_modified_at | date: '%B, %Y' }}</p>
