import asyncio
from datetime import date
import random

from sqlmodel import Session

from core.schemas import StudentCreate
from core.helpers import postgres_helper
from core.logger import logger

from api.v1.students import StudentService

FIRST_NAMES = [
    "Alex", "Maria", "John", "Sophie", "Dmitry", "Anna", "Peter", "Elena",
    "Michael", "Olga", "James", "Natalia"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Taylor", "Wilson", "Davis", "Clark",
    "Shevchenko", "Kovalenko", "Bondarenko", "Tkachenko", "Melnyk", "Zakharchenko",
    "Symonenko", "Kravchenko"
]

GROUPS = [
    "PZ-21", "PZ-22", "KI-204", "SA-21"
]

GENDERS = ["Male", "Female", "Other"]


async def populate_students(session, num_students: int = 20, ):
    try:
        for _ in range(num_students):
            current_year = date.today().year
            birth_year = random.randint(current_year - 99, current_year - 17)
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)

            student_data = StudentCreate(
                group=random.choice(GROUPS),
                first_name=random.choice(FIRST_NAMES),
                last_name=random.choice(LAST_NAMES),
                gender=random.choice(GENDERS),
                birthday=date(birth_year, birth_month, birth_day)
            )

            try:
                await StudentService.create_student(student_data, session)
                logger.info(
                    f"Created student: {student_data.first_name} {student_data.last_name} in {student_data.group}")

            except Exception as e:
                logger.error(f"Skipped student creation: {str(e)}")
                continue

        students = await StudentService.get_students(session, 0, num_students)
        logger.info(f"Total students in database: {len(students)}")

    except Exception as e:
        logger.error(f"Error during population: {str(e)}")
        session.rollback()
    finally:
        session.close()


async def main():
    postgres_helper.create_db_and_tables()
    logger.info("Starting student population...")
    session = Session(postgres_helper.engine)
    await populate_students(session=session, num_students=10)
    logger.info("Population complete!")


if __name__ == "__main__":
    asyncio.run(main())
