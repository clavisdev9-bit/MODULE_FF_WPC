import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # The partner extension may already be present in the registry while an
    # older database has not created its physical columns yet.
    cr.execute(
        "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS street3 VARCHAR"
    )
    cr.execute(
        "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS street4 VARCHAR"
    )

    """FF-71: freight.air.quotation berhenti jadi model/tabel terpisah dan
    digabung langsung ke sale.order (pola yang sama dengan Sea, lihat commit
    migrasi Sea sebelumnya di freight.sea.quotation.migration.wizard).

    Model freight.air.quotation tidak pernah dibuat lewat kode manapun
    (dispatcher action_convert_to_booking_direct/action_convert_to_jobsheet_direct
    dan UI Air Quotation selalu bekerja lewat sale.order langsung), sehingga
    tabelnya seharusnya kosong di semua environment produksi. UPDATE di
    bawah ini murni safety-net kalau ternyata ada baris legacy.

    HARUS post-migrate, bukan pre-migrate: kolom air-specific (mis.
    transportation_method, air_shipping_line_id) baru dibuat di tabel
    sale_order oleh _auto_init setelah pre-migrate berjalan, jadi UPDATE
    ke kolom-kolom itu hanya valid dijalankan setelah module fully loaded.

    Catatan risiko: join `so.id = faq.id` mengasumsikan baris freight_air_quotation
    sudah pernah disinkronkan ke sale_order dengan id yang sama (lihat
    _sync_sale_order_rows di models/common/quotation.py, yang memang insert
    dengan id sumbernya). Kalau ternyata ada baris yang TIDAK pernah disync,
    id-nya bisa kebetulan cocok dengan sale_order lain yang tidak berhubungan.
    Sebagai pengaman, UPDATE dibatasi hanya ke baris sale_order yang belum
    berstatus is_freight_quotation, supaya tidak menimpa quotation asli.
    """
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'freight_air_quotation'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute("SELECT count(*) FROM freight_air_quotation")
    row_count = cr.fetchone()[0]
    if row_count:
        _logger.warning(
            "FF-71 migration: found %s row(s) in legacy freight_air_quotation "
            "table (expected 0). Migrating them into sale_order, restricted "
            "to rows not already flagged is_freight_quotation.",
            row_count,
        )

    cr.execute(
        """
        UPDATE sale_order so
        SET freight_business_type = 'air',
            freight_type = faq.freight_type,
            is_freight_quotation = faq.is_freight_quotation,
            quotation_title = faq.quotation_title,
            salesman_id = faq.salesman_id,
            partner_id = faq.partner_id,
            service_level = faq.service_level,
            delivery_type_id = faq.delivery_type_id,
            valid_from = faq.valid_from,
            reference_number = faq.reference_number,
            commodity_id = faq.commodity_id,
            pickup_street = faq.pickup_street,
            pickup_street2 = faq.pickup_street2,
            pickup_city = faq.pickup_city,
            pickup_state_id = faq.pickup_state_id,
            pickup_zip = faq.pickup_zip,
            pickup_country_id = faq.pickup_country_id,
            delivery_street = faq.delivery_street,
            delivery_street2 = faq.delivery_street2,
            delivery_city = faq.delivery_city,
            delivery_state_id = faq.delivery_state_id,
            delivery_zip = faq.delivery_zip,
            delivery_country_id = faq.delivery_country_id,
            description_of_goods = faq.description_of_goods,
            quantity = faq.quantity,
            actual_weight = faq.actual_weight,
            volume = faq.volume,
            chargeable_weight = faq.chargeable_weight,
            has_insurance = faq.has_insurance,
            insurance_id = faq.insurance_id,
            loose_quantity = faq.loose_quantity,
            pcs = faq.pcs,
            uom_id = faq.uom_id,
            length = faq.length,
            width = faq.width,
            height = faq.height,
            dimension = faq.dimension,
            origin_id = faq.origin_id,
            est_transit_time_days = faq.est_transit_time_days,
            est_transit_time_note = faq.est_transit_time_note,
            frequency = faq.frequency,
            frt_collect = faq.frt_collect,
            note = faq.note,
            header = faq.header,
            special_instruction = faq.special_instruction,
            footer = faq.footer,
            terms_and_conditions = faq.terms_and_conditions,
            container_type = faq.container_type,
            transportation_method = faq.transportation_method,
            expiry_date = faq.expiry_date,
            source_street = faq.source_street,
            source_street2 = faq.source_street2,
            source_city = faq.source_city,
            source_state_id = faq.source_state_id,
            source_zip = faq.source_zip,
            source_country_id = faq.source_country_id,
            destination_street = faq.destination_street,
            destination_street2 = faq.destination_street2,
            destination_city = faq.destination_city,
            destination_state_id = faq.destination_state_id,
            destination_zip = faq.destination_zip,
            destination_country_id = faq.destination_country_id,
            fumigation = faq.fumigation,
            air_shipping_line_id = faq.shipping_line_id
        FROM freight_air_quotation faq
        WHERE so.id = faq.id
          AND (so.is_freight_quotation IS NOT TRUE)
        """
    )

    cr.execute(
        """
        DROP TABLE IF EXISTS
            freight_air_quotation_transaction_rel,
            freight_air_quotation_tag_rel,
            freight_air_quotation
        CASCADE
        """
    )
