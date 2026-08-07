from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('teacher', 'Teacher'),
    ('student', 'Student'),
    ('owner', 'Owner'),
]

ATTENDANCE_STATUS = [
    ('present', 'Present'),
    ('absent', 'Absent'),
    ('late', 'Late'),
]

FEE_STATUS = [
    ('pending', 'Pending'),
    ('paid', 'Paid'),
]

LEAVE_STATUS = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    dob = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


class SchoolClass(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(Subject, blank=True, related_name='teachers')

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=50, unique=True)
    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.SET_NULL)
    bus = models.ForeignKey('Bus', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Note(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='notes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Syllabus(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    file = models.FileField(upload_to='syllabus/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject.name} syllabus"


class Timetable(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='timetables/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Bus(models.Model):
    route_name = models.CharField(max_length=200)
    stops = models.TextField(help_text='Comma-separated stops')

    def __str__(self):
        return self.route_name


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS)

    class Meta:
        unique_together = ('student', 'subject', 'date')

    def __str__(self):
        return f"{self.student} — {self.date} : {self.status}"


class LeaveRequest(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LEAVE_STATUS, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Leave request for {self.student}"


class Exam(models.Model):
    name = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return self.name


class Result(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ('exam', 'student')

    def __str__(self):
        return f"{self.student} — {self.exam.name}"


class FeePayment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=FEE_STATUS, default='pending')
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} — {self.status}"


class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.user.username}"
