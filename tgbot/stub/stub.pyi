from contextlib import contextmanager
from typing import Any, Generator, Union

from aiogram_i18n import LazyProxy


class User:
   def start_cmd(self) -> Union[str, LazyProxy]: ...
   def language_changed(self) -> Union[str, LazyProxy]: ...

class Languages:
   def ru(self) -> Union[str, LazyProxy]: ...
   def en(self) -> Union[str, LazyProxy]: ...

class I18nStubs:
    languages = Languages()
    user = User()

class I18nContext(I18nStubs):
    def get(self, key: str, /, **kwargs: Any) -> str: ...
    async def set_locale(self, locale: str, **kwargs: Any) -> None: ...
    @contextmanager
    def use_locale(self, locale: str) -> Generator[I18nContext, None, None]: ...

class LazyFactory(I18nStubs):
    key_separator: str
    def set_separator(self, key_separator: str) -> None: ...
    def __call__(self, key: str, /, **kwargs: dict[str, Any]) -> LazyProxy: ...

L: LazyFactory