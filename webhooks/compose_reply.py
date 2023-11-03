import json
import os

import requests

from discourse_bot_python.settings import XJTUMEN_URL_BASE, API_CALL_HEADERS, AttrDict, API_USERNAME
from webhooks.play_oai_api import ai_respond
from bs4 import BeautifulSoup


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
        res = requests.request('GET', f'{XJTUMEN_URL_BASE}/t/-/{topic_id}.json?print=true',
                                                   headers=API_CALL_HEADERS)
        res = res.json()
        all_posts = res['post_stream']['posts']
        OP = BeautifulSoup(all_posts[0]['cooked']).get_text()
        topic_title_and_OP = f'{title}: {OP}'

        extra_msgs = []
        if lookback:
            num_look_back = 3
            if post.reply_to_post_number == 0:
                post.reply_to_post_number = 1
            last_reply_in_thread = all_posts[post.reply_to_post_number-1]
            print(post.reply_to_post_number)
            def get_role(i):
                if i % 2 == 0:
                    return 'assistant'
                else:
                    return 'user'
            def get_should_reply_to(i):
                if i % 2 == 0:
                    return post.username
                else:
                    return API_USERNAME

            for i in range(num_look_back):
                extra_msgs.append({"role":get_role(i),"content":BeautifulSoup(last_reply_in_thread['cooked']).get_text()})

                last_reply_in_thread_num = last_reply_in_thread.get('reply_to_post_number')
                last_reply_name_in_thread_num = last_reply_in_thread.get('reply_to_user')
                if last_reply_in_thread_num is not None and last_reply_in_thread_num != 0:
                    if last_reply_name_in_thread_num is not None:
                        if get_should_reply_to(i) == last_reply_name_in_thread_num['username']:
                            last_reply_in_thread = all_posts[last_reply_in_thread_num-1]
                        print(last_reply_in_thread_num)
                else:
                    break
        extra_msgs = list(reversed(extra_msgs))
        print(extra_msgs)
        resp_raw = ai_respond(f'{prompt}', init_append_msg=f'讨论的主题是：{topic_title_and_OP}',extra_msgs=extra_msgs)

    # resp_raw = f'{post} {uname} {title}'
    _json = {'topic_id': f'{topic_id}', 'raw': resp_raw}
    if not first_post:
        _json['reply_to_post_number'] = post_number

    response = requests.request('POST', f'{XJTUMEN_URL_BASE}/posts.json', headers=API_CALL_HEADERS,
                                json=_json
                                )
    print(response)
    print()


if __name__ == '__main__':
    body = json.loads(open('../sample_req_body.json').read())
    reply_to_post(body)
    print()
