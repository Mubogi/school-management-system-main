from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .forms import (
    AttendanceForm,
    ClassForm,
    ExamForm,
    FeePaymentForm,
    FeedbackForm,
    LeaveRequestForm,
    LoginForm,
    NoteForm,
    NoticeForm,
    StudentForm,
    SubjectForm,
    SyllabusForm,
    TeacherForm,
    TimetableForm,
    BusForm,
)
from .models import (
    Attendance,
    Exam,
    FeePayment,
    Feedback,
    LeaveRequest,
    Note,
    Notice,
    SchoolClass,
    Subject,
    Syllabus,
    Teacher,
    Timetable,
    Student,
    Bus,
)


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'school/index.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'school/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    counts = {
        'notices': Notice.objects.count(),
        'notes': Note.objects.count(),
        'syllabi': Syllabus.objects.count(),
        'timetables': Timetable.objects.count(),
        'subjects': Subject.objects.count(),
        'classes': SchoolClass.objects.count(),
        'teachers': Teacher.objects.count(),
        'students': Student.objects.count(),
        'buses': Bus.objects.count(),
        'attendance': Attendance.objects.count(),
        'exams': Exam.objects.count(),
        'results': Result.objects.count(),
        'fees': FeePayment.objects.count(),
        'leaves': LeaveRequest.objects.count(),
        'feedback': Feedback.objects.count(),
    }
    return render(request, 'school/dashboard.html', {'counts': counts})


@login_required
def notice_list(request):
    notices = Notice.objects.order_by('-created_at')
    return render(request, 'school/notice_list.html', {'notices': notices})


@login_required
def notice_create(request):
    form = NoticeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('notice_list')
    return render(request, 'school/notice_form.html', {'form': form})


@login_required
def note_list(request):
    notes = Note.objects.order_by('-uploaded_at')
    return render(request, 'school/note_list.html', {'notes': notes})


@login_required
def note_create(request):
    form = NoteForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('note_list')
    return render(request, 'school/note_form.html', {'form': form})


@login_required
def syllabus_list(request):
    syllabi = Syllabus.objects.order_by('-uploaded_at')
    return render(request, 'school/syllabus_list.html', {'syllabi': syllabi})


@login_required
def syllabus_create(request):
    form = SyllabusForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('syllabus_list')
    return render(request, 'school/syllabus_form.html', {'form': form})


@login_required
def timetable_list(request):
    timetables = Timetable.objects.order_by('-uploaded_at')
    return render(request, 'school/timetable_list.html', {'timetables': timetables})


@login_required
def timetable_create(request):
    form = TimetableForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('timetable_list')
    return render(request, 'school/timetable_form.html', {'form': form})


@login_required
def subject_list(request):
    subjects = Subject.objects.order_by('name')
    return render(request, 'school/subject_list.html', {'subjects': subjects})


@login_required
def subject_create(request):
    form = SubjectForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('subject_list')
    return render(request, 'school/subject_form.html', {'form': form})


@login_required
def class_list(request):
    classes = SchoolClass.objects.order_by('name')
    return render(request, 'school/class_list.html', {'classes': classes})


@login_required
def class_create(request):
    form = ClassForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('class_list')
    return render(request, 'school/class_form.html', {'form': form})


@login_required
def teacher_list(request):
    teachers = Teacher.objects.select_related('user').order_by('user__username')
    return render(request, 'school/teacher_list.html', {'teachers': teachers})


@login_required
def teacher_create(request):
    form = TeacherForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('teacher_list')
    return render(request, 'school/teacher_form.html', {'form': form})


@login_required
def student_list(request):
    students = Student.objects.select_related('user', 'school_class', 'bus').order_by('roll_number')
    return render(request, 'school/student_list.html', {'students': students})


@login_required
def student_create(request):
    form = StudentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('student_list')
    return render(request, 'school/student_form.html', {'form': form})


@login_required
def bus_list(request):
    buses = Bus.objects.order_by('route_name')
    return render(request, 'school/bus_list.html', {'buses': buses})


@login_required
def bus_create(request):
    form = BusForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('bus_list')
    return render(request, 'school/bus_form.html', {'form': form})


@login_required
def attendance_list(request):
    attendance = Attendance.objects.order_by('-date')
    return render(request, 'school/attendance_list.html', {'attendance': attendance})


@login_required
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('attendance_list')
    return render(request, 'school/attendance_form.html', {'form': form})


@login_required
def leave_list(request):
    leaves = LeaveRequest.objects.order_by('-requested_at')
    return render(request, 'school/leave_list.html', {'leaves': leaves})


@login_required
def leave_create(request):
    form = LeaveRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('leave_list')
    return render(request, 'school/leave_form.html', {'form': form})


@login_required
def exam_list(request):
    exams = Exam.objects.order_by('-date')
    return render(request, 'school/exam_list.html', {'exams': exams})


@login_required
def exam_create(request):
    form = ExamForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('exam_list')
    return render(request, 'school/exam_form.html', {'form': form})


@login_required
def result_list(request):
    results = Result.objects.order_by('exam__date')
    return render(request, 'school/result_list.html', {'results': results})


@login_required
def result_create(request):
    form = ResultForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('result_list')
    return render(request, 'school/result_form.html', {'form': form})


@login_required
def fee_list(request):
    fees = FeePayment.objects.order_by('-paid_at')
    return render(request, 'school/fee_list.html', {'fees': fees})


@login_required
def fee_create(request):
    form = FeePaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('fee_list')
    return render(request, 'school/fee_form.html', {'form': form})


@login_required
def feedback_list(request):
    feedback = Feedback.objects.order_by('-submitted_at')
    return render(request, 'school/feedback_list.html', {'feedback': feedback})


@login_required
def feedback_create(request):
    form = FeedbackForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        feedback = form.save(commit=False)
        feedback.user = request.user
        feedback.save()
        return redirect('feedback_list')
    return render(request, 'school/feedback_form.html', {'form': form})
