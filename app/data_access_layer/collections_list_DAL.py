import asyncio
import logging
import time

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError

from app.models.database_models import CollectionsList
from app.schemas.collection_list import CollectionsListCreate
from app.data_access_layer.exceptions import CollectionExistsException, CollectionNotFoundException


class CollectionsListDaL:

    @staticmethod
    def get_collections_list(database: Session):
        """Получить список существующих коллекций."""
        with database as session:
            statement = select(CollectionsList)
            result = session.exec(statement)
            return result.all() or []

    @staticmethod
    async def aget_collections_list(database: AsyncSession):
        """Асинхронно получить список существующих коллекций."""
        async with database as session:
            statement = select(CollectionsList)
            result = await session.exec(statement)
            return result.all() or []

    @staticmethod
    def create_collection(database: Session, collection: CollectionsListCreate):
        """Создать новую коллекцию."""
        with database as session:
            with session.begin():
                try:
                    session.add(collection)
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    raise CollectionExistsException(collection.name)
                else:
                    session.refresh(collection)
                    return collection

    @staticmethod
    async def acreate_collection(database: Session, collection: CollectionsListCreate):
        """Асинхронно создать новую коллекцию."""
        async with database as session:
            async with session.begin():
                try:
                    session.add(collection)
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    raise CollectionExistsException(collection.name)
                else:
                    await session.refresh(collection)
                    return collection

    @staticmethod
    def add_to_collection(database: Session, collection_name: str, id_to_add: int, retries: int = 3):
        """Добавить ID в поле 'contains_ids' с обработкой deadlock и lock timeout."""

        retry_count = 0
        while retry_count < retries:
            try:
                with database as session:
                    select_statement = select(CollectionsList).where(
                        CollectionsList.name == collection_name).with_for_update()
                    result = session.exec(select_statement)
                    found: CollectionsList = result.first()

                    if not found:
                        raise CollectionNotFoundException(collection_name)

                    found.contains_ids.append(id_to_add)
                    session.add(found)
                    session.commit()

                # Успешное завершение транзакции, выходим из цикла
                return found

            except OperationalError as e:
                # Проверяем, не связан ли OperationalError с deadlock или lock timeout
                if "deadlock detected" in str(e.orig) or "lock timeout" in str(e.orig):
                    retry_count += 1
                    session.rollback()  # Откат транзакции перед повтором
                    logging.info(f"Deadlock/Lock timeout detected. Retrying... Attempt {retry_count}/{retries}")
                    time.sleep(1)  # Пауза перед повторной попыткой
                else:
                    # Если ошибка не связана с блокировками, пробрасываем её дальше
                    session.rollback()
                    raise

            except StaleDataError:
                # Обработка ошибок устаревших данных, если актуальные данные были изменены другим процессом
                session.rollback()
                logging.info("Stale data detected, retrying...")
                retry_count += 1
                time.sleep(1)

        # Если все попытки исчерпаны, выбрасываем исключение
        raise Exception(
            f"Failed to add ID to collection '{collection_name}' after {retries} attempts due to deadlock/lock timeout.")


    @staticmethod
    async def aadd_to_collection(database: AsyncSession, collection_name: str, id_to_add: int, retries: int = 3):
        """Асинхронный метод для добавления ID в поле 'contains_ids' с обработкой deadlock и lock timeout."""

        retry_count = 0
        while retry_count < retries:
            try:
                async with database as session:
                    async with session.begin():
                        select_statement = select(CollectionsList).where(
                            CollectionsList.name == collection_name).with_for_update()
                        result = await session.exec(select_statement)
                        found: CollectionsList = result.first()

                        if not found:
                            raise CollectionNotFoundException(collection_name)

                        # Добавляем ID в список contains_ids
                        found.contains_ids.append(id_to_add)
                        session.add(found)
                        await session.commit()  # Асинхронная фиксация транзакции

                # Успешное завершение транзакции, выходим из цикла
                return found

            except OperationalError as e:
                # Проверяем, связан ли OperationalError с deadlock или lock timeout
                if "deadlock detected" in str(e.orig) or "lock timeout" in str(e.orig):
                    retry_count += 1
                    await session.rollback()  # Откат транзакции перед повтором
                    logging.info(f"Deadlock/Lock timeout detected. Retrying... Attempt {retry_count}/{retries}")
                    await asyncio.sleep(1)  # Асинхронная пауза перед повторной попыткой
                else:
                    # Если ошибка не связана с deadlock/lock timeout, пробрасываем её дальше
                    await session.rollback()
                    raise

            except StaleDataError:
                # Обработка ошибок устаревших данных
                await session.rollback()
                logging.info("Stale data detected, retrying...")
                retry_count += 1
                await asyncio.sleep(1)

        # Если все попытки исчерпаны, выбрасываем исключение
        raise Exception(
            f"Failed to add ID to collection '{collection_name}' after {retries} attempts due to deadlock/lock timeout.")

    @staticmethod
    def delete_collection(database: Session, collection_name: str):
        with database as session:
            with session.begin():
                try:
                    select_statement = select(CollectionsList).where(
                        CollectionsList.name == collection_name).with_for_update()
                    result = session.exec(select_statement)
                    found: CollectionsList = result.first()

                    if not found:
                        raise CollectionNotFoundException(collection_name)
                    session.delete(found)
                    session.commit()

                except IntegrityError:
                    session.rollback()
                    ...
                else:
                    return found



