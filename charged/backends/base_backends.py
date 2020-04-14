from abc import ABCMeta, abstractmethod


class AbstractBackend:
    __metaclass__ = ABCMeta

    type = None
    streaming = False

    @classmethod
    @abstractmethod
    def from_settings(cls, settings):
        return NotImplemented

    @abstractmethod
    def dump_settings(self):
        return NotImplemented

    @abstractmethod
    def get_info(self):
        return NotImplemented

    @abstractmethod
    def create_invoice(self, **kwargs):
        return NotImplemented

    @abstractmethod
    def get_invoice(self, **kwargs):
        return NotImplemented

    @abstractmethod
    def stream_invoices(self, **kwargs):
        return NotImplemented

    @property
    def supports_streaming(self):
        return self.streaming
