import json
import os

import requests

from discourse_bot_python.settings import XJTUMEN_URL_BASE, API_CALL_HEADERS, AttrDict, API_USERNAME
from webhooks.play_oai_api import ai_respond
from bs4 import BeautifulSoup

MAX_LOOK_BEHIND = 5


def reply_to_post(body, first_post, lookback):
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

    prompt = post['raw']

    if first_post:
        resp_raw = ai_respond(f'{title}: {prompt}')
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
        resp_raw = ai_respond(f'{prompt}', init_append_msg=f'讨论的主题是：{topic_title_and_OP}', extra_msgs=extra_msgs)

    # resp_raw = f'{post} {uname} {title}'
    _json = {'topic_id': f'{topic_id}', 'raw': resp_raw}
    if not first_post:
        _json['reply_to_post_number'] = post_number

    response = requests.request('POST', f'{XJTUMEN_URL_BASE}/posts.json', headers=API_CALL_HEADERS,
                                json=_json
                                )
    print(response)
    print()


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
        return  'assistant'

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
                                               last_post['cooked'],features="lxml").get_text()})
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
