from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from django.db.models import Q
from .models import AcademicYear, CalendarEvent, Chapter, Class, Section, SessionLog, SessionTopicDetail, Subject, SubTopic, SyllabusPacing, TeacherAssignment, Timetable, User, TeacherAttendance, AuditLog


# ──────────────────────────────────────────────────────────────────────────────
# Login Serializer — POST /api/v1/auth/login/
# ──────────────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    """
    Accepts phone + password, validates credentials,
    and returns the authenticated user object.
    """

    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone = data.get("phone")
        password = data.get("password")

        if not phone or not password:
            raise serializers.ValidationError("Both phone number and password are required.")

        # Lookup the user by phone number
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid phone number or password.")

        # Check the password
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid phone number or password.")

        # Check if the account is active
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated. Contact the admin.")

        data["user"] = user
        return data


# ──────────────────────────────────────────────────────────────────────────────
# Change Password Serializer — POST /api/v1/auth/change-password/
# ──────────────────────────────────────────────────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    """
    Requires the current password + new password.
    Validates that the current password is correct before allowing the change.
    """

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("New password must be at least 8 characters.")
        return value

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


# ──────────────────────────────────────────────────────────────────────────────
# User Profile Serializer — GET /api/v1/auth/me/
# ──────────────────────────────────────────────────────────────────────────────

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the currently logged-in user's profile.
    Returns all relevant user fields.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "employee_id",
            "role",
            "phone",
            "qualification",
            "profile_photo",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Teacher Management Serializers — /api/v1/users/
# ──────────────────────────────────────────────────────────────────────────────

class TeacherCreateSerializer(serializers.ModelSerializer):
    """
    Admin-only: Create a new teacher account.
    Password is write-only and gets hashed before saving.
    """

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "employee_id",
            "phone",
            "password",
            "role",
            "qualification",
            "profile_photo",
        ]
        extra_kwargs = {
            "role": {"default": User.Role.TEACHER},
        }

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_employee_id(self, value):
        if User.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError("This Employee ID is already taken.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()
        return user


class TeacherListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing teachers.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "employee_id",
            "phone",
            "role",
            "qualification",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = fields


class TeacherDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for a single teacher — Admin read.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "employee_id",
            "role",
            "phone",
            "qualification",
            "profile_photo",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]


class TeacherUpdateSerializer(serializers.ModelSerializer):
    """
    Admin-only: Update a teacher's information.
    Phone and employee_id are validated for uniqueness on change.
    """

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "employee_id",
            "phone",
            "qualification",
            "profile_photo",
            "role",
        ]

    def validate_phone(self, value):
        qs = User.objects.filter(phone=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_employee_id(self, value):
        qs = User.objects.filter(employee_id=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This Employee ID is already taken.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """
    Admin-only: Force-reset a teacher's password.
    No current password required.
    """

    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def save(self, user):
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class UpdateOwnProfileSerializer(serializers.ModelSerializer):
    """
    Both roles: Users can update only their own phone and profile photo.
    """

    class Meta:
        model = User
        fields = ["phone", "profile_photo"]

    def validate_phone(self, value):
        qs = User.objects.filter(phone=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value


# ──────────────────────────────────────────────────────────────────────────────
# School Structure Serializers — /api/v1/classes/ | /sections/ | /subjects/
# ──────────────────────────────────────────────────────────────────────────────

class ClassSerializer(serializers.ModelSerializer):
    """
    Used for both listing and creating/updating classes.
    """

    class Meta:
        model = Class
        fields = ["id", "name", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        qs = Class.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A class with this name already exists.")
        return value


class SectionSerializer(serializers.ModelSerializer):
    """
    Includes a read-only class_name field for display.
    Filterable by class_id query param on list.
    """

    class_name = serializers.CharField(source="class_id.name", read_only=True)

    class Meta:
        model = Section
        fields = ["id", "class_id", "class_name", "name", "is_active", "created_at"]
        read_only_fields = ["id", "class_name", "created_at"]

    def validate(self, data):
        class_obj = data.get("class_id", getattr(self.instance, "class_id", None))
        name = data.get("name", getattr(self.instance, "name", None))
        qs = Section.objects.filter(class_id=class_obj, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"name": f"Section '{name}' already exists in this class."}
            )
        return data


class SubjectSerializer(serializers.ModelSerializer):
    """
    Used for both listing and creating/updating subjects.
    """

    class Meta:
        model = Subject
        fields = ["id", "name", "code", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        qs = Subject.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A subject with this name already exists.")
        return value

    def validate_code(self, value):
        if not value:
            return value
        qs = Subject.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A subject with this code already exists.")
        return value


# ──────────────────────────────────────────────────────────────────────────────
# Teacher Assignment Serializers — /api/v1/assignments/
# ──────────────────────────────────────────────────────────────────────────────

class AssignmentCreateSerializer(serializers.ModelSerializer):
    """
    Admin-only: Assign a teacher to class + section + subject + academic year.
    Validates:
     - teacher must have role=teacher
     - section must belong to the chosen class
     - no duplicate assignment (same 5-tuple)
    """

    class Meta:
        model = TeacherAssignment
        fields = [
            "id",
            "teacher",
            "class_id",
            "section",
            "subject",
            "academic_year",
        ]
        read_only_fields = ["id"]

    def validate_teacher(self, value):
        if value.role != User.Role.TEACHER:
            raise serializers.ValidationError(
                "Only users with role=teacher can be assigned."
            )
        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot assign an inactive teacher account."
            )
        return value

    def validate(self, data):
        class_obj = data.get("class_id")
        section = data.get("section")

        # Validate section belongs to chosen class
        if class_obj and section:
            if section.class_id != class_obj:
                raise serializers.ValidationError(
                    {"section": "This section does not belong to the selected class."}
                )

        # Duplicate assignment check
        if TeacherAssignment.objects.filter(
            teacher=data.get("teacher"),
            class_id=class_obj,
            section=section,
            subject=data.get("subject"),
            academic_year=data.get("academic_year"),
        ).exists():
            raise serializers.ValidationError(
                "This teacher is already assigned to this class, section, "
                "subject, and academic year."
            )

        return data

    def create(self, validated_data):
        assigned_by = validated_data.pop("assigned_by", None)
        return TeacherAssignment.objects.create(
            **validated_data, assigned_by=assigned_by
        )


class AssignmentListSerializer(serializers.ModelSerializer):
    """
    Compact read-only view used in list responses.
    Embeds names instead of raw UUIDs for readability.
    """

    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    teacher_phone = serializers.CharField(source="teacher.phone", read_only=True)
    class_name = serializers.CharField(source="class_id.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    assigned_by_name = serializers.CharField(
        source="assigned_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = TeacherAssignment
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "teacher_phone",
            "class_id",
            "class_name",
            "section",
            "section_name",
            "subject",
            "subject_name",
            "academic_year",
            "academic_year_name",
            "is_active",
            "assigned_by",
            "assigned_by_name",
            "assigned_at",
        ]
        read_only_fields = fields


class AssignmentDetailSerializer(AssignmentListSerializer):
    """
    Full detail view — same fields as list, used for single-object responses.
    Inherits all fields from AssignmentListSerializer.
    """
    pass


# ──────────────────────────────────────────────────────────────────────────────
# Timetable Serializers — /api/v1/timetable/
# ──────────────────────────────────────────────────────────────────────────────

class TimetableCreateSerializer(serializers.ModelSerializer):
    """
    Create/Update a timetable period slot.
    Validates that there are no overlaps for the teacher or the section.
    """

    class Meta:
        model = Timetable
        fields = [
            "id",
            "teacher_assignment",
            "day_of_week",
            "period_number",
            "start_time",
            "end_time",
            "room",
            "is_active"
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        assignment = data.get("teacher_assignment") or getattr(self.instance, "teacher_assignment", None)
        day = data.get("day_of_week") or getattr(self.instance, "day_of_week", None)
        start_t = data.get("start_time") or getattr(self.instance, "start_time", None)
        end_t = data.get("end_time") or getattr(self.instance, "end_time", None)

        if start_t and end_t and start_t >= end_t:
            raise serializers.ValidationError("start_time must be before end_time")

        # Overlap queries
        if assignment and day and start_t and end_t:
            base_qs = Timetable.objects.filter(
                day_of_week=day,
                is_active=True,
                start_time__lt=end_t,
                end_time__gt=start_t
            )

            if self.instance:
                base_qs = base_qs.exclude(pk=self.instance.pk)

            # 1. Teacher Overlap Check
            teacher_overlap = base_qs.filter(teacher_assignment__teacher=assignment.teacher).exists()
            if teacher_overlap:
                raise serializers.ValidationError("Teacher already has a class scheduled at this time on this day.")

            # 2. Section Overlap Check
            section_overlap = base_qs.filter(
                teacher_assignment__class_id=assignment.class_id,
                teacher_assignment__section=assignment.section
            ).exists()
            if section_overlap:
                raise serializers.ValidationError("This class and section already have a class scheduled at this time on this day.")

        return data


class TimetableListSerializer(serializers.ModelSerializer):
    """
    Read-only serializer returning detailed timetable info.
    """
    teacher_name = serializers.CharField(source="teacher_assignment.teacher.full_name", read_only=True)
    class_name = serializers.CharField(source="teacher_assignment.class_id.name", read_only=True)
    section_name = serializers.CharField(source="teacher_assignment.section.name", read_only=True)
    subject_name = serializers.CharField(source="teacher_assignment.subject.name", read_only=True)

    class Meta:
        model = Timetable
        fields = [
            "id",
            "teacher_assignment",
            "teacher_name",
            "class_name",
            "section_name",
            "subject_name",
            "day_of_week",
            "period_number",
            "start_time",
            "end_time",
            "room",
            "is_active"
        ]
        read_only_fields = fields


class TimetableDetailSerializer(TimetableListSerializer):
    pass


# ──────────────────────────────────────────────────────────────────────────────
# Syllabus Serializers — /api/v1/chapters/ | /api/v1/subtopics/
# ──────────────────────────────────────────────────────────────────────────────

class SubTopicSerializer(serializers.ModelSerializer):
    chapter_name = serializers.CharField(source="chapter.name", read_only=True)

    class Meta:
        model = SubTopic
        fields = [
            "id",
            "chapter",
            "chapter_name",
            "name",
            "order_index",
            "description",
            "is_active",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class ChapterSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = Chapter
        fields = [
            "id",
            "subject",
            "subject_name",
            "name",
            "order_index",
            "total_periods_required",
            "description",
            "is_active",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class FullSyllabusChapterSerializer(serializers.ModelSerializer):
    subtopics = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = [
            "id",
            "name",
            "order_index",
            "total_periods_required",
            "description",
            "subtopics"
        ]

    def get_subtopics(self, obj):
        # Only return active subtopics
        active_subtopics = obj.subtopics.filter(is_active=True).order_by("order_index")
        return SubTopicSerializer(active_subtopics, many=True).data


# ──────────────────────────────────────────────────────────────────────────────
# Academic Year & Calendar Serializers
# ──────────────────────────────────────────────────────────────────────────────

class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["id", "name", "start_date", "end_date", "is_current", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        start_date = data.get("start_date") or getattr(self.instance, "start_date", None)
        end_date = data.get("end_date") or getattr(self.instance, "end_date", None)

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("start_date must be before end_date")
        return data


class CalendarEventSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "academic_year",
            "academic_year_name",
            "title",
            "event_date",
            "end_date",
            "event_type",
            "affects_all",
            "description",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        event_date = data.get("event_date") or getattr(self.instance, "event_date", None)
        end_date = data.get("end_date") or getattr(self.instance, "end_date", None)

        if event_date and end_date and event_date > end_date:
            raise serializers.ValidationError("event_date (start) cannot be after end_date")
        return data


# ──────────────────────────────────────────────────────────────────────────────
# Pacing Serializers — /api/v1/pacing/
# ──────────────────────────────────────────────────────────────────────────────

class SyllabusPacingSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher_assignment.teacher.full_name", read_only=True)
    class_name = serializers.CharField(source="teacher_assignment.class_id.name", read_only=True)
    section_name = serializers.CharField(source="teacher_assignment.section.name", read_only=True)
    subject_name = serializers.CharField(source="teacher_assignment.subject.name", read_only=True)
    chapter_name = serializers.CharField(source="chapter.name", read_only=True)

    class Meta:
        model = SyllabusPacing
        fields = [
            "id",
            "teacher_assignment",
            "teacher_name",
            "class_name",
            "section_name",
            "subject_name",
            "chapter",
            "chapter_name",
            "expected_start_date",
            "expected_end_date",
            "status",
            "days_behind",
            "last_calculated_at"
        ]
        read_only_fields = ["id", "last_calculated_at"]


# ──────────────────────────────────────────────────────────────────────────────
# Session Tracking Serializers — /api/v1/sessions/
# ──────────────────────────────────────────────────────────────────────────────

class SessionTopicDetailSerializer(serializers.ModelSerializer):
    subtopic_name = serializers.CharField(source="subtopic.name", read_only=True)
    chapter_name = serializers.CharField(source="chapter.name", read_only=True)

    class Meta:
        model = SessionTopicDetail
        fields = ["id", "session", "subtopic", "subtopic_name", "chapter", "chapter_name", "status", "created_at"]
        read_only_fields = ["id", "session", "created_at"]


class SessionLogSerializer(serializers.ModelSerializer):
    topic_details = SessionTopicDetailSerializer(many=True, read_only=True)
    teacher_name = serializers.CharField(source="teacher_assignment.teacher.full_name", read_only=True)
    class_name = serializers.CharField(source="teacher_assignment.class_id.name", read_only=True)
    subject_name = serializers.CharField(source="teacher_assignment.subject.name", read_only=True)

    class Meta:
        model = SessionLog
        fields = [
            "id",
            "teacher_assignment",
            "teacher_name",
            "class_name",
            "subject_name",
            "session_date",
            "period_number",
            "session_type",
            "notes",
            "topic_details",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        # Teacher same-day edit rule validation is handled in the views since it requires request.user context
        return data


# ──────────────────────────────────────────────────────────────────────────────
# Teacher Attendance Serializer — /api/v1/attendance/
# ──────────────────────────────────────────────────────────────────────────────

class TeacherAttendanceSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    teacher_employee_id = serializers.CharField(source="teacher.employee_id", read_only=True)
    marked_by_name = serializers.CharField(source="marked_by.full_name", read_only=True, default=None)

    class Meta:
        model = TeacherAttendance
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "teacher_employee_id",
            "date",
            "status",
            "reason",
            "marked_by",
            "marked_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "marked_by", "created_at"]

    def validate_teacher(self, value):
        if value.role != User.Role.TEACHER:
            raise serializers.ValidationError("Attendance can only be recorded for users with role='teacher'.")
        if not value.is_active:
            raise serializers.ValidationError("Cannot record attendance for an inactive teacher account.")
        return value

    def validate(self, data):
        # Enforce unique constraint check (teacher, date) during creation/updating
        teacher = data.get("teacher") or (self.instance.teacher if self.instance else None)
        date_val = data.get("date") or (self.instance.date if self.instance else None)
        
        if teacher and date_val:
            qs = TeacherAttendance.objects.filter(teacher=teacher, date=date_val)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "An attendance record already exists for this teacher on this date."
                )
        return data


# ──────────────────────────────────────────────────────────────────────────────
# Audit Trail Serializer — /api/v1/audit-logs/
# ──────────────────────────────────────────────────────────────────────────────

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True, default="System")

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_name",
            "user_role",
            "action_type",
            "entity_type",
            "entity_id",
            "old_value",
            "new_value",
            "ip_address",
            "timestamp",
        ]
        read_only_fields = fields


