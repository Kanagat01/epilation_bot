from datetime import date, datetime

from sqlalchemy import MetaData, DateTime, Column, Integer, String, TEXT, DATE, TIME, JSON, TIMESTAMP, select, \
    insert, delete, update, or_, and_, extract
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, as_declarative
from sqlalchemy.sql import expression

from create_bot import DATABASE_URL

engine = create_async_engine(DATABASE_URL)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False)


@as_declarative()
class Base:
    metadata = MetaData()


class UtcNow(expression.FunctionElement):
    type = DateTime()
    inherit_cache = True


@compiles(UtcNow, 'postgresql')
def pg_utcnow(element, compiler, **kw):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


class TextsDB(Base):
    """Тексты, id фоток и видео"""
    __tablename__ = "texts"

    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    chapter = Column(String, nullable=False)
    text = Column(TEXT, nullable=False)  # Может быть id файла


class ServicesDB(Base):
    """Перечень услуг и прайс-лист"""
    __tablename__ = "services"

    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    category = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    title = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    # Время выполнения услуги в минутах
    duration = Column(Integer, nullable=False)
    status = Column(String, nullable=False, server_default="enabled")
    ordering = Column(Integer, nullable=False)


class ClientsDB(Base):
    """Профили клиентов"""
    __tablename__ = "clients"

    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    user_id = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, nullable=False, server_default="")
    phone = Column(String, nullable=False)
    gender = Column(String, nullable=False)  # boys girls
    birthday = Column(DATE, nullable=True)
    note = Column(TEXT, nullable=True)
    service_duration = Column(Integer, nullable=True)
    resource = Column(String, nullable=True)
    entry_point = Column(String, nullable=False,
                         default="world")  # world office


class MailingsDB(Base):
    """Рассылки"""
    __tablename__ = "mailings"

    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    # Группы клиентов: all_clients, new_clients, not_new_clients, bio_group, laser_group, group_by_date
    client_group = Column(String, nullable=False)
    dtime = Column(TIMESTAMP, nullable=False)
    text = Column(TEXT, nullable=False)
    photo = Column(TEXT, nullable=True)
    # Статус: waiting, sent
    status = Column(String, nullable=False, default="waiting")


class RegistrationsDB(Base):
    """Записи клиентов"""
    __tablename__ = "registrations"

    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    phone = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    reg_date = Column(DATE, nullable=False)
    reg_time_start = Column(TIME, nullable=False)
    reg_time_finish = Column(TIME, nullable=False)
    services = Column(JSON, nullable=True)
    total_price = Column(Integer, nullable=True)
    # created no_show cancelled cancelled_by_master finished moved
    status = Column(String, nullable=False, default="created")


class StaticsDB(Base):
    __tablename__ = "statics"

    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    category = Column(String, nullable=True)
    title = Column(String, nullable=False)
    file_id = Column(String, nullable=False)


class BaseDAO:
    """Класс взаимодействия с БД"""
    model = None

    @classmethod
    async def get_one_or_none(cls, **filter_by):
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(
                **filter_by).limit(1)
            result = await session.execute(query)
            return result.mappings().one_or_none()

    @classmethod
    async def get_many(cls, **filter_by) -> list:
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(
                **filter_by).order_by(cls.model.id)
            result = await session.execute(query)
            return result.mappings().all()

    @classmethod
    async def create(cls, **data):
        async with async_session_maker() as session:
            stmt = insert(cls.model).values(**data)
            result = await session.execute(stmt)
            await session.commit()
            return result.mappings().one_or_none()

    @classmethod
    async def delete(cls, **data):
        async with async_session_maker() as session:
            stmt = delete(cls.model).filter_by(**data)
            await session.execute(stmt)
            await session.commit()


class TextsDAO(BaseDAO):
    model = TextsDB

    @classmethod
    async def update(cls, chapter: str, **data):
        async with async_session_maker() as session:
            stmt = update(cls.model).values(**data).filter_by(chapter=chapter)
            await session.execute(stmt)
            await session.commit()


class ServicesDAO(BaseDAO):
    model = ServicesDB

    @classmethod
    async def get_next_ordering(cls, category: str, gender: str):
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(category=category, gender=gender).order_by(
                cls.model.ordering.desc())
            result = await session.execute(query)
            last_ordering = result.mappings().first()
            return last_ordering.ordering + 1 if last_ordering else 1

    @classmethod
    async def get_order_list(cls, **filter_by) -> list:
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(**filter_by).order_by(ServicesDB.ordering.asc(),
                                                                                        ServicesDB.id.asc())
            result = await session.execute(query)
            return result.mappings().all()

    @classmethod
    async def update(cls, service_id: int, data):
        async with async_session_maker() as session:
            stmt = update(cls.model).values(data).filter_by(id=service_id)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_many(cls, **filter_by) -> list:
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(
                **filter_by).order_by(cls.model.ordering)
            result = await session.execute(query)
            return result.mappings().all()


class ClientsDAO(BaseDAO):
    model = ClientsDB

    @classmethod
    async def update(cls, user_id: str, **data):
        async with async_session_maker() as session:
            stmt = update(cls.model).values(**data).filter_by(user_id=user_id)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_many(cls, **filter_by) -> list:
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(
                **filter_by).order_by(cls.model.id)
            result = await session.execute(query)
            return result.mappings().all()

    @classmethod
    async def get_birthday_people(cls, birth_date: date) -> list:
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).where(
                extract('month', cls.model.birthday) == birth_date.month,
                extract('day', cls.model.birthday) == birth_date.day,
                cls.model.birthday != datetime.date(1900, 1, 1)
            ).order_by(cls.model.id)
            result = await session.execute(query)
            return result.mappings().all()


class MailingsDAO(BaseDAO):
    model = MailingsDB

    @classmethod
    async def get_clients_from_client_group(cls, client_group, reg_date=None) -> list:
        if client_group == "new_clients":
            clients = await ClientsDAO.get_many()
            res = []
            for client in clients:
                regs = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], finished=True)
                if len(regs) == 0:
                    res.append(client)
            return res

        elif client_group == "all_clients":
            clients = await ClientsDAO.get_many()
            return clients

        elif client_group == "not_new_clients":
            clients = await ClientsDAO.get_many()
            res = []
            for client in clients:
                regs = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], finished=True)
                if len(regs) != 0:
                    res.append(client)
            return res

        elif client_group == "bio":
            clients = await ClientsDAO.get_many()
            res = []
            for client in clients:
                regs = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], finished=True)
                if len(regs) != 0:
                    service_id = regs[0]["services"][0]
                    service = await ServicesDAO.get_one_or_none(id=service_id)
                    if service["category"] == "bio":
                        res.append(client)
            return res

        elif client_group == "laser":
            clients = await ClientsDAO.get_many()
            res = []
            for client in clients:
                regs = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], finished=True)
                if len(regs) != 0:
                    service_id = regs[0]["services"][0]
                    service = await ServicesDAO.get_one_or_none(id=service_id)
                    if service["category"] == "laser":
                        res.append(client)
            return res

        elif client_group == "group_by_date":
            regs = await RegistrationsDAO.get_many(is_sorted=True, reg_date=reg_date)
            res = []
            for reg in regs:
                client = await ClientsDAO.get_one_or_none(user_id=reg["user_id"])
                res.append(client)
            return res

    @classmethod
    async def update(cls, id: int, **data):
        async with async_session_maker() as session:
            stmt = update(cls.model).values(**data).filter_by(id=id)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_many_sorted_by_dtime(cls, reverse=False, **filter_by) -> list:
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(
                **filter_by).order_by(cls.model.dtime.desc() if reverse else cls.model.dtime.asc())
            result = await session.execute(query)
            return result.mappings().all()


class RegistrationsDAO(BaseDAO):
    model = RegistrationsDB

    @classmethod
    async def update(cls, reg_id: int, **data):
        async with async_session_maker() as session:
            stmt = update(cls.model).values(**data).filter_by(id=reg_id)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_many(cls, is_sorted=False, **filter_by) -> list:
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(**filter_by)
            if is_sorted:
                query = query.order_by(
                    cls.model.reg_date.asc(),
                    cls.model.reg_time_start.asc()
                )
            result = await session.execute(query)
            return result.mappings().all()

    @classmethod
    async def get_many_created(cls) -> list:
        async with async_session_maker() as session:
            today = datetime.now().date()
            current_time = datetime.now().time()
            query = select(cls.model.__table__.columns).filter(
                or_(cls.model.reg_date < today, and_(cls.model.reg_date == today, cls.model.reg_time_start < current_time))).\
                filter(cls.model.status.in_(["created", "moved"]))
            result = await session.execute(query)
            return result.mappings().all()

    @classmethod
    async def get_by_user_id(cls, user_id: str, finished: bool = None, created: bool = None, is_sorted: bool = False) -> dict:
        async with async_session_maker() as session:
            query_registrations = select(
                cls.model.__table__.columns).filter_by(user_id=user_id)
            if finished:
                query_registrations = query_registrations.filter_by(
                    status="finished")
            if created:
                query_registrations = query_registrations.filter(
                    cls.model.status.in_(["created"]))
            if is_sorted:
                query_registrations = query_registrations.order_by(
                    cls.model.reg_date.desc(),
                    cls.model.reg_time_start.desc()
                )
            result = await session.execute(query_registrations)
            return result.mappings().all()

    @classmethod
    async def get_last_4_ordering(cls, user_id: str):
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(user_id=user_id).\
                order_by(cls.model.reg_date.desc(),
                         cls.model.reg_time_start.desc()).limit(4)
            result = await session.execute(query)
            return result.mappings().all()

    @classmethod
    async def check_interval(cls, reg_date, start_time, finish_time, return_result=False, except_reg_id=None, except_event_id=None):
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(reg_date=reg_date).\
                filter(or_(and_(start_time <= cls.model.reg_time_start, cls.model.reg_time_start <= finish_time),
                           and_(start_time <= cls.model.reg_time_finish, cls.model.reg_time_finish <= finish_time))).\
                filter(cls.model.status.in_(["created", "moved"]))
            if except_reg_id:
                query = query.filter(cls.model.id != except_reg_id)
            result = await session.execute(query)
            result = result.mappings().all()
            return result


class StaticsDAO(BaseDAO):
    model = StaticsDB

    @classmethod
    async def get_order_list(cls, category: str, like: str):
        async with async_session_maker() as session:
            query = select(cls.model.__table__.columns).filter_by(category=category).\
                where(cls.model.title.like(f"%{like}%")).order_by(
                    cls.model.title.asc())
            result = await session.execute(query)
            return result.mappings().all()

    @classmethod
    async def update(cls, id: int, **data):
        async with async_session_maker() as session:
            stmt = update(cls.model).values(**data).filter_by(id=id)
            await session.execute(stmt)
            await session.commit()


def status_translation(status):
    dict1 = {"created": "Создано", "no_show": "Не явился", "cancelled": "Отменено",
             "cancelled_by_master": "Отменено мастером", "finished": "Завершено", "moved": "Перенесено"}
    return dict1[status]


def category_translation(category):
    return 'БИО' if category == 'bio' else 'Лазер'


def gender_translation(gender):
    if gender not in ["boys", "girls"]:
        return "Неизвестно"
    return "Мужчина" if gender == "boys" else "Девушка"


def mailing_status_translation(status):
    dict1 = {"waiting": "Ожидает отправки",
             "sent": "Отправлено", "auto_text": "Автотекст"}
    if status not in dict1:
        return None
    return dict1[status]


def client_group_translation(client_group):
    dict1 = {"all_clients": "Все клиенты", "new_clients": "Новые клиенты",
             "not_new_clients": "Кроме новых клиентов", "bio_group": "Био", "laser_group": "Лазер", "group_by_date": "Клиенты, записанные на дату"}
    if client_group not in dict1:
        return None
    return dict1[client_group]


def get_client_group_num(client_group):
    dict1 = {"all_clients": 1, "new_clients": 2,
             "not_new_clients": 3, "bio_group": 4, "laser_group": 5, "group_by_date": 6}
    return dict1[client_group]


def get_client_group_by_num(num):
    dict1 = {1: "new_clients", 2: "all_clients",
             3: "not_new_clients", 4: "bio_group", 5: "laser_group"}
    return dict1[num]
