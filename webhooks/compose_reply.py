import json
import os

import requests

from discourse_bot_python.settings import XJTUMEN_URL_BASE, API_CALL_HEADERS, AttrDict


def reply_to_first_post(body, first_post):
    if not isinstance(body, AttrDict):
        body = AttrDict(body)
    post = AttrDict(body.post)
    topic_id = post.topic_id
    post_number = post.post_number
    try:
        title  = post.topic_title
    except KeyError:
        title = ''
    uname = post.name
    if len(uname) == 0:
        uname = post.username

    resp_raw = f'{post} {uname} {title}'
    _json = {'topic_id': f'{topic_id}', 'raw': resp_raw}
    if not first_post:
        _json['reply_to_post_number'] = post_number
    response = requests.request('POST', XJTUMEN_URL_BASE, headers=API_CALL_HEADERS,
                                json=_json
                                )
    print(response)
    print()


if __name__ == '__main__':
    body = json.loads(open('../sample_req_body.json').read())
    reply_to_first_post(body)
    print()
