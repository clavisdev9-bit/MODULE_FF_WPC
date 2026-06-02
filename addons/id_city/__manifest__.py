{
    "name": "Indonesia Regional Localization",
    "summary": "Complete Indonesian regional data: Province, City/Regency, District (Kecamatan), Village (Kelurahan) with ZIP codes",
    "description": """
Indonesia Regional Localization
===============================

This module provides complete Indonesian regional/administrative data hierarchy:

* **Provinsi (Province)** - 38 provinces
* **Kabupaten/Kota (City/Regency)** - 514 cities/regencies  
* **Kecamatan (District)** - 7,266 districts
* **Desa/Kelurahan (Village)** - 83,931 villages with ZIP codes

Features
--------
* Auto-fill ZIP code when selecting village
* Cascading dropdowns (Province > City > District > Village)
* Easy to configure in Partner/Contact form
* Menu in Contacts > Configuration > Localization

Data Source
-----------
Based on official Indonesian government administrative data (Kemendagri).
    """,
    "author": "Steven Marp",
    "website": "https://apps.odoo.com/apps/browse?repo_maintainer_id=512936",
    "category": "Regional",
    "version": "18.0.1.0.0",
    "depends": [
        "base",
        "contacts",
        'base_address_extended',
    ],
    "data": [
        "security/ir.model.access.csv",
        # "data/res.country.state.csv",
        "data/res.city.csv",
        # "data/res.subdistrict.csv",
        # "data/res.village.csv",
        # "views/res_partner_views.xml",
        # "views/res_country_state_views.xml",
        "views/res_city_views.xml",
        # "views/res_subdistrict_views.xml",
        # "views/res_village_views.xml",
    ],
    "demo": [],
    "images": [
        "static/description/images/banner.gif",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
