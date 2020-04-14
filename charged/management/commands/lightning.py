# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from charged.backends import FakeBackend


class Command(BaseCommand):
    help = 'lightning info'

    # def add_arguments(self, parser):
    #   parser.add_argument('command' , nargs='+', type=str)

    def handle(self, *args, **options):
        result = FakeBackend().get_info()
        print(result)
