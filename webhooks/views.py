import hashlib
import hmac
import json
import os
import random

import redis
from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from discourse_bot_python.settings import API_USERNAME, NEW_TOPIC_RANDOM_TRIGGER_PROB
from .compose_reply import reply_to_post


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
        return instance.removeprefix('https://') in ['xjtu.live', 'xjtu.app', 'xjtu.men', 'ipv4.xjtu.live',
                                                     'ipv6.xjtu.live', 'cf.xjtu.live']
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
    if valid_key:
        print(request.META['HTTP_X_DISCOURSE_EVENT'])
        print(request.META['HTTP_X_DISCOURSE_EVENT_ID'])
        print(request.META['HTTP_X_DISCOURSE_EVENT_TYPE'])
    # try:
        body = request.body.decode()
        body = json.loads(body)
        print(body)
        if (('post' in body) and (reply_to_user := body['post'].get('reply_to_user')) and (
                reply_to_user.get('username') == API_USERNAME)):
            # direct reply to bot, 100% trigger
            res = reply_to_post(body, first_post=False, lookback=True)
            print(res)
            return HttpResponse('Successfully replied to reply')
        elif (('post' in body) and f'@{API_USERNAME}' in body['post']['raw']):
            # @bot, 100% trigger
            res = reply_to_post(body, first_post=False, lookback=False)
            print(res)
            return HttpResponse('Successfully replied to @reply')
        elif ('post' in body) and (body['post']['post_number'] == 1) and (random.random() > NEW_TOPIC_RANDOM_TRIGGER_PROB):
            # new topic, 60% trigger
            res = reply_to_post(body, first_post=True, lookback=False)
            print(res)
            return HttpResponse('Successfully replied to topic')
        elif ('post' in body):
            # new post, tigger with exponentially decayed probability
            res = reply_to_post(body, first_post=False, lookback=False, random_tiggered=True)
            print(res)
            return HttpResponse('Successfully replied to topic')
        else:
            print(f'do not respond to body: {body}')
            return HttpResponse('Ignored')
        # except Exception as e:
        #     return HttpResponse(f'Internal Err: {e}')
    else:
        return HttpResponse('Unauthorized')
