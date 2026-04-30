from odoo import fields, models


class SeaBookingPickupInfo(models.Model):
    _name = "freight.sea.booking.pickup.info"
    _description = "Sea Booking Pickup Info"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )
    
    # Route Charges
    type = fields.Selection(
        [
            ("get_up", "Get Up"),
            ("by_car", "By Car"),
            ("prior_transport", "Prior Transport"),
            ("delivery", "Delivery"),
        ],
        string="Type",
        required=True,
    )
    pickup = fields.Boolean(string="Pickup From Warehouse")
    receive_from_id = fields.Many2one(
        "res.partner",
        string="Receive From",
        domain="[('is_company', '=', True)]",
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse", 
        string="Warehouse"
    )
    type_of_load = fields.Selection(
        [
            ("free", "Free"),
            ("paid", "Paid"),
        ],
        string="Type of Load",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
    )
    position = fields.Float(string="Position")

    address = fields.Selection(
        [
            ("contact", "Contact Address"),
            ("site", "Site Address"),
        ],
        string="Address",
    )
    
    estimate_pickup = fields.Datetime(string="Estimate Pickup")
    estimate_arrival = fields.Datetime(string="Estimate Arrival")
    
    # Location Details
    loading_port = fields.Many2one(
        "freight.port",
        string="Loading Port",
    )
    discharge_port = fields.Many2one(
        "freight.port",
        string="Discharge Port",
    )
    
    # Address
    source_street = fields.Char(string="Street")
    source_street2 = fields.Char(string="Street 2")
    source_city = fields.Char(string="City")
    source_state_id = fields.Many2one(
        "res.country.state",
        string="State",
    )
    source_zip = fields.Char(string="Zip")
    source_country_id = fields.Many2one(
        "res.country",
        string="Country",
    )
    
    destination_street = fields.Char(string="Street")
    destination_street2 = fields.Char(string="Street 2")
    destination_city = fields.Char(string="City")
    destination_state_id = fields.Many2one(
        "res.country.state",
        string="State",
    )
    destination_zip = fields.Char(string="Zip")
    destination_country_id = fields.Many2one(
        "res.country",
        string="Country",
    )
    
    # Ship/Vehicle Details
    bouquet_id = fields.Many2one(
        "freight.vessel",
        string="Bouquet",
    )
    obl_no = fields.Char(string="OBL No.")
    trip_no = fields.Char(string="Trip No.")