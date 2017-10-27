"""Metric reporting for extractions."""

import boto3
import os
# See http://flask.pocoo.org/docs/0.12/extensiondev/
from flask import _app_ctx_stack as stack
from references.types import Callable
from functools import wraps
from .util import get_application_config, get_application_global


class MetricsSession(object):
    """Reports processing metrics to CloudWatch."""

    namespace = 'arXiv/References'

    def __init__(self, endpoint_url: str=None, aws_access_key: str=None,
                 aws_secret_key: str=None, aws_session_token: str=None,
                 region_name: str=None, verify: bool=True) -> None:
        """Initialize with AWS configuration."""
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_session_token = aws_session_token
        self.verify = verify
        self.endpoint_url = endpoint_url
        self.cloudwatch = boto3.client('cloudwatch', region_name=region_name,
                                       endpoint_url=endpoint_url,
                                       aws_access_key_id=aws_access_key,
                                       aws_secret_access_key=aws_secret_key,
                                       aws_session_token=aws_session_token,
                                       verify=verify)

    def report(self, metric: str, value: object, units: str=None,
               dimensions: dict=None) -> None:
        """
        Put data for a metric to CloudWatch.

        Parameters
        ----------
        metric : str
        value : str, int, float
        units : str or None
        dimensions : dict or None
        """
        metric_data = {'MetricName': metric, 'Value': value}
        if units is not None:
            metric_data.update({'Unit': units})
        if dimensions is not None:
            metric_data.update({
                'Dimensions': [{'Name': key, 'Value': value}
                               for key, value in dimensions.items()]
            })
        self.cloudwatch.put_metric_data(Namespace=self.namespace,
                                        MetricData=[metric_data])

    def reporter(self, func) -> Callable:
        """Generate a decorator to handle metrics reporting."""
        @wraps(func)
        def metrics_wrapper(*args, **kwargs):
            """Report metrics data returned by ``func``."""
            result = func(*args, **kwargs)
            if type(result) is tuple and len(result) > 1 \
                    and hasattr(result[-1], '__iter__'):
                metrics = result[-1]
                remainder = result[:-1]
                for item in metrics:
                    if 'metric' not in item:
                        continue
                    self.report(item['metric'], item['value'],
                                item.get('units'), item.get('dimensions'))
                if type(remainder) in [list, tuple] and len(remainder) == 1:
                    return remainder[0]
                return remainder
            return result
        return metrics_wrapper


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('CLOUDWATCH_ENDPOINT',
                      'https://monitoring.us-east-1.amazonaws.com')
    config.setdefault('AWS_REGION', 'us-east-1')
    config.setdefault('CLOUDWATCH_VERIFY', 'true')


def get_session(app: object = None) -> MetricsSession:
    """Get a new metrics session."""
    config = get_application_config(app)
    g = get_application_global()
    access_key, secret_key, token = None, None, None
    if g is not None and 'credentials' in g and \
            config.get('INSTANCE_CREDENTIALS') == 'true':
        try:
            access_key, secret_key, token = g.credentials.get_credentials()
        except IOError as e:
            pass
    if access_key is None or secret_key is None:
        access_key = config.get('AWS_ACCESS_KEY_ID', None)
        secret_key = config.get('AWS_SECRET_ACCESS_KEY', None)
        token = config.get('AWS_SESSION_TOKEN', None)
    endpoint_url = config.get('CLOUDWATCH_ENDPOINT', None)
    region_name = config.get('AWS_REGION', 'us-east-1')
    verify = config.get('CLOUDWATCH_VERIFY', 'true') == 'true'
    return MetricsSession(endpoint_url, access_key, secret_key, token,
                          region_name, verify=verify)


def current_session():
    """Get/create :class:`.MetricsSession` for this context."""
    g = get_application_global()
    if g is None:
        return get_session()
    if 'metrics' not in g:
        g.metrics = get_session()
    return g.metrics


def report(metric: str, value: object, units: str = None,
           dimensions: dict = None) -> None:
    """
    Put data for a metric to CloudWatch.

    See :meth:`MetricsSession.report`.
    """
    return current_session().report(metric, value, units=units,
                                    dimensions=dimensions)
