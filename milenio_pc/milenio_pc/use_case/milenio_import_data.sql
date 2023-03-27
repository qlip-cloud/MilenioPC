DROP PROCEDURE IF EXISTS milenio_import_data;
delimiter //
CREATE PROCEDURE milenio_import_data()
BEGIN

    DECLARE temporal_total_lines int;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SHOW ERRORS;
        ROLLBACK;
    END;
    START TRANSACTION;

    -- Número de registros a procesar
    SELECT count(*)
    INTO temporal_total_lines
    FROM `tabMilenio_Temporal_Data_File` mtdf;

    -- Validaciones Temporal Data File en base al proceso que lanza la carga
    SELECT count(*)
    FROM `tabMilenio_Temporal_Data_File` mrdf,
         `tabMilenio_File_Upload` mfu
    WHERE mfu.status = 'Active'
    AND mrdf.company = mfu.company

    SELECT temporal_total_lines AS total_lines_processed;
    SELECT 0 AS result;

    COMMIT;

END //
delimiter ;

call milenio_import_data();