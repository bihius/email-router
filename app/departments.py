from enum import Enum


class Department(str, Enum):
    """Allowed routing target for a ticket.

    The enum value is what the model sees. The email address stays in the map below.
    """

    KADRY = "kadry"
    HUMAN_RESOURCES = "human_resources"
    IT = "it"
    HELP_DESK = "help_desk"
    OTHER = "other"


DEPARTMENT_EMAIL: dict[Department, str] = {
    Department.KADRY: "kadry@example.com",
    Department.HUMAN_RESOURCES: "human-resources@example.com",
    Department.IT: "it@example.com",
    Department.HELP_DESK: "help-desk@example.com",
    Department.OTHER: "other@example.com",
}
