import logging
from django.db import transaction

logger = logging.getLogger(__name__)


@transaction.atomic
def cleanup_candidate_data(candidate):
    logger.info(f"Starting data cleanup for candidate {candidate.id}")

    try:
        user = candidate.user

        assessments = candidate.assessments.all()

        for assessment in assessments:
            assessment.code_submission = "[REDACTED - Data removed per privacy policy]"
            assessment.evaluation_results = None
            assessment.feedback = "[REDACTED - Data removed per privacy policy]"
            assessment.save()

            logger.info(f"Assessment {assessment.id} data redacted")

        user.is_active = False
        user.save()

        logger.info(f"User {user.id} and candidate {candidate.id} data anonymized")

        return True, "Candidate data has been anonymized successfully."

    except Exception as e:
        logger.error(f"Error during candidate data cleanup: {str(e)}")
        return False, f"Error during data cleanup: {str(e)}"