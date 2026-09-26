import csv
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Department:
    """One row from the department catalog. The model sees name, not email."""

    name: str
    email: str
    description: str


def catalog_path() -> Path:
    override = os.environ.get("DEPARTMENTS_FILE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "data" / "departments.csv"


def load_departments(path: Path | None = None) -> tuple[Department, ...]:
    file_path = path or catalog_path()
    with file_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["name", "email", "description"]:
            raise ValueError("departments.csv must have columns name, email, description")
        rows = [
            Department(
                name=row["name"].strip(),
                email=row["email"].strip(),
                description=row["description"].strip(),
            )
            for row in reader
        ]
    names = [row.name for row in rows]
    if not names or len(names) != len(set(names)):
        raise ValueError("department names must be present and unique")
    if "other" not in names:
        raise ValueError("departments.csv must include an other row")
    return tuple(rows)


DEPARTMENTS = load_departments()
BY_NAME = {item.name: item for item in DEPARTMENTS}


def get_department(name: str) -> Department:
    """Return the named row, or other when the model picks a name that is not in the file."""
    return BY_NAME.get(name, BY_NAME["other"])
