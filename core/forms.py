from django import forms
from django.contrib.auth import get_user_model
from .models import (
    Student, FeePaymentLedger, FeeStructure, SchoolConfiguration, UserProfile,
    SchoolClass, Subject, TeacherSubjectAssignment, AssessmentType,
)


TAILWIND_INPUT = 'border rounded px-3 py-2 w-full focus:outline-none focus:ring'


class UserProfileEditForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT})
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT})
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'w-full'})
    )


class StudentEditForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'guardian_name', 'guardian_phone', 'guardian_email', 'address',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': TAILWIND_INPUT}),
            'last_name': forms.TextInput(attrs={'class': TAILWIND_INPUT}),
            'date_of_birth': forms.DateInput(attrs={'class': TAILWIND_INPUT, 'type': 'date'}),
            'gender': forms.Select(attrs={'class': TAILWIND_INPUT}),
            'guardian_name': forms.TextInput(attrs={'class': TAILWIND_INPUT}),
            'guardian_phone': forms.TextInput(attrs={'class': TAILWIND_INPUT}),
            'guardian_email': forms.EmailInput(attrs={'class': TAILWIND_INPUT}),
            'address': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'rows': 3}),
        }


class StudentRegistrationForm(forms.ModelForm):
    current_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        required=True,
        label='Class',
        widget=forms.Select(attrs={'class': TAILWIND_INPUT})
    )
    optional_subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        label='Optional subjects',
        widget=forms.CheckboxSelectMultiple,
        help_text='Compulsory subjects apply to the whole class automatically.',
    )

    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'current_class',
            'guardian_name', 'guardian_phone', 'guardian_email', 'address', 'passport_photo'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Last name'}),
            'date_of_birth': forms.DateInput(attrs={'class': TAILWIND_INPUT, 'type': 'date'}),
            'gender': forms.Select(attrs={'class': TAILWIND_INPUT}),
            'guardian_name': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Parent / Guardian Name'}),
            'guardian_phone': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Parent / Guardian Phone'}),
            'guardian_email': forms.EmailInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Parent / Guardian Email'}),
            'address': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Home Address', 'rows': 3}),
            'passport_photo': forms.ClearableFileInput(attrs={'class': 'w-full'}),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['current_class'].queryset = SchoolClass.objects.filter(school=school)
            self.fields['optional_subjects'].queryset = Subject.objects.filter(
                school=school, subject_type=Subject.OPTIONAL,
            )
        else:
            self.fields['current_class'].queryset = SchoolClass.objects.none()
            self.fields['optional_subjects'].queryset = Subject.objects.none()

    def clean_current_class(self):
        value = self.cleaned_data.get('current_class')
        if hasattr(value, 'name'):
            return value.name
        return value

    def save_optional_subjects(self, student):
        from .models import StudentSubjectEnrollment
        for subject in self.cleaned_data.get('optional_subjects', []):
            if subject.class_level == student.current_class:
                StudentSubjectEnrollment.objects.get_or_create(
                    student=student, subject=subject,
                    defaults={'is_active': True},
                )


class SchoolSettingsForm(forms.ModelForm):
    """Edit the single school configuration for this deployment."""
    
    # Dropdown fields for academic settings
    active_academic_year = forms.ChoiceField(
        choices=[],  # Populated in __init__
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Academic Year'
    )
    active_term = forms.ChoiceField(
        choices=[
            ('T1', 'Term 1'),
            ('T2', 'Term 2'),
            ('T3', 'Term 3'),
            ('S1', 'Semester 1'),
            ('S2', 'Semester 2'),
        ],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Active Term'
    )

    class Meta:
        model = SchoolConfiguration
        fields = [
            'school_name', 'school_initials_prefix', 'logo', 'motto',
            'address', 'phone', 'email', 'website',
            'head_teacher_name', 'bursar_name', 'dos_name',
            'active_academic_year', 'active_term',
        ]
        widgets = {
            'school_name': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Full school name'}),
            'school_initials_prefix': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'e.g. AIU'}),
            'motto': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'School motto'}),
            'address': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'rows': 2, 'placeholder': 'Physical address'}),
            'phone': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'School phone'}),
            'email': forms.EmailInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'School email'}),
            'website': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Website (optional)'}),
            'head_teacher_name': forms.TextInput(attrs={'class': TAILWIND_INPUT}),
            'bursar_name': forms.TextInput(attrs={'class': TAILWIND_INPUT}),
            'dos_name': forms.TextInput(attrs={'class': TAILWIND_INPUT}),
            'logo': forms.ClearableFileInput(attrs={'class': 'w-full'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate academic year choices (current year - 5 to + 5)
        from datetime import datetime
        current_year = datetime.now().year
        year_choices = [(str(y), str(y)) for y in range(current_year - 5, current_year + 6)]
        self.fields['active_academic_year'].choices = year_choices


class SchoolConfigForm(SchoolSettingsForm):
    """Alias kept for admin dashboard compatibility."""
    pass


class FeePaymentForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        label='Student',
        widget=forms.Select(attrs={'class': TAILWIND_INPUT})
    )
    fee_type = forms.ChoiceField(
        choices=[('', '-- Select fee type --')],
        label='Fee type',
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
    )
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Amount in Ushs'}),
    )
    payment_mode = forms.ChoiceField(
        choices=FeePaymentLedger.PAYMENT_MODES,
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
    )
    excess_action = forms.ChoiceField(
        required=False,
        label='If overpaid, apply excess to',
        choices=[
            ('', 'Keep as credit on this fee'),
            ('other_fee', 'Another fee type'),
            ('next_term', 'Forward to next term'),
        ],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
    )
    excess_fee_type = forms.CharField(
        required=False,
        label='Target fee type (if overpaid)',
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'e.g. Lunch, Transport'}),
    )

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.none()
        self.school = school
        if school:
            self.fields['student'].queryset = Student.objects.filter(school=school, is_active=True)
            fee_types = set()
            for ft in FeeStructure.objects.filter(school=school).values_list('fee_type', flat=True):
                fee_types.add(ft or 'General')
            if fee_types:
                self.fields['fee_type'].choices = [(ft, ft) for ft in sorted(fee_types)]
            else:
                self.fields['fee_type'].choices = [('General', 'General')]


class StaffUserCreationForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Last name'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Password'})
    )
    role = forms.ChoiceField(
        choices=[('', '-- Select Role --')] + [choice for choice in UserProfile.ROLE_CHOICES if choice[0] != 'SUPER_ADMIN'],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT})
    )
    assigned_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        required=False,
        label='Assigned class',
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
    )
    assigned_subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        label='Assigned subjects',
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['assigned_class'].queryset = SchoolClass.objects.filter(school=school)
            self.fields['assigned_subjects'].queryset = Subject.objects.filter(school=school)

    def clean_username(self):
        username = self.cleaned_data['username']
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        return username


class AssessmentTypeForm(forms.ModelForm):
    class Meta:
        model = AssessmentType
        fields = ['name', 'weight_percentage']
        widgets = {
            'name': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Assessment name'}),
            'weight_percentage': forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Weight %'}),
        }


class SchoolClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Class name'}),
            'description': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Optional description', 'rows': 2}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'class_level', 'subject_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Subject name'}),
            'class_level': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Class level (e.g. Form 1A)'}),
            'subject_type': forms.Select(attrs={'class': TAILWIND_INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['class_level'].label = 'Class level'


class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ['school_class', 'target_class', 'fee_type', 'term', 'academic_year', 'total_fees_required']
        widgets = {
            'school_class': forms.Select(attrs={'class': TAILWIND_INPUT}),
            'target_class': forms.HiddenInput(),
            'fee_type': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'e.g. Tuition, Lunch, Transport'}),
            'term': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Term, e.g. T1'}),
            'academic_year': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Academic year'}),
            'total_fees_required': forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Amount (Ushs)'}),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school
        self.fields['school_class'].queryset = SchoolClass.objects.none()
        self.fields['school_class'].required = True
        self.fields['target_class'].required = False
        if school:
            self.fields['school_class'].queryset = SchoolClass.objects.filter(school=school)
            if not self.instance.pk:
                self.fields['term'].initial = school.active_term
                self.fields['academic_year'].initial = school.active_academic_year
                self.fields['fee_type'].initial = 'Tuition'

    def clean(self):
        cleaned = super().clean()
        school_class = cleaned.get('school_class')
        if school_class:
            cleaned['target_class'] = school_class.name
        fee_type = (cleaned.get('fee_type') or '').strip()
        cleaned['fee_type'] = fee_type or 'General'
        return cleaned


class MarkEntryForm(forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.none(), widget=forms.Select(attrs={'class': TAILWIND_INPUT}))
    subject = forms.ModelChoiceField(queryset=Subject.objects.none(), widget=forms.Select(attrs={'class': TAILWIND_INPUT}))
    assessment = forms.ModelChoiceField(queryset=AssessmentType.objects.none(), widget=forms.Select(attrs={'class': TAILWIND_INPUT}))
    score = forms.DecimalField(max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Score'}))

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.none()
        self.fields['subject'].queryset = Subject.objects.none()
        self.fields['assessment'].queryset = AssessmentType.objects.none()
        if school:
            self.fields['student'].queryset = Student.objects.filter(school=school)
            self.fields['subject'].queryset = Subject.objects.filter(school=school)
            self.fields['assessment'].queryset = AssessmentType.objects.filter(school=school)


class StudentTermRecordForm(forms.ModelForm):
    class Meta:
        from .models import StudentTermRecord
        model = StudentTermRecord
        fields = [
            'days_present', 'total_school_days', 'conduct_rating', 'conduct_note',
            'class_teacher_remark', 'head_teacher_remark', 'dos_remark'
        ]
        widgets = {
            'days_present': forms.NumberInput(attrs={'class': TAILWIND_INPUT}),
            'total_school_days': forms.NumberInput(attrs={'class': TAILWIND_INPUT}),
            'conduct_rating': forms.Select(attrs={'class': TAILWIND_INPUT}),
            'conduct_note': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'rows': 2}),
            'class_teacher_remark': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'rows': 3}),
            'head_teacher_remark': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'rows': 3}),
            'dos_remark': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'rows': 3}),
        }


class ClassPromotionRuleForm(forms.ModelForm):
    from_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='From Class'
    )
    to_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='To Class'
    )
    
    class Meta:
        from .models import ClassPromotionRule
        model = ClassPromotionRule
        fields = ['from_class', 'to_class', 'pass_mark']
        widgets = {
            'pass_mark': forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Pass mark % (optional)'}),
        }
    
    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['from_class'].queryset = SchoolClass.objects.filter(school=school)
            self.fields['to_class'].queryset = SchoolClass.objects.filter(school=school)
        else:
            self.fields['from_class'].queryset = SchoolClass.objects.none()
            self.fields['to_class'].queryset = SchoolClass.objects.none()
    
    def clean(self):
        cleaned = super().clean()
        from_class = cleaned.get('from_class')
        to_class = cleaned.get('to_class')
        if from_class and to_class:
            cleaned['from_class'] = from_class.name if hasattr(from_class, 'name') else from_class
            cleaned['to_class'] = to_class.name if hasattr(to_class, 'name') else to_class
        return cleaned


class StaffPasswordResetForm(forms.Form):
    new_password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'New password'}),
    )


class SuperAdminSchoolForm(forms.ModelForm):
    class Meta:
        model = SchoolConfiguration
        fields = ['is_active', 'carry_fees_on_term_close']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'carry_fees_on_term_close': forms.CheckboxInput(attrs={'class': 'rounded'}),
        }


class SuperAdminFeatureForm(forms.ModelForm):
    class Meta:
        model = SchoolConfiguration
        fields = [
            'feature_student_photos', 'feature_reports', 'feature_payments',
            'feature_marks_entry', 'feature_promotion', 'feature_notifications',
        ]
        widgets = {f: forms.CheckboxInput(attrs={'class': 'rounded'}) for f in [
            'feature_student_photos', 'feature_reports', 'feature_payments',
            'feature_marks_entry', 'feature_promotion', 'feature_notifications',
        ]}


class SuperAdminTerminologyForm(forms.ModelForm):
    class Meta:
        model = SchoolConfiguration
        fields = [
            'label_class', 'label_subject', 'label_head_teacher',
            'label_dos', 'label_bursar', 'label_secretary',
        ]
        widgets = {f: forms.TextInput(attrs={'class': TAILWIND_INPUT}) for f in [
            'label_class', 'label_subject', 'label_head_teacher',
            'label_dos', 'label_bursar', 'label_secretary',
        ]}


class SuperAdminGradingForm(forms.ModelForm):
    class Meta:
        model = SchoolConfiguration
        fields = ['grading_system']
        widgets = {
            'grading_system': forms.Select(attrs={'class': TAILWIND_INPUT}),
        }


class SuperAdminPeriodForm(forms.ModelForm):
    active_academic_year = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Academic Year'
    )
    active_term = forms.ChoiceField(
        choices=[
            ('T1', 'Term 1'),
            ('T2', 'Term 2'),
            ('T3', 'Term 3'),
            ('S1', 'Semester 1'),
            ('S2', 'Semester 2'),
        ],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Active Term'
    )
    
    class Meta:
        model = SchoolConfiguration
        fields = ['academic_period_type', 'periods_per_year', 'active_term', 'active_academic_year']
        widgets = {
            'academic_period_type': forms.Select(attrs={'class': TAILWIND_INPUT}),
            'periods_per_year': forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'min': 1, 'max': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from datetime import datetime
        current_year = datetime.now().year
        year_choices = [(str(y), str(y)) for y in range(current_year - 5, current_year + 6)]
        self.fields['active_academic_year'].choices = year_choices


class SuperAdminBackupForm(forms.ModelForm):
    class Meta:
        model = SchoolConfiguration
        fields = [
            'backup_google_drive_url', 'backup_google_folder_id',
            'backup_google_refresh_token', 'backup_auto_sync_enabled',
            'backup_auto_sync_days', 'network_app_name',
        ]
        widgets = {
            'backup_google_drive_url': forms.URLInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'https://drive.google.com/drive/folders/...'}),
            'backup_google_folder_id': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Drive folder ID (optional if URL set)'}),
            'backup_google_refresh_token': forms.Textarea(attrs={'class': TAILWIND_INPUT, 'rows': 2, 'placeholder': 'OAuth2 refresh token from Google Cloud Console'}),
            'backup_auto_sync_enabled': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'backup_auto_sync_days': forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'min': 1, 'max': 30}),
            'network_app_name': forms.TextInput(attrs={'class': TAILWIND_INPUT}),
        }


class PromotionRunForm(forms.Form):
    to_academic_year = forms.ChoiceField(
        choices=[],  # Populated in __init__
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Promote to Academic Year'
    )
    reset_term = forms.BooleanField(required=False, initial=False, label='Reset to Term 1')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from datetime import datetime
        current_year = datetime.now().year
        year_choices = [(str(y), str(y)) for y in range(current_year, current_year + 6)]
        self.fields['to_academic_year'].choices = year_choices


class StudentBulkPromotionForm(forms.Form):
    """Form for bulk promoting students from one class to another."""
    from_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Current Class'
    )
    to_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Target Class'
    )
    academic_year = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Target Academic Year'
    )
    student_ids = forms.CharField(
        widget=forms.HiddenInput(),
        help_text='Comma-separated student IDs to promote'
    )
    
    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['from_class'].queryset = SchoolClass.objects.filter(school=school)
            self.fields['to_class'].queryset = SchoolClass.objects.filter(school=school)
        else:
            self.fields['from_class'].queryset = SchoolClass.objects.none()
            self.fields['to_class'].queryset = SchoolClass.objects.none()
        
        # Populate academic year choices
        from datetime import datetime
        current_year = datetime.now().year
        year_choices = [(str(y), str(y)) for y in range(current_year, current_year + 6)]
        self.fields['academic_year'].choices = year_choices
    
    def clean(self):
        cleaned = super().clean()
        from_class = cleaned.get('from_class')
        to_class = cleaned.get('to_class')
        if from_class and to_class:
            if from_class.name == to_class.name:
                raise forms.ValidationError("Source and target classes must be different.")
        return cleaned


class PromotionCriteriaForm(forms.ModelForm):
    class Meta:
        from .models import PromotionCriteria
        model = PromotionCriteria
        fields = [
            'minimum_average', 'require_fees_cleared',
            'minimum_attendance_percent', 'auto_promote_on_year_end',
        ]
        widgets = {
            'minimum_average': forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'Pass mark %'}),
            'minimum_attendance_percent': forms.NumberInput(attrs={'class': TAILWIND_INPUT}),
            'require_fees_cleared': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'auto_promote_on_year_end': forms.CheckboxInput(attrs={'class': 'rounded'}),
        }


class LoadNewTermForm(forms.Form):
    new_term = forms.ChoiceField(
        choices=[
            ('T1', 'Term 1'),
            ('T2', 'Term 2'),
            ('T3', 'Term 3'),
            ('S1', 'Semester 1'),
            ('S2', 'Semester 2'),
        ],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='New Term'
    )
    new_academic_year = forms.ChoiceField(
        choices=[],  # Populated in __init__
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
        label='Academic Year'
    )
    archive_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TAILWIND_INPUT, 'rows': 2, 'placeholder': 'Optional notes for archived term'}),
    )
    reports_were_published = forms.BooleanField(required=False, initial=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from datetime import datetime
        current_year = datetime.now().year
        year_choices = [(str(y), str(y)) for y in range(current_year - 5, current_year + 6)]
        self.fields['new_academic_year'].choices = year_choices


class ReportNotifyForm(forms.Form):
    REPORT_CHOICES = [
        ('midterm', 'Mid-Term'),
        ('eot', 'End of Term'),
    ]
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Both'),
    ]

    report_type = forms.ChoiceField(choices=REPORT_CHOICES, widget=forms.Select(attrs={'class': TAILWIND_INPUT}))
    class_name = forms.ChoiceField(choices=[('', 'Whole School')], required=False, widget=forms.Select(attrs={'class': TAILWIND_INPUT}))
    channel = forms.ChoiceField(choices=CHANNEL_CHOICES, widget=forms.Select(attrs={'class': TAILWIND_INPUT}))

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            classes = SchoolClass.objects.filter(school=school).values_list('name', 'name')
            choices = [('', 'Whole School')] + list(classes)
            self.fields['class_name'].choices = choices
