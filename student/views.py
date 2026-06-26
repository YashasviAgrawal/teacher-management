import decimal

from django.db import transaction
from django.db.models import Q, Avg, Sum, Count, F, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app1.models import AcademicYear, Section, TeacherAssignment, Subject
from app1.permissions import IsAdmin, IsTeacher, IsSuccessManager
from .models import (
    Exam,
    ExamMark,
    ExamSubject,
    GradingScheme,
    Student,
    StudentAttendance,
    StudentEnrollment,
    StudentPerformanceNote,
    StudentSuccessNote,
)
from .serializers import (
    ExamSerializer,
    ExamListSerializer,
    ExamSubjectSerializer,
    ExamMarkSerializer,
    ExamMarkListSerializer,
    StudentAttendanceSerializer,
    StudentAttendanceListSerializer,
    StudentEnrollmentSerializer,
    StudentEnrollmentListSerializer,
    StudentListSerializer,
    StudentSerializer,
    StudentPerformanceNoteSerializer,
    StudentPerformanceNoteListSerializer,
    StudentSuccessNoteSerializer,
    StudentSuccessNoteListSerializer,
)


class StudentListCreateView(APIView):
    """
    POST /api/v1/students/ — Create a new student (Admin only).
    GET  /api/v1/students/ — List / search / filter students (Admin + Success Manager see all, Teacher sees assigned only).
    """
    
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def post(self, request):
        serializer = StudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        user = request.user
        
        # Scoping based on user role
        if user.role in ["admin", "success_manager"]:
            queryset = Student.objects.filter(is_active=True)
        elif user.role == "teacher":
            from app1.models import TeacherAssignment, AcademicYear
            current_year = AcademicYear.objects.filter(is_current=True).first()
            
            assignments = TeacherAssignment.objects.filter(teacher=user, is_active=True)
            if current_year:
                assignments = assignments.filter(academic_year=current_year)
                
            assigned_pairs = list(assignments.values_list("class_id", "section"))
            if not assigned_pairs:
                queryset = Student.objects.none()
            else:
                pair_queries = Q()
                for class_id, section_id in assigned_pairs:
                    pair_queries |= Q(class_id=class_id, section=section_id)
                
                enrollments = StudentEnrollment.objects.filter(pair_queries)
                if current_year:
                    enrollments = enrollments.filter(academic_year=current_year)
                    
                student_ids = enrollments.values_list("student_id", flat=True)
                queryset = Student.objects.filter(id__in=student_ids, is_active=True)
        else:
            queryset = Student.objects.none()

        # Apply search filter
        search_query = request.query_params.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(admission_number__icontains=search_query)
            )

        # Apply class_id, section_id, and status filter
        class_id = request.query_params.get("class_id")
        section_id = request.query_params.get("section_id")
        status_filter = request.query_params.get("status")

        if class_id or section_id:
            from app1.models import AcademicYear
            current_year = AcademicYear.objects.filter(is_current=True).first()
            
            enrollment_filter = Q()
            if class_id:
                enrollment_filter &= Q(class_id=class_id)
            if section_id:
                enrollment_filter &= Q(section=section_id)
            if current_year:
                enrollment_filter &= Q(academic_year=current_year)
                
            matching_student_ids = StudentEnrollment.objects.filter(enrollment_filter).values_list("student_id", flat=True)
            queryset = queryset.filter(id__in=matching_student_ids)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        queryset = queryset.prefetch_related("enrollments", "enrollments__class_id", "enrollments__section").order_by("full_name")
        serializer = StudentListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentDetailView(APIView):
    """
    GET   /api/v1/students/{id}/ — Single student details (All roles, Teacher: assigned only).
    PATCH /api/v1/students/{id}/ — Update student details (Admin only).
    DELETE /api/v1/students/{id}/ — Soft delete student (Admin only).
    """

    def get_permissions(self):
        if self.request.method in ["PATCH", "DELETE"]:
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_object(self, pk):
        try:
            return Student.objects.get(pk=pk)
        except (Student.DoesNotExist, ValueError):
            return None

    def check_teacher_access(self, user, student):
        if user.role != "teacher":
            return True
        from app1.models import TeacherAssignment, AcademicYear
        current_year = AcademicYear.objects.filter(is_current=True).first()
        
        enrollments = student.enrollments.all()
        if current_year:
            enrollments = enrollments.filter(academic_year=current_year)
            
        if not enrollments.exists():
            return False
            
        for enrollment in enrollments:
            has_assignment = TeacherAssignment.objects.filter(
                teacher=user,
                class_id=enrollment.class_id,
                section=enrollment.section,
                is_active=True
            )
            if current_year:
                has_assignment = has_assignment.filter(academic_year=current_year)
            if has_assignment.exists():
                return True
        return False

    def get(self, request, pk):
        student = self.get_object(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        if not self.check_teacher_access(request.user, student):
            return Response(
                {"error": "You do not have permission to view this student."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = StudentSerializer(student)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        student = self.get_object(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudentSerializer(student, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        student = self.get_object(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        student.is_active = False
        student.status = Student.Status.INACTIVE
        student.save(update_fields=["is_active", "status"])
        return Response(
            {"message": f'Student "{student.full_name}" has been successfully deactivated.'},
            status=status.HTTP_200_OK
        )


class StudentProfileView(APIView):
    """
    GET /api/v1/students/{id}/profile/ — Full 360° profile (Admin + Success Manager).
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request, pk):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to view the student profile."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            student = Student.objects.get(pk=pk)
        except (Student.DoesNotExist, ValueError):
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Info
        student_data = StudentSerializer(student).data

        # 2. Current Enrollment
        from app1.models import AcademicYear
        current_year = AcademicYear.objects.filter(is_current=True).first()
        
        enrollment = student.enrollments.all()
        if current_year:
            enrollment = enrollment.filter(academic_year=current_year, status="active").first()
        else:
            enrollment = enrollment.first()
            
        current_enrollment_data = None
        if enrollment:
            current_enrollment_data = {
                "class_id": str(enrollment.class_id.id),
                "class_name": enrollment.class_id.name,
                "section_id": str(enrollment.section.id),
                "section_name": enrollment.section.name,
                "roll_number": enrollment.roll_number,
                "academic_year": enrollment.academic_year.name,
                "status": enrollment.status,
                "enrolled_on": enrollment.enrolled_on
            }

        # 3. Enrollment History
        enrollment_history = []
        for e in student.enrollments.all().select_related("class_id", "section", "academic_year"):
            enrollment_history.append({
                "class_id": str(e.class_id.id),
                "class_name": e.class_id.name,
                "section_id": str(e.section.id),
                "section_name": e.section.name,
                "roll_number": e.roll_number,
                "academic_year": e.academic_year.name,
                "status": e.status,
                "enrolled_on": e.enrolled_on
            })

        # 4. Attendance Summary & History
        attendance_qs = student.attendance_records.all()
        present_count = attendance_qs.filter(status="present").count()
        absent_count = attendance_qs.filter(status="absent").count()
        late_count = attendance_qs.filter(status="late").count()
        total_days = present_count + absent_count + late_count
        
        attendance_rate = 100.0
        if total_days > 0:
            attendance_rate = round(((present_count + late_count) / total_days) * 100, 2)
            
        recent_attendance = [
            {
                "date": att.date,
                "status": att.status,
                "reason": att.reason
            }
            for att in attendance_qs[:30]
        ]

        # 5. Exam Marks (only published ones)
        marks_qs = ExamMark.objects.filter(student=student, entry_status="published").select_related(
            "exam_subject__exam", "exam_subject__subject"
        )
        exam_marks = [
            {
                "exam_name": m.exam_subject.exam.name,
                "subject_name": m.exam_subject.subject.name,
                "marks_obtained": float(m.marks_obtained) if m.marks_obtained is not None else None,
                "max_marks": float(m.exam_subject.max_marks),
                "pass_marks": float(m.exam_subject.pass_marks),
                "grade": m.grade,
                "is_absent": m.is_absent,
                "remarks": m.remarks
            }
            for m in marks_qs
        ]

        # 6. Performance Notes
        notes_qs = StudentPerformanceNote.objects.filter(student=student).select_related(
            "subject", "teacher", "exam"
        ).order_by("-created_at")
        performance_notes = [
            {
                "note_type": n.note_type,
                "note_text": n.note_text,
                "subject_name": n.subject.name if n.subject else None,
                "exam_name": n.exam.name if n.exam else None,
                "teacher_name": n.teacher.full_name,
                "created_at": n.created_at
            }
            for n in notes_qs
        ]

        # 7. Success Notes
        success_qs = StudentSuccessNote.objects.filter(student=student).select_related(
            "success_manager"
        ).order_by("-created_at")
        success_notes = [
            {
                "category": s.category,
                "severity": s.severity,
                "title": s.title,
                "note_text": s.note_text,
                "follow_up_date": s.follow_up_date,
                "status": s.status,
                "success_manager_name": s.success_manager.full_name,
                "created_at": s.created_at
            }
            for s in success_qs
        ]

        return Response({
            "student": student_data,
            "current_enrollment": current_enrollment_data,
            "enrollment_history": enrollment_history,
            "attendance_summary": {
                "present_count": present_count,
                "absent_count": absent_count,
                "late_count": late_count,
                "total_days": total_days,
                "attendance_rate_percent": attendance_rate
            },
            "recent_attendance": recent_attendance,
            "exam_marks": exam_marks,
            "performance_notes": performance_notes,
            "success_notes": success_notes
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 15 — Enrollment & Promotion
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/students/{id}/enrollments/ — Enroll student        (Admin Only)
# GET  /api/v1/students/{id}/enrollments/ — Enrollment history    (Admin + Success Mgr)
# ──────────────────────────────────────────────────────────────────────────────

class StudentEnrollmentView(APIView):
    """
    POST — Admin enrolls a student into a class + section for an academic year.
    GET  — Admin / Success Manager views the full enrollment history of a student.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_student(self, pk):
        try:
            return Student.objects.get(pk=pk)
        except (Student.DoesNotExist, ValueError):
            return None

    def get(self, request, pk):
        # Only Admin and Success Manager can view enrollment history
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to view enrollment history."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student = self.get_student(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        enrollments = StudentEnrollment.objects.filter(student=student).select_related(
            "class_id", "section", "academic_year"
        ).order_by("-academic_year__start_date")

        serializer = StudentEnrollmentListSerializer(enrollments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        student = self.get_student(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        if not student.is_active:
            return Response(
                {"error": "Cannot enroll an inactive student."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Inject the student from the URL into the request data
        data = request.data.copy()
        data["student"] = str(student.id)

        serializer = StudentEnrollmentSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.save()
        return Response(
            StudentEnrollmentListSerializer(enrollment).data,
            status=status.HTTP_201_CREATED,
        )


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/enrollments/{id}/ — Correct or change enrollment  (Admin Only)
# ──────────────────────────────────────────────────────────────────────────────

class EnrollmentDetailView(APIView):
    """
    PATCH — Admin corrects or updates an existing enrollment
            (e.g., fixes wrong section, changes status to promoted/repeated).
    """

    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return StudentEnrollment.objects.select_related(
                "student", "class_id", "section", "academic_year"
            ).get(pk=pk)
        except (StudentEnrollment.DoesNotExist, ValueError):
            return None

    def patch(self, request, pk):
        enrollment = self.get_object(pk)
        if not enrollment:
            return Response(
                {"error": "Enrollment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StudentEnrollmentSerializer(
            enrollment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.save()
        return Response(
            StudentEnrollmentListSerializer(enrollment).data,
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/sections/{id}/students/ — Section roster            (All Roles)
# Teacher: only their assigned sections | Admin + SM: any section
# ──────────────────────────────────────────────────────────────────────────────

class SectionRosterView(APIView):
    """
    GET — Returns the list of active students enrolled in a given section
          for the current academic year.

    Access:
      - Admin / Success Manager: any section.
      - Teacher: only sections they are assigned to in the current academic year.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Resolve section
        try:
            section = Section.objects.select_related("class_id").get(pk=pk)
        except (Section.DoesNotExist, ValueError):
            return Response({"error": "Section not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        current_year = AcademicYear.objects.filter(is_current=True).first()

        # Teacher scope — must be assigned to this section
        if user.role == "teacher":
            assignment_qs = TeacherAssignment.objects.filter(
                teacher=user,
                section=section,
                is_active=True,
            )
            if current_year:
                assignment_qs = assignment_qs.filter(academic_year=current_year)
            if not assignment_qs.exists():
                return Response(
                    {"error": "You are not assigned to this section."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Build enrollment queryset
        enrollment_qs = StudentEnrollment.objects.filter(
            section=section, status="active"
        ).select_related("student", "class_id", "section", "academic_year")

        if current_year:
            enrollment_qs = enrollment_qs.filter(academic_year=current_year)

        # Return student list with enrollment context
        serializer = StudentEnrollmentListSerializer(enrollment_qs, many=True)
        return Response(
            {
                "section_id": str(section.id),
                "section_name": section.name,
                "class_name": section.class_id.name,
                "academic_year": current_year.name if current_year else None,
                "total_students": enrollment_qs.count(),
                "students": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/enrollments/promote/ — Bulk year-end promotion     (Admin Only)
# ──────────────────────────────────────────────────────────────────────────────

class BulkPromoteView(APIView):
    """
    POST — Promotes all active students of a source section to a target
           class + section in a new academic year.

    Request body:
      {
        "source_section_id":      "<uuid>",   // section being promoted FROM
        "target_class_id":        "<uuid>",   // class to move INTO
        "target_section_id":      "<uuid>",   // section to move INTO
        "new_academic_year_id":   "<uuid>",   // the NEW academic year
        "exclude_student_ids":    ["<uuid>"], // optional: students who repeat
        "final_year":             true        // optional: mark as graduated instead of promoted
      }

    Behaviour:
      1. Marks source enrollments as 'promoted' (or 'graduated' if final_year=True).
      2. Creates fresh 'active' enrollments in the target class/section for the new year.
      3. Students in exclude_student_ids get a new enrollment in the SAME class (repeated).
      4. Nothing is ever hard-deleted — all history is preserved.
      5. The entire operation is wrapped in a DB transaction; any error rolls back all changes.
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        data = request.data

        # ── Validate required fields ──────────────────────────────────────────
        required = ["source_section_id", "target_class_id", "target_section_id", "new_academic_year_id"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Resolve objects ───────────────────────────────────────────────────
        try:
            source_section = Section.objects.select_related("class_id").get(
                pk=data["source_section_id"]
            )
        except (Section.DoesNotExist, ValueError):
            return Response({"error": "Source section not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            from app1.models import Class
            target_class = Class.objects.get(pk=data["target_class_id"])
        except (Class.DoesNotExist, ValueError):
            return Response({"error": "Target class not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            target_section = Section.objects.get(pk=data["target_section_id"])
        except (Section.DoesNotExist, ValueError):
            return Response({"error": "Target section not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate target section belongs to target class
        if target_section.class_id != target_class:
            return Response(
                {"error": "Target section does not belong to the target class."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_academic_year = AcademicYear.objects.get(pk=data["new_academic_year_id"])
        except (AcademicYear.DoesNotExist, ValueError):
            return Response({"error": "New academic year not found."}, status=status.HTTP_404_NOT_FOUND)

        is_final_year = data.get("final_year", False)
        exclude_ids = set(data.get("exclude_student_ids", []))

        # ── Fetch the current active enrollments from the source section ──────
        # We use the most recent academic year that has active enrollments
        # in this section (not necessarily is_current, in case admin runs promotion
        # after year has been closed).
        source_enrollments = StudentEnrollment.objects.filter(
            section=source_section,
            status="active",
        ).select_related("student", "academic_year")

        if not source_enrollments.exists():
            return Response(
                {"error": "No active students found in the source section."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        promoted_count = 0
        repeated_count = 0
        skipped = []

        with transaction.atomic():
            for enrollment in source_enrollments:
                student = enrollment.student
                student_id_str = str(student.id)

                if student_id_str in exclude_ids:
                    # Student repeats — same class, same section, new year
                    new_status = StudentEnrollment.EnrollmentStatus.REPEATED
                    new_class = source_section.class_id
                    new_section = source_section
                else:
                    # Student is promoted or graduated
                    new_status_for_old = (
                        StudentEnrollment.EnrollmentStatus.GRADUATED
                        if is_final_year
                        else StudentEnrollment.EnrollmentStatus.PROMOTED
                    )
                    new_class = target_class
                    new_section = target_section
                    new_status = StudentEnrollment.EnrollmentStatus.ACTIVE

                # Close the old enrollment
                enrollment.status = (
                    StudentEnrollment.EnrollmentStatus.GRADUATED
                    if is_final_year and student_id_str not in exclude_ids
                    else (
                        StudentEnrollment.EnrollmentStatus.REPEATED
                        if student_id_str in exclude_ids
                        else StudentEnrollment.EnrollmentStatus.PROMOTED
                    )
                )
                enrollment.save(update_fields=["status"])

                # Skip creating new enrollment for graduated students (final year)
                if is_final_year and student_id_str not in exclude_ids:
                    # Mark student as graduated
                    student.status = Student.Status.GRADUATED
                    student.save(update_fields=["status"])
                    promoted_count += 1
                    continue

                # Check if enrollment for new year already exists (idempotency)
                already_exists = StudentEnrollment.objects.filter(
                    student=student,
                    academic_year=new_academic_year,
                ).exists()

                if already_exists:
                    skipped.append(student_id_str)
                    continue

                # Create the new enrollment
                StudentEnrollment.objects.create(
                    student=student,
                    class_id=new_class,
                    section=new_section,
                    academic_year=new_academic_year,
                    roll_number=enrollment.roll_number,  # preserved; admin can update later
                    status=StudentEnrollment.EnrollmentStatus.ACTIVE,
                    enrolled_on=new_academic_year.start_date,
                )

                if student_id_str in exclude_ids:
                    repeated_count += 1
                else:
                    promoted_count += 1

        return Response(
            {
                "message": "Promotion completed successfully.",
                "promoted_count": promoted_count,
                "repeated_count": repeated_count,
                "skipped_count": len(skipped),
                "skipped_student_ids": skipped,
                "target_class": target_class.name,
                "target_section": target_section.name,
                "new_academic_year": new_academic_year.name,
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 16 — Student Attendance
# ──────────────────────────────────────────────────────────────────────────────


def _teacher_can_access_student(teacher, student):
    """
    Returns True if the teacher has an active assignment for the class+section
    the student is currently enrolled in (current academic year).
    """
    current_year = AcademicYear.objects.filter(is_current=True).first()
    enrollments = student.enrollments.all()
    if current_year:
        enrollments = enrollments.filter(academic_year=current_year, status="active")
    if not enrollments.exists():
        return False
    for enrollment in enrollments:
        qs = TeacherAssignment.objects.filter(
            teacher=teacher,
            class_id=enrollment.class_id,
            section=enrollment.section,
            is_active=True,
        )
        if current_year:
            qs = qs.filter(academic_year=current_year)
        if qs.exists():
            return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/attendance/          — Mark single attendance  (Admin + Teacher)
# POST /api/v1/attendance/bulk/     — Bulk mark a section     (Admin + Teacher)
# ──────────────────────────────────────────────────────────────────────────────

class AttendanceMarkView(APIView):
    """
    POST /api/v1/attendance/
      — Admin or Teacher marks attendance for a single student.
      — Teacher: only for students in their assigned class+section.
      — marked_by is auto-set from request.user (never from request body).
      — Duplicate (same student + date) returns 400.

    POST /api/v1/attendance/bulk/
      — Admin or Teacher marks attendance for ALL active students in a section for a date.
      — Request body:
          {
            "section_id": "<uuid>",
            "date":       "YYYY-MM-DD",
            "records": [
              {"student": "<uuid>", "status": "present|absent|late", "reason": "optional"},
              ...
            ]
          }
      — Any student not in `records` is skipped (not auto-marked).
      — Already-marked students (duplicate) are skipped and reported in response.
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def _check_role(self, user):
        if user.role not in ["admin", "teacher"]:
            return Response(
                {"error": "Only Admin or Teacher can mark attendance."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    # ── POST /api/v1/attendance/ ──────────────────────────────────────────────
    def post(self, request):
        denied = self._check_role(request.user)
        if denied:
            return denied

        data = request.data.copy()
        student_id = data.get("student")
        if not student_id:
            return Response({"error": "student field is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(pk=student_id, is_active=True)
        except (Student.DoesNotExist, ValueError):
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Teacher scope check
        if request.user.role == "teacher":
            if not _teacher_can_access_student(request.user, student):
                return Response(
                    {"error": "You are not assigned to this student's class."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = StudentAttendanceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(marked_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AttendanceBulkMarkView(APIView):
    """
    POST /api/v1/attendance/bulk/
    Marks attendance for multiple students in a section in a single request.
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request):
        user = request.user
        if user.role not in ["admin", "teacher"]:
            return Response(
                {"error": "Only Admin or Teacher can mark attendance."},
                status=status.HTTP_403_FORBIDDEN,
            )

        section_id = request.data.get("section_id")
        date_val = request.data.get("date")
        records = request.data.get("records", [])

        # Validate required fields
        if not section_id:
            return Response({"error": "section_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not date_val:
            return Response({"error": "date is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not records or not isinstance(records, list):
            return Response({"error": "records must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve section
        try:
            section = Section.objects.select_related("class_id").get(pk=section_id)
        except (Section.DoesNotExist, ValueError):
            return Response({"error": "Section not found."}, status=status.HTTP_404_NOT_FOUND)

        # Teacher scope: must be assigned to this section
        if user.role == "teacher":
            current_year = AcademicYear.objects.filter(is_current=True).first()
            qs = TeacherAssignment.objects.filter(
                teacher=user, section=section, is_active=True
            )
            if current_year:
                qs = qs.filter(academic_year=current_year)
            if not qs.exists():
                return Response(
                    {"error": "You are not assigned to this section."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        created = []
        skipped = []
        errors = []

        with transaction.atomic():
            for entry in records:
                student_id = entry.get("student")
                entry_status = entry.get("status")
                reason = entry.get("reason", "")

                if not student_id or not entry_status:
                    errors.append({"entry": entry, "error": "student and status are required."})
                    continue

                try:
                    student = Student.objects.get(pk=student_id, is_active=True)
                except (Student.DoesNotExist, ValueError):
                    errors.append({"student": student_id, "error": "Student not found."})
                    continue

                # Check duplicate
                if StudentAttendance.objects.filter(student=student, date=date_val).exists():
                    skipped.append({
                        "student": student_id,
                        "student_name": student.full_name,
                        "reason": "Attendance already marked for this date.",
                    })
                    continue

                record = StudentAttendance.objects.create(
                    student=student,
                    date=date_val,
                    status=entry_status,
                    reason=reason or None,
                    marked_by=user,
                )
                created.append({
                    "id": str(record.id),
                    "student": student_id,
                    "student_name": student.full_name,
                    "status": record.status,
                    "date": str(record.date),
                })

        return Response(
            {
                "message": f"Bulk attendance processed for section '{section}'.",
                "date": date_val,
                "created_count": len(created),
                "skipped_count": len(skipped),
                "error_count": len(errors),
                "created": created,
                "skipped": skipped,
                "errors": errors,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/students/{id}/attendance/ — Student attendance history (All Roles)
# Teacher: assigned students only
# ──────────────────────────────────────────────────────────────────────────────

class StudentAttendanceHistoryView(APIView):
    """
    GET /api/v1/students/{id}/attendance/
      Returns the full attendance history for a student.
      Optional query params:
        ?from_date=YYYY-MM-DD
        ?to_date=YYYY-MM-DD
        ?status=present|absent|late

    Access:
      - Admin / Success Manager: any student.
      - Teacher: only assigned students.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            student = Student.objects.get(pk=pk, is_active=True)
        except (Student.DoesNotExist, ValueError):
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Teacher scope
        if request.user.role == "teacher":
            if not _teacher_can_access_student(request.user, student):
                return Response(
                    {"error": "You are not assigned to this student's class."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        qs = StudentAttendance.objects.filter(student=student).select_related("marked_by")

        # Filters
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        status_filter = request.query_params.get("status")

        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.order_by("-date")

        # Summary counts
        total = qs.count()
        present = qs.filter(status="present").count()
        absent = qs.filter(status="absent").count()
        late = qs.filter(status="late").count()
        attendance_rate = round(((present + late) / total) * 100, 2) if total > 0 else 100.0

        serializer = StudentAttendanceListSerializer(qs, many=True)
        return Response(
            {
                "student_id": str(student.id),
                "student_name": student.full_name,
                "summary": {
                    "total_days": total,
                    "present": present,
                    "absent": absent,
                    "late": late,
                    "attendance_rate_percent": attendance_rate,
                },
                "records": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/sections/{id}/attendance/ — Section attendance for a date
#                                         (Admin + Success Manager)
# ──────────────────────────────────────────────────────────────────────────────

class SectionAttendanceView(APIView):
    """
    GET /api/v1/sections/{id}/attendance/
      Returns all attendance records for every student in a section for a specific date.
      Also shows which enrolled students have NO record yet (not-marked).

      Required query param: ?date=YYYY-MM-DD
      Optional query param: ?status=present|absent|late

    Access: Admin + Success Manager only.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "Only Admin or Success Manager can view section attendance."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            section = Section.objects.select_related("class_id").get(pk=pk)
        except (Section.DoesNotExist, ValueError):
            return Response({"error": "Section not found."}, status=status.HTTP_404_NOT_FOUND)

        date_val = request.query_params.get("date")
        if not date_val:
            return Response(
                {"error": "Query param 'date' (YYYY-MM-DD) is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # All students enrolled in this section (current year)
        current_year = AcademicYear.objects.filter(is_current=True).first()
        enrolled_qs = StudentEnrollment.objects.filter(
            section=section, status="active"
        ).select_related("student")
        if current_year:
            enrolled_qs = enrolled_qs.filter(academic_year=current_year)

        enrolled_student_ids = list(enrolled_qs.values_list("student_id", flat=True))

        # Attendance records for that date + optional status filter
        att_qs = StudentAttendance.objects.filter(
            student_id__in=enrolled_student_ids,
            date=date_val,
        ).select_related("student", "marked_by")

        status_filter = request.query_params.get("status")
        if status_filter:
            att_qs = att_qs.filter(status=status_filter)

        # Students with NO record on that date
        marked_student_ids = set(att_qs.values_list("student_id", flat=True))
        not_marked = [
            {
                "student_id": str(e.student.id),
                "student_name": e.student.full_name,
                "roll_number": e.roll_number,
            }
            for e in enrolled_qs
            if e.student.id not in marked_student_ids
        ]

        serializer = StudentAttendanceListSerializer(att_qs, many=True)
        return Response(
            {
                "section_id": str(section.id),
                "section_name": section.name,
                "class_name": section.class_id.name,
                "date": date_val,
                "total_enrolled": len(enrolled_student_ids),
                "marked_count": att_qs.count(),
                "not_marked_count": len(not_marked),
                "attendance_records": serializer.data,
                "not_marked_students": not_marked,
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/attendance/{id}/ — Correct an attendance record (Admin Only)
# ──────────────────────────────────────────────────────────────────────────────

class AttendanceDetailView(APIView):
    """
    PATCH /api/v1/attendance/{id}/
      Admin corrects a previously marked attendance record.
      Only status, reason fields can be updated.
      marked_by is NOT changed — it stays as the original marker.
    """

    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return StudentAttendance.objects.select_related("student", "marked_by").get(pk=pk)
        except (StudentAttendance.DoesNotExist, ValueError):
            return None

    def patch(self, request, pk):
        record = self.get_object(pk)
        if not record:
            return Response(
                {"error": "Attendance record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StudentAttendanceSerializer(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # Preserve original marked_by — admin correction doesn't change who originally marked it
        serializer.save()
        return Response(
            StudentAttendanceListSerializer(record).data,
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 17 — Exams & Exam Subjects
# ──────────────────────────────────────────────────────────────────────────────

class ExamListCreateView(APIView):
    """
    POST /api/v1/exams/ — Create an exam event (Admin Only).
    GET  /api/v1/exams/ — List exams (All authenticated roles).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def post(self, request):
        serializer = ExamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Initial status is draft, created_by is request.user
        serializer.save(
            created_by=request.user,
            status=Exam.ExamStatus.DRAFT
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        academic_year_id = request.query_params.get("academic_year")
        status_param = request.query_params.get("status")
        exam_type = request.query_params.get("exam_type")

        qs = Exam.objects.select_related("academic_year", "created_by").all()

        if academic_year_id:
            qs = qs.filter(academic_year_id=academic_year_id)
        if status_param:
            qs = qs.filter(status=status_param)
        if exam_type:
            qs = qs.filter(exam_type=exam_type)

        serializer = ExamListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExamDetailView(APIView):
    """
    GET    /api/v1/exams/{id}/ — Exam details (All authenticated roles).
    PATCH  /api/v1/exams/{id}/ — Edit an exam (Admin Only).
    DELETE /api/v1/exams/{id}/ — Cancel/delete an exam (Admin Only).
    """

    def get_permissions(self):
        if self.request.method in ["PATCH", "DELETE"]:
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_object(self, pk):
        try:
            return Exam.objects.select_related("academic_year", "created_by").get(pk=pk)
        except (Exam.DoesNotExist, ValueError):
            return None

    def get(self, request, pk):
        exam = self.get_object(pk)
        if not exam:
            return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ExamSerializer(exam)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        exam = self.get_object(pk)
        if not exam:
            return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ExamSerializer(exam, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        exam = self.get_object(pk)
        if not exam:
            return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cascades to delete ExamSubject and ExamMark records
        exam.delete()
        return Response(
            {"message": f"Exam '{exam.name}' has been successfully deleted."},
            status=status.HTTP_200_OK
        )


class ExamSubjectListCreateView(APIView):
    """
    POST /api/v1/exams/{id}/subjects/ — Add a class+subject paper (Admin Only).
    GET  /api/v1/exams/{id}/subjects/ — List subjects/papers under an exam (All authenticated roles).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def post(self, request, pk):
        try:
            exam = Exam.objects.get(pk=pk)
        except (Exam.DoesNotExist, ValueError):
            return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data["exam"] = str(exam.id)

        serializer = ExamSubjectSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, pk):
        try:
            exam = Exam.objects.get(pk=pk)
        except (Exam.DoesNotExist, ValueError):
            return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

        qs = ExamSubject.objects.filter(exam=exam).select_related("class_id", "subject")
        serializer = ExamSubjectSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExamPublishView(APIView):
    """
    POST /api/v1/exams/{id}/publish/ — Publish results and lock marks (Admin Only).
    """
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            exam = Exam.objects.get(pk=pk)
        except (Exam.DoesNotExist, ValueError):
            return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

        if exam.status == Exam.ExamStatus.PUBLISHED:
            return Response(
                {"error": "Exam is already published."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            exam.status = Exam.ExamStatus.PUBLISHED
            exam.save(update_fields=["status"])

            # Lock all associated marks: update status to PUBLISHED
            exam_subjects = exam.exam_subjects.all()
            ExamMark.objects.filter(exam_subject__in=exam_subjects).update(
                entry_status=ExamMark.EntryStatus.PUBLISHED
            )

        return Response(
            {"message": f"Exam '{exam.name}' has been successfully published, and all marks are locked."},
            status=status.HTTP_200_OK
        )


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 18 — Marks Entry
# ──────────────────────────────────────────────────────────────────────────────

def _compute_grade(marks_obtained, max_marks):
    if marks_obtained is None or max_marks is None or max_marks == 0:
        return None
    percent = (marks_obtained / max_marks) * 100
    scheme = GradingScheme.objects.filter(
        min_percent__lte=percent,
        max_percent__gte=percent,
        is_active=True
    ).first()
    return scheme.grade if scheme else None


def _teacher_can_access_student_for_subject(teacher, student, subject):
    current_year = AcademicYear.objects.filter(is_current=True).first()
    enrollments = student.enrollments.all()
    if current_year:
        enrollments = enrollments.filter(academic_year=current_year, status="active")
    if not enrollments.exists():
        return False
    for enrollment in enrollments:
        qs = TeacherAssignment.objects.filter(
            teacher=teacher,
            class_id=enrollment.class_id,
            section=enrollment.section,
            subject=subject,
            is_active=True
        )
        if current_year:
            qs = qs.filter(academic_year=current_year)
        if qs.exists():
            return True
    return False


class ExamSubjectMarksView(APIView):
    """
    POST /api/v1/exam-subjects/{id}/marks/ — Enter/save marks (draft) (Admin + Teacher).
    GET  /api/v1/exam-subjects/{id}/marks/ — Marksheet for a paper (All Roles).
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def _check_access(self, user):
        if user.role not in ["admin", "teacher", "success_manager"]:
            return Response({"error": "Unauthorized access."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def post(self, request, exam_subject_pk):
        denied = self._check_access(request.user)
        if denied:
            return denied

        try:
            exam_subject = ExamSubject.objects.select_related("exam").get(pk=exam_subject_pk)
        except (ExamSubject.DoesNotExist, ValueError):
            return Response({"error": "Exam subject not found."}, status=status.HTTP_404_NOT_FOUND)

        # Enforce that exam is not published (already locked)
        if exam_subject.exam.status == Exam.ExamStatus.PUBLISHED:
            return Response(
                {"error": "Cannot modify marks. The exam has already been published."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Teacher scope check: must be assigned to teach this class/subject
        if request.user.role == "teacher":
            current_year = AcademicYear.objects.filter(is_current=True).first()
            assignment_qs = TeacherAssignment.objects.filter(
                teacher=request.user,
                class_id=exam_subject.class_id,
                subject=exam_subject.subject,
                is_active=True
            )
            if current_year:
                assignment_qs = assignment_qs.filter(academic_year=current_year)
            if not assignment_qs.exists():
                return Response(
                    {"error": "You are not assigned to teach this class and subject."},
                    status=status.HTTP_403_FORBIDDEN
                )

        records = request.data
        is_bulk = isinstance(records, list)
        if not is_bulk:
            records = [records]

        created_marks = []
        errors = []

        with transaction.atomic():
            for idx, entry in enumerate(records):
                student_id = entry.get("student")
                marks_obtained = entry.get("marks_obtained")
                is_absent = entry.get("is_absent", False)
                remarks = entry.get("remarks", "")

                if not student_id:
                    errors.append({"index": idx, "error": "student field is required."})
                    continue

                try:
                    student = Student.objects.get(pk=student_id, is_active=True)
                except (Student.DoesNotExist, ValueError):
                    errors.append({"student": student_id, "error": "Student not found or inactive."})
                    continue

                # Teacher scoping: check if the teacher teaches this student's specific section
                if request.user.role == "teacher":
                    if not _teacher_can_access_student_for_subject(request.user, student, exam_subject.subject):
                        errors.append({
                            "student": student_id,
                            "error": "You are not assigned to this student's section."
                        })
                        continue

                # Check if there is an existing mark
                existing_mark = ExamMark.objects.filter(exam_subject=exam_subject, student=student).first()
                if existing_mark:
                    # If existing is already submitted/published, teacher cannot modify it via save
                    if request.user.role == "teacher" and existing_mark.entry_status in ["submitted", "published"]:
                        errors.append({
                            "student": student_id,
                            "error": f"Cannot modify marks. Already {existing_mark.entry_status}."
                        })
                        continue

                # Validations: marks vs absent
                if is_absent and marks_obtained is not None:
                    errors.append({"student": student_id, "error": "Marks must be empty if marked absent."})
                    continue
                if not is_absent and marks_obtained is None:
                    errors.append({"student": student_id, "error": "Marks are required if not absent."})
                    continue
                if marks_obtained is not None:
                    try:
                        import decimal
                        marks_val = decimal.Decimal(str(marks_obtained))
                        if marks_val < 0 or marks_val > exam_subject.max_marks:
                            errors.append({"student": student_id, "error": f"Marks must be between 0 and {exam_subject.max_marks}."})
                            continue
                    except (ValueError, decimal.InvalidOperation):
                        errors.append({"student": student_id, "error": "Invalid decimal format for marks_obtained."})
                        continue

                # Compute Grade
                computed_grade = None
                if not is_absent and marks_obtained is not None:
                    computed_grade = _compute_grade(decimal.Decimal(str(marks_obtained)), exam_subject.max_marks)

                # Save / update (draft status)
                mark_record, _ = ExamMark.objects.update_or_create(
                    exam_subject=exam_subject,
                    student=student,
                    defaults={
                        "marks_obtained": marks_obtained,
                        "is_absent": is_absent,
                        "grade": computed_grade,
                        "remarks": remarks,
                        "entered_by": request.user,
                        "entry_status": ExamMark.EntryStatus.DRAFT
                    }
                )
                created_marks.append(mark_record)

        if errors and not created_marks:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExamMarkListSerializer(created_marks, many=True)
        return Response(
            {
                "message": f"Successfully processed {len(created_marks)} mark record(s).",
                "errors": errors,
                "records": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    def get(self, request, exam_subject_pk):
        denied = self._check_access(request.user)
        if denied:
            return denied

        try:
            exam_subject = ExamSubject.objects.get(pk=exam_subject_pk)
        except (ExamSubject.DoesNotExist, ValueError):
            return Response({"error": "Exam subject not found."}, status=status.HTTP_404_NOT_FOUND)

        qs = ExamMark.objects.filter(exam_subject=exam_subject).select_related("student", "exam_subject__subject", "entered_by", "updated_by")

        # Teacher scoping: only view marks of students in sections they teach
        if request.user.role == "teacher":
            current_year = AcademicYear.objects.filter(is_current=True).first()
            teacher_assignments = TeacherAssignment.objects.filter(
                teacher=request.user,
                class_id=exam_subject.class_id,
                subject=exam_subject.subject,
                is_active=True
            )
            if current_year:
                teacher_assignments = teacher_assignments.filter(academic_year=current_year)

            assigned_sections = teacher_assignments.values_list("section_id", flat=True)
            enrollments = StudentEnrollment.objects.filter(
                section_id__in=assigned_sections,
                status="active"
            )
            if current_year:
                enrollments = enrollments.filter(academic_year=current_year)
            
            allowed_student_ids = enrollments.values_list("student_id", flat=True)
            qs = qs.filter(student_id__in=allowed_student_ids)

        serializer = ExamMarkListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExamSubjectSubmitView(APIView):
    """
    POST /api/v1/exam-subjects/{id}/submit/ — Submit marks — locks the teacher's edits (Admin + Teacher).
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, exam_subject_pk):
        user = request.user
        if user.role not in ["admin", "teacher"]:
            return Response({"error": "Only Admin or Teacher can submit marks."}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam_subject = ExamSubject.objects.get(pk=exam_subject_pk)
        except (ExamSubject.DoesNotExist, ValueError):
            return Response({"error": "Exam subject not found."}, status=status.HTTP_404_NOT_FOUND)

        qs = ExamMark.objects.filter(exam_subject=exam_subject, entry_status=ExamMark.EntryStatus.DRAFT)

        # Scoping: Teachers only submit for their assigned students
        if user.role == "teacher":
            current_year = AcademicYear.objects.filter(is_current=True).first()
            teacher_assignments = TeacherAssignment.objects.filter(
                teacher=user,
                class_id=exam_subject.class_id,
                subject=exam_subject.subject,
                is_active=True
            )
            if current_year:
                teacher_assignments = teacher_assignments.filter(academic_year=current_year)

            assigned_sections = teacher_assignments.values_list("section_id", flat=True)
            enrollments = StudentEnrollment.objects.filter(
                section_id__in=assigned_sections,
                status="active"
            )
            if current_year:
                enrollments = enrollments.filter(academic_year=current_year)

            allowed_student_ids = enrollments.values_list("student_id", flat=True)
            qs = qs.filter(student_id__in=allowed_student_ids)

        updated_count = qs.update(entry_status=ExamMark.EntryStatus.SUBMITTED)

        return Response(
            {"message": f"Successfully submitted {updated_count} marks for {exam_subject.subject.name}."},
            status=status.HTTP_200_OK
        )


class StudentMarksHistoryView(APIView):
    """
    GET /api/v1/students/{id}/marks/ — A student's marks across all exams (All Roles).
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request, student_pk):
        try:
            student = Student.objects.get(pk=student_pk, is_active=True)
        except (Student.DoesNotExist, ValueError):
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Scoping permissions:
        # Admin / Success Manager can view any.
        # Teacher can only view if assigned to the student's current class/section.
        if request.user.role == "teacher":
            current_year = AcademicYear.objects.filter(is_current=True).first()
            enrollment = student.enrollments.filter(status="active")
            if current_year:
                enrollment = enrollment.filter(academic_year=current_year)
            enrollment = enrollment.first()

            if not enrollment:
                return Response({"error": "Student has no active enrollment in current academic year."}, status=status.HTTP_403_FORBIDDEN)

            has_assignment = TeacherAssignment.objects.filter(
                teacher=request.user,
                class_id=enrollment.class_id,
                section=enrollment.section,
                is_active=True
            )
            if current_year:
                has_assignment = has_assignment.filter(academic_year=current_year)
            if not has_assignment.exists():
                return Response(
                    {"error": "You are not assigned to this student's section."},
                    status=status.HTTP_403_FORBIDDEN
                )

        qs = ExamMark.objects.filter(student=student).select_related(
            "exam_subject__exam", "exam_subject__subject", "entered_by", "updated_by"
        )
        serializer = ExamMarkSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarkDetailView(APIView):
    """
    PATCH /api/v1/marks/{id}/ — Edit a mark (Teacher pre-submit; Admin any, audited).
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_object(self, pk):
        try:
            return ExamMark.objects.select_related("exam_subject__exam", "student").get(pk=pk)
        except (ExamMark.DoesNotExist, ValueError):
            return None

    def patch(self, request, pk):
        mark = self.get_object(pk)
        if not mark:
            return Response({"error": "Mark record not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role not in ["admin", "teacher"]:
            return Response({"error": "Only Admin or Teacher can modify marks."}, status=status.HTTP_403_FORBIDDEN)

        # Scoping logic & rules:
        if user.role == "teacher":
            # 1. Check if the mark is in draft state (pre-submit)
            if mark.entry_status != ExamMark.EntryStatus.DRAFT:
                return Response(
                    {"error": "Cannot edit marks. Only draft marks can be edited by teachers."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 2. Check if the teacher teaches this student's section for this subject
            if not _teacher_can_access_student_for_subject(user, mark.student, mark.exam_subject.subject):
                return Response(
                    {"error": "You are not assigned to this student's section for this subject."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Validations
        data = request.data.copy()
        is_absent = data.get("is_absent", mark.is_absent)
        marks_obtained = data.get("marks_obtained")

        # Allow passing marks_obtained as None/null or absent
        if is_absent and marks_obtained is not None:
            return Response({"error": "Marks must be empty if marked absent."}, status=status.HTTP_400_BAD_REQUEST)

        # If modifying marks_obtained
        if "marks_obtained" in data and marks_obtained is not None:
            try:
                import decimal
                marks_val = decimal.Decimal(str(marks_obtained))
                if marks_val < 0 or marks_val > mark.exam_subject.max_marks:
                    return Response({"error": f"Marks must be between 0 and {mark.exam_subject.max_marks}."}, status=status.HTTP_400_BAD_REQUEST)
                # Compute grade
                data["grade"] = _compute_grade(marks_val, mark.exam_subject.max_marks)
            except (ValueError, decimal.InvalidOperation):
                return Response({"error": "Invalid decimal format for marks_obtained."}, status=status.HTTP_400_BAD_REQUEST)
        elif is_absent:
            data["grade"] = None
            data["marks_obtained"] = None
        elif "marks_obtained" in data and marks_obtained is None and not is_absent:
            return Response({"error": "Marks are required if not absent."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExamMarkSerializer(mark, data=data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Auditing: if Admin, set updated_by
        if user.role == "admin":
            serializer.save(updated_by=user)
        else:
            serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentPerformanceNoteListCreateView(APIView):
    """
    POST /api/v1/students/{pk}/performance-notes/ — Add a performance note (Admin + Teacher: own subject)
    GET  /api/v1/students/{pk}/performance-notes/ — List a student's performance notes (All Roles)
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_student(self, pk):
        try:
            return Student.objects.get(pk=pk, is_active=True)
        except (Student.DoesNotExist, ValueError):
            return None

    def post(self, request, pk):
        student = self.get_student(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role not in ["admin", "teacher"]:
            return Response(
                {"error": "You do not have permission to add performance notes."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Scoping logic for Teacher:
        if user.role == "teacher":
            subject_id = request.data.get("subject")
            if not subject_id:
                return Response(
                    {"error": "Subject must be specified for teacher-authored performance notes."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                subject = Subject.objects.get(pk=subject_id)
            except (Subject.DoesNotExist, ValueError):
                return Response(
                    {"error": "Specified subject does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not _teacher_can_access_student_for_subject(user, student, subject):
                return Response(
                    {"error": "You are not assigned to teach this student this subject."},
                    status=status.HTTP_403_FORBIDDEN
                )

        data = request.data.copy()
        data["student"] = str(student.id)

        serializer = StudentPerformanceNoteSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(teacher=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, pk):
        student = self.get_student(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        # All Roles (Admin, Success Manager, Teacher) are allowed, but Teacher is scoped:
        if user.role not in ["admin", "success_manager", "teacher"]:
            return Response(
                {"error": "You do not have permission to view performance notes."},
                status=status.HTTP_403_FORBIDDEN
            )

        if user.role == "teacher":
            if not _teacher_can_access_student(user, student):
                return Response(
                    {"error": "You are not assigned to this student's class."},
                    status=status.HTTP_403_FORBIDDEN
                )

        notes = StudentPerformanceNote.objects.filter(student=student).select_related(
            "student", "subject", "exam", "teacher"
        ).order_by("-created_at")

        serializer = StudentPerformanceNoteListSerializer(notes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentPerformanceNoteDetailView(APIView):
    """
    PATCH  /api/v1/performance-notes/{pk}/ — Edit a note (Admin + Teacher: author only)
    DELETE /api/v1/performance-notes/{pk}/ — Delete a note (Admin + Teacher: author only)
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_object(self, pk):
        try:
            return StudentPerformanceNote.objects.select_related("student", "subject", "teacher").get(pk=pk)
        except (StudentPerformanceNote.DoesNotExist, ValueError):
            return None

    def patch(self, request, pk):
        note = self.get_object(pk)
        if not note:
            return Response({"error": "Performance note not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role not in ["admin", "teacher"]:
            return Response(
                {"error": "You do not have permission to modify this note."},
                status=status.HTTP_403_FORBIDDEN
            )

        if user.role == "teacher":
            # Teacher: author only
            if note.teacher != user:
                return Response(
                    {"error": "You can only edit notes you authored."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # If subject is provided in request, validate it
            subject_id = request.data.get("subject")
            if "subject" in request.data:
                if not subject_id:
                    return Response(
                        {"error": "Subject must be specified for teacher-authored performance notes."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                try:
                    subject = Subject.objects.get(pk=subject_id)
                except (Subject.DoesNotExist, ValueError):
                    return Response(
                        {"error": "Specified subject does not exist."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if not _teacher_can_access_student_for_subject(user, note.student, subject):
                    return Response(
                        {"error": "You are not assigned to teach this student this subject."},
                        status=status.HTTP_403_FORBIDDEN
                    )

        if "student" in request.data and request.data["student"] != str(note.student.id):
            return Response({"error": "Cannot change the student of a performance note."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = StudentPerformanceNoteSerializer(note, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        note = self.get_object(pk)
        if not note:
            return Response({"error": "Performance note not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role not in ["admin", "teacher"]:
            return Response(
                {"error": "You do not have permission to delete this note."},
                status=status.HTTP_403_FORBIDDEN
            )

        if user.role == "teacher":
            # Teacher: author only
            if note.teacher != user:
                return Response(
                    {"error": "You can only delete notes you authored."},
                    status=status.HTTP_403_FORBIDDEN
                )

        note.delete()
        return Response(
            {"message": "Performance note has been successfully deleted."},
            status=status.HTTP_200_OK
        )


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 20 — Success Manager & Analytics
# ──────────────────────────────────────────────────────────────────────────────


def _compute_attendance_rate(student):
    """
    Computes attendance rate for a student as (present + late) / total * 100.
    Returns (rate, total_days).
    """
    att_qs = student.attendance_records.all()
    present = att_qs.filter(status="present").count()
    absent = att_qs.filter(status="absent").count()
    late = att_qs.filter(status="late").count()
    total = present + absent + late
    if total == 0:
        return 100.0, 0
    return round(((present + late) / total) * 100, 2), total


def _get_at_risk_reasons(student):
    """
    Returns a list of reasons a student is flagged as at-risk.
    Empty list means student is NOT at-risk.
    """
    reasons = []

    # 1. Low Attendance (below 75%)
    rate, total_days = _compute_attendance_rate(student)
    if total_days > 0 and rate < 75.0:
        reasons.append(f"Low attendance ({rate:.2f}%)")

    # 2. Academic Failure — failed at least one exam subject in a published exam
    published_marks = ExamMark.objects.filter(
        student=student,
        entry_status="published",
    ).select_related("exam_subject__subject", "exam_subject__exam")

    for mark in published_marks:
        es = mark.exam_subject
        if mark.is_absent:
            reasons.append(
                f"Failed in {es.subject.name} (absent, 0.00/{es.max_marks:.2f})"
            )
        elif mark.marks_obtained is not None and mark.marks_obtained < es.pass_marks:
            reasons.append(
                f"Failed in {es.subject.name} ({mark.marks_obtained:.2f}/{es.max_marks:.2f})"
            )

    return reasons


class SuccessManagerDashboardView(APIView):
    """
    GET /api/v1/success-manager/dashboard/
    Overview: at-risk count, top performers, recent alerts.
    Access: Admin + Success Manager.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to access this dashboard."},
                status=status.HTTP_403_FORBIDDEN,
            )

        active_students = Student.objects.filter(is_active=True)

        # 1. At-risk count
        at_risk_count = 0
        for student in active_students:
            if _get_at_risk_reasons(student):
                at_risk_count += 1

        # 2. Top 5 performers — by overall average percentage across published exams
        top_performers = []
        student_averages = []
        for student in active_students:
            marks = ExamMark.objects.filter(
                student=student,
                entry_status="published",
                is_absent=False,
                marks_obtained__isnull=False,
            ).select_related("exam_subject")
            if not marks.exists():
                continue
            total_obtained = sum(float(m.marks_obtained) for m in marks)
            total_max = sum(float(m.exam_subject.max_marks) for m in marks)
            if total_max > 0:
                avg_pct = round((total_obtained / total_max) * 100, 2)
                student_averages.append((student, avg_pct))

        student_averages.sort(key=lambda x: x[1], reverse=True)
        for student, avg_pct in student_averages[:5]:
            top_performers.append({
                "student_id": str(student.id),
                "student_name": student.full_name,
                "average_percent": avg_pct,
            })

        # 3. Alerts — 5 most recent success notes with severity at_risk or watch
        alert_notes = StudentSuccessNote.objects.filter(
            severity__in=["at_risk", "watch"]
        ).select_related("student", "success_manager").order_by("-created_at")[:5]

        alerts = [
            {
                "id": str(n.id),
                "student_id": str(n.student.id),
                "student_name": n.student.full_name,
                "category": n.category,
                "severity": n.severity,
                "title": n.title,
                "note_text": n.note_text,
                "status": n.status,
                "created_at": n.created_at,
            }
            for n in alert_notes
        ]

        return Response({
            "at_risk_count": at_risk_count,
            "top_performers": top_performers,
            "alerts": alerts,
        }, status=status.HTTP_200_OK)


class SuccessManagerAtRiskView(APIView):
    """
    GET /api/v1/success-manager/at-risk/
    Returns at-risk students with the reason each was flagged.
    Access: Admin + Success Manager.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to access this resource."},
                status=status.HTTP_403_FORBIDDEN,
            )

        active_students = Student.objects.filter(is_active=True)
        at_risk_list = []

        for student in active_students:
            reasons = _get_at_risk_reasons(student)
            if reasons:
                at_risk_list.append({
                    "student_id": str(student.id),
                    "student_name": student.full_name,
                    "admission_number": student.admission_number,
                    "reasons": reasons,
                })

        return Response({
            "at_risk_count": len(at_risk_list),
            "students": at_risk_list,
        }, status=status.HTTP_200_OK)


class StudentAnalysisView(APIView):
    """
    GET /api/v1/students/{id}/analysis/
    Subject-wise strengths and weaknesses for a student.
    Access: Admin + Success Manager.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to view student analysis."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            student = Student.objects.get(pk=pk)
        except (Student.DoesNotExist, ValueError):
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all published marks
        marks = ExamMark.objects.filter(
            student=student,
            entry_status="published",
        ).select_related("exam_subject__subject")

        # Group by subject
        subject_scores = {}  # subject_name -> list of (obtained, max)
        for mark in marks:
            subj = mark.exam_subject.subject
            subj_name = subj.name
            if subj_name not in subject_scores:
                subject_scores[subj_name] = {"obtained": [], "max": [], "failed": False, "subject_id": str(subj.id)}

            if mark.is_absent:
                subject_scores[subj_name]["obtained"].append(0)
                subject_scores[subj_name]["max"].append(float(mark.exam_subject.max_marks))
                subject_scores[subj_name]["failed"] = True
            elif mark.marks_obtained is not None:
                obtained = float(mark.marks_obtained)
                max_m = float(mark.exam_subject.max_marks)
                subject_scores[subj_name]["obtained"].append(obtained)
                subject_scores[subj_name]["max"].append(max_m)
                if obtained < float(mark.exam_subject.pass_marks):
                    subject_scores[subj_name]["failed"] = True

        # Calculate averages and classify
        strengths = []
        weaknesses = []
        subject_averages = []

        for subj_name, data in subject_scores.items():
            total_obtained = sum(data["obtained"])
            total_max = sum(data["max"])
            avg_pct = round((total_obtained / total_max) * 100, 2) if total_max > 0 else 0.0

            entry = {
                "subject_id": data["subject_id"],
                "subject_name": subj_name,
                "average_percent": avg_pct,
                "exams_count": len(data["obtained"]),
            }
            subject_averages.append(entry)

            if avg_pct >= 75.0:
                strengths.append(entry)
            if avg_pct < 50.0 or data["failed"]:
                weaknesses.append(entry)

        return Response({
            "student_id": str(student.id),
            "student_name": student.full_name,
            "subject_averages": subject_averages,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }, status=status.HTTP_200_OK)


class StudentGrowthView(APIView):
    """
    GET /api/v1/students/{id}/growth/
    Exam-over-exam growth trend for a student.
    Access: Admin + Success Manager.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to view growth trends."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            student = Student.objects.get(pk=pk)
        except (Student.DoesNotExist, ValueError):
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all published marks grouped by exam
        marks = ExamMark.objects.filter(
            student=student,
            entry_status="published",
        ).select_related("exam_subject__exam")

        # Group by exam
        exam_data = {}  # exam_id -> { name, date, obtained, max }
        for mark in marks:
            exam = mark.exam_subject.exam
            exam_id = str(exam.id)
            if exam_id not in exam_data:
                exam_data[exam_id] = {
                    "exam_id": exam_id,
                    "exam_name": exam.name,
                    "exam_date": exam.created_at,
                    "total_obtained": 0,
                    "total_max": 0,
                }

            if mark.is_absent:
                exam_data[exam_id]["total_max"] += float(mark.exam_subject.max_marks)
            elif mark.marks_obtained is not None:
                exam_data[exam_id]["total_obtained"] += float(mark.marks_obtained)
                exam_data[exam_id]["total_max"] += float(mark.exam_subject.max_marks)

        # Sort by exam date (creation date)
        sorted_exams = sorted(exam_data.values(), key=lambda x: x["exam_date"])

        # Compute growth trend
        trend = []
        prev_avg = None
        for exam_info in sorted_exams:
            avg = round((exam_info["total_obtained"] / exam_info["total_max"]) * 100, 2) if exam_info["total_max"] > 0 else 0.0
            delta = None
            if prev_avg is not None:
                delta = round(avg - prev_avg, 2)

            trend.append({
                "exam_id": exam_info["exam_id"],
                "exam_name": exam_info["exam_name"],
                "average_percent": avg,
                "delta": f"+{delta:.2f}%" if delta is not None and delta >= 0 else (f"{delta:.2f}%" if delta is not None else None),
            })
            prev_avg = avg

        return Response({
            "student_id": str(student.id),
            "student_name": student.full_name,
            "growth_trend": trend,
        }, status=status.HTTP_200_OK)


class SectionAnalysisView(APIView):
    """
    GET /api/v1/sections/{id}/analysis/
    Section-level performance overview.
    Access: Admin + Success Manager.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to view section analysis."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            section = Section.objects.select_related("class_id").get(pk=pk)
        except (Section.DoesNotExist, ValueError):
            return Response({"error": "Section not found."}, status=status.HTTP_404_NOT_FOUND)

        current_year = AcademicYear.objects.filter(is_current=True).first()

        # Get active students in this section
        enrollment_qs = StudentEnrollment.objects.filter(
            section=section, status="active"
        ).select_related("student")
        if current_year:
            enrollment_qs = enrollment_qs.filter(academic_year=current_year)

        students = [e.student for e in enrollment_qs if e.student.is_active]
        total_students = len(students)

        if total_students == 0:
            return Response({
                "section_id": str(section.id),
                "section_name": section.name,
                "class_name": section.class_id.name,
                "total_students": 0,
                "section_average_attendance_rate": None,
                "section_average_score_percent": None,
                "subject_averages": [],
                "at_risk_count": 0,
                "top_performers": [],
            }, status=status.HTTP_200_OK)

        # 1. Section Average Attendance Rate
        total_rate = 0.0
        students_with_att = 0
        for student in students:
            rate, total_days = _compute_attendance_rate(student)
            if total_days > 0:
                total_rate += rate
                students_with_att += 1
        section_avg_att = round(total_rate / students_with_att, 2) if students_with_att > 0 else None

        # 2. Section Average Score Percent & Subject Averages
        student_ids = [s.id for s in students]
        all_marks = ExamMark.objects.filter(
            student_id__in=student_ids,
            entry_status="published",
            is_absent=False,
            marks_obtained__isnull=False,
        ).select_related("exam_subject__subject")

        # Overall section average
        total_obtained = 0
        total_max = 0
        # Subject-wise breakdown
        subject_data = {}  # subject_name -> { obtained, max }

        for mark in all_marks:
            obtained = float(mark.marks_obtained)
            max_m = float(mark.exam_subject.max_marks)
            total_obtained += obtained
            total_max += max_m

            subj_name = mark.exam_subject.subject.name
            if subj_name not in subject_data:
                subject_data[subj_name] = {"obtained": 0, "max": 0}
            subject_data[subj_name]["obtained"] += obtained
            subject_data[subj_name]["max"] += max_m

        section_avg_score = round((total_obtained / total_max) * 100, 2) if total_max > 0 else None

        subject_averages = []
        for subj_name, data in subject_data.items():
            avg = round((data["obtained"] / data["max"]) * 100, 2) if data["max"] > 0 else 0.0
            subject_averages.append({
                "subject_name": subj_name,
                "average_percent": avg,
            })

        # 3. At-Risk Count
        at_risk_count = 0
        for student in students:
            if _get_at_risk_reasons(student):
                at_risk_count += 1

        # 4. Top 5 Performers
        student_averages_list = []
        for student in students:
            marks = ExamMark.objects.filter(
                student=student,
                entry_status="published",
                is_absent=False,
                marks_obtained__isnull=False,
            ).select_related("exam_subject")
            if not marks.exists():
                continue
            s_obtained = sum(float(m.marks_obtained) for m in marks)
            s_max = sum(float(m.exam_subject.max_marks) for m in marks)
            if s_max > 0:
                avg_pct = round((s_obtained / s_max) * 100, 2)
                student_averages_list.append((student, avg_pct))

        student_averages_list.sort(key=lambda x: x[1], reverse=True)
        top_performers = [
            {
                "student_id": str(s.id),
                "student_name": s.full_name,
                "average_percent": avg,
            }
            for s, avg in student_averages_list[:5]
        ]

        return Response({
            "section_id": str(section.id),
            "section_name": section.name,
            "class_name": section.class_id.name,
            "total_students": total_students,
            "section_average_attendance_rate": section_avg_att,
            "section_average_score_percent": section_avg_score,
            "subject_averages": subject_averages,
            "at_risk_count": at_risk_count,
            "top_performers": top_performers,
        }, status=status.HTTP_200_OK)


class StudentSuccessNoteListCreateView(APIView):
    """
    POST /api/v1/students/{pk}/success-notes/ — Add an intervention / flag note.
    GET  /api/v1/students/{pk}/success-notes/ — List a student's success notes.
    Access: Admin + Success Manager.
    """

    permission_classes = [IsAuthenticated]

    def get_student(self, pk):
        try:
            return Student.objects.get(pk=pk, is_active=True)
        except (Student.DoesNotExist, ValueError):
            return None

    def post(self, request, pk):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to add success notes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student = self.get_student(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data["student"] = str(student.id)

        serializer = StudentSuccessNoteSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(success_manager=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, pk):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to view success notes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student = self.get_student(pk)
        if not student:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        notes = StudentSuccessNote.objects.filter(student=student).select_related(
            "student", "success_manager"
        ).order_by("-created_at")

        serializer = StudentSuccessNoteListSerializer(notes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SuccessNoteDetailView(APIView):
    """
    PATCH /api/v1/success-notes/{pk}/ — Update a note or its status.
    Access: Admin + Success Manager (SM: author only).
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return StudentSuccessNote.objects.select_related("student", "success_manager").get(pk=pk)
        except (StudentSuccessNote.DoesNotExist, ValueError):
            return None

    def patch(self, request, pk):
        if request.user.role not in ["admin", "success_manager"]:
            return Response(
                {"error": "You do not have permission to modify this note."},
                status=status.HTTP_403_FORBIDDEN,
            )

        note = self.get_object(pk)
        if not note:
            return Response({"error": "Success note not found."}, status=status.HTTP_404_NOT_FOUND)

        # Success managers can only edit their own notes
        if request.user.role == "success_manager" and note.success_manager != request.user:
            return Response(
                {"error": "You can only edit notes you authored."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # student and success_manager fields are read-only
        if "student" in request.data and request.data["student"] != str(note.student.id):
            return Response(
                {"error": "Cannot change the student of a success note."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StudentSuccessNoteSerializer(note, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

