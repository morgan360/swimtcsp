import logging
from datetime import date
from django.utils import timezone
from lessons_bookings.models import Term
from schools_bookings.models import ScoTerm

# Configure logging to show messages in the console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

def get_current_term():
    today = timezone.now().date()
    current_term = Term.objects.filter(start_date__lte=today, end_date__gte=today).first()
    if current_term:
        logger.info(f"Found current term: {current_term}")
    else:
        logger.info("No current term found.")
    return current_term

def get_previous_term():
    current_term = get_current_term()
    if current_term:
        previous_term = Term.objects.filter(end_date__lt=current_term.start_date).order_by('-end_date').first()
        if previous_term:
            logger.info(f"Found previous term: {previous_term}")
        else:
            logger.info("No previous term found.")
        return previous_term
    return None

def get_next_term():
    current_term = get_current_term()
    if current_term:
        next_term = Term.objects.filter(start_date__gt=current_term.end_date).order_by('start_date').first()
        if next_term:
            logger.info(f"Found next term: {next_term}")
        else:
            logger.info("No next term found.")
        return next_term
    return None

def get_current_sco_term():
    today = timezone.now().date()
    current_sco_term = ScoTerm.objects.filter(start_date__lte=today, end_date__gte=today).first()
    if current_sco_term:
        logger.info(f"Found current sco term: {current_sco_term}")
    else:
        logger.info("No current sco term found.")
    return current_sco_term
