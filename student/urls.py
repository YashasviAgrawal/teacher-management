from django.urls import path

from .views import (
    # Module 14 — Student Management
    StudentListCreateView,
    StudentDetailView,
    StudentProfileView,
    # Module 15 — Enrollment & Promotion
    StudentEnrollmentView,
    EnrollmentDetailView,
    SectionRosterView,
    BulkPromoteView,
    # Module 16 — Student Attendance
    AttendanceMarkView,
    AttendanceBulkMarkView,
    StudentAttendanceHistoryView,
    SectionAttendanceView,
    AttendanceDetailView,
    # Module 18 — Marks Entry
    StudentMarksHistoryView,
    # Module 19 — Performance Notes
    StudentPerformanceNoteListCreateView,
    # Module 20 — Success Manager & Analytics
    StudentAnalysisView,
    StudentGrowthView,
    SectionAnalysisView,
    StudentSuccessNoteListCreateView,
)

urlpatterns = [
    # ──────────────────────────────────────────────────────────────────────────
    # Module 14 — Student Management
    # ──────────────────────────────────────────────────────────────────────────

    # POST /api/v1/students/         — Create student       (Admin)
    # GET  /api/v1/students/         — List / search        (All roles, Teacher: assigned only)
    path('', StudentListCreateView.as_view(), name='student-list-create'),

    # GET    /api/v1/students/{id}/  — Single student detail (All roles, Teacher: assigned only)
    # PATCH  /api/v1/students/{id}/  — Update student        (Admin)
    # DELETE /api/v1/students/{id}/  — Soft-delete student   (Admin)
    path('<uuid:pk>/', StudentDetailView.as_view(), name='student-detail'),

    # GET /api/v1/students/{id}/profile/ — Full 360° profile (Admin + Success Mgr)
    path('<uuid:pk>/profile/', StudentProfileView.as_view(), name='student-profile'),

    # ──────────────────────────────────────────────────────────────────────────
    # Module 15 — Enrollment & Promotion
    # ──────────────────────────────────────────────────────────────────────────

    # POST /api/v1/students/{id}/enrollments/ — Enroll student into class+section (Admin)
    # GET  /api/v1/students/{id}/enrollments/ — Full enrollment history           (Admin + SM)
    path('<uuid:pk>/enrollments/', StudentEnrollmentView.as_view(), name='student-enrollments'),

    # PATCH /api/v1/students/enrollments/{id}/ — Correct or change an enrollment  (Admin)
    path('enrollments/<uuid:pk>/', EnrollmentDetailView.as_view(), name='enrollment-detail'),

    # GET /api/v1/students/sections/{id}/students/ — Section roster               (All Roles)
    path('sections/<uuid:pk>/students/', SectionRosterView.as_view(), name='section-roster'),

    # POST /api/v1/students/enrollments/promote/ — Bulk year-end promotion        (Admin)
    path('enrollments/promote/', BulkPromoteView.as_view(), name='enrollment-promote'),

    # ──────────────────────────────────────────────────────────────────────────
    # Module 16 — Student Attendance
    # ──────────────────────────────────────────────────────────────────────────

    # POST /api/v1/students/attendance/       — Mark single attendance  (Admin + Teacher)
    path('attendance/', AttendanceMarkView.as_view(), name='attendance-mark'),

    # POST /api/v1/students/attendance/bulk/  — Bulk mark a section     (Admin + Teacher)
    path('attendance/bulk/', AttendanceBulkMarkView.as_view(), name='attendance-bulk-mark'),

    # PATCH /api/v1/students/attendance/{id}/ — Correct attendance      (Admin Only)
    path('attendance/<uuid:pk>/', AttendanceDetailView.as_view(), name='attendance-detail'),

    # GET /api/v1/students/{id}/attendance/   — Student attendance history (All Roles)
    path('<uuid:pk>/attendance/', StudentAttendanceHistoryView.as_view(), name='student-attendance-history'),

    # GET /api/v1/students/sections/{id}/attendance/ — Section attendance for a date (Admin + SM)
    path('sections/<uuid:pk>/attendance/', SectionAttendanceView.as_view(), name='section-attendance'),

    # GET /api/v1/students/{id}/marks/        — Student marks history (All Roles)
    path('<uuid:student_pk>/marks/', StudentMarksHistoryView.as_view(), name='student-marks-history'),

    # POST /api/v1/students/{id}/performance-notes/ — Add a performance note (Admin + Teacher: own subject)
    # GET  /api/v1/students/{id}/performance-notes/ — List a student's performance notes (All Roles)
    path('<uuid:pk>/performance-notes/', StudentPerformanceNoteListCreateView.as_view(), name='student-performance-notes'),

    # ──────────────────────────────────────────────────────────────────────────
    # Module 20 — Success Manager & Analytics
    # ──────────────────────────────────────────────────────────────────────────

    # GET /api/v1/students/{id}/analysis/ — Subject-wise strengths & weaknesses (Admin + SM)
    path('<uuid:pk>/analysis/', StudentAnalysisView.as_view(), name='student-analysis'),

    # GET /api/v1/students/{id}/growth/ — Exam-over-exam growth trend (Admin + SM)
    path('<uuid:pk>/growth/', StudentGrowthView.as_view(), name='student-growth'),

    # GET /api/v1/students/sections/{id}/analysis/ — Section performance overview (Admin + SM)
    path('sections/<uuid:pk>/analysis/', SectionAnalysisView.as_view(), name='section-analysis'),

    # POST /api/v1/students/{id}/success-notes/ — Add intervention / flag note (Admin + SM)
    # GET  /api/v1/students/{id}/success-notes/ — List student's success notes (Admin + SM)
    path('<uuid:pk>/success-notes/', StudentSuccessNoteListCreateView.as_view(), name='student-success-notes'),
]

