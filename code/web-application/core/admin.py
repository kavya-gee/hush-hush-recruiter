from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from .models import User, Candidate, HiringManager, Assessment, CodingQuestion
from .utils.email_utils import generate_random_password, send_candidate_credentials_email

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'email', 'full_name', 'is_candidate', 'is_hiring_manager', 'is_staff', 'is_active')
    list_filter = ('is_candidate', 'is_hiring_manager', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('full_name',)}),
        ('Permissions', {'fields': ('is_candidate', 'is_hiring_manager',
                                    'is_staff', 'is_active', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'password1', 'password2',
                       'is_candidate', 'is_hiring_manager', 'is_staff', 'is_active')}
         ),
    )
    search_fields = ('username', 'email', 'full_name')
    ordering = ('username',)
    actions = ['create_and_email_candidate']

    def create_and_email_candidate(self, request, queryset):
        candidate_count = 0
        email_count = 0

        for user in queryset:
            if user.is_candidate:
                password = generate_random_password()
                user.set_password(password)
                user.save()

                candidate, created = Candidate.objects.get_or_create(user=user)
                candidate.generated_password = password
                candidate.save()

                if send_candidate_credentials_email(
                        candidate_username=user.username,
                        candidate_email=user.email,
                        candidate_password=password,
                        candidate_name=user.full_name
                ):
                    email_count += 1

                candidate_count += 1

        messages.success(request,
                         f"Generated new passwords for {candidate_count} candidates. {email_count} emails sent.")

    create_and_email_candidate.short_description = "Generate & email credentials for candidates"


class CandidateAdmin(admin.ModelAdmin):
    list_display = ('user', 'source', 'source_score', 'profile_completed', 'created_at')
    list_filter = ('source', 'profile_completed')
    search_fields = ('user__username', 'user__email', 'user__full_name', 'skills')
    actions = ['resend_credentials_email']

    def resend_credentials_email(self, request, queryset):
        email_count = 0

        for candidate in queryset:
            if candidate.generated_password:
                if send_candidate_credentials_email(
                        candidate_username=candidate.user.username,
                        candidate_email=candidate.user.email,
                        candidate_password=candidate.generated_password,
                        candidate_name=candidate.user.full_name
                ):
                    email_count += 1
            else:
                self.message_user(
                    request,
                    f"No stored password for {candidate.user.username}. Use 'Generate & email credentials' action on the User.",
                    level=messages.WARNING
                )

        messages.success(request, f"Resent credential emails to {email_count} candidates.")

    resend_credentials_email.short_description = "Resend credentials email to candidates"


class HiringManagerAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'department', 'position', 'can_create_assessments')
    list_filter = ('company_name', 'can_create_assessments')
    search_fields = ('user__username', 'user__email', 'user__full_name', 'company_name')


class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'candidate', 'created_by', 'status', 'score', 'start_time', 'end_time')
    list_filter = ('status', 'chosen_question_type')
    search_fields = ('title', 'candidate__user__username', 'candidate__user__email', 'created_by__user__username')
    readonly_fields = ('created_at',)

class CodingQuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'question_type', 'difficulty', 'created_at')
    list_filter = ('question_type', 'difficulty')
    search_fields = ('title', 'description')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'question_type', 'difficulty')
        }),
        ('Examples and Constraints', {
            'fields': ('example_input', 'example_output', 'constraints')
        }),
        ('Starter Code', {
            'fields': ('starter_code_python', 'starter_code_javascript', 'starter_code_sql',
                      'starter_code_html', 'starter_code_css')
        }),
        ('Testing', {
            'fields': ('test_cases',)
        }),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(Candidate, CandidateAdmin)
admin.site.register(HiringManager, HiringManagerAdmin)
admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(CodingQuestion, CodingQuestionAdmin)