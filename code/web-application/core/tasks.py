from celery import shared_task
import logging

from .models import Assessment
from .evaluation import evaluate_submission

logger = logging.getLogger(__name__)


@shared_task
def evaluate_assessment(assessment_id: int):
    try:
        assessment = Assessment.objects.get(id=assessment_id)

        if assessment.status != 'FINISHED' or not assessment.code_submission:
            logger.warning(f"Assessment {assessment_id} is not ready for evaluation")
            return {
                'status': 'error',
                'message': 'Assessment is not ready for evaluation'
            }

        logger.info(f"Starting evaluation for assessment {assessment_id}")

        assessment.status = 'SCORING'
        assessment.save()

        results = evaluate_submission(assessment)

        if results.get('status') == 'success':
            assessment.status = 'SCORED'
        else:
            assessment.status = 'FINISHED'
            logger.error(f"Evaluation failed for assessment {assessment_id}: {results.get('message')}")

        assessment.save()

        logger.info(f"Evaluation completed for assessment {assessment_id} with score: {assessment.score}")

        return {
            'status': 'success',
            'assessment_id': assessment_id,
            'score': assessment.score
        }

    except Assessment.DoesNotExist:
        logger.error(f"Assessment {assessment_id} not found")
        return {
            'status': 'error',
            'message': f'Assessment {assessment_id} not found'
        }
    except Exception as e:
        logger.exception(f"Error evaluating assessment {assessment_id}")
        return {
            'status': 'error',
            'message': str(e)
        }