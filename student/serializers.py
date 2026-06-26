from rest_framework import serializers

from app1.models import AcademicYear, Class, Section, Subject
from .models import (
    Exam,
    ExamMark,
    ExamSubject,
    GradingScheme,
    Student,
    StudentAnalysisSnapshot,
    StudentAttendance,
    StudentEnrollment,
    StudentPerformanceNote,
    StudentSuccessNote,
)


# ──────────────────────────────────────────────────────────────────────────────
# Table 16: Student — Core Identity
# ──────────────────────────────────────────────────────────────────────────────

class StudentSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST   /api/v1/students/          — Admin creates a student
      - GET    /api/v1/students/{id}/     — Single student detail (all roles)
      - PATCH  /api/v1/students/{id}/     — Admin updates a student
    """

    class Meta:
        model = Student
        fields = [
            "id",
            "admission_number",
            "full_name",
            "date_of_birth",
            "gender",
            "guardian_name",
            "guardian_contact",
            "address",
            "photo_url",
            "admission_date",
            "status",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "is_active", "created_at"]

    def validate_admission_number(self, value):
        qs = Student.objects.filter(admission_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A student with this admission number already exists."
            )
        return value


class StudentListSerializer(serializers.ModelSerializer):
    """
    Used for:
      - GET /api/v1/students/ — Optimized list response.
    Includes the student's current class, section, and roll number
    derived from their active enrollment in the current academic year.
    """

    current_class_id = serializers.SerializerMethodField()
    current_class_name = serializers.SerializerMethodField()
    current_section_id = serializers.SerializerMethodField()
    current_section_name = serializers.SerializerMethodField()
    current_roll_number = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "admission_number",
            "full_name",
            "date_of_birth",
            "gender",
            "guardian_name",
            "guardian_contact",
            "address",
            "photo_url",
            "admission_date",
            "status",
            "is_active",
            "created_at",
            "current_class_id",
            "current_class_name",
            "current_section_id",
            "current_section_name",
            "current_roll_number",
        ]

    def _get_current_enrollment(self, obj):
        """
        Returns the active enrollment for the current academic year.
        Uses an in-memory cache per serializer instance to avoid N+1 queries
        when rendering a list.
        """
        if not hasattr(self, "_enrollment_cache"):
            self._enrollment_cache = {}

        if obj.id not in self._enrollment_cache:
            enrollment = None
            try:
                current_year = AcademicYear.objects.filter(is_current=True).first()
                if current_year:
                    enrollment = obj.enrollments.filter(
                        academic_year=current_year, status="active"
                    ).first()
            except Exception:
                pass
            # Fall back to the most recent enrollment if no active-year match
            if enrollment is None:
                enrollment = obj.enrollments.first()
            self._enrollment_cache[obj.id] = enrollment

        return self._enrollment_cache[obj.id]

    def get_current_class_id(self, obj):
        enrollment = self._get_current_enrollment(obj)
        return str(enrollment.class_id.id) if enrollment else None

    def get_current_class_name(self, obj):
        enrollment = self._get_current_enrollment(obj)
        return enrollment.class_id.name if enrollment else None

    def get_current_section_id(self, obj):
        enrollment = self._get_current_enrollment(obj)
        return str(enrollment.section.id) if enrollment else None

    def get_current_section_name(self, obj):
        enrollment = self._get_current_enrollment(obj)
        return enrollment.section.name if enrollment else None

    def get_current_roll_number(self, obj):
        enrollment = self._get_current_enrollment(obj)
        return enrollment.roll_number if enrollment else None


# ──────────────────────────────────────────────────────────────────────────────
# Table 17: StudentEnrollment — Class placement per academic year
# ──────────────────────────────────────────────────────────────────────────────

class StudentEnrollmentSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST  /api/v1/students/{id}/enrollments/  — Admin enrolls a student in a class/section/year
      - PATCH /api/v1/students/{id}/enrollments/{id}/ — Admin updates enrollment status (promotion etc.)

    Validations:
      - section must belong to the given class_id
      - student can only have ONE enrollment per academic year (unique_together)
    """

    # Read-only display names — returned alongside raw IDs
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    class_name = serializers.CharField(source="class_id.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = [
            "id",
            "student",
            "student_name",
            "class_id",
            "class_name",
            "section",
            "section_name",
            "academic_year",
            "academic_year_name",
            "roll_number",
            "status",
            "enrolled_on",
        ]
        read_only_fields = ["id", "student_name", "class_name", "section_name", "academic_year_name"]

    def validate(self, data):
        class_obj = data.get("class_id", getattr(self.instance, "class_id", None))
        section = data.get("section", getattr(self.instance, "section", None))

        # Validate section belongs to the selected class
        if class_obj and section:
            if section.class_id != class_obj:
                raise serializers.ValidationError(
                    {"section": "This section does not belong to the selected class."}
                )

        # Enforce one enrollment per student per academic year
        student = data.get("student", getattr(self.instance, "student", None))
        academic_year = data.get("academic_year", getattr(self.instance, "academic_year", None))
        if student and academic_year:
            qs = StudentEnrollment.objects.filter(student=student, academic_year=academic_year)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "This student is already enrolled for the selected academic year."
                )

        return data


class StudentEnrollmentListSerializer(serializers.ModelSerializer):
    """
    Compact read-only serializer used when listing all enrollments of a student
    or all students in a class/section.
    """

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    class_name = serializers.CharField(source="class_id.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = [
            "id",
            "student",
            "student_name",
            "admission_number",
            "class_id",
            "class_name",
            "section",
            "section_name",
            "academic_year",
            "academic_year_name",
            "roll_number",
            "status",
            "enrolled_on",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Table 18: StudentAttendance — Daily attendance per student
# ──────────────────────────────────────────────────────────────────────────────

class StudentAttendanceSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST  /api/v1/students/attendance/      — Teacher/Admin marks attendance
      - PATCH /api/v1/students/attendance/{id}/ — Update a record (e.g., correct a mistake)
      - GET   /api/v1/students/attendance/      — List attendance records

    Validations:
      - Only one record per student per date (unique_together enforced here too)
      - marked_by is set from the request context in the view (not user-submitted)
    """

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    marked_by_name = serializers.CharField(source="marked_by.full_name", read_only=True, default=None)

    class Meta:
        model = StudentAttendance
        fields = [
            "id",
            "student",
            "student_name",
            "date",
            "status",
            "reason",
            "marked_by",
            "marked_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "student_name", "marked_by", "marked_by_name", "created_at"]

    def validate(self, data):
        student = data.get("student", getattr(self.instance, "student", None))
        date_val = data.get("date", getattr(self.instance, "date", None))

        if student and date_val:
            qs = StudentAttendance.objects.filter(student=student, date=date_val)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Attendance for this student on this date has already been marked."
                )

        return data


class StudentAttendanceListSerializer(serializers.ModelSerializer):
    """
    Read-only compact serializer for listing/filtering attendance records.
    """

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    marked_by_name = serializers.CharField(source="marked_by.full_name", read_only=True, default=None)

    class Meta:
        model = StudentAttendance
        fields = [
            "id",
            "student",
            "student_name",
            "admission_number",
            "date",
            "status",
            "reason",
            "marked_by",
            "marked_by_name",
            "created_at",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Table 19: Exam — Exam events (school-wide)
# ──────────────────────────────────────────────────────────────────────────────

class ExamSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST /api/v1/exams/       — Admin creates an exam event
      - PUT  /api/v1/exams/{id}/  — Admin updates exam details
      - GET  /api/v1/exams/{id}/  — Detail view

    created_by is injected by the view from request.user.
    """

    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default=None)

    class Meta:
        model = Exam
        fields = [
            "id",
            "name",
            "exam_type",
            "academic_year",
            "academic_year_name",
            "term",
            "weightage",
            "status",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "academic_year_name", "created_by", "created_by_name", "created_at"]


class ExamListSerializer(serializers.ModelSerializer):
    """
    Compact read-only serializer for listing exams.
    """

    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id",
            "name",
            "exam_type",
            "academic_year",
            "academic_year_name",
            "term",
            "weightage",
            "status",
            "created_at",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Table 20: ExamSubject — Per-class subject details under an exam
# ──────────────────────────────────────────────────────────────────────────────

class ExamSubjectSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST /api/v1/exams/{exam_id}/subjects/       — Admin adds a subject to an exam
      - PUT  /api/v1/exams/{exam_id}/subjects/{id}/  — Admin updates max/pass marks or date
      - GET  /api/v1/exams/{exam_id}/subjects/       — List all subjects under an exam

    Validations:
      - No duplicate (exam, class_id, subject) — unique_together on the model
      - pass_marks must not exceed max_marks
    """

    exam_name = serializers.CharField(source="exam.name", read_only=True)
    class_name = serializers.CharField(source="class_id.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = ExamSubject
        fields = [
            "id",
            "exam",
            "exam_name",
            "class_id",
            "class_name",
            "subject",
            "subject_name",
            "max_marks",
            "pass_marks",
            "exam_date",
        ]
        read_only_fields = ["id", "exam_name", "class_name", "subject_name"]

    def validate(self, data):
        max_marks = data.get("max_marks", getattr(self.instance, "max_marks", None))
        pass_marks = data.get("pass_marks", getattr(self.instance, "pass_marks", None))

        if max_marks is not None and pass_marks is not None:
            if pass_marks > max_marks:
                raise serializers.ValidationError(
                    {"pass_marks": "Pass marks cannot exceed max marks."}
                )

        # Duplicate check for (exam, class_id, subject)
        exam = data.get("exam", getattr(self.instance, "exam", None))
        class_obj = data.get("class_id", getattr(self.instance, "class_id", None))
        subject = data.get("subject", getattr(self.instance, "subject", None))
        if exam and class_obj and subject:
            qs = ExamSubject.objects.filter(exam=exam, class_id=class_obj, subject=subject)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "This subject is already added for this class under this exam."
                )

        return data


# ──────────────────────────────────────────────────────────────────────────────
# Table 21: ExamMark — A student's marks for one subject in one exam
# ──────────────────────────────────────────────────────────────────────────────

class ExamMarkSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST  /api/v1/exams/{exam_id}/marks/       — Teacher/Admin enters marks
      - PATCH /api/v1/exams/{exam_id}/marks/{id}/  — Update marks (draft → submitted)
      - GET   /api/v1/exams/{exam_id}/marks/       — List all mark entries for an exam

    Rules from model:
      - marks_obtained can be null if the student is absent (is_absent=True)
      - entered_by is injected by the view from request.user
      - updated_by tracks the admin who overrides a submitted entry
    """

    exam_name = serializers.CharField(source="exam_subject.exam.name", read_only=True)
    subject_name = serializers.CharField(source="exam_subject.subject.name", read_only=True)
    class_name = serializers.CharField(source="exam_subject.class_id.name", read_only=True)
    max_marks = serializers.DecimalField(
        source="exam_subject.max_marks",
        max_digits=6,
        decimal_places=2,
        read_only=True,
    )
    pass_marks = serializers.DecimalField(
        source="exam_subject.pass_marks",
        max_digits=6,
        decimal_places=2,
        read_only=True,
    )
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    entered_by_name = serializers.CharField(source="entered_by.full_name", read_only=True, default=None)
    updated_by_name = serializers.CharField(source="updated_by.full_name", read_only=True, default=None)

    class Meta:
        model = ExamMark
        fields = [
            "id",
            "exam_subject",
            "exam_name",
            "subject_name",
            "class_name",
            "max_marks",
            "pass_marks",
            "student",
            "student_name",
            "admission_number",
            "marks_obtained",
            "grade",
            "is_absent",
            "entry_status",
            "remarks",
            "entered_by",
            "entered_by_name",
            "updated_by",
            "updated_by_name",
            "entered_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "exam_name",
            "subject_name",
            "class_name",
            "max_marks",
            "pass_marks",
            "student_name",
            "admission_number",
            "entered_by",
            "entered_by_name",
            "updated_by",
            "updated_by_name",
            "entered_at",
            "updated_at",
        ]

    def validate(self, data):
        is_absent = data.get("is_absent", getattr(self.instance, "is_absent", False))
        marks_obtained = data.get("marks_obtained", getattr(self.instance, "marks_obtained", None))
        exam_subject = data.get("exam_subject", getattr(self.instance, "exam_subject", None))

        # If not absent, marks must be provided
        if not is_absent and marks_obtained is None:
            raise serializers.ValidationError(
                {"marks_obtained": "Marks are required when the student is not absent."}
            )

        # If absent, marks_obtained should be null
        if is_absent and marks_obtained is not None:
            raise serializers.ValidationError(
                {"marks_obtained": "Marks must be empty when the student is marked absent."}
            )

        # Marks cannot exceed max_marks
        if marks_obtained is not None and exam_subject is not None:
            if marks_obtained > exam_subject.max_marks:
                raise serializers.ValidationError(
                    {"marks_obtained": "Marks obtained cannot exceed the maximum marks."}
                )
            if marks_obtained < 0:
                raise serializers.ValidationError(
                    {"marks_obtained": "Marks obtained cannot be negative."}
                )

        # Duplicate check for (exam_subject, student)
        student = data.get("student", getattr(self.instance, "student", None))
        if exam_subject and student:
            qs = ExamMark.objects.filter(exam_subject=exam_subject, student=student)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Marks for this student in this exam subject have already been entered."
                )

        return data


class ExamMarkListSerializer(serializers.ModelSerializer):
    """
    Compact read-only serializer for bulk mark listings (e.g., all students in one exam subject).
    """

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    subject_name = serializers.CharField(source="exam_subject.subject.name", read_only=True)
    max_marks = serializers.DecimalField(
        source="exam_subject.max_marks",
        max_digits=6,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = ExamMark
        fields = [
            "id",
            "exam_subject",
            "student",
            "student_name",
            "admission_number",
            "subject_name",
            "marks_obtained",
            "max_marks",
            "grade",
            "is_absent",
            "entry_status",
            "remarks",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Table 22: StudentPerformanceNote — Teacher qualitative feedback
# ──────────────────────────────────────────────────────────────────────────────

class StudentPerformanceNoteSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST  /api/v1/students/{id}/performance-notes/       — Teacher/Admin adds a note
      - PATCH /api/v1/students/{id}/performance-notes/{id}/  — Author updates note
      - GET   /api/v1/students/{id}/performance-notes/       — List notes for a student

    Rules:
      - teacher field is injected by the view from request.user
      - Teachers can only write notes for students in their assigned classes
        (enforced in the view, not the serializer)
      - subject and exam are optional links
    """

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True, default=None)
    subject_name = serializers.CharField(source="subject.name", read_only=True, default=None)
    exam_name = serializers.CharField(source="exam.name", read_only=True, default=None)

    class Meta:
        model = StudentPerformanceNote
        fields = [
            "id",
            "student",
            "student_name",
            "subject",
            "subject_name",
            "exam",
            "exam_name",
            "teacher",
            "teacher_name",
            "note_type",
            "note_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "teacher",
            "teacher_name",
            "subject_name",
            "exam_name",
            "created_at",
            "updated_at",
        ]


class StudentPerformanceNoteListSerializer(serializers.ModelSerializer):
    """
    Compact read-only view for listing performance notes.
    """

    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True, default=None)
    subject_name = serializers.CharField(source="subject.name", read_only=True, default=None)
    exam_name = serializers.CharField(source="exam.name", read_only=True, default=None)

    class Meta:
        model = StudentPerformanceNote
        fields = [
            "id",
            "student",
            "subject",
            "subject_name",
            "exam",
            "exam_name",
            "teacher",
            "teacher_name",
            "note_type",
            "note_text",
            "created_at",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Table 23: StudentSuccessNote — Success Manager interventions
# ──────────────────────────────────────────────────────────────────────────────

class StudentSuccessNoteSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST  /api/v1/students/{id}/success-notes/       — Success Manager logs an intervention
      - PATCH /api/v1/students/{id}/success-notes/{id}/  — Update note status / follow-up
      - GET   /api/v1/students/{id}/success-notes/       — List notes for a student

    Rules:
      - success_manager is injected by the view from request.user
      - Only Success Managers and Admins can write/read these notes
        (enforced in the view via IsSuccessManager | IsAdmin permission)
    """

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    success_manager_name = serializers.CharField(
        source="success_manager.full_name", read_only=True, default=None
    )

    class Meta:
        model = StudentSuccessNote
        fields = [
            "id",
            "student",
            "student_name",
            "success_manager",
            "success_manager_name",
            "category",
            "severity",
            "title",
            "note_text",
            "follow_up_date",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "success_manager",
            "success_manager_name",
            "created_at",
            "updated_at",
        ]


class StudentSuccessNoteListSerializer(serializers.ModelSerializer):
    """
    Compact read-only view for listing success notes.
    """

    success_manager_name = serializers.CharField(
        source="success_manager.full_name", read_only=True, default=None
    )

    class Meta:
        model = StudentSuccessNote
        fields = [
            "id",
            "student",
            "success_manager",
            "success_manager_name",
            "category",
            "severity",
            "title",
            "note_text",
            "follow_up_date",
            "status",
            "created_at",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Table 24: GradingScheme — Percentage-to-grade bands
# ──────────────────────────────────────────────────────────────────────────────

class GradingSchemeSerializer(serializers.ModelSerializer):
    """
    Used for:
      - POST   /api/v1/grading-schemes/       — Admin creates a grade band
      - PUT    /api/v1/grading-schemes/{id}/  — Admin updates a band
      - DELETE /api/v1/grading-schemes/{id}/  — Admin removes a band (hard delete OK — config data)
      - GET    /api/v1/grading-schemes/       — List all active bands

    Validations:
      - min_percent must be less than max_percent
      - Overlapping bands for the same scheme name are not checked here
        (the admin is responsible for maintaining clean config data)
    """

    class Meta:
        model = GradingScheme
        fields = [
            "id",
            "name",
            "min_percent",
            "max_percent",
            "grade",
            "grade_point",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        min_pct = data.get("min_percent", getattr(self.instance, "min_percent", None))
        max_pct = data.get("max_percent", getattr(self.instance, "max_percent", None))

        if min_pct is not None and max_pct is not None:
            if min_pct >= max_pct:
                raise serializers.ValidationError(
                    {"min_percent": "min_percent must be less than max_percent."}
                )

        return data


# ──────────────────────────────────────────────────────────────────────────────
# Table 25: StudentAnalysisSnapshot — Cached computed growth data
# ──────────────────────────────────────────────────────────────────────────────

class StudentAnalysisSnapshotSerializer(serializers.ModelSerializer):
    """
    Used for:
      - GET /api/v1/students/{id}/snapshots/ — List cached performance snapshots for a student

    These records are typically created by a background job / management command,
    not through a regular API POST. The serializer is primarily used for reading.
    For admin override, POST is also supported.

    subject_breakdown is a JSON field — the API accepts and returns it as-is (dict).
    """

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    exam_name = serializers.CharField(source="exam.name", read_only=True, default=None)

    class Meta:
        model = StudentAnalysisSnapshot
        fields = [
            "id",
            "student",
            "student_name",
            "academic_year",
            "academic_year_name",
            "exam",
            "exam_name",
            "average_percent",
            "rank_in_section",
            "subject_breakdown",
            "trend",
            "generated_at",
        ]
        read_only_fields = ["id", "student_name", "academic_year_name", "exam_name", "generated_at"]
