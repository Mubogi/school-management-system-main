from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import marks_views
from . import report_workflow_views
from . import super_admin_views
from . import sync_views
from . import master_vendor_views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('student/<str:student_id>/', views.StudentProfileView.as_view(), name='student_profile'),

    # MASTER VENDOR ROUTES (Software Owner Only)
    path('master-vendor/', master_vendor_views.master_vendor_dashboard, name='master_vendor_dashboard'),
    path('system/license-status/', master_vendor_views.license_status_view, name='vendor_license_status'),
    path('system/license-status/apply/', master_vendor_views.apply_upgrade_key, name='vendor_apply_upgrade'),
    path('master-vendor/schools/', master_vendor_views.vendor_schools, name='vendor_schools'),
    path('master-vendor/schools/<int:school_id>/toggle/', master_vendor_views.toggle_school_status, name='vendor_toggle_school'),
    path('master-vendor/users/', master_vendor_views.vendor_users, name='vendor_users'),
    path('master-vendor/users/<int:user_id>/role/', master_vendor_views.update_user_role, name='vendor_update_user_role'),
    path('master-vendor/audit/', master_vendor_views.vendor_audit_log, name='vendor_audit_log'),
    path('master-vendor/feature-matrix/', master_vendor_views.vendor_feature_matrix, name='vendor_feature_matrix'),
    path('master-vendor/feature-matrix/generate/', master_vendor_views.generate_feature_matrix, name='vendor_generate_matrix'),
    path('master-vendor/backups/', master_vendor_views.vendor_backups, name='vendor_backups'),
    path('master-vendor/backups/create/', master_vendor_views.create_manual_backup, name='vendor_create_backup'),
    path('master-vendor/statistics/', master_vendor_views.vendor_statistics, name='vendor_statistics'),
    path('master-vendor/branding/', master_vendor_views.vendor_branding, name='vendor_branding'),
    path('master-vendor/branding/update/', master_vendor_views.update_vendor_branding, name='vendor_update_branding'),

    # DASHBOARDS
    path('super-admin/', views.SuperAdminDashboardView.as_view(), name='super_admin_dashboard'),
    path('super-admin/control/', super_admin_views.SuperAdminControlView.as_view(), name='super_admin_control'),
    path('super-admin/archived-reports/', super_admin_views.ArchivedTermReportsView.as_view(), name='archived_reports'),
    path('super-admin/export-backup/', super_admin_views.export_system_backup, name='export_system_backup'),
    path('super-admin/export-schoolhub/', super_admin_views.export_schoolhub_backup, name='export_schoolhub_backup'),
    path('super-admin/id-cards/', super_admin_views.student_id_cards_pdf, name='student_id_cards_pdf'),
    path('manifest.json', super_admin_views.pwa_manifest, name='pwa_manifest'),
    path('sw.js', super_admin_views.pwa_service_worker, name='pwa_service_worker'),
    path('api/offline-sync/', sync_views.offline_sync_upload, name='offline_sync_upload'),
    path('api/offline-sync/ping/', sync_views.offline_sync_ping, name='offline_sync_ping'),
    path('secretary/', views.SecretaryDashboardView.as_view(), name='secretary_dashboard'),
    path('bursar/', views.BursarDashboardView.as_view(), name='bursar_dashboard'),
    path('subject-teacher/', views.SubjectTeacherDashboardView.as_view(), name='subject_teacher_dashboard'),
    path('class-teacher/', views.ClassTeacherDashboardView.as_view(), name='class_teacher_dashboard'),
    path('dos/', views.DOSDashboardView.as_view(), name='dos_dashboard'),
    path('head-teacher/', views.HeadTeacherDashboardView.as_view(), name='head_teacher_dashboard'),

    # INTERNAL DASHBOARD ADMIN ROUTES
    path('dashboard/admin/schools/', views.AdminSchoolsView.as_view(), name='admin_schools'),
    path('dashboard/admin/staff/', views.AdminStaffView.as_view(), name='admin_staff'),
    path('dashboard/admin/classes/', views.AdminClassesView.as_view(), name='admin_classes'),
    path('dashboard/admin/subjects/', views.AdminSubjectsView.as_view(), name='admin_subjects'),
    path('dashboard/admin/assessments/', views.AdminAssessmentsView.as_view(), name='admin_assessments'),
    path('dashboard/admin/assignments/', views.AdminAssignmentsView.as_view(), name='admin_assignments'),
    path('dashboard/admin/fees/', views.AdminFeesView.as_view(), name='admin_fees'),
    
    # DATABASE MANAGEMENT & AUDIT
    path('super-admin/database/', super_admin_views.DatabaseManagementView.as_view(), name='database_management'),
    path('super-admin/backup/create/', super_admin_views.create_instant_backup, name='create_backup'),
    path('super-admin/backup/download/<str:backup_name>/', super_admin_views.download_backup, name='download_backup'),
    path('super-admin/sessions/', super_admin_views.SessionManagementView.as_view(), name='session_management'),
    path('super-admin/sessions/terminate/<str:session_key>/', super_admin_views.terminate_session, name='terminate_session'),
    path('super-admin/sessions/terminate-all/', super_admin_views.terminate_all_sessions, name='terminate_all_sessions'),
    path('super-admin/audit/', super_admin_views.AuditLogView.as_view(), name='audit_log'),

    # HEAD TEACHER ROUTES
    path('head-teacher/students/', views.HeadTeacherStudentsView.as_view(), name='head_teacher_students'),
    path('head-teacher/classes/', views.HeadTeacherClassesView.as_view(), name='head_teacher_classes'),
    path('head-teacher/reports/', views.HeadTeacherReportsView.as_view(), name='head_teacher_reports'),

    # CLASS TEACHER ROUTES
    path('class-teacher/students/', views.ClassTeacherStudentsView.as_view(), name='class_teacher_students'),
    path('class-teacher/marks/', views.ClassTeacherMarksView.as_view(), name='class_teacher_marks'),
    path('class-teacher/performance/', views.ClassTeacherPerformanceView.as_view(), name='class_teacher_performance'),
    path('class-teacher/reports/', views.ClassTeacherReportsView.as_view(), name='class_teacher_reports'),

    # SUBJECT TEACHER ROUTES
    path('subject-teacher/marks/', views.SubjectTeacherMarksView.as_view(), name='subject_teacher_marks'),
    path('subject-teacher/reports/', views.SubjectTeacherReportsView.as_view(), name='subject_teacher_reports'),

    # BURSAR ROUTES
    path('bursar/fees/', views.BursarFeesView.as_view(), name='bursar_fees'),
    path('bursar/payments/', views.BursarPaymentsView.as_view(), name='bursar_payments'),
    path('bursar/receipts/', views.BursarReceiptsView.as_view(), name='bursar_receipts'),
    path('bursar/balances/', views.BursarBalancesView.as_view(), name='bursar_balances'),
    path('bursar/reports/', views.BursarReportsView.as_view(), name='bursar_reports'),
    path('bursar/term-workflow/', views.BursarTermWorkflowView.as_view(), name='bursar_term_workflow'),

    # SECRETARY ROUTES
    path('secretary/students/', views.SecretaryStudentsView.as_view(), name='secretary_students'),
    path('secretary/enroll/', views.SecretaryEnrollView.as_view(), name='secretary_enroll'),
    path('secretary/marks/', views.SecretaryMarksView.as_view(), name='secretary_marks'),
    path('secretary/payments/', views.SecretaryPaymentsView.as_view(), name='secretary_payments'),

    # DOS ROUTES
    path('dos/students/', views.DOSStudentsView.as_view(), name='dos_students'),
    path('dos/classes/', views.DOSClassesView.as_view(), name='dos_classes'),
    path('dos/reports/', views.DOSReportsView.as_view(), name='dos_reports'),

    # COMMON ROUTES
    path('search/students/', views.SearchStudentsView.as_view(), name='search_students'),
    path('receipt/<str:receipt_id>/', views.receipt_view, name='receipt_view'),
    path('mark-entry/', views.mark_entry_view, name='mark_entry'),
    # MARKS BULK/CSV
    path('marks/bulk/', marks_views.MarksBulkEntryView.as_view(), name='marks_bulk_entry'),
    path('marks/csv/download/', marks_views.marks_csv_download, name='marks_csv_download'),
    path('marks/csv/upload/', marks_views.marks_csv_upload, name='marks_csv_upload'),

    # REPORT/PUBLISH WORKFLOW
    path('head-teacher/publish/', report_workflow_views.HeadTeacherPublishReportsView.as_view(), name='head_teacher_publish'),
    path('class-teacher/remarks/', report_workflow_views.ClassTeacherRemarksView.as_view(), name='class_teacher_remarks'),
    path('reports/notifications/', report_workflow_views.ReportNotificationsView.as_view(), name='report_notifications'),
    path('dos/promotion-rules/', report_workflow_views.PromotionRulesView.as_view(), name='promotion_rules'),
    path('dos/year-end-promotion/', report_workflow_views.YearEndPromotionView.as_view(), name='year_end_promotion'),
    path('dos/bulk-promotion/', report_workflow_views.BulkStudentPromotionView.as_view(), name='bulk_promotion'),

    # PDFs
    path('pdf/report/<str:student_id>/', views.student_report_pdf, name='student_report_pdf'),
    path('pdf/report/<str:student_id>/<str:report_type>/', views.student_report_pdf_typed, name='student_report_pdf_typed'),
    path('pdf/class-report/<str:class_name>/<str:report_type>/', views.class_term_reports_pdf_typed, name='class_term_reports_pdf_typed'),
    path('pdf/broadsheet/<str:class_name>/', views.class_broadsheet_pdf, name='class_broadsheet_pdf'),
    path('pdf/subject/<int:subject_id>/', views.subject_performance_pdf, name='subject_performance_pdf'),
    path('pdf/assessment/<int:assessment_id>/', views.assessment_report_pdf, name='assessment_report_pdf'),
    path('pdf/receipt/<str:receipt_id>/', views.receipt_pdf, name='receipt_pdf'),
    path('pdf/financial-statement/<str:student_id>/', views.student_financial_statement_pdf, name='student_financial_statement_pdf'),
    path('pdf/demand-letter/<str:student_id>/', views.bursar_demand_letter_pdf, name='bursar_demand_letter_pdf'),
    path('pdf/fee-report/', views.bursar_fee_report_pdf, name='bursar_fee_report_pdf'),
    path('pdf/cleared-students/', views.bursar_clearance_list_pdf, name='bursar_clearance_list_pdf'),
    path('pdf/outstanding-students/', views.bursar_outstanding_list_pdf, name='bursar_outstanding_list_pdf'),
    path('pdf/clearance/<str:student_id>/', views.student_clearance_pdf, name='student_clearance_pdf'),
    
    # QR CODE FOR MOBILE/LAN ACCESS
    path('qr-connect/', views.QRCodeConnectView.as_view(), name='qr_connect'),
    path('qr-connect/image/', views.qr_code_image, name='qr_connect_image'),
    
    # TERMLY RETURN CHECKER
    path('dos/termly-return/', report_workflow_views.TermlyReturnCheckerView.as_view(), name='termly_return_checker'),
    
    # BATCH ID CARDS
    path('dos/batch-id-cards/', report_workflow_views.batch_id_card_generator, name='batch_id_cards'),
    path('dos/id-card/<str:student_id>/', report_workflow_views.print_id_card, name='print_id_card'),
    
    # PARENT KIOSK PORTAL (PUBLIC)
    path('parent-kiosk/', views.parent_kiosk_view, name='parent_kiosk'),
    path('parent-kiosk/login/', views.parent_kiosk_login, name='parent_kiosk_login'),
    path('api/parent-student/', views.api_get_parent_student, name='api_parent_student'),
]
