import json
import math
import os
import random

import redis
import requests

from discourse_bot_python.settings import XJTUMEN_URL_BASE, API_CALL_HEADERS, AttrDict, API_USERNAME, MAX_LOOK_BEHIND, \
    RANDOM_TRIGGER_FACTOR
from webhooks.call_oai_api import oai_respond
from bs4 import BeautifulSoup

r = redis.Redis(host='localhost', port=6379, db=0)


def single_true(iterable):
    i = iter(iterable)
    return any(i) and not any(i)

def at_most_one_true(iterable):
    return sum(map(bool, iterable)) <= 1

def mutual_ex(a, b):
    return bool(a) != bool(b)


def should_skip(i):
    prob = math.exp(-RANDOM_TRIGGER_FACTOR * i)
    if random.random() < 1 - prob:
        return True
    else:
        return False
def reply_to_post(body, first_post, lookback, random_tiggered=False):
    assert at_most_one_true([random_tiggered, first_post, lookback])
    if not isinstance(body, AttrDict):
        body = AttrDict(body)
    post = AttrDict(body.post)
    topic_id = post.topic_id
    post_number = post.post_number
    try:
        title = post.topic_title
    except KeyError:
        title = ''
    uname = post.name
    if len(uname) == 0:
        uname = post.username

    if random_tiggered:
        if post.username == API_USERNAME:
            return  # skip if the post is created by the bot itself
        k = f'disbot_reply_to_topic_{topic_id}'
        got = r.get(k)
        if got is None:
            # first time we reply to this topic randomly
            r.set(k, 1)
            if should_skip(1):
                return  # some chances we ignore this trigger
        else:
            if should_skip(int(got.decode())):
                return  # even higher chances we ignore this trigger
    prompt = post['raw']

    if first_post:
        resp_raw = oai_respond(f'{title}: {prompt}')
    else:
        url = f'{XJTUMEN_URL_BASE}/t/-/{topic_id}.json?print=true'
        # url = f'{XJTUMEN_URL_BASE}/t/-/{topic_id}.json'
        url = f'{XJTUMEN_URL_BASE}/t/{topic_id}/posts.json'
        res = requests.request('GET', url, headers=API_CALL_HEADERS)
        res = res.json()
        try:
            all_posts = res['post_stream']['posts']
        except KeyError:
            return res
        OP = BeautifulSoup(all_posts[0]['cooked'], features="lxml").get_text()
        topic_title_and_OP = f'{title}: {OP}'
        print(len(all_posts))
        extra_msgs = []
        if lookback:
            extra_msgs = get_thread(post_number, topic_id)
            extra_msgs = list(reversed(extra_msgs))
            print('#' * 20)
            for msg in extra_msgs:
                print(msg)
            print('#' * 20)
        elif random_tiggered:
            for i in range(MAX_LOOK_BEHIND):
                try:
                    _post = all_posts.pop()
                    if _post['post_number'] == post_number:
                        _post = all_posts.pop()
                    extra_msgs.append({"role": get_role(i),
                                       "content": f'{_post["username"]} 说：' + BeautifulSoup(
                                           _post['cooked'], features="lxml").get_text()})
                except IndexError:
                    break
            extra_msgs = list(reversed(extra_msgs))

        resp_raw = oai_respond(f'{prompt}', init_append_msg=f'讨论的主题是：{topic_title_and_OP}', extra_msgs=extra_msgs)

    # resp_raw = f'{post} {uname} {title}'
    _json = {'topic_id': f'{topic_id}', 'raw': resp_raw}
    if not first_post:
        _json['reply_to_post_number'] = post_number

    response = requests.request('POST', f'{XJTUMEN_URL_BASE}/posts.json', headers=API_CALL_HEADERS,
                                json=_json)
    print(response)
    print()
    if random_tiggered:
        r.incr(k, 1)

def get_post_filtered_by_post_num(posts, post_number):
    filtered = list(filter(lambda p: p['post_number'] == post_number, posts))
    if len(filtered) != 1:
        print(f'{post_number} not in this topic')
        return None
    post = filtered[0]
    return post


def get_role(i):
    if i % 2 == 0:
        return 'user'
    else:
        return 'assistant'


def get_should_reply_to(i, thread_username, name):
    if i % 2 == 0:
        return thread_username == name
    else:
        return API_USERNAME == name


def get_thread(post_number, topic_id):
    thread = []
    url = f'{XJTUMEN_URL_BASE}/t/-/{topic_id}.json?print=true'
    res = requests.request('GET', url, headers=API_CALL_HEADERS)
    res = res.json()
    if (got := res.get('post_stream')) is None:
        return thread
    posts = got['posts']
    last_post = get_post_filtered_by_post_num(posts, post_number)
    assert last_post is not None, 'a direct reply should never be None'
    for i in range(MAX_LOOK_BEHIND):
        if i == 0 or get_should_reply_to(i, thread_user_name, last_post['username']):
            if i == 0:
                thread_user_name = last_post["username"]
                print(f'thread user name: {thread_user_name}')
            thread.append({"role": get_role(i),
                           "content": f'{last_post["username"]} 说：' + BeautifulSoup(
                               last_post['cooked'], features="lxml").get_text()})
            post_number = last_post['reply_to_post_number']
            last_post = get_post_filtered_by_post_num(posts, post_number)
            if last_post is None:
                break
        else:
            break
    return thread


if __name__ == '__main__':
    thread = get_thread(25, 7040)
    print(thread)
