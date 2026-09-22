import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SeaQuotationMigrationWizard(models.TransientModel):
    _name = "freight.sea.quotation.migration.wizard"
    _description = "Migration Wizard for Sea Quotation"

    def action_migrate(self):
        # FF-80: legacy freight_sea_quotation.salesman_id menyimpan
        # hr.employee.id (sama seperti Sea Booking/Job lama) -- BUKAN
        # res.users langsung. Resolve lewat employee.user_id, tulis ke
        # native sale_order.user_id (canonical Salesperson, FF-80), BUKAN
        # ke kolom sale_order.salesman_id lama yang sudah dead/orphan
        # (field Python-nya sudah dihapus, tapi fisiknya belum tentu
        # di-drop -- jangan ditulis/dibaca lagi lewat jalur mana pun).
        # Kalau employee tidak punya linked user, JANGAN menebak --
        # so.user_id dibiarkan apa adanya (COALESCE ke nilai existing,
        # yang biasanya sudah terisi default current user dari create()).
        self.env.cr.execute("""
            SELECT fsq.id, fsq.salesman_id
            FROM freight_sea_quotation fsq
            LEFT JOIN hr_employee he ON he.id = fsq.salesman_id
            WHERE fsq.salesman_id IS NOT NULL AND he.user_id IS NULL
        """)
        unresolved = self.env.cr.fetchall()
        if unresolved:
            _logger.warning(
                "FF-80 Sea Quotation migration wizard: %s row(s) in legacy "
                "freight_sea_quotation have salesman_id pointing to an "
                "hr.employee WITHOUT a linked user -- sale_order.user_id "
                "left untouched (not guessed) for: %s",
                len(unresolved), unresolved,
            )

        # Migrasi data untuk Sea Quotation (fokus ke Sea)
        self.env.cr.execute("""
            UPDATE sale_order so
            SET freight_business_type = 'sea',
                freight_type = fsq.freight_type,
                quotation_title = fsq.quotation_title,
                user_id = COALESCE(he.user_id, so.user_id),
                partner_id = fsq.partner_id,
                service_level = fsq.service_level,
                delivery_type_id = fsq.delivery_type_id,
                valid_from = fsq.effective_date,
                reference_number = fsq.reference_number,
                commodity_id = fsq.commodity_id,
                pickup_street = fsq.pickup_street,
                pickup_street2 = fsq.pickup_street2,
                pickup_city = fsq.pickup_city,
                pickup_state_id = fsq.pickup_state_id,
                pickup_zip = fsq.pickup_zip,
                pickup_country_id = fsq.pickup_country_id,
                delivery_street = fsq.delivery_street,
                delivery_street2 = fsq.delivery_street2,
                delivery_city = fsq.delivery_city,
                delivery_state_id = fsq.delivery_state_id,
                delivery_zip = fsq.delivery_zip,
                delivery_country_id = fsq.delivery_country_id,
                description_of_goods = fsq.description_of_goods,
                quantity = fsq.quantity,
                actual_weight = fsq.actual_weight,
                volume = fsq.volume,
                chargeable_weight = fsq.chargeable_weight,
                has_insurance = fsq.has_insurance,
                insurance_id = fsq.insurance_id,
                loose_quantity = fsq.loose_quantity,
                pcs = fsq.pcs,
                uom_id = fsq.uom_id,
                length = fsq.length,
                width = fsq.width,
                height = fsq.height,
                dimension = fsq.dimension,
                origin_id = fsq.origin_id,
                destination_id = fsq.destination_id,
                est_transit_time_days = fsq.est_transit_time_days,
                est_transit_time_note = fsq.est_transit_time_note,
                frequency = fsq.frequency,
                frt_collect = fsq.frt_collect,
                note = fsq.note,
                header = fsq.header,
                special_instruction = fsq.special_instruction,
                footer = fsq.footer,
                original_quotation_id = fsq.original_quotation_id,
                port_of_loading_id = fsq.port_of_loading_id,
                port_of_discharge_id = fsq.port_of_discharge_id,
                via_port_id = fsq.via_port_id,
                shipping_line_id = fsq.shipping_line_id,
                via2_id = fsq.via2_id,
                via3_id = fsq.via3_id
            FROM freight_sea_quotation fsq
            LEFT JOIN hr_employee he ON he.id = fsq.salesman_id
            WHERE so.id = fsq.id;
        """)

        # Drop the table
        self.env.cr.execute("DROP TABLE IF EXISTS freight_sea_quotation CASCADE;")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Migration Complete',
                'message': 'Data migration for Sea Quotation is completed successfully.',
                'sticky': False,
                'type': 'success',
            }
        }
