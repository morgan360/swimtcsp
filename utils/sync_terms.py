import pymysql
import logging
from django.conf import settings
from lessons_bookings.models import Term

logger = logging.getLogger(__name__)

def clean_date(value):
    if value in ("0000-00-00", None):
        return None
    return value

def sync_terms_from_remote():
    try:
        db = settings.REMOTE_TCSP_DB
        connection = pymysql.connect(
            host=db['HOST'],
            port=db['PORT'],
            user=db['USER'],
            password=db['PASSWORD'],
            database=db['NAME'],
            charset=db['CHARSET'],
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        logger.error(f"[TCSP] Could not connect to remote DB: {e}")
        return

    try:
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    term_id, 
                    start_date, 
                    finish_date, 
                    COALESCE(rebook_start, '0000-00-00') AS rebooking_date,
                    COALESCE(booking_switch_date, '0000-00-00') AS booking_date,
                    COALESCE(assesments_complete, '0000-00-00') AS assessment_date
                FROM mor_terms
                WHERE term_id != 0
            """
            cursor.execute(query)
            terms = cursor.fetchall()

        logger.info(f"[TCSP] Retrieved {len(terms)} term(s) from remote.")

        updated = 0
        for row in terms:
            term_id = row["term_id"]
            term, created = Term.objects.update_or_create(
                id=term_id,
                defaults={
                    "start_date": clean_date(row["start_date"]),
                    "end_date": clean_date(row["finish_date"]),
                    "rebooking_date": clean_date(row["rebooking_date"]),
                    "booking_date": clean_date(row["booking_date"]),
                    "assessment_date": clean_date(row["assessment_date"]),
                }
            )
            updated += 1

        logger.info(f"[TCSP] {updated} term(s) synced successfully.")

    except Exception as e:
        logger.error(f"[TCSP] Error syncing terms: {e}")

    finally:
        connection.close()
