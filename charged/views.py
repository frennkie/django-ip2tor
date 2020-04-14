import json

import lnrpc
from django.http import JsonResponse, HttpResponse
from django.views import View, generic
from django.views.generic import TemplateView, ListView
from protobuf_to_dict import protobuf_to_dict

from charged.models import Backend, PurchaseOrder, LnInvoice


class InfoView(ListView):
    model = Backend

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)

        backends_get_info = {}
        for backend in self.get_queryset():
            try:
                gi = backend.get_info
            except AttributeError:  # not implemented backend
                continue

            if isinstance(gi, lnrpc.rpc_pb2.GetInfoResponse):
                backends_get_info.update({backend.name: protobuf_to_dict(gi)})
            else:
                backends_get_info.update({backend.name: {"error": "Not yet configured"}})

        if backends_get_info:
            return HttpResponse(json.dumps({'data': backends_get_info}), content_type='application/json')

        return JsonResponse({'error': 'no results'})


# class InvoiceView(View):
#     btc_msat_ratio = 100000000000
#
#     def post(self, request):
#
#         params = {}
#         options = ['amount', 'msatoshi', 'description', 'currency', 'expiry']
#
#         for option in options:
#             params[option] = request.POST.get(option)
#
#         params['label'] = rndstr()
#
#         try:
#             if params['amount'] is not None and params['currency'] is not None:
#                 exch_rate = exchange_rate(params['currency'])
#                 params['msatoshi'] = round(float(params['amount']) / exch_rate * self.btc_msat_ratio)
#         except:
#             return JsonResponse({'error': 'conversion error'})
#
#         try:
#             if params['label'] is None or params['description'] is None:
#                 return JsonResponse({'error': 'missing arguments_'})
#         except KeyError:
#             return JsonResponse({'error': 'missing arguments'})
#
#         try:
#             result = Ln().invoice_create(params=params)
#             if result:
#                 return HttpResponse(json.dumps(result), status=201, content_type='application/json')
#             return JsonResponse({'error': 'missing arguments__'})
#         except:
#             return JsonResponse({'error': 'error'})
#
#     def get(self, request, label):
#         params = {'label': label}
#         result = Ln().invoice_get(params=params)
#         if result is not False:
#             return HttpResponse(json.dumps(result), content_type='application/json')
#


class RegisterListener(View):
    pass


class DemoView(TemplateView):
    template_name = 'charged/demo.html'


class PurchaseOrderDetailView(generic.DetailView):
    model = PurchaseOrder


class LnInvoiceDetailView(generic.DetailView):
    model = LnInvoice
