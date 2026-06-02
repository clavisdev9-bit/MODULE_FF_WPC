================================
Indonesia Regional Localization
================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Production-green.png
    :target: https://odoo-community.org/page/development-status
    :alt: Production
.. |badge2| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :target: https://www.gnu.org/licenses/lgpl-3.0.html
    :alt: License: LGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-stevenmarp-lightgray.png?logo=github
    :target: https://github.com/stevenmarp/indonesia_regional_localization
    :alt: stevenmarp/indonesia_regional_localization

|badge1| |badge2| |badge3|

This module provides complete Indonesian regional/administrative data hierarchy for Odoo 18.

**Table of contents**

.. contents::
   :local:

Features
========

Complete Indonesian Administrative Data:

* **Provinsi (Province)** - 38 provinces
* **Kabupaten/Kota (City/Regency)** - 514 cities/regencies
* **Kecamatan (District)** - 7,266 districts
* **Desa/Kelurahan (Village)** - 83,931 villages with ZIP codes

Functionality:

* Auto-fill ZIP code when selecting village
* Cascading dropdowns (Province > City > District > Village)
* Integrated with Partner/Contact form
* Easy configuration menu in Contacts > Configuration > Localization

Installation
============

1. Download the module from GitHub or Odoo Apps
2. Place the module in your Odoo addons directory
3. Update the Apps list in Odoo
4. Install "Indonesia Regional Localization" module

Configuration
=============

After installation:

1. Go to **Contacts > Configuration > Localization**
2. You will find menus for:
   
   - States (Provinces)
   - Cities (Kabupaten/Kota)
   - Subdistricts (Kecamatan)
   - Villages (Desa/Kelurahan)

3. Regional data is automatically loaded during installation

Usage
=====

1. Open any Contact/Partner form
2. In the address section, you will see new fields:
   
   - Kabupaten/Kota (City/Regency)
   - Kecamatan (District)
   - Desa/Kelurahan (Village)

3. Select Province first, then City, District, and Village
4. ZIP code will be automatically filled when you select a Village

Data Source
===========

Based on official Indonesian government administrative data from:

* Kementerian Dalam Negeri (Kemendagri)
* Badan Pusat Statistik (BPS)

===========


Credits
=======

Authors
-------

* Steven Marp

Maintainers
-----------

This module is maintained by Steven Marp.

.. image:: https://img.shields.io/badge/maintainer-stevenmarp-blue.png
   :alt: maintainer

Current maintainer:



