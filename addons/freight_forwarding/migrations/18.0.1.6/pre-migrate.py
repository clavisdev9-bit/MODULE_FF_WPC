def migrate(cr, version):
    cr.execute(
        """
        DROP TABLE IF EXISTS
            freight_sea_charge_table,
            freight_sea_charge_table_line,
            freight_sea_cost_table,
            freight_sea_cost_table_line,
            freight_terms_conditions
        CASCADE
        """
    )
