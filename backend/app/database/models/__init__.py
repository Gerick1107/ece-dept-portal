from app.database.models.copo import CopoEvaluationRun, CopoMarksUpload, CopoResultArchive
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot
from app.database.models.course import Course
from app.database.models.user import User
from app.awards.models.entities import FacultyAward
from app.notifications.models.entities import Notification, NotificationAttachment, NotificationRecipient
from app.publications.models.entities import (
    BlockedPublication,
    Faculty,
    Publication,
    PublicationAuditLog,
    PublicationFaculty,
    ScrapeLog,
)
from app.projects.models.entities import Project, ProjectSdg, ProjectStudent, ProjectUpload, Sdg

__all__ = [
    "User",
    "CopoMarksUpload",
    "CopoEvaluationRun",
    "CopoResultArchive",
    "CopoRunAnalyticsSnapshot",
    "Course",
    "FacultyAward",
    "Notification",
    "NotificationAttachment",
    "NotificationRecipient",
    "Faculty",
    "Publication",
    "PublicationFaculty",
    "ScrapeLog",
    "BlockedPublication",
    "PublicationAuditLog",
    "Project",
    "ProjectStudent",
    "ProjectSdg",
    "ProjectUpload",
    "Sdg",
]
