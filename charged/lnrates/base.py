from abc import ABCMeta, abstractmethod


class BaseLnRatesProvider(object):
    __metaclass__ = ABCMeta

    provider = tuple()
    settings = None

    @abstractmethod
    def fetch_rates(self):
        raise NotImplementedError

    # @abstractmethod
    # def get_pairs(self):
    #     # https://www.xe.com/iso4217.php
    #     raise NotImplementedError
    #
    # @abstractmethod
    # def get_credentials(self):
    #     raise NotImplementedError
    #
    # @abstractmethod
    # def get_rate(self, **kwargs):
    #     raise NotImplementedError
