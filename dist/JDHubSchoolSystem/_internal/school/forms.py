from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .models import (
    Attendance,
    Exam,
    FeePayment,
    LeaveRequest,
    Note,
    Notice,
    Result,
    SchoolClass,
    Subject,
    Syllabus,
    Timetable,
    Teacher,
    Student,
    Bus,
    Feedback,
)

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content']

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'file']

class SyllabusForm(forms.ModelForm):
    class Meta:
        model = Syllabus
        fields = ['subject', 'file']

class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['title', 'file']

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code']

class ClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ['name']

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['user', 'subjects']

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['user', 'roll_number', 'school_class', 'bus']

class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = ['route_name', 'stops']

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'subject', 'date', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['student', 'reason']

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'subject', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['exam', 'student', 'marks_obtained', 'total_marks']

class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = FeePayment
        fields = ['student', 'amount', 'status', 'paid_at']
        widgets = {
            'paid_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['message']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
