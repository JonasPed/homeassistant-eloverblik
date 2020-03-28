# eloverblik

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

The `eloverblik`component is a Home Assistant custom component for monitoring your electricity data from eloverblik.dk

*The custom component in it's very early stage for showing data from eloverblik.dk.*

## Installation
---
### Manual Installation
  1. Copy eloverblik folder into your custom_components folder in your hass configuration directory.
  2. Confiure the `eloverblik` sensor.
  3. Restart Home Assistant.

### Installation with HACS (Home Assistant Community Store)
  1. Ensure that [HACS](https://hacs.xyz/) is installed.
  2. Search for and install the `eloverblik` integration.
  3. Confiure the `eloverblik` sensor.
  4. Restart Home Assistant.


## Configuration
---
Fully configurable through config flow.
  1. Head to configuration --> integration
  2. Add new and search for eloverblik
  3. enter refresh token and metering point.

### Refresh token and metering point
Get refresh token and metering point from https://eloverblik.dk.
  1. Login at [eloverblik](https://eloverblik.dk).
  2. metering point is your `ID`
  3. refresh token can be created by clicking at you user and chose share data.

## State and attributes
---
A sensor for each over hour in the past 24 hours is created with the syntax:
 * sensor.eloverblik_energy_0_1
 * sensor.eloverblik_energy_1_2
 * etc.

A sensor which sum up the total energy usage is added as well:
 * sensor.eloverblik_energy_total

All sensors show their value in kWh.

## Disclaimer
Very early development and stuff might still explode etc.
