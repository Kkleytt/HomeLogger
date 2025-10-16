import os
import shutil
import asyncio
import aiofiles
import zipfile
import tarfile
import gzip
import bz2
import lzma
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional, Literal, Dict
import io
from pydantic import BaseModel, Field

from src.models.config_models import ServerConfig

class FileData(BaseModel):
    path: Optional[Path] = None
    date_start: datetime = datetime.now()
    count_lines: int = 0
    
    class Config:
        extra = "forbid"


class Writer:
    def __init__(self, config: ServerConfig.Files):
        """ Класс для записи логов в файлы

        Arguments:
            config {ServerConfig.Files} -- Pydantic модель с настройками класса
        """
        
        self.cfg = config
        
        # Данные активного файла
        self._active_file_data: Dict[str, FileData] = {}
        self._active_file_handle: Dict[str, io.TextIOWrapper] = {}  # Пока синхронный файл, см. ниже
        self._log_dir: Dict[str, Path] = {}
        self._archive_dir: Dict[str, Path] = {}

    def get_info(self) -> ServerConfig.Files:
        return self.cfg
        
    async def __aenter__(self):
        return self
    
    async def _create_directory(self, project: str) -> bool:
        """ Функция для создания базовых директорий проекта

        Returns:
            bool -- Статус создания директорий
        """
        try:
            self._log_dir[project] = Path(self.cfg.share_directory) / self.cfg.project_directory.format(project=project)
            self._log_dir[project].mkdir(parents=True, exist_ok=True)
            self._archive_dir[project] = self._log_dir[project] / self.cfg.archive.directory
            self._archive_dir[project].mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Ошибка создания директории: {e}")
            return False

    def _write_start_log(self, project: str):
        """Записывает заголовок файла"""
        if not self._active_file_handle.get(project):
            return

        start_time_str = self._active_file_data[project].date_start.replace(tzinfo=ZoneInfo(self.cfg.date_timezone)).strftime("%d:%m:%Y %H:%M:%S %z")
        file_name = self._active_file_data[project].path.name if self._active_file_data[project].path else "unknown" # type: ignore

        # Фиксированная ширина содержимого между │ и │
        content_width = 80

        # Формируем строки с правильным выравниванием
        line1 = f"│ LOG FILE START{' ' * (content_width - len('LOG FILE START') - 2)} │"
        line2 = f"│ File: {file_name}{' ' * (content_width - len('File: ') - len(file_name) - 2)} │"
        line3 = f"│ Project: {project}{' ' * (content_width - len('Project: ') - len(project) - 2)} │"
        line4 = f"│ Start Date: {start_time_str}{' ' * (content_width - len('Start Date: ') - len(start_time_str) - 2)} │"

        header = (
            f"┌{'─' * content_width}┐\n"
            f"{line1}\n"
            f"{line2}\n"
            f"{line3}\n"
            f"{line4}\n"
            f"└{'─' * content_width}┘\n"
        )
        self._active_file_handle[project].write(header)
        self._active_file_handle[project].flush()

    def _write_end_log(self, project: str):
        """Записывает футер файла перед закрытием"""
        if not self._active_file_handle.get(project):
            return

        # Закрываем файл для получения актуального размера
        self._active_file_handle[project].close()

        if self._active_file_data[project].path and self._active_file_data[project].path.exists(): # type: ignore
            file_size = self._active_file_data[project].path.stat().st_size # type: ignore
            size_str = self._format_size(file_size)
            end_time_str = datetime.now(ZoneInfo(self.cfg.date_timezone)).strftime("%d:%m:%Y %H:%M:%S %z")
            content_width = 80

            line1 = f"│ LOG FILE END{' ' * (content_width - len('LOG FILE END') - 2)} │"
            line2 = f"│ End Date: {end_time_str}{' ' * (content_width - len('End Date: ') - len(end_time_str) - 2)} │"
            line3 = f"│ Total Lines: {self._active_file_data[project].count_lines}{' ' * (content_width - len('Total Lines: ') - len(str(self._active_file_data[project].count_lines)) - 2)} │"
            line4 = f"│ File Size: {size_str}{' ' * (content_width - len('File Size: ') - len(size_str) - 2)} │"

            footer = (
                f"\n┌{'─' * content_width}┐\n"
                f"{line1}\n"
                f"{line2}\n"
                f"{line3}\n"
                f"{line4}\n"
                f"└{'─' * content_width}┘\n"
            )

            # Открываем файл в режиме дозаписи и добавляем футер
            with open(self._active_file_data[project].path, 'a', encoding='utf-8') as f: # type: ignore
                f.write(footer)

        # Переоткрываем файл для продолжения записи (если нужно)
        self._active_file_handle[project] = open(self._active_file_data[project].path, 'a', encoding='utf-8') # type: ignore

    def _format_size(self, size_bytes: int) -> str:
        """ Функция для форматирования размера файла в читаемый вид

        Arguments:
            size_bytes {int} -- Размер файла в байтах

        Returns:
            str -- Строка с размером файла
        """
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes = int(size_bytes / 1024.0)
        return f"{size_bytes:.1f} TB"

    async def _open_new_file(self, project: str) -> bool:
        """ Функция для открытия нового файла и инициализации переменных

        Returns:
            bool -- Статус открытия файла
        """
        
        try:
            # Проверяем существует ли активный файл и закрываем его
            if self._active_file_handle.get(project):
                self._write_end_log(project)

            # Генерируем данные активного файла
            filename = self.cfg.filename.format(
                project=project,
                date=datetime.now().strftime(self.cfg.date_file_format)
            )
            
            # Создаем директории по пути файла
            self._active_file_data[project].path = self._log_dir[project] / filename
            self._active_file_data[project].path.parent.mkdir(parents=True, exist_ok=True) # type: ignore
            
            # Открываем файл
            self._active_file_handle[project] = open(self._active_file_data[project].path, 'a', encoding='utf-8') # type: ignore
            
            # Сохраняем данные файла
            self._active_file_data[project].count_lines = 0
            self._active_file_data[project].date_start = datetime.now(ZoneInfo("UTC"))
            
            # Записываем заголовок
            self._write_start_log(project)
            
            # Проверяем, нужно ли архивировать старый файл
            if self.cfg.archive.enabled:
                await self.check_old_logfile(project)
            
            return True
        except Exception as e:
            print(f"Ошибка открытия файла: {e}")
            return False

    async def write_log(self, log_data: dict) -> bool:
        """ Функция для записи лога в файл

        Arguments:
            log_data {dict} -- Словарь с данными лога

        Returns:
            bool -- Статус записи лога
        """
        
        try:
            # Получем от какого проекта пришел запрос
            project = log_data.get("project", "unknown")
            
            # Проверяем что объект проекта уже хранится в кэше
            if project not in self._active_file_handle:
                self._active_file_data[project] = FileData()
                await self._create_directory(project)
                await self._open_new_file(project)
                
            # Проверяем на смену файла
            if self._should_rotate(project):
                await self._open_new_file(project)
                

            # Форматируем строку лога
            formatted_log = self.cfg.log_format.format(
                project=project,
                timestamp=log_data.get("timestamp", datetime.now().strftime(self.cfg.date_log_format)),
                level=log_data.get("level", "unknown").upper(),
                module=log_data.get("module", "unknown"),
                function=log_data.get("function", "unknown"),
                message=log_data.get("message", ""),
                code=log_data.get("code", 0)
            )
            
            if self._active_file_handle[project]:
                self._active_file_handle[project].write(formatted_log + "\n")
                self._active_file_handle[project].flush()
                self._active_file_data[project].count_lines += 1
            
            return True
        except Exception as e:
            print(f"Ошибка записи лога: {e}")
            return False

    def _should_rotate(self, project: str) -> bool:
        """ Функция для проверки необходимости смены файла

        Arguments:
            project {str} -- Имя проекта

        Returns:
            bool -- Необходимость смены файла
        """
        
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        # Проверка на смену дня (для daily)
        if self.cfg.rotation.trigger == "daily":
            if current_time_str == self.cfg.rotation.daily and self._active_file_data[project].date_start.strftime("%Y-%m-%d") != now.strftime("%Y-%m-%d"):
                return True

        # Проверка по времени (если rotation_trigger == "time")
        if self.cfg.rotation.trigger == "time":
            if (datetime.now() - self._active_file_data[project].date_start).total_seconds() >= self.cfg.rotation.time:
                return True

        # Проверка по количеству строк
        if self.cfg.rotation.trigger == "lines":
            if self._active_file_data[project].count_lines >= self.cfg.rotation.lines:
                return True

        # Проверка по размеру
        if self.cfg.rotation.trigger == "size":
            if self._active_file_data[project].path and self._active_file_data[project].path.stat().st_size >= self.cfg.rotation.size: # type: ignore
                return True

        return False

    async def check_old_logfile(self, project: str) -> bool:
        """ Функция для проверки старых файлов и архивации

        Arguments:
            project {str} -- Имя проекта

        Returns:
            bool -- Статус проверки старых файлов
        """
        
        try:
            log_dir = self._log_dir[project]
            archive_dir = self._archive_dir[project]

            # Получаем список файлов в директории (не активный файл)
            current_file = self._active_file_data[project].path
            log_files = [
                f for f in log_dir.glob("*.log") 
                if f != current_file
            ]

            # Архивация по количеству файлов
            if self.cfg.archive.trigger == "count" and len(log_files) > self.cfg.archive.count:
                # Сортируем файлы по времени модификации (сначала самые старые)
                sorted_files = sorted(log_files, key=lambda f: f.stat().st_mtime)
                
                # Архивируем лишние файлы (те, что превышают лимит)
                excess_count = len(log_files) - self.cfg.archive.count
                for i in range(excess_count):
                    oldest_file = sorted_files[i]
                    await self._archive_single_file(oldest_file, project)

            # Архивация по возрасту
            elif self.cfg.archive.trigger == "age":
                now = datetime.now(ZoneInfo("UTC"))
                for log_file in log_files:
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime, tz=ZoneInfo("UTC"))
                    if (now - file_mtime).total_seconds() > self.cfg.archive.age:
                        await self._archive_single_file(log_file, project)
                        
            return True
        except Exception as e:
            print(f"Ошибка при проверке старых файлов: {e}")
            return False
                    
    async def _archive_single_file(self, file_path: Path, project: str) -> bool:
        """ Функция для архивации файла

        Arguments:
            file_path {Path} -- Путь к файлу
            project {str} -- Имя проекта

        Returns:
            bool -- Статус архивации
        """
        
        try:
            if not file_path.exists():
                return False

            # Формируем имя архива: заменяем .log на .zip (или иной тип)
            archive_name = file_path.with_suffix(f".{self.cfg.archive.type}").name
            archive_dir = self._archive_dir[project]
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / archive_name

            # Архивируем (асинхронно не поддерживается напрямую, но можно в executor)
            def do_archive():
                archive_type = self.cfg.archive.type
                if archive_type == "zip":
                    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.write(file_path, file_path.name)
                elif archive_type == "gz":
                    with open(file_path, 'rb') as f_in:
                        with gzip.open(archive_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                elif archive_type == "bz2":
                    with open(file_path, 'rb') as f_in:
                        with bz2.open(archive_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                elif archive_type == "xz":
                    with open(file_path, 'rb') as f_in:
                        with lzma.open(archive_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

            await asyncio.get_event_loop().run_in_executor(None, do_archive)

            # Удаляем исходный файл
            file_path.unlink()
            
            return True
        except Exception as e:
            print(f"Ошибка при архивации файла {file_path}: {e}")
            return False

    async def close(self, project: str) -> bool:
        """ Функция для закрытия файла

        Arguments:
            project {str} -- Имя проекта

        Returns:
            bool -- Статус закрытия файла
        """
        
        try:
            if self._active_file_handle.get(project):
                self._write_end_log(project)
                self._active_file_handle[project].close()
                
            return True
        except Exception as e:
            print(f"Ошибка при закрытии файла: {e}")
            return False

    async def close_all(self) -> bool:
        """ Функция для закрытия всех файлов

        Returns:
            bool -- Статус закрытия файлов
        """
        
        try:
            for project in self._active_file_handle:
                await self.close(project)
                
            return True
        except Exception as e:
            print(f"Ошибка при закрытии файлов: {e}")
            return False
        