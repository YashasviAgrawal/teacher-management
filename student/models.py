import uuid

from django.conf import settings
from django.db import models


# ──────────────────────────────────────────────────────────────────────────────
# Table 16: students — Student Identity
# ──────────────────────────────────────────────────────────────────────────────

class Student(models.Model):
    """
    The student's identity — stable information that does not change year to year.
    Created and managed by the Admin.
    """

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        TRANSFERRED = "transferred", "Transferred"
        GRADUATED = "graduated", "Graduated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admission_number = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=120)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    guardian_name = models.CharField(max_length=120)
    guardian_contact = models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)
    photo_url = models.CharField(max_length=255, blank=True, null=True)
    admission_date = models.DateField()
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.ACTIVE
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "students"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"


# ──────────────────────────────────────────────────────────────────────────────
# Table 17: student_enrollments — Class placement per academic year
# ──────────────────────────────────────────────────────────────────────────────

class StudentEnrollment(models.Model):
    """
    Links a student to a class + section for one academic year.
    This is what makes year-end promotion and history possible.
    """

    class EnrollmentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        PROMOTED = "promoted", "Promoted"
        REPEATED = "repeated", "Repeated"
        GRADUATED = "graduated", "Graduated"
        TRANSFERRED = "transferred", "Transferred"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    class_id = models.ForeignKey(
        "app1.Class",
        on_delete=models.PROTECT,
        related_name="student_enrollments",
        db_column="class_id",
    )
    section = models.ForeignKey(
        "app1.Section",
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )
    academic_year = models.ForeignKey(
        "app1.AcademicYear",
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )
    roll_number = models.CharField(max_length=20)
    status = models.CharField(
        max_length=15,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE,
    )
    enrolled_on = models.DateField()

    class Meta:
        db_table = "student_enrollments"
        unique_together = [("student", "academic_year")]
        ordering = ["-academic_year__start_date"]

    def __str__(self):
        return (
            f"{self.student.full_name} → "
            f"{self.class_id.name}-{self.section.name} ({self.academic_year.name})"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Table 18: student_attendance — Daily attendance per student
# ──────────────────────────────────────────────────────────────────────────────

class StudentAttendance(models.Model):
    """
    Daily attendance — the early-warning signal for at-risk detection.
    One record per student per day.
    """

    class AttendanceStatus(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    reason = models.CharField(max_length=255, blank=True, null=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_attendance_marked",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_attendance"
        unique_together = [("student", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.student.full_name} — {self.date} — {self.get_status_display()}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 19: exams — Exam events
# ──────────────────────────────────────────────────────────────────────────────

class Exam(models.Model):
    """
    The exam event itself (e.g. "Half-Yearly 2025–26").
    School-wide — per-class details live in ExamSubject.
    """

    class ExamType(models.TextChoices):
        UNIT_TEST = "unit_test", "Unit Test"
        MID_TERM = "mid_term", "Mid Term"
        FINAL = "final", "Final"
        PRACTICAL = "practical", "Practical"

    class ExamStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"
        PUBLISHED = "published", "Published"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=20, choices=ExamType.choices)
    academic_year = models.ForeignKey(
        "app1.AcademicYear",
        on_delete=models.PROTECT,
        related_name="exams",
    )
    term = models.CharField(max_length=20, blank=True, null=True)
    weightage = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True,
        help_text="Percent this exam contributes to the overall grade",
    )
    status = models.CharField(
        max_length=15, choices=ExamStatus.choices, default=ExamStatus.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="exams_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exams"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_exam_type_display()}) — {self.academic_year.name}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 20: exam_subjects — Per-class subject papers under an exam
# ──────────────────────────────────────────────────────────────────────────────

class ExamSubject(models.Model):
    """
    Per-class subject details under an exam — which class sits which subject,
    max marks, pass marks, and the exam date for that paper.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="exam_subjects",
    )
    class_id = models.ForeignKey(
        "app1.Class",
        on_delete=models.PROTECT,
        related_name="exam_subjects",
        db_column="class_id",
    )
    subject = models.ForeignKey(
        "app1.Subject",
        on_delete=models.PROTECT,
        related_name="exam_subjects",
    )
    max_marks = models.DecimalField(max_digits=6, decimal_places=2)
    pass_marks = models.DecimalField(max_digits=6, decimal_places=2)
    exam_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "exam_subjects"
        unique_together = [("exam", "class_id", "subject")]

    def __str__(self):
        return (
            f"{self.exam.name} | {self.class_id.name} — {self.subject.name} "
            f"(Max: {self.max_marks})"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Table 21: exam_marks — A student's marks for one subject in one exam
# ──────────────────────────────────────────────────────────────────────────────

class ExamMark(models.Model):
    """
    A single student's marks for one subject in one exam.
    Carries the draft → submitted → published lifecycle.
    """

    class EntryStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        PUBLISHED = "published", "Published"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam_subject = models.ForeignKey(
        ExamSubject,
        on_delete=models.CASCADE,
        related_name="marks",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="exam_marks",
    )
    marks_obtained = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True,
        help_text="Score (null if absent)",
    )
    grade = models.CharField(
        max_length=5, blank=True, null=True,
        help_text="Grade, computed from grading_schemes",
    )
    is_absent = models.BooleanField(default=False)
    entry_status = models.CharField(
        max_length=12, choices=EntryStatus.choices, default=EntryStatus.DRAFT
    )
    remarks = models.CharField(max_length=255, blank=True, null=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="marks_entered",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marks_updated",
        help_text="Admin who later overrode (audited)",
    )
    entered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "exam_marks"
        unique_together = [("exam_subject", "student")]

    def __str__(self):
        return (
            f"{self.student.full_name} | {self.exam_subject.subject.name} — "
            f"{self.marks_obtained}/{self.exam_subject.max_marks}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Table 22: student_performance_notes — Teacher qualitative feedback
# ──────────────────────────────────────────────────────────────────────────────

class StudentPerformanceNote(models.Model):
    """
    A teacher's qualitative feedback about a student, usually subject-specific.
    Teachers can only write notes for students in their assigned classes/subjects.
    """

    class NoteType(models.TextChoices):
        STRENGTH = "strength", "Strength"
        CONCERN = "concern", "Concern"
        OBSERVATION = "observation", "Observation"
        IMPROVEMENT = "improvement", "Improvement"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="performance_notes",
    )
    subject = models.ForeignKey(
        "app1.Subject",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="student_performance_notes",
        help_text="Subject-specific note (null = general note)",
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="performance_notes",
        help_text="Optional link to an exam",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_performance_notes_authored",
    )
    note_type = models.CharField(max_length=15, choices=NoteType.choices)
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_performance_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.student.full_name} | {self.get_note_type_display()} "
            f"by {self.teacher.full_name}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Table 23: student_success_notes — Success Manager interventions
# ──────────────────────────────────────────────────────────────────────────────

class StudentSuccessNote(models.Model):
    """
    The Success Manager's interventions, flags and follow-ups.
    This is the home of the new Success Manager role.
    """

    class Category(models.TextChoices):
        ACADEMIC = "academic", "Academic"
        BEHAVIORAL = "behavioral", "Behavioral"
        ATTENDANCE = "attendance", "Attendance"
        PARENTAL = "parental", "Parental"
        INTERVENTION = "intervention", "Intervention"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WATCH = "watch", "Watch"
        AT_RISK = "at_risk", "At Risk"

    class NoteStatus(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="success_notes",
    )
    success_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="success_notes_authored",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.INFO
    )
    title = models.CharField(max_length=120, blank=True, null=True)
    note_text = models.TextField()
    follow_up_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=15, choices=NoteStatus.choices, default=NoteStatus.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_success_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.student.full_name} | {self.get_category_display()} "
            f"({self.get_severity_display()})"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Table 24: grading_schemes — Percentage-to-grade bands
# ──────────────────────────────────────────────────────────────────────────────

class GradingScheme(models.Model):
    """
    The percentage-to-grade bands, stored as editable rows so the rule
    can change without touching code.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50,
        help_text="Scheme name (e.g. CBSE Default)",
    )
    min_percent = models.DecimalField(max_digits=5, decimal_places=2)
    max_percent = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5, help_text="Grade label (A1, A2, B1…)")
    grade_point = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True,
        help_text="Optional GPA point",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "grading_schemes"
        ordering = ["-min_percent"]

    def __str__(self):
        return f"{self.name} | {self.grade} ({self.min_percent}%–{self.max_percent}%)"


# ──────────────────────────────────────────────────────────────────────────────
# Table 25: student_analysis_snapshots — Cached computed growth data (optional)
# ──────────────────────────────────────────────────────────────────────────────

class StudentAnalysisSnapshot(models.Model):
    """
    Caches computed growth numbers per term so dashboards load instantly
    instead of recomputing from raw marks each time.
    Optional — can be added later if performance needs it.
    """

    class Trend(models.TextChoices):
        IMPROVING = "improving", "Improving"
        DECLINING = "declining", "Declining"
        STABLE = "stable", "Stable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="analysis_snapshots",
    )
    academic_year = models.ForeignKey(
        "app1.AcademicYear",
        on_delete=models.PROTECT,
        related_name="student_analysis_snapshots",
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="analysis_snapshots",
        help_text="Snapshot point (after which exam)",
    )
    average_percent = models.DecimalField(max_digits=5, decimal_places=2)
    rank_in_section = models.IntegerField(blank=True, null=True)
    subject_breakdown = models.JSONField(
        default=dict,
        help_text="Per-subject scores at this point",
    )
    trend = models.CharField(max_length=15, choices=Trend.choices)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_analysis_snapshots"
        ordering = ["-generated_at"]

    def __str__(self):
        return (
            f"{self.student.full_name} | {self.academic_year.name} — "
            f"{self.get_trend_display()} ({self.average_percent}%)"
        )
