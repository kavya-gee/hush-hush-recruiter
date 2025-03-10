import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .evaluation import evaluate_submission, logger
from .forms import AddCandidateForm, CandidateForm, UserForm
from .models import Assessment, Candidate
from .models import HiringManager, CodingQuestion
from .tasks import evaluate_assessment
from .utils.email_utils import generate_random_password, send_candidate_credentials_email
from .utils.email_utils import send_interview_invitation_email, send_rejection_email
from .utils.gdpr_utils import cleanup_candidate_data


def home(request):
    context = {
        'current_time': timezone.now(),
    }
    return render(request, 'core/home.html', context)


def candidate_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_candidate:
            login(request, user)
            return redirect('core:candidate_dashboard')
        else:
            messages.error(request, 'Invalid credentials or you are not registered as a candidate.')

    return render(request, 'core/candidate_login.html')


def manager_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_hiring_manager:
            login(request, user)
            return redirect('core:manager_dashboard')
        else:
            messages.error(request, 'Invalid credentials or you are not registered as a hiring manager.')

    return render(request, 'core/manager_login.html')


@login_required
def candidate_dashboard(request):
    if not request.user.is_candidate:
        return HttpResponseForbidden("Access Denied: You must be a candidate to view this page.")

    return render(request, 'core/candidate_dashboard.html')


@login_required
def manager_dashboard(request):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access Denied: You must be a hiring manager to view this page.")

    hiring_manager = request.user.hiring_manager_profile
    candidates = Candidate.objects.all().select_related('user')
    assessments = Assessment.objects.filter(created_by=hiring_manager).select_related('candidate__user')

    candidate_assessments = {}
    for assessment in assessments:
        candidate_id = assessment.candidate.id
        if candidate_id not in candidate_assessments or assessment.created_at > candidate_assessments[
            candidate_id].created_at:
            candidate_assessments[candidate_id] = assessment

    for candidate in candidates:
        if candidate.id in candidate_assessments:
            candidate.latest_assessment = candidate_assessments[candidate.id]

            status = candidate.latest_assessment.status
            evaluation_status = candidate.latest_assessment.evaluation_status

            if status == 'SENT':
                candidate.status_display = 'Invitation Sent'
                candidate.status_color = 'blue'
            elif status == 'ACCEPTED':
                candidate.status_display = 'Invitation Accepted'
                candidate.status_color = 'green'
            elif status == 'STARTED':
                candidate.status_display = 'Assessment In Progress'
                candidate.status_color = 'orange'
            elif status == 'FINISHED':
                if evaluation_status == 'EVALUATING':
                    candidate.status_display = 'Evaluation In Progress'
                    candidate.status_color = 'purple'
                elif evaluation_status == 'PENDING':
                    candidate.status_display = 'Awaiting Evaluation'
                    candidate.status_color = 'yellow'
                elif evaluation_status == 'FAILED':
                    candidate.status_display = 'Evaluation Failed'
                    candidate.status_color = 'red'
                else:
                    candidate.status_display = 'Completed'
                    candidate.status_color = 'gray'
            elif status == 'SCORING':
                candidate.status_display = 'Scoring In Progress'
                candidate.status_color = 'purple'
            elif status == 'SCORED':
                candidate.status_display = 'Evaluated'
                candidate.status_color = 'green'
            else:
                candidate.status_display = status
                candidate.status_color = 'gray'
        else:
            candidate.latest_assessment = None

    total_candidates = candidates.count()
    invited_candidates = sum(1 for c in candidates if c.latest_assessment and c.latest_assessment.status == 'SENT')
    in_progress_assessments = sum(
        1 for c in candidates if c.latest_assessment and c.latest_assessment.status in ['ACCEPTED', 'STARTED'])
    completed_assessments = sum(1 for c in candidates if
                                c.latest_assessment and c.latest_assessment.status in ['FINISHED', 'SCORING', 'SCORED'])
    scored_assessments = sum(1 for c in candidates if c.latest_assessment and c.latest_assessment.status == 'SCORED')

    accepted_for_interview = sum(1 for c in candidates if c.interview_status == 'ACCEPTED')
    rejected_candidates = sum(1 for c in candidates if c.interview_status == 'REJECTED')

    companies = HiringManager.objects.values('company_name').distinct()
    company_names = [company['company_name'] for company in companies]

    source_choices = dict(Candidate.SOURCE_CHOICES)
    sources = [{'code': code, 'name': name} for code, name in source_choices.items()]

    status_filter = request.GET.get('status', '')
    interview_filter = request.GET.get('interview_status', '')
    source_filter = request.GET.get('source', '')

    if status_filter:
        if status_filter == 'INVITED':
            candidates = [c for c in candidates if c.latest_assessment and c.latest_assessment.status == 'SENT']
        elif status_filter == 'IN_PROGRESS':
            candidates = [c for c in candidates if
                          c.latest_assessment and c.latest_assessment.status in ['ACCEPTED', 'STARTED']]
        elif status_filter == 'COMPLETED':
            candidates = [c for c in candidates if
                          c.latest_assessment and c.latest_assessment.status in ['FINISHED', 'SCORING', 'SCORED']]
        elif status_filter == 'SCORED':
            candidates = [c for c in candidates if c.latest_assessment and c.latest_assessment.status == 'SCORED']
        elif status_filter == 'NO_ASSESSMENT':
            candidates = [c for c in candidates if not c.latest_assessment]

    if interview_filter:
        candidates = [c for c in candidates if c.interview_status == interview_filter]

    if source_filter:
        candidates = [c for c in candidates if c.source == source_filter]

    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'name':
        candidates = sorted(candidates, key=lambda c: c.user.full_name or c.user.username)
    elif sort_by == 'status':
        candidates = sorted(candidates, key=lambda c: c.latest_assessment.status if c.latest_assessment else 'ZZZZ')
    elif sort_by == 'score':
        candidates = sorted(candidates, key=lambda
            c: c.latest_assessment.score if c.latest_assessment and c.latest_assessment.score else -1, reverse=True)
    elif sort_by == 'interview':
        candidates = sorted(candidates, key=lambda c: c.interview_status)
    elif sort_by == 'date':
        candidates = sorted(candidates, key=lambda
            c: c.latest_assessment.created_at if c.latest_assessment else timezone.make_aware(datetime.min))
    elif sort_by == 'source':
        candidates = sorted(candidates, key=lambda c: c.source)

    context = {
        'candidates': candidates,
        'total_candidates': total_candidates,
        'invited_candidates': invited_candidates,
        'in_progress_assessments': in_progress_assessments,
        'completed_assessments': completed_assessments,
        'scored_assessments': scored_assessments,
        'accepted_for_interview': accepted_for_interview,
        'rejected_candidates': rejected_candidates,
        'companies': company_names,
        'current_sort': sort_by,
        'current_filter': status_filter,
        'current_interview_filter': interview_filter,
        'current_source_filter': source_filter,
        'sources': sources,
        'current_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'current_user': request.user.username,
    }

    return render(request, 'core/manager_dashboard.html', context)


@login_required
def invite_assessment(request, candidate_id):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access Denied: You must be a hiring manager to perform this action.")

    try:
        candidate = Candidate.objects.get(id=candidate_id)
        hiring_manager = request.user.hiring_manager_profile

        new_password = None
        if candidate.generated_password == "default":
            new_password = generate_random_password()

            user = candidate.user
            user.set_password(new_password)
            user.save()

            candidate.generated_password = new_password
            candidate.save()

        existing_assessment = Assessment.objects.filter(
            candidate=candidate,
            status__in=['DRAFT', 'SENT', 'ACCEPTED', 'STARTED']
        ).first()

        if existing_assessment:
            messages.warning(
                request,
                f"Assessment already exists for {candidate.user.username} with status: {existing_assessment.get_status_display()}"
            )
            return redirect('core:manager_dashboard')

        assessment = Assessment.objects.create(
            candidate=candidate,
            created_by=hiring_manager,
            title=f"Coding Assessment for {candidate.user.full_name or candidate.user.username}",
            description="Please complete this coding assessment to proceed with your application.",
            status='SENT',
            sent_at=timezone.now(),
            question_frontend="Create a responsive form with validation using React.js...",
            question_backend="Build a RESTful API with authentication using Django...",
            question_database="Design a database schema for a social media platform..."
        )

        if new_password:
            send_candidate_credentials_email(
                candidate_username=candidate.user.username,
                candidate_email=candidate.user.email,
                candidate_password=new_password,
                candidate_name=candidate.user.full_name or candidate.user.username,
            )
            messages.success(request, f"New login credentials sent to {candidate.user.username}")

        from core.utils.email_utils import send_assessment_invitation_email
        send_assessment_invitation_email(assessment)

        messages.success(request, f"Assessment invitation sent to {candidate.user.username}")
    except Candidate.DoesNotExist:
        messages.error(request, "Candidate not found.")
    except Exception as e:
        messages.error(request, f"Error sending invitation: {str(e)}")

    return redirect('core:manager_dashboard')

@login_required
def add_candidate(request):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access Denied: You must be a hiring manager to view this page.")

    if request.method == 'POST':
        form = AddCandidateForm(request.POST)
        if form.is_valid():
            new_user = get_user_model()
            password = generate_random_password()

            send_candidate_credentials_email(
                candidate_username=form.cleaned_data['username'],
                candidate_email=form.cleaned_data['email'],
                candidate_password=password,
                candidate_name=form.cleaned_data['full_name'],
            )

            messages.success(
                request,
                f"Candidate {form.cleaned_data['username']} was created successfully and sent login credentials."
            )
            return redirect('core:manager_dashboard')
    else:
        form = AddCandidateForm()

    return render(request, 'core/add_candidate.html', {'form': form})


def accept_assessment_invite(request, assessment_id):
    try:
        assessment = Assessment.objects.get(id=assessment_id)

        if assessment.status != 'SENT':
            if assessment.status == 'ACCEPTED':
                messages.info(request, "You have already accepted this assessment.")
                return redirect('core:candidate_dashboard')
            elif assessment.status == 'STARTED':
                messages.info(request, "This assessment has already been started.")
                return redirect('core:candidate_dashboard')
            else:
                messages.error(request,
                               f"This assessment cannot be accepted (status: {assessment.get_status_display()}).")
                return redirect('core:candidate_dashboard')

        if assessment.is_invite_expired():
            messages.error(request, "This assessment invitation has expired.")
            return redirect('core:candidate_dashboard')

        assessment.status = 'ACCEPTED'
        assessment.accepted_at = timezone.now()
        assessment.save()

        from core.utils.email_utils import send_assessment_acceptance_email
        send_assessment_acceptance_email(assessment)

        if request.user.is_authenticated and request.user.is_candidate:
            messages.success(request, "Assessment accepted. You can now start it from your dashboard.")
            return redirect('core:candidate_dashboard')
        else:
            messages.success(request, "Assessment accepted. Please log in to begin.")
            return redirect('core:candidate_login')

    except Assessment.DoesNotExist:
        return HttpResponseNotFound("Assessment not found")


@login_required
def candidate_dashboard(request):
    if not request.user.is_candidate:
        return HttpResponseForbidden("Access Denied: You must be a candidate to view this page.")

    candidate = request.user.candidate_profile

    current_user = request.user.full_name
    assessments = Assessment.objects.filter(candidate=candidate).order_by('-created_at')

    for assessment in assessments:
        if assessment.status == 'STARTED':
            assessment.remaining_time = assessment.time_remaining()
            assessment.progress = assessment.progress_percentage()

    context = {
        'assessments': assessments,
        'current_date': timezone.now(),
        'current_user': current_user,
    }

    return render(request, 'core/candidate_dashboard.html', context)


@login_required
def start_assessment(request, token):
    if not request.user.is_candidate:
        return HttpResponseForbidden("Access Denied: You must be a candidate to view this page.")

    try:
        assessment = Assessment.objects.get(
            assessment_url_token=token,
            candidate=request.user.candidate_profile
        )

        if assessment.status not in ['ACCEPTED', 'STARTED']:
            if assessment.status == 'FINISHED':
                messages.info(request, "You have already completed this assessment.")
                return redirect('core:candidate_dashboard')
            else:
                messages.error(request,
                               f"This assessment cannot be started (status: {assessment.get_status_display()}).")
                return redirect('core:candidate_dashboard')

        if assessment.is_invite_expired():
            messages.error(request, "This assessment invitation has expired.")
            return redirect('core:candidate_dashboard')

        if assessment.status == 'ACCEPTED':
            assessment.status = 'STARTED'
            assessment.start_time = timezone.now()
            assessment.end_time = assessment.start_time + timezone.timedelta(hours=24)
            assessment.save()

            return render(request, 'core/assessment_instructions.html', {'assessment': assessment})

        if assessment.is_time_up():
            messages.error(request, "Time is up. You can no longer work on this assessment.")
            assessment.status = 'FINISHED'
            assessment.save()
            return redirect('core:candidate_dashboard')

        remaining_time = assessment.time_remaining()

        if assessment.chosen_question_type == 'FRONTEND':
            question = assessment.question_frontend
        elif assessment.chosen_question_type == 'BACKEND':
            question = assessment.question_backend
        elif assessment.chosen_question_type == 'DATABASE':
            question = assessment.question_database
        else:
            return render(request, 'core/assessment_question_selection.html', {'assessment': assessment})

        return render(request, 'core/assessment_workspace.html', {
            'assessment': assessment,
            'question': question,
            'remaining_time': remaining_time
        })

    except Assessment.DoesNotExist:
        return HttpResponseNotFound("Assessment not found or not assigned to you.")


@login_required
def choose_assessment_question(request, token):
    if not request.user.is_candidate:
        return HttpResponseForbidden("Access Denied: You must be a candidate to view this page.")

    try:
        assessment = Assessment.objects.get(
            assessment_url_token=token,
            candidate=request.user.candidate_profile,
            status='STARTED'
        )

        if assessment.chosen_question:
            return redirect('core:view_assessment', token=token)

        if request.method == 'POST':
            question_id = request.POST.get('question_id')

            try:
                question = CodingQuestion.objects.get(id=question_id)

                if assessment.available_questions.filter(
                        id=question_id).exists() or not assessment.available_questions.exists():
                    assessment.chosen_question = question
                    assessment.chosen_question_type = question.question_type

                    if question.question_type == 'FRONTEND':
                        assessment.code_language = 'javascript'
                    elif question.question_type == 'BACKEND':
                        assessment.code_language = 'python'
                    elif question.question_type == 'DATABASE':
                        assessment.code_language = 'sql'

                    assessment.save()

                    messages.success(request, f"You've selected the question: {question.title}")
                    return redirect('core:view_assessment', token=token)
                else:
                    messages.error(request, "This question is not available for your assessment.")
            except CodingQuestion.DoesNotExist:
                messages.error(request, "Invalid question selection.")

        if assessment.available_questions.exists():
            questions = assessment.available_questions.all()
        else:
            questions = CodingQuestion.objects.all()

        return render(request, 'core/assessment_question_selection.html', {
            'assessment': assessment,
            'questions': questions,
            'current_date': timezone.now().date().isoformat(),
            'current_user': request.user.username,
        })

    except Assessment.DoesNotExist:
        return HttpResponseNotFound("Assessment not found or not assigned to you.")


@login_required
def view_assessment(request, token):
    if not request.user.is_candidate:
        return HttpResponseForbidden("Access Denied: You must be a candidate to view this page.")

    try:
        assessment = Assessment.objects.get(
            assessment_url_token=token,
            candidate=request.user.candidate_profile
        )

        if assessment.status == 'FINISHED':
            return render(request, 'core/assessment_summary.html', {
                'assessment': assessment,
                'current_date': timezone.now().date().isoformat(),
                'current_user': request.user.username,
            })

        if assessment.is_time_up():
            assessment.status = 'FINISHED'
            assessment.save()
            messages.error(request, "Time is up. Your assessment has been submitted automatically.")
            return redirect('core:candidate_dashboard')

        if assessment.status == 'STARTED':
            if not assessment.chosen_question:
                return redirect('core:choose_assessment_question', token=token)

            if request.method == 'POST':
                code_submission = request.POST.get('code_submission', '')
                code_language = request.POST.get('code_language', assessment.code_language)

                assessment.code_submission = code_submission
                assessment.code_language = code_language
                assessment.save()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Code saved successfully',
                        'saved_at': timezone.now(),
                    })

                messages.success(request, "Your code has been saved.")

            if not assessment.code_submission and assessment.chosen_question:
                assessment.code_submission = assessment.chosen_question.get_starter_code(assessment.code_language)
                assessment.save()

            return render(request, 'core/assessment_workspace.html', {
                'assessment': assessment,
                'question': assessment.chosen_question,
                'remaining_time': assessment.time_remaining(),
                'current_date': timezone.now().date().isoformat(),
                'current_user': request.user.username,
            })

        if assessment.status == 'ACCEPTED':
            return redirect('core:start_assessment', token=token)

        messages.info(request, f"Assessment status: {assessment.get_status_display()}")
        return redirect('core:candidate_dashboard')

    except Assessment.DoesNotExist:
        return HttpResponseNotFound("Assessment not found or not assigned to you.")


@login_required
def submit_assessment(request, token):
    if not request.user.is_candidate:
        return HttpResponseForbidden("Access Denied: You must be a candidate to view this page.")

    try:
        assessment = Assessment.objects.get(
            assessment_url_token=token,
            candidate=request.user.candidate_profile,
            status='STARTED'
        )

        if request.method == 'POST':
            code_submission = request.POST.get('code_submission', '')
            code_language = request.POST.get('code_language', '')

            assessment.code_submission = code_submission
            assessment.code_language = code_language
            assessment.status = 'FINISHED'
            assessment.end_time = timezone.now()
            assessment.evaluation_status = 'PENDING'
            assessment.save()

            try:
                evaluate_assessment.delay(assessment.id)
                messages.success(request,
                                 "Your assessment has been successfully submitted and will be evaluated shortly!")
            except Exception as e:
                logger.exception("Failed to queue evaluation task")
                messages.success(request, "Your assessment has been submitted! It will be evaluated by our team.")

            return redirect('core:candidate_dashboard')

        return render(request, 'core/assessment_submit_confirmation.html', {
            'assessment': assessment,
            'current_date': timezone.now().date().isoformat(),
            'current_user': request.user.username
        })

    except Assessment.DoesNotExist:
        return HttpResponseNotFound("Assessment not found or not assigned to you.")


@login_required
def save_code(request, token):
    if not request.user.is_candidate or request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    try:
        assessment = Assessment.objects.get(
            assessment_url_token=token,
            candidate=request.user.candidate_profile,
            status='STARTED'
        )

        if assessment.is_time_up():
            return JsonResponse({'status': 'error', 'message': 'Time is up'}, status=400)

        data = json.loads(request.body)
        code_submission = data.get('code')
        code_language = data.get('language', assessment.code_language)

        assessment.code_submission = code_submission
        assessment.code_language = code_language
        assessment.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Code saved successfully',
            'saved_at': timezone.now().date().isoformat()
        })

    except Assessment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Assessment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def check_evaluation_status(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)

    if request.user.is_candidate and assessment.candidate != request.user.candidate_profile:
        return JsonResponse({"error": "Access denied"}, status=403)

    if request.user.is_hiring_manager and assessment.created_by != request.user.hiring_manager_profile:
        return JsonResponse({"error": "Access denied"}, status=403)

    return JsonResponse({
        "id": assessment.id,
        "status": assessment.status,
        "evaluation_status": assessment.evaluation_status,
        "evaluation_score": assessment.evaluation_score,
        "completed_at": assessment.evaluation_completed_at.isoformat() if assessment.evaluation_completed_at else None
    })


@login_required
def trigger_evaluation(request, assessment_id):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access denied. Only hiring managers can perform this action.")

    assessment = get_object_or_404(Assessment, id=assessment_id)

    if assessment.created_by != request.user.hiring_manager_profile:
        return HttpResponseForbidden("Access denied. You don't have permission for this assessment.")

    if assessment.status != 'FINISHED':
        messages.error(request, "This assessment cannot be evaluated yet.")
        return redirect('core:manager_assessment_detail', assessment_id=assessment_id)

    try:
        results = evaluate_submission(assessment)

        if results.get('status') == 'success':
            messages.success(request, f"Evaluation completed with score: {assessment.evaluation_score}")
            assessment.status = 'SCORED'
            assessment.save()
        else:
            messages.error(request, f"Evaluation failed: {results.get('message')}")

    except Exception as e:
        messages.error(request, f"Error during evaluation: {str(e)}")

    return redirect('core:manager_assessment_detail', assessment_id=assessment_id)


@login_required
def view_candidate(request, candidate_id):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access Denied: You must be a hiring manager to view this page.")

    candidate = get_object_or_404(Candidate, id=candidate_id)

    assessments = Assessment.objects.filter(candidate=candidate).order_by('-created_at')

    context = {
        'candidate': candidate,
        'assessments': assessments,
        'current_date': timezone.now().date().isoformat(),
        'current_user': request.user.username,
    }

    return render(request, 'core/view_candidate.html', context)


@login_required
def edit_candidate(request, candidate_id):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access Denied: You must be a hiring manager to view this page.")

    candidate = get_object_or_404(Candidate, id=candidate_id)

    if request.method == 'POST':
        form = CandidateForm(request.POST, instance=candidate)
        user_form = UserForm(request.POST, instance=candidate.user)

        if form.is_valid() and user_form.is_valid():
            user = user_form.save()
            candidate = form.save(commit=False)
            candidate.user = user
            candidate.save()

            messages.success(request, f"Candidate {user.email} updated successfully.")
            return redirect('core:manager_dashboard')
    else:
        form = CandidateForm(instance=candidate)
        user_form = UserForm(instance=candidate.user)

    context = {
        'form': form,
        'user_form': user_form,
        'candidate': candidate,
        'current_date': timezone.now().date().isoformat(),
        'current_user': request.user.username,
    }

    return render(request, 'core/edit_candidate.html', context)


@login_required
def resend_assessment(request, assessment_id):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access Denied: You must be a hiring manager to view this page.")

    assessment = get_object_or_404(Assessment, id=assessment_id)

    if assessment.created_by != request.user.hiring_manager_profile:
        return HttpResponseForbidden("Access denied. You don't have permission for this assessment.")

    try:
        if assessment.status == 'SENT':
            from core.utils.email_utils import send_assessment_invitation_email
            send_assessment_invitation_email(assessment)

            assessment.invite_expires_at = timezone.now() + timezone.timedelta(days=7)
            assessment.save()

            messages.success(request, f"Assessment invitation resent to {assessment.candidate.user.email}.")

        elif assessment.status == 'ACCEPTED':
            from core.utils.email_utils import send_assessment_acceptance_email
            send_assessment_acceptance_email(assessment)

            assessment.invite_expires_at = timezone.now() + timezone.timedelta(days=7)
            assessment.save()

            messages.success(request, f"Assessment start link resent to {assessment.candidate.user.email}.")

        else:
            messages.warning(request,
                             f"Cannot resend email for assessments in {assessment.get_status_display()} status.")

    except Exception as e:
        messages.error(request, f"Failed to resend email: {str(e)}")

    return redirect('core:manager_dashboard')


@login_required
def manager_assessment_detail(request, assessment_id):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access Denied: You must be a hiring manager to view this page.")

    assessment = get_object_or_404(Assessment, id=assessment_id)

    if assessment.created_by != request.user.hiring_manager_profile:
        return HttpResponseForbidden("Access denied. You don't have permission for this assessment.")

    if request.method == 'POST' and 'feedback' in request.POST:
        feedback = request.POST.get('feedback', '')
        assessment.feedback = feedback
        assessment.save()
        messages.success(request, "Feedback saved successfully.")
        return redirect('core:manager_assessment_detail', assessment_id=assessment.id)

    context = {
        'assessment': assessment,
        'current_date': timezone.now().date().isoformat(),
        'current_user': request.user.username,
    }

    return render(request, 'core/manager_assessment_detail.html', context)


@login_required
def save_feedback(request, assessment_id):
    if not request.user.is_hiring_manager or request.method != 'POST':
        return HttpResponseForbidden("Access denied or invalid request method.")

    assessment = get_object_or_404(Assessment, id=assessment_id)

    if assessment.created_by != request.user.hiring_manager_profile:
        return HttpResponseForbidden("Access denied. You don't have permission for this assessment.")

    feedback = request.POST.get('feedback', '')
    assessment.feedback = feedback
    assessment.save()

    messages.success(request, "Feedback saved successfully.")
    return redirect('core:manager_assessment_detail', assessment_id=assessment.id)


@login_required
def finalize_interview_decision(request, candidate_id, decision):
    if not request.user.is_hiring_manager:
        return HttpResponseForbidden("Access Denied: You must be a hiring manager to perform this action.")

    candidate = get_object_or_404(Candidate, id=candidate_id)

    if decision not in ['accept', 'reject']:
        messages.error(request, "Invalid decision. Must be 'accept' or 'reject'.")
        return redirect('core:view_candidate', candidate_id=candidate_id)

    if request.method == 'GET':
        context = {
            'candidate': candidate,
            'decision': decision,
            'current_date': timezone.now().date().isoformat(),
            'current_user': request.user.username,
        }
        return render(request, 'core/confirm_interview_decision.html', context)

    elif request.method == 'POST':
        candidate.interview_decision_date = timezone.now()

        if decision == 'accept':
            candidate.interview_status = 'ACCEPTED'

            interview_date_str = request.POST.get('interview_date', '')
            interview_time_str = request.POST.get('interview_time', '')

            if interview_date_str and interview_time_str:
                try:
                    interview_date = timezone.datetime.strptime(
                        f"{interview_date_str} {interview_time_str}",
                        "%Y-%m-%d %H:%M"
                    )
                    interview_date = timezone.make_aware(interview_date)
                    candidate.interview_date = interview_date
                except ValueError:
                    messages.error(request, "Invalid date or time format.")
                    return redirect('core:finalize_interview_decision', candidate_id=candidate_id, decision='accept')

            candidate.interview_notes = request.POST.get('notes', '')
            candidate.save()

            if candidate.interview_date:
                try:
                    send_interview_invitation_email(candidate, candidate.interview_date)
                    messages.success(request, f"Interview invitation email sent to {candidate.user.email}")
                except Exception as e:
                    messages.error(request, f"Error sending email: {str(e)}")
            else:
                messages.info(request, "Candidate accepted, but no interview date was set. No email was sent.")

            messages.success(request, f"Candidate {candidate.user.email} has been accepted for interview.")

        elif decision == 'reject':
            candidate.interview_status = 'REJECTED'
            candidate.save()

            try:
                send_rejection_email(candidate)
                messages.success(request, f"Rejection email sent to {candidate.user.email}")
            except Exception as e:
                messages.error(request, f"Error sending rejection email: {str(e)}")

            success, message = cleanup_candidate_data(candidate)

            if success:
                messages.success(request, "Candidate data has been anonymized for GDPR compliance.")
            else:
                messages.error(request, f"Error during data cleanup: {message}")

            messages.info(request, f"Candidate {candidate.user.email} has been rejected.")

        return redirect('core:view_candidate', candidate_id=candidate_id)

    return HttpResponseForbidden("Invalid request method.")


@login_required
@require_POST
def interview_decision_ajax(request, candidate_id):
    if not request.user.is_hiring_manager:
        return JsonResponse({"status": "error", "message": "Access denied"}, status=403)

    candidate = get_object_or_404(Candidate, id=candidate_id)
    decision = request.POST.get('decision')

    if decision not in ['accept', 'reject']:
        return JsonResponse({"status": "error", "message": "Invalid decision"}, status=400)

    try:
        candidate.interview_decision_date = timezone.now()

        if decision == 'accept':
            candidate.interview_status = 'ACCEPTED'
            candidate.save()
            return JsonResponse({"status": "success", "message": "Candidate accepted for interview"})

        elif decision == 'reject':
            candidate.interview_status = 'REJECTED'
            candidate.save()

            send_rejection_email(candidate)
            cleanup_candidate_data(candidate)

            return JsonResponse({"status": "success", "message": "Candidate rejected and data cleaned up"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)