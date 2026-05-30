import uuid
import datetime
from django.forms.models import model_to_dict
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from .models import (
    User,
    TeacherAssignment,
    Timetable,
    Chapter,
    SubTopic,
    AcademicYear,
    CalendarEvent,
    SessionLog,
    SessionTopicDetail,
    TeacherAttendance,
    AuditLog,
    Class,
    Section,
    Subject,
)
from .middleware import get_current_user, get_current_ip

# List of models we want to track
AUDITED_MODELS = [
    User,
    TeacherAssignment,
    Timetable,
    Chapter,
    SubTopic,
    AcademicYear,
    CalendarEvent,
    SessionLog,
    SessionTopicDetail,
    TeacherAttendance,
    Class,
    Section,
    Subject,
]

# Mapping of Model Class names to action prefixes
MODEL_PREFIXES = {
    "User": "USER",
    "TeacherAssignment": "ASSIGNMENT",
    "Timetable": "TIMETABLE",
    "Chapter": "CHAPTER",
    "SubTopic": "SUBTOPIC",
    "AcademicYear": "ACADEMIC_YEAR",
    "CalendarEvent": "CALENDAR_EVENT",
    "SessionLog": "SESSION",
    "SessionTopicDetail": "SESSION_TOPIC",
    "TeacherAttendance": "ATTENDANCE",
    "Class": "CLASS",
    "Section": "SECTION",
    "Subject": "SUBJECT",
}

def clean_for_json(data):
    """
    Recursively ensures that all values in data are JSON-serializable.
    Converts UUIDs, datetime, date, and time objects to strings.
    """
    if isinstance(data, dict):
        return {str(k): clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_json(v) for v in data]
    elif isinstance(data, uuid.UUID):
        return str(data)
    elif isinstance(data, (datetime.datetime, datetime.date, datetime.time)):
        return data.isoformat()
    return data

def serialize_instance(instance):
    """
    Converts a model instance into a JSON-serializable dictionary.
    Safely removes password fields before returning.
    """
    try:
        data = model_to_dict(instance)
    except Exception:
        # Fallback if model_to_dict encounters issues
        data = {}
        for field in instance._meta.fields:
            data[field.name] = getattr(instance, field.name)
            
    # Remove sensitive fields
    data.pop("password", None)
    data.pop("password_hash", None)
    return clean_for_json(data)

@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """
    Pre-save receiver: Stores the current DB state in _old_value_dict
    before it is overwritten by the save operation.
    """
    if sender not in AUDITED_MODELS:
        return
        
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_value_dict = serialize_instance(old_instance)
        except sender.DoesNotExist:
            instance._old_value_dict = None
    else:
        instance._old_value_dict = None

@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """
    Post-save receiver: Captures creations and updates, determines deactivations,
    resolves current request user/IP, and creates an AuditLog record.
    """
    if sender not in AUDITED_MODELS:
        return

    prefix = MODEL_PREFIXES.get(sender.__name__, "ENTITY")
    current_user = get_current_user()
    current_ip = get_current_ip()
    
    # Snapshot role of actor
    user_role = current_user.role if current_user else "system"
    
    new_value = serialize_instance(instance)
    old_value = getattr(instance, "_old_value_dict", None)

    if created:
        action_type = f"{prefix}_CREATED"
    else:
        # Detect is_active soft delete transitions
        if old_value and "is_active" in old_value and "is_active" in new_value:
            if old_value["is_active"] is True and new_value["is_active"] is False:
                action_type = f"{prefix}_DEACTIVATED"
            elif old_value["is_active"] is False and new_value["is_active"] is True:
                action_type = f"{prefix}_ACTIVATED"
            else:
                action_type = f"{prefix}_UPDATED"
        else:
            action_type = f"{prefix}_UPDATED"

    # Save audit entry
    AuditLog.objects.create(
        user=current_user,
        user_role=user_role,
        action_type=action_type,
        entity_type=sender.__name__.lower(),
        entity_id=instance.pk,
        old_value=old_value,
        new_value=new_value,
        ip_address=current_ip,
    )

@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    """
    Post-delete receiver: Automatically logs hard deletion events.
    """
    if sender not in AUDITED_MODELS:
        return

    prefix = MODEL_PREFIXES.get(sender.__name__, "ENTITY")
    current_user = get_current_user()
    current_ip = get_current_ip()
    
    user_role = current_user.role if current_user else "system"
    old_value = serialize_instance(instance)

    AuditLog.objects.create(
        user=current_user,
        user_role=user_role,
        action_type=f"{prefix}_DELETED",
        entity_type=sender.__name__.lower(),
        entity_id=instance.pk,
        old_value=old_value,
        new_value=None,
        ip_address=current_ip,
    )
