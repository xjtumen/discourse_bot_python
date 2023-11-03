import hashlib
import hmac
import os

from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.views.decorators.http import require_POST



def get_client_ips(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(', ')
    else:
        ip = [request.META.get('REMOTE_ADDR')]
    return ip


def is_valid_key(request):
    secret = os.environ['DIS_BOT_WEBHOOK_SECRET']
    secret = bytes(secret, 'utf-8')
    h = hmac.new(secret, request.body, hashlib.sha256)
    digest = h.hexdigest()
    recv = request.META.get('HTTP_X_DISCOURSE_EVENT_SIGNATURE')
    return recv == f'sha256={digest}'


def is_valid_instance(request):
    instance = request.META.get('HTTP_X_DISCOURSE_INSTANCE')
    if instance:
        return instance.removeprefix('https://') in ['xjtu.live', 'xjtu.app', 'xjtu.men', 'ipv4.xjtu.live', 'ipv6.xjtu.live', 'cf.xjtu.live']
    else:
        return False

def is_valid_ip(client_ips):
    trusted_ip = os.environ['DIS_BOT_WEBHOOK_TRUSTED_IP'].strip().split()
    for i in trusted_ip:
        if i in client_ips:
            return True
    return False


@require_POST
def example(request):
    valid_key = is_valid_key(request)
    client_ips = get_client_ips(request)
    if is_valid_ip(client_ips) and valid_key:
        print(request.META['HTTP_X_DISCOURSE_EVENT'])
        print(request.META['HTTP_X_DISCOURSE_EVENT_ID'])
        print(request.META['HTTP_X_DISCOURSE_EVENT_TYPE'])
        return HttpResponse('true')
    else:
        return HttpResponse('Hello, world. This is the webhook response.')
