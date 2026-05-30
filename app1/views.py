from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AcademicYear, CalendarEvent, Chapter, Class, Section, SessionLog, SessionTopicDetail, Subject, SubTopic, SyllabusPacing, TeacherAssignment, Timetable, User, TeacherAttendance, AuditLog
from .permissions import IsAdmin, IsTeacher
from .serializers import (
    AcademicYearSerializer,
    AssignmentCreateSerializer,
    AssignmentDetailSerializer,
    AssignmentListSerializer,
    AuditLogSerializer,
    CalendarEventSerializer,
    ChangePasswordSerializer,
    ChapterSerializer,
    ClassSerializer,
    FullSyllabusChapterSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    SectionSerializer,
    SessionLogSerializer,
    SessionTopicDetailSerializer,
    SubjectSerializer,
    SubTopicSerializer,
    SyllabusPacingSerializer,
    TeacherAttendanceSerializer,
    TeacherCreateSerializer,
    TeacherDetailSerializer,
    TeacherListSerializer,
    TeacherUpdateSerializer,
    TimetableCreateSerializer,
    TimetableDetailSerializer,
    TimetableListSerializer,
    UpdateOwnProfileSerializer,
    UserProfileSerializer,
)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/login/
# Access: 🟡 Both (no auth required — this IS the login)
# ──────────────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    """
    Login with phone number and password.
    Returns JWT access and refresh tokens.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        # Update last_login timestamp
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                "user": {
                    "id": str(user.id),
                    "full_name": user.full_name,
                    "role": user.role,
                    "phone": user.phone,
                },
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/logout/
# Access: 🟡 Both (must be logged in)
# ──────────────────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    Logout — blacklists the refresh token so it can't be used again.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message": "Logout successful. Token has been blacklisted."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"error": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/v1/auth/change-password/
# Access: 🟡 Both (must be logged in)
# ──────────────────────────────────────────────────────────────────────────────

class ChangePasswordView(APIView):
    """
    Change password after verifying the current one.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/auth/me/
# Access: 🟡 Both (must be logged in)
# ──────────────────────────────────────────────────────────────────────────────

class MeView(APIView):
    """
    Retrieve the currently logged-in user's profile and role.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# USER MANAGEMENT — /api/v1/users/
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# GET  /api/v1/users/        — List all teachers  (Admin only)
# POST /api/v1/users/        — Create teacher     (Admin only)
# ──────────────────────────────────────────────────────────────────────────────

class TeacherListCreateView(APIView):
    """
    GET  — Returns all users with role=teacher.
             Optional query params: ?is_active=true|false
    POST — Admin creates a new teacher account.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = User.objects.filter(role=User.Role.TEACHER)

        # Optional filter by active status
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        serializer = TeacherListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TeacherCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        teacher = serializer.save(created_by=request.user)
        return Response(
            TeacherDetailSerializer(teacher).data,
            status=status.HTTP_201_CREATED,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/users/{id}/   — Teacher detail  (Admin only)
# PUT /api/v1/users/{id}/   — Update teacher  (Admin only)
# ──────────────────────────────────────────────────────────────────────────────

class TeacherDetailView(APIView):
    """
    GET — Full profile of a single teacher.
    PUT — Update teacher info (name, email, qualification, etc.).
    """

    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk, role=User.Role.TEACHER)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response(
                {"error": "Teacher not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TeacherDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response(
                {"error": "Teacher not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TeacherUpdateSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            TeacherDetailSerializer(user).data,
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/users/{id}/activate/   — Activate teacher   (Admin only)
# ──────────────────────────────────────────────────────────────────────────────

class TeacherActivateView(APIView):
    """
    PATCH — Set a teacher's account to active.
    """

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.TEACHER)
        except User.DoesNotExist:
            return Response(
                {"error": "Teacher not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_active:
            return Response(
                {"message": "Teacher account is already active."},
                status=status.HTTP_200_OK,
            )

        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(
            {"message": f"{user.full_name}'s account has been activated."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/users/{id}/deactivate/ — Deactivate teacher  (Admin only)
# ──────────────────────────────────────────────────────────────────────────────

class TeacherDeactivateView(APIView):
    """
    PATCH — Deactivate a teacher's account — blocks all login attempts.
    """

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.TEACHER)
        except User.DoesNotExist:
            return Response(
                {"error": "Teacher not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_active:
            return Response(
                {"message": "Teacher account is already deactivated."},
                status=status.HTTP_200_OK,
            )

        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(
            {"message": f"{user.full_name}'s account has been deactivated."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/users/{id}/reset-password/ — Force reset password  (Admin only)
# ──────────────────────────────────────────────────────────────────────────────

class TeacherResetPasswordView(APIView):
    """
    PATCH — Admin force-resets a teacher's password.
    Does not require the current password.
    """

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.TEACHER)
        except User.DoesNotExist:
            return Response(
                {"error": "Teacher not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(
            {"message": f"Password for {user.full_name} has been reset successfully."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET   /api/v1/users/me/ — Own profile     (Both)
# PATCH /api/v1/users/me/ — Update own profile — phone + photo only (Both)
# ──────────────────────────────────────────────────────────────────────────────

class MyProfileView(APIView):
    """
    GET   — Returns the logged-in user's full profile.
    PATCH — Allows updating only phone number and profile photo.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UpdateOwnProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            UserProfileSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# SCHOOL STRUCTURE — /api/v1/classes/ | /sections/ | /subjects/
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# GET  /api/v1/classes/      — List all classes   (Both)
# POST /api/v1/classes/      — Create class       (Admin)
# ──────────────────────────────────────────────────────────────────────────────

class ClassListCreateView(APIView):
    """
    GET  — List all classes (both roles see all, including inactive).
    POST — Admin creates a new class.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request):
        queryset = Class.objects.all().order_by("name")
        serializer = ClassSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ClassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# PUT    /api/v1/classes/{id}/ — Update class   (Admin)
# DELETE /api/v1/classes/{id}/ — Soft-delete    (Admin)
# ──────────────────────────────────────────────────────────────────────────────

class ClassDetailView(APIView):
    """
    PUT    — Update a class name or description.
    DELETE — Soft-delete: sets is_active = False.
    """

    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Class.objects.get(pk=pk)
        except Class.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response(
                {"error": "Class not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ClassSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response(
                {"error": "Class not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response(
            {"message": f'Class "{obj.name}" has been deactivated.'},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET  /api/v1/sections/     — List sections ?class_id= (Both)
# POST /api/v1/sections/     — Create section             (Admin)
# ──────────────────────────────────────────────────────────────────────────────

class SectionListCreateView(APIView):
    """
    GET  — List all sections. Filterable by ?class_id=<uuid>.
    POST — Admin creates a section within a class.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request):
        queryset = Section.objects.select_related("class_id").all()

        class_id = request.query_params.get("class_id")
        if class_id:
            queryset = queryset.filter(class_id=class_id)

        serializer = SectionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/v1/sections/{id}/ — Update section (Admin)
# ──────────────────────────────────────────────────────────────────────────────

class SectionDetailView(APIView):
    """
    PUT — Update a section's name or class assignment.
    """

    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Section.objects.select_related("class_id").get(pk=pk)
        except Section.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response(
                {"error": "Section not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SectionSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# GET  /api/v1/subjects/     — List subjects    (Both)
# POST /api/v1/subjects/     — Create subject   (Admin)
# ──────────────────────────────────────────────────────────────────────────────

class SubjectListCreateView(APIView):
    """
    GET  — List all subjects.
    POST — Admin creates a new subject.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request):
        queryset = Subject.objects.all().order_by("name")
        serializer = SubjectSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SubjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# PUT    /api/v1/subjects/{id}/ — Update subject  (Admin)
# DELETE /api/v1/subjects/{id}/ — Soft-delete     (Admin)
# ──────────────────────────────────────────────────────────────────────────────

class SubjectDetailView(APIView):
    """
    PUT    — Update a subject's details.
    DELETE — Soft-delete: sets is_active = False.
    """

    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Subject.objects.get(pk=pk)
        except Subject.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response(
                {"error": "Subject not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SubjectSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response(
                {"error": "Subject not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response(
            {"message": f'Subject "{obj.name}" has been deactivated.'},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# TEACHER ASSIGNMENTS — /api/v1/assignments/
# ──────────────────────────────────────────────────────────────────────────────

class AssignmentListCreateView(APIView):
    """
    GET  — List assignments (Admin). Filterable by teacher, class_id, section, subject, academic_year.
    POST — Create new assignment (Admin).
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = TeacherAssignment.objects.select_related(
            "teacher", "class_id", "section", "subject", "academic_year", "assigned_by"
        ).all()

        # Filters
        teacher = request.query_params.get("teacher")
        class_id = request.query_params.get("class_id")
        section = request.query_params.get("section")
        subject = request.query_params.get("subject")
        academic_year = request.query_params.get("academic_year")

        if teacher:
            queryset = queryset.filter(teacher_id=teacher)
        if class_id:
            queryset = queryset.filter(class_id=class_id)
        if section:
            queryset = queryset.filter(section_id=section)
        if subject:
            queryset = queryset.filter(subject_id=subject)
        if academic_year:
            queryset = queryset.filter(academic_year_id=academic_year)

        serializer = AssignmentListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(assigned_by=request.user)
        return Response(
            AssignmentDetailSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class AssignmentDetailView(APIView):
    """
    GET — Get full assignment details (Admin).
    """

    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return TeacherAssignment.objects.select_related(
                "teacher", "class_id", "section", "subject", "academic_year", "assigned_by"
            ).get(pk=pk)
        except TeacherAssignment.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response(
                {"error": "Assignment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = AssignmentDetailSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AssignmentDeactivateView(APIView):
    """
    PATCH — Soft-delete an assignment (Admin).
    """

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            obj = TeacherAssignment.objects.get(pk=pk)
        except TeacherAssignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not obj.is_active:
            return Response(
                {"message": "Assignment is already deactivated."},
                status=status.HTTP_200_OK,
            )

        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response(
            {"message": "Assignment has been deactivated."},
            status=status.HTTP_200_OK,
        )


class MyAssignmentsView(APIView):
    """
    GET — Teacher gets their own assignments.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = TeacherAssignment.objects.select_related(
            "teacher", "class_id", "section", "subject", "academic_year", "assigned_by"
        ).filter(teacher=request.user, is_active=True)

        serializer = AssignmentListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# TIMETABLE — /api/v1/timetable/
# ──────────────────────────────────────────────────────────────────────────────

class TimetableListCreateView(APIView):
    """
    GET  — List timetable slots (Admin). Filterable by class, teacher, day.
    POST — Add a new timetable slot (Admin).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = Timetable.objects.select_related(
            "teacher_assignment__teacher",
            "teacher_assignment__class_id",
            "teacher_assignment__section",
            "teacher_assignment__subject"
        ).filter(is_active=True).order_by("day_of_week", "start_time")

        # Filters
        day = request.query_params.get("day")
        teacher = request.query_params.get("teacher")
        class_id = request.query_params.get("class_id")

        if day:
            queryset = queryset.filter(day_of_week=day)
        if teacher:
            queryset = queryset.filter(teacher_assignment__teacher_id=teacher)
        if class_id:
            queryset = queryset.filter(teacher_assignment__class_id=class_id)

        serializer = TimetableListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TimetableCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        timetable = serializer.save()
        return Response(
            TimetableDetailSerializer(timetable).data,
            status=status.HTTP_201_CREATED
        )


class TimetableDetailView(APIView):
    """
    PUT    — Update a period slot (change time or room) (Admin).
    DELETE — Remove a period slot (Soft delete) (Admin).
    """
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Timetable.objects.select_related(
                "teacher_assignment__teacher",
                "teacher_assignment__class_id",
                "teacher_assignment__section",
                "teacher_assignment__subject"
            ).get(pk=pk, is_active=True)
        except Timetable.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"error": "Timetable slot not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TimetableCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        timetable = serializer.save()
        return Response(TimetableDetailSerializer(timetable).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"error": "Timetable slot not found."}, status=status.HTTP_404_NOT_FOUND)
        
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response({"message": "Timetable slot deactivated."}, status=status.HTTP_200_OK)


class MyScheduleView(APIView):
    """
    GET — Teacher views their own weekly timetable.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Timetable.objects.select_related(
            "teacher_assignment__teacher",
            "teacher_assignment__class_id",
            "teacher_assignment__section",
            "teacher_assignment__subject"
        ).filter(
            teacher_assignment__teacher=request.user,
            is_active=True
        ).order_by("day_of_week", "start_time")

        serializer = TimetableListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyTodayScheduleView(APIView):
    """
    GET — Teacher views today's periods.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Determine today's day string (e.g. 'MON', 'TUE')
        today_day = timezone.now().strftime('%a').upper()

        queryset = Timetable.objects.select_related(
            "teacher_assignment__teacher",
            "teacher_assignment__class_id",
            "teacher_assignment__section",
            "teacher_assignment__subject"
        ).filter(
            teacher_assignment__teacher=request.user,
            day_of_week=today_day,
            is_active=True
        ).order_by("start_time")

        serializer = TimetableListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# SYLLABUS DEFINITION — /api/v1/chapters/ | /api/v1/subtopics/
# ──────────────────────────────────────────────────────────────────────────────

class ChapterListCreateView(APIView):
    """
    GET  — List chapters (Both). Filterable by subject_id.
    POST — Create new chapter (Admin).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        queryset = Chapter.objects.select_related("subject").filter(is_active=True).order_by("subject", "order_index")
        subject_id = request.query_params.get("subject_id")
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        serializer = ChapterSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ChapterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChapterDetailView(APIView):
    """
    PUT    — Update a chapter (Admin).
    DELETE — Soft delete a chapter (Admin).
    """
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Chapter.objects.get(pk=pk, is_active=True)
        except Chapter.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"error": "Chapter not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ChapterSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"error": "Chapter not found."}, status=status.HTTP_404_NOT_FOUND)
        
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response({"message": "Chapter soft deleted."}, status=status.HTTP_200_OK)


class SubTopicListCreateView(APIView):
    """
    GET  — List subtopics (Both). Filterable by chapter_id.
    POST — Create new subtopic (Admin).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        queryset = SubTopic.objects.select_related("chapter").filter(is_active=True).order_by("chapter", "order_index")
        chapter_id = request.query_params.get("chapter_id")
        if chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)
        
        serializer = SubTopicSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SubTopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SubTopicDetailView(APIView):
    """
    PUT    — Update a subtopic (Admin).
    DELETE — Soft delete a subtopic (Admin).
    """
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return SubTopic.objects.get(pk=pk, is_active=True)
        except SubTopic.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"error": "SubTopic not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = SubTopicSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"error": "SubTopic not found."}, status=status.HTTP_404_NOT_FOUND)
        
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response({"message": "SubTopic soft deleted."}, status=status.HTTP_200_OK)


class FullSyllabusView(APIView):
    """
    GET — Get the full nested syllabus (Chapters + Subtopics) for a given Subject ID.
    Both Admin and Teacher can access.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        # Verify subject exists
        try:
            subject = Subject.objects.get(pk=subject_id, is_active=True)
        except Subject.DoesNotExist:
            return Response({"error": "Subject not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all active chapters for this subject
        chapters = Chapter.objects.filter(
            subject=subject, 
            is_active=True
        ).prefetch_related("subtopics").order_by("order_index")

        serializer = FullSyllabusChapterSerializer(chapters, many=True)
        
        return Response({
            "subject_id": subject.id,
            "subject_name": subject.name,
            "syllabus": serializer.data
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# ACADEMIC YEAR & CALENDAR — /api/v1/academic-years/ | /api/v1/calendar/
# ──────────────────────────────────────────────────────────────────────────────

class AcademicYearListCreateView(APIView):
    """
    GET  — List all academic years (Both).
    POST — Create a new academic year (Admin).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        queryset = AcademicYear.objects.all().order_by("-start_date")
        serializer = AcademicYearSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AcademicYearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AcademicYearCurrentView(APIView):
    """
    PATCH — Mark an academic year as the current active year (Admin).
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            year = AcademicYear.objects.get(pk=pk)
        except AcademicYear.DoesNotExist:
            return Response({"error": "Academic Year not found."}, status=status.HTTP_404_NOT_FOUND)

        # Set all others to false
        AcademicYear.objects.exclude(pk=pk).update(is_current=False)
        # Set this one to true
        year.is_current = True
        year.save(update_fields=["is_current"])

        return Response({"message": f"{year.name} is now the current academic year."}, status=status.HTTP_200_OK)


class CalendarEventListCreateView(APIView):
    """
    GET  — List calendar events (Both). Filterable by year, type, date range.
    POST — Add a new calendar event (Admin).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        queryset = CalendarEvent.objects.select_related("academic_year").all().order_by("event_date")
        
        # Filters
        academic_year_id = request.query_params.get("academic_year_id")
        event_type = request.query_params.get("event_type")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if academic_year_id:
            queryset = queryset.filter(academic_year_id=academic_year_id)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if start_date:
            queryset = queryset.filter(event_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(event_date__lte=end_date)

        serializer = CalendarEventSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CalendarEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CalendarEventDetailView(APIView):
    """
    PUT    — Update a calendar event (Admin).
    DELETE — Delete a calendar event (Admin).
    """
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return CalendarEvent.objects.get(pk=pk)
        except CalendarEvent.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"error": "Event not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CalendarEventSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"error": "Event not found."}, status=status.HTTP_404_NOT_FOUND)
        
        obj.delete()
        return Response({"message": "Event deleted."}, status=status.HTTP_200_OK)


class EffectiveDaysView(APIView):
    """
    GET — Get the count of effective working days within a given date range.
    Requires start_date and end_date query params.
    Formula: Total Days - Sundays - Holidays/Exam Days (from calendar).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from datetime import datetime, timedelta
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({"error": "start_date must be before or equal to end_date."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Total Days
        total_days = (end_date - start_date).days + 1

        # 2. Total Sundays (0 = Monday, 6 = Sunday in Python)
        sundays = 0
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() == 6:  # Sunday
                sundays += 1
            current_date += timedelta(days=1)

        # 3. Calendar Non-Working Days (Holidays, Exams)
        events = CalendarEvent.objects.filter(
            event_date__lte=end_date,
            event_type__in=[CalendarEvent.EventType.HOLIDAY, CalendarEvent.EventType.EXAM]
        )
        
        non_working_dates = set()
        for event in events:
            evt_end = event.end_date if event.end_date else event.event_date
            
            # Intersection of the requested range and the event range
            overlap_start = max(start_date, event.event_date)
            overlap_end = min(end_date, evt_end)
            
            curr = overlap_start
            while curr <= overlap_end:
                if curr.weekday() != 6: # Don't double count Sundays
                    non_working_dates.add(curr)
                curr += timedelta(days=1)

        # 4. Effective Days
        calendar_non_working_days = len(non_working_dates)
        effective_days = total_days - sundays - calendar_non_working_days

        return Response({
            "start_date": start_date_str,
            "end_date": end_date_str,
            "total_days": total_days,
            "sundays": sundays,
            "calendar_non_working_days": calendar_non_working_days,
            "effective_days": effective_days
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# PACING ENGINE — /api/v1/pacing/
# ──────────────────────────────────────────────────────────────────────────────

class PacingListView(APIView):
    """
    GET — View pacing status for all assignments (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = SyllabusPacing.objects.select_related(
            "teacher_assignment__teacher",
            "teacher_assignment__class_id",
            "teacher_assignment__section",
            "teacher_assignment__subject",
            "chapter"
        ).all().order_by("teacher_assignment", "chapter__order_index")
        
        serializer = SyllabusPacingSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyPacingView(APIView):
    """
    GET — Teacher views their own pacing status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = SyllabusPacing.objects.select_related(
            "teacher_assignment__teacher",
            "teacher_assignment__class_id",
            "teacher_assignment__section",
            "teacher_assignment__subject",
            "chapter"
        ).filter(
            teacher_assignment__teacher=request.user,
            teacher_assignment__is_active=True
        ).order_by("teacher_assignment", "chapter__order_index")
        
        serializer = SyllabusPacingSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BehindAlertsView(APIView):
    """
    GET — List only the assignments that are currently behind schedule (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = SyllabusPacing.objects.select_related(
            "teacher_assignment__teacher",
            "teacher_assignment__class_id",
            "teacher_assignment__section",
            "teacher_assignment__subject",
            "chapter"
        ).filter(status=SyllabusPacing.PacingStatus.BEHIND).order_by("-days_behind")
        
        serializer = SyllabusPacingSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PacingDetailView(APIView):
    """
    GET — View detailed pacing information for a specific chapter (Both).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id, chapter_id):
        try:
            pacing = SyllabusPacing.objects.get(
                teacher_assignment_id=assignment_id,
                chapter_id=chapter_id
            )
        except SyllabusPacing.DoesNotExist:
            return Response({"error": "Pacing record not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SyllabusPacingSerializer(pacing)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecalculatePacingView(APIView):
    """
    POST — Manually trigger a pacing recalculation (Admin Only).
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        from datetime import timedelta
        
        # 1. Get current active academic year
        try:
            current_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            return Response({"error": "No current academic year set."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Get all holidays/exams
        events = CalendarEvent.objects.filter(
            academic_year=current_year,
            event_type__in=[CalendarEvent.EventType.HOLIDAY, CalendarEvent.EventType.EXAM]
        )
        non_working_dates = set()
        for event in events:
            evt_end = event.end_date if event.end_date else event.event_date
            curr = event.event_date
            while curr <= evt_end:
                non_working_dates.add(curr)
                curr += timedelta(days=1)

        # 3. For each active teacher assignment
        assignments = TeacherAssignment.objects.filter(academic_year=current_year, is_active=True)
        
        updated_count = 0
        
        for assignment in assignments:
            # Get timetable for this assignment
            slots = Timetable.objects.filter(teacher_assignment=assignment, is_active=True)
            if not slots.exists():
                continue # Cannot calculate pacing without a timetable
                
            # Count periods per day of week
            periods_per_day = {
                "MON": 0, "TUE": 0, "WED": 0, "THU": 0, "FRI": 0, "SAT": 0, "SUN": 0
            }
            for slot in slots:
                periods_per_day[slot.day_of_week] += 1
                
            chapters = Chapter.objects.filter(subject=assignment.subject, is_active=True).order_by("order_index")
            
            curr_date = current_year.start_date
            today = timezone.now().date()
            
            for chapter in chapters:
                required = chapter.total_periods_required or 0
                if required == 0:
                    continue # Skip chapters with 0 periods
                    
                chapter_start = curr_date
                periods_covered = 0
                
                # Advance dates until required periods are met
                while periods_covered < required:
                    # Check if valid day
                    if curr_date.weekday() != 6 and curr_date not in non_working_dates: # Not sunday, not holiday
                        day_str = curr_date.strftime("%a").upper() # 'MON'
                        if periods_per_day.get(day_str, 0) > 0:
                            periods_covered += periods_per_day[day_str]
                    
                    if periods_covered < required:
                        curr_date += timedelta(days=1)
                
                chapter_end = curr_date
                
                # Setup next chapter to start on next day
                curr_date += timedelta(days=1)
                
                # Determine status
                # (Without actual session tracking, we just check if expected_end_date has passed)
                # Later, with Session tracking, we'd check if the chapter was marked COMPLETE in SessionTopicDetail.
                status_val = SyllabusPacing.PacingStatus.ON_TRACK
                days_behind = 0
                
                # Pseudo-logic: If today is past the expected end date, they are behind.
                if today > chapter_end:
                    status_val = SyllabusPacing.PacingStatus.BEHIND
                    # Calculate working days behind
                    diff_days = (today - chapter_end).days
                    days_behind = diff_days
                
                # Save/Update pacing record
                pacing, _ = SyllabusPacing.objects.update_or_create(
                    teacher_assignment=assignment,
                    chapter=chapter,
                    defaults={
                        "expected_start_date": chapter_start,
                        "expected_end_date": chapter_end,
                        "status": status_val,
                        "days_behind": days_behind
                    }
                )
                updated_count += 1

        return Response({"message": f"Pacing recalculated successfully. {updated_count} records updated."}, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# SESSION TRACKING — /api/v1/sessions/
# ──────────────────────────────────────────────────────────────────────────────

class SessionListView(APIView):
    """
    GET  — View all sessions (Admin Only).
    POST — Log a new session (Teacher Only).
    """
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request):
        queryset = SessionLog.objects.select_related(
            "teacher_assignment__teacher",
            "teacher_assignment__class_id",
            "teacher_assignment__subject"
        ).all()
        
        date_filter = request.query_params.get("date")
        teacher_id = request.query_params.get("teacher_id")
        session_type = request.query_params.get("type")

        if date_filter:
            queryset = queryset.filter(session_date=date_filter)
        if teacher_id:
            queryset = queryset.filter(teacher_assignment__teacher_id=teacher_id)
        if session_type:
            queryset = queryset.filter(session_type=session_type)

        serializer = SessionLogSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.role != "teacher":
            return Response({"error": "Only teachers can log sessions."}, status=status.HTTP_403_FORBIDDEN)
            
        # Ensure the teacher assignment belongs to this teacher
        assignment_id = request.data.get("teacher_assignment")
        try:
            assignment = TeacherAssignment.objects.get(id=assignment_id, is_active=True)
            if assignment.teacher != request.user:
                return Response({"error": "Cannot log a session for another teacher's assignment."}, status=status.HTTP_403_FORBIDDEN)
        except TeacherAssignment.DoesNotExist:
            return Response({"error": "Invalid or inactive assignment."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SessionLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MySessionListView(APIView):
    """
    GET — Teacher views their own sessions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "teacher":
            return Response({"error": "Only teachers can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
            
        queryset = SessionLog.objects.select_related(
            "teacher_assignment__class_id",
            "teacher_assignment__subject"
        ).filter(teacher_assignment__teacher=request.user)

        date_filter = request.query_params.get("date")
        if date_filter:
            queryset = queryset.filter(session_date=date_filter)

        serializer = SessionLogSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SessionDetailView(APIView):
    """
    GET    — Retrieve full details of a session (Both).
    PATCH  — Update a session (Teacher same day, Admin anytime).
    DELETE — Delete an incorrect session (Admin Only).
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return SessionLog.objects.get(pk=pk)
        except SessionLog.DoesNotExist:
            return None

    def get(self, request, pk):
        session = self.get_object(pk)
        if not session:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
            
        # Access control
        if request.user.role == "teacher" and session.teacher_assignment.teacher != request.user:
            return Response({"error": "Cannot access another teacher's session."}, status=status.HTTP_403_FORBIDDEN)

        serializer = SessionLogSerializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        session = self.get_object(pk)
        if not session:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == "teacher":
            if session.teacher_assignment.teacher != request.user:
                return Response({"error": "Cannot edit another teacher's session."}, status=status.HTTP_403_FORBIDDEN)
            
            # Same day edit check
            today = timezone.now().date()
            if session.session_date != today:
                return Response({"error": "Teachers can only edit sessions on the same day they occurred."}, status=status.HTTP_403_FORBIDDEN)

        serializer = SessionLogSerializer(session, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        if request.user.role != "admin":
            return Response({"error": "Only admins can delete sessions."}, status=status.HTTP_403_FORBIDDEN)
            
        session = self.get_object(pk)
        if not session:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
            
        session.delete()
        return Response({"message": "Session deleted successfully."}, status=status.HTTP_200_OK)


class SessionTopicCreateView(APIView):
    """
    POST — Add subtopics or chapters to a session (Teacher Only).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        if request.user.role != "teacher":
            return Response({"error": "Only teachers can add topics."}, status=status.HTTP_403_FORBIDDEN)

        try:
            session = SessionLog.objects.get(pk=session_id)
        except SessionLog.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        if session.teacher_assignment.teacher != request.user:
            return Response({"error": "Cannot edit another teacher's session."}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.now().date()
        if session.session_date != today:
            return Response({"error": "Topics can only be added on the same day the session occurred."}, status=status.HTTP_403_FORBIDDEN)

        subtopic_id = request.data.get("subtopic")
        chapter_id = request.data.get("chapter")
        
        # Validation rules based on Session Type
        if session.session_type == SessionLog.SessionType.TEACHING:
            if not subtopic_id:
                return Response({"subtopic": "Subtopic is required for Teaching sessions."}, status=status.HTTP_400_BAD_REQUEST)
        elif session.session_type in [SessionLog.SessionType.QA, SessionLog.SessionType.TEST]:
            if not chapter_id:
                return Response({"chapter": "Chapter is required for QA/Test sessions."}, status=status.HTTP_400_BAD_REQUEST)
        elif session.session_type == SessionLog.SessionType.REVISION:
            if not chapter_id and not subtopic_id:
                return Response({"error": "Either Chapter or Subtopic must be provided for Revision sessions."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SessionTopicDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(session=session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SessionTopicDetailView(APIView):
    """
    PATCH  — Update a topic's status (Teacher Only).
    DELETE — Remove a topic from a session (Teacher Only).
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, session_id, topic_id):
        try:
            return SessionTopicDetail.objects.get(pk=topic_id, session_id=session_id)
        except SessionTopicDetail.DoesNotExist:
            return None

    def patch(self, request, session_id, topic_id):
        if request.user.role != "teacher":
            return Response({"error": "Only teachers can edit topics."}, status=status.HTTP_403_FORBIDDEN)

        topic = self.get_object(session_id, topic_id)
        if not topic:
            return Response({"error": "Topic not found."}, status=status.HTTP_404_NOT_FOUND)

        if topic.session.teacher_assignment.teacher != request.user:
            return Response({"error": "Cannot edit another teacher's session."}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.now().date()
        if topic.session.session_date != today:
            return Response({"error": "Topics can only be edited on the same day the session occurred."}, status=status.HTTP_403_FORBIDDEN)

        serializer = SessionTopicDetailSerializer(topic, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, session_id, topic_id):
        if request.user.role != "teacher":
            return Response({"error": "Only teachers can delete topics."}, status=status.HTTP_403_FORBIDDEN)

        topic = self.get_object(session_id, topic_id)
        if not topic:
            return Response({"error": "Topic not found."}, status=status.HTTP_404_NOT_FOUND)

        if topic.session.teacher_assignment.teacher != request.user:
            return Response({"error": "Cannot edit another teacher's session."}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.now().date()
        if topic.session.session_date != today:
            return Response({"error": "Topics can only be deleted on the same day the session occurred."}, status=status.HTTP_403_FORBIDDEN)

        topic.delete()
        return Response({"message": "Topic removed from session."}, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# TEACHER ATTENDANCE — /api/v1/attendance/
# ──────────────────────────────────────────────────────────────────────────────

class AttendanceListCreateView(APIView):
    """
    GET  — List attendance records for all teachers (Admin Only).
           Filterable by date and teacher_id.
    POST — Record a teacher's attendance (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = TeacherAttendance.objects.select_related("teacher", "marked_by").all().order_by("-date")
        
        # Optional filters
        date_filter = request.query_params.get("date")
        teacher_filter = request.query_params.get("teacher_id")
        
        if date_filter:
            queryset = queryset.filter(date=date_filter)
        if teacher_filter:
            queryset = queryset.filter(teacher_id=teacher_filter)
            
        serializer = TeacherAttendanceSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TeacherAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # marked_by is the current logged-in admin
        attendance = serializer.save(marked_by=request.user)
        return Response(TeacherAttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)


class AttendanceDetailView(APIView):
    """
    PATCH — Correct an existing attendance entry (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return TeacherAttendance.objects.select_related("teacher", "marked_by").get(pk=pk)
        except TeacherAttendance.DoesNotExist:
            return None

    def patch(self, request, pk):
        attendance = self.get_object(pk)
        if not attendance:
            return Response({"error": "Attendance record not found."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = TeacherAttendanceSerializer(attendance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyAttendanceView(APIView):
    """
    GET — Teacher views their own attendance history (Teacher Only).
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        queryset = TeacherAttendance.objects.select_related("teacher", "marked_by").filter(
            teacher=request.user
        ).order_by("-date")
        
        serializer = TeacherAttendanceSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# AUDIT TRAIL — /api/v1/audit-logs/
# ──────────────────────────────────────────────────────────────────────────────

class AuditLogListView(APIView):
    """
    GET — View all system action logs (Admin Only).
          Filterable by user_id, date, and action_type.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = AuditLog.objects.select_related("user").all().order_by("-timestamp")
        
        # Filters
        user_id = request.query_params.get("user_id")
        date_val = request.query_params.get("date")
        action_type = request.query_params.get("action_type")
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if date_val:
            queryset = queryset.filter(timestamp__date=date_val)
        if action_type:
            queryset = queryset.filter(action_type=action_type)
            
        serializer = AuditLogSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuditLogDetailView(APIView):
    """
    GET — Retrieve the full details of a specific audit log entry (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            log = AuditLog.objects.select_related("user").get(pk=pk)
        except AuditLog.DoesNotExist:
            return Response({"error": "Audit log entry not found."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = AuditLogSerializer(log)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuditLogByUserView(APIView):
    """
    GET — View all logged actions performed by a specific user/teacher (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request, user_id):
        queryset = AuditLog.objects.select_related("user").filter(user_id=user_id).order_by("-timestamp")
        serializer = AuditLogSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuditLogByEntityView(APIView):
    """
    GET — View all actions performed on a specific record (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request, entity_id):
        queryset = AuditLog.objects.select_related("user").filter(entity_id=entity_id).order_by("-timestamp")
        serializer = AuditLogSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN DASHBOARD & ANALYTICS — /api/v1/dashboard/
# ──────────────────────────────────────────────────────────────────────────────

class AdminDashboardOverviewView(APIView):
    """
    GET — High-level statistics: total teachers, classes, and overall syllabus completion percentage (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        total_teachers = User.objects.filter(role=User.Role.TEACHER, is_active=True).count()
        total_classes = Class.objects.filter(is_active=True).count()

        # Overall syllabus completion: completed active subtopics / total active subtopics
        total_subtopics = SubTopic.objects.filter(is_active=True, chapter__is_active=True).count()
        
        # Completed subtopics: distinct subtopics marked as 'complete' in SessionTopicDetail
        completed_subtopics = SessionTopicDetail.objects.filter(
            status=SessionTopicDetail.CompletionStatus.COMPLETE,
            subtopic__is_active=True,
            subtopic__chapter__is_active=True
        ).values("subtopic").distinct().count()

        completion_percentage = 0.0
        if total_subtopics > 0:
            completion_percentage = round((completed_subtopics / total_subtopics) * 100, 2)

        return Response({
            "total_teachers": total_teachers,
            "total_classes": total_classes,
            "overall_syllabus_completion_percentage": completion_percentage
        }, status=status.HTTP_200_OK)


class AdminDashboardSyllabusProgressView(APIView):
    """
    GET — Syllabus completion percentage broken down by class, section, and subject (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        # Fetch active assignments
        assignments = TeacherAssignment.objects.select_related(
            "class_id", "section", "subject", "teacher"
        ).filter(is_active=True)

        progress_data = []

        for assignment in assignments:
            # Active subtopics for this assignment's subject
            subtopics = SubTopic.objects.filter(
                chapter__subject=assignment.subject,
                is_active=True,
                chapter__is_active=True
            )
            total_count = subtopics.count()

            # Completed subtopics under this specific assignment
            completed_count = SessionTopicDetail.objects.filter(
                session__teacher_assignment=assignment,
                status=SessionTopicDetail.CompletionStatus.COMPLETE,
                subtopic__in=subtopics
            ).values("subtopic").distinct().count()

            completion_percentage = 0.0
            if total_count > 0:
                completion_percentage = round((completed_count / total_count) * 100, 2)

            progress_data.append({
                "assignment_id": assignment.id,
                "class_id": assignment.class_id.id,
                "class_name": assignment.class_id.name,
                "section_id": assignment.section.id,
                "section_name": assignment.section.name,
                "subject_id": assignment.subject.id,
                "subject_name": assignment.subject.name,
                "teacher_id": assignment.teacher.id,
                "teacher_name": assignment.teacher.full_name,
                "total_subtopics": total_count,
                "completed_subtopics": completed_count,
                "completion_percentage": completion_percentage
            })

        return Response(progress_data, status=status.HTTP_200_OK)


class AdminDashboardUnmarkedTopicsView(APIView):
    """
    GET — List of subtopics not yet covered — filterable by subject and class (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        subject_id = request.query_params.get("subject_id")
        class_id = request.query_params.get("class_id")

        # Start with all active subtopics
        queryset = SubTopic.objects.select_related("chapter__subject").filter(
            is_active=True,
            chapter__is_active=True
        )

        if subject_id:
            queryset = queryset.filter(chapter__subject_id=subject_id)

        # Exclude subtopics already marked complete in any session log
        completed_subtopic_ids = SessionTopicDetail.objects.filter(
            status=SessionTopicDetail.CompletionStatus.COMPLETE,
            subtopic__isnull=False
        ).values_list("subtopic_id", flat=True)

        queryset = queryset.exclude(id__in=completed_subtopic_ids)

        # If class_id is provided, we filter topics taught in that class
        if class_id:
            # Find subjects assigned to this class
            subjects_in_class = TeacherAssignment.objects.filter(
                class_id=class_id,
                is_active=True
            ).values_list("subject_id", flat=True)
            queryset = queryset.filter(chapter__subject_id__in=subjects_in_class)

        # Structure response
        unmarked_topics = []
        for subtopic in queryset.order_by("chapter__subject", "chapter__order_index", "order_index"):
            unmarked_topics.append({
                "subtopic_id": subtopic.id,
                "subtopic_name": subtopic.name,
                "chapter_id": subtopic.chapter.id,
                "chapter_name": subtopic.chapter.name,
                "subject_id": subtopic.chapter.subject.id,
                "subject_name": subtopic.chapter.subject.name,
            })

        return Response(unmarked_topics, status=status.HTTP_200_OK)


class AdminDashboardTeacherActivityView(APIView):
    """
    GET — Last session date per teacher — highlights teachers with no recent activity (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        teachers = User.objects.filter(role=User.Role.TEACHER, is_active=True)
        activity_data = []

        for teacher in teachers:
            last_session = SessionLog.objects.filter(
                teacher_assignment__teacher=teacher
            ).order_by("-session_date", "-created_at").first()

            last_session_date = None
            days_inactive = None

            if last_session:
                last_session_date = last_session.session_date
                days_inactive = (timezone.now().date() - last_session_date).days

            activity_data.append({
                "teacher_id": teacher.id,
                "teacher_name": teacher.full_name,
                "employee_id": teacher.employee_id,
                "phone": teacher.phone,
                "last_session_date": last_session_date,
                "days_inactive": days_inactive
            })

        return Response(activity_data, status=status.HTTP_200_OK)


class AdminDashboardBehindScheduleView(APIView):
    """
    GET — Classes and subjects that are currently behind their pacing schedule (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        behind_records = SyllabusPacing.objects.select_related(
            "teacher_assignment__class_id",
            "teacher_assignment__section",
            "teacher_assignment__subject",
            "teacher_assignment__teacher",
            "chapter"
        ).filter(
            status=SyllabusPacing.PacingStatus.BEHIND,
            teacher_assignment__is_active=True
        ).order_by("-days_behind")

        behind_data = []
        for pacing in behind_records:
            behind_data.append({
                "pacing_id": pacing.id,
                "class_name": pacing.teacher_assignment.class_id.name,
                "section_name": pacing.teacher_assignment.section.name,
                "subject_name": pacing.teacher_assignment.subject.name,
                "teacher_name": pacing.teacher_assignment.teacher.full_name,
                "chapter_name": pacing.chapter.name,
                "expected_start_date": pacing.expected_start_date,
                "expected_end_date": pacing.expected_end_date,
                "days_behind": pacing.days_behind
            })

        return Response(behind_data, status=status.HTTP_200_OK)


class AdminDashboardTestFrequencyView(APIView):
    """
    GET — Subject-wise report on how frequently tests are being conducted (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        subjects = Subject.objects.filter(is_active=True)
        frequency_data = []

        for subject in subjects:
            test_count = SessionLog.objects.filter(
                session_type=SessionLog.SessionType.TEST,
                teacher_assignment__subject=subject
            ).count()

            frequency_data.append({
                "subject_id": subject.id,
                "subject_name": subject.name,
                "code": subject.code,
                "test_count": test_count
            })

        return Response(frequency_data, status=status.HTTP_200_OK)


class AdminDashboardRevisionCoverageView(APIView):
    """
    GET — Chapter-wise revision status across all classes (Admin Only).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        chapters = Chapter.objects.select_related("subject").filter(is_active=True)
        coverage_data = []

        for chapter in chapters:
            # Count revision of this direct chapter
            direct_revision = SessionTopicDetail.objects.filter(
                session__session_type=SessionLog.SessionType.REVISION,
                chapter=chapter
            ).count()

            # Count revision of subtopics belonging to this chapter
            subtopic_revision = SessionTopicDetail.objects.filter(
                session__session_type=SessionLog.SessionType.REVISION,
                subtopic__chapter=chapter
            ).count()

            total_revision = direct_revision + subtopic_revision

            coverage_data.append({
                "chapter_id": chapter.id,
                "chapter_name": chapter.name,
                "subject_name": chapter.subject.name,
                "order_index": chapter.order_index,
                "revision_count": total_revision
            })

        return Response(coverage_data, status=status.HTTP_200_OK)


class TeacherDashboardOverviewView(APIView):
    """
    GET — Summary of assigned classes, today's periods, and overall syllabus progress (Teacher Only).
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        assignments = TeacherAssignment.objects.filter(
            teacher=request.user,
            is_active=True
        )

        assigned_classes = []
        seen_pairings = set()
        for a in assignments:
            pairing_key = (a.class_id.id, a.section.id, a.subject.id)
            if pairing_key not in seen_pairings:
                seen_pairings.add(pairing_key)
                assigned_classes.append({
                    "class_id": a.class_id.id,
                    "class_name": a.class_id.name,
                    "section_id": a.section.id,
                    "section_name": a.section.name,
                    "subject_id": a.subject.id,
                    "subject_name": a.subject.name
                })

        # Today's periods count
        today_day = timezone.now().strftime("%a").upper()
        today_periods_count = Timetable.objects.filter(
            teacher_assignment__teacher=request.user,
            day_of_week=today_day,
            is_active=True,
            teacher_assignment__is_active=True
        ).count()

        # Overall syllabus progress across all assigned subjects
        assigned_subjects = [a.subject for a in assignments]
        total_subtopics = SubTopic.objects.filter(
            chapter__subject__in=assigned_subjects,
            is_active=True,
            chapter__is_active=True
        ).distinct()

        total_count = total_subtopics.count()

        completed_count = SessionTopicDetail.objects.filter(
            session__teacher_assignment__in=assignments,
            status=SessionTopicDetail.CompletionStatus.COMPLETE,
            subtopic__isnull=False,
            subtopic__is_active=True,
            subtopic__chapter__is_active=True
        ).values("subtopic").distinct().count()

        overall_progress = 0.0
        if total_count > 0:
            overall_progress = round((completed_count / total_count) * 100, 2)

        return Response({
            "teacher_id": request.user.id,
            "teacher_name": request.user.full_name,
            "assigned_classes_count": len(assigned_classes),
            "assigned_classes": assigned_classes,
            "today_periods_count": today_periods_count,
            "overall_syllabus_completion_percentage": overall_progress
        }, status=status.HTTP_200_OK)


class TeacherDashboardSyllabusStatusView(APIView):
    """
    GET — Own completion status broken down by subject, chapter, and subtopic (Teacher Only).
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        assignments = TeacherAssignment.objects.filter(
            teacher=request.user,
            is_active=True
        ).select_related("class_id", "section", "subject")

        syllabus_data = []
        for a in assignments:
            # Get chapters for this subject
            chapters = Chapter.objects.filter(subject=a.subject, is_active=True).order_by("order_index")
            chapters_data = []

            for ch in chapters:
                # Find pacing record for this chapter & assignment
                pacing = SyllabusPacing.objects.filter(
                    teacher_assignment=a,
                    chapter=ch
                ).first()

                expected_start_date = pacing.expected_start_date if pacing else None
                expected_end_date = pacing.expected_end_date if pacing else None
                pacing_status = pacing.status if pacing else SyllabusPacing.PacingStatus.ON_TRACK
                days_behind = pacing.days_behind if pacing else 0

                # Get subtopics for this chapter
                subtopics = SubTopic.objects.filter(chapter=ch, is_active=True).order_by("order_index")
                subtopics_data = []

                for sub in subtopics:
                    # Determine completion status for this specific teacher assignment
                    has_complete = SessionTopicDetail.objects.filter(
                        session__teacher_assignment=a,
                        subtopic=sub,
                        status=SessionTopicDetail.CompletionStatus.COMPLETE
                    ).exists()

                    if has_complete:
                        sub_status = "complete"
                    else:
                        has_partial = SessionTopicDetail.objects.filter(
                            session__teacher_assignment=a,
                            subtopic=sub,
                            status=SessionTopicDetail.CompletionStatus.PARTIAL
                        ).exists()
                        sub_status = "partial" if has_partial else "unmarked"

                    subtopics_data.append({
                        "subtopic_id": sub.id,
                        "subtopic_name": sub.name,
                        "order_index": sub.order_index,
                        "status": sub_status
                    })

                chapters_data.append({
                    "chapter_id": ch.id,
                    "chapter_name": ch.name,
                    "order_index": ch.order_index,
                    "expected_start_date": expected_start_date,
                    "expected_end_date": expected_end_date,
                    "pacing_status": pacing_status,
                    "days_behind": days_behind,
                    "subtopics": subtopics_data
                })

            syllabus_data.append({
                "assignment_id": a.id,
                "class_id": a.class_id.id,
                "class_name": a.class_id.name,
                "section_id": a.section.id,
                "section_name": a.section.name,
                "subject_id": a.subject.id,
                "subject_name": a.subject.name,
                "chapters": chapters_data
            })

        return Response(syllabus_data, status=status.HTTP_200_OK)


class TeacherDashboardPendingTopicsView(APIView):
    """
    GET — List of topics not yet marked — pending coverage (Teacher Only).
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        subject_id = request.query_params.get("subject_id")
        class_id = request.query_params.get("class_id")

        assignments = TeacherAssignment.objects.filter(
            teacher=request.user,
            is_active=True
        )

        if subject_id:
            assignments = assignments.filter(subject_id=subject_id)
        if class_id:
            assignments = assignments.filter(class_id=class_id)

        pending_topics = []
        for a in assignments:
            # Active subtopics for this assignment's subject
            subtopics = SubTopic.objects.filter(
                chapter__subject=a.subject,
                is_active=True,
                chapter__is_active=True
            ).select_related("chapter")

            # Completed subtopic IDs for this specific assignment
            completed_ids = SessionTopicDetail.objects.filter(
                session__teacher_assignment=a,
                status=SessionTopicDetail.CompletionStatus.COMPLETE,
                subtopic__isnull=False
            ).values_list("subtopic_id", flat=True)

            # Exclude complete subtopics
            pending_subs = subtopics.exclude(id__in=completed_ids).order_by("chapter__order_index", "order_index")

            for sub in pending_subs:
                pending_topics.append({
                    "assignment_id": a.id,
                    "class_name": a.class_id.name,
                    "section_name": a.section.name,
                    "subject_name": a.subject.name,
                    "chapter_name": sub.chapter.name,
                    "subtopic_id": sub.id,
                    "subtopic_name": sub.name,
                    "order_index": sub.order_index
                })

        return Response(pending_topics, status=status.HTTP_200_OK)


class TeacherDashboardTodayScheduleView(APIView):
    """
    GET — Today's periods along with the relevant syllabus context for each (Teacher Only).
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        today_day = timezone.now().strftime("%a").upper()

        slots = Timetable.objects.filter(
            teacher_assignment__teacher=request.user,
            day_of_week=today_day,
            is_active=True,
            teacher_assignment__is_active=True
        ).select_related(
            "teacher_assignment__class_id",
            "teacher_assignment__section",
            "teacher_assignment__subject"
        ).order_by("period_number")

        schedule_data = []
        for s in slots:
            a = s.teacher_assignment

            # Last completed subtopic context
            last_completed_detail = SessionTopicDetail.objects.filter(
                session__teacher_assignment=a,
                status=SessionTopicDetail.CompletionStatus.COMPLETE,
                subtopic__isnull=False
            ).order_by("-session__session_date", "-session__created_at").first()

            last_completed = None
            if last_completed_detail:
                last_completed = {
                    "subtopic_id": last_completed_detail.subtopic.id,
                    "subtopic_name": last_completed_detail.subtopic.name,
                    "chapter_name": last_completed_detail.subtopic.chapter.name
                }

            # Next pending subtopic context
            all_subtopics = SubTopic.objects.filter(
                chapter__subject=a.subject,
                is_active=True,
                chapter__is_active=True
            ).order_by("chapter__order_index", "order_index")

            completed_ids = set(SessionTopicDetail.objects.filter(
                session__teacher_assignment=a,
                status=SessionTopicDetail.CompletionStatus.COMPLETE,
                subtopic__isnull=False
            ).values_list("subtopic_id", flat=True))

            next_pending = None
            for sub in all_subtopics:
                if sub.id not in completed_ids:
                    next_pending = {
                        "subtopic_id": sub.id,
                        "subtopic_name": sub.name,
                        "chapter_name": sub.chapter.name
                    }
                    break

            schedule_data.append({
                "timetable_id": s.id,
                "period_number": s.period_number,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "room": s.room,
                "class_name": a.class_id.name,
                "section_name": a.section.name,
                "subject_name": a.subject.name,
                "last_completed_subtopic": last_completed,
                "next_pending_subtopic": next_pending
            })

        return Response(schedule_data, status=status.HTTP_200_OK)



