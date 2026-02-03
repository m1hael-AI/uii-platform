from aiogram.fsm.state import State, StatesGroup

class QuizStates(StatesGroup):
    # Quiz questions (5 questions)
    q1_country = State()
    q2_age = State()
    q3_work = State()
    q4_income = State()
    q5_education = State()
    # Contact info
    name = State()
    phone = State()
    email = State()
    # Subscription check
    check_subscription = State()
