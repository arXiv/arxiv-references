"""
Celery configuration module.

See `the celery docs
<http://docs.celeryproject.org/en/latest/userguide/configuration.html>`_.
"""

import os
from urllib import parse

AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
# AWS_SECRET_KEY = parse.quote(AWS_SECRET_KEY, safe='')
# broker_url = "sqs://{}:{}@".format(AWS_ACCESS_KEY, AWS_SECRET_KEY)
REFLINK_REDIS_ENDPOINT = os.environ.get('REFLINK_REDIS_ENDPOINT')
broker_url = "redis://%s/0" % REFLINK_REDIS_ENDPOINT
result_backend = "redis://%s/0" % REFLINK_REDIS_ENDPOINT
broker_transport_options = {
    'region': os.environ.get('REFLINK_AWS_REGION', 'us-east-1'),
    'queue_name_prefix': 'reflink-',
}
worker_prefetch_multiplier = 1
task_acks_late = True
