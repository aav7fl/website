---
layout: post
title: 'Tracking Birds at My Feeder'
date: '2026-11-12 22:52'
#updated: '2026-11-12 22:52'
comments: true
image:
  path: /assets/img/2026/11/bird-feeder-camera-setup.jpg
  height: 602
  width: 800
alt: Security camera pointed directly at two bird feeders in front of a wooded background at sunset
published: true
tag: "medium project"
description: "How I'm tracking birds at my bird feeders"

---

Lorem ipsum dolor sit amet consectetur adipiscing elit. Quisque faucibus ex sapien vitae pellentesque sem placerat. In id cursus mi pretium tellus duis convallis. Tempus leo eu aenean sed diam urna tempor. Pulvinar vivamus fringilla lacus nec metus bibendum egestas. Iaculis massa nisl malesuada lacinia integer nunc posuere. Ut hendrerit semper vel class aptent taciti sociosqu. Ad litora torquent per conubia nostra inceptos himenaeos.


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

## TODO

- Add some kind of link with Home Assistant. Automations/camera/tracking? What does the API provide.

## Example Post

Lorem ipsum dolor sit amet consectetur adipiscing elit. Quisque faucibus ex sapien vitae pellentesque sem placerat. In id cursus mi pretium tellus duis convallis. Tempus leo eu aenean sed diam urna tempor. Pulvinar vivamus fringilla lacus nec metus bibendum egestas. Iaculis massa nisl malesuada lacinia integer nunc posuere. Ut hendrerit semper vel class aptent taciti sociosqu. Ad litora torquent per conubia nostra inceptos himenaeos.

## Callout

> Example callout

[This is a link](https://example.com)

## Image

![BirdNET-Go main dashboard](/assets/img/2026/11/bird-feeder-camera-setup.jpg)*My security camera pointed directly at two of my bird feeders*

![Home Assistant dashboard cards showing bird detections and sightings](/assets/img/2026/11/bird-detections-and-sightings.png)*Cross-confirmed detections and sightings between BirdNET-Go and Yet Another WhosAtMyFeeder (YA-WAMF)*

![Collage of 20 different birds recorded by my bird feeder camera](/assets/img/2026/11/bird-feeder-collage.png)*Collage of bird species that my feeder camera has captured in the last few months*

## Remove Metadata

```bash
exiftool -all= -overwrite_original -r .

exiftool -gpslatitude .
```

## Line Numbers

{% highlight bash linenos %}
exiftool -all= -overwrite_original -r .

exiftool -gpslatitude .
{% endhighlight %}

## Table

{: .table-post}
| Syntax      | Description | Test Text     |
| :---        |    :----:   |          ---: |
| Header      | Title       | Here's this   |
| Paragraph   | Text        | And more      |


## Mermaid Diagram

```mermaid
%%{init: {
  "themeVariables": {"edgeLabelBackground": "#ffffff"}
}}%%
graph TD
    accTitle: Example Image Name
    accDescr: Example Description
    A[Start] --> B{Test 1?}
    B -- Yes --> C[Test 2!]
    B -- No --> D[Test 3]
    D --> B
```

## Details

<!-- If an HTML tag has an attribute markdown="block", then the content of the tag is parsed as block level elements. -->
<!-- https://kramdown.gettalong.org/syntax.html#html-blocks -->
<details markdown="block">

<summary>[YAML] Example Configuration</summary>

```yaml
{% raw %}
template:
  - trigger:
      - platform: time_pattern
        # Let's be honest, we don't need to check often. 
        # But 5 minutes should be reactive enough if I need to correct an event date.
        minutes: "/5" 
{% endraw %}
```
</details>


Combining **YetAnother-WhosAtMyFeeder (YA-WAMF)** with **BirdNET-Go** in Home Assistant bridges optical feeder detections with acoustic soundscape data. Below is the complete, self-contained reference for the sensors, automations, and dashboard cards we built.

---

## 1. YA-WAMF Daily Summary `command_line` Sensor & Push Trigger

While YA-WAMF's native Home Assistant integration only exposes the single most recent detection (`sensor.ya_wamf_last_bird_detected`), querying the YA-WAMF `/api/events` endpoint directly gives Home Assistant a complete daily species summary (`sensor.ya_wamf_daily_summary`) that stays 100% in sync with YA-WAMF's database—even if you delete or reclassify false positives in the YA-WAMF web UI.

### Prerequisite: Enable `Last Detection Event` in Home Assistant

To avoid hammering the YA-WAMF API with frequent polling, we use `sensor.ya_wamf_last_detection_event` as a push trigger to update the `command_line` sensor the instant a new bird visits the feeder (mirroring the BirdNET-Go MQTT push pattern).

* **Important Note:** The `Last Detection Event` sensor (`sensor.ya_wamf_last_detection_event`) is **disabled by default** in the YA-WAMF Home Assistant integration. To enable it, go to **Settings → Devices & services → YetAnother-WhosAtMyFeeder**, click on the device, locate **Last Detection Event** under the **Sensors** section (shown as disabled), click it, click the gear icon, toggle **Enabled** on, and click **Update**.



### Step 1A: `command_line.yaml` Sensor

This fetches the last `2000` events from your YA-WAMF instance (sized to comfortably cover heavy 1,600+ detection days), filters for events matching today's local date (`YYYY-MM-DD`), and aggregates them by species with visit counts and latest timestamps:

```yaml
# command_line.yaml
- sensor:
    name: "YA-WAMF Daily Summary"
    unique_id: "ya_wamf_daily_summary"
    command: >
      TODAY=$(date +%Y-%m-%d);
      curl --connect-timeout 5 --max-time 15 --retry 3 --retry-delay 0 --retry-max-time 20 -s
      "<FEEDER_URL>/api/events?limit=2000" |
      jq --arg today "$TODAY" '
        (if type == "array" then . else (.items // .events // []) end)
        | map(select((.detection_time // .start_time // "") | startswith($today)))
        | group_by(.display_name // .label // .species)
        | map({
            common_name: (.[0].display_name // .[0].label // .[0].species),
            count: length,
            latest_seen: (map(.detection_time // .start_time) | max)
          })
        | sort_by(-.count)
        | {species_list: .}
      '
    value_template: >
      {% if value_json is defined and value_json.species_list is iterable %}
        {{ value_json.species_list | length }}
      {% else %}
        0
      {% endif %}
    unit_of_measurement: "species"
    json_attributes:
      - species_list
    scan_interval: 300
    command_timeout: 35

```

(Note: Just like your `sensor.birdnet_*` entities, consider adding `sensor.ya_wamf_daily_summary` to your `recorder: exclude:` list in `configuration.yaml` if you want to keep large attribute payloads out of the Home Assistant history database.)

### Step 1B: Automation to Force Immediate Updates on Every Visit

Because `sensor.ya_wamf_last_bird_detected` doesn't change state when two birds of the same species visit back-to-back, this automation watches `sensor.ya_wamf_last_detection_event` (which updates its event ID on every single visit) and forces `sensor.ya_wamf_daily_summary` to refresh immediately:

```yaml
alias: Trigger YA-WAMF API fetch
description: Forces sensor.ya_wamf_daily_summary to update immediately when a bird lands
triggers:
  - trigger: state
    entity_id:
      - sensor.ya_wamf_last_detection_event
    not_to:
      - unknown
      - unavailable
conditions: []
actions:
  - action: homeassistant.update_entity
    target:
      entity_id: sensor.ya_wamf_daily_summary
mode: queued
max: 5

```

---

## 2. Card: "Feeder Visitor Dossier" (Live Snapshot + Acoustic Lookup)

**What it does:** This vertical stack pairs YA-WAMF's cropped live feeder snapshot (`camera.ya_wamf_latest_bird_snapshot`) with a stateless Markdown card. It takes the species name from `sensor.ya_wamf_last_bird_detected` and cross-references it against your existing `sensor.birdnet_daily_summary` and `sensor.birdnet_species_summary` sensors.

* It pulls the `species_code` from BirdNET-Go to make the bird's name a clickable eBird link.


* It displays the YA-WAMF confidence score, relative time since the feeder visit, and total 24h feeder visits.


* It reports whether the bird in the photo has been **Heard Today** on BirdNET-Go (with count and last-heard time), is a **Silent Visitor Today** (heard in the past, but silent today), or is a **Visual-Only Species** (never detected by BirdNET-Go).



```yaml
type: vertical-stack
cards:
  - type: picture-entity
    entity: camera.ya_wamf_latest_bird_snapshot
    name: Latest Feeder Visitor
    show_state: false
    show_name: false
    tap_action:
      action: more-info
  - type: markdown
    content: >-
      {%- set entity_bird  = 'sensor.ya_wamf_last_bird_detected' -%}
      {%- set entity_time  = 'sensor.ya_wamf_last_detection_time' -%}
      {%- set entity_count = 'sensor.ya_wamf_bird_count_24h' -%}

      {%- set seen_bird = states(entity_bird) -%}
      {%- set seen_time = states(entity_time) -%}
      {%- set seen_conf = state_attr(entity_bird, 'score') -%}

      {%- if seen_bird not in ['unknown', 'unavailable', 'None', 'none', ''] -%}
        {%- set daily_list = state_attr('sensor.birdnet_daily_summary', 'species_list') or [] -%}
        {%- set overall_list = state_attr('sensor.birdnet_species_summary', 'species_list') or [] -%}

        {%- set daily_match = daily_list | selectattr('common_name', 'match', '(?i)^' ~ seen_bird ~ '$') | list -%}
        {%- set overall_match = overall_list | selectattr('common_name', 'match', '(?i)^' ~ seen_bird ~ '$') | list -%}

        {%- set code = overall_match[0].get('species_code', '') if overall_match else '' -%}
        {%- set title = '[' ~ seen_bird ~ '](https://ebird.org/species/' ~ code ~ ')' if (code | length >= 1 and code | length <= 7) else seen_bird -%}

        {%- set conf_num = seen_conf | float(0) -%}
        {%- set conf_pct = (conf_num * 100) | round(0) if conf_num <= 1.0 else conf_num | round(0) -%}
        {%- set seen_dt = as_datetime(seen_time) -%}
        {%- set seen_str = relative_time(seen_dt) ~ ' ago' if seen_dt != none else seen_time -%}

        {%- if daily_match | count > 0 -%}
          {%- set b = daily_match[0] -%}
          {%- set heard_t = today_at(b.latest_heard) if ':' in (b.latest_heard | string) and 'T' not in (b.latest_heard | string) else as_datetime(b.latest_heard) -%}
          {%- set audio_line = '🔊 **Heard Today:** ' ~ b.count ~ ' times (last heard at ' ~ (heard_t | as_timestamp | timestamp_custom('%H:%M', true) if heard_t != none else b.latest_heard) ~ ')' -%}
        {%- elif overall_match | count > 0 -%}
          {%- set last_heard_dt = as_datetime(overall_match[0].last_heard) -%}
          {%- set audio_line = '🔇 **Silent Visitor Today:** Not heard today on BirdNET-Go (last heard ' ~ (relative_time(last_heard_dt) if last_heard_dt != none else overall_match[0].last_heard) ~ ' ago)' -%}
        {%- else -%}
          {%- set audio_line = '🔇 **Visual-Only Species:** Seen at the feeder, but *never* detected by BirdNET-Go' -%}
        {%- endif -%}
      ### {{ title }}{% if conf_num > 0 %} ({{ conf_pct }}%){% endif %}

      📸 **Seen at Feeder:** {{ seen_str }} ({{ states(entity_count) }} visits in 24h)<br>{{ audio_line }}
      {%- else -%}
      No recent feeder detections.
      {%- endif -%}

```

---

## 3. Card: Combined BirdNET-Go Daily Summary + YA-WAMF Feeder Badges & Silent Visitors

**What it does:** Upgrades your existing **Daily Species Summary With Sparklines** Markdown card by combining `sensor.birdnet_daily_summary` with `sensor.ya_wamf_daily_summary`:

* **Top Callout Banner:** At the very top of the card, it lists any species that were **🔇 Seen at Feeder, Not Heard Today** (with visit counts and last-seen times). If every feeder species today was also vocal on BirdNET-Go, it displays a `✅ All X feeder species seen today were also heard on BirdNET-Go.` confirmation banner instead.
* **Inline `📸` Badges:** In the main BirdNET-Go table, any species that also physically visited the feeder today gets a `📸` icon next to its name.


* **Dual-Sensor Footer:** At the bottom, it displays both total **Audio Detections** and total **Feeder Visits** for the day.

```yaml
type: markdown
content: >-
  {% if has_value('sensor.birdnet_daily_summary') %}
  {% set species_data = state_attr('sensor.birdnet_daily_summary', 'species_list') %}
  {%- set feeder_data = state_attr('sensor.ya_wamf_daily_summary', 'species_list') or [] -%}
  {%- set seen_names = feeder_data | map(attribute='common_name') | map('lower') | list -%}
  {% if species_data and species_data | count > 0 %}
  {%- set heard_names = species_data | map(attribute='common_name') | map('lower') | list -%}
  {%- set ns = namespace(silent=[]) -%}
  {%- for f_bird in feeder_data -%}
    {%- if (f_bird.common_name | lower) not in heard_names -%}
      {%- set ns.silent = ns.silent + [f_bird] -%}
    {%- endif -%}
  {%- endfor -%}
  {%- if ns.silent | count > 0 -%}
  **🔇 Seen at Feeder, Not Heard Today:**
  {% for b in ns.silent %}
  - {{ b.common_name }} ({{ b.count }} {{ 'visit' if b.count == 1 else 'visits' }}, last seen {{ as_datetime(b.latest_seen) | as_local | as_timestamp | timestamp_custom('%H:%M', true) if as_datetime(b.latest_seen) != none else b.latest_seen }})
  {% endfor %}
  ---
  {% elif feeder_data | count > 0 -%}
  ✅ **All {{ feeder_data | count }} feeder species seen today were also heard on BirdNET-Go.**

  ---
  {% endif -%}
  Last Heard | Species | Count | Sparkline (6AM-6PM)
  :-- | :-- | :-- | --
  {% for bird in species_data | sort(attribute='latest_heard', reverse=true) | sort(attribute='count', reverse=true) %}
  {#- Basic Info -#}
  {%- set time = bird.get('latest_heard', '00:00:00') -%}
  {%- set name = bird.get('common_name', 'Unknown') -%}
  {%- set count = bird.get('count', 0) -%}
  {%- set species_code = bird.get('species_code', '') -%}
  {%- set ebird_url = "https://ebird.org/species/" ~ species_code -%}
  {%- set badge = ' 📸' if (name | lower in seen_names) else '' -%}
  {#--- Sparkline Calculation (Full Day Aggregated - 14 slots) ---#}
  {%- set hourly = bird.hourly_counts -%}
  {%- set sparkline_str = "N/A" -%} {#- Default value -#}
  {%- if hourly is defined and hourly is iterable and hourly | count == 24 -%}
    {#- Aggregate counts: [0-6], 6..18, [18-24] (14 slots total, safe concatenation) -#}
    {%- set early_sum = hourly[0:6] | sum -%}
    {%- set middle_part = hourly[6:18] -%}
    {%- set late_sum = hourly[18:24] | sum -%}
    {%- set aggregated_counts = [early_sum] + middle_part + [late_sum] -%}

    {# Check if list has expected count before finding max #}
    {%- if aggregated_counts | count == 14 -%}
      {#- Find Max for Scaling -#}
      {%- set max_val = aggregated_counts | max -%}

      {#- Define Sparkline Characters (7 levels, U+2581 to U+2587) -#}
      {%- set spark_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇'] -%}
      {%- set sparkline = namespace(text="") -%}

      {%- for v in aggregated_counts -%}
        {#- Map value to character index (0-6), scale factor 7, max index 6 -#}
        {%- set char_index = ([0, (v * 7 / max_val)|int , 6] | sort)[1] if max_val > 0 else 0 -%}
        {#- Append character -#}
        {%- set sparkline.text = sparkline.text ~ spark_chars[char_index] -%}
      {%- endfor -%}
      {%- set sparkline_str = sparkline.text -%}
    {%- else -%}
      {%- set sparkline_str = "?" * 12 -%}
    {%- endif -%}
  {%- endif -%}
  {#--- End Sparkline Calculation ---#}

  {#- Output Row -#}
  {{ today_at(time) | as_timestamp | timestamp_custom('%H:%M', true) }} | {% if species_code | length >= 1 and species_code | length <= 7 %}[{{ name }}]({{ ebird_url }}){% else %}{{ name }}{% endif %}{{ badge }} | {{ count }} | {{ sparkline_str }}
  {% endfor %}

  ---
  {{ species_data | sum(attribute='count') | int }} Audio Detections ({{ species_data | count }} Species)
  {%- if feeder_data | count > 0 %}
  {{ feeder_data | sum(attribute='count') | int }} Feeder Visits ({{ feeder_data | count }} Species 📸)
  {%- endif %}
  {% else %}
  No bird species data available or list is empty.
  {% endif %}
  {% else %}
  BirdNET-Go API is not available.
  {% endif %}

```

---

## 4. Conditional "Stealth Visitor" Pop-Up Card

**What it does:** Hides a dedicated photo + alert card completely unless the most recent bird at the feeder visited within the last 60 minutes AND has **0 audio detections** on BirdNET-Go today.

Because Home Assistant's frontend `conditional` card only evaluates entity states (not Jinja2 templates) and always forces itself visible while in Dashboard Edit Mode, this uses a lightweight template `binary_sensor` to drive the visibility cleanly.

### Step 4A: `template.yaml` Binary Sensor

```yaml
# template.yaml
- binary_sensor:
    - name: "YA-WAMF Stealth Visitor Active"
      unique_id: ya_wamf_stealth_visitor_active
      icon: mdi:volume-off
      state: >-
        {% set seen_bird = states('sensor.ya_wamf_last_bird_detected') %}
        {% set seen_dt = as_datetime(states('sensor.ya_wamf_last_detection_time')) %}
        {% set daily_list = state_attr('sensor.birdnet_daily_summary', 'species_list') or [] %}
        {% if seen_bird not in ['unknown', 'unavailable', 'None', 'none', ''] and seen_dt != none %}
          {% set heard_today = daily_list | selectattr('common_name', 'match', '(?i)^' ~ seen_bird ~ '$') | list | count > 0 %}
          {{ (now() - seen_dt).total_seconds() < 3600 and not heard_today }}
        {% else %}
          false
        {% endif %}

```

### Step 4B: Dashboard `conditional` Card

*(Note: Exit Dashboard Edit Mode by clicking **Done** in the top right to see the card hide when `binary_sensor.ya_wamf_stealth_visitor_active` is `off`.)*

```yaml
type: conditional
conditions:
  - condition: state
    entity: binary_sensor.ya_wamf_stealth_visitor_active
    state: "on"
card:
  type: vertical-stack
  cards:
    - type: picture-entity
      entity: camera.ya_wamf_latest_bird_snapshot
      name: "🔇 Stealth Visitor (Seen, Not Heard Today)"
      show_state: false
      show_name: true
    - type: markdown
      content: >-
        {%- set seen_bird = states('sensor.ya_wamf_last_bird_detected') -%}
        {%- set seen_dt = as_datetime(states('sensor.ya_wamf_last_detection_time')) -%}
        {%- set daily_list = state_attr('sensor.birdnet_daily_summary', 'species_list') or [] -%}
        {%- set heard_today = daily_list | selectattr('common_name', 'match', '(?i)^' ~ seen_bird ~ '$') | list | count > 0 -%}
        {%- if not heard_today -%}
        🔇 **{{ seen_bird }}** was spotted at the feeder {{ relative_time(seen_dt) if seen_dt != none else '' }} ago, but has not been heard by BirdNET-Go today.
        {%- else -%}
        *(Edit Mode Preview: **{{ seen_bird }}** was heard today, so this card is hidden in normal view.)*
        {%- endif -%}

```