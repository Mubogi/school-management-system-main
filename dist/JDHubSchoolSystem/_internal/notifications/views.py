"""
WhatsApp Queue and Notification Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.urls import reverse
from urllib.parse import quote, urlencode

from core.models import Student
from core.views import RoleRequiredMixin, get_profile, get_user_school

from .models import WhatsAppMessage, NotificationTemplate, NotificationBatch


def format_whatsapp_link(phone: str, message: str) -> str:
    """
    Format a WhatsApp URL with pre-filled message.
    Phone should be in international format (without + or spaces).
    """
    # Clean phone number
    clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    if not clean_phone.startswith('+'):
        clean_phone = '+' + clean_phone
    
    # Encode message
    encoded_message = quote(message)
    
    # Format URL (wa.me format)
    return f"https://wa.me/{clean_phone[1:]}?text={encoded_message}"


@login_required
@require_http_methods(["GET", "POST"])
def whatsapp_queue_view(request):
    """
    WhatsApp Queue Dispatcher view.
    Allows staff to select students and generate WhatsApp links.
    """
    profile = get_profile(request.user)
    school = get_user_school(profile)
    
    if not school:
        messages.error(request, 'No school associated with your account.')
        return redirect('core:dashboard')
    
    context = {
        'school': school,
        'user_role': profile.role if profile else '',
    }
    
    # Get available templates
    context['templates'] = NotificationTemplate.objects.filter(is_active=True)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate_queue':
            # Get selected students
            student_ids = request.POST.getlist('student_ids')
            message_type = request.POST.get('message_type', 'GENERAL')
            custom_message = request.POST.get('custom_message', '').strip()
            template_id = request.POST.get('template_id')
            
            if not student_ids:
                messages.error(request, 'Please select at least one student.')
                return render(request, 'notifications/whatsapp_queue.html', context)
            
            # Get template if selected
            template_content = ''
            if template_id:
                try:
                    template = NotificationTemplate.objects.get(id=template_id)
                    template_content = template.template_content
                except NotificationTemplate.DoesNotExist:
                    pass
            
            # Process students
            queue_items = []
            errors = []
            
            for sid in student_ids:
                try:
                    student = Student.objects.get(id=sid, school=school)
                    
                    # Get parent info
                    parent_phone = student.guardian_phone
                    parent_name = student.guardian_name or 'Parent'
                    
                    if not parent_phone:
                        errors.append(f"{student.student_id}: No parent phone")
                        continue
                    
                    # Build message
                    if template_content:
                        message = template_content.format(
                            student_name=f"{student.first_name} {student.last_name}",
                            guardian_name=parent_name,
                            class_name=student.current_class,
                            student_id=student.student_id,
                            school_name=school.school_name,
                            academic_year=school.active_academic_year,
                            term=school.active_term,
                        )
                    elif custom_message:
                        message = custom_message.format(
                            student_name=f"{student.first_name} {student.last_name}",
                            guardian_name=parent_name,
                            class_name=student.current_class,
                            student_id=student.student_id,
                            school_name=school.school_name,
                            academic_year=school.active_academic_year,
                            term=school.active_term,
                        )
                    else:
                        message = f"Dear {parent_name},\n\nYour child {student.first_name} {student.last_name} ({student.student_id}) requires your attention.\n\nBest regards,\n{school.school_name}"
                    
                    # Generate WhatsApp link
                    wa_link = format_whatsapp_link(parent_phone, message)
                    
                    # Create queue item
                    queue_items.append({
                        'id': sid,
                        'student': student,
                        'parent_phone': parent_phone,
                        'parent_name': parent_name,
                        'message': message,
                        'wa_link': wa_link,
                    })
                    
                except Student.DoesNotExist:
                    errors.append(f"Student ID {sid} not found")
            
            context['queue_items'] = queue_items
            context['errors'] = errors
            context['message_type'] = message_type
            context['custom_message'] = custom_message
            
            # Save queue if there are items
            if queue_items:
                batch = NotificationBatch.objects.create(
                    name=f"WhatsApp - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    channel='WHATSAPP',
                    template_id=template_id,
                    student_count=len(queue_items),
                    created_by=request.user
                )
                context['batch_id'] = batch.id
        
        elif action == 'mark_sent':
            # Mark individual message as sent
            student_id = request.POST.get('student_id')
            
            try:
                student = Student.objects.get(id=student_id, school=school)
                msg = WhatsAppMessage.objects.filter(
                    student=student,
                    status='QUEUED'
                ).first()
                
                if msg:
                    msg.mark_as_sent()
                    return JsonResponse({'success': True, 'student_id': student_id})
                
            except Student.DoesNotExist:
                pass
            
            return JsonResponse({'success': False})
        
        elif action == 'mark_all_sent':
            # Mark all in batch as sent
            batch_id = request.POST.get('batch_id')
            
            if batch_id:
                try:
                    batch = NotificationBatch.objects.get(id=batch_id, created_by=request.user)
                    messages = WhatsAppMessage.objects.filter(
                        student__school=school,
                        status='QUEUED',
                        created_at__gte=batch.created_at
                    )
                    
                    for msg in messages:
                        msg.mark_as_sent()
                    
                    batch.sent_count = messages.count()
                    batch.status = 'COMPLETED'
                    batch.completed_at = timezone.now()
                    batch.save()
                    
                    messages.success(request, f'{messages.count()} messages marked as sent.')
                    
                except NotificationBatch.DoesNotExist:
                    messages.error(request, 'Batch not found.')
            else:
                messages.error(request, 'Invalid batch ID.')
    
    # Get students for selection
    students = Student.objects.filter(
        school=school,
        is_active=True,
        guardian_phone__isnull=False
    ).exclude(guardian_phone='').order_by('current_class', 'last_name')
    
    # Group by class
    students_by_class = {}
    for student in students:
        class_name = student.current_class or 'Unassigned'
        if class_name not in students_by_class:
            students_by_class[class_name] = []
        students_by_class[class_name].append(student)
    
    context['students_by_class'] = students_by_class
    context['total_with_phone'] = students.count()
    
    return render(request, 'notifications/whatsapp_queue.html', context)


@login_required
def whatsapp_preview(request):
    """
    Preview a WhatsApp message before sending.
    """
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        message = request.POST.get('message', '')
        
        try:
            student = Student.objects.get(id=student_id)
            phone = student.guardian_phone or ''
            
            if phone:
                wa_link = format_whatsapp_link(phone, message)
                return JsonResponse({
                    'success': True,
                    'wa_link': wa_link,
                    'phone': phone,
                    'message_preview': message[:100] + '...' if len(message) > 100 else message
                })
            
            return JsonResponse({'success': False, 'error': 'No phone number'})
            
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def email_queue_view(request):
    """
    Email Queue view for bulk email sending.
    """
    profile = get_profile(request.user)
    school = get_user_school(profile)
    
    if not school:
        messages.error(request, 'No school associated with your account.')
        return redirect('core:dashboard')
    
    context = {
        'school': school,
        'user_role': profile.role if profile else '',
        'templates': NotificationTemplate.objects.filter(is_active=True),
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'preview':
            student_ids = request.POST.getlist('student_ids')
            students = Student.objects.filter(
                id__in=student_ids,
                school=school,
                guardian_email__isnull=False
            ).exclude(guardian_email='')
            
            context['preview_students'] = list(students)
            context['preview_count'] = students.count()
        
        elif action == 'send_emails':
            from utils.email_dispatcher import send_bulk_individual_emails, get_email_template_context
            from django.template.loader import render_to_string
            
            student_ids = request.POST.getlist('student_ids')
            subject = request.POST.get('subject', f'Report Card from {school.school_name}')
            message = request.POST.get('message', '')
            template_id = request.POST.get('template_id')
            
            # Get template if selected
            template_content = message
            if template_id:
                try:
                    template = NotificationTemplate.objects.get(id=template_id)
                    template_content = template.template_content
                except NotificationTemplate.DoesNotExist:
                    pass
            
            students = Student.objects.filter(
                id__in=student_ids,
                school=school,
                guardian_email__isnull=False
            ).exclude(guardian_email='')
            
            def email_template_func(student):
                ctx = get_email_template_context(student)
                html = render_to_string('notifications/generic_email.html', ctx)
                text = strip_tags(html)
                return (text, html, student.guardian_email)
            
            results = send_bulk_individual_emails(
                subject=subject,
                template_body_func=email_template_func,
                student_queryset=students
            )
            
            messages.success(
                request, 
                f"Email batch complete: {results['sent']}/{results['total']} sent successfully."
            )
            
            if results['errors']:
                for error in results['errors'][:5]:
                    messages.warning(request, error)
    
    # Get students for selection
    students = Student.objects.filter(
        school=school,
        is_active=True,
        guardian_email__isnull=False
    ).exclude(guardian_email='').order_by('current_class', 'last_name')
    
    students_by_class = {}
    for student in students:
        class_name = student.current_class or 'Unassigned'
        if class_name not in students_by_class:
            students_by_class[class_name] = []
        students_by_class[class_name].append(student)
    
    context['students_by_class'] = students_by_class
    context['total_with_email'] = students.count()
    
    return render(request, 'notifications/email_queue.html', context)


from django.utils.html import strip_tags


@login_required
def notification_templates_view(request):
    """
    Manage notification templates.
    """
    profile = get_profile(request.user)
    school = get_user_school(profile)
    
    context = {
        'school': school,
        'templates': NotificationTemplate.objects.all(),
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name', '').strip()
            message_type = request.POST.get('message_type', 'GENERAL')
            subject = request.POST.get('subject', '')
            content = request.POST.get('template_content', '').strip()
            
            if name and content:
                NotificationTemplate.objects.create(
                    name=name,
                    message_type=message_type,
                    subject=subject,
                    template_content=content
                )
                messages.success(request, f'Template "{name}" created.')
            else:
                messages.error(request, 'Name and content are required.')
        
        elif action == 'delete':
            template_id = request.POST.get('template_id')
            try:
                template = NotificationTemplate.objects.get(id=template_id)
                template.delete()
                messages.success(request, 'Template deleted.')
            except NotificationTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
    
    return render(request, 'notifications/templates.html', context)
