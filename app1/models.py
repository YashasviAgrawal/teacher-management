import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


# ──────────────────────────────────────────────────────────────────────────────
# Table 1: users — Custom User Model
# ──────────────────────────────────────────────────────────────────────────────

class UserManager(BaseUserManager):
    """Custom manager for the User model — uses email as the unique identifier."""

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("The Phone number field is required")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Stores all system users — both Admins and Teachers.
    The role column determines access level throughout the system.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        TEACHER = "teacher", "Teacher"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.TEACHER)
    phone = models.CharField(max_length=15, unique=True)
    qualification = models.TextField(blank=True, null=True)
    profile_photo = models.TextField(blank=True, null=True)  # URL or file path
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Required by Django admin
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
    )

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name", "employee_id"]

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.full_name} ({self.role})"


# ──────────────────────────────────────────────────────────────────────────────
# Table 2: classes
# ──────────────────────────────────────────────────────────────────────────────

class Class(models.Model):
    """
    Defines the school's class levels — Class 9, 10, 11, 12, etc.
    Created and managed by the Admin.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "classes"
        verbose_name_plural = "classes"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────────────────────────────────────
# Table 3: sections
# ──────────────────────────────────────────────────────────────────────────────

class Section(models.Model):
    """
    Sections within each class — A, B, C.
    Supports multi-section tracking per class.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class_id = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="sections",
        db_column="class_id",
    )
    name = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sections"
        unique_together = [("class_id", "name")]  # Section name unique within a class
        ordering = ["class_id", "name"]

    def __str__(self):
        return f"{self.class_id.name} - {self.name}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 4: subjects
# ──────────────────────────────────────────────────────────────────────────────

class Subject(models.Model):
    """
    All subjects taught at the school — Physics, Chemistry, Mathematics, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subjects"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────────────────────────────────────
# Table 9: academic_years  (defined before teacher_assignments because it's a FK)
# ──────────────────────────────────────────────────────────────────────────────

class AcademicYear(models.Model):
    """
    Defines the school's academic year — the foundation for all pacing calculations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)  # e.g., '2025-26'
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)  # Only one can be current
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_years"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────────────────────────────────────
# Table 5: teacher_assignments
# ──────────────────────────────────────────────────────────────────────────────

class TeacherAssignment(models.Model):
    """
    Maps which teacher is assigned to which class, section, and subject.
    The core linking table of the system.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assignments",
        limit_choices_to={"role": "teacher"},
    )
    class_id = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="assignments",
        db_column="class_id",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignments_created",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "teacher_assignments"
        unique_together = [
            ("teacher", "class_id", "section", "subject", "academic_year")
        ]
        ordering = ["-assigned_at"]

    def __str__(self):
        return (
            f"{self.teacher.full_name} → "
            f"{self.class_id.name}-{self.section.name} | {self.subject.name}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Table 6: timetable
# ──────────────────────────────────────────────────────────────────────────────

class Timetable(models.Model):
    """
    Defines the period-wise weekly schedule — which teacher goes to which class
    on which day and at what time. Used for planning and reference only;
    session logging is not bound to this.
    """

    class DayOfWeek(models.TextChoices):
        MONDAY = "MON", "Monday"
        TUESDAY = "TUE", "Tuesday"
        WEDNESDAY = "WED", "Wednesday"
        THURSDAY = "THU", "Thursday"
        FRIDAY = "FRI", "Friday"
        SATURDAY = "SAT", "Saturday"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher_assignment = models.ForeignKey(
        TeacherAssignment,
        on_delete=models.CASCADE,
        related_name="timetable_slots",
    )
    day_of_week = models.CharField(max_length=3, choices=DayOfWeek.choices)
    period_number = models.SmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "timetable"
        ordering = ["day_of_week", "period_number"]

    def __str__(self):
        return (
            f"{self.get_day_of_week_display()} | Period {self.period_number} | "
            f"{self.start_time} - {self.end_time}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Table 7: chapters
# ──────────────────────────────────────────────────────────────────────────────

class Chapter(models.Model):
    """
    Chapters defined for each subject.
    Created by the Admin — teachers have read-only access.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="chapters",
    )
    name = models.CharField(max_length=200)
    order_index = models.SmallIntegerField()
    total_periods_required = models.SmallIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chapters"
        ordering = ["subject", "order_index"]

    def __str__(self):
        return f"{self.subject.name} | Ch {self.order_index}: {self.name}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 8: subtopics
# ──────────────────────────────────────────────────────────────────────────────

class SubTopic(models.Model):
    """
    Subtopics within each chapter. This is the most granular level —
    teachers mark completion status at the subtopic level.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="subtopics",
    )
    name = models.CharField(max_length=250)
    order_index = models.SmallIntegerField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subtopics"
        ordering = ["chapter", "order_index"]

    def __str__(self):
        return f"{self.chapter.name} | {self.order_index}. {self.name}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 10: calendar_events
# ──────────────────────────────────────────────────────────────────────────────

class CalendarEvent(models.Model):
    """
    School calendar entries — holidays, exam periods, and events.
    The pacing engine skips these dates when calculating effective teaching days.
    """

    class EventType(models.TextChoices):
        HOLIDAY = "holiday", "Holiday"
        EXAM = "exam", "Exam"
        EVENT = "event", "Event"
        WORKING_SUNDAY = "working_sunday", "Working Sunday"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="calendar_events",
    )
    title = models.CharField(max_length=200)
    event_date = models.DateField()  # Start date
    end_date = models.DateField(blank=True, null=True)  # NULL = single day
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    affects_all = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calendar_events"
        ordering = ["event_date"]

    def __str__(self):
        return f"{self.title} ({self.get_event_type_display()}) — {self.event_date}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 11: syllabus_pacing
# ──────────────────────────────────────────────────────────────────────────────

class SyllabusPacing(models.Model):
    """
    System-calculated pacing data — expected chapter deadlines and
    On Track / Behind / Ahead status.
    Updated automatically on a nightly schedule.
    """

    class PacingStatus(models.TextChoices):
        ON_TRACK = "on_track", "On Track"
        BEHIND = "behind", "Behind"
        AHEAD = "ahead", "Ahead"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher_assignment = models.ForeignKey(
        TeacherAssignment,
        on_delete=models.CASCADE,
        related_name="pacing_records",
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="pacing_records",
    )
    expected_start_date = models.DateField(blank=True, null=True)
    expected_end_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=15,
        choices=PacingStatus.choices,
        default=PacingStatus.ON_TRACK,
    )
    days_behind = models.SmallIntegerField(
        blank=True,
        null=True,
        help_text="Positive = behind, Negative = ahead, 0 = on track",
    )
    last_calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "syllabus_pacing"
        unique_together = [("teacher_assignment", "chapter")]

    def __str__(self):
        return f"{self.teacher_assignment} | {self.chapter.name} — {self.get_status_display()}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 12: session_logs
# ──────────────────────────────────────────────────────────────────────────────

class SessionLog(models.Model):
    """
    The parent record for every teacher activity — Teaching, Revision, Q&A, or Test.
    Session logging is fully manual and is not tied to the timetable.
    """

    class SessionType(models.TextChoices):
        TEACHING = "teaching", "Teaching"
        REVISION = "revision", "Revision"
        QA = "qa", "Q&A"
        TEST = "test", "Test"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher_assignment = models.ForeignKey(
        TeacherAssignment,
        on_delete=models.CASCADE,
        related_name="session_logs",
    )
    session_date = models.DateField()
    period_number = models.IntegerField(
        blank=True,
        null=True,
        help_text="Which period the teacher attended the class (e.g., 1, 2, 3)",
    )
    session_type = models.CharField(max_length=10, choices=SessionType.choices)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session_logs"
        ordering = ["-session_date", "-created_at"]

    def __str__(self):
        return (
            f"{self.teacher_assignment.teacher.full_name} | "
            f"{self.get_session_type_display()} — {self.session_date}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Table 13: session_topic_details
# ──────────────────────────────────────────────────────────────────────────────

class SessionTopicDetail(models.Model):
    """
    The granular detail of each session — which subtopics or chapters were covered
    and what their completion status is.

    Rules:
      - Teaching session → subtopic_id required
      - Revision → both may apply
      - Q&A / Test → chapter_id required
    """

    class CompletionStatus(models.TextChoices):
        COMPLETE = "complete", "Complete"
        PARTIAL = "partial", "Partial"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        SessionLog,
        on_delete=models.CASCADE,
        related_name="topic_details",
    )
    subtopic = models.ForeignKey(
        SubTopic,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="session_details",
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="session_details",
    )
    status = models.CharField(max_length=10, choices=CompletionStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "session_topic_details"

    def __str__(self):
        target = self.subtopic.name if self.subtopic else self.chapter.name
        return f"{target} — {self.get_status_display()}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 14: teacher_attendance
# ──────────────────────────────────────────────────────────────────────────────

class TeacherAttendance(models.Model):
    """
    Tracks daily teacher attendance.
    Absent days are factored into the syllabus pacing calculation.
    """

    class AttendanceStatus(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        HALF_DAY = "half_day", "Half Day"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        limit_choices_to={"role": "teacher"},
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    reason = models.CharField(max_length=200, blank=True, null=True)
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="attendance_marked",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "teacher_attendance"
        unique_together = [("teacher", "date")]  # One record per teacher per day
        ordering = ["-date"]

    def __str__(self):
        return f"{self.teacher.full_name} — {self.date} — {self.get_status_display()}"


# ──────────────────────────────────────────────────────────────────────────────
# Table 15: audit_logs
# ──────────────────────────────────────────────────────────────────────────────

class AuditLog(models.Model):
    """
    An immutable log of every significant action performed in the system.
    No user can delete or modify these records. Provides complete accountability.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    user_role = models.CharField(max_length=20)  # Snapshot of role at action time
    action_type = models.CharField(max_length=50)  # e.g., 'TOPIC_MARKED', 'TEACHER_CREATED'
    entity_type = models.CharField(max_length=50)  # e.g., 'subtopic', 'chapter', 'user'
    entity_id = models.UUIDField(blank=True, null=True)
    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-timestamp"]
        # Prevent deletion and modification at the Django level
        managed = True

    def __str__(self):
        return f"[{self.timestamp}] {self.action_type} by {self.user} on {self.entity_type}"
