from abc import ABCMeta, abstractmethod


class BaseLnRatesProvider(object):
    __metaclass__ = ABCMeta

    provider = tuple()

    @abstractmethod
    def get_pairs(self):
        # https://www.xe.com/iso4217.php
        raise NotImplementedError

    @abstractmethod
    def get_credentials(self):
        raise NotImplementedError

    @abstractmethod
    def get_rate(self, **kwargs):
        raise NotImplementedError
