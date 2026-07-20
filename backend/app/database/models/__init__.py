from app.database.models.assessment import Assessment, AssessmentCoMapping
from app.database.models.copo import CopoEvaluationRun, CopoMarksUpload, CopoResultArchive
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot
from app.database.models.course import Course
from app.database.models.user import User
from app.awards.models.entities import FacultyAward
from app.notifications.models.entities import Notification, NotificationAttachment, NotificationRecipient
from app.publications.models.entities import (
    Affiliation,
    BlockedPublication,
    Faculty,
    FacultyAffiliation,
    Publication,
    PublicationAuditLog,
    PublicationFaculty,
    ScrapeLog,
)
from app.projects.models.entities import Project, ProjectSdg, ProjectStudent, ProjectUpload, Sdg
from app.ece_eve_projects.models.entities import EceEveProject
from app.llm.models.entities import LlmInsightsCache

from app.moderation.models.entities import GradeCriterion, QuestionPaper
from app.labs.models.entities import Lab

__all__ = [
    "User",
    "CopoMarksUpload",
    "CopoEvaluationRun",
    "Assessment",
    "AssessmentCoMapping",
    "CopoResultArchive",
    "CopoRunAnalyticsSnapshot",
    "Course",
    "FacultyAward",
    "Notification",
    "NotificationAttachment",
    "NotificationRecipient",
    "Affiliation",
    "Faculty",
    "FacultyAffiliation",
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
    "EceEveProject",
    "LlmInsightsCache",
    "QuestionPaper", 
    "GradeCriterion",
    "Lab",
]
