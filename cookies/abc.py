from abc import ABC, abstractmethod
from ast import Not

from redbot.core import Config
from redbot.core.bot import Red

_MAX_BALANCE = 2 ** 63 - 1

class MixinMeta(ABC):
    def __init__(self, *_args):
        self.config: Config
        self.bot: Red

    @abstractmethod
    def display_time(self):
        raise NotImplementedError

    @abstractmethod
    def _max_balance_check(self):
        raise NotImplementedError

    @abstractmethod
    async def can_spend(self):
        raise NotImplementedError

    @abstractmethod
    async def withdraw_cookies(self):
        raise NotImplementedError

    @abstractmethod
    async def deposit_cookies(self):
        raise NotImplementedError

    @abstractmethod
    async def get_cookies(self):
        raise NotImplementedError