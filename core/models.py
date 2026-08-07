from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class SchoolConfiguration(models.Model):
    school_name = models.CharField(max_length=255)
    school_initials_prefix = models.CharField(max_length=20, help_text="Prefix used for student IDs, e.g. AIU")
    logo = models.ImageField(upload_to='school_logos/', null=True, blank=True)
    active_academic_year = models.CharField(max_length=20, default=str(timezone.now().year))
    active_term = models.CharField(max_length=10, default='T1')
    is_active = models.BooleanField(default=True, help_text="Legacy flag; single-school deployments always use the one school record")
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    website = models.CharField(max_length=200, blank=True, default='')
    motto = models.CharField(max_length=255, blank=True, default='')
    head_teacher_name = models.CharField(max_length=120, blank=True, default='')
    bursar_name = models.CharField(max_length=120, blank=True, default='')
    dos_name = models.CharField(max_length=120, blank=True, default='')
    fees_demanded = models.BooleanField(
        default=False,
        help_text='Fee demand notices have been issued for the current term',
    )
    fees_demanded_at = models.DateTimeField(null=True, blank=True)
    term_open_for_academics = models.BooleanField(
        default=True,
        help_text='When False, mark entry is blocked until bursar opens the term',
    )
    term_opened_at = models.DateTimeField(null=True, blank=True)
    current_term_locked = models.BooleanField(
        default=False,
        help_text='When True, academic records for the active term cannot be edited',
    )
    PERIOD_TERMS = 'TERMS'
    PERIOD_SEMESTERS = 'SEMESTERS'
    PERIOD_TYPE_CHOICES = [
        (PERIOD_TERMS, 'Terms (e.g. 3 per year)'),
        (PERIOD_SEMESTERS, 'Semesters (e.g. 2 per year)'),
    ]
    academic_period_type = models.CharField(
        max_length=12, choices=PERIOD_TYPE_CHOICES, default=PERIOD_TERMS,
    )
    periods_per_year = models.PositiveSmallIntegerField(
        default=3, help_text='Number of terms or semesters per academic year',
    )
    GRADING_UGCE = 'UGCE'
    GRADING_LETTER = 'LETTER'
    GRADING_CHOICES = [
        (GRADING_UGCE, 'Uganda UCE (D1–F9)'),
        (GRADING_LETTER, 'Letter grades (A–F)'),
    ]
    grading_system = models.CharField(max_length=10, choices=GRADING_CHOICES, default=GRADING_UGCE)
    label_class = models.CharField(max_length=40, default='Class', blank=True)
    label_subject = models.CharField(max_length=40, default='Subject', blank=True)
    label_head_teacher = models.CharField(max_length=60, default='Head Teacher', blank=True)
    label_dos = models.CharField(max_length=60, default='Director of Studies', blank=True)
    label_bursar = models.CharField(max_length=60, default='Bursar', blank=True)
    label_secretary = models.CharField(max_length=60, default='Secretary', blank=True)
    feature_student_photos = models.BooleanField(default=True)
    feature_reports = models.BooleanField(default=True)
    feature_payments = models.BooleanField(default=True)
    feature_marks_entry = models.BooleanField(default=True)
    feature_promotion = models.BooleanField(default=True)
    feature_notifications = models.BooleanField(default=True)
    carry_fees_on_term_close = models.BooleanField(
        default=True,
        help_text='Outstanding fee demands carry forward when a term is closed',
    )
    backup_google_drive_url = models.URLField(blank=True, default='', help_text='Permanent Google Drive folder link for backups')
    backup_google_refresh_token = models.TextField(blank=True, default='', help_text='OAuth2 refresh token for automated Drive uploads')
    backup_google_folder_id = models.CharField(max_length=120, blank=True, default='', help_text='Google Drive folder ID for backups')
    backup_auto_sync_enabled = models.BooleanField(default=False)
    backup_auto_sync_days = models.PositiveSmallIntegerField(default=7)
    backup_last_export_at = models.DateTimeField(null=True, blank=True)
    network_app_name = models.CharField(max_length=80, blank=True, default='OfficeHub School')

    class Meta:
        verbose_name = "School Configuration"
        verbose_name_plural = "School Configurations"

    def __str__(self):
        return self.school_name

    @classmethod
    def get_school(cls):
        """Return the single school record for this deployment."""
        school = cls.objects.order_by('pk').first()
        if school is None:
            school = cls.objects.create(
                school_name='My School',
                school_initials_prefix='SCH',
                is_active=True,
            )
        return school

    @classmethod
    def get_active(cls):
        return cls.get_school()


class SchoolClass(models.Model):
    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('school', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('SCHOOL_ADMIN', 'School Admin'),
        ('DOS', 'Director of Studies'),
        ('SECRETARY', 'Secretary'),
        ('BURSAR', 'Bursar'),
        ('CLASS_TEACHER', 'Class Teacher'),
        ('SUBJECT_TEACHER', 'Subject Teacher'),
        ('HEAD_TEACHER', 'Head Teacher'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text='Inactive users cannot log in')

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class StudentIDSequence(models.Model):
    school = models.OneToOneField(SchoolConfiguration, on_delete=models.CASCADE)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.school.school_initials_prefix}: {self.last_number}"


class Student(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=30, unique=True, db_index=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, default='M')
    current_class = models.CharField(max_length=50)
    guardian_name = models.CharField(max_length=200, null=True, blank=True)
    guardian_phone = models.CharField(max_length=20, null=True, blank=True)
    guardian_email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    enrollment_date = models.DateField(default=timezone.now)
    passport_photo = models.ImageField(upload_to='student_photos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['student_id', 'last_name']

    def __str__(self):
        return f"{self.student_id} - {self.first_name} {self.last_name}"

    def enrolled_subjects(self, term=None, academic_year=None):
        """Compulsory subjects for class + optional subjects assigned to this student."""
        compulsory = Subject.objects.filter(
            school=self.school,
            class_level=self.current_class,
            subject_type=Subject.COMPULSORY,
        )
        optional_ids = StudentSubjectEnrollment.objects.filter(
            student=self, is_active=True,
        ).values_list('subject_id', flat=True)
        optional = Subject.objects.filter(pk__in=optional_ids)
        return compulsory.union(optional).order_by('name')

    @property
    def class_object(self):
        return SchoolClass.objects.filter(school=self.school, name=self.current_class).first()

    def get_fee_structure(self, term=None, academic_year=None, fee_type=None):
        from .fee_utils import resolve_fee_structure
        fs, _ = resolve_fee_structure(
            self.school, self.current_class,
            term or self.school.active_term,
            academic_year or self.school.active_academic_year,
            fee_type=fee_type,
        )
        return fs

    def get_all_fee_structures(self, term=None, academic_year=None):
        from .fee_utils import term_aliases
        term = term or self.school.active_term
        academic_year = academic_year or self.school.active_academic_year
        seen = set()
        structures = []
        for t in term_aliases(term):
            for fs in FeeStructure.objects.filter(
                school=self.school,
                target_class=self.current_class,
                academic_year=academic_year,
                term=t,
            ):
                if fs.id not in seen:
                    seen.add(fs.id)
                    structures.append(fs)
        return structures

    def total_fees_required(self, term=None, academic_year=None):
        structures = self.get_all_fee_structures(term, academic_year)
        if not structures:
            return Decimal('0.00')
        return sum((fs.compute_total() for fs in structures), Decimal('0.00'))

    def total_paid(self, term=None, academic_year=None, fee_type=None):
        from .fee_utils import term_aliases
        term = term or self.school.active_term
        academic_year = academic_year or self.school.active_academic_year
        qs = FeePaymentLedger.objects.filter(
            student=self,
            academic_year=academic_year,
            term__in=term_aliases(term),
        )
        if fee_type:
            qs = qs.filter(fee_type=fee_type)
        total = qs.aggregate(total=models.Sum('amount_paid'))['total'] or Decimal('0.00')
        credit = StudentFeeCredit.credit_total(self, term, academic_year, fee_type=fee_type)
        return (total + credit).quantize(Decimal('0.01'))

    def balance(self, term=None, academic_year=None, fee_type=None):
        if fee_type:
            fee_struct = self.get_fee_structure(term, academic_year, fee_type=fee_type)
            if not fee_struct:
                return None
            required = fee_struct.compute_total()
            paid = self.total_paid(term, academic_year, fee_type=fee_type)
            return (required - paid).quantize(Decimal('0.01'))
        structures = self.get_all_fee_structures(term, academic_year)
        if not structures:
            return None
        required = self.total_fees_required(term, academic_year)
        paid = self.total_paid(term, academic_year)
        return (required - paid).quantize(Decimal('0.01'))

    def is_fees_cleared(self, term=None, academic_year=None):
        balance = self.balance(term, academic_year)
        return balance is not None and balance <= Decimal('0.00')

    def save(self, *args, **kwargs):
        # Ensure a student_id is generated using the school's prefix and an atomic sequence
        if not self.student_id:
            if not self.school:
                self.school = SchoolConfiguration.get_school()

            with transaction.atomic():
                seq, _ = StudentIDSequence.objects.select_for_update().get_or_create(school=self.school)
                seq.last_number += 1
                seq.save()
                number = str(seq.last_number).zfill(5)
                self.student_id = f"{self.school.school_initials_prefix}-{number}"

        super().save(*args, **kwargs)


class Subject(models.Model):
    COMPULSORY = 'COMPULSORY'
    OPTIONAL = 'OPTIONAL'
    TYPE_CHOICES = [
        (COMPULSORY, 'Compulsory (whole class)'),
        (OPTIONAL, 'Optional (per student)'),
    ]

    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    class_level = models.CharField(max_length=50)
    subject_type = models.CharField(max_length=12, choices=TYPE_CHOICES, default=COMPULSORY)

    class Meta:
        ordering = ['class_level', 'name']

    def __str__(self):
        tag = 'C' if self.subject_type == self.COMPULSORY else 'O'
        return f"{self.name} ({self.class_level}) [{tag}]"

    @property
    def is_compulsory(self):
        return self.subject_type == self.COMPULSORY


class StudentSubjectEnrollment(models.Model):
    """Optional subjects assigned to individual students."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subject_enrollments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='student_enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'subject')
        ordering = ['subject__name']

    def __str__(self):
        return f"{self.student.student_id} -> {self.subject.name}"


class TeacherSubjectAssignment(models.Model):
    teacher = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['CLASS_TEACHER', 'SUBJECT_TEACHER', 'SCHOOL_ADMIN', 'DOS', 'HEAD_TEACHER']},
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    assigned_class = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.teacher.user.username} -> {self.subject.name} ({self.assigned_class})"


class ClassTeacherAssignment(models.Model):
    teacher = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['CLASS_TEACHER', 'DOS', 'HEAD_TEACHER']},
    )
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('teacher', 'school_class')

    def __str__(self):
        return f"{self.teacher.user.username} -> {self.school_class.name}"


class AssessmentType(models.Model):
    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    weight_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text='Percentage weight for this assessment, e.g., 30.00')

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return f"{self.school.school_initials_prefix}: {self.name} ({self.weight_percentage}%)"


class MarkEntry(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    assessment_type = models.ForeignKey(AssessmentType, on_delete=models.CASCADE)
    score_achieved = models.DecimalField(max_digits=6, decimal_places=2)
    grading_term = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    recorded_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['student', 'subject', 'grading_term', 'academic_year'])]

    def weighted_score(self):
        weight = Decimal(self.assessment_type.weight_percentage) / Decimal(100)
        return (Decimal(self.score_achieved) * weight).quantize(Decimal('0.01'))

    def grade(self):
        total = float(self.score_achieved)
        school = self.student.school if self.student_id else None
        return grade_from_score(total, school=school)

    def __str__(self):
        return f"{self.student.student_id} - {self.subject.name} - {self.assessment_type.name}: {self.score_achieved}"


def grade_from_score(score: float, school=None) -> str:
    if school and getattr(school, 'grading_system', None) == SchoolConfiguration.GRADING_LETTER:
        if score >= 80:
            return 'A'
        if score >= 70:
            return 'B'
        if score >= 60:
            return 'C'
        if score >= 50:
            return 'D'
        if score >= 40:
            return 'E'
        return 'F'
    if score >= 80:
        return 'D1'
    if score >= 75:
        return 'D2'
    if score >= 70:
        return 'C3'
    if score >= 65:
        return 'C4'
    if score >= 60:
        return 'C5'
    if score >= 50:
        return 'C6'
    if score >= 45:
        return 'P7'
    if score >= 40:
        return 'P8'
    return 'F9'


class FeeStructure(models.Model):
    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, null=True, blank=True)
    target_class = models.CharField(max_length=50)
    fee_type = models.CharField(max_length=120, blank=True, default='', help_text='Fee type or category')
    term = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    total_fees_required = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('school', 'target_class', 'term', 'academic_year', 'fee_type')

    def __str__(self):
        label = self.fee_type or 'General'
        return f"{self.school.school_name} {self.target_class} [{label}] {self.term}/{self.academic_year}: {self.total_fees_required}"

    def save(self, *args, **kwargs):
        if self.school_class and not self.target_class:
            self.target_class = self.school_class.name
        super().save(*args, **kwargs)

    def fee_items(self):
        return list(self.components.all())

    def compute_total(self):
        if self.components.exists():
            return sum((item.amount for item in self.components.all()), Decimal('0.00'))
        return self.total_fees_required


class FeeComponent(models.Model):
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='components')
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.name} - {self.amount}"


class ReceiptSequence(models.Model):
    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE)
    year = models.CharField(max_length=10)
    term = models.CharField(max_length=10)
    last_seq = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('school', 'year', 'term')

    def __str__(self):
        return f"{self.school.school_initials_prefix} {self.year}-{self.term} -> {self.last_seq}"


class FeePaymentLedger(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    balance_remaining = models.DecimalField(max_digits=12, decimal_places=2)
    fee_type = models.CharField(max_length=120, blank=True, default='', help_text='Fee category this payment applies to')
    term = models.CharField(blank=True, default='', max_length=10)
    academic_year = models.CharField(blank=True, default='', max_length=10)
    PAYMENT_MODES = [
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK', 'Bank Deposit'),
        ('CHEQUE', 'Cheque'),
        ('OTHER', 'Other'),
    ]
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='CASH')
    unique_receipt_id = models.CharField(max_length=50, unique=True)
    date_of_payment = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['student', 'unique_receipt_id'])]

    def __str__(self):
        return f"{self.unique_receipt_id} - {self.student.student_id} - {self.amount_paid}"

    @classmethod
    def create_payment(
        cls,
        student: Student,
        amount: Decimal,
        recorded_by: UserProfile = None,
        term: str = None,
        academic_year: str = None,
        payment_mode: str = 'CASH',
        fee_type: str = None,
        excess_action: str = None,
        excess_fee_type: str = None,
    ):
        from .fee_utils import create_payment_record
        return create_payment_record(
            student=student,
            amount=amount,
            recorded_by=recorded_by,
            term=term,
            academic_year=academic_year,
            payment_mode=payment_mode,
            fee_type=fee_type,
            excess_action=excess_action,
            excess_fee_type=excess_fee_type,
        )


class StudentFeeCredit(models.Model):
    """Overpayment credit applied to another fee type or forwarded to a future term."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_credits')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee_type = models.CharField(max_length=120, blank=True, default='')
    term = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    notes = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.student_id} credit {self.amount} ({self.term}/{self.academic_year})"

    @classmethod
    def credit_total(cls, student, term, academic_year, fee_type=None):
        from .fee_utils import term_aliases
        qs = cls.objects.filter(
            student=student,
            academic_year=academic_year,
            term__in=term_aliases(term),
        )
        if fee_type:
            qs = qs.filter(fee_type=fee_type)
        total = qs.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        return total


class PromotionCriteria(models.Model):
    """Academic promotion thresholds set by super admin."""
    school = models.OneToOneField(SchoolConfiguration, on_delete=models.CASCADE, related_name='promotion_criteria')
    minimum_average = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('50.00'),
        help_text='Minimum overall average (%) to qualify for promotion',
    )
    require_fees_cleared = models.BooleanField(default=False)
    minimum_attendance_percent = models.PositiveIntegerField(
        default=75, help_text='Minimum attendance % required for promotion',
    )
    auto_promote_on_year_end = models.BooleanField(
        default=False,
        help_text='When enabled, year-end promotion skips students below pass mark',
    )

    def __str__(self):
        return f"{self.school.school_name} pass mark {self.minimum_average}%"


class SchoolTermArchive(models.Model):
    """Historical record when a school advances to a new term/year."""
    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE, related_name='term_archives')
    term = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    closed_at = models.DateTimeField(auto_now_add=True)
    reports_published = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')
    closed_by = models.ForeignKey('UserProfile', blank=True, null=True, on_delete=models.SET_NULL)
    records_locked = models.BooleanField(default=True)
    fees_carried_forward = models.BooleanField(default=False)

    class Meta:
        ordering = ['-closed_at']
        unique_together = ('school', 'term', 'academic_year')

    def __str__(self):
        return f"{self.school.school_name} {self.term}/{self.academic_year}"


class TermReportPublication(models.Model):
    REPORT_MIDTERM = 'midterm'
    REPORT_EOT = 'eot'
    REPORT_TYPES = [
        (REPORT_MIDTERM, 'Mid-Term'),
        (REPORT_EOT, 'End of Term'),
    ]

    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE, related_name='report_publications')
    class_name = models.CharField(blank=True, default='', help_text='Blank = entire school', max_length=50)
    term = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    report_type = models.CharField(choices=REPORT_TYPES, max_length=10)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    published_by = models.ForeignKey('UserProfile', blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-published_at']
        unique_together = ('school', 'class_name', 'term', 'academic_year', 'report_type')

    def __str__(self):
        return f"{self.school.school_name} {self.class_name or 'Whole School'} {self.term}/{self.academic_year} {self.report_type}"


class StudentTermRecord(models.Model):
    CONDUCT_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('NEEDS_IMPROVEMENT', 'Needs Improvement'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='term_records')
    term = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    days_present = models.PositiveIntegerField(default=0)
    total_school_days = models.PositiveIntegerField(default=60, help_text='Total school days in the term')
    conduct_rating = models.CharField(choices=CONDUCT_CHOICES, default='GOOD', max_length=20)
    conduct_note = models.TextField(blank=True, default='')
    class_teacher_remark = models.TextField(blank=True, default='')
    head_teacher_remark = models.TextField(blank=True, default='')
    dos_remark = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('UserProfile', blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['student__last_name']
        unique_together = ('student', 'term', 'academic_year')

    def __str__(self):
        return f"{self.student.student_id} {self.term}/{self.academic_year}"

    @property
    def days_absent(self):
        return max(self.total_school_days - self.days_present, 0)

    @property
    def attendance_percent(self):
        if not self.total_school_days:
            return 0
        return round((self.days_present / self.total_school_days) * 100, 2)

    def get_conduct_rating_display(self):
        return dict(self.CONDUCT_CHOICES).get(self.conduct_rating, self.conduct_rating)


class ClassPromotionRule(models.Model):
    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE, related_name='promotion_rules')
    from_class = models.CharField(max_length=50)
    to_class = models.CharField(blank=True, default='', help_text='Leave blank to mark students as graduated', max_length=50)
    pass_mark = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Minimum average (%) to promote from this class; uses school default if blank',
    )

    class Meta:
        ordering = ['from_class']
        unique_together = ('school', 'from_class')

    def __str__(self):
        return f"{self.school.school_name}: {self.from_class} -> {self.to_class or 'Graduate'}"


class PromotionRun(models.Model):
    school = models.ForeignKey(SchoolConfiguration, on_delete=models.CASCADE, related_name='promotion_runs')
    from_academic_year = models.CharField(max_length=10)
    to_academic_year = models.CharField(max_length=10)
    students_promoted = models.PositiveIntegerField(default=0)
    students_graduated = models.PositiveIntegerField(default=0)
    run_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')
    run_by = models.ForeignKey('UserProfile', blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.school.school_name} {self.from_academic_year}->{self.to_academic_year}"


class ReportNotificationLog(models.Model):
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
    ]

    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_SKIPPED = 'skipped'
    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SKIPPED, 'Skipped'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='report_notifications')
    term = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    report_type = models.CharField(max_length=10)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    recipient = models.CharField(blank=True, max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    detail = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey('UserProfile', blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.student.student_id} {self.channel} {self.status}"
