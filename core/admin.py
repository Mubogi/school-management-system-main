from django.contrib import admin
from .models import (
    SchoolConfiguration, UserProfile, Student, SchoolClass, Subject,
    TeacherSubjectAssignment, ClassTeacherAssignment, AssessmentType,
    MarkEntry, FeeStructure, FeeComponent, FeePaymentLedger,
    TermReportPublication, StudentTermRecord, ClassPromotionRule,
    PromotionRun, ReportNotificationLog,
)


@admin.register(SchoolConfiguration)
class SchoolConfigurationAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'school_initials_prefix', 'active_academic_year', 'active_term', 'is_active')
    list_filter = ('is_active', 'active_academic_year')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'school')
    list_filter = ('role',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'current_class', 'is_active')
    search_fields = ('student_id', 'first_name', 'last_name')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_level', 'school')
    search_fields = ('name',)


@admin.register(TeacherSubjectAssignment)
class TeacherSubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'assigned_class')


@admin.register(ClassTeacherAssignment)
class ClassTeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'school_class')


@admin.register(FeeComponent)
class FeeComponentAdmin(admin.ModelAdmin):
    list_display = ('fee_structure', 'name', 'amount')


@admin.register(AssessmentType)
class AssessmentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'weight_percentage')


@admin.register(MarkEntry)
class MarkEntryAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'assessment_type', 'score_achieved', 'grading_term', 'academic_year')
    list_filter = ('grading_term', 'academic_year')


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('school', 'target_class', 'term', 'academic_year', 'total_fees_required')


@admin.register(FeePaymentLedger)
class FeePaymentLedgerAdmin(admin.ModelAdmin):
    list_display = ('unique_receipt_id', 'student', 'amount_paid', 'balance_remaining', 'date_of_payment')
    search_fields = ('unique_receipt_id', 'student__student_id')


@admin.register(TermReportPublication)
class TermReportPublicationAdmin(admin.ModelAdmin):
    list_display = ('school', 'class_name', 'term', 'academic_year', 'report_type', 'is_published', 'published_at')
    list_filter = ('is_published', 'report_type')


@admin.register(StudentTermRecord)
class StudentTermRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'academic_year', 'days_present', 'conduct_rating')
    search_fields = ('student__student_id',)


@admin.register(ClassPromotionRule)
class ClassPromotionRuleAdmin(admin.ModelAdmin):
    list_display = ('school', 'from_class', 'to_class')


@admin.register(ReportNotificationLog)
class ReportNotificationLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'channel', 'status', 'sent_at')
    list_filter = ('channel', 'status')
